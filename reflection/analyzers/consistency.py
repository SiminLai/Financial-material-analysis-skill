from typing import Dict, Any
from reflection.evaluators import BaseEvaluator


class ConsistencyEvaluator(BaseEvaluator):
    name = "consistency"

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Very small heuristic: check that derived metrics are consistent if present
        issues = []
        score = 1.0

        revenue = state.get("revenue")
        net_income = state.get("net_income")
        eps = state.get("eps")

        if revenue is not None and net_income is not None:
            # net income should be <= revenue
            try:
                if float(net_income) > float(revenue):
                    issues.append("net_income > revenue")
                    score = min(score, 0.2)
            except Exception:
                pass

        if net_income is not None and eps is not None:
            # cannot verify exact relation without shares outstanding, but flag suspicious zeros
            try:
                if float(eps) == 0 and float(net_income) != 0:
                    issues.append("eps == 0 while net_income != 0")
                    score = min(score, 0.5)
            except Exception:
                pass

        internal_feedback = ("No obvious consistency issues." if not issues else f"Issues: {', '.join(issues)}")

        return {
            "name": self.name,
            "score": score,
            "internal_feedback": internal_feedback,
            "details": {"issues": issues},
        }
