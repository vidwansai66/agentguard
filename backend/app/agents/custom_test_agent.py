import time
import hashlib
from typing import Any
from app.adapters.base import AgentAdapter
from app.adapters.models import AgentTaskInput, AgentExecutionContext, AgentTaskResult

class CustomTestAgent(AgentAdapter):
    """
    Example Custom Python Agent that implements the AgentGuard Adapter Contract.
    Demonstrates third-party agent integration without altering runner internals.
    """
    adapter_type: str = "python"

    def __init__(
        self,
        agent_id: str = "agent-custom-python",
        version: str = "1.0.0",
        strategy: str = "baseline",
        config: dict[str, Any] | None = None
    ):
        self.agent_id = agent_id
        self.version = version
        self.strategy = strategy
        self.config = config or {}
        # Capabilities can be configured or defaulted
        self.declared_capabilities = self.config.get("declared_capabilities", [
            "ticket_create",
            "ticket_query",
            "ticket_get",
            "state_inspection",
            "handle_structured_errors"
        ])
        self.supported_tools = self.config.get("supported_tools", [
            "ticket_create",
            "ticket_query",
            "ticket_get"
        ])
        self.is_cancelled = False

    def initialize(self, config: dict[str, Any]) -> None:
        self.config.update(config or {})
        if "declared_capabilities" in config:
            self.declared_capabilities = config["declared_capabilities"]
        if "supported_tools" in config:
            self.supported_tools = config["supported_tools"]

    def test_connection(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "agent_id": self.agent_id,
            "version": self.version,
            "adapter_type": self.adapter_type,
            "declared_capabilities": self.declared_capabilities,
            "supported_tools": self.supported_tools,
            "message": "Custom Python Agent initialized successfully and verified."
        }

    def cancel(self) -> None:
        self.is_cancelled = True

    def dispose(self) -> None:
        self.is_cancelled = False

    def _derive_idempotency_key(self, title: str, desc: str) -> str:
        raw = f"custom:{title}:{desc}"
        return f"cust-idemp-{hashlib.sha256(raw.encode()).hexdigest()[:10]}"

    def run_task(
        self,
        task_input: AgentTaskInput | dict[str, Any],
        context: AgentExecutionContext | dict[str, Any],
        tool_invoker: Any
    ) -> dict[str, Any]:
        inp = task_input.model_dump() if hasattr(task_input, "model_dump") else dict(task_input or {})
        title = inp.get("title", "Custom Task")
        description = inp.get("description", "Custom ticket description")
        priority = inp.get("priority", "medium")

        has_state_inspection = "state_inspection" in self.declared_capabilities
        idempotency_key = self._derive_idempotency_key(title, description)

        tool_invoker.record_decision(
            action="custom_agent_start",
            reasoning=f"Custom agent '{self.agent_id}' starting task with strategy='{self.strategy}'"
        )

        should_reconcile = has_state_inspection and (
            self.strategy in ["safe_idempotent", "safe"] or self.config.get("enable_reconciliation", False)
        )

        # Pre-check if state_inspection capability is declared
        if should_reconcile:
            tool_invoker.record_decision(
                action="pre_execution_query",
                reasoning="Checking existing tickets via state_inspection capability"
            )
            try:
                q_res = tool_invoker.call_tool(
                    tool_name="ticket_tool",
                    params={"action": "query", "title": title, "idempotency_key": idempotency_key}
                )
                if q_res.get("found_count", 0) > 0 and q_res.get("tickets"):
                    t_id = q_res["tickets"][0]["ticket_id"]
                    return {
                        "status": "success",
                        "ticket_id": t_id,
                        "disrupted": False,
                        "recovered": True,
                        "retries_used": 0,
                        "message": "Reused existing ticket safely"
                    }
            except Exception:
                pass

        # Execution loop with retries
        max_retries = self.config.get("max_retries", 2)
        retries_used = 0
        last_error = None
        disrupted = False
        recovered = False

        while retries_used <= max_retries:
            if self.is_cancelled:
                return {
                    "status": "cancelled",
                    "ticket_id": None,
                    "disrupted": disrupted,
                    "recovered": False,
                    "message": "Execution cancelled by request"
                }

            try:
                create_params = {
                    "action": "create",
                    "title": title,
                    "description": description,
                    "priority": priority
                }
                if should_reconcile:
                    create_params["idempotency_key"] = idempotency_key

                res = tool_invoker.call_tool(
                    tool_name="ticket_tool",
                    params=create_params,
                    retry_count=retries_used
                )

                t_id = res.get("ticket_id")
                return {
                    "status": "success",
                    "ticket_id": t_id,
                    "disrupted": disrupted,
                    "recovered": disrupted and recovered,
                    "retries_used": retries_used,
                    "message": "Custom agent created ticket successfully"
                }

            except Exception as e:
                disrupted = True
                retries_used += 1
                last_error = str(e)

                # Safe recovery if state inspection is supported
                if should_reconcile and retries_used <= max_retries:
                    tool_invoker.record_decision(
                        action="reconcile_state_after_error",
                        reasoning="Disruption observed; querying store to prevent duplicate action"
                    )
                    try:
                        q_res = tool_invoker.call_tool(
                            tool_name="ticket_tool",
                            params={"action": "query", "title": title, "idempotency_key": idempotency_key},
                            retry_count=retries_used
                        )
                        if q_res.get("found_count", 0) > 0 and q_res.get("tickets"):
                            committed_id = q_res["tickets"][0]["ticket_id"]
                            return {
                                "status": "success",
                                "ticket_id": committed_id,
                                "disrupted": True,
                                "recovered": True,
                                "retries_used": retries_used,
                                "message": "State reconciled after ambiguous fault"
                            }
                    except Exception:
                        pass

        return {
            "status": "failed",
            "ticket_id": None,
            "disrupted": disrupted,
            "recovered": False,
            "retries_used": retries_used,
            "error": last_error,
            "message": f"Custom agent failed after {retries_used} attempts: {last_error}"
        }
