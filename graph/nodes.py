"""
Node factory functions for LangGraph.
Each node:
1. Read data from State
2. Invoke Tool
3. Write result back to State
"""

def create_parser_node(parser_tool):

    def parser_node(state):

        file_path = state.get("input_file")
        if file_path is None:
            raise ValueError("state is missing required key: 'input_file'")

        document = parser_tool.invoke({
            "file_path": file_path
        })

        state["document"] = document

        return state

    return parser_node


def create_metric_node(metric_tool):

    def metric_node(state):

        document = state.get("document")
        if document is None:
            raise ValueError("state is missing required key: 'document'")

        metrics = metric_tool.invoke(document)

        state["metrics"] = metrics

        return state

    return metric_node


def create_risk_node(risk_tool):

    def risk_node(state):

        metrics = state.get("metrics")
        if metrics is None:
            raise ValueError("state is missing required key: 'metrics'")

        risk = risk_tool.invoke(metrics)

        state["risk"] = risk

        return state

    return risk_node


# def create_browser_node(browser_tool):

#     async def browser_node(state):

#         risk = state.get("risk")
#         metrics = state.get("metrics")

#         if risk is None:
#             raise ValueError("state is missing required key: 'risk'")

#         if metrics is None:
#             raise ValueError("state is missing required key: 'metrics'")

#         # 可以根据自己的业务改 Prompt
#         query = (
#             f"Search latest financial risks and news about "
#             f"{metrics.get('company_name', '')}. "
#             f"Current risk score: {risk.get('risk_score', '')}"
#         )

#         browser_result = await browser_tool.ainvoke({
#             "query": query
#         })

#         state["browser_result"] = browser_result

#         return state

#     return browser_node
def create_browser_node(browser_tool):

    async def browser_node(state):

        risk = state.get("risk")
        metrics = state.get("metrics")

        if risk is None:
            raise ValueError(
                "state is missing required key: 'risk'"
            )

        if metrics is None:
            raise ValueError(
                "state is missing required key: 'metrics'"
            )


        # =========================
        # Build company-focused query
        # =========================

        company = (
            metrics.get("company_name")
            or state.get("document", {})
            .get("company_name")
            or ""
        )


        risk_flags = risk.get(
            "risk_flags",
            []
        )


        risk_reason = " ".join(
            risk_flags
        )


        query = f"""
{company}

latest earnings report
financial outlook
profitability risk
cash flow risk
debt risk

Risk factors:
{risk_reason}

Risk score:
{risk.get("risk_score")}
"""


        browser_result = await browser_tool.ainvoke(
            {
                "query": query
            }
        )


        state["browser_result"] = browser_result


        return state


    return browser_node

def create_report_node(report_tool):

    def report_node(state):

        document = state.get("document")
        metrics = state.get("metrics")
        risk = state.get("risk")

        if document is None:
            raise ValueError("state is missing required key: 'document'")

        if metrics is None:
            raise ValueError("state is missing required key: 'metrics'")

        if risk is None:
            raise ValueError("state is missing required key: 'risk'")

        tool_input = {
            "document": document,
            "metrics": metrics,
            "risk": risk,
        }

        browser_result = state.get("browser_result")

        if browser_result:
            tool_input["browser_result"] = browser_result

        report = report_tool.invoke(tool_input)

        state["report"] = report

        return state

    return report_node