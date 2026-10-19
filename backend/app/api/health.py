from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.agent import Agent
from app.models.scenario import Scenario
from app.models.run import TestRun
from app.schemas.stats import DashboardStatsResponse, SystemStatusResponse
from app.services.metrics_service import metrics_service
import time

router = APIRouter(tags=["Health & System"])
start_time = time.time()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AgentGuard API",
        "version": "1.0.0",
        "timestamp": time.time()
    }

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    return metrics_service.get_dashboard_metrics(db)

@router.get("/system/status", response_model=SystemStatusResponse)
def get_system_status(db: Session = Depends(get_db)):
    try:
        agents_count = db.query(Agent).count()
        scenarios_count = db.query(Scenario).count()
        runs_count = db.query(TestRun).count()
        db_connected = True
    except Exception:
        agents_count = 0
        scenarios_count = 0
        runs_count = 0
        db_connected = False

    return SystemStatusResponse(
        status="healthy" if db_connected else "degraded",
        version="1.0.0",
        database_connected=db_connected,
        database_url_type="sqlite",
        registered_agents_count=agents_count,
        total_scenarios_count=scenarios_count,
        total_runs_count=runs_count,
        uptime_seconds=round(time.time() - start_time, 1)
    )
