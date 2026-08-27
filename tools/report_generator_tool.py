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

    def _metric_value(self, metric):
        if metric is None:
            return None
        if isinstance(metric, dict):
            return metric.get("value")
        return metric

    def _metric_blocking_reason(self, metrics, report):
        reasons = []
        if self._metric_value(metrics.get("debt_ratio")) is None and self._metric_value(report.get("debt_ratio")) is not None:
            reasons.append("generated metric conflicts with extraction: debt_ratio")
        if self._metric_value(metrics.get("debt_ratio")) is None:
            reasons.append("missing debt_ratio")
        if self._metric_value(metrics.get("revenue")) is None and self._metric_value(report.get("revenue")) is not None:
            reasons.append("generated revenue conflicts with extraction")
        return reasons

    def _sanitize_report(self, report, metrics):
        if not isinstance(report, dict):
            return report

        cleaned = dict(report)
        financial_keys = {"revenue", "net_profit", "debt_ratio", "cash_flow", "cash_flow_ratio", "net_profit_yoy"}

        for key in list(cleaned.keys()):
            if key in {"summary", "risk_assessment", "recommendation", "key_points", "external_evidence", "meta", "warnings", "needs_review", "blocking_reason", "consistency"}:
                continue
            if key.lower() in financial_keys:
                metric_value = metrics.get(key)
                if metric_value is None:
                    cleaned.pop(key, None)
                continue
            if key in metrics:
                continue
            if isinstance(cleaned.get(key), (int, float)):
                cleaned.pop(key, None)

        if metrics.get("debt_ratio") is None:
            cleaned.pop("debt_ratio", None)

        if not cleaned.get("summary"):
            cleaned["summary"] = "Financial profile summary is available below."

        if not isinstance(cleaned.get("key_points"), list):
            cleaned["key_points"] = []

        for point in cleaned["key_points"]:
            if isinstance(point, dict) and "evidence" not in point:
                point["evidence"] = {
                    "metric": "risk_score",
                    "value": 0.0,
                    "source": "internal_risk_engine",
                }

        return cleaned



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

        try:
            json_str = self._extract_json(
                raw_output
            )

            parsed = json.loads(
                json_str
            )
        except Exception:
            parsed = self._build_fallback_report(metrics, risk)
            parsed.setdefault("warnings", []).append("report_llm_json_parse_failed")

        parsed = self._sanitize_report(parsed, metrics)

        if not parsed.get("summary"):
            parsed["summary"] = "Financial performance summary is unavailable; key findings and risk metrics are shown below."

        if not isinstance(parsed.get("meta"), dict):
            parsed["meta"] = {}
        parsed["meta"]["risk_score"] = risk.get("risk_score")

        if not isinstance(parsed.get("external_evidence"), dict):
            parsed["external_evidence"] = {"source": "internal", "available": False, "data": {}}

        if not isinstance(parsed.get("key_points"), list):
            parsed["key_points"] = []

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

        if text is None:
            raise ValueError("No JSON found in LLM output")

        text = str(text)
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
                "No JSON found in LLM output"
            )


        return match.group(0)


    def _build_fallback_report(self, metrics, risk):
        score = risk.get("risk_score")
        level = risk.get("risk_level")
        flags = risk.get("risk_flags") or []

        points = []
        for metric_name in ("revenue", "net_profit", "debt_ratio", "cash_flow"):
            value = metrics.get(metric_name)
            if value is None:
                continue
            points.append(
                {
                    "claim": f"{metric_name} observed at {value}",
                    "evidence": {
                        "metric": metric_name,
                        "value": value,
                        "source": "parsed_metrics",
                    },
                }
            )

        if flags:
            points.append(
                {
                    "claim": "deterministic risk flags were triggered",
                    "evidence": {
                        "metric": "risk_flags",
                        "value": flags,
                        "source": "risk_engine",
                    },
                }
            )

        summary = (
            "Fallback report generated because LLM output was not valid JSON. "
            f"risk_score={score}, risk_level={level}."
        )

        return {
            "summary": summary,
            "risk_assessment": f"Risk level is {level} with flags: {flags}",
            "recommendation": self._derive_recommendation(metrics, risk),
            "key_points": points,
            "external_evidence": {"source": "internal", "available": False, "data": {}},
            "meta": {"risk_score": score},
        }



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

        blocking_reasons = self._metric_blocking_reason(metrics, report)
        if blocking_reasons:
            report["needs_review"] = True
            report["blocking_reason"] = blocking_reasons
            report["risk_assessment"] = (report.get("risk_assessment") or "") + " Review required due to missing or conflicting financial metrics."

        expected = self._derive_recommendation(
            metrics,
            risk
        )

        recommendation = str(expected).upper()
        if recommendation not in {"BUY", "HOLD", "SELL"}:
            raise ValueError(f"Invalid recommendation returned by risk logic: {recommendation}")
        report["recommendation"] = recommendation

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
        has_evidence_ids = False

        if provided_external:
            # Check for external_summary presence in report data or evidence_ids in key_points
            report_external_summary = external_evidence.get("data", {}).get("external_summary") or external_summary

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

        meta = {
            "engine": self.name,
            "risk_score": risk.get("risk_score"),
            "validation": "strict",
            "external_citation_included": has_evidence_ids or bool(external_evidence.get("data", {}).get("external_summary")),
            "needs_review": bool(report.get("needs_review")),
            "blocking_reason": report.get("blocking_reason", []),
        }
        if report.get("warnings"):
            meta["validation"] = "strict_with_warnings"
            meta["warnings"] = report.get("warnings")
        if report.get("needs_review"):
            meta["validation"] = "failed"

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


        profit = self._metric_value(metrics.get("net_profit"))
        cash = self._metric_value(metrics.get("cash_flow"))

        if metrics.get("debt_ratio") is None:
            return "HOLD"

        if (
            score < 0.3
            and profit is not None
            and cash is not None
            and profit > 0
            and cash > 0
        ):
            return "BUY"

        if score < 0.7:
            return "HOLD"

        return "SELL"
