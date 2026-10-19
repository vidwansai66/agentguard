import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.suite import TestSuite, SuiteScenario
from app.schemas.suite import SuiteResponse, SuiteCreate, SuiteUpdate
from app.core.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/suites", tags=["Test Suites"])

def _to_suite_response(suite: TestSuite) -> dict:
    scen_ids = [ss.scenario_id for ss in sorted(suite.suite_scenarios, key=lambda x: x.order)]
    return {
        "id": suite.id,
        "name": suite.name,
        "description": suite.description,
        "is_regression_suite": suite.is_regression_suite,
        "scenario_ids": scen_ids,
        "scenario_count": len(scen_ids),
        "created_at": suite.created_at,
        "updated_at": suite.updated_at
    }

@router.get("", response_model=list[SuiteResponse])
def list_suites(db: Session = Depends(get_db)):
    suites = db.query(TestSuite).all()
    return [_to_suite_response(s) for s in suites]

@router.post("", response_model=SuiteResponse, status_code=status.HTTP_201_CREATED)
def create_suite(payload: SuiteCreate, db: Session = Depends(get_db)):
    suite_id = payload.id or f"suite-{uuid.uuid4().hex[:8]}"
    existing = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if existing:
        raise ValidationError(f"Suite with ID '{suite_id}' already exists.")

    ts = TestSuite(
        id=suite_id,
        name=payload.name,
        description=payload.description,
        is_regression_suite=payload.is_regression_suite
    )
    db.add(ts)
    db.flush()

    for idx, sid in enumerate(payload.scenario_ids):
        ss = SuiteScenario(
            id=f"{ts.id}-{sid}",
            suite_id=ts.id,
            scenario_id=sid,
            order=idx
        )
        db.add(ss)

    db.commit()
    db.refresh(ts)
    return _to_suite_response(ts)

@router.get("/{suite_id}", response_model=SuiteResponse)
def get_suite(suite_id: str, db: Session = Depends(get_db)):
    ts = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not ts:
        raise NotFoundError("TestSuite", suite_id)
    return _to_suite_response(ts)

@router.patch("/{suite_id}", response_model=SuiteResponse)
def update_suite(suite_id: str, payload: SuiteUpdate, db: Session = Depends(get_db)):
    ts = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
    if not ts:
        raise NotFoundError("TestSuite", suite_id)

    if payload.name is not None:
        ts.name = payload.name
    if payload.description is not None:
        ts.description = payload.description
    if payload.is_regression_suite is not None:
        ts.is_regression_suite = payload.is_regression_suite

    if payload.scenario_ids is not None:
        db.query(SuiteScenario).filter(SuiteScenario.suite_id == suite_id).delete()
        for idx, sid in enumerate(payload.scenario_ids):
            ss = SuiteScenario(
                id=f"{ts.id}-{sid}",
                suite_id=ts.id,
                scenario_id=sid,
                order=idx
            )
            db.add(ss)

    db.commit()
    db.refresh(ts)
    return _to_suite_response(ts)
