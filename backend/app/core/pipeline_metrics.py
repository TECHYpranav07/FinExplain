"""
Lightweight per-stage pipeline metrics for FinExplain.

Provides a ``PipelineTimer`` context manager that tracks elapsed time
per pipeline stage per request.  Results are logged with the request
and can be used for p50/p95/p99 monitoring.
"""

import time
import logging
from typing import Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PipelineTimer:
    """Accumulates per-stage timing for a single pipeline execution."""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or ""
        self.stages: Dict[str, float] = {}
        self._start: Optional[float] = None

    @contextmanager
    def stage(self, name: str):
        """Time a named pipeline stage."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.stages[name] = elapsed_ms

    def total_ms(self) -> float:
        return sum(self.stages.values())

    def summary(self) -> str:
        """Return a human-readable per-stage breakdown."""
        lines = []
        total = self.total_ms()
        for name, ms in self.stages.items():
            pct = (ms / total * 100) if total > 0 else 0
            bar = "█" * int(pct / 2.5)
            lines.append(f"  {name:<25s} {ms:>8.1f}ms  {pct:>5.1f}%  {bar}")
        lines.append(f"  {'TOTAL':<25s} {total:>8.1f}ms")
        return "\n".join(lines)

    def log_summary(self):
        """Log the timing summary at INFO level."""
        logger.info(
            f"[PipelineMetrics] Request {self.request_id}\n{self.summary()}"
        )
