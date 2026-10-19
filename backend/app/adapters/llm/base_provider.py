from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class LlmMessage(BaseModel):
    role: str  # system, user, assistant, tool
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class LlmResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    finish_reason: str = "stop"  # stop, tool_calls, length, content_filter
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    raw_response: Dict[str, Any] = Field(default_factory=dict)

class BaseLlmProvider(ABC):
    """Abstract base provider for LLM API integrations."""

    @abstractmethod
    def chat_complete(
        self,
        messages: List[LlmMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 30.0
    ) -> LlmResponse:
        """Execute chat completion request."""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test API reachability and credentials."""
        pass
