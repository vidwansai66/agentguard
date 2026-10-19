import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.models.agent import Agent, AgentVersion
from app.adapters.http_adapter import HttpAgentAdapter
from app.adapters.wrappers.callable_wrapper import CallableAgentWrapper
from app.agents.existing_sample_agent import existing_ticket_solver, ExistingCustomerSupportAgent
from app.runner.executor import ScenarioRunner

def test_connect_existing_http_agent_level_1(client):
    """Tests connecting an existing HTTP agent with Level 1 (Result-Only) observability."""
    payload = {
        "id": "agent-ext-http-level1",
        "name": "External FAQ Bot",
        "description": "Third-party customer service bot",
        "connection_method": "http_endpoint",
        "observability_level": "level_1_result_only",
        "version": "1.0.0",
        "declared_capabilities": ["ticket_create", "ticket_get"],
        "supported_tools": ["ticket_create"],
        "http_config": {
            "base_url": "http://127.0.0.1:9099",
            "health_endpoint": "/health",
            "invocation_endpoint": "/v1/chat/completions",
            "auth_type": "Bearer",
            "secret_env_var": "EXT_BOT_API_KEY",
            "observability_level": "level_1_result_only",
            "connect_timeout_seconds": 3.0,
            "read_timeout_seconds": 10.0,
            "allow_local_dev": True,
            "request_mapping": {
                "user_prompt": "prompt",
                "session_id": "run_id"
            },
            "response_mapping": {
                "result_path": "choices.0.message.content",
                "status_path": "status"
            }
        }
    }

    res = client.post("/api/agents/connect-existing", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == "agent-ext-http-level1"
    assert data["observability_level"] == "level_1_result_only"
    assert data["registration_source"] == "connected_existing"
    assert data["adapter_type"] == "http"

def test_connect_existing_python_sdk_wrapper_level_2(client):
    """Tests connecting an existing Python agent using the SDK Callable wrapper with Level 2."""
    payload = {
        "id": "agent-ext-sdk-level2",
        "name": "Legacy Ticketing Function",
        "description": "Pre-existing function connected via SDK wrapper",
        "connection_method": "python_sdk_wrapper",
        "observability_level": "level_2_structured_events",
        "version": "1.0.0",
        "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get"],
        "supported_tools": ["ticket_create"],
        "sdk_config": {
            "wrapper_type": "callable",
            "target_name": "existing_ticket_solver",
            "observability_level": "level_2_structured_events",
            "input_parameter_name": "prompt"
        }
    }

    res = client.post("/api/agents/connect-existing", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == "agent-ext-sdk-level2"
    assert data["observability_level"] == "level_2_structured_events"
    assert data["adapter_type"] == "python_sdk_wrapper"

def test_http_adapter_level_1_invocation_and_mapping():
    """Tests HTTP adapter Level 1 request mapping and response extraction."""
    config = {
        "base_url": "http://127.0.0.1:9099",
        "invocation_endpoint": "/api/chat",
        "observability_level": "level_1_result_only",
        "allow_local_dev": True,
        "request_mapping": {
            "query": "prompt",
            "session": "run_id"
        },
        "response_mapping": {
            "result_path": "data.answer",
            "status_path": "data.state"
        }
    }

    adapter = HttpAgentAdapter(agent_id="test-http-lvl1", config=config)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": {
            "answer": "Issue has been resolved successfully.",
            "state": "success"
        }
    }

    mock_invoker = MagicMock()

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        result = adapter.run_task(
            task_input={"prompt": "Cannot access server"},
            context={"run_id": "RUN-TEST-123", "scenario_id": "scen-01"},
            tool_invoker=mock_invoker
        )

        assert mock_post.called
        sent_json = mock_post.call_args[1]["json"]
        assert sent_json["query"] == "Cannot access server"
        assert sent_json["session"] == "RUN-TEST-123"

        assert result["status"] == "success"
        assert "Issue has been resolved" in result["message"]
        assert result["observability_level"] == "level_1_result_only"

def test_http_adapter_level_2_structured_events_forwarding():
    """Tests HTTP adapter Level 2 extracting and recording external execution events into the trace."""
    config = {
        "base_url": "http://127.0.0.1:9099",
        "invocation_endpoint": "/api/agent",
        "observability_level": "level_2_structured_events",
        "allow_local_dev": True,
        "response_mapping": {
            "result_path": "output",
            "events_path": "execution_trace"
        }
    }

    adapter = HttpAgentAdapter(agent_id="test-http-lvl2", config=config)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "success",
        "output": "All actions finished",
        "execution_trace": [
            {"action": "search_db", "type": "tool_call", "tool_name": "db_lookup", "duration_ms": 15.0},
            {"action": "format_answer", "type": "agent_decision", "duration_ms": 5.0}
        ]
    }

    mock_invoker = MagicMock()
    mock_invoker.current_step = 1

    with patch("httpx.Client.post", return_value=mock_resp):
        result = adapter.run_task(
            task_input={"prompt": "Find order #999"},
            context={"run_id": "RUN-999", "scenario_id": "scen-trace"},
            tool_invoker=mock_invoker
        )

        assert result["status"] == "success"
        assert result["observability_level"] == "level_2_structured_events"
        # Verify events were forwarded to recorder
        assert mock_invoker.recorder.record_event.call_count == 2

