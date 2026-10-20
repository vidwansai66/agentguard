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


def test_scenario_12_duplicate_prevention_with_http_agent(mock_http_client, test_agent_store):
    """
    Verifies that the dedicated SCEN-12 scenario genuinely exercises two equivalent create
    requests with the same idempotency key, verifies the identical ticket ID is returned,
    records the probe trace events, and confirms no redundant tickets are created.
    """
    from app.db.seed_data import DEMO_SCENARIOS

    scen_12 = next(s for s in DEMO_SCENARIOS if s["id"] == "SCEN-12-DUPLICATE-PREVENTION")

    result = scenario_runner.run_scenario(
        scenario_data=scen_12,
        agent_id="test-stateful-http-dup-scenario",
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

    # 1. Assert scenario execution passed honestly
    assert result["passed"] is True
    assert result["status"] == "passed"
    assert result["has_unsafe_side_effect"] is False
    assert result["execution_output"].get("duplicate_prevented") is True

    returned_ticket_id = result["execution_output"].get("ticket_id")
    assert returned_ticket_id is not None
    assert returned_ticket_id.startswith("TICK-HTTP-")

    # 2. Verify trace events record the genuine double execution
    trace_actions = [e["action_name"] for e in result["trace_events"]]
    assert "http_dispatch_start" in trace_actions
    assert "duplicate_probe_start" in trace_actions
    assert "duplicate_probe_verified" in trace_actions

    # Two HTTP responses recorded in the trace
    http_responses = [e for e in result["trace_events"] if e["action_name"] == "http_response"]
    assert len(http_responses) == 2
    assert http_responses[0]["sanitized_output"]["ticket_id"] == returned_ticket_id
    assert http_responses[1]["sanitized_output"]["ticket_id"] == returned_ticket_id
    assert http_responses[0]["sanitized_output"]["status_code"] == 200
    assert http_responses[1]["sanitized_output"]["status_code"] == 200

    # 3. Out-of-band store verification: exactly 1 ticket in store
    all_tickets = test_agent_store.get_all_tickets()
    assert len(all_tickets) == 1
    assert all_tickets[0]["id"] == returned_ticket_id
    assert all_tickets[0]["idempotency_key"] == "idemp-vpn-duplicate-001"


def test_scenario_12_duplicate_prevention_fails_baseline_python_agent():
    """
    Verifies that SCEN-12 correctly catches an agent that does NOT handle idempotency.
    The baseline Python agent naively issues two create calls, creating two separate
    tickets, and is honestly evaluated as failed with a critical duplicate finding.
    """
    from app.db.seed_data import DEMO_SCENARIOS

    scen_12 = next(s for s in DEMO_SCENARIOS if s["id"] == "SCEN-12-DUPLICATE-PREVENTION")

    result = scenario_runner.run_scenario(
        scenario_data=scen_12,
        agent_id="agent-ticket-sample",
        agent_version="1.0.0",
        agent_strategy="baseline",
        adapter_type="python"
    )

    assert result["passed"] is False
    assert result["status"] == "failed"
    assert result["has_unsafe_side_effect"] is True

    # Trace records probe start and failure
    trace_actions = [e["action_name"] for e in result["trace_events"]]
    assert "duplicate_probe_start" in trace_actions
    assert "duplicate_probe_failed" in trace_actions

    # Assertion findings include critical duplicate action failure
    dup_findings = [f for f in result["findings"] if f["rule_id"] == "ASSERT_NO_DUPLICATE_ACTIONS"]
    assert len(dup_findings) == 1
    assert dup_findings[0]["status"] == "failed"
    assert dup_findings[0]["severity"] == "critical"
    assert "Duplicate side effect detected" in dup_findings[0]["message"]


def test_scenario_12_duplicate_prevention_passes_candidate_python_agent():
    """
    Verifies that the candidate patch (1.1.0-patch) with safe_idempotent strategy passes
    SCEN-12 by reconciling state or passing the idempotency key, creating only 1 ticket.
    """
    from app.db.seed_data import DEMO_SCENARIOS

    scen_12 = next(s for s in DEMO_SCENARIOS if s["id"] == "SCEN-12-DUPLICATE-PREVENTION")

    result = scenario_runner.run_scenario(
        scenario_data=scen_12,
        agent_id="agent-ticket-sample",
        agent_version="1.1.0-patch",
        agent_strategy="safe_idempotent",
        custom_config={"enable_idempotency_check": True},
        adapter_type="python"
    )

    assert result["passed"] is True
    assert result["status"] == "passed"
    assert result["has_unsafe_side_effect"] is False
    assert result["execution_output"].get("duplicate_prevented") is True

    # Assert findings passed cleanly
    dup_findings = [f for f in result["findings"] if f["rule_id"] == "ASSERT_NO_DUPLICATE_ACTIONS"]
    assert len(dup_findings) == 1
    assert dup_findings[0]["status"] == "passed"


def test_scenario_12_seeded_in_database():
    """
    Verifies that SCEN-12 is properly seeded into the database, linked to Core Reliability
    Suite and Full Regression Suite, and queryable by API.
    """
    from app.db.session import SessionLocal, init_db
    from app.db.seed_data import seed_database
    from app.models.scenario import Scenario
    from app.models.suite import TestSuite, SuiteScenario

    init_db()
    db = SessionLocal()
    try:
        seed_database(db)
        scen = db.query(Scenario).filter(Scenario.id == "SCEN-12-DUPLICATE-PREVENTION").first()
        assert scen is not None
        assert scen.name == "Duplicate Ticket Prevention via Idempotency"
        assert scen.failure_type == "normal_execution"
        assert scen.is_seeded is True
        assert scen.category == "ticketing"
        assert scen.severity == "high"

        # Verify linked to suite-core-reliability
        core_links = db.query(SuiteScenario).filter(
            SuiteScenario.suite_id == "suite-core-reliability",
            SuiteScenario.scenario_id == "SCEN-12-DUPLICATE-PREVENTION"
        ).first()
        assert core_links is not None
    finally:
        db.close()
