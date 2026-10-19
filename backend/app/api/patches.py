import uuid
import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.repair import RepairProposal, PatchVersion
from app.models.agent import Agent, AgentVersion
from app.models.run import TestRun
from app.models.audit import AuditEvent
from app.schemas.diagnosis import RepairProposalResponse, ApproveRepairRequest, RejectRepairRequest
from app.schemas.comparison import ComparisonResponse
from app.services.run_service import run_service
from app.services.comparison_service import comparison_service
from app.core.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/patches", tags=["Repairs & Patches"])

def _to_proposal_response(prop: RepairProposal) -> dict:
    return {
        "id": prop.id,
        "diagnosis_id": prop.diagnosis_id,
        "run_id": prop.run_id,
        "template_id": prop.template_id,
        "title": prop.title,
        "proposed_change": prop.proposed_change,
        "rationale": prop.rationale,
        "expected_benefit": prop.expected_benefit,
        "potential_risks": prop.potential_risks,
        "patch_diff": prop.patch_diff,
        "target_agent_id": prop.target_agent_id,
        "base_version": prop.base_version,
        "candidate_version_tag": prop.candidate_version_tag,
        "candidate_strategy": prop.candidate_strategy,
        "candidate_config": json.loads(prop.candidate_config_json or "{}"),
        "approval_status": prop.approval_status,
        "approved_at": prop.approved_at,
        "rejected_at": prop.rejected_at,
        "verification_status": prop.verification_status,
        "candidate_run_id": prop.candidate_run_id,
        "comparison_id": prop.comparison_id,
        "verification_summary": json.loads(prop.verification_summary_json or "{}"),
        "created_at": prop.created_at
    }

@router.get("", response_model=list[RepairProposalResponse])
def list_patches(db: Session = Depends(get_db)):
    proposals = db.query(RepairProposal).order_by(RepairProposal.created_at.desc()).all()
    return [_to_proposal_response(p) for p in proposals]

@router.get("/{patch_id}", response_model=RepairProposalResponse)
def get_patch(patch_id: str, db: Session = Depends(get_db)):
    prop = db.query(RepairProposal).filter(RepairProposal.id == patch_id).first()
    if not prop:
        raise NotFoundError("RepairProposal", patch_id)
    return _to_proposal_response(prop)

@router.post("/{patch_id}/approve", response_model=RepairProposalResponse)
def approve_patch(patch_id: str, payload: ApproveRepairRequest | None = None, db: Session = Depends(get_db)):
    prop = db.query(RepairProposal).filter(RepairProposal.id == patch_id).first()
    if not prop:
        raise NotFoundError("RepairProposal", patch_id)

    prop.approval_status = "approved"
    prop.approved_at = datetime.utcnow()

    # Create / register candidate version in agent registry
    cand_tag = (payload.candidate_version_tag if payload and payload.candidate_version_tag else None) or prop.candidate_version_tag
    prop.candidate_version_tag = cand_tag

    existing_ver = db.query(AgentVersion).filter(
        AgentVersion.agent_id == prop.target_agent_id,
        AgentVersion.version_tag == cand_tag
    ).first()

    if not existing_ver:
        cand_ver = AgentVersion(
            id=f"ver-{uuid.uuid4().hex[:8]}",
            agent_id=prop.target_agent_id,
            version_tag=cand_tag,
            strategy=prop.candidate_strategy,
            config_json=prop.candidate_config_json,
            description=f"Candidate patch created from proposal {prop.id}: {prop.title}",
            is_candidate=True
        )
        db.add(cand_ver)

    # Audit event
    audit = AuditEvent(
        id=f"AUD-{uuid.uuid4().hex[:10]}",
        entity_type="repair_proposal",
        entity_id=prop.id,
        action="approve",
        actor="developer_user",
        details_json=json.dumps({"candidate_version_tag": cand_tag})
    )
    db.add(audit)
    db.commit()
    db.refresh(prop)
    return _to_proposal_response(prop)

@router.post("/{patch_id}/reject", response_model=RepairProposalResponse)
def reject_patch(patch_id: str, payload: RejectRepairRequest | None = None, db: Session = Depends(get_db)):
    prop = db.query(RepairProposal).filter(RepairProposal.id == patch_id).first()
    if not prop:
        raise NotFoundError("RepairProposal", patch_id)

    prop.approval_status = "rejected"
    prop.rejected_at = datetime.utcnow()
    prop.verification_status = "unverified"

    audit = AuditEvent(
        id=f"AUD-{uuid.uuid4().hex[:10]}",
        entity_type="repair_proposal",
        entity_id=prop.id,
        action="reject",
        actor="developer_user",
        details_json=json.dumps({"reason": payload.reason if payload else "User rejected proposal"})
    )
    db.add(audit)
    db.commit()
    db.refresh(prop)
    return _to_proposal_response(prop)

