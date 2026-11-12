"""Bridge run events to Tracer spans (OBS-02)."""

from __future__ import annotations

import time
from typing import Any

from personal_agent.domain.models import RunEvent
from personal_agent.infrastructure.observability.tracing import Span, Tracer


class TracingEventSink:
    """Emit GenAI-flavoured spans from run.started / tool.* / terminal events."""

    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer
        self._runs: dict[str, dict[str, Any]] = {}
        self._tools: dict[tuple[str, str], Span] = {}

    def emit(self, event: RunEvent) -> None:
        if event.type == "run.started":
            trace_id = str(event.data.get("trace_id") or "")
            span = Span(
                trace_id=trace_id or event.run_id,
                span_id=event.run_id[:16],
                parent_span_id=None,
                name="gen_ai.chat",
                start_ns=time.time_ns(),
                attributes={
                    "gen_ai.system": "aura",
                    "gen_ai.request.model": str(event.data.get("model") or ""),
                    "aura.run_id": event.run_id,
                    "aura.origin": str(event.data.get("origin") or ""),
                },
                _exporter=self._tracer.exporter,
            )
            self._runs[event.run_id] = {"span": span, "trace_id": span.trace_id}
            return

        run = self._runs.get(event.run_id)
        if run is None:
            return
        trace_id = str(run["trace_id"])

        if event.type == "tool.started":
            call_id = str(event.data.get("call_id") or "")
            tool_span = Span(
                trace_id=trace_id,
                span_id=call_id[:16] or event.run_id[:16],
                parent_span_id=event.run_id[:16],
                name=f"gen_ai.tool.{event.data.get('name', 'unknown')}",
                start_ns=time.time_ns(),
                attributes={
                    "gen_ai.tool.name": str(event.data.get("name") or ""),
                    "aura.call_id": call_id,
                },
                _exporter=self._tracer.exporter,
            )
            self._tools[(event.run_id, call_id)] = tool_span
            return

        if event.type == "tool.finished":
            call_id = str(event.data.get("call_id") or "")
            tool_span = self._tools.pop((event.run_id, call_id), None)
            if tool_span is not None:
                tool_span.set("gen_ai.tool.status", "ok" if event.data.get("ok") else "error")
                if event.data.get("duration_ms") is not None:
                    tool_span.set("aura.duration_ms", event.data.get("duration_ms"))
                tool_span.end()
            return

        if event.type in {"run.completed", "run.failed"}:
            span: Span = run["span"]
            span.set("aura.status", event.type.split(".", 1)[-1])
            if event.data.get("stop_reason"):
                span.set("aura.stop_reason", event.data.get("stop_reason"))
            span.end()
            self._runs.pop(event.run_id, None)
            for key in [k for k in self._tools if k[0] == event.run_id]:
                self._tools.pop(key).end()
