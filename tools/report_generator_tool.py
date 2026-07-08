# from tools.base_tool import BaseTool
# import json
# import re


# class ReportGeneratorTool(BaseTool):

#     name = "report_generator"
#     description = "Grounded financial report generator with strict consistency control"

#     input_schema = {
#         "type": "dict",
#         "required_fields": ["document", "metrics", "risk"],
#         "optional_fields": ["browser_result"],
#         "field_types": {
#             "document": dict,
#             "metrics": dict,
#             "risk": dict,
#             "browser_result": dict
#         },
#     }

#     output_schema = {
#         "type": "dict",
#         "required_fields": ["summary", "risk_assessment", "recommendation", "key_points", "meta"],
#         "field_types": {
#             "summary": str,
#             "risk_assessment": str,
#             "recommendation": str,
#             "key_points": list,
#             "meta": dict,
#         },
#     }

#     def __init__(self, llm_provider):
#         self._llm = llm_provider

#     # =========================
#     # MAIN ENTRY
#     # =========================
#     def _execute(self, input_data):

#         document = input_data["document"]
#         metrics = input_data["metrics"]
#         risk = input_data["risk"]
#         browser_result=input_data.get("browser_result")

#         # 1. pre-check consistency
#         self._validate_consistency(metrics, risk)

#         # 2. LLM generation (controlled)
#         prompt = self._build_prompt(document, metrics, risk, browser_result)

#         raw_output = self._llm._request(prompt)


#         # print(raw_output)


#         # 3. safe parse
#         return self._safe_parse(raw_output, metrics, risk)

#     # =========================
#     # PROMPT (STRICT CONTROL)
#     # =========================
#     def _build_prompt(self, document, metrics, risk, browser_result=None):
#         external_info = ""

#         if browser_result is not None:

#             external_info = f"""

#         EXTERNAL WEB EVIDENCE

#         The following information was retrieved because
#         the quantitative risk assessment exceeded the routing threshold.

#         This information is intended ONLY to provide
#         supporting explanations for the identified risks.

#         {json.dumps(browser_result, indent=2)}

#         Rules for external evidence:

#         - Use it ONLY to explain why the current risk exists. If the external evidence conflicts with the quantitative metrics,
# always trust the quantitative metrics.
#         - NEVER change financial metrics.
#         - NEVER modify risk_score.
#         - NEVER invent new financial data.
#         - Treat this as supporting qualitative evidence.
#         """
#         return f"""
# You are a STRICT financial reporting system.

# CRITICAL RULES:

# - You MUST NOT modify any financial numbers.
# - You MUST NOT modify the calculated risk_score.
# - You MUST base all quantitative conclusions ONLY on provided metrics and risk.
# - If external web evidence is provided, use it ONLY to explain or support the risk assessment.
# - Never invent financial data.
# - Never contradict the provided metrics.
# - Return ONLY valid JSON.

# DOCUMENT (context only):
# {document["text"]}

# METRICS (ground truth):
# {json.dumps(metrics, indent=2)}

# RISK (ground truth):
# {json.dumps(risk, indent=2)}


# {external_info}

# OUTPUT FORMAT:
# {{
#     "summary": "Grounded summary based ONLY on metrics",
#     "risk_assessment": "Must align with risk_level",
#     "recommendation": "BUY | HOLD | SELL",
#     "key_points": []
# }}
# """

#     # =========================
#     # CONSISTENCY CHECK (IMPORTANT)
#     # =========================
#     def _validate_consistency(self, metrics, risk):

#         if "risk_score" not in risk:
#             raise ValueError("Missing risk_score")

#         if metrics.get("revenue") is None:
#             raise ValueError("Invalid metrics: revenue missing")

#     # =========================
#     # SAFE PARSER
#     # =========================
#     def _safe_parse(self, raw_output, metrics, risk):

#         json_str = self._extract_json(raw_output)

#         parsed = json.loads(json_str)

#         return self._post_validate(parsed, metrics, risk)

#     def _extract_json(self, text):

#         match = re.search(r"\{.*\}", text, re.DOTALL)

#         if not match:
#             raise ValueError("No JSON found in LLM output")

#         return match.group(0)

#     # =========================
#     # POST VALIDATION (CRITICAL)
#     # =========================
#     def _post_validate(self, report, metrics, risk):

#         # enforce recommendation logic consistency
#         expected = self._derive_recommendation(metrics, risk)

#         report["recommendation"] = expected

#         return {
#             **report,
#             "meta": {
#                 "engine": self.name,
#                 "grounded": True,
#                 "risk_score": risk.get("risk_score"),
#                 "validation": "strict"
#             }
#         }

#     # =========================
#     # RULE-BASED RECOMMENDATION (IMPORTANT)
#     # =========================
#     def _derive_recommendation(self, metrics, risk):

#         score = risk.get("risk_score", 1.0)

#         profit = metrics.get("net_profit", 0)
#         cash = metrics.get("cash_flow", 0)

