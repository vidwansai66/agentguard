import os
import json
import time
from typing import Any, Dict, List, Optional
from app.adapters.base import AgentAdapter
from app.adapters.models import (
    AgentTaskInput,
    AgentExecutionContext,
    AgentTaskResult,
    ToolCallRequest,
    ToolCallResult
)
from app.adapters.llm.base_provider import BaseLlmProvider, LlmMessage
from app.adapters.llm.openai_provider import OpenAiCompatibleProvider
from app.tracing.sanitizer import sanitize_text

# Standard allowed tools exposed to model-backed agents
SUPPORTED_MODEL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Create a customer support ticket in the ticketing system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the ticket"},
                    "description": {"type": "string", "description": "Details about the user inquiry"},
                    "idempotency_key": {"type": "string", "description": "Unique key to prevent duplicate ticket creation"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket_status",
            "description": "Retrieve status of a ticket by ticket_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket ID to look up"}
                },
                "required": ["ticket_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_tickets",
            "description": "Search existing tickets matching keywords or customer criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query terms"}
                },
                "required": ["query"]
            }
        }
    }
]

ALLOWED_TOOL_NAMES = {"create_ticket", "get_ticket_status", "query_tickets"}

class ModelBackedAgentAdapter(AgentAdapter):
    """
    Model-backed agent adapter.
    Orchestrates an LLM conversation using an OpenAI-compatible provider.
    Enforces a strict tool allowlist and routes all tool invocations through
    AgentGuard's ToolInvoker for controlled fault injection.
    """
    adapter_type: str = "model_backed"

    def __init__(
        self,
        agent_id: str,
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
        self.supported_tools = list(ALLOWED_TOOL_NAMES)

        self.model = self.config.get("model", "gpt-4o-mini")
        self.base_url = self.config.get("base_url", "https://api.openai.com/v1")
        self.secret_env_var = self.config.get("secret_env_var") or self.config.get("api_key_env_var") or "OPENAI_API_KEY"
        self.request_timeout = float(self.config.get("request_timeout_seconds", 30.0))
        self.max_model_calls = int(self.config.get("max_model_calls", 5))
        self.max_tool_calls = int(self.config.get("max_tool_calls", 5))
        self.temperature = float(self.config.get("temperature", 0.0))
        self.max_tokens = int(self.config.get("max_tokens", 1024))
        self.system_prompt = self.config.get(
            "system_prompt",
            "You are an AI support agent for a ticketing system. Use the provided tools to inspect and create tickets. "
            "Always verify if a ticket already exists before creating a duplicate, and always provide an idempotency_key when creating a ticket."
        )

        mock_responses = self.config.get("mock_responses")
        self.provider: BaseLlmProvider = OpenAiCompatibleProvider(
            base_url=self.base_url,
            model=self.model,
            secret_env_var=self.secret_env_var,
            max_retries=int(self.config.get("max_retries", 2)),
            mock_responses=mock_responses
        )
        self._cancelled = False

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validates configuration schema and security rules for model-backed agents."""
        base_url = config.get("base_url", "https://api.openai.com/v1")
        if not base_url.startswith(("http://", "https://")):
            return {"valid": False, "error": "base_url must use http or https scheme."}

        secret_var = config.get("secret_env_var", "OPENAI_API_KEY")
        if not secret_var or not secret_var.replace("_", "").isalnum():
            return {"valid": False, "error": "secret_env_var must be a valid environment variable name."}

        max_calls = config.get("max_model_calls", 5)
        if not isinstance(max_calls, int) or max_calls < 1 or max_calls > 20:
            return {"valid": False, "error": "max_model_calls must be an integer between 1 and 20."}

        return {"valid": True, "error": None}

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        self._cancelled = False

    def test_connection(self) -> Dict[str, Any]:
        """Tests provider connectivity and checks API key configuration."""
        provider_test = self.provider.test_connection()
        return {
            "status": provider_test.get("status", "healthy"),
            "agent_id": self.agent_id,
            "version": self.version,
            "adapter_type": self.adapter_type,
            "observability_level": self.observability_level,
            "model": self.model,
            "provider": "openai_compatible",
            "base_url": self.base_url,
            "secret_env_var": self.secret_env_var,
            "message": provider_test.get("message", "Model provider connection tested.")
        }

    def run_task(
        self,
        task_input: Any,
        context: Any,
        tool_invoker: Any
    ) -> Dict[str, Any]:
        """
        Executes bounded multi-turn conversation loop:
        1. Sends prompt to LLM with allowed tools.
        2. Dispatches tool calls through tool_invoker (where fault injection occurs).
        3. Returns tool results to LLM until completion or limits reached.
        """
        self._cancelled = False
        start_time = time.perf_counter()

        # Check API key unless in mock mode
        if not getattr(self.provider, "mock_responses", None):
            api_key = os.environ.get(self.secret_env_var) if self.secret_env_var else None
            if not api_key:
                tool_invoker.record_decision(
                    action="model_execution_skipped",
                    reasoning=f"API key environment variable '{self.secret_env_var}' is not configured."
                )
                return {
                    "status": "unsupported",
                    "error": f"API key environment variable '{self.secret_env_var}' is not configured. Please set {self.secret_env_var} to run live model-backed tasks.",
                    "message": "Model execution skipped: missing API key.",
                    "observability_level": self.observability_level
                }

        # Extract task prompt
        if hasattr(task_input, "model_dump"):
            inp_dict = task_input.model_dump()
        elif isinstance(task_input, dict):
            inp_dict = task_input
        else:
            inp_dict = {"prompt": str(task_input)}

        prompt = inp_dict.get("prompt") or inp_dict.get("description") or inp_dict.get("task") or str(inp_dict)

        messages: List[LlmMessage] = [
            LlmMessage(role="system", content=self.system_prompt),
            LlmMessage(role="user", content=prompt)
        ]

        tool_invoker.record_decision(
            action="model_run_start",
            reasoning=f"Beginning model-backed agent loop with model='{self.model}' [Observability: {self.observability_level}]"
        )

        model_calls_count = 0
        total_tool_calls = 0
        final_answer = ""
        last_ticket_id = None
        has_error = False
        error_msg = None

        while model_calls_count < self.max_model_calls:
            if self._cancelled:
                return {
                    "status": "cancelled",
                    "message": "Execution cancelled by user.",
                    "observability_level": self.observability_level
                }

            model_calls_count += 1
            try:
                # LLM request
                response = self.provider.chat_complete(
                    messages=messages,
                    tools=SUPPORTED_MODEL_TOOLS,
                    tool_choice="auto",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=self.request_timeout
                )
            except Exception as e:
                has_error = True
                error_msg = sanitize_text(str(e))
                tool_invoker.record_decision(
                    action="model_call_error",
                    reasoning=f"Model call failed: {error_msg}"
                )
                break

            # If model returned text output
            if response.content:
                final_answer = response.content

            # Check for tool calls
            if not response.tool_calls:
                # Model finished its turn without tool calls
                break

            # Model wants to call tools
            assistant_msg = LlmMessage(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls
            )
            messages.append(assistant_msg)

            for t_call in response.tool_calls:
                total_tool_calls += 1
                if total_tool_calls > self.max_tool_calls:
                    tool_invoker.record_decision(
                        action="tool_limit_reached",
                        reasoning=f"Max tool calls ({self.max_tool_calls}) exceeded."
                    )
                    break

                t_id = t_call.get("id", f"call_{total_tool_calls}")
                fn_obj = t_call.get("function", {})
                fn_name = fn_obj.get("name", "")
                raw_args = fn_obj.get("arguments", "{}")

                # Parse arguments
                try:
                    if isinstance(raw_args, str):
                        fn_args = json.loads(raw_args)
                    else:
                        fn_args = raw_args
                except Exception:
                    fn_args = {"raw": raw_args}

                # Tool Allowlist Enforcement
                if fn_name not in ALLOWED_TOOL_NAMES:
                    tool_invoker.record_decision(
                        action="unauthorized_tool_call_blocked",
                        reasoning=f"Tool '{fn_name}' is not in allowed tools: {ALLOWED_TOOL_NAMES}"
                    )
                    messages.append(LlmMessage(
                        role="tool",
                        name=fn_name,
                        tool_call_id=t_id,
                        content=json.dumps({"error": f"Tool '{fn_name}' is not permitted."})
                    ))
                    continue

                # Tool Dispatcher routes through tool_invoker (Fault Injection occurs here!)
                if fn_name == "create_ticket":
                    tool_result = tool_invoker.call_tool(
                        tool_name="ticket_create",
                        params={
                            "action": "create",
                            "title": fn_args.get("title", "Support Request"),
                            "description": fn_args.get("description", ""),
                            "idempotency_key": fn_args.get("idempotency_key", f"model-key-{total_tool_calls}"),
                            "priority": fn_args.get("priority", "medium")
                        }
                    )
                    if isinstance(tool_result, dict):
                        if tool_result.get("ticket_id"):
                            last_ticket_id = tool_result.get("ticket_id")
                        elif tool_result.get("data", {}).get("ticket_id"):
                            last_ticket_id = tool_result["data"]["ticket_id"]

                elif fn_name == "get_ticket_status":
                    tool_result = tool_invoker.call_tool(
                        tool_name="ticket_get",
                        params={
                            "action": "get",
                            "ticket_id": fn_args.get("ticket_id", "")
                        }
                    )

                elif fn_name == "query_tickets":
                    tool_result = tool_invoker.call_tool(
                        tool_name="ticket_query",
                        params={
                            "action": "query",
                            "query": fn_args.get("query", "")
                        }
                    )
                else:
                    tool_result = {"error": f"Unknown tool: {fn_name}"}

                # Feed sanitized tool result back to the model conversation
                clean_tool_result = sanitize_text(json.dumps(tool_result, default=str))
                messages.append(LlmMessage(
                    role="tool",
                    name=fn_name,
                    tool_call_id=t_id,
                    content=clean_tool_result
                ))

        if has_error:
            return {
                "status": "failed",
                "error": error_msg,
                "message": f"Execution failed: {error_msg}",
                "ticket_id": last_ticket_id,
                "observability_level": self.observability_level
            }

        return {
            "status": "success",
            "message": final_answer or "Task completed by model-backed agent.",
            "ticket_id": last_ticket_id,
            "model_calls": model_calls_count,
            "tool_calls": total_tool_calls,
            "observability_level": self.observability_level
        }

    def cancel(self) -> None:
        self._cancelled = True

    def dispose(self) -> None:
        pass
