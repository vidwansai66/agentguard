import pytest
from app.runner.executor import scenario_runner
from app.tracing.sanitizer import sanitize_dict

def test_normal_successful_execution():
    scenario = {
        "id": "SCEN-TEST-NORMAL",
        "name": "Test Normal Scenario",
        "failure_type": "normal_execution",
        "task_input": {
            "action": "create_ticket",
            "title": "Test Title",
            "description": "Test Description",
            "priority": "low"
        },
        "expected_outcome": {"status": "success"},
        "fault_parameters": {"fault_type": "normal_execution"},
        "allowed_tools": ["ticket_create", "ticket_query", "ticket_get"],
        "execution_limits": {"max_steps": 10}
    }

    result = scenario_runner.run_scenario(
        scenario_data=scenario,
        agent_id="agent-ticket-sample",
        agent_version="1.0.0",
        agent_strategy="baseline"
    )

    assert result["status"] == "passed"
    assert result["passed"] is True
    assert result["has_unsafe_side_effect"] is False
    assert result["execution_output"]["ticket_id"] is not None
    assert len(result["trace_events"]) > 0

def test_trace_redaction_sanitizer():
    sensitive_payload = {
        "api_key": "sk-1234567890abcdef1234567890",
        "password": "supersecretpassword123",
        "token": "my_bearer_token",
        "user_note": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz",
        "safe_field": "public_data"
    }

    sanitized = sanitize_dict(sensitive_payload)

    assert sanitized["api_key"] == "[REDACTED_SECRET]"
    assert sanitized["password"] == "[REDACTED_SECRET]"
    assert sanitized["token"] == "[REDACTED_SECRET]"
    assert "[REDACTED_SECRET]" in sanitized["user_note"]
    assert sanitized["safe_field"] == "public_data"
