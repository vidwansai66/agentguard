import uuid
import json
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.scenario import Scenario, ScenarioVersion
from app.schemas.scenario import (
    ScenarioResponse,
    ScenarioCreate,
    ScenarioUpdate,
    ScenarioImportRequest,
    ScenarioImportResponse
)
from app.core.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

@router.get("", response_model=list[ScenarioResponse])
def list_scenarios(
    failure_type: str | None = Query(None),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Scenario)
    if failure_type:
        query = query.filter(Scenario.failure_type == failure_type)
    if severity:
        query = query.filter(Scenario.severity == severity)
    if category:
        query = query.filter(Scenario.category == category)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            (Scenario.name.ilike(search_fmt)) |
            (Scenario.description.ilike(search_fmt)) |
            (Scenario.failure_type.ilike(search_fmt))
        )
    scenarios = query.order_by(Scenario.created_at.asc()).all()
    return [s.to_dict() for s in scenarios]

@router.get("/export")
def export_scenarios(db: Session = Depends(get_db)):
    scenarios = db.query(Scenario).all()
    data = [s.to_dict() for s in scenarios]
    return {
        "version": "1.0",
        "exported_at": "2026-10-19T10:00:00Z",
        "scenarios": data
    }

@router.post("/import", response_model=ScenarioImportResponse)
def import_scenarios(payload: ScenarioImportRequest, db: Session = Depends(get_db)):
    imported_ids = []
    for item in payload.scenarios:
        scen_id = item.id or f"SCEN-{uuid.uuid4().hex[:8].upper()}"
        existing = db.query(Scenario).filter(Scenario.id == scen_id).first()
        if existing:
            # Update existing
            existing.name = item.name
            existing.description = item.description
            existing.category = item.category
            existing.failure_type = item.failure_type
            existing.severity = item.severity
            existing.task_input_json = json.dumps(item.task_input)
            existing.expected_outcome_json = json.dumps(item.expected_outcome)
            existing.fault_parameters_json = json.dumps(item.fault_parameters)
            existing.allowed_tools_json = json.dumps(item.allowed_tools)
            existing.policy_constraints_json = json.dumps(item.policy_constraints)
            existing.execution_limits_json = json.dumps(item.execution_limits)
            existing.expected_assertions_json = json.dumps(item.expected_assertions)
            existing.version += 1
            imported_ids.append(existing.id)
        else:
            new_scen = Scenario(
                id=scen_id,
                name=item.name,
                description=item.description,
                category=item.category,
                failure_type=item.failure_type,
                severity=item.severity,
                is_enabled=item.is_enabled,
                is_seeded=False,
                version=1,
                task_input_json=json.dumps(item.task_input),
                expected_outcome_json=json.dumps(item.expected_outcome),
                fault_parameters_json=json.dumps(item.fault_parameters),
                allowed_tools_json=json.dumps(item.allowed_tools),
                policy_constraints_json=json.dumps(item.policy_constraints),
                execution_limits_json=json.dumps(item.execution_limits),
                expected_assertions_json=json.dumps(item.expected_assertions)
            )
            db.add(new_scen)
            db.flush()
            # Version snapshot
            v = ScenarioVersion(
                id=f"ver-{new_scen.id}-v1",
                scenario_id=new_scen.id,
                version_number=1,
                snapshot_json=json.dumps(new_scen.to_dict())
            )
            db.add(v)
            imported_ids.append(new_scen.id)

    db.commit()
    return ScenarioImportResponse(imported_count=len(imported_ids), scenario_ids=imported_ids)

