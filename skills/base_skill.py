from abc import ABC, abstractmethod
from typing import Any

from validators import validate_payload


class BaseSkill(ABC):
    """
    Base class for all skills.
    """

    name: str = ""
    description: str = ""

    def invoke(self, input_data: Any) -> Any:
        """
        Unified entry point of a skill.
        """

        self.validate_input(input_data)

        result = self._execute(input_data)

        self.validate_output(result)

        return result

    @abstractmethod
    def _execute(self, input_data: Any) -> Any:
        """
        Core business logic of the skill.
        """
        raise NotImplementedError

    def validate_input(self, input_data: Any) -> None:
        """
        Override if necessary.
        """
        if getattr(self, "input_schema", None) is not None:
            validate_payload(input_data, self.input_schema, field_name="skill_input")

    def validate_output(self, output_data: Any) -> None:
        """
        Override if necessary.
        """
        if getattr(self, "output_schema", None) is not None:
            validate_payload(output_data, self.output_schema, field_name="skill_output")