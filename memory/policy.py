from typing import Dict, Any


class MemoryPolicy:
    def __init__(self, small_threshold: int = 2000, summary_threshold: int = 1000, risk_threshold: float = 0.6):
        self.small_threshold = small_threshold
        self.summary_threshold = summary_threshold
        self.risk_threshold = risk_threshold

    def decide(self, raw_text: str = None, summary: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Return a dict describing persistence actions.

        Keys: store_raw, store_summary, add_to_vector, reason
        """
        md = metadata or {}
        text_len = len(raw_text or "")
        summary_len = len(summary or "")

        # If small, keep raw + summary
        if text_len and text_len <= self.small_threshold:
            return {"store_raw": True, "store_summary": True, "add_to_vector": False, "reason": "small_raw"}

        # If risk flags or high risk score, keep everything and vectorize
        risk_flags = md.get("risk_flags") or []
        risk_score = md.get("risk_score") or 0.0
        if risk_flags or (risk_score and risk_score >= self.risk_threshold):
            return {"store_raw": True, "store_summary": True, "add_to_vector": True, "reason": "high_risk"}

        # If summary exists and is reasonably short, store summary only
        if summary_len and summary_len <= self.summary_threshold:
            return {"store_raw": False, "store_summary": True, "add_to_vector": False, "reason": "short_summary"}

        # Default: store summary only
        return {"store_raw": False, "store_summary": True, "add_to_vector": False, "reason": "default"}
