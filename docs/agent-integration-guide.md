# AgentGuard Agent Integration Guide

This guide describes how to integrate custom AI agents into AgentGuard using the explicit Agent Adapter Contract.

AgentGuard supports testing external and custom agents against controlled fault injection, deterministic evaluation, diagnosis, and verified repairs. To maintain system security and deterministic test guarantees, AgentGuard does **not** allow arbitrary code uploads or unrestricted execution. All integrations must satisfy the documented `AgentAdapter` contract.

---

## 1. The Agent Adapter Contract

AgentGuard defines an abstract protocol and typed Pydantic models in `backend/app/adapters/`:

### Core Interface (`app.adapters.base.AgentAdapter`)
```python
class AgentAdapter(Protocol):
    agent_id: str
    version: str
    declared_capabilities: List[str]
    supported_tools: List[str]

    def initialize(self, context: AgentExecutionContext) -> None:
        """Initialize the agent with execution context and configuration."""
        ...

    def run_task(
        self,
        task_input: AgentTaskInput,
        tool_invoker: Callable[[ToolCallRequest], ToolCallResult]
    ) -> AgentTaskResult:
        """Execute the agent task using the controlled tool invoker."""
        ...

    def test_connection(self) -> Dict[str, Any]:
        """Test agent initialization, connectivity, or health."""
        ...

    def cancel(self) -> None:
        """Signal safe cancellation to any in-flight execution."""
        ...

    def dispose(self) -> None:
        """Clean up allocated resources, connections, or state."""
        ...
```

### Typed Data Models (`app.adapters.models`)
- **`AgentExecutionContext`**: Contains `run_id`, `agent_id`, `agent_version`, `scenario_id`, `trace_id`, and `config`.
- **`AgentTaskInput`**: Contains `prompt`, `parameters`, `max_steps`, and `timeout_seconds`.
- **`ToolCallRequest`**: Contains `tool_name`, `arguments`, and unique `invocation_id`.
- **`ToolCallResult`**: Contains `invocation_id`, `tool_name`, `success`, `output`, `error`, `error_category`, and `is_fault_injected`.
- **`AgentTaskResult`**: Contains `final_answer`, `status` (`completed`, `failed`, `timeout`, `cancelled`), `steps_executed`, `tool_calls_count`, and `metadata`.

---

## 2. Integration Modes

### Mode A: Python Adapter (In-Process Trusted Adapter)

For agents installed as trusted Python modules or defined in the codebase.

#### Rules & Security Constraints:
- Must be registered in `app.adapters.registry.AgentRegistry`.
- Arbitrary script uploading or dynamic `eval`/`exec` is strictly prohibited.
- Trusted adapters run with the host process permissions; code must be vetted.

#### Step-by-Step Python Implementation:
```python
from typing import Callable, Dict, Any, List
from app.adapters.base import AgentAdapter
from app.adapters.models import (
    AgentExecutionContext,
    AgentTaskInput,
    ToolCallRequest,
    ToolCallResult,
    AgentTaskResult
)

class MyCustomAgent(AgentAdapter):
    def __init__(self, agent_id: str = "custom-agent", version: str = "v1.0.0"):
        self.agent_id = agent_id
        self.version = version
        self.declared_capabilities = ["ticket_creation", "state_inspection", "handle_structured_errors"]
        self.supported_tools = ["create_ticket", "get_ticket_status"]
        self._cancelled = False

    def initialize(self, context: AgentExecutionContext) -> None:
        self.context = context
        self._cancelled = False

    def run_task(
        self,
        task_input: AgentTaskInput,
        tool_invoker: Callable[[ToolCallRequest], ToolCallResult]
    ) -> AgentTaskResult:
        # Step 1: Query state if capable
        status_req = ToolCallRequest(tool_name="get_ticket_status", arguments={"query": "order-123"})
        status_res = tool_invoker(status_req)

        # Step 2: Issue action through controlled invoker
        call_req = ToolCallRequest(
            tool_name="create_ticket",
            arguments={"title": "Custom Ticket", "idempotency_key": "custom-key-1"}
        )
        call_res = tool_invoker(call_req)

        if not call_res.success:
            return AgentTaskResult(
                final_answer="Failed to create ticket: " + str(call_res.error),
                status="failed",
                steps_executed=2,
                tool_calls_count=2
            )

        return AgentTaskResult(
            final_answer=f"Ticket created successfully: {call_res.output}",
            status="completed",
            steps_executed=2,
            tool_calls_count=2
        )

    def test_connection(self) -> Dict[str, Any]:
        return {"status": "ok", "agent_id": self.agent_id, "version": self.version}

    def cancel(self) -> None:
        self._cancelled = True

    def dispose(self) -> None:
        pass
```

