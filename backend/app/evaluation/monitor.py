from typing import Dict, Any, List
from collections import deque

class QualityMonitor:
    """In-memory rolling quality monitor tracking latency and low-confidence rates."""
    def __init__(self, window_size: int = 100):
        self.history = deque(maxlen=window_size)

    def record_query(self, query_result: Dict[str, Any], duration_ms: float):
        confidence = query_result.get("confidence_score", 0.0)
        has_conflicts = len(query_result.get("conflicts", [])) > 0
        self.history.append({
            "confidence": confidence,
            "has_conflicts": has_conflicts,
            "duration_ms": duration_ms,
            "status": query_result.get("status", "ok")
        })

    def get_metrics(self) -> Dict[str, Any]:
        if not self.history:
            return {"total_queries": 0, "avg_confidence": 0.0, "avg_latency_ms": 0.0}
        total = len(self.history)
        avg_conf = sum(h["confidence"] for h in self.history) / total
        avg_lat = sum(h["duration_ms"] for h in self.history) / total
        low_conf_count = sum(1 for h in self.history if h["confidence"] < 0.5)
        
        return {
            "total_queries_recorded": total,
            "avg_confidence": round(avg_conf, 3),
            "avg_latency_ms": round(avg_lat, 2),
            "low_confidence_rate": round(low_conf_count / total, 3)
        }

quality_monitor = QualityMonitor()
