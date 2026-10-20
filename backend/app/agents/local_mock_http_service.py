"""
Stateful, verifiable HTTP test agent for local development and testing.
Provides an isolated, thread-safe ticket store, actual ticket ID generation,
idempotency-key handling, ticket lookup, and deterministic failure simulation
without external network dependencies.
"""
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route


class MockHttpTicketStore:
    """Thread-safe in-memory ticket store for HTTP test agent verification."""

    def __init__(self):
        self._lock = threading.Lock()
        self.tickets: List[Dict[str, Any]] = []
        self.tickets_by_id: Dict[str, Dict[str, Any]] = {}
        self.tickets_by_idemp: Dict[str, Dict[str, Any]] = {}
        self.call_history: List[Dict[str, Any]] = []
        self.simulated_failure: Optional[Dict[str, Any]] = None

    def reset(self) -> None:
        """Clears all tickets, history, and simulation rules."""
        with self._lock:
            self.tickets.clear()
            self.tickets_by_id.clear()
            self.tickets_by_idemp.clear()
            self.call_history.clear()
            self.simulated_failure = None

    def set_simulated_failure(
        self,
        status_code: int = 500,
        error_message: str = "Simulated internal server error",
        error_type: str = "http_error"
    ) -> None:
        """Configures simulated failure for upcoming requests."""
        with self._lock:
            self.simulated_failure = {
                "status_code": status_code,
                "error_message": error_message,
                "error_type": error_type
            }

    def clear_simulated_failure(self) -> None:
        """Clears any active simulated failure."""
        with self._lock:
            self.simulated_failure = None

    def create_or_get_ticket(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a ticket or returns existing ticket if idempotency_key matches."""
        with self._lock:
            if idempotency_key and idempotency_key in self.tickets_by_idemp:
                existing = self.tickets_by_idemp[idempotency_key]
                return {
                    "ticket": existing,
                    "ticket_id": existing["id"],
                    "is_duplicate": True
                }

            ticket_id = f"TICK-HTTP-{uuid.uuid4().hex[:8].upper()}"
            ticket = {
                "id": ticket_id,
                "ticket_id": ticket_id,
                "title": title,
                "description": description,
                "priority": priority,
                "idempotency_key": idempotency_key,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            self.tickets.append(ticket)
            self.tickets_by_id[ticket_id] = ticket
            if idempotency_key:
                self.tickets_by_idemp[idempotency_key] = ticket
            return {
                "ticket": ticket,
                "ticket_id": ticket_id,
                "is_duplicate": False
            }

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a ticket by ID."""
        with self._lock:
            return self.tickets_by_id.get(ticket_id)

    def get_all_tickets(self) -> List[Dict[str, Any]]:
        """Returns all created tickets."""
        with self._lock:
            return list(self.tickets)


# Shared default store for simple usage
default_mock_store = MockHttpTicketStore()


def _get_store(request) -> MockHttpTicketStore:
    return getattr(request.app.state, "ticket_store", default_mock_store)


async def mock_health(request):
    store = _get_store(request)
    return JSONResponse({
        "status": "healthy",
        "service": "stateful-customer-portal-agent",
        "version": "1.0.0",
        "capabilities": ["ticket_create", "ticket_query", "ticket_get"],
        "observability": "level_1_result_only",
        "ticket_count": len(store.get_all_tickets())
    })


async def mock_run(request):
    store = _get_store(request)
    try:
        body = await request.json()
    except Exception:
        body = {}

    with store._lock:
        store.call_history.append({"path": request.url.path, "body": body})

    # 1. Check if store-level simulated failure is configured
    if store.simulated_failure:
        fail_cfg = store.simulated_failure
        status_code = fail_cfg.get("status_code", 500)
        err_msg = fail_cfg.get("error_message", "Simulated internal server error")
        err_type = fail_cfg.get("error_type", "http_error")
        if err_type == "malformed_json":
            return Response("<<<MALFORMED_JSON_PAYLOAD_EOF>>>", media_type="application/json", status_code=200)
        return JSONResponse({"status": "failed", "error": err_msg, "message": err_msg}, status_code=status_code)

    # 2. Check per-request failure simulation parameters
    task_inp = body.get("task_input") if isinstance(body.get("task_input"), dict) else {}
    sim_error = body.get("simulate_error") or task_inp.get("simulate_error") or request.headers.get("X-Simulate-Error")
    if sim_error:
        err_code = int(body.get("error_status_code") or task_inp.get("error_status_code") or request.headers.get("X-Simulate-Error-Code") or 500)
        err_msg = body.get("error_message") or task_inp.get("error_message") or "Simulated external agent failure"
        return JSONResponse({"status": "failed", "error": err_msg, "message": err_msg}, status_code=err_code)

    if body.get("simulate_malformed_json") or task_inp.get("simulate_malformed_json"):
        return Response("<<<MALFORMED_JSON_PAYLOAD_EOF>>>", media_type="application/json", status_code=200)

    if body.get("simulate_mapping_error") or task_inp.get("simulate_mapping_error"):
        return JSONResponse({"unrelated_data": 12345}, status_code=200)

    # 3. Extract task input parameters
    task = body.get("task") or body.get("prompt") or body.get("query")
    if not task and isinstance(body.get("task_input"), dict):
        task = body["task_input"].get("description") or body["task_input"].get("task") or body["task_input"].get("title")
    if not task:
        task = "Customer support inquiry"

    title = body.get("title") or (body.get("task_input", {}).get("title") if isinstance(body.get("task_input"), dict) else None) or f"Inquiry: {task[:40]}"
    priority = body.get("priority") or (body.get("task_input", {}).get("priority") if isinstance(body.get("task_input"), dict) else None) or "medium"
    idempotency_key = body.get("idempotency_key") or (body.get("task_input", {}).get("idempotency_key") if isinstance(body.get("task_input"), dict) else None) or request.headers.get("X-Idempotency-Key")

    # 4. Create or retrieve ticket via store
    ticket_res = store.create_or_get_ticket(
        title=title,
        description=task,
        priority=priority,
        idempotency_key=idempotency_key
    )
    ticket_id = ticket_res["ticket_id"]
    is_duplicate = ticket_res["is_duplicate"]
    msg = f"External HTTP agent resolved inquiry: '{task}'"

    events = [
        {"action": "receive_inquiry", "type": "agent_step", "duration_ms": 1.2},
        {"action": "create_ticket_record", "type": "agent_step", "duration_ms": 2.5, "output": {"ticket_id": ticket_id, "is_duplicate": is_duplicate}},
        {"action": "formulate_resolution", "type": "agent_step", "duration_ms": 3.1}
    ]

    return JSONResponse({
        "status": "success",
        "result": msg,
        "output": msg,
        "message": msg,
        "ticket_id": ticket_id,
        "is_duplicate": is_duplicate,
        "ticket": ticket_res["ticket"],
        "events": events,
        "metadata": {
            "processing_time_ms": 15.4,
            "engine": "StatefulHttpTestAgent/2.0",
            "ticket_id": ticket_id,
            "is_duplicate": is_duplicate
        }
    })


async def mock_get_ticket(request):
    store = _get_store(request)
    ticket_id = request.path_params.get("ticket_id")
    ticket = store.get_ticket(ticket_id)
    if not ticket:
        return JSONResponse({"status": "not_found", "error": f"Ticket {ticket_id} not found"}, status_code=404)
    return JSONResponse({"status": "success", "ticket": ticket})


async def mock_list_tickets(request):
    store = _get_store(request)
    tickets = store.get_all_tickets()
    return JSONResponse({"status": "success", "tickets": tickets, "count": len(tickets)})


async def mock_reset(request):
    store = _get_store(request)
    store.reset()
    return JSONResponse({"status": "success", "message": "Ticket store reset successfully"})


def create_mock_agent_app(store: Optional[MockHttpTicketStore] = None) -> Starlette:
    """Returns a standalone Starlette ASGI app for testing HttpAgentAdapter with a dedicated or shared ticket store."""
    app_store = store or MockHttpTicketStore()
    routes = [
        Route("/health", mock_health, methods=["GET"]),
        Route("/run", mock_run, methods=["POST"]),
        Route("/agent/invoke", mock_run, methods=["POST"]),
        Route("/api/v1/run", mock_run, methods=["POST"]),
        Route("/api/v1/health", mock_health, methods=["GET"]),
        Route("/tickets", mock_list_tickets, methods=["GET"]),
        Route("/tickets/{ticket_id}", mock_get_ticket, methods=["GET"]),
        Route("/reset", mock_reset, methods=["POST"]),
    ]
    app = Starlette(routes=routes)
    app.state.ticket_store = app_store
    return app
