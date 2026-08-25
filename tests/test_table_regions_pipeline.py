import json
import os
import tempfile
import unittest

from providers.pdf_provider import PDFProvider
from tools.metric_extractor_tool import MetricExtractorTool
from providers.evidence_builder import EvidenceBuilder
from reflection.evidence_store import EvidenceStore


class _StubLLMProvider:
    def _request(self, prompt: str):
        # Keep LLM output minimal so table_regions extraction is the primary source.
        return json.dumps(
            {
                "company_name": "Unknown",
                "revenue": None,
                "net_profit": None,
                "debt_ratio": None,
                "cash_flow": None,
            },
            ensure_ascii=False,
        )


class TestTableRegionsPipeline(unittest.TestCase):
    def test_table_regions_metric_and_rag_evidence_page(self):
        two_d_table = [
            ["Metric", "2025"],
            ["Revenue", "1000"],
        ]

        # 1) table_regions preserves 2D structure
        table_regions = PDFProvider._to_json_table_regions(
            [
                {
                    "page": 10,
                    "bbox": (1.0, 2.0, 3.0, 4.0),
                    "rows": two_d_table,
                }
            ]
        )
        self.assertIsInstance(table_regions[0]["rows"], list)
        self.assertIsInstance(table_regions[0]["rows"][0], list)
        self.assertEqual(table_regions[0]["rows"][1], ["Revenue", "1000"])

        # 2) metric extractor can read from table_regions with table source evidence
        extractor = MetricExtractorTool(_StubLLMProvider())
        metrics = extractor.invoke(
            {
                "text": "",
                "cleaned_text": "",
                "table_regions": table_regions,
            }
        )
        self.assertEqual(metrics.get("revenue"), 1000.0)
        source = (metrics.get("meta") or {}).get("metric_sources", {}).get("revenue", {})
        self.assertEqual(source.get("source_type"), "table")
        self.assertEqual(source.get("page"), 10)

        # 3) RAG evidence can reference table page info
        with tempfile.TemporaryDirectory() as td:
            store_path = os.path.join(td, "evidence_store.json")
            evidence_store = EvidenceStore(path=store_path)
            evidence_builder = EvidenceBuilder(evidence_store)

            rag_item = {
                "id": "table_chunk_10_1",
                "content": json.dumps(
                    {
                        "type": "table",
                        "page": 10,
                        "content": two_d_table,
                    },
                    ensure_ascii=False,
                ),
                "meta": {
                    "source": "pdf",
                    "type": "table",
                    "page": 10,
                },
            }
            ids = evidence_builder.from_rag_items([rag_item])
            stored = evidence_store.get(ids[0])
            self.assertEqual(stored.get("page"), 10)
            self.assertEqual((stored.get("meta") or {}).get("type"), "table")


if __name__ == "__main__":
    unittest.main()
