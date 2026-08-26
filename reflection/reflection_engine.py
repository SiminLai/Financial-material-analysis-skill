class ReflectionEngine:

    def __init__(self, evaluators, memory_manager=None, rag_tool=None, evidence_store=None):
        self.evaluators = evaluators
        self.memory_manager = memory_manager
        self.rag_tool = rag_tool
        self.evidence_store = evidence_store

    def _normalize_score(self, value):
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        if score < 0.0:
            return 0.0
        if score > 1.0:
            return 1.0
        return score

    def _normalize_confidence(self, value):
        try:
            conf = float(value)
        except (TypeError, ValueError):
            return 1.0
        if conf < 0.0:
            return 0.0
        if conf > 1.0:
            return 1.0
        return conf

    def _status_from_score(self, score, threshold=0.8):
        if isinstance(score, (int, float)):
            return "PASS" if float(score) >= threshold else "FAIL"
        return "UNKNOWN"

    def _validate_output_chain(self, metrics, risk, report):
        issues = []
        financial_fields = ["revenue", "net_profit", "debt_ratio", "cash_flow", "cash_flow_ratio", "net_profit_yoy"]

        for field in financial_fields:
            metric_value = metrics.get(field) if isinstance(metrics, dict) else None
            risk_value = risk.get(field) if isinstance(risk, dict) else None
            report_value = report.get(field) if isinstance(report, dict) else None

            if metric_value is None and (risk_value is not None or report_value is not None):
                issues.append(f"{field}: metrics is None but risk/report contains value")

        return issues

    def reflect(self, state, query: str = None, use_external: bool = True, external_override=None, min_valid_evaluators: int = 2, min_confidence: float = 0.5):
        """Run evaluators and produce structured reflection output.

        Returns a dict with:
          - `evaluation_results`: list of evaluator outputs
          - `internal_feedback`: list of feedback strings from evaluators
          - `component_scores`: per-evaluator numeric scores
          - `overall_score`: always None by design to avoid forced aggregate judgments
          - `score_status`: 'component_scores_only' | 'insufficient_evidence'
          - `external_feedback`: list of retrieved environment/context items (if any)
          - `needs_review`: whether missing/conflicting evidence blocks recommendation
          - `blocking_reason`: list of human-readable blockers
        """
        evaluation_results = []
        internal_feedback = []
        component_scores = {}
        low_confidence = []
        blocking_reason = []

        # run each evaluator and collect numeric/internal feedback
        for evaluator in self.evaluators:
            try:
                result = evaluator.evaluate(state)
            except Exception as e:
                result = {"name": getattr(evaluator, "name", "unknown"), "score": 0.0, "confidence": 0.0, "internal_feedback": f"evaluator error: {e}", "details": {}}

            evaluation_results.append(result)
            if isinstance(result, dict):
                if "internal_feedback" in result:
                    internal_feedback.append(result.get("internal_feedback"))

                name = result.get("name") or "unknown"
                score = self._normalize_score(result.get("score"))
                confidence = self._normalize_confidence(result.get("confidence"))

                if score is not None:
                    component_scores[name] = score
                    if confidence < min_confidence:
                        low_confidence.append(name)

        overall_score = None
        if component_scores:
            if len(component_scores) >= min_valid_evaluators and not low_confidence:
                score_status = "component_scores_only"
            else:
                score_status = "insufficient_evidence"
        else:
            score_status = "insufficient_evidence"

        # add explicit review blockers for missing critical metrics or report contradictions
        metrics = state.get("metrics") if isinstance(state, dict) and isinstance(state.get("metrics"), dict) else (state or {})
        risk = state.get("risk") if isinstance(state, dict) else {}
        report = state.get("report") if isinstance(state, dict) else {}
        debt_ratio = metrics.get("debt_ratio")
        if debt_ratio is None:
            blocking_reason.append("missing debt_ratio")
        if isinstance(report, dict) and report.get("debt_ratio") is not None and debt_ratio is None:
            blocking_reason.append("generated metric conflicts with extraction")

        risk_flags = risk.get("risk_flags", []) if isinstance(risk, dict) else []
        if debt_ratio is None and (
            any("HIGH_LEVERAGE" in str(flag).upper() for flag in risk_flags)
            or any("ELEVATED_LEVERAGE" in str(flag).upper() for flag in risk_flags)
            or any("debt_ratio" in str(flag).lower() for flag in risk_flags)
            or (isinstance(report, dict) and report.get("debt_ratio") is not None)
        ):
            blocking_reason.append("cross-layer inconsistency: metrics.debt_ratio is None while risk/report referenced debt_ratio")

        output_issues = self._validate_output_chain(metrics, risk, report)
        for issue in output_issues:
            blocking_reason.append(issue)

        completeness_status = "PASS"
        consistency_status = "PASS"
        for evaluator in self.evaluators:
            try:
                result = evaluator.evaluate(state)
            except Exception:
                continue
            if isinstance(result, dict) and result.get("name") == "completeness":
                completeness_status = self._status_from_score(result.get("score"), threshold=0.8)
            if isinstance(result, dict) and result.get("name") == "consistency":
                consistency_status = self._status_from_score(result.get("score"), threshold=0.8)

        if completeness_status == "FAIL":
            blocking_reason.append("completeness check failed")
        if consistency_status == "FAIL":
            blocking_reason.append("consistency check failed")

        if blocking_reason:
            needs_review = True
            consistency = "FAIL"
        else:
            needs_review = False
            consistency = "PASS"

        completeness = completeness_status
        if completeness == "FAIL":
            needs_review = True

        external_feedback = []
        if external_override is not None:
            external_feedback = external_override
        else:
            if use_external and self.rag_tool:
                # build a retrieval query: prefer explicit query, else join internal feedback
                q = query or " ".join([s for s in internal_feedback if s])
                if q:
                    try:
                        external_feedback = self.rag_tool.retrieve(q, k=5)
                    except Exception:
                        external_feedback = []

        # conflict resolution between state metrics and external evidence
        conflict_resolution = None
        try:
            if external_feedback:
                from reflection.conflict_resolver import resolve_conflicts

                conflict_resolution = resolve_conflicts(state, external_feedback, evidence_store=self.evidence_store)
        except Exception:
            conflict_resolution = None

        return {
            "evaluation_results": evaluation_results,
            "internal_feedback": internal_feedback,
            "component_scores": component_scores,
            "overall_score": overall_score,
            "score_status": score_status,
            "low_confidence_evaluators": low_confidence,
            "external_feedback": external_feedback,
            "conflict_resolution": conflict_resolution,
            "needs_review": needs_review,
            "blocking_reason": blocking_reason,
            "consistency": consistency,
            "completeness": completeness,
        }