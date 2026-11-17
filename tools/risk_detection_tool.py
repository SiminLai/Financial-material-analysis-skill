import math

from tools.base_tool import BaseTool


class RiskDetectionTool(BaseTool):
    name = "risk_detection"
    RULE_VERSION = "research-rules-1.0"

    def __init__(self, llm_provider=None):
        self._llm = llm_provider

    def _execute(self, input_data):
        facts = {fact["metric"]: fact for fact in input_data.get("facts", [])}
        checks = []

        def evaluate(name, names, predicate, weight, compatible=False):
            selected = [facts.get(metric, {}) for metric in names]
            usable = all(fact.get("validation_status") == "validated"
                         and isinstance(fact.get("value"), (int, float))
                         and not isinstance(fact.get("value"), bool)
                         and math.isfinite(fact["value"]) for fact in selected)
            if usable and compatible:
                usable = all(selected[0].get(key) not in (None, "", "unknown")
                             and all(fact.get(key) == selected[0][key] for fact in selected)
                             for key in ("period", "scope", "currency", "unit"))
                usable = usable and selected[-1]["value"] > 0
            triggered = bool(predicate(*[fact["value"] for fact in selected])) if usable else False
            checks.append({"rule": name,
                           "status": "triggered" if triggered else "not_triggered" if usable else "not_evaluable",
                           "fact_ids": [fact["id"] for fact in selected if fact.get("id")],
                           "required_metrics": names, "weight": weight,
                           "reason": "Inputs validated" if usable else "Missing, unverified or incomparable inputs"})

        evaluate("HIGH_LEVERAGE", ["debt_ratio"], lambda debt: debt > 0.7, 0.4)
        evaluate("LOW_OPERATING_CASH_FLOW", ["cash_flow", "revenue"], lambda cash, revenue: cash / revenue < 0.01, 0.3, True)
        evaluate("LOW_PROFIT_MARGIN", ["net_profit", "revenue"], lambda profit, revenue: profit / revenue < 0.05, 0.15, True)
        evaluate("NEGATIVE_REVENUE", ["revenue"], lambda revenue: revenue < 0, 0.3)
        evaluated = [check for check in checks if check["status"] != "not_evaluable"]
        score = min(sum(check["weight"] for check in checks if check["status"] == "triggered"), 1.0)
        return {"risk_score": score,
                "risk_level": "UNKNOWN" if len(evaluated) != len(checks) else "HIGH" if score >= 0.6 else "MEDIUM" if score >= 0.3 else "LOW",
                "assessment_status": "complete" if len(evaluated) == len(checks) else "partial" if evaluated else "not_evaluable",
                "risk_flags": [check["rule"] for check in checks if check["status"] == "triggered"],
                "rule_checks": checks,
                "meta": {"rule_version": self.RULE_VERSION, "missing_data_penalty": 0,
                         "score_meaning": "Heuristic signals, not calibrated investment risk"}}
