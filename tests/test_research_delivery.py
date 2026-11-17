import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.research import build_facts, finalize_research, research_report
from runtime.runtime import analyze_document
from tools.risk_detection_tool import RiskDetectionTool
from tools.metric_extractor_tool import MetricExtractorTool
from utils.metric_imputer import compute_debt_ratio_from_evidence


def fixture_state():
    values = {"revenue": 1000, "net_profit": 100, "cash_flow": 80, "debt_ratio": 0.4}
    sources = {name: {"value": value, "raw_value": str(value), "row": [name, str(value)],
                      "page": 1, "period": "2025", "scope": "consolidated", "currency": "CNY",
                      "unit": "ratio" if name == "debt_ratio" else "CNY"}
               for name, value in values.items()}
    metrics = {**values, "company_name": "Fixture", "meta": {"metric_sources": sources}}
    facts, evidence, issues = build_facts(metrics, "fixture.pdf")
    state = {"facts": facts, "evidence": evidence, "issues": issues, "metrics": metrics,
             "risk": RiskDetectionTool().invoke({"facts": facts}), "execution_mode": "production"}
    state["report"] = research_report(state)
    return state


class FakeGraph:
    async def ainvoke(self, state, config=None):
        result = fixture_state()
        result["execution_mode"] = state["execution_mode"]
        result.update(finalize_research(result))
        return result


class DeliveryTests(unittest.TestCase):
    def test_valid_fixture_passes(self):
        self.assertEqual(finalize_research(fixture_state())["status"], "succeeded")

    def test_demo_never_passes(self):
        state = fixture_state()
        state["execution_mode"] = "demo"
        self.assertEqual(finalize_research(state)["status"], "needs_review")

    def test_report_is_not_alias_of_source(self):
        state = fixture_state()
        state["report"]["facts"][0]["value"] = 999
        self.assertEqual(state["facts"][0]["value"], 1000)
        self.assertEqual(finalize_research(state)["status"], "needs_review")

    def test_required_fact_missing_blocks(self):
        state = fixture_state()
        state["facts"] = []
        state["report"] = research_report(state)
        self.assertEqual(finalize_research(state)["status"], "needs_review")

    def test_empty_and_broken_evidence_block(self):
        for references in ([], ["nonexistent"]):
            with self.subTest(references=references):
                state = fixture_state()
                state["facts"][0]["evidence_refs"] = references
                state["report"] = research_report(state)
                self.assertEqual(finalize_research(state)["status"], "needs_review")

    def test_unvalidated_fact_and_nonfinite_value_block(self):
        for changes in ({"validation_status": "needs_review"}, {"value": float("inf")}):
            state = fixture_state()
            state["facts"][0].update(changes)
            state["report"] = research_report(state)
            self.assertEqual(finalize_research(state)["status"], "needs_review")

    def test_rule_tampering_blocks(self):
        state = fixture_state()
        state["report"]["risk_assessment"]["risk_score"] = 0.99
        self.assertEqual(finalize_research(state)["status"], "needs_review")

    def test_graph_delivery_path(self):
        from graph.financial_graph import create_finance_graph
        class Parser:
            def invoke(self, payload):
                return {"text": "Synthetic fixture", "meta": {}}
        class Extractor:
            def invoke(self, document):
                return fixture_state()["metrics"]
        graph = create_finance_graph(Parser(), Extractor(), RiskDetectionTool())
        result = asyncio.run(graph.ainvoke({"input_file": "fixture.pdf", "execution_mode": "production"}))
        self.assertEqual(result["status"], "succeeded")
        self.assertIn("validation", result)
        self.assertNotIn("recommendation", result["report"])

    def test_missing_data_is_not_low_risk(self):
        risk = RiskDetectionTool().invoke({"facts": []})
        self.assertEqual(risk["risk_score"], 0)
        self.assertEqual(risk["risk_level"], "UNKNOWN")

    def test_extractor_ambiguity_and_numeric_safety(self):
        class Stub:
            def _request(self, prompt):
                return json.dumps({"company_name": "Fixture"})
        extractor = MetricExtractorTool(Stub())
        self.assertEqual(extractor._parse_numeric("(1,250)"), -1250)
        self.assertIsNone(extractor._parse_numeric("2025 report"))
        metrics = extractor.invoke({"text": "", "table_regions": [{"page": 1, "rows": [["Revenue", "100", "80"]]}]})
        self.assertIsNone(metrics["revenue"])

    def test_derivation_rejects_unknown_context(self):
        metrics = {"debt_ratio": None, "meta": {"metric_sources": {
            "total_assets": {"value": 1000}, "total_liabilities": {"value": 400}}}}
        self.assertIsNone(compute_debt_ratio_from_evidence(None, metrics)["debt_ratio"])

    def test_artifacts_and_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.pdf"
            source.write_bytes(b"fixture only; injected graph")
            root = Path(temporary) / "runs"
            result = asyncio.run(analyze_document(str(source), str(root), "test", graph_factory=lambda directory: FakeGraph()))
            self.assertEqual(result["status"], "succeeded")
            path = root / "test" / "result.json"
            original = path.read_bytes()
            again = asyncio.run(analyze_document(str(source), str(root), "test", graph_factory=lambda directory: FakeGraph()))
            self.assertEqual(again["status"], "failed")
            self.assertEqual(path.read_bytes(), original)
            invalid = asyncio.run(analyze_document(str(source), str(root), "../escape"))
            self.assertEqual(invalid["status"], "failed")

    def test_artifact_failure_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.pdf"
            source.write_bytes(b"fixture")
            with patch("runtime.runtime.write_json", side_effect=OSError("disk unavailable")):
                result = asyncio.run(analyze_document(str(source), temporary, "failure", graph_factory=lambda directory: FakeGraph()))
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["artifact_paths"], {})
            self.assertEqual(result["validation"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
