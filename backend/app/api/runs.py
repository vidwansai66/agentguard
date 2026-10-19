import json
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.run import TestRun, ScenarioResult
from app.models.trace import TraceEvent
from app.models.evaluation import EvaluationFinding
from app.schemas.run import TestRunResponse, RunCreate, TraceEventResponse, ScenarioResultResponse, EvaluationFindingResponse
from app.services.run_service import run_service
from app.core.errors import NotFoundError

router = APIRouter(prefix="/runs", tags=["Runs"])

def _to_scenario_result_response(res: ScenarioResult) -> dict:
    findings = [
        EvaluationFindingResponse(
            id=f.id,
            run_id=f.run_id,
            scenario_result_id=f.scenario_result_id,
            scenario_id=f.scenario_id,
            rule_id=f.rule_id,
            rule_name=f.rule_name,
            status=f.status,
            severity=f.severity,
            message=f.message,
            explanation=f.explanation,
            trace_event_ids=json.loads(f.trace_event_ids_json or "[]"),
            evidence=json.loads(f.evidence_json or "{}"),
            created_at=f.created_at
        )
        for f in res.findings
    ]
    return {
        "id": res.id,
        "run_id": res.run_id,
        "scenario_id": res.scenario_id,
        "scenario_name": res.scenario_name,
        "scenario_version": res.scenario_version,
        "failure_type": res.failure_type,
        "status": res.status,
        "passed": res.passed,
        "disrupted": res.disrupted,
        "recovered": res.recovered,
        "has_unsafe_side_effect": res.has_unsafe_side_effect,
        "duration_ms": res.duration_ms,
        "retry_count": res.retry_count,
        "step_count": res.step_count,
        "error_message": res.error_message,
        "execution_output": json.loads(res.execution_output_json or "{}"),
        "findings": findings,
        "created_at": res.created_at
    }

def _to_run_response(run: TestRun) -> dict:
    return {
        "id": run.id,
        "name": run.name,
        "agent_id": run.agent_id,
        "agent_version": run.agent_version,
        "suite_id": run.suite_id,
        "scenario_id": run.scenario_id,
        "status": run.status,
        "trigger_type": run.trigger_type,
        "total_scenarios": run.total_scenarios,
        "passed_scenarios": run.passed_scenarios,
        "failed_scenarios": run.failed_scenarios,
        "unsupported_scenarios": getattr(run, "unsupported_scenarios", 0),
        "unsafe_side_effects_count": run.unsafe_side_effects_count,
        "disrupted_count": run.disrupted_count,
        "recovered_count": run.recovered_count,
        "total_duration_ms": run.total_duration_ms,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "created_at": run.created_at,
        "scenario_results": [_to_scenario_result_response(sr) for sr in run.scenario_results]
    }

@router.get("", response_model=list[TestRunResponse])
def list_runs(
    limit: int = Query(50, ge=1, le=200),
    agent_id: str | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(TestRun)
    if agent_id:
        query = query.filter(TestRun.agent_id == agent_id)
    if status:
        query = query.filter(TestRun.status == status)
    runs = query.order_by(TestRun.created_at.desc()).limit(limit).all()
    return [_to_run_response(r) for r in runs]

@router.post("", response_model=TestRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_run(payload: RunCreate, db: Session = Depends(get_db)):
    test_run = run_service.execute_run(
        db=db,
        agent_id=payload.agent_id,
        agent_version=payload.agent_version,
        suite_id=payload.suite_id,
        scenario_id=payload.scenario_id,
        custom_config=payload.custom_config,
        trigger_type=payload.trigger_type,
        run_name=payload.name
    )
    return _to_run_response(test_run)

@router.get("/{run_id}", response_model=TestRunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise NotFoundError("TestRun", run_id)
    return _to_run_response(run)

@router.get("/{run_id}/results", response_model=list[ScenarioResultResponse])
def get_run_results(run_id: str, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise NotFoundError("TestRun", run_id)
    results = db.query(ScenarioResult).filter(ScenarioResult.run_id == run_id).all()
    return [_to_scenario_result_response(r) for r in results]

@router.get("/{run_id}/trace", response_model=list[TraceEventResponse])
def get_run_trace(
    run_id: str,
    scenario_id: str | None = Query(None),
    event_type: str | None = Query(None),
    severity: str | None = Query(None),
    db: Session = Depends(get_db)
):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise NotFoundError("TestRun", run_id)

    query = db.query(TraceEvent).filter(TraceEvent.run_id == run_id)
    if scenario_id:
        query = query.filter(TraceEvent.scenario_id == scenario_id)
    if event_type:
        query = query.filter(TraceEvent.event_type == event_type)
    if severity:
        query = query.filter(TraceEvent.severity == severity)

    events = query.order_by(TraceEvent.step_index.asc(), TraceEvent.timestamp.asc()).all()
    return [
        TraceEventResponse(
            id=e.id,
            run_id=e.run_id,
            scenario_result_id=e.scenario_result_id,
            scenario_id=e.scenario_id,
            step_index=e.step_index,
            event_type=e.event_type,
            severity=e.severity,
            action_name=e.action_name,
            tool_name=e.tool_name,
            sanitized_input=json.loads(e.sanitized_input_json or "{}"),
            sanitized_output=json.loads(e.sanitized_output_json or "{}"),
            fault_details=json.loads(e.fault_details_json or "{}"),
            retry_count=e.retry_count,
            duration_ms=e.duration_ms,
            error_message=e.error_message,
            timestamp=e.timestamp
        )
        for e in events
    ]

@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise NotFoundError("TestRun", run_id)
    if run.status == "running":
        run.status = "cancelled"
        db.commit()
    return {"id": run.id, "status": run.status, "message": "Run cancelled successfully"}
