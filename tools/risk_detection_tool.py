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
            "revenue": (int, float, type(None)),
            "net_profit": (int, float, type(None)),
            "debt_ratio": (int, float, type(None)),
            "cash_flow": (int, float, type(None)),
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
            return float(value)
        except:
            return None
    # =========================
    # MAIN ENTRY
    # =========================
    def _execute(self, input_data):

        metrics = input_data

        # 1. deterministic core
        rule_score, rule_flags = self._rule_based_score(metrics)

        # 2. LLM explanation (SAFE)
        llm_analysis = self._llm_reasoning(metrics, rule_flags, rule_score)

        # 3. final merge (controlled)
        return self._merge(rule_score, rule_flags, llm_analysis)
    def _safe_float(self, value):
        try:
            if value is None:
                return None
            return float(value)
        except:
            return None
    # =========================
    # RULE ENGINE (TRUTH SOURCE)
    # =========================
    def _rule_based_score(self, m):

        score = 0.0
        flags = []

        debt_ratio = self._safe_float(m.get("debt_ratio"))
        cash_flow = self._safe_float(m.get("cash_flow"))
        net_profit = self._safe_float(m.get("net_profit"))
        revenue = self._safe_float(m.get("revenue"))

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

        score += missing_penalty

        if debt_ratio is not None and debt_ratio > 0.7:
            score += 0.4
            flags.append("HIGH_LEVERAGE")
        elif debt_ratio is not None and debt_ratio > 0.5:
            score += 0.2
            flags.append("ELEVATED_LEVERAGE")

        if cash_flow is not None and cash_flow < 5000:
            score += 0.3
            flags.append("LOW_CASH_FLOW")

        if net_profit is not None and net_profit < 0:
            score += 0.3
            flags.append("LOSS_MAKING")

        # profitability checks: profit margin
        try:
            if revenue is not None and net_profit is not None and revenue != 0:
                profit_margin = net_profit / revenue
                if profit_margin < 0.05:
                    score += 0.15
                    flags.append("LOW_PROFIT_MARGIN")
                if profit_margin < 0:
                    score += 0.2
                    flags.append("NEGATIVE_MARGIN")
        except Exception:
            pass

        # anomaly detection: inconsistent cash flow vs profit
        if (net_profit is not None) and (cash_flow is not None):
            # if cash flow is negative while profit positive -> warning
            if cash_flow < 0 and net_profit > 0:
                score += 0.25
                flags.append("CASH_FLOW_NEGATIVE_WHILE_PROFIT")

            # large mismatch between reported profit and cash (possible non-cash adjustments)
            try:
                denom = max(1.0, abs(net_profit))
                if abs(net_profit - cash_flow) / denom > 2.0:
                    score += 0.15
                    flags.append("PROFIT_CASH_MISMATCH")
            except Exception:
                pass

        # anomaly: revenue negative or implausibly small
        if revenue is not None:
            if revenue < 0:
                score += 0.3
                flags.append("NEGATIVE_REVENUE")
            elif revenue > 0 and revenue < 100:
                # very small revenue (units likely missing) may indicate parsing error
                score += 0.1
                flags.append("SUSPICIOUS_SMALL_REVENUE")

        # cash flow to revenue sanity check
        try:
            if revenue and cash_flow is not None:
                c2r = cash_flow / max(1.0, revenue)
                if c2r < 0.01:
                    score += 0.1
                    flags.append("LOW_CASH_FLOW_TO_REVENUE")
        except Exception:
            pass

        return min(score, 1.0), flags

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

        except:
            return {"risk_level_explanation": "invalid_llm_output", "key_drivers": []}

    # =========================
    # FINAL MERGE (CONTROLLED)
    # =========================
    def _merge(self, score, flags, llm_analysis):

        if score < 0.3:
            level = "LOW"
        elif score < 0.7:
            level = "MEDIUM"
        else:
            level = "HIGH"

        return {
            "risk_score": score,
            "risk_level": level,
            "risk_flags": flags,

            "explanation": llm_analysis,

            "meta": {
                "engine": "risk_v2.1",
                "llm_role": "explanation_only",
                "rule_source": "deterministic"
            }
        }
    
