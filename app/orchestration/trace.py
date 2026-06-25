from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4


@dataclass(frozen=True)
class TraceSummary:
    trace_id: str
    timing_ms: float


class TraceTimer:
    def __init__(self) -> None:
        self._trace_id = str(uuid4())
        self._start = perf_counter()

    def finish(self) -> TraceSummary:
        return TraceSummary(
            trace_id=self._trace_id,
            timing_ms=round((perf_counter() - self._start) * 1000, 2),
        )
