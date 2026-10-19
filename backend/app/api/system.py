from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.seed_data import seed_database
from app.models.run import TestRun, ScenarioResult
from app.models.trace import TraceEvent
from app.models.evaluation import EvaluationFinding
from app.models.diagnosis import Diagnosis
from app.models.repair import RepairProposal
from app.models.comparison import Comparison

router = APIRouter(prefix="/system", tags=["System Management"])

@router.post("/reset-demo-data")
def reset_demo_data(db: Session = Depends(get_db)):
    # Clear runs, traces, diagnoses, comparisons to reset cleanly
    db.query(Comparison).delete()
    db.query(RepairProposal).delete()
    db.query(Diagnosis).delete()
    db.query(EvaluationFinding).delete()
    db.query(TraceEvent).delete()
    db.query(ScenarioResult).delete()
    db.query(TestRun).delete()
    db.commit()

    # Re-seed baseline data
    seed_database(db)
    return {"status": "success", "message": "Demo data reset and default scenarios verified."}
