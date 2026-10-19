from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.agents import router as agents_router
from app.api.scenarios import router as scenarios_router
from app.api.suites import router as suites_router
from app.api.runs import router as runs_router
from app.api.diagnoses import router as diagnoses_router
from app.api.patches import router as patches_router
from app.api.comparisons import router as comparisons_router
from app.api.system import router as system_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(agents_router)
api_router.include_router(scenarios_router)
api_router.include_router(suites_router)
api_router.include_router(runs_router)
api_router.include_router(diagnoses_router)
api_router.include_router(patches_router)
api_router.include_router(comparisons_router)
api_router.include_router(system_router)
