from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Any

class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    run_id: str
    scenario_result_id: str
    scenario_id: str
    title: str
    likely_cause: str
    confidence: str
    explanation: str
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    relevant_trace_event_ids: list[str] = Field(default_factory=list)
    recommended_strategy: str
    recommended_patch_template_id: str | None = None
    limitations: str | None = None
    created_at: datetime | None = None

class RepairProposalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    diagnosis_id: str
    run_id: str
    template_id: str
    title: str
    proposed_change: str
    rationale: str
    expected_benefit: str
    potential_risks: str
    patch_diff: str
    target_agent_id: str
    base_version: str
    candidate_version_tag: str
    candidate_strategy: str
    candidate_config: dict[str, Any] = Field(default_factory=dict)
    approval_status: str
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    verification_status: str
    candidate_run_id: str | None = None
    comparison_id: str | None = None
    verification_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

class ApproveRepairRequest(BaseModel):
    candidate_version_tag: str | None = None
    notes: str | None = None

class RejectRepairRequest(BaseModel):
    reason: str | None = None
