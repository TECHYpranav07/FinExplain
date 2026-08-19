import time
from typing import Dict, Any, List
from contextlib import contextmanager

class RAGTracer:
    """Collects timing and telemetry traces across RAG pipeline steps."""
    def __init__(self):
        self.spans: List[Dict[str, Any]] = []

    @contextmanager
    def span(self, name: str):
        start_time = time.perf_counter()
        span_data = {"name": name, "start_time": start_time}
        try:
            yield span_data
        finally:
            elapsed = time.perf_counter() - start_time
            span_data["duration_ms"] = round(elapsed * 1000, 2)
            self.spans.append(span_data)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_spans": len(self.spans),
            "total_duration_ms": sum(s.get("duration_ms", 0) for s in self.spans),
            "spans": self.spans
        }
