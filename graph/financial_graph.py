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

                async def ainvoke(self, init_state, config=None):
                    state = dict(init_state or {})
                    cfg = config or {}
                    configurable = cfg.get('configurable') if isinstance(cfg, dict) else {}
                    thread_id = configurable.get('thread_id') or state.get('thread_id') or 'default'
                    state['thread_id'] = str(thread_id)
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
    create_rag_index_node,
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
    embedder=None,
    rag_tool=None,
    checkpointer=None,
):

    # 1. Create graph builder

    builder = StateGraph(FinanceState)


    # 2. Create core nodes

    # instantiate Evidence + RAG + Reflection components for graph-level use
    from reflection.evidence_store import EvidenceStore
    from providers.evidence_builder import EvidenceBuilder
    from reflection.feedback_summarizer import FeedbackSummarizer
    from memory.manager import MemoryManager
    from providers.embedding_provider_bge import BGEEmbeddingProvider
    from memory.vector_store import VectorStore
    from tools.rag_tool import RAGTool
    from reflection.reflection_engine import ReflectionEngine
    from reflection.analyzers.missing import MissingFieldsEvaluator
    from reflection.analyzers.completeness import CompletenessEvaluator
    from reflection.analyzers.consistency import ConsistencyEvaluator

    evidence_store = EvidenceStore()
    evidence_builder = EvidenceBuilder(evidence_store)

    memory_manager = MemoryManager()
    # allow caller to supply an embedder; otherwise create a default (locale-aware)
    if embedder is None:
        embedder = BGEEmbeddingProvider(locale=os.getenv("EMBED_LOCALE", "en"), use_fp16=True)

    vector_store = None
    if rag_tool is not None and getattr(rag_tool, "vector_store", None) is not None:
        vector_store = rag_tool.vector_store
    else:
        vector_store = VectorStore(embedding_provider=embedder, dim=getattr(embedder, 'dim', 128))

    if rag_tool is None:
        rag_tool_internal = RAGTool(
            memory_manager=memory_manager,
            vector_store=vector_store
        )
    else:
        rag_tool_internal = rag_tool

    evaluators = [MissingFieldsEvaluator(), CompletenessEvaluator(), ConsistencyEvaluator()]
    reflection_engine = ReflectionEngine(evaluators, memory_manager=memory_manager, rag_tool=rag_tool_internal, evidence_store=evidence_store)

    parser_node = create_parser_node(
        parser_tool,
        evidence_builder=evidence_builder,
    )

    rag_index_node = create_rag_index_node(
        vector_store=vector_store,
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
        "rag_index",
        rag_index_node
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

    # register reflection after report; this also aligns fallback executor
    # behavior (which runs nodes in registration order)
    builder.add_node(
        "reflect",
        reflection_node
    )


    # 6. Build graph edges

    build_edges(
        builder,
        enable_browser=browser_tool is not None
    )

    try:
        if checkpointer is not None:
            graph = builder.compile(checkpointer=checkpointer)
        else:
            graph = builder.compile()
    except Exception:
        graph = builder.compile()


    # attach internal components for external access (e.g., main/debug)
    try:
        setattr(graph, 'rag_tool_internal', rag_tool_internal)
        setattr(graph, 'evidence_store', evidence_store)
        setattr(graph, 'evidence_builder', evidence_builder)
    except Exception:
        pass

    return graph