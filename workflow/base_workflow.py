from abc import ABC, abstractmethod
from typing import Any

from validators import validate_payload


class BaseWorkflow(ABC):
    """
    Base class for all workflows.
    """

    def invoke(self, state: Any) -> Any:
        """
        Unified execution entry.
        """

        self.validate_input(state)

        state = self._execute(state)

        self.validate_output(state)

        return state

    @abstractmethod
    def _execute(self, state: Any) -> Any:
        """
        Core workflow logic.
        """
        raise NotImplementedError

    def validate_input(self, state: Any) -> None:
        """
        Override if necessary.
        """
        if getattr(self, "input_schema", None) is not None:
            validate_payload(state, self.input_schema, field_name="workflow_input")

    def validate_output(self, state: Any) -> None:
        """
        Override if necessary.
        """
        if getattr(self, "output_schema", None) is not None:
            validate_payload(state, self.output_schema, field_name="workflow_output")