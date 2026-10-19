from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Any

class ComparisonCreate(BaseModel):
    baseline_run_id: str
    candidate_run_id: str

class PerScenarioComparison(BaseModel):
    scenario_id: str
    scenario_name: str
    failure_type: str
    baseline_passed: bool
    candidate_passed: bool
    baseline_unsafe: bool
    candidate_unsafe: bool
    baseline_duration_ms: float
    candidate_duration_ms: float
    status_change: str # improved, regressed, unchanged_pass, unchanged_fail

class ComparisonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    baseline_run_id: str
    candidate_run_id: str
    baseline_agent_version: str
    candidate_agent_version: str
    baseline_success_rate: float
    candidate_success_rate: float
    baseline_recovery_rate: float
    candidate_recovery_rate: float
    baseline_unsafe_side_effect_rate: float
    candidate_unsafe_side_effect_rate: float
    baseline_median_latency_ms: float
    candidate_median_latency_ms: float
    baseline_p95_latency_ms: float
    candidate_p95_latency_ms: float
    regression_rate: float
    newly_passing_scenarios: list[str] = Field(default_factory=list)
    newly_failing_scenarios: list[str] = Field(default_factory=list)
    safety_regressions: list[str] = Field(default_factory=list)
    per_scenario_comparison: list[dict[str, Any]] = Field(default_factory=list)
    interpretation: str
    verification_verdict: str # verified_passed, verified_failed, trade_offs_detected
    created_at: datetime | None = None
