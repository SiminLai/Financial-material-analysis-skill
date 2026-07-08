from langgraph.graph import START, END

from .router import route_after_risk


def build_edges(builder):
    """
    Register all graph edges.
    """

    # Main pipeline
    builder.add_edge(
        START,
        "parser"
    )

    builder.add_edge(
        "parser",
        "metric"
    )

    builder.add_edge(
        "metric",
        "risk"
    )


    # Risk based routing
    builder.add_conditional_edges(
        "risk",
        route_after_risk,
        {
            "browser": "browser",
            "report": "report",
        },
    )


    # Optional external evidence retrieval
    builder.add_edge(
        "browser",
        "report"
    )


    builder.add_edge(
        "report",
        END
    )