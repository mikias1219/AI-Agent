"""Event plumbing for agent runs (AGT-02).

- `RecordingEventSink`: keeps events in a list; the sink used by tests.
- `FanoutSink`: forwards each event to several sinks, isolating failures.
- `RunStepRecorder`: turns tool.started / tool.finished events into persisted `RunStep`s.
- `RunEventBroker`: in-memory live buffer per run so HTTP streams can attach at any time
  (replay from seq 0, then follow) without the agent knowing who is listening.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections import OrderedDict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from personal_agent.domain.models import RunEvent, RunStep, StepStatus, ToolContext
from personal_agent.domain.ports import AgentRunRepository, EventSink

logger = logging.getLogger(__name__)

TERMINAL_EVENTS = frozenset({"run.completed", "run.failed"})
MAX_STORED_OUTPUT = 4000


def emit_event(ctx: ToolContext, event_type: str, **data: Any) -> None:
    """Publish one event on the run attached to `ctx`; never let a sink break the caller."""
    if ctx.events is None or ctx.run_id is None:
        return
    try:
        ctx.events.emit(RunEvent(run_id=ctx.run_id, type=event_type, data=data))
    except Exception:  # noqa: BLE001 — observability must not take the run down
        logger.exception("Event sink failed for %s", event_type)


class RecordingEventSink:
    """Collects events in memory, in arrival order."""

    def __init__(self) -> None:
        self.events: list[RunEvent] = []

    def emit(self, event: RunEvent) -> None:
        self.events.append(event)

    @property
    def types(self) -> list[str]:
        return [event.type for event in self.events]


class FanoutSink:
    """Send every event to each sink; one failing sink never breaks the agent."""

    def __init__(self, sinks: Sequence[EventSink]) -> None:
        self._sinks = list(sinks)

    def emit(self, event: RunEvent) -> None:
        for sink in self._sinks:
            try:
                sink.emit(event)
            except Exception:  # noqa: BLE001 — observability must not take the run down
                logger.exception("Event sink failed for %s", event.type)


class RunStepRecorder:
    """Persist tool steps as `RunStep` rows from the event stream (OBS-01)."""

    def __init__(self, repository: AgentRunRepository) -> None:
        self._repository = repository
        self._open: dict[tuple[str, str], RunStep] = {}
        self._seq: dict[str, int] = {}
        self._lock = threading.Lock()

    def emit(self, event: RunEvent) -> None:
        if event.type == "tool.started":
            self._started(event)
        elif event.type == "tool.finished":
            self._finished(event)
        elif event.type in TERMINAL_EVENTS:
            with self._lock:
                self._seq.pop(event.run_id, None)

    def _started(self, event: RunEvent) -> None:
        with self._lock:
            seq = self._seq.get(event.run_id, 0) + 1
            self._seq[event.run_id] = seq
            step = RunStep(
                id=uuid.uuid4().hex,
                run_id=event.run_id,
                seq=seq,
                kind="tool",
                name=str(event.data.get("name", "")),
                arguments=dict(event.data.get("arguments") or {}),
                started_at=datetime.now(UTC),
            )
            self._open[(event.run_id, str(event.data.get("call_id", "")))] = step
        self._repository.add_step(step)

    def _finished(self, event: RunEvent) -> None:
        with self._lock:
            step = self._open.pop((event.run_id, str(event.data.get("call_id", ""))), None)
        if step is None:
            return
        ok = bool(event.data.get("ok"))
        step.status = StepStatus.OK if ok else StepStatus.FAILED
        text = str(event.data.get("output") or "")[:MAX_STORED_OUTPUT]
        if ok:
            step.output = text
        else:
            step.error = text
        step.finished_at = datetime.now(UTC)
        step.duration_ms = int(event.data.get("duration_ms") or 0)
        self._repository.save_step(step)


@dataclass
class _Buffer:
    events: list[RunEvent] = field(default_factory=list)
    done: bool = False


class RunEventBroker:
    """Thread-safe per-run event buffer with blocking readers.

    Assigns a monotonically increasing `seq` (from 1) to each event. Finished buffers are
    kept for a bounded number of runs; older runs are replayed from persisted steps.
    """

    def __init__(self, max_runs: int = 200) -> None:
        self._buffers: OrderedDict[str, _Buffer] = OrderedDict()
        self._cond = threading.Condition()
        self._max_runs = max_runs

    def open(self, run_id: str) -> None:
        with self._cond:
            self._buffers.setdefault(run_id, _Buffer())
            while len(self._buffers) > self._max_runs:
                oldest = next(iter(self._buffers))
                if not self._buffers[oldest].done:
                    break
                del self._buffers[oldest]

    def emit(self, event: RunEvent) -> None:
        with self._cond:
            buffer = self._buffers.setdefault(event.run_id, _Buffer())
            buffer.events.append(replace(event, seq=len(buffer.events) + 1))
            if event.type in TERMINAL_EVENTS:
                buffer.done = True
            self._cond.notify_all()

    def has(self, run_id: str) -> bool:
        with self._cond:
            return run_id in self._buffers

    def snapshot(self, run_id: str) -> list[RunEvent]:
        with self._cond:
            buffer = self._buffers.get(run_id)
            return list(buffer.events) if buffer else []

    def follow(
        self, run_id: str, after_seq: int = 0, idle_timeout: float = 5.0
    ) -> Iterator[RunEvent | None]:
        """Yield events after `after_seq` until the run ends.

        Yields `None` as a keep-alive whenever `idle_timeout` passes with no news, so the
        caller can detect client disconnects.
        """
        index = after_seq
        while True:
            with self._cond:
                buffer = self._buffers.get(run_id)
                if buffer is None:
                    return
                if index >= len(buffer.events) and not buffer.done:
                    self._cond.wait(timeout=idle_timeout)
                pending = buffer.events[index:]
                done = buffer.done
            if not pending and not done:
                yield None
                continue
            yield from pending
            index += len(pending)
            if done:
                return
