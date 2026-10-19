import pytest
import os
import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.adapters.llm.base_provider import LlmResponse
from app.adapters.llm.openai_provider import OpenAiCompatibleProvider
from app.adapters.model_backed_adapter import ModelBackedAgentAdapter, ALLOWED_TOOL_NAMES
from app.adapters.frameworks.langgraph_adapter import LangGraphAgentAdapter
from app.agents.framework_sample_graph import customer_support_graph, build_customer_support_graph
from app.agents.local_mock_http_service import create_mock_agent_app
from app.adapters.http_adapter import HttpAgentAdapter
from app.agents.registry import agent_registry

def test_framework_catalog_endpoint(client: TestClient):
    """Verifies that framework catalog accurately lists implemented vs planned frameworks."""
    resp = client.get("/api/agents/frameworks/catalog")
    assert resp.status_code == 200
    catalog = resp.json()
    assert isinstance(catalog, list)

    fw_map = {item["framework"]: item for item in catalog}
    assert "langgraph" in fw_map
    assert fw_map["langgraph"]["status"] == "supported"
    assert "1.2" in fw_map["langgraph"]["installed_version"]

    assert "crewai" in fw_map
    assert fw_map["crewai"]["status"] == "planned"
    assert "autogen" in fw_map
    assert fw_map["autogen"]["status"] == "planned"

def test_langgraph_adapter_test_connection():
    """Verifies LangGraph connection inspection and node discovery."""
    adapter = LangGraphAgentAdapter(agent_id="test-langgraph", graph_instance=customer_support_graph)
    test_res = adapter.test_connection()
    assert test_res["status"] == "healthy"
    assert test_res["framework"] == "langgraph"
    assert test_res["observability_level"] == "level_3_instrumented_tools"
    assert "analyze_request" in test_res["nodes"]
    assert "create_ticket" in test_res["nodes"]

def test_langgraph_adapter_execution_routes_tools_through_invoker():
    """Verifies LangGraph executes nodes and routes tool calls through tool_invoker."""
    adapter = LangGraphAgentAdapter(agent_id="test-langgraph-run", graph_instance=customer_support_graph)

    # Mock tool invoker
    mock_invoker = MagicMock()
    mock_invoker.current_step = 0
    mock_invoker.call_tool.return_value = {
        "status": "success",
        "ticket_id": "TICKET-LG-1001",
        "title": "Support Request: technical"
    }

    result = adapter.run_task(
        task_input={"prompt": "Found a critical bug in checkout!"},
        context={},
        tool_invoker=mock_invoker
    )

    assert result["status"] == "success"
    assert result["ticket_id"] == "TICKET-LG-1001"
    assert result["observability_level"] == "level_3_instrumented_tools"
    # Verify tool call was intercepted
    assert mock_invoker.call_tool.called
    call_args = mock_invoker.call_tool.call_args[1]
    assert call_args["tool_name"] == "ticket_create"
    assert "checkout" in call_args["params"]["description"]
    # Verify events were streamed/recorded
    events = adapter.stream_events()
    assert len(events) >= 3

def test_model_backed_adapter_missing_api_key_reports_unconfigured():
    """Verifies that missing API keys report honest status rather than pretending success."""
    # Ensure env var is absent
    env_key = "NON_EXISTENT_TEST_KEY_FOR_AGENTGUARD"
    if env_key in os.environ:
        del os.environ[env_key]

    adapter = ModelBackedAgentAdapter(
        agent_id="test-model-missing-key",
        config={"secret_env_var": env_key}
    )

    test_res = adapter.test_connection()
    assert test_res["status"] == "unconfigured"
    assert "is not set" in test_res["message"]

    mock_invoker = MagicMock()
    run_res = adapter.run_task(
        task_input={"prompt": "Help me with my order"},
        context={},
        tool_invoker=mock_invoker
    )
    assert run_res["status"] == "unsupported"
    assert "missing API key" in run_res["message"]

