from tools.base_tool import BaseTool
import json
import re


class ReportGeneratorTool(BaseTool):

    name = "report_generator"
    description = "Grounded financial report generator with strict consistency control"

    input_schema = {
        "type": "dict",
        "required_fields": ["document", "metrics", "risk"],
        "field_types": {
            "document": dict,
            "metrics": dict,
            "risk": dict,
        },
    }

    output_schema = {
        "type": "dict",
        "required_fields": ["summary", "risk_assessment", "recommendation", "key_points", "meta"],
        "field_types": {
            "summary": str,
            "risk_assessment": str,
            "recommendation": str,
            "key_points": list,
            "meta": dict,
        },
    }

    def __init__(self, llm_provider):
        self._llm = llm_provider

    # =========================
    # MAIN ENTRY
    # =========================
    def _execute(self, input_data):

        document = input_data["document"]
        metrics = input_data["metrics"]
        risk = input_data["risk"]

        # 1. pre-check consistency
        self._validate_consistency(metrics, risk)

        # 2. LLM generation (controlled)
        prompt = self._build_prompt(document, metrics, risk)

        raw_output = self._llm._request(prompt)


        # print(raw_output)


        # 3. safe parse
        return self._safe_parse(raw_output, metrics, risk)

    # =========================
    # PROMPT (STRICT CONTROL)
    # =========================
    def _build_prompt(self, document, metrics, risk):

        return f"""
You are a STRICT financial reporting system.

CRITICAL RULES:
- You MUST NOT modify any given numbers
- You MUST base conclusions ONLY on provided metrics and risk
- Do NOT invent new financial data
- Return ONLY valid JSON

DOCUMENT (context only):
{document["text"]}

METRICS (ground truth):
{json.dumps(metrics, indent=2)}

RISK (ground truth):
{json.dumps(risk, indent=2)}

OUTPUT FORMAT:
{{
    "summary": "Grounded summary based ONLY on metrics",
    "risk_assessment": "Must align with risk_level",
    "recommendation": "BUY | HOLD | SELL",
    "key_points": []
}}
"""

    # =========================
    # CONSISTENCY CHECK (IMPORTANT)
    # =========================
    def _validate_consistency(self, metrics, risk):

        if "risk_score" not in risk:
            raise ValueError("Missing risk_score")

        if metrics.get("revenue") is None:
            raise ValueError("Invalid metrics: revenue missing")

    # =========================
    # SAFE PARSER
    # =========================
    def _safe_parse(self, raw_output, metrics, risk):

        json_str = self._extract_json(raw_output)

        parsed = json.loads(json_str)

        return self._post_validate(parsed, metrics, risk)

    def _extract_json(self, text):

        match = re.search(r"\{.*\}", text, re.DOTALL)

        if not match:
            raise ValueError("No JSON found in LLM output")

        return match.group(0)

    # =========================
    # POST VALIDATION (CRITICAL)
    # =========================
    def _post_validate(self, report, metrics, risk):

        # enforce recommendation logic consistency
        expected = self._derive_recommendation(metrics, risk)

        report["recommendation"] = expected

        return {
            **report,
            "meta": {
                "engine": "report_v2.2",
                "grounded": True,
                "risk_score": risk.get("risk_score"),
                "validation": "strict"
            }
        }

    # =========================
    # RULE-BASED RECOMMENDATION (IMPORTANT)
    # =========================
    def _derive_recommendation(self, metrics, risk):

        score = risk.get("risk_score", 1.0)

        profit = metrics.get("net_profit", 0)
        cash = metrics.get("cash_flow", 0)

        if score < 0.3 and profit > 0 and cash > 0:
            return "BUY"

        if score < 0.7:
            return "HOLD"

        return "SELL"