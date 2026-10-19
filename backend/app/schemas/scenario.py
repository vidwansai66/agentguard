from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Any

class ScenarioBase(BaseModel):
    name: str
    description: str | None = None
    category: str = "ticketing"
    failure_type: str = "transient_timeout" # transient_timeout, ambiguous_outcome, malformed_output, repeated_action, prompt_injection, policy_violation, normal_execution
    severity: str = "medium" # low, medium, high, critical
    is_enabled: bool = True
    task_input: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: dict[str, Any] = Field(default_factory=dict)
    fault_parameters: dict[str, Any] = Field(default_factory=dict)
    allowed_tools: list[str] = Field(default_factory=list)
    policy_constraints: dict[str, Any] = Field(default_factory=dict)
    execution_limits: dict[str, Any] = Field(default_factory=dict)
    expected_assertions: list[str] = Field(default_factory=list)

class ScenarioCreate(ScenarioBase):
    id: str | None = None

class ScenarioUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    failure_type: str | None = None
    severity: str | None = None
    is_enabled: bool | None = None
    task_input: dict[str, Any] | None = None
    expected_outcome: dict[str, Any] | None = None
    fault_parameters: dict[str, Any] | None = None
    allowed_tools: list[str] | None = None
    policy_constraints: dict[str, Any] | None = None
    execution_limits: dict[str, Any] | None = None
    expected_assertions: list[str] | None = None

class ScenarioResponse(ScenarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    is_seeded: bool = False
    version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ScenarioImportRequest(BaseModel):
    scenarios: list[ScenarioCreate]

class ScenarioImportResponse(BaseModel):
    imported_count: int
    scenario_ids: list[str]
