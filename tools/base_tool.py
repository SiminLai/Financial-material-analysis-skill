from abc import ABC, abstractmethod
from typing import Any

from validators import ValidationError, validate_payload


class BaseTool(ABC):
    """
    Base class for all tools.
    """

    name: str = ""
    description: str = ""

    input_schema = None
    output_schema = None

    def invoke(self, input_data: Any) -> Any:
        """
        Public entry of every tool.
        """

        self.validate_input(input_data)

        result = self._execute(input_data)

        self.validate_output(result)

        return result

    @abstractmethod
    def _execute(self, input_data: Any) -> Any:
        """
        Tool implementation.
        """
        pass

    def validate_input(self, input_data: Any):
        """
        Override if needed.
        """
        if getattr(self, "input_schema", None) is not None:
            validate_payload(input_data, self.input_schema, field_name="tool_input")

    def validate_output(self, output_data: Any):
        """
        Override if needed.
        """
        if getattr(self, "output_schema", None) is not None:
            validate_payload(output_data, self.output_schema, field_name="tool_output")