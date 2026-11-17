from typing import Any

from .base_skill import BaseSkill
from workflow.financial_workflow import FinancialWorkflow
from state.workflow_state import WorkflowState


class FinancialAnalysisSkill(BaseSkill):

    name = "financial_analysis"
    description = "Analyze financial documents including PDF parsing, metric extraction, risk analysis and report generation"

    input_schema = {
        "type": "any",
    }

    output_schema = {
        "type": "dict",
        "required_fields": ["status", "run_id", "artifact_paths"],
        "field_types": {
            "status": str,
            "run_id": str,
            "artifact_paths": dict,
        },
    }

    def __init__(self, workflow=None):
        self._workflow = workflow or FinancialWorkflow()

    def _execute(self, input_data: Any) -> Any:

        if isinstance(input_data, str):
            normalized_input = {"file_path": input_data}
        elif isinstance(input_data, dict):
            normalized_input = input_data
        else:
            raise TypeError(f"Unsupported input type: {type(input_data).__name__}")

        state = WorkflowState(input_data=normalized_input)

        state = self._workflow.invoke(state)

        return state.output
