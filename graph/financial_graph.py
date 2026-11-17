from langgraph.graph import StateGraph

from graph.edges import build_edges
from runtime.research import build_facts, finalize_research, research_report
from state.agent_state import FinanceState
from utils.metric_imputer import compute_debt_ratio_from_evidence


def create_finance_graph(parser_tool, metric_tool, risk_tool, browser_tool=None,
                         report_tool=None, llm_provider=None, embedder=None,
                         rag_tool=None, checkpointer=None):
    builder = StateGraph(FinanceState)

    def parse(state):
        document = parser_tool.invoke({"file_path": state["input_file"]})
        error = (document.get("meta") or {}).get("error")
        if error or not (document.get("text") or document.get("table_regions")):
            raise ValueError(error or "Document has no extractable content")
        return {"document": document}

    def index(state):
        if rag_tool is None:
            return {"retrieval": {"enabled": False}}
        from graph.nodes import create_rag_index_node
        create_rag_index_node(rag_tool.vector_store)(dict(state))
        return {"retrieval": {"enabled": True}}

    def extract(state):
        return {"metrics": metric_tool.invoke(state["document"])}

    def derive(state):
        metrics = compute_debt_ratio_from_evidence(None, state["metrics"])
        facts, evidence, issues = build_facts(metrics, state["input_file"])
        issues.extend({"code": "document_parse_warning", "severity": "blocking", **warning}
                      for warning in state["document"].get("meta", {}).get("parse_warnings", []))
        return {"metrics": metrics, "facts": facts, "evidence": evidence, "issues": issues}

    def risk(state):
        return {"risk": risk_tool.invoke({"facts": state["facts"]})}

    async def browser(state):
        company = state["metrics"].get("company_name")
        if not company:
            return {"browser_result": {"status": "skipped", "reason": "company_unknown"}}
        result = await browser_tool.ainvoke({"query": str(company) + " financial disclosures"})
        return {"browser_result": {"status": "supporting_only", "data": result}}

    def report(state):
        return {"report": research_report(state)}

    for name, node in (("parser", parse), ("rag_index", index), ("metric", extract),
                       ("impute", derive), ("risk", risk), ("report", report),
                       ("reflect", finalize_research)):
        builder.add_node(name, node)
    if browser_tool is not None:
        builder.add_node("browser", browser)
    build_edges(builder, enable_browser=browser_tool is not None)
    return builder.compile(checkpointer=checkpointer)
