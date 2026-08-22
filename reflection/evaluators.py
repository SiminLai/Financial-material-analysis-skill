from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseEvaluator(ABC):
    """Base evaluator interface for reflection evaluators.

    Implementations should return a dict with at least:
      - `name`: evaluator name
      - `score`: float between 0 and 1 (higher is better)
      - `internal_feedback`: short human-readable feedback string
      - optional `details`: any extra data
    """

    name: str = "base"

    @abstractmethod
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError()
