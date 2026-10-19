from abc import ABC, abstractmethod
from typing import Any
from app.adapters.models import AgentTaskInput, AgentExecutionContext, AgentTaskResult

class AgentAdapter(ABC):
    """
    Stable Agent Adapter Contract for AgentGuard.
    All custom agents (Python modules or HTTP microservices) must satisfy this interface.
    """
    agent_id: str
    version: str
    adapter_type: str = "python"  # "python" or "http"
    declared_capabilities: list[str] = []
    supported_tools: list[str] = ["ticket_create", "ticket_query", "ticket_get"]
    config: dict[str, Any] = {}

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Validate adapter configuration schema and security rules."""
        return {"valid": True, "error": None}

    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize agent instance from validated configuration."""
        pass

    @abstractmethod
    def run_task(
        self,
        task_input: AgentTaskInput | dict[str, Any],
        context: AgentExecutionContext | dict[str, Any],
        tool_invoker: Any
    ) -> AgentTaskResult | dict[str, Any]:
        """
        Execute task using tool_invoker to interact with approved tools.
        Returns structured AgentTaskResult.
        """
        pass

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """Verify configuration, connectivity, and declared capabilities."""
        pass

    def stream_events(self) -> list[dict[str, Any]] | None:
        """Return structured execution events when event streaming or buffering is supported."""
        return None

    def cancel(self) -> None:
        """Signal execution cancellation where technically possible."""
        pass

    def dispose(self) -> None:
        """Dispose of resources and clean up connection pools."""
        pass

