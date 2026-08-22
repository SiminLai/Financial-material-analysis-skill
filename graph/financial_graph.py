try:
    from langgraph.graph import StateGraph
except Exception:
    # Lightweight fallback StateGraph for environments without langgraph
    class StateGraph:
        def __init__(self, state_cls=None):
            self._nodes = {}
            self._edges = []

        def add_node(self, name, fn):
            self._nodes[name] = fn

        def add_edge(self, a, b):
            # simple record of edges; not used by fallback executor
            self._edges.append((a, b))

        def add_conditional_edges(self, src, route_fn, mapping):
            # record conditional edges; not used in fallback
            self._edges.append((src, mapping))

        def compile(self):
            nodes = list(self._nodes.items())

            class _Graph:
                def __init__(self, nodes):
                    self._nodes = nodes

                async def ainvoke(self, init_state):
                    state = dict(init_state or {})
                    for _name, fn in self._nodes:
                        try:
                            res = fn(state)
                            if hasattr(res, '__await__'):
                                res = await res
                            state = res or state
                        except TypeError:
                            # maybe fn is async function
                            res = fn(state)
                            if hasattr(res, '__await__'):
                                res = await res
                            state = res or state
                    return state

            return _Graph(nodes)

from state.agent_state import FinanceState

from .nodes import (
    create_parser_node,
    create_metric_node,
    create_risk_node,
    create_browser_node,
    create_report_node,
    create_reflection_node,
    create_impute_node,
)

from .edges import build_edges


