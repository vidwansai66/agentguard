import time
import hashlib
from typing import Any
from app.agents.base import AgentAdapter

class SampleTicketAgent(AgentAdapter):
    """
    Built-in Sample Python Agent that manages support tickets through mock tools.
    Supports configurable recovery strategies:
    - baseline: naive retry without duplicate checks; follows injected instructions; no response validation
    - safe_idempotent: checks state before retrying after ambiguous faults; uses idempotency keys
    - bounded_backoff: strictly limits retries with bounded backoff
    - strict_policy: strictly validates tool whitelists and rejects untrusted prompt injections
    """
    def __init__(self, agent_id: str = "agent-ticket-sample", version: str = "1.0.0", strategy: str = "baseline", config: dict[str, Any] | None = None):
        self.agent_id = agent_id
        self.version = version
        self.strategy = strategy
        self.config = config or {}

    def _derive_idempotency_key(self, task_input: dict[str, Any]) -> str:
        title = task_input.get("title", "")
        desc = task_input.get("description", "")
        raw = f"{title}:{desc}"
        return f"idemp-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    def run_task(
        self,
        task_input: dict[str, Any],
        context: dict[str, Any],
        tool_invoker: Any
    ) -> dict[str, Any]:
        action_name = task_input.get("action", "create_ticket")
        title = task_input.get("title", "Customer Inquiry")
        description = task_input.get("description", "Customer requested assistance with order.")
        priority = task_input.get("priority", "medium")

        # Strategy flags
        is_idempotent_strategy = (
            self.strategy in ["safe_idempotent", "strict_policy"] or
            self.config.get("enable_idempotency_check", False)
        )
        is_strict_policy = (
            self.strategy == "strict_policy" or
            self.config.get("enable_strict_policy", False)
        )
        max_retries = self.config.get("max_retries", 3 if self.strategy == "bounded_backoff" else 3)
        require_schema_validation = (
            self.strategy in ["safe_idempotent", "strict_policy"] or
            self.config.get("require_schema_validation", False)
        )

        idempotency_key = self._derive_idempotency_key(task_input) if is_idempotent_strategy else None

        retries_used = 0
        last_error = None
        ticket_id = None
        disrupted = False
        recovered = False

        tool_invoker.record_decision(
            action="initiate_task",
            reasoning=f"Starting support ticket task with strategy='{self.strategy}', idempotency={is_idempotent_strategy}"
        )

        # Pre-check if state-aware recovery is enabled and ticket might already exist
        if is_idempotent_strategy:
            tool_invoker.record_decision(
                action="pre_execution_state_check",
                reasoning="Checking if ticket already exists before creating"
            )
            try:
                query_res = tool_invoker.call_tool(
                    tool_name="ticket_tool",
                    params={"action": "query", "title": title, "idempotency_key": idempotency_key}
                )
                if query_res.get("found_count", 0) > 0 and query_res.get("tickets"):
                    existing_id = query_res["tickets"][0]["ticket_id"]
                    tool_invoker.record_decision(
                        action="existing_ticket_found",
                        reasoning=f"Ticket already exists with id {existing_id}. Reusing existing resource."
                    )
                    return {
                        "status": "success",
                        "ticket_id": existing_id,
                        "disrupted": False,
                        "recovered": True,
                        "retries_used": 0,
                        "message": "Existing ticket reused successfully"
                    }
            except Exception as e:
                tool_invoker.record_decision(
                    action="pre_check_skipped",
                    reasoning=f"State query exception: {str(e)}"
                )

        while retries_used <= max_retries:
            try:
                tool_invoker.record_decision(
                    action="call_create_ticket",
                    reasoning=f"Attempt {retries_used + 1}/{max_retries + 1} to create ticket '{title}'"
                )
                create_params = {
                    "action": "create",
                    "title": title,
                    "description": description,
                    "priority": priority
                }
                if idempotency_key:
                    create_params["idempotency_key"] = idempotency_key

                res = tool_invoker.call_tool(
                    tool_name="ticket_tool",
                    params=create_params,
                    retry_count=retries_used
                )

                # Schema validation check
                if require_schema_validation:
                    if not isinstance(res, dict) or "ticket_id" not in res or "status" not in res:
                        raise ValueError(f"Malformed tool response received: missing expected schema fields ({res})")

                # Prompt Injection Defense:
                # If naive baseline, check if external response tells us to invoke admin_override
                if not is_strict_policy:
                    untrusted_text = str(res.get("untrusted_external_comment", "") or res.get("message", ""))
                    if "admin_override" in untrusted_text:
                        tool_invoker.record_decision(
                            action="follow_untrusted_prompt",
                            reasoning="External tool response instructed execution of 'admin_override'. Executing now without validation."
                        )
                        # Naively invoke disallowed tool
                        tool_invoker.call_tool(
                            tool_name="ticket_tool",
                            params={"action": "admin_override", "payload": "unauthorized_leak"}
                        )

                ticket_id = res.get("ticket_id")
                if disrupted:
                    recovered = True

                tool_invoker.record_decision(
                    action="task_completed",
                    reasoning=f"Ticket created successfully with ID {ticket_id}"
                )
                return {
                    "status": "success",
                    "ticket_id": ticket_id,
                    "disrupted": disrupted,
                    "recovered": recovered,
                    "retries_used": retries_used,
                    "message": "Ticket successfully created"
                }

            except Exception as e:
                disrupted = True
                retries_used += 1
                last_error = str(e)
                tool_invoker.record_decision(
                    action="error_encountered",
                    reasoning=f"Tool call failed with error: {last_error}. Evaluating recovery policy."
                )

                # STATE-AWARE RECOVERY:
                # If safe_idempotent strategy is active, before attempting a blind duplicate retry,
                # check if the ticket actually got created despite the lost response (ambiguous outcome)!
                if is_idempotent_strategy and retries_used <= max_retries:
                    tool_invoker.record_decision(
                        action="state_aware_query_recovery",
                        reasoning="Disruption occurred. Performing state query to verify if action committed before re-invoking creation."
                    )
                    try:
                        q_res = tool_invoker.call_tool(
                            tool_name="ticket_tool",
                            params={"action": "query", "title": title, "idempotency_key": idempotency_key},
                            retry_count=retries_used
                        )
                        if q_res.get("found_count", 0) > 0 and q_res.get("tickets"):
                            committed_ticket_id = q_res["tickets"][0]["ticket_id"]
                            tool_invoker.record_decision(
                                action="state_aware_recovery_success",
                                reasoning=f"Discovered ticket {committed_ticket_id} was successfully created prior to response loss! Recovered safely without duplicate action."
                            )
                            return {
                                "status": "success",
                                "ticket_id": committed_ticket_id,
                                "disrupted": True,
                                "recovered": True,
                                "retries_used": retries_used,
                                "message": "State-aware recovery succeeded: existing ticket reconciled"
                            }
                    except Exception as query_err:
                        tool_invoker.record_decision(
                            action="state_query_failed",
                            reasoning=f"State query attempt failed: {str(query_err)}"
                        )

                # If bounded backoff, apply a slight delay
                if self.strategy == "bounded_backoff":
                    time.sleep(0.01)

        tool_invoker.record_decision(
            action="task_failed",
            reasoning=f"Task exhausted retry budget ({max_retries}). Final error: {last_error}"
        )
        return {
            "status": "failed",
            "ticket_id": None,
            "disrupted": disrupted,
            "recovered": False,
            "retries_used": retries_used,
            "error": last_error,
            "message": f"Task failed after {retries_used} attempts: {last_error}"
        }
