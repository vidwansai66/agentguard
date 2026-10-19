"""
Minimal working LangGraph StateGraph agent for customer support ticketing.
Built using langgraph v1.2+, with zero external API dependencies.
Exposes a compiled StateGraph that interacts with AgentGuard's instrumented tool invoker.
"""
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END

class SupportGraphState(TypedDict):
    prompt: str
    inquiry_type: str
    existing_ticket_id: Optional[str]
    ticket_id: Optional[str]
    status: str
    result: str
    steps: List[str]
    tools: Optional[Dict[str, Any]]

def analyze_request_node(state: SupportGraphState) -> Dict[str, Any]:
    """Analyzes the incoming prompt to extract intent."""
    prompt = state.get("prompt", "")
    steps = list(state.get("steps", []))
    steps.append("analyze_request")

    inquiry_type = "technical" if "bug" in prompt.lower() or "error" in prompt.lower() else "billing"
    return {
        "inquiry_type": inquiry_type,
        "steps": steps,
        "status": "analyzed"
    }

def check_existing_node(state: SupportGraphState) -> Dict[str, Any]:
    """Inspects system state to avoid duplicate tickets."""
    steps = list(state.get("steps", []))
    steps.append("check_existing")
    tools = state.get("tools") or {}

    existing_id = None
    if "query_tickets" in tools:
        # Calls instrumented tool through AgentGuard tool_invoker
        query_res = tools["query_tickets"](query=state.get("prompt", ""))
        if isinstance(query_res, dict) and query_res.get("found"):
            existing_id = query_res.get("ticket_id")

    return {
        "existing_ticket_id": existing_id,
        "steps": steps,
        "status": "checked"
    }

def create_ticket_node(state: SupportGraphState) -> Dict[str, Any]:
    """Creates a ticket using the instrumented tool dispatcher."""
    steps = list(state.get("steps", []))
    steps.append("create_ticket")
    tools = state.get("tools") or {}

    ticket_id = state.get("existing_ticket_id")
    result_text = ""

    if not ticket_id and "create_ticket" in tools:
        # Invocations are intercepted by AgentGuard's FaultInjector
        res = tools["create_ticket"](
            title=f"Support Request: {state.get('inquiry_type', 'general')}",
            description=state.get("prompt", ""),
            idempotency_key=f"langgraph-key-{len(steps)}"
        )
        if isinstance(res, dict):
            ticket_id = res.get("ticket_id") or res.get("data", {}).get("ticket_id")
            result_text = f"Ticket created: {ticket_id}"
        else:
            result_text = f"Ticket created: {res}"
    else:
        result_text = f"Using existing ticket {ticket_id}"

    return {
        "ticket_id": ticket_id,
        "result": result_text,
        "steps": steps,
        "status": "completed"
    }

def finalize_node(state: SupportGraphState) -> Dict[str, Any]:
    """Produces the final agent response."""
    steps = list(state.get("steps", []))
    steps.append("finalize")
    t_id = state.get("ticket_id") or "UNKNOWN"
    return {
        "result": f"Inquiry resolved. Reference Ticket: {t_id}. Steps taken: {', '.join(steps)}",
        "steps": steps,
        "status": "success"
    }

def build_customer_support_graph():
    """Builds and compiles the customer support LangGraph."""
    builder = StateGraph(SupportGraphState)
    builder.add_node("analyze_request", analyze_request_node)
    builder.add_node("check_existing", check_existing_node)
    builder.add_node("create_ticket", create_ticket_node)
    builder.add_node("finalize", finalize_node)

    builder.set_entry_point("analyze_request")
    builder.add_edge("analyze_request", "check_existing")
    builder.add_edge("check_existing", "create_ticket")
    builder.add_edge("create_ticket", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()

# Pre-compiled instance ready for inspection or direct invocation
customer_support_graph = build_customer_support_graph()