#         if score < 0.3 and profit > 0 and cash > 0:
#             return "BUY"

#         if score < 0.7:
#             return "HOLD"

#         return "SELL"

from tools.base_tool import BaseTool
import json
import re


class ReportGeneratorTool(BaseTool):

    name = "report_generator"
    description = "Grounded financial report generator with strict consistency control"

    input_schema = {
        "type": "dict",
        "required_fields": [
            "document",
            "metrics",
            "risk"
        ],
        "optional_fields": [
            "browser_result"
        ],
        "field_types": {
            "document": dict,
            "metrics": dict,
            "risk": dict,
            "browser_result": dict
        },
    }


    output_schema = {
        "type": "dict",
        "required_fields": [
            "summary",
            "risk_assessment",
            "recommendation",
            "key_points",
            "external_evidence",
            "meta"
        ],
        "field_types": {
            "summary": str,
            "risk_assessment": str,
            "recommendation": str,
            "key_points": list,
            "external_evidence": dict,
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

        browser_result = input_data.get(
            "browser_result",
            None
        )


        # 1. consistency check
        self._validate_consistency(
            metrics,
            risk
        )


        # 2. build prompt
        prompt = self._build_prompt(
            document,
            metrics,
            risk,
            browser_result
        )


        # 3. LLM generation

        raw_output = self._llm._request(prompt)


        # 4. parse

        return self._safe_parse(
            raw_output,
            metrics,
            risk,
            browser_result
        )



    # =========================
    # PROMPT
    # =========================

    def _build_prompt(
        self,
        document,
        metrics,
        risk,
        browser_result=None
    ):


        external_info = ""


        if browser_result:


            external_info = f"""

EXTERNAL WEB EVIDENCE FROM MCP


The following information was retrieved from external sources.

IMPORTANT:

- This information is ONLY supporting evidence.
- Do NOT modify financial metrics.
- Do NOT modify risk_score.
- Do NOT invent financial numbers.
- Do NOT override quantitative analysis.


Evidence:

{json.dumps(browser_result, indent=2)}


"""


        return f"""

You are a STRICT financial reporting system.


RULES:

- Financial metrics are ground truth.
- Risk score is ground truth.
- Never change numerical values.
- Never create new financial facts.
- Return ONLY JSON.


DOCUMENT:

{document["text"]}



METRICS:

{json.dumps(metrics, indent=2)}



RISK:

{json.dumps(risk, indent=2)}



{external_info}



OUTPUT FORMAT:


{{
    "summary": "",
    "risk_assessment": "",
    "recommendation": "BUY | HOLD | SELL",
    "key_points": []
}}

"""



    # =========================
    # CONSISTENCY CHECK
    # =========================

    def _validate_consistency(
        self,
        metrics,
        risk
    ):


        if "risk_score" not in risk:
            raise ValueError(
                "Missing risk_score"
            )


        if metrics.get("revenue") is None:
            raise ValueError(
                "Invalid metrics: revenue missing"
            )



    # =========================
    # SAFE PARSER
    # =========================

    def _safe_parse(
        self,
        raw_output,
        metrics,
        risk,
        browser_result=None
    ):


        json_str = self._extract_json(
            raw_output
        )


        parsed = json.loads(
            json_str
        )


        return self._post_validate(
            parsed,
            metrics,
            risk,
            browser_result
        )



    def _extract_json(
        self,
        text
    ):


        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )


        if not match:
            raise ValueError(
                "No JSON found in LLM output"
            )


        return match.group(0)



    # =========================
    # POST VALIDATION
    # =========================

    def _post_validate(
        self,
        report,
        metrics,
        risk,
        browser_result=None
    ):


        expected = self._derive_recommendation(
            metrics,
            risk
        )


        # 强制覆盖推荐结果
        report["recommendation"] = expected



        # 保存 MCP 原始证据

        if browser_result:


            external_evidence = {

                "source": "MCP",

                "available": True,

                "description":
                    "External information retrieved from web sources",

                "data":
                    browser_result
            }


        else:


            external_evidence = {

                "source": "MCP",

                "available": False,

                "description":
                    "No external evidence retrieved",

                "data": []
            }



        return {


            **report,


            "external_evidence":
                external_evidence,


            "meta": {

                "engine":
                    self.name,


                "grounded":
                    True,


                "risk_score":
                    risk.get("risk_score"),


                "validation":
                    "strict"
            }
        }



    # =========================
    # RECOMMENDATION LOGIC
    # =========================

    def _derive_recommendation(
        self,
        metrics,
        risk
    ):


        score = risk.get(
            "risk_score",
            1.0
        )


        profit = metrics.get(
            "net_profit",
            0
        )


        cash = metrics.get(
            "cash_flow",
            0
        )


        if (
            score < 0.3
            and profit > 0
            and cash > 0
        ):
            return "BUY"


        if score < 0.7:
            return "HOLD"


        return "SELL"