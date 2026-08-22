from typing import Dict, Any
from reflection.evaluators import BaseEvaluator


class CompletenessEvaluator(BaseEvaluator):
    name = "completeness"

    def __init__(self, required_sections=None):
        if required_sections is None:
            required_sections = ["executive_summary", "financials", "risk_factors"]
        self.required_sections = required_sections

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        present = []
        missing = []
        # assume state may contain a `sections` list or keys
        sections = state.get("sections") or []
        for s in self.required_sections:
            if s in sections or s in state:
                present.append(s)
            else:
                missing.append(s)

        score = 0.0
        if self.required_sections:
            score = len(present) / len(self.required_sections)

        internal_feedback = (
            "All required sections present." if not missing else
            f"Missing sections: {', '.join(missing)}"
        )

        return {
            "name": self.name,
            "score": score,
            "internal_feedback": internal_feedback,
            "details": {"present": present, "missing": missing},
        }
