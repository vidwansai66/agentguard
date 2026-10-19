from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class AgentExecutionContext(BaseModel):
    model_config = ConfigDict(extra="ignore")
    run_id: str
    agent_id: str
    agent_version: str
    scenario_id: str
    trace_correlation_id: str
    step_timeout_seconds: float = 30.0
    max_steps: int = 20

class AgentTaskInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: str = "create_ticket"
    title: str = "Support Inquiry"
    description: str = ""
    priority: str = "medium"
    metadata: dict[str, Any] = Field(default_factory=dict)

class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tool_name: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    retry_count: int = 0

class ToolCallResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    invocation_id: str
    tool_name: str
    action: str
    status: str  # "success" or "error"
    data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    error_category: str | None = None
    injected_fault: str | None = None
    retry_count: int = 0
    duration_ms: float = 0.0
    sanitized_output: dict[str, Any] = Field(default_factory=dict)

class AgentTaskResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str  # "success", "failed", "error", "unsupported"
    ticket_id: str | None = None
    message: str = ""
    disrupted: bool = False
    recovered: bool = False
    retries_used: int = 0
    unsupported_capabilities: list[str] = Field(default_factory=list)
    execution_events: list[dict[str, Any]] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
