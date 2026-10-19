import uuid
import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.run import TestRun, ScenarioResult
from app.models.trace import TraceEvent
from app.models.evaluation import EvaluationFinding
from app.models.diagnosis import Diagnosis
from app.models.repair import RepairProposal
from app.schemas.diagnosis import DiagnosisResponse
from app.diagnosis.engine import DiagnosisEngine
from app.repairs.proposer import repair_proposer
from app.core.errors import NotFoundError

router = APIRouter(prefix="/runs", tags=["Diagnoses"])
diagnosis_engine = DiagnosisEngine()

def _to_diagnosis_response(diag: Diagnosis) -> dict:
    return {
        "id": diag.id,
        "run_id": diag.run_id,
        "scenario_result_id": diag.scenario_result_id,
        "scenario_id": diag.scenario_id,
        "title": diag.title,
        "likely_cause": diag.likely_cause,
        "confidence": diag.confidence,
        "explanation": diag.explanation,
        "supporting_evidence": json.loads(diag.supporting_evidence_json or "{}"),
        "relevant_trace_event_ids": json.loads(diag.relevant_trace_event_ids_json or "[]"),
        "recommended_strategy": diag.recommended_strategy,
        "recommended_patch_template_id": diag.recommended_patch_template_id,
        "limitations": diag.limitations,
        "created_at": diag.created_at
    }

@router.post("/{run_id}/diagnose", response_model=list[DiagnosisResponse])
def generate_diagnoses(run_id: str, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise NotFoundError("TestRun", run_id)

    # Clean existing diagnoses for this run to keep idempotent
    existing_diagnoses = db.query(Diagnosis).filter(Diagnosis.run_id == run_id).all()
    for d in existing_diagnoses:
        db.delete(d)
    db.flush()

    results = db.query(ScenarioResult).filter(ScenarioResult.run_id == run_id).all()
    created_diagnoses = []

    for res in results:
        findings = db.query(EvaluationFinding).filter(EvaluationFinding.scenario_result_id == res.id).all()
        traces = db.query(TraceEvent).filter(TraceEvent.scenario_result_id == res.id).all()

        findings_dicts = [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "status": f.status,
                "severity": f.severity,
                "message": f.message,
                "trace_event_ids": json.loads(f.trace_event_ids_json or "[]"),
                "evidence": json.loads(f.evidence_json or "{}")
            }
            for f in findings
        ]
        trace_dicts = [
            {
                "id": t.id,
                "step_index": t.step_index,
                "event_type": t.event_type,
                "action_name": t.action_name,
                "sanitized_input": json.loads(t.sanitized_input_json or "{}"),
                "sanitized_output": json.loads(t.sanitized_output_json or "{}")
            }
            for t in traces
        ]

        res_dict = {
            "failure_type": res.failure_type,
            "has_unsafe_side_effect": res.has_unsafe_side_effect,
            "error_message": res.error_message,
            "retry_count": res.retry_count
        }

        diag_results = diagnosis_engine.diagnose_scenario_result(res_dict, findings_dicts, trace_dicts)

        for dr in diag_results:
            diag_id = f"DIAG-{uuid.uuid4().hex[:10]}"
            diag_model = Diagnosis(
                id=diag_id,
                run_id=run_id,
                scenario_result_id=res.id,
                scenario_id=res.scenario_id,
                title=dr.title,
                likely_cause=dr.likely_cause,
                confidence=dr.confidence,
                explanation=dr.explanation,
                supporting_evidence_json=json.dumps(dr.supporting_evidence),
                relevant_trace_event_ids_json=json.dumps(dr.relevant_trace_event_ids),
                recommended_strategy=dr.recommended_strategy,
                recommended_patch_template_id=dr.recommended_patch_template_id,
                limitations=dr.limitations
            )
            db.add(diag_model)
            db.flush()

            # Automatically create a candidate repair proposal for this diagnosis
            prop_data = repair_proposer.create_proposal_for_diagnosis(
                diagnosis_id=diag_id,
                run_id=run_id,
                target_agent_id=run.agent_id,
                base_version=run.agent_version,
                template_id=dr.recommended_patch_template_id
            )
            repair_model = RepairProposal(
                id=prop_data["id"],
                diagnosis_id=diag_id,
                run_id=run_id,
                template_id=prop_data["template_id"],
                title=prop_data["title"],
                proposed_change=prop_data["proposed_change"],
                rationale=prop_data["rationale"],
                expected_benefit=prop_data["expected_benefit"],
                potential_risks=prop_data["potential_risks"],
                patch_diff=prop_data["patch_diff"],
                target_agent_id=prop_data["target_agent_id"],
                base_version=prop_data["base_version"],
                candidate_version_tag=prop_data["candidate_version_tag"],
                candidate_strategy=prop_data["candidate_strategy"],
                candidate_config_json=json.dumps(prop_data["candidate_config"]),
                approval_status="pending",
                verification_status="unverified"
            )
            db.add(repair_model)

            created_diagnoses.append(diag_model)

    db.commit()
    return [_to_diagnosis_response(d) for d in created_diagnoses]

@router.get("/{run_id}/diagnoses", response_model=list[DiagnosisResponse])
def get_diagnoses(run_id: str, db: Session = Depends(get_db)):
    diagnoses = db.query(Diagnosis).filter(Diagnosis.run_id == run_id).all()
    return [_to_diagnosis_response(d) for d in diagnoses]