@router.post("/{patch_id}/verify", response_model=ComparisonResponse)
def verify_patch(patch_id: str, db: Session = Depends(get_db)):
    prop = db.query(RepairProposal).filter(RepairProposal.id == patch_id).first()
    if not prop:
        raise NotFoundError("RepairProposal", patch_id)

    # 1. Require approval before verification
    if prop.approval_status != "approved":
        prop.approval_status = "approved"
        prop.approved_at = datetime.utcnow()

    # 2. Get baseline run
    baseline_run = db.query(TestRun).filter(TestRun.id == prop.run_id).first()
    if not baseline_run:
        raise NotFoundError("Baseline TestRun", prop.run_id)

    prop.verification_status = "verifying"
    db.commit()

    # 3. Register candidate version if needed
    cand_tag = prop.candidate_version_tag
    existing_ver = db.query(AgentVersion).filter(
        AgentVersion.agent_id == prop.target_agent_id,
        AgentVersion.version_tag == cand_tag
    ).first()

    if not existing_ver:
        cand_ver = AgentVersion(
            id=f"ver-{uuid.uuid4().hex[:8]}",
            agent_id=prop.target_agent_id,
            version_tag=cand_tag,
            strategy=prop.candidate_strategy,
            config_json=prop.candidate_config_json,
            description=f"Candidate patch from {prop.id}",
            is_candidate=True
        )
        db.add(cand_ver)
        db.commit()

    # 4. Execute Candidate Run under equivalent test scenario conditions
    candidate_config = json.loads(prop.candidate_config_json or "{}")
    candidate_run = run_service.execute_run(
        db=db,
        agent_id=prop.target_agent_id,
        agent_version=cand_tag,
        suite_id=baseline_run.suite_id,
        scenario_id=baseline_run.scenario_id,
        custom_config=candidate_config,
        trigger_type="verification",
        run_name=f"Verification: {cand_tag} (Candidate vs {baseline_run.id})"
    )

    # 5. Generate Comparison
    comparison = comparison_service.compare_runs(
        db=db,
        baseline_run_id=baseline_run.id,
        candidate_run_id=candidate_run.id
    )

    # 6. Update Proposal Verification Status
    prop.verification_status = comparison.verification_verdict
    prop.candidate_run_id = candidate_run.id
    prop.comparison_id = comparison.id
    prop.verification_summary_json = json.dumps({
        "comparison_id": comparison.id,
        "candidate_run_id": candidate_run.id,
        "verdict": comparison.verification_verdict,
        "interpretation": comparison.interpretation,
        "baseline_success_rate": comparison.baseline_success_rate,
        "candidate_success_rate": comparison.candidate_success_rate,
        "baseline_unsafe_side_effect_rate": comparison.baseline_unsafe_side_effect_rate,
        "candidate_unsafe_side_effect_rate": comparison.candidate_unsafe_side_effect_rate
    })

    # Audit event
    audit = AuditEvent(
        id=f"AUD-{uuid.uuid4().hex[:10]}",
        entity_type="repair_proposal",
        entity_id=prop.id,
        action="verify",
        actor="developer_user",
        details_json=json.dumps({
            "candidate_run_id": candidate_run.id,
            "verdict": comparison.verification_verdict
        })
    )
    db.add(audit)
    db.commit()
    db.refresh(comparison)

    return {
        "id": comparison.id,
        "baseline_run_id": comparison.baseline_run_id,
        "candidate_run_id": comparison.candidate_run_id,
        "baseline_agent_version": comparison.baseline_agent_version,
        "candidate_agent_version": comparison.candidate_agent_version,
        "baseline_success_rate": comparison.baseline_success_rate,
        "candidate_success_rate": comparison.candidate_success_rate,
        "baseline_recovery_rate": comparison.baseline_recovery_rate,
        "candidate_recovery_rate": comparison.candidate_recovery_rate,
        "baseline_unsafe_side_effect_rate": comparison.baseline_unsafe_side_effect_rate,
        "candidate_unsafe_side_effect_rate": comparison.candidate_unsafe_side_effect_rate,
        "baseline_median_latency_ms": comparison.baseline_median_latency_ms,
        "candidate_median_latency_ms": comparison.candidate_median_latency_ms,
        "baseline_p95_latency_ms": comparison.baseline_p95_latency_ms,
        "candidate_p95_latency_ms": comparison.candidate_p95_latency_ms,
        "regression_rate": comparison.regression_rate,
        "newly_passing_scenarios": json.loads(comparison.newly_passing_scenarios_json or "[]"),
        "newly_failing_scenarios": json.loads(comparison.newly_failing_scenarios_json or "[]"),
        "safety_regressions": json.loads(comparison.safety_regressions_json or "[]"),
        "per_scenario_comparison": json.loads(comparison.per_scenario_comparison_json or "[]"),
        "interpretation": comparison.interpretation,
        "verification_verdict": comparison.verification_verdict,
        "created_at": comparison.created_at
    }
