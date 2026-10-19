from typing import Any
import uuid
from app.tools.base import Tool

class MockTicketingTool(Tool):
    """
    Mock ticketing tool that simulates a backend customer support ticketing API.
    Maintains a simulated state store per run context.
    """
    name = "ticket_tool"
    description = "Mock customer support ticketing tool for creating, querying, and retrieving tickets."

    def __init__(self):
        pass

    def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        action = params.get("action", "create")
        state: dict = context.get("tool_state", {}) if context else {}
        if "tickets" not in state:
            state["tickets"] = []
        if "call_history" not in state:
            state["call_history"] = []

        state["call_history"].append({"action": action, "params": params})

        if action == "create":
            title = params.get("title", "Untitled Ticket")
            description = params.get("description", "")
            priority = params.get("priority", "medium")
            idempotency_key = params.get("idempotency_key")

            # Check idempotency if key provided
            if idempotency_key:
                for existing in state["tickets"]:
                    if existing.get("idempotency_key") == idempotency_key:
                        return {
                            "status": "success",
                            "ticket_id": existing["id"],
                            "title": existing["title"],
                            "message": "Ticket already exists (idempotent return)",
                            "is_duplicate": True
                        }

            ticket_id = f"TICK-{uuid.uuid4().hex[:8].upper()}"
            ticket = {
                "id": ticket_id,
                "title": title,
                "description": description,
                "priority": priority,
                "idempotency_key": idempotency_key,
                "created_at": "2026-10-19T10:00:00Z"
            }
            state["tickets"].append(ticket)
            return {
                "status": "success",
                "ticket_id": ticket_id,
                "title": title,
                "priority": priority,
                "message": "Ticket created successfully"
            }

        elif action == "query":
            title = params.get("title")
            idempotency_key = params.get("idempotency_key")
            matched = []
            for t in state["tickets"]:
                if title and t.get("title") == title:
                    matched.append(t)
                elif idempotency_key and t.get("idempotency_key") == idempotency_key:
                    matched.append(t)

            return {
                "status": "success",
                "found_count": len(matched),
                "tickets": [{"ticket_id": t["id"], "title": t["title"], "priority": t["priority"]} for t in matched]
            }

        elif action == "get":
            ticket_id = params.get("ticket_id")
            for t in state["tickets"]:
                if t.get("id") == ticket_id:
                    return {
                        "status": "success",
                        "ticket": t
                    }
            return {
                "status": "not_found",
                "message": f"Ticket {ticket_id} not found"
            }

        elif action == "admin_override":
            # Disallowed tool action for policy violation testing
            return {
                "status": "unauthorized",
                "message": "Admin override executed without authorization check",
                "privileged_access": True
            }

        else:
            return {
                "status": "error",
                "message": f"Unknown ticketing action: {action}"
            }
