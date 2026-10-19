from typing import Any
from app.agents.base import AgentAdapter
from app.agents.sample_ticket_agent import SampleTicketAgent

class AgentRegistry:
    def __init__(self):
        self._registry = {
            "agent-ticket-sample": SampleTicketAgent
        }

    def get_agent(
        self,
        agent_id: str,
        version: str = "1.0.0",
        strategy: str = "baseline",
        config: dict[str, Any] | None = None
    ) -> AgentAdapter:
        agent_cls = self._registry.get(agent_id, SampleTicketAgent)
        return agent_cls(agent_id=agent_id, version=version, strategy=strategy, config=config or {})

agent_registry = AgentRegistry()