Register this class in `AgentRegistry` (`app/adapters/registry.py`):
```python
agent_registry.register_python_adapter("my-custom-agent", MyCustomAgent)
```

---

### Mode B: HTTP Adapter (External Microservice)

For agents running as separate HTTP services.

#### Configuration Schema:
```json
{
  "base_url": "https://agent-service.internal/api/v1",
  "endpoint": "/run",
  "connect_timeout": 5.0,
  "read_timeout": 30.0,
  "secret_env_var": "AGENT_SERVICE_API_KEY",
  "allow_local_dev": false
}
```

#### HTTP Security & SSRF Protection:
- **SSRF Prevention**: All targets are validated against an IP blocklist. Cloud metadata services (`169.254.169.254`, `metadata.google.internal`), multicast (`224.0.0.0/4`), and loopback (`127.0.0.1`, `localhost`) are blocked by default.
- **Local Dev Exception**: `allow_local_dev: true` is strictly permitted only in controlled local test setups.
- **Secret Redaction**: Credentials must be supplied via environment variable references (`secret_env_var`), never stored directly in the database.
- **TLS Verification**: Enforced on all HTTPS calls. Redirects to unauthorized hosts are blocked.

---

## 3. Tool Interception & Fault Injection

AgentGuard achieves controlled reliability testing because **all tool calls must pass through `tool_invoker`**.

When an agent requests a tool call via `tool_invoker(request)`:
1. **Invocation Tracking**: Unique invocation IDs and timestamps are assigned.
2. **Fault Injection**: The `FaultInjector` checks whether the active scenario configures a fault (e.g., `transient_timeout`, `ambiguous_outcome`, `malformed_output`, `prompt_injection`, `policy_violation`).
3. **Execution**: If no fault is triggered or after transient conditions, the mock service executes the tool.
4. **Trace Recording**: Every tool name, argument, output, fault flag, and duration is stored in the immutable execution trace.
5. **Sanitization**: API keys and secrets in inputs/outputs are redacted automatically.

---

## 4. Scenario Compatibility & Capability Declaration

Scenarios declare `required_capabilities` in their definitions:
```json
{
  "scenario_id": "scen-ambiguous-01",
  "name": "Ambiguous Timeout Recovery",
  "required_capabilities": ["ticket_creation", "state_inspection", "handle_structured_errors"]
}
```

Agents declare `declared_capabilities` upon registration:
```json
{
  "agent_id": "agent-custom-order",
  "declared_capabilities": ["ticket_creation", "state_inspection", "handle_structured_errors"]
}
```

### Pre-Run Capability Check:
- AgentGuard verifies that `scenario.required_capabilities ⊆ agent.declared_capabilities`.
- If an agent lacks a required capability:
  - The UI highlights the missing capability and blocks execution.
  - If triggered via API, the runner returns `status="unsupported"` with an explicit `ASSERT_CAPABILITY_SUPPORT` finding.
  - Unsupported scenarios are **never** reported as passed or counted towards reliability benchmarks.

---

---

## 5. Existing Agent Connector & Observability Levels

AgentGuard allows developers to connect their **already-built** AI agents without having to rewrite them to implement AgentGuard's raw `AgentAdapter` interface.

### The Three Execution Observability Levels

AgentGuard distinguishes three clear tiers of observability:

