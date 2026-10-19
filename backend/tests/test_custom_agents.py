import pytest
from app.adapters.base import AgentAdapter
from app.agents.sample_ticket_agent import SampleTicketAgent
from app.agents.custom_test_agent import CustomTestAgent
from app.adapters.http_adapter import HttpAgentAdapter, HttpAdapterSecurityError
from app.agents.registry import agent_registry
from app.runner.executor import scenario_runner
from app.services.run_service import run_service
from app.models.agent import Agent
from app.models.scenario import Scenario

def test_sample_agent_satisfies_adapter_contract():
    agent = SampleTicketAgent(agent_id="test-sample")
    assert isinstance(agent, AgentAdapter)
    assert hasattr(agent, "declared_capabilities")
    assert "ticket_create" in agent.declared_capabilities
    assert "state_inspection" in agent.declared_capabilities

    test_res = agent.test_connection()
    assert test_res["status"] == "healthy"
    assert "declared_capabilities" in test_res

def test_custom_test_agent_satisfies_adapter_contract():
    agent = CustomTestAgent(agent_id="test-custom")
    assert isinstance(agent, AgentAdapter)
    assert hasattr(agent, "declared_capabilities")
    assert "ticket_create" in agent.declared_capabilities
    assert "ticket_query" in agent.declared_capabilities

    test_res = agent.test_connection()
    assert test_res["status"] == "healthy"
    assert test_res["agent_id"] == "test-custom"

