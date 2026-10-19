import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.run import TestRun, ScenarioResult
from app.models.trace import TraceEvent
from app.models.evaluation import EvaluationFinding
from app.models.comparison import Comparison
from app.schemas.comparison import ComparisonResponse, ComparisonCreate
from app.services.comparison_service import comparison_service
from app.core.errors import NotFoundError

router = APIRouter(tags=["Comparisons & Reporting"])

def _to_comparison_response(comp: Comparison) -> dict:
    return {
        "id": comp.id,
        "baseline_run_id": comp.baseline_run_id,
        "candidate_run_id": comp.candidate_run_id,
        "baseline_agent_version": comp.baseline_agent_version,
        "candidate_agent_version": comp.candidate_agent_version,
        "baseline_success_rate": comp.baseline_success_rate,
        "candidate_success_rate": comp.candidate_success_rate,
        "baseline_recovery_rate": comp.baseline_recovery_rate,
        "candidate_recovery_rate": comp.candidate_recovery_rate,
        "baseline_unsafe_side_effect_rate": comp.baseline_unsafe_side_effect_rate,
        "candidate_unsafe_side_effect_rate": comp.candidate_unsafe_side_effect_rate,
        "baseline_median_latency_ms": comp.baseline_median_latency_ms,
        "candidate_median_latency_ms": comp.candidate_median_latency_ms,
        "baseline_p95_latency_ms": comp.baseline_p95_latency_ms,
        "candidate_p95_latency_ms": comp.candidate_p95_latency_ms,
        "regression_rate": comp.regression_rate,
        "newly_passing_scenarios": json.loads(comp.newly_passing_scenarios_json or "[]"),
        "newly_failing_scenarios": json.loads(comp.newly_failing_scenarios_json or "[]"),
        "safety_regressions": json.loads(comp.safety_regressions_json or "[]"),
        "per_scenario_comparison": json.loads(comp.per_scenario_comparison_json or "[]"),
        "interpretation": comp.interpretation,
        "verification_verdict": comp.verification_verdict,
        "created_at": comp.created_at
    }

@router.post("/comparisons", response_model=ComparisonResponse)
def create_comparison(payload: ComparisonCreate, db: Session = Depends(get_db)):
    comp = comparison_service.compare_runs(db, payload.baseline_run_id, payload.candidate_run_id)
    return _to_comparison_response(comp)

@router.get("/comparisons/{comparison_id}", response_model=ComparisonResponse)
def get_comparison(comparison_id: str, db: Session = Depends(get_db)):
    comp = db.query(Comparison).filter(Comparison.id == comparison_id).first()
    if not comp:
        raise NotFoundError("Comparison", comparison_id)
    return _to_comparison_response(comp)

@router.get("/runs/{run_id}/export")
def export_run_results(run_id: str, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise NotFoundError("TestRun", run_id)

    results = db.query(ScenarioResult).filter(ScenarioResult.run_id == run_id).all()
    traces = db.query(TraceEvent).filter(TraceEvent.run_id == run_id).all()
    findings = db.query(EvaluationFinding).filter(EvaluationFinding.run_id == run_id).all()

    return {
        "run": {
            "id": run.id,
            "name": run.name,
            "agent_id": run.agent_id,
            "agent_version": run.agent_version,
            "status": run.status,
            "total_scenarios": run.total_scenarios,
            "passed_scenarios": run.passed_scenarios,
            "failed_scenarios": run.failed_scenarios,
            "unsafe_side_effects_count": run.unsafe_side_effects_count,
            "total_duration_ms": run.total_duration_ms,
            "created_at": run.created_at.isoformat() if run.created_at else None
        },
        "scenario_results": [
            {
                "id": r.id,
                "scenario_id": r.scenario_id,
                "scenario_name": r.scenario_name,
                "status": r.status,
                "passed": r.passed,
                "disrupted": r.disrupted,
                "recovered": r.recovered,
                "has_unsafe_side_effect": r.has_unsafe_side_effect,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message
            }
            for r in results
        ],
        "findings": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "status": f.status,
                "severity": f.severity,
                "message": f.message
            }
            for f in findings
        ],
        "trace_events_count": len(traces)
    }