| Observability Level | Description | Capabilities & Fault Injections Supported | Report Guarantees |
| :--- | :--- | :--- | :--- |
| **LEVEL 1 — Result-only** (`level_1_result_only`) | The external agent returns a task result or answer string. Internal steps and tool calls are opaque. | Evaluates final answers, basic prompt injection resistance, and policy adherence. **Cannot** inject or verify tool-level faults. | Output evaluation only. Evaluator findings will explicitly note opaque tool visibility. |
| **LEVEL 2 — Structured-event** (`level_2_structured_events`) | The external agent returns structured execution events, internal tool calls, errors, retries, and step timings in its response payload. | Reconstructs complete execution timeline and step counts. Tool calls are visible in trace viewer for post-hoc inspection. | Full timeline observability, step-count tracking, and error taxonomy verification. Fault injection remains external. |
| **LEVEL 3 — Instrumented-tools** (`level_3_instrumented_tools`) | The agent delegates its tool calls back through AgentGuard's controlled tool registry. | **Full reliability testing**: Injects transient timeouts, duplicate actions, ambiguous outcomes, and malformed outputs. | Comprehensive fault injection, trace coverage, policy verification, and side-effect guarantees. |

### Observability Scenario Compatibility
Before executing a scenario, AgentGuard verifies whether the agent's observability level satisfies the scenario's requirements:
- If a scenario requires tool-level fault injection (`ambiguous_outcome`, `transient_timeout`, `repeated_action`, `malformed_output`, `policy_violation`) but the connected agent provides only **Level 1 (Result-Only)**:
  - The UI flags an observability mismatch and disables run execution.
  - If executed via API or batch, the runner sets `status="unsupported"` with finding `ASSERT_OBSERVABILITY_COMPATIBILITY`.
  - **Unsupported tests are never counted as passing.**

---

## 6. Connection Methods for Existing Agents

### A. HTTP Agent Endpoint
Connect any REST / HTTP-based agent microservice.

#### Configurable Fields:
- `base_url`: Base URL of the agent (e.g., `http://127.0.0.1:8080/api`).
- `health_endpoint`: Optional health-check path (default: `/health`).
- `invocation_endpoint`: Task execution path (default: `/run`).
- `auth_type`: `None`, `Bearer`, `ApiKey-Header`, `Basic`, or `Custom`.
- `secret_env_var`: Name of the environment variable storing credentials (redacted from all logs/traces).
- `connect_timeout` & `read_timeout`: Timeout limits in seconds.
- `request_mapping`: Map AgentGuard task fields (`prompt`, `context`, `parameters`, `max_steps`) to the agent's expected body structure.
- `response_mapping`: Dot-notation extractors:
  - `result_path`: Dot path to final answer (e.g., `data.answer` or `response.result`).
  - `status_path`: Dot path to status string (e.g., `data.status`).
  - `events_path`: Dot path to structured event list for Level 2 observability (e.g., `data.timeline`).
  - `error_path`: Dot path to error details.

### B. Python SDK Adapter Wrapper (`CallableAgentWrapper`)
Wrap existing Python functions, LangChain chains, or custom agent objects without altering their code.

#### Example Existing Function:
```python
# Standalone agent with ZERO AgentGuard imports:
def legacy_ticket_solver(prompt: str, tools: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if tools and "create_ticket" in tools:
        # Calls the passed-in tool function directly
        res = tools["create_ticket"](title="Help Ticket", idempotency_key="key-123")
        return {"output": "Resolved", "tool_result": res}
    return {"output": f"Answered: {prompt}"}
```

#### Wrapping via `CallableAgentWrapper`:
```python
from app.adapters.wrappers import CallableAgentWrapper
from app.adapters.registry import agent_registry

# Wrap the callable for Level 3 tool-instrumented execution
wrapped_adapter = CallableAgentWrapper(
    target=legacy_ticket_solver,
    agent_id="legacy-support-bot",
    version="v1.2.0",
    observability_level="level_3_instrumented_tools",
    declared_capabilities=["ticket_creation", "state_inspection", "handle_structured_errors"],
    supported_tools=["create_ticket", "get_ticket_status"]
)

# Register into the Agent Registry
agent_registry.register_adapter("legacy-support-bot", wrapped_adapter)
```

---

## 7. Connecting an Existing Agent in the UI