def test_custom_agent_registration_api(client, db_session):
    payload = {
        "id": "agent-api-custom-01",
        "name": "Custom Logistics Dispatcher",
        "description": "Custom agent for testing logistics dispatch tickets",
        "adapter_type": "python",
        "version": "1.0.0",
        "strategy": "baseline",
        "supported_tools": ["ticket_create", "ticket_query", "ticket_get"],
        "declared_capabilities": ["ticket_create", "ticket_query", "state_inspection"],
        "adapter_config": {
            "class_name": "CustomTestAgent",
            "enable_reconciliation": True
        }
    }
    resp = client.post("/api/agents/custom", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "agent-api-custom-01"
    assert data["name"] == "Custom Logistics Dispatcher"
    assert data["adapter_type"] == "python"
    assert data["registration_source"] == "custom"
    assert "state_inspection" in data["declared_capabilities"]

    # Verify listing
    list_resp = client.get("/api/agents")
    assert list_resp.status_code == 200
    ids = [a["id"] for a in list_resp.json()]
    assert "agent-api-custom-01" in ids

def test_validate_adapter_config_api(client):
    # Valid Python config
    valid_py = client.post("/api/agents/validate-config", json={
        "adapter_type": "python",
        "adapter_config": {"class_name": "CustomTestAgent"}
    })
    assert valid_py.status_code == 200
    assert valid_py.json()["valid"] is True

    # Untrusted / Invalid Python config
    invalid_py = client.post("/api/agents/validate-config", json={
        "adapter_type": "python",
        "adapter_config": {"class_name": "MaliciousUnregisteredAgent"}
    })
    assert invalid_py.status_code == 200
    assert invalid_py.json()["valid"] is False
    assert "Untrusted" in invalid_py.json()["error"] or "untrusted" in invalid_py.json()["error"].lower()

    # Valid HTTP config
    valid_http = client.post("/api/agents/validate-config", json={
        "adapter_type": "http",
        "adapter_config": {"base_url": "http://127.0.0.1:8080"}
    })
    assert valid_http.status_code == 200
    assert valid_http.json()["valid"] is True

    # SSRF Cloud Metadata Block
    ssrf_http = client.post("/api/agents/validate-config", json={
        "adapter_type": "http",
        "adapter_config": {"base_url": "http://169.254.169.254/latest/meta-data"}
    })
    assert ssrf_http.status_code == 200
    assert ssrf_http.json()["valid"] is False
    assert "metadata" in ssrf_http.json()["error"].lower() or "blocked" in ssrf_http.json()["error"].lower()

def test_scenario_compatibility_check_api(client, db_session):
    # Register an agent with minimal capabilities (only ticket_create)
    client.post("/api/agents/custom", json={
        "id": "agent-minimal-create",
        "name": "Minimal Agent",
        "adapter_type": "python",
        "version": "1.0.0",
        "strategy": "baseline",
        "supported_tools": ["ticket_create"],
        "declared_capabilities": ["ticket_create"],
        "adapter_config": {"class_name": "CustomTestAgent"}
    })

    # SCEN-03-AMBIGUOUS-OUTCOME requires state_inspection
    compat_resp = client.post("/api/scenarios/compatibility", json={
        "agent_id": "agent-minimal-create",
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
    })
    assert compat_resp.status_code == 200
    compat_data = compat_resp.json()
    assert compat_data["compatible"] is False
    assert len(compat_data["scenarios"]) == 1
    assert "state_inspection" in compat_data["scenarios"][0]["missing_capabilities"]

    # Built-in agent has state_inspection -> should be fully compatible
    builtin_compat = client.post("/api/scenarios/compatibility", json={
        "agent_id": "agent-ticket-sample",
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
    })
    assert builtin_compat.status_code == 200
    assert builtin_compat.json()["compatible"] is True

def test_runner_marks_scenario_unsupported_on_missing_capabilities(client, db_session):
    # Register an agent missing state_inspection
    client.post("/api/agents/custom", json={
        "id": "agent-no-state-inspect",
        "name": "No State Agent",
        "adapter_type": "python",
        "version": "1.0.0",
        "strategy": "baseline",
        "supported_tools": ["ticket_create"],
        "declared_capabilities": ["ticket_create"],
        "adapter_config": {"class_name": "CustomTestAgent"}
    })

    # Execute SCEN-03-AMBIGUOUS-OUTCOME
    run_resp = client.post("/api/runs", json={
        "name": "Unsupported Capability Test",
        "agent_id": "agent-no-state-inspect",
        "agent_version": "1.0.0",
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
    })
    assert run_resp.status_code == 201
    run_data = run_resp.json()

    # The scenario must NOT be marked as passed
    assert run_data["passed_scenarios"] == 0
    assert run_data["unsupported_scenarios"] == 1

    # Check the scenario result
    results = run_data["scenario_results"]
    assert len(results) == 1
    scen_res = results[0]
    assert scen_res["status"] == "unsupported"
    assert scen_res["passed"] is False

    # Check the assertion findings
    findings = scen_res["findings"]
    cap_findings = [f for f in findings if f["rule_id"] == "ASSERT_CAPABILITY_SUPPORT"]
    assert len(cap_findings) == 1
    assert "lacks required capabilities" in cap_findings[0]["message"]

def test_ambiguous_outcome_scenario_with_custom_test_agent(client, db_session):
    # agent-custom-order has declared capabilities: ticket_create, ticket_query, ticket_get, state_inspection
    run_resp = client.post("/api/runs", json={
        "name": "Custom Agent Ambiguous Recovery",
        "agent_id": "agent-custom-order",
        "agent_version": "1.0.0",
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
    })
    assert run_resp.status_code == 201
    run_data = run_resp.json()

    assert run_data["total_scenarios"] == 1
    scen_res = run_data["scenario_results"][0]

    # CustomTestAgent with reconciliation recovers from dropped response and prevents duplicates
    assert scen_res["has_unsafe_side_effect"] is False
    assert scen_res["passed"] is True
    assert scen_res["disrupted"] is True
    assert scen_res["recovered"] is True

def test_http_adapter_ssrf_protections():
    # Loopback allowed only in local dev
    with pytest.raises(HttpAdapterSecurityError):
        HttpAgentAdapter(agent_id="test", config={"base_url": "http://127.0.0.1:8080", "allow_local_dev": False})

    # Cloud metadata is unconditionally blocked
    with pytest.raises(HttpAdapterSecurityError):
        HttpAgentAdapter(agent_id="test", config={"base_url": "http://169.254.169.254", "allow_local_dev": True})

    # Hostname metadata blocked
    with pytest.raises(HttpAdapterSecurityError):
        HttpAgentAdapter(agent_id="test", config={"base_url": "http://metadata.google.internal", "allow_local_dev": True})

    # Unsupported schemes blocked
    with pytest.raises(HttpAdapterSecurityError):
        HttpAgentAdapter(agent_id="test", config={"base_url": "ftp://127.0.0.1/upload", "allow_local_dev": True})

def test_agent_connectivity_test_endpoint(client, db_session):
    # Built-in agent
    res = client.post("/api/agents/agent-ticket-sample/test-connection")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "ticket_create" in data["declared_capabilities"]

    # Custom agent
    res_custom = client.post("/api/agents/agent-custom-order/test-connection")
    assert res_custom.status_code == 200
    data_custom = res_custom.json()
    assert data_custom["status"] == "healthy"
    assert data_custom["adapter_type"] == "python"
