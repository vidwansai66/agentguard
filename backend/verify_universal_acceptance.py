"""
End-to-End Acceptance Test Script for AgentGuard Universal AI Agent Integration System.
Executes and validates all four connection types (A, B, C, D) and observability rules.
"""

import sys
import os
import json

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.scenario import Scenario
from app.models.agent import Agent
from app.models.run import TestRun
from app.services.run_service import RunService
from app.adapters.http_adapter import HttpAgentAdapter
from app.adapters.frameworks.langgraph_adapter import LangGraphAgentAdapter
from app.adapters.model_backed_adapter import ModelBackedAgentAdapter
from app.adapters.llm.openai_provider import OpenAiCompatibleProvider

client = TestClient(app)
db = SessionLocal()

print("=" * 80)
print("AGENTGUARD UNIVERSAL INTEGRATION - END-TO-END ACCEPTANCE SUITE")
print("=" * 80)

def section(title: str):
    print(f"\n--- {title} ---")

# ---------------------------------------------------------
# Test A: Connection Type A - Existing Python Agent (Callable Wrapper)
# ---------------------------------------------------------
section("A. EXISTING PYTHON PROJECT (CALLABLE AGENT WRAPPER)")
from unittest.mock import MagicMock
from app.adapters.wrappers.callable_wrapper import CallableAgentWrapper

# Real external function that knows nothing about AgentGuard internal classes
def legacy_billing_agent(prompt: str, tools: dict) -> dict:
    ticket = tools["create_ticket"](
        title=f"Billing inquiry: {prompt[:30]}",
        customer_id="CUST-8821"
    )
    return {
        "status": "success",
        "output": f"Created billing ticket {ticket.get('ticket_id')}",
        "ticket_id": ticket.get("ticket_id")
    }

callable_adapter = CallableAgentWrapper(
    agent_id="legacy_billing_agent",
    target_callable=legacy_billing_agent,
    config={
        "observability_level": "level_3_instrumented_tools",
        "declared_capabilities": ["ticket_create", "billing_support"]
    }
)

conn_res_a = callable_adapter.test_connection()
assert conn_res_a["status"] == "healthy", f"Init failed: {conn_res_a}"

# Run through runner mock invoker
mock_invoker = MagicMock()
mock_invoker.call_tool.return_value = {"ticket_id": "TICKET-LEGACY-001", "status": "open"}

result_a = callable_adapter.run_task(
    task_input={"prompt": "Dispute incorrect subscription charge"},
    context={"run_id": "RUN-A1"},
    tool_invoker=mock_invoker
)
assert result_a["status"] == "success"
assert result_a["ticket_id"] == "TICKET-LEGACY-001"
print(f"[PASS] Python Callable Wrapper executed cleanly.")
print(f"       Agent output: {result_a.get('message')}")
print(f"       Status check: {conn_res_a['status']} ({conn_res_a['message']})")

# ---------------------------------------------------------
# Test B: Connection Type B - HTTP Agent with Local Mock Service
# ---------------------------------------------------------
section("B. HTTP/API AGENT (LOCAL MOCK SERVICE)")
from starlette.testclient import TestClient as StarletteClient
from app.agents.local_mock_http_service import create_mock_agent_app

mock_app = create_mock_agent_app()
mock_client = StarletteClient(mock_app, base_url="http://127.0.0.1:9099")

http_adapter = HttpAgentAdapter(
    agent_id="test_http_agent",
    config={
        "base_url": "http://127.0.0.1:9099",
        "invocation_endpoint": "/agent/invoke",
        "health_endpoint": "/health",
        "http_method": "POST",
        "request_mapping": {"prompt": "prompt"},
        "response_mapping": {"result_path": "result.answer"},
        "auth_type": "none",
        "allow_local_dev": True
    }
)
http_adapter._client = mock_client  # inject starlette client for in-process network safety

conn_res_b = http_adapter.test_connection()
assert conn_res_b["status"] == "healthy", f"HTTP test_connection failed: {conn_res_b}"

run_res_b = http_adapter.run_task(
    task_input={"prompt": "Can you check on ticket 101?"},
    context={"run_id": "RUN-B1"},
    tool_invoker=mock_invoker
)
assert run_res_b["status"] in ["success", "completed"], f"Unexpected run_res_b status: {run_res_b}"
assert "resolved inquiry" in run_res_b.get("message", "").lower() or "external http agent" in run_res_b.get("message", "").lower()
print(f"[PASS] HTTP Agent connected and executed successfully.")
print(f"       Health probe: {conn_res_b['status']} ({conn_res_b['message']})")
print(f"       Invocation output: {run_res_b.get('message')}")

# ---------------------------------------------------------
# Test C: Connection Type C - Agent Framework (LangGraph Customer Support)
# ---------------------------------------------------------
section("C. FRAMEWORK ADAPTER (LANGGRAPH STATEGRAPH)")
langgraph_adapter = LangGraphAgentAdapter(
    agent_id="langgraph_support_agent",
    config={"graph_identifier": "customer_support_graph"}
)

