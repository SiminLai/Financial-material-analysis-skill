from .base_workflow import BaseWorkflow


class FinancialWorkflow(BaseWorkflow):

    input_schema = {
        "type": "any",
    }

    output_schema = {
        "type": "any",
    }

    def __init__(self, tools):
        self._tools = tools
        self.parser_tool = tools["parser"]
        self.metric_tool = tools["metric"]
        self.risk_tool = tools["risk"]
        self.report_tool = tools["report"]

    def _execute(self, state):

        # Step 1: parse PDF → document
        state.document = self.parser_tool.invoke(state.input_data)

        # Step 2: extract metrics → metrics
        state.metrics = self.metric_tool.invoke(state.document)

        # Step 3: risk analysis → risk
        state.risk = self.risk_tool.invoke(state.metrics)

        # Step 4: generate report → output
        state.output = self.report_tool.invoke({
            "document": state.document,
            "metrics": state.metrics,
            "risk": state.risk
        })

        return state