def test_model_backed_adapter_with_mock_provider_routes_tools():
    """Verifies model-backed agent routes tool calls through AgentGuard tool_invoker with allowlist."""
    mock_responses = [
        # First turn: LLM calls create_ticket tool
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "create_ticket",
                        "arguments": json.dumps({"title": "Order Delayed", "idempotency_key": "model-key-101"})
                    }
                }
            ],
            "finish_reason": "tool_calls"
        },
        # Second turn: LLM receives tool output and finishes
        {
            "content": "I have created ticket TICKET-LLM-552 for your delayed order.",
            "tool_calls": [],
            "finish_reason": "stop"
        }
    ]

    adapter = ModelBackedAgentAdapter(
        agent_id="test-model-mock",
        config={
            "model": "gpt-4o-mini",
            "mock_responses": mock_responses
        }
    )

    mock_invoker = MagicMock()
    mock_invoker.call_tool.return_value = {
        "status": "success",
        "ticket_id": "TICKET-LLM-552"
    }

    result = adapter.run_task(
        task_input={"prompt": "My order is delayed, please create a ticket"},
        context={},
        tool_invoker=mock_invoker
    )

    assert result["status"] == "success"
    assert result["ticket_id"] == "TICKET-LLM-552"
    assert "TICKET-LLM-552" in result["message"]
    # Verify tool call was routed through tool_invoker
    assert mock_invoker.call_tool.called
    assert mock_invoker.call_tool.call_args[1]["tool_name"] == "ticket_create"

def test_model_backed_adapter_blocks_unauthorized_tools():
    """Verifies that unauthorized tool calls from model are blocked by the tool allowlist."""
    mock_responses = [
        {
            "content": None,
            "tool_calls": [
                {
                    "id": "call_malicious",
                    "type": "function",
                    "function": {
                        "name": "delete_all_database_records",
                        "arguments": "{}"
                    }
                }
            ],
            "finish_reason": "tool_calls"
        },
        {
            "content": "Unable to execute unauthorized tool.",
            "tool_calls": [],
            "finish_reason": "stop"
        }
    ]

    adapter = ModelBackedAgentAdapter(
        agent_id="test-model-allowlist",
        config={"mock_responses": mock_responses}
    )

    mock_invoker = MagicMock()
    result = adapter.run_task(
        task_input={"prompt": "Execute admin purge"},
        context={},
        tool_invoker=mock_invoker
    )

    # Tool was blocked: call_tool should NOT have been called with the unauthorized name
    assert not mock_invoker.call_tool.called
    # Decision was recorded
    assert any("unauthorized_tool_call_blocked" in str(c) for c in mock_invoker.record_decision.call_args_list)

def test_connect_existing_agent_api_framework(client: TestClient):
    """Verifies connecting a LangGraph framework agent through the universal connect API."""
    payload = {
        "id": "agent-fw-langgraph-test",
        "name": "Customer Support StateGraph",
        "connection_method": "agent_framework",
        "observability_level": "level_3_instrumented_tools",
        "version": "1.0.0",
        "supported_tools": ["ticket_create", "ticket_get", "ticket_query"],
        "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get", "state_inspection"],
        "framework_config": {
            "framework": "langgraph",
            "graph_target": "customer_support_graph",
            "max_steps": 10
        }
    }

    resp = client.post("/api/agents/connect-existing", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "agent-fw-langgraph-test"
    assert data["adapter_type"] == "langgraph"
    assert data["observability_level"] == "level_3_instrumented_tools"

    # Test connection
    conn_resp = client.post(f"/api/agents/{data['id']}/test-connection")
    assert conn_resp.status_code == 200
    assert conn_resp.json()["status"] == "healthy"

def test_connect_existing_agent_api_model_backed(client: TestClient):
    """Verifies connecting a Model-Backed agent through the universal connect API."""
    payload = {
        "id": "agent-model-backed-test",
        "name": "Support GPT-4o-Mini",
        "connection_method": "model_backed",
        "observability_level": "level_3_instrumented_tools",
        "version": "1.0.0",
        "supported_tools": ["ticket_create", "ticket_get", "ticket_query"],
        "declared_capabilities": ["ticket_create", "ticket_query", "ticket_get"],
        "llm_config": {
            "provider": "openai_compatible",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
            "secret_env_var": "OPENAI_API_KEY",
            "max_model_calls": 5,
            "max_tool_calls": 5
        }
    }


    resp = client.post("/api/agents/connect-existing", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "agent-model-backed-test"
    assert data["adapter_type"] == "model_backed"
    assert data["observability_level"] == "level_3_instrumented_tools"
