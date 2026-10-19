"""
Safe sample HTTP agent for local development and testing.
Provides a mock HTTP service simulating external agent endpoints without external dependencies.
"""
from typing import Dict, Any, List
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

async def mock_health(request):
    return JSONResponse({
        "status": "healthy",
        "service": "sample-customer-portal-agent",
        "version": "1.0.0",
        "capabilities": ["ticket_create", "ticket_query", "ticket_get"],
        "observability": "level_1_result_only"
    })

async def mock_run(request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    task = body.get("task") or body.get("prompt") or body.get("query") or "Default task"

    # Simulate structured events if Level 2 requested
    events = [
        {"action": "receive_inquiry", "type": "agent_step", "duration_ms": 1.2},
        {"action": "check_catalog", "type": "agent_step", "duration_ms": 2.5},
        {"action": "formulate_resolution", "type": "agent_step", "duration_ms": 3.1}
    ]

    return JSONResponse({
        "status": "completed",
        "result": f"External HTTP agent resolved inquiry: '{task}'",
        "ticket_id": "TICKET-EXT-8821",
        "events": events,
        "metadata": {
            "processing_time_ms": 15.4,
            "engine": "SampleHttpBot/1.0"
        }
    })

def create_mock_agent_app() -> Starlette:
    """Returns a standalone Starlette ASGI app for testing HttpAgentAdapter."""
    routes = [
        Route("/health", mock_health, methods=["GET"]),
        Route("/run", mock_run, methods=["POST"]),
        Route("/agent/invoke", mock_run, methods=["POST"]),
        Route("/api/v1/run", mock_run, methods=["POST"]),
        Route("/api/v1/health", mock_health, methods=["GET"])
    ]
    return Starlette(routes=routes)
