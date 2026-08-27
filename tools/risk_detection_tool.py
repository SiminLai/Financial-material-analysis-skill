from tools.base_tool import BaseTool
import json
import re


class RiskDetectionTool(BaseTool):

    name = "risk_detection"
    description = "Deterministic financial risk engine with explainable AI layer"

    input_schema = {
        "type": "dict",
        "required_fields": ["revenue", "net_profit", "debt_ratio", "cash_flow"],
        "field_types": {
            "revenue": (int, float, dict, type(None)),
            "net_profit": (int, float, dict, type(None)),
            "debt_ratio": (int, float, dict, type(None)),
            "cash_flow": (int, float, dict, type(None)),
        },
    }

    output_schema = {
        "type": "dict",
        "required_fields": ["risk_score", "risk_level", "risk_flags", "explanation", "meta"],
        "field_types": {
            "risk_score": (int, float),
            "risk_level": str,
            "risk_flags": list,
            "explanation": dict,
            "meta": dict,
        },
    }

    def __init__(self, llm_provider):
        self._llm = llm_provider

    def _safe_float(self, value):
        try:
            if value is None:
                return None
            if isinstance(value, dict):
                value = value.get("value")
            return float(value)
        except Exception:
            return None

    def _metric_value(self, metric):
        if metric is None:
            return None
        if isinstance(metric, dict):
            return self._safe_float(metric.get("value"))
        return self._safe_float(metric)

    def _metric_unit(self, metric):
        if isinstance(metric, dict):
            return metric.get("unit")
        return None

    def _normalize_metrics(self, metrics):
        normalized = dict(metrics or {})
        for key in ["revenue", "net_profit", "cash_flow", "debt_ratio", "cash_flow_ratio", "net_profit_yoy"]:
            if key not in normalized:
                continue
            value = normalized.get(key)
            if value is None:
                normalized[key] = None
                continue
            if isinstance(value, dict):
                normalized[key] = value
                continue
            normalized[key] = {
                "value": self._safe_float(value),
                "unit": "unknown",
                "period": "FY2025",
                "source": "Financial Results",
            }
        return normalized
    # =========================
    # MAIN ENTRY
    # =========================
    def _execute(self, input_data):

        metrics = self._normalize_metrics(input_data)

        # 1. deterministic core
        rule_score, rule_flags = self._rule_based_score(metrics)

        # 2. LLM explanation (SAFE)
        llm_analysis = self._llm_reasoning(metrics, rule_flags, rule_score)

        # 3. final merge (controlled)
        return self._merge(rule_score, rule_flags, llm_analysis, metrics)

    # =========================
    # RULE ENGINE (TRUTH SOURCE)
    # =========================
    def _rule_based_score(self, m):

        score = 0.0
        flags = []

        debt_ratio = self._metric_value(m.get("debt_ratio"))
        cash_flow = self._metric_value(m.get("cash_flow"))
        net_profit = self._metric_value(m.get("net_profit"))
        revenue = self._metric_value(m.get("revenue"))
        revenue_unit = self._metric_unit(m.get("revenue"))
        net_profit_yoy = self._as_ratio(m.get("net_profit_yoy"))

        # penalize missing critical data: missing metrics increase risk
        missing_penalty = 0.0
        if revenue is None:
            missing_penalty += 0.2
            flags.append("MISSING_REVENUE")
        if net_profit is None:
            missing_penalty += 0.15
            flags.append("MISSING_NET_PROFIT")
        if cash_flow is None:
            missing_penalty += 0.15
            flags.append("MISSING_CASH_FLOW")
        if debt_ratio is None:
            missing_penalty += 0.1
            flags.append("MISSING_DEBT_RATIO")
            flags.append("MISSING_FINANCIAL_FIELD")

        score += missing_penalty

        if debt_ratio is not None and debt_ratio > 0.7:
            score += 0.4
            flags.append("HIGH_LEVERAGE")
        elif debt_ratio is not None and debt_ratio > 0.5:
            score += 0.2
            flags.append("ELEVATED_LEVERAGE")

        # unit-sensitive rule: avoid absolute thresholds and use normalized unit-aware checks
        try:
            if revenue is not None and revenue != 0 and cash_flow is not None:
                c2r = cash_flow / max(abs(revenue), 1.0)
                if c2r < 0.01:
                    score += 0.3
                    flags.append("LOW_CASH_FLOW")
                elif c2r < 0.03:
                    score += 0.1
                    flags.append("WEAK_CASH_FLOW_RATIO")
        except Exception:
            pass

        if debt_ratio is not None and 0.65 <= debt_ratio <= 0.7:
            flags.append("LEVERAGE_NEAR_HIGH_THRESHOLD")

        if net_profit_yoy is not None:
            if net_profit_yoy <= -0.50:
                score += 0.2
                flags.append("SHARP_PROFIT_DECLINE")
            elif net_profit_yoy <= -0.30:
                score += 0.1
                flags.append("PROFIT_DECLINE")

        # Do not flag LOSS_MAKING solely because net_profit < 0.
        # Profitability is evaluated with context, not simple sign-based risk.

        # profitability checks: profit margin
        try:
            if revenue is not None and net_profit is not None and revenue != 0:
                profit_margin = net_profit / revenue
                if profit_margin < 0.05:
                    score += 0.15
                    flags.append("LOW_PROFIT_MARGIN")
                if profit_margin < 0:
                    score += 0.15
                    flags.append("NEGATIVE_MARGIN")
        except Exception:
            pass

        # anomaly detection: inconsistent cash flow vs profit
        if (net_profit is not None) and (cash_flow is not None) and (revenue is not None) and (revenue != 0):
            # Only trigger when discrepancy is material relative to revenue, not merely sign mismatch.
            try:
                discrepancy = abs(net_profit - cash_flow) / abs(revenue)
                if discrepancy > 0.35:
                    score += 0.15
                    flags.append("PROFIT_CASH_DISCREPANCY")
            except Exception:
                pass

        # anomaly: revenue negative or implausibly small
        if revenue is not None:
            if revenue < 0:
                score += 0.3
                flags.append("NEGATIVE_REVENUE")
            elif revenue > 0 and revenue_unit in ("million_usd", "usd") and revenue < 100:
                score += 0.1
                flags.append("SUSPICIOUS_SMALL_REVENUE")

        return min(score, 1.0), flags

    def _as_ratio(self, value):
        value = self._safe_float(value)
        if value is None:
            return None
        return value / 100.0 if abs(value) > 1.0 else value

    # =========================
    # LLM (EXPLANATION ONLY)
    # =========================
    def _llm_reasoning(self, metrics, flags, score):

        prompt = f"""
You are a financial risk explanation assistant.

IMPORTANT RULE:
- DO NOT compute risk score
- ONLY explain given risk signals

INPUT METRICS:
{metrics}

RULE FLAGS:
{flags}

RISK SCORE (already computed):
{score}

Return ONLY JSON:
{{
    "risk_level_explanation": "...",
    "key_drivers": []
}}
"""

        raw = self._llm._request(prompt)

        return self._safe_parse(raw)

    # =========================
    # SAFE PARSER
    # =========================
    def _safe_parse(self, text):

        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return {"risk_level_explanation": "parse_failed", "key_drivers": []}

            return json.loads(match.group(0))

        except Exception:
            return {"risk_level_explanation": "invalid_llm_output", "key_drivers": []}

    # =========================
    # FINAL MERGE (CONTROLLED)
    # =========================
    def _merge(self, score, flags, llm_analysis, metrics=None):

        if score < 0.3:
            level = "LOW"
        elif score < 0.7:
            level = "MEDIUM"
        else:
            level = "HIGH"

        debt_ratio = self._metric_value((metrics or {}).get("debt_ratio"))
        cash_flow_ratio = None
        revenue = self._metric_value((metrics or {}).get("revenue"))
        cash_flow = self._metric_value((metrics or {}).get("cash_flow"))
        if revenue not in (None, 0) and cash_flow is not None:
            try:
                cash_flow_ratio = cash_flow / max(abs(revenue), 1.0)
            except Exception:
                cash_flow_ratio = None

        net_profit_yoy = self._metric_value((metrics or {}).get("net_profit_yoy"))
        if net_profit_yoy is not None and abs(net_profit_yoy) > 1:
            net_profit_yoy = net_profit_yoy / 100.0

        def _rule_reason(value, threshold, metric_name, trigger_message, non_trigger_message):
            if value is None:
                return f"{metric_name} is unavailable; threshold check could not be evaluated."
            value_str = f"{value:.4f}" if isinstance(value, float) else str(value)
            if value <= threshold:
                return f"{metric_name}={value_str} <= {threshold}; {trigger_message}"
            return f"{metric_name}={value_str} > {threshold}; {non_trigger_message}"

        rule_checks = {
            "HIGH_LEVERAGE": {
                "triggered": "HIGH_LEVERAGE" in flags,
                "threshold": 0.70,
                "value": debt_ratio,
                "reason": _rule_reason(debt_ratio, 0.70, "debt_ratio", "HIGH_LEVERAGE triggers when debt_ratio exceeds 0.70.", "debt_ratio is below the HIGH_LEVERAGE threshold; HIGH_LEVERAGE is not triggered.") if debt_ratio is not None else "debt_ratio is unavailable; HIGH_LEVERAGE could not be evaluated.",
            },
            "LOW_CASH_FLOW": {
                "triggered": "LOW_CASH_FLOW" in flags,
                "threshold": 0.01,
                "value": cash_flow_ratio,
                "reason": _rule_reason(cash_flow_ratio, 0.01, "cash_flow_ratio", "LOW_CASH_FLOW triggers when cash_flow_ratio is at or below 0.01.", "cash_flow_ratio remains above 0.01; LOW_CASH_FLOW is not triggered.") if cash_flow_ratio is not None else "cash_flow_ratio is unavailable; LOW_CASH_FLOW could not be evaluated.",
            },
            "SHARP_PROFIT_DECLINE": {
                "triggered": "SHARP_PROFIT_DECLINE" in flags,
                "threshold": -0.50,
                "value": net_profit_yoy,
                "reason": _rule_reason(net_profit_yoy, -0.50, "net_profit_yoy", "SHARP_PROFIT_DECLINE triggers when net_profit_yoy is at or below -0.50.", "net_profit_yoy is above -0.50; SHARP_PROFIT_DECLINE is not triggered.") if net_profit_yoy is not None else "net_profit_yoy is unavailable; SHARP_PROFIT_DECLINE could not be evaluated.",
            },
        }

        explanation = dict(llm_analysis or {})
        explanation["rule_checks"] = rule_checks

        return {
            "risk_score": score,
            "risk_level": level,
            "risk_flags": flags,
            "explanation": explanation,
            "meta": {
                "engine": "risk_v2.1",
                "llm_role": "explanation_only",
                "rule_source": "deterministic",
                "rule_checks": rule_checks,
            }
        }

    def _as_ratio(self, value):
        value = self._safe_float(value)
        if value is None:
            return None
        return value / 100.0 if abs(value) > 1.0 else value

    # =========================
    # LLM (EXPLANATION ONLY)
    # =========================
    def _llm_reasoning(self, metrics, flags, score):

        prompt = f"""
You are a financial risk explanation assistant.

IMPORTANT RULE:
- DO NOT compute risk score
- ONLY explain given risk signals

INPUT METRICS:
{metrics}

RULE FLAGS:
{flags}

RISK SCORE (already computed):
{score}

Return ONLY JSON:
{{
    "risk_level_explanation": "...",
    "key_drivers": []
}}
"""

        raw = self._llm._request(prompt)

        return self._safe_parse(raw)

    # =========================
    # SAFE PARSER
    # =========================
    def _safe_parse(self, text):

        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return {"risk_level_explanation": "parse_failed", "key_drivers": []}

            return json.loads(match.group(0))

        except Exception:
            return {"risk_level_explanation": "invalid_llm_output", "key_drivers": []}

