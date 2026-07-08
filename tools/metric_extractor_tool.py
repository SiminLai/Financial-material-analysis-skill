from typing import Any, Dict
import json
import re

from .base_tool import BaseTool


class MetricExtractorTool(BaseTool):

    name = "metric_extractor"
    description = "Extract structured financial metrics with validation and grounding protection"


    input_schema = {
        "type": "dict",
        "required_fields": ["text"],
        "field_types": {
            "text": str,
        },
    }


    output_schema = {
        "type": "dict",
        "required_fields": [
            "company_name",
            "revenue",
            "net_profit",
            "debt_ratio",
            "cash_flow",
            "meta"
        ],
        "field_types": {
            "company_name": str,
            "revenue": (int, float, type(None)),
            "net_profit": (int, float, type(None)),
            "debt_ratio": (int, float, type(None)),
            "cash_flow": (int, float, type(None)),
            "meta": dict,
        },
    }


    REQUIRED_KEYS = [
        "company_name",
        "revenue",
        "net_profit",
        "debt_ratio",
        "cash_flow"
    ]


    def __init__(self, llm_provider: Any):

        if llm_provider is None:
            raise ValueError(
                "llm_provider must not be None"
            )

        self._llm = llm_provider



    # =========================
    # MAIN ENTRY
    # =========================

    def _execute(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:


        document = input_data

        prompt = self._build_prompt(
            document
        )


        raw_output = self._llm._request(
            prompt
        )


        parsed = self._safe_parse(
            raw_output
        )


        validated = self._validate(
            parsed
        )


        return validated



    # =========================
    # PROMPT
    # =========================

    def _build_prompt(
        self,
        document: Dict[str, Any]
    ) -> str:


        return f"""

You are a STRICT financial extraction system.

CRITICAL RULES:

- ONLY extract information explicitly present in the document.
- DO NOT infer.
- DO NOT estimate.
- DO NOT use external knowledge.
- If missing, return null.
- Return ONLY valid JSON.


DOCUMENT:

{document["text"]}


Extract:

1. Company name
2. Revenue
3. Net profit
4. Debt ratio
5. Operating cash flow


OUTPUT FORMAT:

{{
    "company_name": "company name or null",
    "revenue": number or null,
    "net_profit": number or null,
    "debt_ratio": number or null,
    "cash_flow": number or null
}}

"""



    # =========================
    # SAFE PARSE
    # =========================

    def _safe_parse(
        self,
        raw_output: str
    ) -> Dict:


        if not raw_output:
            raise ValueError(
                "Empty LLM output"
            )


        json_str = self._extract_json(
            raw_output
        )


        try:

            return json.loads(
                json_str
            )

        except Exception as e:

            raise ValueError(
                f"Invalid JSON from LLM: {raw_output}"
            ) from e



    def _extract_json(
        self,
        text: str
    ) -> str:


        text = (
            text
            .replace("```json", "")
            .replace("```", "")
        )


        match = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )


        if not match:

            raise ValueError(
                f"No JSON found: {text}"
            )


        return match.group(0)



    # =========================
    # VALIDATION
    # =========================

    def _validate(
        self,
        data: Dict
    ) -> Dict[str, Any]:


        result = {}

        missing = []


        for key in self.REQUIRED_KEYS:


            value = data.get(
                key,
                None
            )


            if value is None:

                missing.append(key)
                result[key] = None


            else:

                if key == "company_name":

                    result[key] = str(value)

                else:

                    result[key] = self._safe_float(
                        value
                    )


        confidence = self._compute_confidence(
            result,
            missing
        )


        result["meta"] = {

            "missing_fields": missing,

            "confidence": confidence,

            "validation": "strict_mode_v3"

        }


        print(
            "===== RAW LLM OUTPUT ====="
        )

        print(
            result
        )


        return result



    # =========================
    # TYPE SAFETY
    # =========================

    def _safe_float(
        self,
        value
    ):

        try:

            return float(value)

        except:

            return None



    # =========================
    # CONFIDENCE
    # =========================

    def _compute_confidence(
        self,
        data: Dict,
        missing: list
    ) -> float:


        base = 1.0


        base -= (
            0.2 *
            len(missing)
        )


        for k,v in data.items():

            if k == "meta":
                continue


            if v is None:

                base -= 0.1


        return max(
            0.0,
            min(
                1.0,
                base
            )
        )