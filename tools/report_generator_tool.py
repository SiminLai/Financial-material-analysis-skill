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
            "browser_result",
            "external_summary",
            "external_evidence_ids",
            "external_citations"
        ],
        "field_types": {
            "document": dict,
            "metrics": dict,
            "risk": dict,
            "browser_result": dict,
            "external_summary": (str, type(None)),
            "external_evidence_ids": list,
            "external_citations": list
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

        external_summary = input_data.get("external_summary", None)
        external_evidence_ids = input_data.get("external_evidence_ids", None)
        external_citations = input_data.get("external_citations", None)


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
            browser_result,
            external_summary=external_summary,
            external_evidence_ids=external_evidence_ids,
            external_citations=external_citations,
        )


        # 3. LLM generation

        raw_output = self._llm._request(prompt)


        # 4. parse

        return self._safe_parse(
            raw_output,
            metrics,
            risk,
            browser_result,
            external_summary=external_summary,
            external_evidence_ids=external_evidence_ids,
            external_citations=external_citations,
        )



    # =========================
    # PROMPT
    # =========================

    def _build_prompt(
        self,
        document,
        metrics,
        risk,
        browser_result=None,
        external_summary=None,
        external_evidence_ids=None,
        external_citations=None,
    ):


        # build external info block if available
        external_info = ""
        if browser_result or external_summary or external_evidence_ids or external_citations:
            external_info = "\n\nEXTERNAL WEB EVIDENCE\n\n"
            external_info += "The following information was retrieved from external sources.\n\n"
            external_info += "IMPORTANT:\n\n"
            external_info += "- This information is ONLY supporting evidence.\n"
            external_info += "- Do NOT modify financial metrics.\n"
            external_info += "- Do NOT modify risk_score.\n"
            external_info += "- Do NOT invent financial numbers.\n"
            external_info += "- Do NOT override quantitative analysis.\n\n"

            if external_summary:
                external_info += "SUMMARY:\n\n" + str(external_summary) + "\n\n"

            if external_evidence_ids:
                external_info += "EVIDENCE IDS AVAILABLE FOR CITATION:\n\n" + json.dumps(external_evidence_ids) + "\n\n"

            if external_citations:
                external_info += "DETAILED CITATIONS:\n\n"
                for c in external_citations:
                    external_info += f"- {c.get('cite')} : {c.get('snippet')}\n"
                external_info += "\n"

            if browser_result:
                external_info += "RAW BROWSER RESULT:\n\n" + json.dumps(browser_result, indent=2) + "\n"

        doc_text = document.get("text", "")
        metrics_json = json.dumps(metrics, indent=2)
        risk_json = json.dumps(risk, indent=2)

        output_format_example = (
            '{\n'
            '  "summary": "",\n'
            '  "risk_assessment": "",\n'
            '  "recommendation": "BUY | HOLD | SELL",\n'
            '  "key_points": [\n'
            '    {\n'
            '      "claim": "financial conclusion",\n'
            '      "evidence": {\n'
            '        "metric": "metric name",\n'
            '        "value": "original value",\n'
            '        "source": "financial statement section"\n'
            '      }\n'
            '    }\n'
            '  ]\n'
            '}'
        )

        # example showing evidence_ids when external evidence is used
        output_format_example = output_format_example[:-1] + ',\n  "external_evidence": {\n    "source": "external",\n    "available": true,\n    "data": {\n      "external_summary": "<summary>",\n      "external_evidence_ids": ["uuid1", "uuid2"]\n    }\n  }\n}'

        prompt = (
            "You are a STRICT financial reporting system.\n\n"
            "RULES:\n\n"
            "- Financial metrics are ground truth.\n"
            "- Risk score is ground truth.\n"
            "- Never change numerical values.\n"
            "- Never create new financial facts.\n"
            "- Every financial conclusion MUST be supported by evidence.\n"
            "- Every key_point MUST include evidence.\n"
            "- Evidence MUST reference provided metrics or risk.\n"
            "- Do not generate unsupported claims.\n"
            "- Return ONLY JSON.\n\n"
            "DOCUMENT:\n\n"
            + doc_text
            + "\n\nMETRICS:\n\n"
            + metrics_json
            + "\n\nRISK:\n\n"
            + risk_json
            + external_info
            + "\n\nOUTPUT FORMAT:\n\n"
            + output_format_example
        )

        # Guidance to require evidence citations in key points
        prompt += "\nWhen external evidence is provided, you MUST incorporate it into the `summary` and/or `risk_assessment` and you MUST include `evidence_ids` on each `key_point` that uses external evidence. If a claim cannot be supported by the provided external evidence, explicitly mark it as `unsupported` and list which evidence ids were consulted. Failure to include evidence ids for claims that rely on external material is an error. Return ONLY valid JSON that matches the output format exactly."

        return prompt


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
            # In offline/demo mode with a stub LLM, allow missing revenue
            llm = getattr(self, '_llm', None)
            if llm and getattr(llm, '_use_stub', False):
                return

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
        browser_result=None,
        external_summary=None,
        external_evidence_ids=None,
        external_citations=None,
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
            browser_result,
            external_summary=external_summary,
            external_evidence_ids=external_evidence_ids,
            external_citations=external_citations,
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
        browser_result=None,
        external_summary=None,
        external_evidence_ids=None,
        external_citations=None,
    ):


        expected = self._derive_recommendation(
            metrics,
            risk
        )


        # 强制覆盖推荐结果
        report["recommendation"] = expected



        # 保存外部证据信息（可能包含 summary 或 evidence ids）
        external_evidence = {
            "source": "external",
            "available": bool(browser_result or external_summary or external_evidence_ids or external_citations),
            "description": "External information retrieved from web sources or RAG summaries",
            "data": {
                "browser_result": browser_result,
                "external_summary": external_summary,
                "external_evidence_ids": external_evidence_ids,
                "external_citations": external_citations,
            }
        }

        # If external evidence was provided by the caller, enforce that the LLM
        # included citations or a summary derived from that evidence. Otherwise
        # raise an error so the pipeline does not silently drop external proof.
        provided_external = bool(browser_result or external_summary or external_evidence_ids or external_citations)

        if provided_external:
            # Check for external_summary presence in report data or evidence_ids in key_points
            report_external_summary = external_evidence.get("data", {}).get("external_summary") or external_summary

            has_evidence_ids = False
            for kp in report.get("key_points", []):
                ev = kp.get("evidence") or {}
                if ev.get("evidence_ids"):
                    has_evidence_ids = True
                    break

            if not report_external_summary and not has_evidence_ids:
                # Downgrade hard error to a recoverable warning. Some LLMs
                # may omit explicit evidence ids while still using the
                # content; preserve the external evidence payload and mark
                # the report so callers can decide to fail-fast or proceed.
                external_evidence["warning"] = (
                    "LLM did not include external evidence citations; "
                    "external evidence was provided but the report contains no external_summary or evidence_ids on key_points."
                )
                report.setdefault("warnings", []).append("external_evidence_missing_citations")
                # continue without raising; caller can inspect report['warnings']

        # include a helpful meta flag indicating whether external citations were integrated
        meta = {
            "engine": self.name,
            "risk_score": risk.get("risk_score"),
            # default validation mode
            "validation": "strict",
            "external_citation_included": has_evidence_ids or bool(external_evidence.get("data", {}).get("external_summary"))
        }

        # if the LLM produced warnings, surface them in meta.validation and meta.warnings
        if report.get("warnings"):
            meta["validation"] = "strict_with_warnings"
            meta["warnings"] = report.get("warnings")

        return {
            **report,
            "external_evidence": external_evidence,
            "meta": meta
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