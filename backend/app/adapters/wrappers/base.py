from abc import ABC
from typing import Any
from app.adapters.base import AgentAdapter

class BaseAgentWrapper(AgentAdapter, ABC):
    """
    Abstract base contract for wrapping pre-existing AI agents
    without requiring modifications to their underlying implementation.
    """
    wrapped_target: Any
    observability_level: str
