import asyncio
import json
import os
import tempfile
import unittest

from graph.financial_graph import create_finance_graph
from memory.manager import MemoryManager
from memory.vector_store import VectorStore
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

    def test_graph_indexes_document_chunks_in_pipeline(self):
        class _Parser:
            def invoke(self, payload):
                return {
                    "text": "Revenue was 1000. Net profit was 150. Debt ratio was 0.35.",
                    "cleaned_text": "Revenue was 1000. Net profit was 150. Debt ratio was 0.35.",
                    "table_regions": [],
                }

        class _Metric:
            def invoke(self, document):
                return {
                    "revenue": 1000.0,
                    "net_profit": 150.0,
                    "debt_ratio": 0.35,
                    "meta": {},
                }

        class _Risk:
            def invoke(self, metrics):
                return {
                    "risk_score": 0.2,
                    "risk_flags": [],
                }

        class _Report:
            def invoke(self, payload):
                return {
                    "summary": "Stable business",
                    "risk_assessment": "Low risk",
                    "recommendation": "HOLD",
                    "key_points": [],
                }

        class _Embedder:
            dim = 2

            def embed_documents(self, texts):
                return [[1.0, 0.0] for _ in texts]

            def embed(self, query):
                return [1.0, 0.0]

        memory_manager = MemoryManager(path=os.path.join(tempfile.gettempdir(), "rag_pipeline_test_memories.json"))
        embedder = _Embedder()
        vector_store = VectorStore(embedding_provider=embedder, dim=embedder.dim)
        rag_tool = __import__('tools.rag_tool', fromlist=['RAGTool']).RAGTool(memory_manager=memory_manager, vector_store=vector_store)

        graph = create_finance_graph(
            parser_tool=_Parser(),
            metric_tool=_Metric(),
            risk_tool=_Risk(),
            browser_tool=None,
            report_tool=_Report(),
            embedder=embedder,
            rag_tool=rag_tool,
        )

        result = asyncio.run(graph.ainvoke(
            {"input_file": "demo.pdf", "thread_id": "rag-pipeline-test"},
            config={"configurable": {"thread_id": "rag-pipeline-test"}},
        ))

        self.assertIn("report", result)
        self.assertGreater(len(vector_store._metadatas), 0)


if __name__ == "__main__":
    unittest.main()
