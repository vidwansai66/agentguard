import time
import uuid
from typing import Any
from app.faults.injector import FaultInjector, FaultInjectionError
from app.tracing.recorder import TraceRecorder
from app.tools.mock_ticketing import MockTicketingTool
from app.agents.registry import agent_registry
from app.evaluation.evaluator import Evaluator

class ToolInvoker:
    def __init__(
        self,
        tool: MockTicketingTool,
        fault_injector: FaultInjector,
        recorder: TraceRecorder,
        context: dict[str, Any],
        max_steps: int = 20,
        allowed_tools: list[str] | None = None
    ):
        self.tool = tool
        self.fault_injector = fault_injector
        self.recorder = recorder
        self.context = context
        self.max_steps = max_steps
        self.allowed_tools = allowed_tools or ["ticket_create", "ticket_query", "ticket_get", "ticket_tool"]
        self.current_step = 0

    def record_decision(self, action: str, reasoning: str):
        self.current_step += 1
        self.recorder.record_event(
            step_index=self.current_step,
            event_type="agent_decision",
            action_name=action,
            severity="info",
            input_data={"reasoning": reasoning}
        )

    def call_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        retry_count: int = 0
    ) -> dict[str, Any]:
        self.current_step += 1
        if self.current_step > self.max_steps:
            raise RuntimeError(f"Maximum step count ({self.max_steps}) exceeded. Halting unbounded execution.")

        action = params.get("action", "")
        start_time = time.perf_counter()

        # Record tool call intention
        self.recorder.record_event(
            step_index=self.current_step,
            event_type="tool_call",
            action_name=action,
            tool_name=tool_name,
            input_data=params,
            retry_count=retry_count
        )

        # 1. Fault injection BEFORE execution
        try:
            fault_res = self.fault_injector.intercept_before_execution(tool_name, params)
            if fault_res is not None:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self.recorder.record_event(
                    step_index=self.current_step,
                    event_type="fault_injected",
                    action_name=action,
                    tool_name=tool_name,
                    fault_details={"fault_type": self.fault_injector.fault_type},
                    duration_ms=duration_ms
                )
                return fault_res
        except FaultInjectionError as fie:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.recorder.record_event(
                step_index=self.current_step,
                event_type="fault_injected",
                action_name=action,
                tool_name=tool_name,
                severity="warning",
                fault_details=fie.details,
                duration_ms=duration_ms,
                error_message=fie.message
            )
            raise fie

        # 2. Actual tool execution in context state
        actual_result = self.tool.execute(params, context=self.context)

        # 3. Fault injection AFTER execution (e.g. ambiguous outcome dropped packet, malformed output, prompt injection)
        try:
            final_result = self.fault_injector.intercept_after_execution(
                tool_name=tool_name,
                params=params,
                actual_result=actual_result,
                context=self.context
            )
        except FaultInjectionError as fie:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.recorder.record_event(
                step_index=self.current_step,
                event_type="fault_injected",
                action_name=action,
                tool_name=tool_name,
                severity="warning",
                fault_details=fie.details,
                duration_ms=duration_ms,
                error_message=fie.message
            )
            raise fie

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record tool response
        self.recorder.record_event(
            step_index=self.current_step,
            event_type="tool_response",
            action_name=action,
            tool_name=tool_name,
            output_data=final_result,
            retry_count=retry_count,
            duration_ms=duration_ms
        )

        return final_result


