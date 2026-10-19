"""
Sample pre-existing AI agent written independently without AgentGuard dependencies.
Demonstrates how an existing function or class can be connected to AgentGuard
using the CallableAgentWrapper with zero code modifications.
"""
from typing import Any, Dict, Optional

def existing_ticket_solver(prompt: str, tools: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Standard customer support function that creates or reconciles a ticket.
    If 'tools' dictionary is provided (Level 3 Instrumented Tools), it calls the tools.
    If 'tools' is None (Level 1 Result-Only / Level 2 Structured Events), it resolves in-memory.
    """
    # Level 3: Instrumented Tools execution
    if tools and "create_ticket" in tools:
        # Check if title is in prompt
        title = "Support Request"
        if "order" in prompt.lower():
            title = "Order Support Request"

        res = tools["create_ticket"](title=title, description=prompt, idempotency_key="existing-key-101")
        if res.get("status") == "success" or res.get("ticket_id"):
            return {
                "status": "success",
                "ticket_id": res.get("ticket_id"),
                "message": f"Successfully created ticket {res.get('ticket_id')}",
                "retries_used": 0
            }
        else:
            return {
                "status": "failed",
                "error": res.get("error", "Failed to create ticket"),
                "message": "Tool execution failed"
            }

    # Level 1 / Level 2 execution (Standalone without tool injection)
    # Returns structured events if applicable
    events = [
        {"action": "parse_prompt", "name": "Prompt Analysis", "input": {"prompt": prompt}, "duration_ms": 2.5},
        {"action": "plan_resolution", "name": "Resolution Planning", "input": {"intent": "resolve_ticket"}, "duration_ms": 4.1}
    ]

    return {
        "status": "success",
        "ticket_id": "TICK-STANDALONE-999",
        "output": f"Resolved support inquiry: {prompt[:40]}...",
        "message": "Resolved independently by existing agent function",
        "events": events
    }


class ExistingCustomerSupportAgent:
    """Class-based existing agent example."""
    def __init__(self, agent_name: str = "LegacyCustomerSupport"):
        self.agent_name = agent_name

    def handle_request(self, prompt: str, tools: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return existing_ticket_solver(prompt=prompt, tools=tools)
