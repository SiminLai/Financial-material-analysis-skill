from langgraph.graph import StateGraph

from state.agent_state import FinanceState

from .nodes import (
    create_parser_node,
    create_metric_node,
    create_risk_node,
    create_browser_node,
    create_report_node,
)

from .edges import build_edges


def create_finance_graph(
    parser_tool,
    metric_tool,
    risk_tool,
    browser_tool,
    report_tool,
):

    # 1. Create graph
    builder = StateGraph(FinanceState)


    # 2. Create nodes

    parser_node = create_parser_node(
        parser_tool
    )

    metric_node = create_metric_node(
        metric_tool
    )

    risk_node = create_risk_node(
        risk_tool
    )

    browser_node = create_browser_node(
        browser_tool
    )

    report_node = create_report_node(
        report_tool
    )


    # 3. Register nodes

    builder.add_node(
        "parser",
        parser_node
    )

    builder.add_node(
        "metric",
        metric_node
    )

    builder.add_node(
        "risk",
        risk_node
    )

    builder.add_node(
        "browser",
        browser_node
    )

    builder.add_node(
        "report",
        report_node
    )


    # 4. Register edges

    build_edges(builder)


    # 5. Compile

    graph = builder.compile()


    return graph