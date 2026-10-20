"""
Deterministic tests for the stateful, verifiable HTTP test agent.
Verifies real task success with ticket artifact generation, honest HTTP failure handling,
and duplicate-action prevention via idempotency keys using in-process ASGI testing.
"""
import pytest
from starlette.testclient import TestClient as StarletteClient

from app.agents.local_mock_http_service import create_mock_agent_app, MockHttpTicketStore
from app.adapters.http_adapter import HttpAgentAdapter
from app.runner.executor import scenario_runner


@pytest.fixture
def test_agent_store():
    """Provides an isolated MockHttpTicketStore for each test."""
    store = MockHttpTicketStore()
    yield store
    store.reset()


@pytest.fixture
def mock_http_client(test_agent_store):
    """Provides an in-process Starlette ASGI TestClient connected to the stateful test agent."""
    app = create_mock_agent_app(store=test_agent_store)
    return StarletteClient(app, base_url="http://127.0.0.1:9099")


def test_verifiable_http_agent_task_success(mock_http_client, test_agent_store):
    """
    Verifies that the stateful HTTP test agent creates a real verifiable ticket ID,
    persists it in its store, and satisfies ScenarioRunner evaluation honestly.
    """
    adapter = HttpAgentAdapter(
        agent_id="test-stateful-http-success",
        config={
            "base_url": "http://127.0.0.1:9099",
            "invocation_endpoint": "/run",
            "health_endpoint": "/health",
            "allow_local_dev": True,
            "response_mapping": {
                "result_path": "output",
                "status_path": "status",
                "ticket_id_path": "ticket_id"
            }
        }
    )
    # Inject in-process ASGI test client for network-free, zero-socket execution
    adapter._client = mock_http_client

    # 1. Verify health check
    health_res = adapter.test_connection()
    assert health_res["status"] == "healthy"
    assert "stateful-customer-portal-agent" in str(health_res)

    # 2. Run Scenario with ScenarioRunner (SCEN-01-NORMAL-CREATE requires ticket_created=True)
    scenario = {
        "id": "SCEN-01-NORMAL-CREATE",
        "name": "Normal Ticket Creation Workflow",
        "failure_type": "normal_execution",
        "task_input": {
            "action": "create_ticket",
            "title": "VPN Remote Access Setup",
            "description": "User requests access to internal staging cluster.",
            "priority": "high",
            "idempotency_key": "idemp-vpn-001"
        },
        "expected_outcome": {
            "status": "success",
            "ticket_created": True,
            "max_tickets_created": 1
        },
        "allowed_tools": ["ticket_create", "ticket_query", "ticket_get"],
        "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get"],
        "required_capabilities": []
    }

    result = scenario_runner.run_scenario(
        scenario_data=scenario,
        agent_id="test-stateful-http-success",
        agent_version="1.0.0",
        adapter_type="http",
        custom_config={
            "base_url": "http://127.0.0.1:9099",
            "invocation_endpoint": "/run",
            "allow_local_dev": True,
            "_client": mock_http_client,
            "response_mapping": {
                "result_path": "output",
                "status_path": "status",
                "ticket_id_path": "ticket_id"
            }
        }
    )

    # 3. Assert real verifiable task outcome
    assert result["passed"] is True
    assert result["status"] == "passed"
    generated_ticket_id = result["execution_output"].get("ticket_id")
    assert generated_ticket_id is not None
    assert generated_ticket_id.startswith("TICK-HTTP-")

    # 4. Assert trace recorded both dispatch start and sanitized http_response with status_code
    trace_actions = [e["action_name"] for e in result["trace_events"]]
    assert "http_dispatch_start" in trace_actions
    assert "http_response" in trace_actions

    http_resp_evt = next(e for e in result["trace_events"] if e["action_name"] == "http_response")
    assert http_resp_evt["sanitized_output"]["status_code"] == 200
    assert http_resp_evt["sanitized_output"]["ticket_id"] == generated_ticket_id

    # 5. Out-of-band store verification (artifact actually exists in store)
    stored_ticket = test_agent_store.get_ticket(generated_ticket_id)
    assert stored_ticket is not None
    assert stored_ticket["title"] == "VPN Remote Access Setup"
    assert stored_ticket["idempotency_key"] == "idemp-vpn-001"