def test_observability_compatibility_blocks_level_1_on_tool_faults(client):
    """
    Verifies that Level 1 (Result-Only) agents cannot execute scenarios requiring tool fault injection,
    and are marked unsupported rather than falsely passing.
    """
    # Create or ensure Level 1 agent
    agent_id = "agent-http-result-only-check"
    client.post("/api/agents/connect-existing", json={
        "id": agent_id,
        "name": "Level 1 Result-Only Agent",
        "connection_method": "http_endpoint",
        "observability_level": "level_1_result_only",
        "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get", "state_inspection", "handle_structured_errors"],
        "http_config": {
            "base_url": "http://127.0.0.1:8888",
            "observability_level": "level_1_result_only"
        }
    })

    # Scenario SCEN-03-AMBIGUOUS-OUTCOME requires tool fault injection (failure_type: ambiguous_outcome)
    comp_res = client.post("/api/scenarios/compatibility", json={
        "agent_id": agent_id,
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
    })
    assert comp_res.status_code == 200
    cdata = comp_res.json()
    assert cdata["compatible"] is False
    assert cdata["observability_level"] == "level_1_result_only"
    scenario_info = cdata["scenarios"][0]
    assert scenario_info["observability_compatible"] is False
    assert "Requires Level 3 Instrumented Tools" in scenario_info["explanation"]

def test_runner_marks_level_1_unsupported_on_tool_fault_scenario():
    """Verifies that ScenarioRunner marks Level 1 execution as status='unsupported' when tool faults are required."""
    runner = ScenarioRunner()
    scenario_data = {
        "id": "scen-tool-fault-check",
        "name": "Transient Tool Timeout",
        "failure_type": "transient_timeout",
        "required_capabilities": ["ticket_create"],
        "task_input": {"prompt": "Create ticket"}
    }

    result = runner.run_scenario(
        scenario_data=scenario_data,
        agent_id="agent-level1-runner-check",
        adapter_type="http",
        agent_adapter_config={
            "base_url": "http://127.0.0.1:9999",
            "observability_level": "level_1_result_only",
            "declared_capabilities": ["ticket_create"]
        }
    )

    assert result["status"] == "unsupported"
    assert result["passed"] is False
    assert any(f["rule_id"] == "ASSERT_OBSERVABILITY_COMPATIBILITY" for f in result["findings"])
    assert "Level 1 (Result-Only)" in result["error_message"]

def test_callable_sdk_wrapper_level_3_tool_instrumentation():
    """
    Tests that a standalone existing agent callable receives instrumented tools (Level 3),
    allowing fault injection through AgentGuard's ToolInvoker without modifying the agent code.
    """
    wrapper = CallableAgentWrapper(
        agent_id="test-sdk-lvl3",
        target_callable=existing_ticket_solver,
        config={"observability_level": "level_3_instrumented_tools"}
    )

    mock_invoker = MagicMock()
    mock_invoker.call_tool.return_value = {"status": "success", "ticket_id": "TICK-MOCK-777"}

    result = wrapper.run_task(
        task_input={"prompt": "Resolve broken order checkout"},
        context={"run_id": "RUN-CALLABLE-1"},
        tool_invoker=mock_invoker
    )

    assert result["status"] == "success"
    assert result["ticket_id"] == "TICK-MOCK-777"
    # Ensure tool was called through invoker
    assert mock_invoker.call_tool.called
    assert mock_invoker.call_tool.call_args[1]["tool_name"] == "ticket_create"

def test_secret_redaction_in_http_adapter_trace():
    """Verifies that secrets specified via secret_env_var are redacted and never leaked in traces."""
    with patch.dict("os.environ", {"EXT_SECRET_KEY": "super-secret-production-token-12345"}):
        adapter = HttpAgentAdapter(
            agent_id="test-secret-agent",
            config={
                "base_url": "http://127.0.0.1:9099",
                "secret_env_var": "EXT_SECRET_KEY",
                "allow_local_dev": True
            }
        )

        headers = adapter._get_auth_header()
        assert "Authorization" in headers
        assert "super-secret-production-token-12345" in headers["Authorization"]

        # Simulate exception containing the secret
        mock_invoker = MagicMock()
        with patch("httpx.Client.post", side_effect=RuntimeError("Connection failed with token super-secret-production-token-12345")):
            res = adapter.run_task(
                task_input={"prompt": "test"},
                context={"run_id": "RUN-SEC"},
                tool_invoker=mock_invoker
            )
            assert res["status"] == "failed"
            # In trace decision, the secret must be redacted
            recorded_reasoning = mock_invoker.record_decision.call_args[1]["reasoning"]
            assert "super-secret-production-token-12345" not in recorded_reasoning