1. Open **Agents** in the AgentGuard navigation.
2. Click **⚡ Connect Existing Agent**.
3. Choose your method:
   - **HTTP Endpoint**: Set base URL, endpoints, auth headers, and JSON path mappings.
   - **Python SDK Wrapper**: Select a registered Python function or module and specify observability level.
   - **Integration Contract**: Review the contract specification and code samples for future frameworks.
4. Select the appropriate **Observability Level** (Result-Only, Structured-Events, or Instrumented-Tools).
5. Click **Validate Configuration** to ensure schemas, timeouts, and SSRF restrictions are satisfied.
6. Click **Test Connectivity** to perform an immediate live handshake.
7. Click **Connect Agent** to save.

---

## 9. Connection Type C — Agent Frameworks

AgentGuard provides first-class support for compiled agent framework workflows behind the unified adapter interface.

### Implemented Framework: LangGraph (`langgraph_adapter.py`)
- **Compatibility**: LangGraph v0.2+ and v1.0+ (`StateGraph`).
- **Architecture**:
  - Compiles state machines with typed state dictionaries.
  - Supports streaming node executions via `stream_events()`.
  - Captures node-level transitions and records them in the AgentGuard execution timeline (`framework_node`).
  - Routes node-initiated tool calls directly through AgentGuard's `ToolInvoker`, enabling full Level 3 tool fault injection on LangGraph agents.
- **Sample Agent**: `customer_support_graph` (`backend/app/agents/framework_sample_graph.py`)
  - Nodes: `analyze_request -> check_existing -> create_ticket -> finalize`.

### Planned Framework Roadmap (Not Advertised as Ready)
- **CrewAI**: Multi-agent task execution and delegation. Adapter architecture designed; planned for next release.
- **AutoGen**: Multi-agent conversational patterns. Adapter contract designed; planned for future release.

---

## 10. Connection Type D — Model-Backed Agents

AgentGuard supports testing LLM-driven agents built directly on top of OpenAI-compatible chat completion endpoints.

### Architecture & Security Rules:
1. **Separation of Concerns**: Model provider logic (`BaseLlmProvider`, `OpenAiCompatibleProvider`) is isolated from agent orchestration (`ModelBackedAgentAdapter`).
2. **Strict Tool Allowlist**: The model can NEVER invoke arbitrary system tools. Allowed tools are strictly constrained (`create_ticket`, `get_ticket_status`, `query_tickets`). Any unauthorized tool call proposed by the model is blocked and recorded in the trace.
3. **Controlled Tool Dispatcher**: Tool calls from the model are routed through AgentGuard's `ToolInvoker`, ensuring all six fault categories (`transient_timeout`, `ambiguous_outcome`, `malformed_output`, `repeated_action`, `prompt_injection`, `policy_violation`) are injected transparently.
4. **Execution Boundaries**: Bounded execution enforced via `max_model_calls` (default 5), `max_tool_calls` (default 5), and `request_timeout_seconds`.
5. **No Hardcoded Credentials**: API keys are accessed strictly via environment variable references (`secret_env_var`). Missing keys report actionable `unconfigured` status instead of false success or crashes.
6. **Zero External Cost for MVP**: The deterministic built-in sample agent and mock modes continue to run without requiring paid API keys.

---

## 11. Universal Agent Connection Wizard (UI)

The Agents page includes a 5-step interactive wizard:
1. **Choose Connection Type**:
   - Existing Python Project (Callable Wrapper)
   - HTTP / API Endpoint
   - Agent Framework (LangGraph ready, CrewAI/AutoGen catalog)
   - Model-Backed Agent (OpenAI-compatible)
2. **Configure Connection**: Dynamically adapts input fields to the chosen connection type with sensible defaults and secret references.
3. **Validate & Test Connection**: Runs configuration validation and a live connectivity probe, displaying verified capabilities and observability level.
4. **Scenario Compatibility Preview**: Compares declared capabilities and observability level against benchmark scenarios, flagging any missing capabilities or tool fault mismatches.
5. **Register & Execute**: Persists the configured connection to the database and allows immediate benchmark execution.


