"""OpenTelemetry-compatible tracing without a hard SDK dependency (OBS-02).

Produces W3C-like 32-hex trace ids and GenAI-flavoured span names. Exporters:
`none` (noop) and `console` (stderr JSON lines). An OTLP exporter can wrap the
same `Tracer` port later.
"""

from __future__ import annotations

import json
import logging
import secrets
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger("personal_agent.trace")


def new_trace_id() -> str:
    """Return a 32-character lowercase hex trace id."""
    return secrets.token_hex(16)


def new_span_id() -> str:
    return secrets.token_hex(8)


class SpanExporter(Protocol):
    def export(self, span: FinishedSpan) -> None: ...


@dataclass(frozen=True, slots=True)
class FinishedSpan:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_ns: int
    end_ns: int
    attributes: Mapping[str, Any]


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    name: str
    start_ns: int
    attributes: dict[str, Any] = field(default_factory=dict)
    _exporter: SpanExporter | None = field(default=None, repr=False)

    def set(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> None:
        finished = FinishedSpan(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            name=self.name,
            start_ns=self.start_ns,
            end_ns=time.time_ns(),
            attributes=dict(self.attributes),
        )
        if self._exporter is not None:
            try:
                self._exporter.export(finished)
            except Exception:  # noqa: BLE001 — tracing must not break the run
                logger.exception("Trace exporter failed for %s", self.name)


class NoopExporter:
    def export(self, span: FinishedSpan) -> None:
        return None


class ConsoleExporter:
    """Print one JSON object per finished span (OTLP-ish GenAI fields)."""

    def export(self, span: FinishedSpan) -> None:
        payload = {
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "name": span.name,
            "duration_ms": (span.end_ns - span.start_ns) / 1_000_000,
            "attributes": dict(span.attributes),
        }
        logger.info("span %s", json.dumps(payload, default=str, ensure_ascii=False))


class Tracer:
    def __init__(self, exporter: SpanExporter | None = None) -> None:
        self.exporter: SpanExporter = exporter or NoopExporter()
        self._exporter = self.exporter  # alias for older call sites

    @contextmanager
    def span(
        self,
        name: str,
        *,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        **attributes: Any,
    ) -> Iterator[Span]:
        current = Span(
            trace_id=trace_id or new_trace_id(),
            span_id=new_span_id(),
            parent_span_id=parent_span_id,
            name=name,
            start_ns=time.time_ns(),
            attributes=dict(attributes),
            _exporter=self._exporter,
        )
        try:
            yield current
        finally:
            current.end()


class NoopTracer(Tracer):
    def __init__(self) -> None:
        super().__init__(NoopExporter())


def build_tracer(exporter_name: str = "none") -> Tracer:
    name = (exporter_name or "none").strip().lower()
    if name in ("", "none", "noop", "off"):
        return NoopTracer()
    if name == "console":
        return Tracer(ConsoleExporter())
    logger.warning("Unknown TRACE_EXPORTER %r; using none", exporter_name)
    return NoopTracer()
