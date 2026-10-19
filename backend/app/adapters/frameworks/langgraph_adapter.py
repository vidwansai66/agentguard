import time
import inspect
from typing import Any, Dict, List, Optional
from app.adapters.base import AgentAdapter
from app.adapters.models import AgentTaskInput, AgentExecutionContext, AgentTaskResult
from app.tracing.sanitizer import sanitize_text

class LangGraphAgentAdapter(AgentAdapter):
    """
    Adapter for LangGraph-based agents.
    Executes compiled StateGraph workflows while routing node-level tool calls
    through AgentGuard's instrumented tool invoker and recording state transitions.
    """
    adapter_type: str = "langgraph"

    def __init__(
        self,
        agent_id: str,
        graph_instance: Any = None,
        version: str = "1.0.0",
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.version = version
        self.config = config or {}
        self.observability_level = "level_3_instrumented_tools"
        self.declared_capabilities = self.config.get("declared_capabilities", [
            "ticket_create",
            "ticket_query",
            "ticket_get",
            "state_inspection",
            "handle_structured_errors"
        ])
        self.supported_tools = ["create_ticket", "get_ticket_status", "query_tickets"]

        self._cancelled = False
        self._buffered_events: List[Dict[str, Any]] = []

        if graph_instance is not None:
            self.graph = graph_instance
        else:
            # Default to the built-in sample customer support graph
            from app.agents.framework_sample_graph import customer_support_graph
            self.graph = customer_support_graph

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates configuration schema for LangGraph agent."""
        framework = config.get("framework", "langgraph")
        if framework != "langgraph":
            return {"valid": False, "error": f"Unsupported framework '{framework}'. Expected 'langgraph'."}
        return {"valid": True, "error": None}

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        self._cancelled = False
        self._buffered_events = []

    def test_connection(self) -> Dict[str, Any]:
        """Inspects graph compilation, registered nodes, and entry points."""
        try:
            node_names = []
            if hasattr(self.graph, "nodes"):
                node_names = list(self.graph.nodes.keys())
            elif hasattr(self.graph, "get_graph"):
                g = self.graph.get_graph()
                node_names = [n.id for n in g.nodes.values()]

            return {
                "status": "healthy",
                "agent_id": self.agent_id,
                "version": self.version,
                "adapter_type": self.adapter_type,
                "observability_level": self.observability_level,
                "framework": "langgraph",
                "nodes": node_names or ["analyze_request", "check_existing", "create_ticket", "finalize"],
                "message": f"LangGraph agent compiled and responsive with {len(node_names)} nodes."
            }
        except Exception as e:
            return {
                "status": "error",
                "adapter_type": self.adapter_type,
                "message": f"LangGraph inspection failed: {str(e)}"
            }

    def run_task(
        self,
        task_input: Any,
        context: Any,
        tool_invoker: Any
    ) -> Dict[str, Any]:
        """
        Executes the LangGraph StateGraph, capturing state transitions as timeline events
        and routing tool invocations through tool_invoker for fault injection.
        """
        self._cancelled = False
        self._buffered_events = []
        start_time = time.perf_counter()

        # Extract prompt
        if hasattr(task_input, "model_dump"):
            inp_dict = task_input.model_dump()
        elif isinstance(task_input, dict):
            inp_dict = task_input
        else:
            inp_dict = {"prompt": str(task_input)}

        prompt = inp_dict.get("prompt") or inp_dict.get("description") or inp_dict.get("task") or str(inp_dict)

        tool_invoker.record_decision(
            action="langgraph_start",
            reasoning=f"Executing LangGraph agent '{self.agent_id}' [Observability: {self.observability_level}]"
        )

        # Create wrapped tool functions that route through AgentGuard's tool_invoker
        def instrumented_create_ticket(title: str, description: str = "", idempotency_key: str = "", **extra):
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

        def instrumented_get_ticket(ticket_id: str):
            return tool_invoker.call_tool(
                tool_name="ticket_get",
                params={"action": "get", "ticket_id": ticket_id}
            )

        def instrumented_query_tickets(query: str):
            return tool_invoker.call_tool(
                tool_name="ticket_query",
                params={"action": "query", "query": query}
            )

        tools_dict = {
            "create_ticket": instrumented_create_ticket,
            "get_ticket_status": instrumented_get_ticket,
            "query_tickets": instrumented_query_tickets,
            "tool_invoker": tool_invoker
        }

        # Prepare initial state
        initial_state = {
            "prompt": prompt,
            "inquiry_type": "general",
            "existing_ticket_id": None,
            "ticket_id": None,
            "status": "started",
            "result": "",
            "steps": [],
            "tools": tools_dict
        }

        try:
            # Stream execution events if graph supports stream, else invoke
            final_state = initial_state
            if hasattr(self.graph, "stream"):
                for output in self.graph.stream(initial_state):
                    if self._cancelled:
                        return {
                            "status": "cancelled",
                            "message": "Graph execution cancelled.",
                            "observability_level": self.observability_level
                        }
                    for node_name, node_update in output.items():
                        # Record node execution in trace
                        ev = {
                            "action": f"langgraph_node_{node_name}",
                            "type": "framework_node",
                            "node": node_name,
                            "output_keys": list(node_update.keys()) if isinstance(node_update, dict) else []
                        }
                        self._buffered_events.append(ev)
                        tool_invoker.recorder.record_event(
                            step_index=tool_invoker.current_step + len(self._buffered_events),
                            event_type="framework_node",
                            action_name=f"langgraph:{node_name}",
                            input_data={"node": node_name},
                            output_data={"keys": list(node_update.keys()) if isinstance(node_update, dict) else []},
                            duration_ms=2.0
                        )
                        if isinstance(node_update, dict):
                            final_state.update(node_update)
            else:
                final_state = self.graph.invoke(initial_state)

            ticket_id = final_state.get("ticket_id") or final_state.get("existing_ticket_id")
            result_msg = final_state.get("result") or f"LangGraph execution finished: {final_state.get('status')}"

            return {
                "status": "success",
                "message": result_msg,
                "ticket_id": ticket_id,
                "steps_executed": len(self._buffered_events),
                "observability_level": self.observability_level,
                "raw_output": {k: v for k, v in final_state.items() if k != "tools"}
            }

        except Exception as e:
            err = sanitize_text(str(e))
            tool_invoker.record_decision(
                action="langgraph_error",
                reasoning=f"LangGraph execution failed: {err}"
            )
            return {
                "status": "failed",
                "error": err,
                "message": f"Graph execution failed: {err}",
                "observability_level": self.observability_level
            }

    def stream_events(self) -> Optional[List[Dict[str, Any]]]:
        return list(self._buffered_events)

    def cancel(self) -> None:
        self._cancelled = True

    def dispose(self) -> None:
        self._buffered_events = []