class ScenarioRunner:
    """
    Executes a single scenario under controlled, bounded conditions.
    """
    def __init__(self):
        self.evaluator = Evaluator()

    def run_scenario(
        self,
        scenario_data: dict[str, Any],
        agent_id: str,
        agent_version: str = "1.0.0",
        agent_strategy: str = "baseline",
        custom_config: dict[str, Any] | None = None,
        run_id: str | None = None
    ) -> dict[str, Any]:
        run_id = run_id or f"RUN-{uuid.uuid4().hex[:10]}"
        scenario_result_id = f"RES-{uuid.uuid4().hex[:10]}"
        scenario_id = scenario_data.get("id", "scenario-unknown")

        # Set up bounded execution context
        execution_limits = scenario_data.get("execution_limits", {})
        max_steps = execution_limits.get("max_steps", 20)

        context: dict[str, Any] = {
            "tool_state": {
                "tickets": [],
                "call_history": []
            }
        }

        fault_params = scenario_data.get("fault_parameters", {})
        fault_injector = FaultInjector(fault_params=fault_params)
        tool = MockTicketingTool()
        recorder = TraceRecorder(run_id=run_id, scenario_result_id=scenario_result_id, scenario_id=scenario_id)

        allowed_tools = scenario_data.get("allowed_tools", ["ticket_create", "ticket_query", "ticket_get"])
        tool_invoker = ToolInvoker(
            tool=tool,
            fault_injector=fault_injector,
            recorder=recorder,
            context=context,
            max_steps=max_steps,
            allowed_tools=allowed_tools
        )

        agent = agent_registry.get_agent(
            agent_id=agent_id,
            version=agent_version,
            strategy=agent_strategy,
            config=custom_config or {}
        )

        start_time = time.perf_counter()
        agent_output = {}
        error_message = None

        try:
            agent_output = agent.run_task(
                task_input=scenario_data.get("task_input", {}),
                context=context,
                tool_invoker=tool_invoker
            )
        except Exception as e:
            error_message = str(e)
            agent_output = {
                "status": "error",
                "disrupted": True,
                "recovered": False,
                "error": error_message
            }
            recorder.record_event(
                step_index=tool_invoker.current_step + 1,
                event_type="error",
                severity="critical",
                error_message=error_message
            )

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Evaluate execution results deterministically
        trace_events = recorder.get_events()
        assertion_results = self.evaluator.evaluate(
            scenario_data=scenario_data,
            agent_output=agent_output,
            trace_events=trace_events,
            context=context
        )

        # Determine overall pass/fail status
        critical_failed = any(not a.passed for a in assertion_results if a.severity in ["critical", "high"])
        overall_passed = not critical_failed and (agent_output.get("status") == "success")

        # Side effect & recovery tracking
        tickets = context["tool_state"].get("tickets", [])
        has_unsafe_side_effect = len(tickets) > 1 or any(
            not a.passed for a in assertion_results if a.rule_id in ["ASSERT_NO_DUPLICATE_ACTIONS", "ASSERT_POLICY_COMPLIANCE", "ASSERT_NO_PROMPT_INJECTION_EXPLOIT"]
        )
        disrupted = agent_output.get("disrupted", False) or bool(fault_injector.history)
        recovered = agent_output.get("recovered", False) and overall_passed

        result_dict = {
            "id": scenario_result_id,
            "run_id": run_id,
            "scenario_id": scenario_id,
            "scenario_name": scenario_data.get("name", "Unnamed Scenario"),
            "scenario_version": scenario_data.get("version", 1),
            "failure_type": scenario_data.get("failure_type", "normal_execution"),
            "status": "passed" if overall_passed else "failed",
            "passed": overall_passed,
            "disrupted": disrupted,
            "recovered": recovered,
            "has_unsafe_side_effect": has_unsafe_side_effect,
            "duration_ms": round(duration_ms, 2),
            "retry_count": agent_output.get("retries_used", 0),
            "step_count": tool_invoker.current_step,
            "error_message": error_message or agent_output.get("error"),
            "execution_output": agent_output,
            "scenario_snapshot": scenario_data,
            "findings": [
                {
                    "rule_id": a.rule_id,
                    "rule_name": a.rule_name,
                    "status": "passed" if a.passed else "failed",
                    "severity": a.severity,
                    "message": a.message,
                    "explanation": a.explanation,
                    "trace_event_ids": a.trace_event_ids,
                    "evidence": a.evidence
                }
                for a in assertion_results
            ],
            "trace_events": trace_events
        }

        return result_dict

scenario_runner = ScenarioRunner()
