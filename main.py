import asyncio
import os
import json
import argparse
import sys
import uuid

from providers.llm_provider import LLMProvider
from providers.pdf_provider import PDFProvider
from providers.excel_provider import ExcelProvider


from tools.pdf_parser_tool import PDFParserTool
from tools.excel_parser_tool import ExcelParserTool
from tools.document_parser_tool import DocumentParserTool
from tools.metric_extractor_tool import MetricExtractorTool
from tools.risk_detection_tool import RiskDetectionTool
from tools.report_generator_tool import ReportGeneratorTool


from graph.financial_graph import create_finance_graph


from mcp_local.manager import MCPManager
from memory.manager import MemoryManager
from tools.rag_tool import RAGTool
from providers.embedding_provider_bge import BGEEmbeddingProvider
from memory.vector_store import VectorStore
from reflection.reflection_engine import ReflectionEngine
from reflection.analyzers.missing import MissingFieldsEvaluator
from reflection.analyzers.completeness import CompletenessEvaluator
from reflection.analyzers.consistency import ConsistencyEvaluator
from reflection.feedback_summarizer import FeedbackSummarizer


def _parse_args():
    parser = argparse.ArgumentParser(description="Financial report analysis entrypoint")
    parser.add_argument(
        "--input-file",
        dest="input_file",
        help="Path to a local PDF/XLSX file to analyze",
    )
    parser.add_argument(
        "--thread-id",
        dest="thread_id",
        help="Optional thread id for tracing/parallel runs",
    )
    return parser.parse_args()


def _resolve_input_file(cli_input_file: str = None) -> str:
    # Priority: CLI arg -> env var -> interactive prompt.
    input_file = cli_input_file or os.getenv("INPUT_FILE")
    if input_file:
        return input_file.strip()

    if sys.stdin.isatty():
        typed = input("Please enter a PDF/XLSX file path to analyze: ").strip()
        if typed:
            return typed

    raise ValueError(
        "No input file provided. Use --input-file <path>, set INPUT_FILE, or run interactively."
    )


async def _run_graph(graph, init_state):
    result = await graph.ainvoke(
        init_state,
        config={"configurable": {"thread_id": init_state["thread_id"]}},
    )

    print(result["report"])

    # print concise post-report reflection validation summary
    try:
        reflection = result.get('reflection') if isinstance(result, dict) else None
        if reflection:
            evals = reflection.get('evaluation_results') or []
            conflicts = (reflection.get('conflict_resolution') or {}).get('conflicts') or []
            overall = reflection.get('overall_score')

            print("\nReflection validation summary:")
            print(f"- overall_score: {overall}")
            print(f"- evaluator_count: {len(evals)}")
            print(f"- conflict_count: {len(conflicts)}")

            # show the first few internal feedback messages for quick diagnosis
            feedback = reflection.get('internal_feedback') or []
            for msg in feedback[:3]:
                print(f"- feedback: {msg}")
    except Exception as exc:
        print(f"Reflection summary unavailable: {type(exc).__name__}: {exc}")

    return result


