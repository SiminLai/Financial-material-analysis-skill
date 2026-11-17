import asyncio

from workflow.base_workflow import BaseWorkflow


class FinancialWorkflow(BaseWorkflow):
    def __init__(self, tools=None):
        if tools is not None:
            raise ValueError("Legacy tool injection is retired; use analyze_document or create_finance_graph")

    def _execute(self, state):
        from runtime.runtime import analyze_document
        payload = state.input_data
        path = payload.get("file_path") if isinstance(payload, dict) else payload
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            state.output = asyncio.run(analyze_document(path))
            return state
        raise RuntimeError("Use await analyze_document(...) inside an active event loop")