def test_verifiable_http_agent_duplicate_action_prevention(mock_http_client, test_agent_store):
    """
    Verifies that calling the test agent repeatedly with the same idempotency key
    returns the existing ticket artifact and avoids creating duplicate tickets.
    """
    adapter = HttpAgentAdapter(
        agent_id="test-stateful-http-idemp",
        config={
            "base_url": "http://127.0.0.1:9099",
            "invocation_endpoint": "/run",
            "allow_local_dev": True,
            "response_mapping": {
                "result_path": "output",
                "status_path": "status",
                "ticket_id_path": "ticket_id"
            }
        }
    )
    adapter._client = mock_http_client

    task_payload = {
        "title": "Database Migration Ticket",
        "description": "Migrate customer schema to v2",
        "idempotency_key": "idemp-db-mig-99"
    }

    # First invocation
    from unittest.mock import MagicMock
    invoker1 = MagicMock()
    res1 = adapter.run_task(task_input=task_payload, context={"run_id": "RUN-IDEMP-1"}, tool_invoker=invoker1)
    assert res1["status"] == "success"
    first_ticket_id = res1["ticket_id"]
    assert first_ticket_id.startswith("TICK-HTTP-")
    assert res1["raw_output"]["is_duplicate"] is False

    # Second invocation with identical idempotency_key
    invoker2 = MagicMock()
    res2 = adapter.run_task(task_input=task_payload, context={"run_id": "RUN-IDEMP-2"}, tool_invoker=invoker2)
    assert res2["status"] == "success"
    second_ticket_id = res2["ticket_id"]
    assert res2["raw_output"]["is_duplicate"] is True

    # Verifiable invariant: The exact same ticket ID was returned
    assert first_ticket_id == second_ticket_id

    # Verifiable invariant: Total tickets in store is strictly 1 (no duplicate side effects)
    all_tickets = test_agent_store.get_all_tickets()
    assert len(all_tickets) == 1
    assert all_tickets[0]["id"] == first_ticket_id


def test_verifiable_http_agent_simulated_http_failure(mock_http_client, test_agent_store):
    """
    Verifies deterministic simulated failure behavior:
    1. HTTP 500 error is captured honestly in the trace as http_response_error.
    2. Task outcome is marked failed and disrupted without false success reports.
    """
    adapter = HttpAgentAdapter(
        agent_id="test-stateful-http-fail",
        config={
            "base_url": "http://127.0.0.1:9099",
            "invocation_endpoint": "/run",
            "allow_local_dev": True
        }
    )
    adapter._client = mock_http_client

    # Configure store to simulate an upstream 503 Service Unavailable
    test_agent_store.set_simulated_failure(
        status_code=503,
        error_message="Gateway overloaded: upstream service unavailable"
    )

    from unittest.mock import MagicMock
    mock_invoker = MagicMock()
    mock_invoker.current_step = 1

    res = adapter.run_task(
        task_input={"prompt": "Reboot edge server"},
        context={"run_id": "RUN-FAIL-503"},
        tool_invoker=mock_invoker
    )

    assert res["status"] == "failed"
    assert res["status_code"] == 503
    assert res["disrupted"] is True
    assert "503" in res["error"]
    assert "Gateway overloaded" in res["error"]

    # Verify trace error event was recorded with status code and error preview
    assert mock_invoker.record_http_error.called
    call_kwargs = mock_invoker.record_http_error.call_args[1]
    assert call_kwargs["action"] == "http_response_error"
    assert call_kwargs["output_data"]["status_code"] == 503
    assert "Gateway overloaded" in call_kwargs["output_data"]["response_preview"]


def test_verifiable_http_agent_per_request_error_flag(mock_http_client):
    """
    Verifies that client payloads requesting 'simulate_error' trigger deterministic
    HTTP failures without altering global store state.
    """
    adapter = HttpAgentAdapter(
        agent_id="test-stateful-per-req-fail",
        config={
            "base_url": "http://127.0.0.1:9099",
            "invocation_endpoint": "/run",
            "allow_local_dev": True
        }
    )
    adapter._client = mock_http_client

    from unittest.mock import MagicMock
    mock_invoker = MagicMock()
    mock_invoker.current_step = 1

    res = adapter.run_task(
        task_input={
            "prompt": "Test fault injection",
            "simulate_error": True,
            "error_status_code": 500,
            "error_message": "Controlled fault injection test"
        },
        context={"run_id": "RUN-PER-REQ-1"},
        tool_invoker=mock_invoker
    )

    assert res["status"] == "failed"
    assert res["status_code"] == 500
    assert "Controlled fault injection test" in res["error"]