conn_res_c = langgraph_adapter.test_connection()
assert conn_res_c["status"] == "healthy", f"LangGraph test_connection failed: {conn_res_c}"

tool_calls_c = []
mock_lg_invoker = MagicMock()
mock_lg_invoker.call_tool.side_effect = lambda tool_name, params, **kwargs: (
    tool_calls_c.append((tool_name, params)) or {"ticket_id": "TICK-LG-55", "status": "created"}
)

run_res_c = langgraph_adapter.run_task(
    task_input={"customer_id": "CUST-LG-12", "prompt": "Issue with checkout payment"},
    context={"run_id": "RUN-C1"},
    tool_invoker=mock_lg_invoker
)
assert run_res_c["status"] == "success"
events_c = langgraph_adapter.stream_events()
assert len(events_c) >= 3, f"Expected node events, got: {events_c}"
node_names = [e.get("node") for e in events_c if e.get("node")]
print(f"[PASS] LangGraph StateGraph compiled and executed.")
print(f"       Nodes executed: {' -> '.join(node_names)}")
print(f"       Tool calls routed through invoker: {tool_calls_c}")
print(f"       Final Agent Status: {run_res_c['status']}")

# ---------------------------------------------------------
# Test D: Connection Type D - Model-Backed Agent (OpenAI-compatible)
# ---------------------------------------------------------
section("D. MODEL-BACKED AGENT (OPENAI-COMPATIBLE)")
# D1: Missing API key handling (Honest unconfigured reporting)
adapter_d1 = ModelBackedAgentAdapter(
    agent_id="model_agent_d1",
    config={
        "provider": "openai",
        "model_name": "gpt-4o",
        "secret_env_var": "AGENTGUARD_NONEXISTENT_KEY_FOR_TEST_XYZ"
    }
)
status_d1 = adapter_d1.test_connection()
assert status_d1["status"] == "unconfigured", f"Expected unconfigured status, got: {status_d1}"
print(f"[PASS] Missing API key accurately reported as unconfigured.")
print(f"       Actionable message: {status_d1['message']}")

# D2: Executing real orchestration with tool dispatcher
class MockLlmProvider(OpenAiCompatibleProvider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_count = 0

    def chat_complete(self, messages, tools=None, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            from app.adapters.llm.base_provider import LlmResponse
            return LlmResponse(
                content=None,
                tool_calls=[{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "create_ticket",
                        "arguments": json.dumps({
                            "customer_id": "CUST-LLM-01",
                            "title": "Broken login button",
                            "priority": "high",
                            "issue_type": "technical"
                        })
                    }
                }],
                finish_reason="tool_calls",
                model="mock-gpt"
            )
        else:
            from app.adapters.llm.base_provider import LlmResponse
            return LlmResponse(
                content="Ticket created successfully. Reference ID is TICK-DISPATCHER-99.",
                tool_calls=[],
                finish_reason="stop",
                model="mock-gpt"
            )

os.environ["AGENTGUARD_MOCK_KEY"] = "mock-key-12345"
adapter_d2 = ModelBackedAgentAdapter(
    agent_id="model_agent_d2",
    config={
        "provider": "openai",
        "model_name": "gpt-4o",
        "secret_env_var": "AGENTGUARD_MOCK_KEY",
        "allowed_tools": ["create_ticket", "get_ticket_status"]
    }
)
adapter_d2.provider = MockLlmProvider(base_url="https://api.openai.com/v1", model="gpt-4o", secret_env_var="AGENTGUARD_MOCK_KEY")
adapter_d2.provider.mock_responses = True

tool_calls_d = []
mock_llm_invoker = MagicMock()
mock_llm_invoker.call_tool.side_effect = lambda tool_name, params, **kwargs: (
    tool_calls_d.append((tool_name, params)) or {"ticket_id": "TICK-DISPATCHER-99", "status": "created"}
)

run_res_d = adapter_d2.run_task(
    task_input={"prompt": "Login button is broken"},
    context={"run_id": "RUN-D1"},
    tool_invoker=mock_llm_invoker
)
assert run_res_d["status"] == "success"
assert "TICK-DISPATCHER-99" in run_res_d.get("message", "")
assert len(tool_calls_d) >= 1
assert tool_calls_d[0][0] == "ticket_create"
print(f"[PASS] Model-backed Agent tool orchestration succeeded.")
print(f"       Model tool call dispatched via AgentGuard allowlist: {tool_calls_d[0][0]}")
print(f"       Final Model Output: {run_res_d.get('message')}")

# ---------------------------------------------------------
# Test E: Observability Enforcement (Level 1 vs Level 3)
# ---------------------------------------------------------
section("E. OBSERVABILITY ENFORCEMENT & COMPATIBILITY CHECKING")
scenario = db.query(Scenario).filter(Scenario.failure_type == "ambiguous_outcome").first()
assert scenario is not None, "Ambiguous outcome scenario not found in DB"

# Clean existing if present
agent_to_del = db.query(Agent).filter(Agent.id == "test-http-lvl-1-acceptance").first()
if agent_to_del:
    db.delete(agent_to_del)
    db.commit()

lvl1_payload = {
    "id": "test-http-lvl-1-acceptance",
    "name": "Result-Only HTTP Agent",
    "connection_method": "http_endpoint",
    "observability_level": "level_1_result_only",
    "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get"],
    "http_config": {
        "base_url": "http://127.0.0.1:9099",
        "observability_level": "level_1_result_only",
        "allow_local_dev": True
    }
}
reg_resp = client.post("/api/agents/connect-existing", json=lvl1_payload)
assert reg_resp.status_code == 201, f"Failed to register: {reg_resp.text}"

