from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Any

class AgentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    agent_id: str
    version_tag: str
    strategy: str
    config: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    is_candidate: bool = False
    created_at: datetime | None = None

class AgentCreate(BaseModel):
    id: str
    name: str
    description: str | None = None
    agent_type: str = "python_mock_agent"
    adapter_type: str = "python"
    registration_source: str = "custom"
    observability_level: str = "level_3_instrumented_tools"  # level_1_result_only, level_2_structured_events, level_3_instrumented_tools
    supported_tools: list[str] = Field(default_factory=lambda: ["ticket_create", "ticket_query", "ticket_get"])
    declared_capabilities: list[str] = Field(default_factory=list)
    adapter_config: dict[str, Any] = Field(default_factory=dict)
    config_schema: dict[str, Any] = Field(default_factory=dict)

class HttpConnectionConfig(BaseModel):
    base_url: str
    health_endpoint: str | None = "/health"
    invocation_endpoint: str = "/run"
    auth_type: str = "Bearer"  # Bearer, ApiKey-Header, Basic, None
    auth_header_name: str = "Authorization"
    secret_env_var: str | None = None
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 15.0
    allow_local_dev: bool = True
    observability_level: str = "level_1_result_only"  # level_1_result_only, level_2_structured_events, level_3_instrumented_tools
    event_format: str = "agentguard_standard"  # agentguard_standard, step_history, raw
    request_mapping: dict[str, Any] = Field(default_factory=dict)
    response_mapping: dict[str, Any] = Field(default_factory=dict)

class SdkWrapperConfig(BaseModel):
    wrapper_type: str = "callable"  # callable, class
    target_module: str | None = None  # e.g. "app.agents.existing_sample_agent"
    target_name: str | None = None    # e.g. "solve_ticket"
    observability_level: str = "level_1_result_only"
    input_parameter_name: str = "prompt"

class AgentCustomRegister(BaseModel):
    id: str
    name: str
    description: str | None = None
    adapter_type: str = "python"  # "python" or "http"
    version: str = "1.0.0"
    strategy: str = "baseline"
    observability_level: str = "level_3_instrumented_tools"
    supported_tools: list[str] = Field(default_factory=lambda: ["ticket_create", "ticket_query", "ticket_get"])
    declared_capabilities: list[str] = Field(default_factory=lambda: ["ticket_create", "ticket_query", "ticket_get"])
    adapter_config: dict[str, Any] = Field(default_factory=dict)

class ModelBackedConnectionConfig(BaseModel):
    provider: str = "openai_compatible"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    secret_env_var: str = "OPENAI_API_KEY"
    request_timeout_seconds: float = 30.0
    max_model_calls: int = 5
    max_tool_calls: int = 5
    temperature: float = 0.0
    system_prompt: str | None = None

class FrameworkConnectionConfig(BaseModel):
    framework: str = "langgraph"  # langgraph, crewai (planned), autogen (planned)
    graph_target: str = "customer_support_graph"
    max_steps: int = 10

class ExistingAgentConnectRequest(BaseModel):
    id: str
    name: str
    description: str | None = None
    connection_method: str = "http_endpoint"  # "http_endpoint", "python_sdk_wrapper", "agent_framework", "model_backed"
    observability_level: str = "level_1_result_only"  # level_1_result_only, level_2_structured_events, level_3_instrumented_tools
    version: str = "1.0.0"
    supported_tools: list[str] = Field(default_factory=list)
    declared_capabilities: list[str] = Field(default_factory=list)
    http_config: HttpConnectionConfig | None = None
    sdk_config: SdkWrapperConfig | None = None
    framework_config: FrameworkConnectionConfig | None = None
    llm_config: ModelBackedConnectionConfig | None = None



class AgentValidateConfigRequest(BaseModel):
    adapter_type: str = "python"
    adapter_config: dict[str, Any] = Field(default_factory=dict)
    observability_level: str | None = None

class AgentValidateConfigResponse(BaseModel):
    valid: bool
    error: str | None = None
    adapter_type: str
    observability_level: str = "level_3_instrumented_tools"
    details: dict[str, Any] = Field(default_factory=dict)

class AgentTestConnectionRequest(BaseModel):
    adapter_type: str | None = None
    adapter_config: dict[str, Any] | None = None

class AgentTestConnectionResponse(BaseModel):
    status: str
    message: str
    adapter_type: str
    observability_level: str = "level_3_instrumented_tools"
    declared_capabilities: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    current_version: str | None = None
    observability_level: str | None = None
    declared_capabilities: list[str] | None = None
    adapter_config: dict[str, Any] | None = None

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None = None
    agent_type: str
    adapter_type: str = "python"
    registration_source: str = "built_in"
    status: str
    observability_level: str = "level_3_instrumented_tools"
    current_version: str
    supported_tools: list[str] = Field(default_factory=list)
    declared_capabilities: list[str] = Field(default_factory=list)
    adapter_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    versions: list[AgentVersionResponse] = Field(default_factory=list)