def create_finance_graph(
    parser_tool,
    metric_tool,
    risk_tool,
    browser_tool,
    report_tool,
    llm_provider=None,
):

    # 1. Create graph builder

    builder = StateGraph(FinanceState)


    # 2. Create core nodes

    # instantiate Evidence + RAG + Reflection components for graph-level use
    from reflection.evidence_store import EvidenceStore
    from providers.evidence_builder import EvidenceBuilder
    from reflection.feedback_summarizer import FeedbackSummarizer
    from memory.manager import MemoryManager
    from providers.embedding_provider import EmbeddingProvider
    from memory.vector_store import VectorStore
    from tools.rag_tool import RAGTool
    from reflection.reflection_engine import ReflectionEngine
    from reflection.analyzers.missing import MissingFieldsEvaluator
    from reflection.analyzers.completeness import CompletenessEvaluator
    from reflection.analyzers.consistency import ConsistencyEvaluator

    evidence_store = EvidenceStore()
    evidence_builder = EvidenceBuilder(evidence_store)

    memory_manager = MemoryManager()
    embedder = EmbeddingProvider(dim=128)
    vector_store = VectorStore(embedding_provider=embedder, dim=128)
    rag_tool_internal = RAGTool(memory_manager=memory_manager, vector_store=vector_store)

    evaluators = [MissingFieldsEvaluator(), CompletenessEvaluator(), ConsistencyEvaluator()]
    reflection_engine = ReflectionEngine(evaluators, memory_manager=memory_manager, rag_tool=rag_tool_internal, evidence_store=evidence_store)

    parser_node = create_parser_node(
        parser_tool,
        evidence_builder=evidence_builder,
    )

    metric_node = create_metric_node(
        metric_tool,
        evidence_store=evidence_store,
        evidence_builder=evidence_builder,
    )

    # impute node attempts to compute missing metrics (debt_ratio) from evidence
    impute_node = create_impute_node(evidence_store=evidence_store, evidence_builder=evidence_builder)

    risk_node = create_risk_node(
        risk_tool,
        evidence_builder=evidence_builder,
    )

    # reflection node will run RAG + reflection and attach outputs to state
    reflection_node = create_reflection_node(
        reflection_engine,
        rag_tool=rag_tool_internal,
        evidence_builder=evidence_builder,
        evidence_store=evidence_store,
        summarizer=FeedbackSummarizer(llm_provider=llm_provider) if llm_provider is not None else None,
        memory_manager=memory_manager,
    )

    report_node = create_report_node(
        report_tool,
        evidence_store=evidence_store,
        evidence_builder=evidence_builder,
    )


    # 3. Register mandatory nodes

    builder.add_node(
        "parser",
        parser_node
    )

    builder.add_node(
        "metric",
        metric_node
    )

    # add impute node after metric node
    builder.add_node(
        "impute",
        impute_node
    )

    builder.add_node(
        "risk",
        risk_node
    )

    # insert reflection node after risk evaluation
    builder.add_node(
        "reflect",
        reflection_node
    )


    # 4. Register optional browser node

    if browser_tool is not None:

        from reflection.feedback_summarizer import FeedbackSummarizer
        from memory.policy import MemoryPolicy

        browser_node = create_browser_node(
            browser_tool,
            evidence_builder=evidence_builder,
            summarizer=FeedbackSummarizer(llm_provider=llm_provider) if 'llm_provider' in locals() else None,
            memory_manager=memory_manager,
            vector_store=vector_store,
            memory_policy=MemoryPolicy(),
        )

        builder.add_node(
            "browser",
            browser_node
        )


    # 5. Register report node

    builder.add_node(
        "report",
        report_node
    )


    # 6. Build graph edges

    build_edges(
        builder,
        enable_browser=browser_tool is not None
    )

    # Register LangGraph native checkpointer (Sqlite) if available.
    # This uses builder-level registration when supported by the installed
    # LangGraph version. This is best-effort and will silently skip if the
    # runtime does not provide the expected classes / APIs.
    ckpt_path = None
    try:
        from pathlib import Path

        db_path = Path('workspace/cache/langgraph_checkpoint.sqlite')
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # attempt to import common Sqlite checkpointer classes
        saver_cls = None
        candidates = [
            ('langgraph.pregel.checkpoint', 'SqliteSaver'),
            ('langgraph.checkpoint', 'SqliteSaver'),
            ('langgraph.pregel.checkpointer', 'SqliteCheckpointer'),
            ('langgraph.checkpointer', 'SqliteCheckpointer'),
            ('langgraph.pregel.persist', 'SqliteSaver'),
            ('langgraph.persist.sqlite', 'SqliteSaver'),
        ]

        for module_path, cls_name in candidates:
            try:
                mod = __import__(module_path, fromlist=[cls_name])
                saver_cls = getattr(mod, cls_name)
                break
            except Exception:
                saver_cls = None

        if saver_cls is not None:
            saver = saver_cls(str(db_path))

            # Prefer builder-level registration APIs if available
            registered = False
            for reg in ('set_checkpointer', 'register_checkpointer', 'attach_checkpointer', 'register', 'add_checkpointer'):
                if hasattr(builder, reg):
                    try:
                        getattr(builder, reg)(saver)
                        ckpt_path = str(db_path)
                        registered = True
                        break
                    except Exception:
                        pass

            # Fallback to saver attaching methods if builder has no registration API
            if not registered:
                for method in ('attach', 'register', 'save', 'checkpoint', 'save_builder', 'save_graph'):
                    if hasattr(saver, method):
                        try:
                            getattr(saver, method)(builder)
                            ckpt_path = str(db_path)
                            registered = True
                            break
                        except Exception:
                            pass

        # if saver_cls is None or registration failed, do not raise; checkpointing is optional
    except Exception:
        ckpt_path = None


    # 7. Compile graph

    graph = builder.compile()

    # attach internal components for external access (e.g., main/debug)
    try:
        setattr(graph, 'rag_tool_internal', rag_tool_internal)
        setattr(graph, 'evidence_store', evidence_store)
        setattr(graph, 'evidence_builder', evidence_builder)
        # attach checkpoint path if saved earlier
        try:
            if 'ckpt_path' in locals() and ckpt_path:
                setattr(graph, 'langgraph_checkpoint', ckpt_path)
        except Exception:
            pass
    except Exception:
        pass

    return graph