from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """
    Base class for all data providers.
    """

    name: str = ""

    def get(self, *args, **kwargs) -> Any:
        """
        Unified entry point for provider requests.
        """
        return self._request(*args, **kwargs)

    @abstractmethod
    def _request(self, *args, **kwargs) -> Any:
        """
        Perform the actual request to the external service.
        """
        raise NotImplementedError