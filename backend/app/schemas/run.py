from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Any

class RunCreate(BaseModel):
    name: str | None = None
    agent_id: str
    agent_version: str = "1.0.0"
    suite_id: str | None = None
    scenario_id: str | None = None
    custom_config: dict[str, Any] = Field(default_factory=dict)
    trigger_type: str = "manual"

class TraceEventResponse(BaseModel):
    id: str
    run_id: str
    scenario_result_id: str
    scenario_id: str
    step_index: int
    event_type: str
    severity: str
    action_name: str | None = None
    tool_name: str | None = None
    sanitized_input: dict[str, Any] = Field(default_factory=dict)
    sanitized_output: dict[str, Any] = Field(default_factory=dict)
    fault_details: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    duration_ms: float = 0.0
    error_message: str | None = None
    timestamp: datetime | None = None

class EvaluationFindingResponse(BaseModel):
    id: str
    run_id: str
    scenario_result_id: str
    scenario_id: str
    rule_id: str
    rule_name: str
    status: str
    severity: str
    message: str
    explanation: str | None = None
    trace_event_ids: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

class ScenarioResultResponse(BaseModel):
    id: str
    run_id: str
    scenario_id: str
    scenario_name: str
    scenario_version: int
    failure_type: str
    status: str
    passed: bool
    disrupted: bool
    recovered: bool
    has_unsafe_side_effect: bool
    duration_ms: float
    retry_count: int
    step_count: int
    error_message: str | None = None
    execution_output: dict[str, Any] = Field(default_factory=dict)
    findings: list[EvaluationFindingResponse] = Field(default_factory=list)
    created_at: datetime | None = None

class TestRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    agent_id: str
    agent_version: str
    suite_id: str | None = None
    scenario_id: str | None = None
    status: str
    observability_level: str = "level_3_instrumented_tools"
    trigger_type: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    unsupported_scenarios: int = 0
    unsafe_side_effects_count: int
    disrupted_count: int
    recovered_count: int
    total_duration_ms: float
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    scenario_results: list[ScenarioResultResponse] = Field(default_factory=list)
