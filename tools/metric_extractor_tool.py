from typing import Any, Dict, List, Tuple
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
            "table_regions": list,
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

        table_metrics, table_sources, table_evidence = self._extract_from_table_regions(
            document.get("table_regions") or []
        )

        prompt = self._build_prompt(
            document
        )


        raw_output = self._llm._request(
            prompt
        )


        parsed = self._safe_parse(
            raw_output
        )

        # Prefer structured values extracted from table_regions over LLM text-only output.
        for key, value in table_metrics.items():
            if value is not None:
                parsed[key] = value


        validated = self._validate(
            parsed
        )

        validated_meta = validated.get("meta", {})
        validated_meta["metric_sources"] = table_sources
        validated_meta["table_evidence"] = table_evidence
        validated_meta["source_priority"] = "table_regions_over_text"
        validated["meta"] = validated_meta


        return validated



    # =========================
    # PROMPT
    # =========================

    def _build_prompt(
        self,
        document: Dict[str, Any]
    ) -> str:

        cleaned_text = document.get("cleaned_text") or document.get("text") or ""
        table_regions = document.get("table_regions") or []
        table_regions_json = json.dumps(table_regions[:20], ensure_ascii=False)


        return f"""

You are a STRICT financial extraction system.

CRITICAL RULES:

- ONLY extract information explicitly present in the document.
- DO NOT infer.
- DO NOT estimate.
- DO NOT use external knowledge.
- If missing, return null.
- Return ONLY valid JSON.


TABLE REGIONS (JSON, preserve as structured evidence):

{table_regions_json}


DOCUMENT TEXT:

{cleaned_text}


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

    def _extract_from_table_regions(self, table_regions: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
        metrics = {
            "company_name": None,
            "revenue": None,
            "net_profit": None,
            "debt_ratio": None,
            "cash_flow": None,
        }
        metric_sources: Dict[str, Dict[str, Any]] = {}
        table_evidence: List[Dict[str, Any]] = []

        label_map = {
            "revenue": ["revenue", "sales", "营业收入", "营收", "收入"],
            "net_profit": ["net profit", "net income", "profit", "净利润", "归母净利润"],
            "cash_flow": ["cash flow", "operating cash flow", "经营活动现金流", "现金流"],
            "debt_ratio": ["debt ratio", "资产负债率", "liability ratio"],
        }

        for region in table_regions:
            page = region.get("page")
            rows = region.get("rows") or []
            for row in rows:
                if not isinstance(row, list) or not row:
                    continue

                row_cells = [str(c or "").strip() for c in row]
                row_label = row_cells[0].lower()
                numeric_value = self._first_numeric(row_cells[1:])

                for metric_key, aliases in label_map.items():
                    if metrics.get(metric_key) is not None:
                        continue
                    if any(alias in row_label for alias in aliases):
                        if numeric_value is None:
                            continue
                        metrics[metric_key] = numeric_value
                        source = {
                            "source_type": "table",
                            "page": page,
                            "row": row_cells,
                        }
                        metric_sources[metric_key] = source
                        table_evidence.append(source)
                        break

        return metrics, metric_sources, table_evidence

    def _first_numeric(self, cells: List[str]):
        for cell in cells:
            value = self._parse_numeric(cell)
            if value is not None:
                return value
        return None

    def _parse_numeric(self, text: str):
        if text is None:
            return None
        s = str(text).strip()
        if not s:
            return None
        s = s.replace(",", "")
        s = s.replace("，", "")
        s = s.replace("%", "")
        match = re.search(r"[-+]?\d*\.?\d+", s)
        if not match:
            return None
        try:
            return float(match.group(0))
        except Exception:
            return None



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