@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(payload: ScenarioCreate, db: Session = Depends(get_db)):
    scen_id = payload.id or f"SCEN-{uuid.uuid4().hex[:8].upper()}"
    existing = db.query(Scenario).filter(Scenario.id == scen_id).first()
    if existing:
        raise ValidationError(f"Scenario with ID '{scen_id}' already exists.")

    scen = Scenario(
        id=scen_id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        failure_type=payload.failure_type,
        severity=payload.severity,
        is_enabled=payload.is_enabled,
        is_seeded=False,
        version=1,
        task_input_json=json.dumps(payload.task_input),
        expected_outcome_json=json.dumps(payload.expected_outcome),
        fault_parameters_json=json.dumps(payload.fault_parameters),
        allowed_tools_json=json.dumps(payload.allowed_tools),
        policy_constraints_json=json.dumps(payload.policy_constraints),
        execution_limits_json=json.dumps(payload.execution_limits),
        expected_assertions_json=json.dumps(payload.expected_assertions)
    )
    db.add(scen)
    db.flush()

    v = ScenarioVersion(
        id=f"ver-{scen.id}-v1",
        scenario_id=scen.id,
        version_number=1,
        snapshot_json=json.dumps(scen.to_dict())
    )
    db.add(v)
    db.commit()
    db.refresh(scen)
    return scen.to_dict()

@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scen = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scen:
        raise NotFoundError("Scenario", scenario_id)
    return scen.to_dict()

@router.patch("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(scenario_id: str, payload: ScenarioUpdate, db: Session = Depends(get_db)):
    scen = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scen:
        raise NotFoundError("Scenario", scenario_id)

    if payload.name is not None:
        scen.name = payload.name
    if payload.description is not None:
        scen.description = payload.description
    if payload.category is not None:
        scen.category = payload.category
    if payload.failure_type is not None:
        scen.failure_type = payload.failure_type
    if payload.severity is not None:
        scen.severity = payload.severity
    if payload.is_enabled is not None:
        scen.is_enabled = payload.is_enabled
    if payload.task_input is not None:
        scen.task_input_json = json.dumps(payload.task_input)
    if payload.expected_outcome is not None:
        scen.expected_outcome_json = json.dumps(payload.expected_outcome)
    if payload.fault_parameters is not None:
        scen.fault_parameters_json = json.dumps(payload.fault_parameters)
    if payload.allowed_tools is not None:
        scen.allowed_tools_json = json.dumps(payload.allowed_tools)
    if payload.policy_constraints is not None:
        scen.policy_constraints_json = json.dumps(payload.policy_constraints)
    if payload.execution_limits is not None:
        scen.execution_limits_json = json.dumps(payload.execution_limits)
    if payload.expected_assertions is not None:
        scen.expected_assertions_json = json.dumps(payload.expected_assertions)

    scen.version += 1
    db.flush()

    # Create immutable version snapshot
    v = ScenarioVersion(
        id=f"ver-{scen.id}-v{scen.version}",
        scenario_id=scen.id,
        version_number=scen.version,
        snapshot_json=json.dumps(scen.to_dict())
    )
    db.add(v)
    db.commit()
    db.refresh(scen)
    return scen.to_dict()

@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scen = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scen:
        raise NotFoundError("Scenario", scenario_id)
    db.delete(scen)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{scenario_id}/duplicate", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def duplicate_scenario(scenario_id: str, db: Session = Depends(get_db)):
    scen = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scen:
        raise NotFoundError("Scenario", scenario_id)

    new_id = f"SCEN-COPY-{uuid.uuid4().hex[:6].upper()}"
    dup = Scenario(
        id=new_id,
        name=f"{scen.name} (Copy)",
        description=scen.description,
        category=scen.category,
        failure_type=scen.failure_type,
        severity=scen.severity,
        is_enabled=scen.is_enabled,
        is_seeded=False,
        version=1,
        task_input_json=scen.task_input_json,
        expected_outcome_json=scen.expected_outcome_json,
        fault_parameters_json=scen.fault_parameters_json,
        allowed_tools_json=scen.allowed_tools_json,
        policy_constraints_json=scen.policy_constraints_json,
        execution_limits_json=scen.execution_limits_json,
        expected_assertions_json=scen.expected_assertions_json
    )
    db.add(dup)
    db.flush()

    v = ScenarioVersion(
        id=f"ver-{dup.id}-v1",
        scenario_id=dup.id,
        version_number=1,
        snapshot_json=json.dumps(dup.to_dict())
    )
    db.add(v)
    db.commit()
    db.refresh(dup)
    return dup.to_dict()
