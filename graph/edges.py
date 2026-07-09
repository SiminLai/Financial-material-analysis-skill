from langgraph.graph import START, END

from .router import route_after_risk


def build_edges(builder, enable_browser: bool):

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



    if enable_browser:

        builder.add_conditional_edges(
            "risk",
            route_after_risk,
            {
                "browser": "browser",
                "report": "report",
            },
        )


        builder.add_edge(
            "browser",
            "report"
        )

    else:



        builder.add_edge(
            "risk",
            "report"
        )



    builder.add_edge(
        "report",
        END
    )