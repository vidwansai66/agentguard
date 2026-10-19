import inspect
import time
from typing import Any, Callable, Dict, List, Optional
from app.adapters.base import AgentAdapter
from app.adapters.models import (
    AgentTaskInput,
    AgentExecutionContext,
    AgentTaskResult,
    ToolCallRequest,
    ToolCallResult
)
from app.tracing.sanitizer import sanitize_text

class CallableAgentWrapper(AgentAdapter):
    """
    SDK Wrapper that adapts an existing Python function, method, or callable object
    into AgentGuard's typed AgentAdapter contract without rewriting agent logic.

    Supports three Observability Levels:
    - LEVEL 1 (Result-Only): Passes task prompt to the callable; maps returned value.
    - LEVEL 2 (Structured-Events): Extracts returned execution events/steps/timings into AgentGuard's trace.
    - LEVEL 3 (Instrumented-Tools): Passes wrapped mock tool dispatchers to the callable,
      routing tool calls through AgentGuard's ToolInvoker for full fault injection.
    """
    adapter_type: str = "python_sdk_wrapper"

    def __init__(
        self,
        agent_id: str,
        target_callable: Callable[..., Any],
        version: str = "1.0.0",
        strategy: str = "default",
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.target_callable = target_callable
        self.version = version
        self.strategy = strategy
        self.config = config or {}
        self.observability_level = self.config.get("observability_level", "level_1_result_only")

        self.declared_capabilities = self.config.get("declared_capabilities", [
            "ticket_create",
            "ticket_query",
            "ticket_get"
        ])
        self.supported_tools = self.config.get("supported_tools", [
            "create_ticket",
            "get_ticket_status"
        ])
        self.input_parameter_name = self.config.get("input_parameter_name", "prompt")
        self._cancelled = False

    def initialize(self, context: Any) -> None:
        self.context = context
        self._cancelled = False

    def test_connection(self) -> Dict[str, Any]:
        """Validates that the target callable is inspectable and executable."""
        if not callable(self.target_callable):
            return {
                "status": "error",
                "message": f"Target object '{self.target_callable}' is not callable.",
                "adapter_type": self.adapter_type
            }

        try:
            sig = inspect.signature(self.target_callable)
            params = list(sig.parameters.keys())
            return {
                "status": "healthy",
                "agent_id": self.agent_id,
                "version": self.version,
                "adapter_type": self.adapter_type,
                "observability_level": self.observability_level,
                "target_name": getattr(self.target_callable, "__name__", str(self.target_callable)),
                "parameters": params,
                "message": f"Callable verified with signature {sig}."
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Callable signature inspection failed: {str(e)}",
                "adapter_type": self.adapter_type
            }

    def run_task(
        self,
        task_input: Any,
        context: Any,
        tool_invoker: Any
    ) -> Dict[str, Any]:
        """
        Executes the wrapped callable, adapting arguments and outputs
        according to the configured observability level.
        """
        self._cancelled = False
        start_time = time.perf_counter()

        # Extract prompt & parameters
        if hasattr(task_input, "model_dump"):
            inp_dict = task_input.model_dump()
        elif isinstance(task_input, dict):
            inp_dict = task_input
        else:
            inp_dict = {"prompt": str(task_input)}

        prompt = inp_dict.get("prompt") or inp_dict.get("description") or inp_dict.get("task") or str(inp_dict)

        tool_invoker.record_decision(
            action="sdk_wrapper_start",
            reasoning=f"Executing existing agent via CallableAgentWrapper [Observability: {self.observability_level}]"
        )

        try:
            sig = inspect.signature(self.target_callable)
            call_kwargs: Dict[str, Any] = {}

            # Determine how the callable expects the input
            if self.input_parameter_name in sig.parameters:
                call_kwargs[self.input_parameter_name] = prompt
            elif "prompt" in sig.parameters:
                call_kwargs["prompt"] = prompt
            elif "task" in sig.parameters:
                call_kwargs["task"] = prompt
            elif "input" in sig.parameters:
                call_kwargs["input"] = prompt
            elif len(sig.parameters) == 1:
                first_param = list(sig.parameters.keys())[0]
                call_kwargs[first_param] = prompt
            else:
                call_kwargs["prompt"] = prompt

            # Provide instrumented tools if Level 3 or if callable accepts tools
            if self.observability_level == "level_3_instrumented_tools" or "tools" in sig.parameters:
                def wrapped_create_ticket(title: str, description: str = "", idempotency_key: str = "", **extra):
                    return tool_invoker.call_tool(
                        tool_name="ticket_create",
                        params={
                            "action": "create",
                            "title": title,
                            "description": description,
                            "idempotency_key": idempotency_key,
                            **extra
                        }
                    )

                def wrapped_get_ticket(ticket_id: str):
                    return tool_invoker.call_tool(
                        tool_name="ticket_get",
                        params={"action": "get", "ticket_id": ticket_id}
                    )

                def wrapped_query_tickets(query: str):
                    return tool_invoker.call_tool(
                        tool_name="ticket_query",
                        params={"action": "query", "query": query}
                    )

                tools_dict = {
                    "create_ticket": wrapped_create_ticket,
                    "get_ticket_status": wrapped_get_ticket,
                    "query_tickets": wrapped_query_tickets,
                    "ticket_tool": tool_invoker.call_tool
                }

                if "tools" in sig.parameters:
                    call_kwargs["tools"] = tools_dict
                elif "tool_invoker" in sig.parameters:
                    call_kwargs["tool_invoker"] = tool_invoker

            # Execute the existing agent callable
            raw_result = self.target_callable(**call_kwargs)

            # Map result according to observability level
            if self.observability_level == "level_2_structured_events":
                # Extract structured execution events if returned by the agent
                if isinstance(raw_result, dict):
                    events = raw_result.get("events") or raw_result.get("trace") or raw_result.get("steps") or []
                    for idx, ev in enumerate(events):
                        ev_name = ev.get("action") or ev.get("name") or "agent_step"
                        ev_type = ev.get("type", "agent_step")
                        tool_invoker.recorder.record_event(
                            step_index=tool_invoker.current_step + idx + 1,
                            event_type=ev_type,
                            action_name=ev_name,
                            tool_name=ev.get("tool_name"),
                            input_data=ev.get("input", {}),
                            output_data=ev.get("output", {}),
                            duration_ms=float(ev.get("duration_ms", 1.0))
                        )

            # Standardize returned output
            if isinstance(raw_result, dict):
                status = raw_result.get("status", "success")
                ticket_id = raw_result.get("ticket_id") or raw_result.get("id")
                msg = raw_result.get("message") or raw_result.get("output") or raw_result.get("answer") or "Task completed"
                return {
                    "status": status,
                    "ticket_id": ticket_id,
                    "disrupted": raw_result.get("disrupted", False),
                    "recovered": raw_result.get("recovered", False),
                    "retries_used": raw_result.get("retries_used", 0),
                    "message": str(msg),
                    "raw_output": raw_result,
                    "observability_level": self.observability_level
                }
            else:
                return {
                    "status": "success",
                    "message": str(raw_result),
                    "disrupted": False,
                    "recovered": False,
                    "raw_output": raw_result,
                    "observability_level": self.observability_level
                }

        except Exception as e:
            err = sanitize_text(str(e))
            tool_invoker.record_decision(
                action="sdk_wrapper_error",
                reasoning=f"Error executing callable agent: {err}"
            )
            return {
                "status": "failed",
                "disrupted": True,
                "recovered": False,
                "error": err,
                "message": f"Execution failed in wrapped agent: {err}",
                "observability_level": self.observability_level
            }

    def cancel(self) -> None:
        self._cancelled = True

    def dispose(self) -> None:
        pass
