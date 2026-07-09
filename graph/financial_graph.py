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

    # 1. Create graph builder

    builder = StateGraph(FinanceState)


    # 2. Create core nodes

    parser_node = create_parser_node(
        parser_tool
    )

    metric_node = create_metric_node(
        metric_tool
    )

    risk_node = create_risk_node(
        risk_tool
    )

    report_node = create_report_node(
        report_tool
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

    builder.add_node(
        "risk",
        risk_node
    )


    # 4. Register optional browser node

    if browser_tool is not None:

        browser_node = create_browser_node(
            browser_tool
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


    # 7. Compile graph

    graph = builder.compile()


    return graph