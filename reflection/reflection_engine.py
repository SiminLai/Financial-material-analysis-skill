class ReflectionEngine:

    def __init__(self, evaluators, memory_manager=None, rag_tool=None, evidence_store=None):
        self.evaluators = evaluators
        self.memory_manager = memory_manager
        self.rag_tool = rag_tool
        self.evidence_store = evidence_store


    def reflect(self, state, query: str = None, use_external: bool = True, external_override=None):
        """Run evaluators and produce structured reflection output.

        Returns a dict with:
          - `evaluation_results`: list of evaluator outputs
          - `internal_feedback`: list of feedback strings from evaluators
          - `overall_score`: average numeric score (0..1) or None
          - `external_feedback`: list of retrieved environment/context items (if any)
        """
        evaluation_results = []
        internal_feedback = []
        scores = []

        # run each evaluator and collect numeric/internal feedback
        for evaluator in self.evaluators:
            try:
                result = evaluator.evaluate(state)
            except Exception as e:
                result = {"name": getattr(evaluator, "name", "unknown"), "score": 0.0, "internal_feedback": f"evaluator error: {e}", "details": {}}

            evaluation_results.append(result)
            if isinstance(result, dict):
                if "internal_feedback" in result:
                    internal_feedback.append(result.get("internal_feedback"))
                if isinstance(result.get("score"), (int, float)):
                    scores.append(float(result.get("score")))

        overall_score = None
        if scores:
            overall_score = sum(scores) / len(scores)

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
            "overall_score": overall_score,
            "external_feedback": external_feedback,
            "conflict_resolution": conflict_resolution,
        }