async def main():

    args = _parse_args()

    mcp_manager = MCPManager(
        "config/mcp.json"
    )

    try:

        enable_tavily = (
            os.getenv("ENABLE_TAVILY", "false").lower() == "true"
        )

        tavily_key = os.getenv("TAVILY_API_KEY")

        search_tool = None

        if enable_tavily and tavily_key:
            await mcp_manager.register("tavily")
            search_tool = mcp_manager.get_tool("tavily")


        llm_provider = LLMProvider(
            model_name="deepseek-v4-flash"
        )


        pdf_provider = PDFProvider()
        excel_provider = ExcelProvider()


        pdf_tool = PDFParserTool(
            pdf_provider
        )

        excel_tool = ExcelParserTool(
            excel_provider
        )


        parser_tool = DocumentParserTool(
            pdf_tool,
            excel_tool
        )


        metric_tool = MetricExtractorTool(
            llm_provider
        )


        risk_tool = RiskDetectionTool(
            llm_provider
        )


        report_tool = ReportGeneratorTool(
            llm_provider
        )

        # instantiate simple local memory + vector store + RAG adapter
        memory_manager = MemoryManager()
        # allow selecting embedding locale via env var EMBED_LOCALE (en/zh) or explicit MODEL path
        embed_locale = os.getenv("EMBED_LOCALE", "en")
        embed_model = os.getenv("EMBED_MODEL", None)
        if embed_model:
            embedder = BGEEmbeddingProvider(model_path=embed_model, use_fp16=True)
        else:
            embedder = BGEEmbeddingProvider(locale=embed_locale, use_fp16=True)

        vector_store = VectorStore(embedding_provider=embedder, dim=embedder.dim)
        rag_tool = RAGTool(memory_manager=memory_manager, vector_store=vector_store)

        # allow thread_id configuration from CLI and env for tracing/running in parallel environments
        thread_id = args.thread_id or os.getenv("THREAD_ID") or f"thread-{uuid.uuid4().hex[:12]}"
        input_file = _resolve_input_file(args.input_file)

        init_state = {"input_file": input_file, "thread_id": thread_id}

        graph = None
        db_path = None
        try:
            from pathlib import Path
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            db_dir = Path("workspace/cache")
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / f"langgraph_checkpoint_{thread_id}.sqlite"

            async with AsyncSqliteSaver.from_conn_string(str(db_path)) as saver:
                graph = create_finance_graph(
                    parser_tool=parser_tool,
                    metric_tool=metric_tool,
                    risk_tool=risk_tool,
                    browser_tool=search_tool,
                    report_tool=report_tool,
                    llm_provider=llm_provider,
                    embedder=embedder,
                    rag_tool=rag_tool,
                    checkpointer=saver,
                )
                graph.langgraph_checkpoint = str(db_path)
                result = await _run_graph(graph, init_state)
                return result
        except Exception:
            graph = create_finance_graph(
                parser_tool=parser_tool,
                metric_tool=metric_tool,
                risk_tool=risk_tool,
                browser_tool=search_tool,
                report_tool=report_tool,
                llm_provider=llm_provider,
                embedder=embedder,
                rag_tool=rag_tool,
            )

        # If the graph saved a LangGraph checkpoint during construction, print it for debugging
        try:
            ck = getattr(graph, 'langgraph_checkpoint', None)
            if ck:
                print(f"LangGraph checkpoint written to: {ck}")
        except Exception:
            pass

        try:
            if hasattr(graph, 'langgraph_checkpoint'):
                base_dir = os.path.dirname(graph.langgraph_checkpoint) or '.'
                base_name = os.path.basename(graph.langgraph_checkpoint)
                stem, ext = os.path.splitext(base_name)
                graph.langgraph_checkpoint = os.path.join(base_dir, f"{stem}_{thread_id}{ext}")
        except Exception:
            pass

        print("\n===== RUN GRAPH PIPELINE =====")
        print(f"Input file: {init_state['input_file']}")

        result = await _run_graph(graph, init_state)

        # print RAG/external chunks used by the graph (if any)
        try:
            reflection = result.get('reflection') if isinstance(result, dict) else None
            if reflection:
                external_feedback = reflection.get('external_feedback', [])
                if external_feedback:
                    es = getattr(graph, 'evidence_store', None)
                    if es:
                        # external_feedback expected to be evidence IDs
                        ids = [e for e in external_feedback if isinstance(e, str)]
                        if ids:
                            items = es.get_many(ids)
                            print('\nGraph RAG/external evidence used:')
                            for it in items:
                                print('-', it.get('id'), it.get('source'), it.get('page'), (it.get('content') or '')[:200])
        except Exception as e:
            print('Could not retrieve graph RAG chunks:', e)

        # demo: persist a short memory of the generated report and run a retrieval
        try:
            report_text = (result.get("report") or "")
            # attach any evidence ids produced by the pipeline when saving the report
            report_eids = result.get('evidence_ids') or []
            memory_manager.add(content=report_text, type="report", metadata={"source": "pipeline", "evidence_ids": report_eids})
            # also chunk and add to vector store for semantic retrieval
            from utils.text_chunker import chunk_text

            chunks = chunk_text(report_text, chunk_size=800, overlap=100)
            docs = []
            for i, c in enumerate(chunks):
                docs.append({"id": f"report_chunk_{i}", "text": c, "meta": {"source": "report", "chunk_index": i}})
            if docs:
                vector_store.add_documents(docs)

            ctx = rag_tool.retrieve("earnings release summary", k=3)
            print("\nRAG context sample:", ctx)

            # run reflection evaluators
            evaluators = [
                MissingFieldsEvaluator(),
                CompletenessEvaluator(),
                ConsistencyEvaluator(),
            ]

            refl = ReflectionEngine(evaluators, memory_manager=memory_manager, rag_tool=rag_tool)

            # build a state from the result; try to include numeric metrics if present
            state = {"report": result.get("report")}
            if isinstance(result, dict):
                metrics = result.get("metrics") or result.get("extracted_metrics") or {}
                if isinstance(metrics, dict):
                    state.update(metrics)
                sections = result.get("sections")
                if sections:
                    state["sections"] = sections

            reflection_output = refl.reflect(state)
            print("\nReflection output:", reflection_output)

            # summarize external feedback using LLM (best-effort)
            try:
                summarizer = FeedbackSummarizer(llm_provider)
                summary = summarizer.summarize(reflection_output.get("external_feedback", []))
                print("\nExternal feedback summary:\n", summary)
                # link reflection memory to evidence ids if present
                refl_eids = []
                try:
                    ef = reflection_output.get('external_feedback') or []
                    refl_eids = [e for e in ef if isinstance(e, str)]
                except Exception:
                    refl_eids = []
                memory_manager.add(content=summary, type="reflection_summary", metadata={"evidence_ids": refl_eids})
            except Exception as e:
                print("Could not summarize external feedback:", e)
        except Exception:
            pass


    finally:

        await mcp_manager.close()


if __name__ == "__main__":

    asyncio.run(main())