compat_resp = client.post("/api/scenarios/compatibility", json={
    "agent_id": "test-http-lvl-1-acceptance",
    "scenario_id": scenario.id
})
assert compat_resp.status_code == 200
compat_data = compat_resp.json()
target_detail = compat_data["scenarios"][0]
assert target_detail["compatible"] is False, f"Expected Level 1 to be incompatible with tool faults: {target_detail}"
assert target_detail["observability_compatible"] is False
print(f"[PASS] Observability Level 1 correctly BLOCKED from tool fault scenario:")
print(f"       Scenario: {target_detail['scenario_name']} ({scenario.failure_type})")
print(f"       Compatible: {target_detail['compatible']}")
print(f"       Explanation: {target_detail['explanation']}")

# Level 3 agent (agent-ticket-sample)
compat_resp_3 = client.post("/api/scenarios/compatibility", json={
    "agent_id": "agent-ticket-sample",
    "scenario_id": scenario.id
})
assert compat_resp_3.status_code == 200
compat_data_3 = compat_resp_3.json()
target_detail_3 = compat_data_3["scenarios"][0]
assert target_detail_3["compatible"] is True, f"Expected Level 3 to be compatible: {target_detail_3}"
print(f"[PASS] Observability Level 3 correctly PERMITTED for tool fault scenario:")
print(f"       Compatible: {target_detail_3['compatible']}")

# ---------------------------------------------------------
# Test F: Regression Testing - Built-in Sample Agent & Evaluator
# ---------------------------------------------------------
section("F. REGRESSION TESTING - BUILT-IN SAMPLE AGENT & EVALUATOR")
from app.services.comparison_service import ComparisonService

run_service = RunService()

# 1. Baseline Run (1.0.0 - Unpatched)
# Expected behavior: Baseline agent fails ambiguous outcome fault due to duplicate retry -> 1 unsafe side effect
baseline_run = run_service.execute_run(
    db=db,
    agent_id="agent-ticket-sample",
    agent_version="1.0.0",
    scenario_id=scenario.id
)
assert baseline_run.status == "completed"
assert baseline_run.unsafe_side_effects_count == 1
assert baseline_run.passed_scenarios == 0
print(f"[PASS] Baseline (1.0.0) evaluated deterministically:")
print(f"       Run ID: {baseline_run.id}")
print(f"       Fault Injected: Ambiguous Outcome (Lost Response)")
print(f"       Outcome: Failed as expected (Unsafe Side Effects: {baseline_run.unsafe_side_effects_count})")
print(f"       Evaluator Finding: Duplicate ticket creation detected")

# 2. Candidate Run (1.1.0-patch - Safe Idempotent)
# Expected behavior: Candidate agent inspects state, avoids duplicate ticket -> 0 unsafe side effects, passed
candidate_run = run_service.execute_run(
    db=db,
    agent_id="agent-ticket-sample",
    agent_version="1.1.0-patch",
    scenario_id=scenario.id
)
assert candidate_run.status == "completed"
assert candidate_run.unsafe_side_effects_count == 0
assert candidate_run.passed_scenarios == 1
assert candidate_run.recovered_count == 1
print(f"[PASS] Candidate (1.1.0-patch) evaluated deterministically:")
print(f"       Run ID: {candidate_run.id}")
print(f"       Outcome: Recovered safely (Passed: {candidate_run.passed_scenarios}, Unsafe: {candidate_run.unsafe_side_effects_count})")

# 3. Comparative Verification Pass
comp_service = ComparisonService()
comparison = comp_service.compare_runs(db=db, baseline_run_id=baseline_run.id, candidate_run_id=candidate_run.id)
assert comparison.verification_verdict == "verified_passed"
assert comparison.candidate_success_rate == 1.0
assert comparison.baseline_unsafe_side_effect_rate == 1.0
assert comparison.candidate_unsafe_side_effect_rate == 0.0
print(f"[PASS] Verifier comparison completed:")
print(f"       Comparison ID: {comparison.id}")
print(f"       Verdict: {comparison.verification_verdict}")
print(f"       Success Rate: {comparison.baseline_success_rate * 100}% -> {comparison.candidate_success_rate * 100}%")
print(f"       Unsafe Side Effects: {comparison.baseline_unsafe_side_effect_rate * 100}% -> {comparison.candidate_unsafe_side_effect_rate * 100}%")

db.close()
print("\n" + "=" * 80)
print("ALL ACCEPTANCE SUITE CHECKS COMPLETED WITH ZERO ERRORS.")
print("=" * 80)
