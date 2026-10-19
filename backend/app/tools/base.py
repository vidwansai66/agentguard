from abc import ABC, abstractmethod
from typing import Any

class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the tool with given parameters and return a result dictionary."""
        pass
