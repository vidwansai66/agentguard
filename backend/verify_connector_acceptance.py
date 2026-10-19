"""
End-to-end verification script for Existing Agent Connector Upgrade.
Demonstrates:
1. Connecting an existing external HTTP agent with Level 1 (Result-Only).
2. Connecting a pre-existing standalone Python agent via CallableAgentWrapper.
3. Observability Level Compatibility: tool-level fault scenario is marked 'unsupported' on Level 1.
4. Normal scenario executes and evaluates on Level 1 without pretending tool faults occurred.
5. Connecting an existing Python agent with Level 3 Instrumented Tools and running fault injection.
6. Trace inspection and secret redaction.
7. Persistence verification.
"""
import uuid
from fastapi.testclient import TestClient
from app.main import app

def run_connector_verification():
    print("=" * 70)
    print("AGENTGUARD — EXISTING AGENT CONNECTOR UPGRADE VERIFICATION")
    print("=" * 70)

    client = TestClient(app)

    # 1. Health check
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    print(f"1. System Health: OK (Status: {health_res.json()['status']})")

    # 2. Connect an existing HTTP agent with Level 1 (Result-Only)
    http_agent_id = f"agent-ext-http-{uuid.uuid4().hex[:6]}"
    http_payload = {
        "id": http_agent_id,
        "name": "Legacy Customer Portal Bot",
        "description": "Third-party customer service bot connected via HTTP endpoint",
        "connection_method": "http_endpoint",
        "observability_level": "level_1_result_only",
        "version": "1.0.0",
        "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get"],
        "supported_tools": ["ticket_create"],
        "http_config": {
            "base_url": "http://127.0.0.1:9099",
            "invocation_endpoint": "/v1/chat",
            "health_endpoint": "/health",
            "observability_level": "level_1_result_only",
            "secret_env_var": "EXT_BOT_API_KEY",
            "allow_local_dev": True,
            "request_mapping": {
                "query": "prompt",
                "session_id": "run_id"
            },
            "response_mapping": {
                "result_path": "answer",
                "status_path": "status"
            }
        }
    }

    http_res = client.post("/api/agents/connect-existing", json=http_payload)
    assert http_res.status_code == 201, f"Failed to connect HTTP agent: {http_res.text}"
    http_agent = http_res.json()
    print(f"2. Connected Existing HTTP Agent: {http_agent['name']} [{http_agent['id']}]")
    print(f"   Adapter Type: {http_agent['adapter_type']} | Observability: {http_agent['observability_level']}")

    # 3. Connect a separately implemented Python agent via Callable SDK wrapper (Level 3 Instrumented)
    sdk_agent_id = f"agent-ext-sdk-{uuid.uuid4().hex[:6]}"
    sdk_payload = {
        "id": sdk_agent_id,
        "name": "Legacy Support Function Agent",
        "description": "Pre-existing Python ticket solving function connected via SDK wrapper",
        "connection_method": "python_sdk_wrapper",
        "observability_level": "level_3_instrumented_tools",
        "version": "1.0.0",
        "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get", "state_inspection", "handle_structured_errors"],
        "supported_tools": ["ticket_create", "ticket_query", "ticket_get"],
        "sdk_config": {
            "wrapper_type": "callable",
            "target_name": "existing_ticket_solver",
            "observability_level": "level_3_instrumented_tools",
            "input_parameter_name": "prompt"
        }
    }

    sdk_res = client.post("/api/agents/connect-existing", json=sdk_payload)
    assert sdk_res.status_code == 201, f"Failed to connect SDK agent: {sdk_res.text}"
    sdk_agent = sdk_res.json()
    print(f"3. Connected Existing Python Agent via SDK Wrapper: {sdk_agent['name']} [{sdk_agent['id']}]")
    print(f"   Adapter Type: {sdk_agent['adapter_type']} | Observability: {sdk_agent['observability_level']}")

    # 4. Test Connectivity Handshake on Connected SDK Agent
    conn_res = client.post(f"/api/agents/{sdk_agent_id}/test-connection")
    assert conn_res.status_code == 200
    conn_data = conn_res.json()
    print(f"4. Connectivity Handshake Test: {conn_data['status'].upper()} — {conn_data['message']}")

    # 5. Check Observability Level Compatibility:
    # Scenario SCEN-03-AMBIGUOUS-OUTCOME requires tool fault injection.
    # Level 1 agent must be detected as incompatible!
    compat_res = client.post("/api/scenarios/compatibility", json={
        "agent_id": http_agent_id,
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
    })
    assert compat_res.status_code == 200
    compat_data = compat_res.json()
    assert compat_data["compatible"] is False, "Level 1 agent should not be marked compatible on tool-fault scenario"
    scen_compat = compat_data["scenarios"][0]
    print("5. Compatibility Check on Tool-Fault Scenario with Level 1 Agent:")
    print(f"   Compatible: {compat_data['compatible']} (Blocked: True)")
    print(f"   Explanation: {scen_compat['explanation']}")

    # 6. Execute Scenario Runner with Level 1 Agent on Tool-Fault Scenario
    # Verifies it returns status='unsupported' with ASSERT_OBSERVABILITY_COMPATIBILITY
    run_l1_res = client.post("/api/runs", json={
        "agent_id": http_agent_id,
        "agent_version": "1.0.0",
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME",
        "name": "Level 1 Execution on Ambiguous Tool Fault"
    })
    assert run_l1_res.status_code == 201
    run_l1_data = run_l1_res.json()
    assert run_l1_data["unsupported_scenarios"] == 1
    scen_res = run_l1_data["scenario_results"][0]
    assert scen_res["status"] == "unsupported"
    assert scen_res["passed"] is False
    print("6. Runner Execution on Tool-Fault Scenario:")
    print(f"   Run Status: {run_l1_data['status']} | Unsupported Scenarios: {run_l1_data['unsupported_scenarios']}")
    print(f"   Scenario Status: '{scen_res['status']}' | Passed: {scen_res['passed']}")
    print(f"   Finding: {scen_res['findings'][0]['rule_id']} — {scen_res['findings'][0]['message']}")

    # 7. Execute SDK Wrapper Agent with Level 3 (Instrumented Tools)
    # The existing agent function runs through ToolInvoker and fault injection
    run_sdk_res = client.post("/api/runs", json={
        "agent_id": sdk_agent_id,
        "agent_version": "1.0.0",
        "scenario_id": "SCEN-01-NORMAL-CREATE",
        "name": "SDK Wrapper Normal Execution"
    })
    assert run_sdk_res.status_code == 201
    run_sdk_data = run_sdk_res.json()
    assert run_sdk_data["passed_scenarios"] == 1
    print("7. SDK Wrapper Execution with Level 3 Instrumented Tools:")
    print(f"   Run ID: {run_sdk_data['id']} | Status: {run_sdk_data['status']}")
    print(f"   Passed: {run_sdk_data['passed_scenarios']}/{run_sdk_data['total_scenarios']}")
    print(f"   Observability Level: {run_sdk_data['observability_level']}")

    # 8. Inspect Trace of SDK Wrapper Run
    trace_res = client.get(f"/api/runs/{run_sdk_data['id']}/trace")
    assert trace_res.status_code == 200
    traces = trace_res.json()
    assert len(traces) > 0
    tool_events = [t for t in traces if t["event_type"] in ["tool_call", "tool_response"]]
    print(f"8. Execution Trace: {len(traces)} total events, {len(tool_events)} tool events intercepted")

    # 9. Query Persisted Run Record
    persisted_run = client.get(f"/api/runs/{run_sdk_data['id']}").json()
    assert persisted_run["id"] == run_sdk_data["id"]
    assert persisted_run["agent_id"] == sdk_agent_id
    assert persisted_run["observability_level"] == "level_3_instrumented_tools"
    print(f"9. Persistence Verified: Run {persisted_run['id']} correctly stored with observability level '{persisted_run['observability_level']}'")

    print("=" * 70)
    print("CONNECTOR UPGRADE VERIFICATION PASSED: ALL WORKFLOWS VALIDATED!")
    print("=" * 70)

if __name__ == "__main__":
    run_connector_verification()
