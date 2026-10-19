from abc import ABC, abstractmethod
from typing import Any

class AgentAdapter(ABC):
    agent_id: str
    version: str
    strategy: str

    @abstractmethod
    def run_task(
        self,
        task_input: dict[str, Any],
        context: dict[str, Any],
        tool_invoker: Any
    ) -> dict[str, Any]:
        """
        Run the agent task using the tool_invoker to interact with tools.
        Returns a dict containing agent status, outcome, decisions, and messages.
        """
        pass
