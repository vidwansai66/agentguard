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
    supported_tools: list[str] = Field(default_factory=lambda: ["ticket_create", "ticket_query", "ticket_get"])
    config_schema: dict[str, Any] = Field(default_factory=dict)

class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    current_version: str | None = None

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None = None
    agent_type: str
    status: str
    current_version: str
    supported_tools: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    versions: list[AgentVersionResponse] = Field(default_factory=list)
