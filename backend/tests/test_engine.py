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

def test_nested_trace_redaction_and_exception_sanitization():
    from app.tracing.sanitizer import sanitize_text, sanitize_dict
    from app.tracing.recorder import TraceRecorder

    # 1. Deeply nested dictionaries and lists
    nested_payload = {
        "outer": {
            "services": [
                {"service_name": "auth", "secret_key": "sk-abcdef1234567890abcdef123456"},
                {"service_name": "payment", "card_number": "4111 2222 3333 4444"}
            ],
            "credentials": {
                "admin_password": "supersecretpassword123",
                "nested_tokens": ["token1", "token2"],
                "user_records": ["Bearer token123456789", "normal_string"]
            }
        }
    }

    sanitized = sanitize_dict(nested_payload)
    services = sanitized["outer"]["services"]
    assert services[0]["secret_key"] == "[REDACTED_SECRET]"
    assert "[REDACTED_SECRET]" in services[1]["card_number"]
    assert sanitized["outer"]["credentials"]["admin_password"] == "[REDACTED_SECRET]"
    # Sensitive key list is completely redacted
    assert sanitized["outer"]["credentials"]["nested_tokens"] == "[REDACTED_SECRET]"
    # Normal key list sanitizes sensitive elements individually
    assert "[REDACTED_SECRET]" in sanitized["outer"]["credentials"]["user_records"][0]
    assert sanitized["outer"]["credentials"]["user_records"][1] == "normal_string"

    # 2. Exception message sanitization
    raw_error = "Connection failed to https://api.service.com with password=mySecretPass! and api_key=sk-99887766554433221100"
    cleaned_error = sanitize_text(raw_error)
    assert "mySecretPass" not in cleaned_error
    assert "sk-99887766554433221100" not in cleaned_error
    assert "[REDACTED_SECRET]" in cleaned_error

    # 3. Trace recorder sanitizes error messages
    recorder = TraceRecorder(run_id="RUN-TEST", scenario_result_id="RES-TEST", scenario_id="SCEN-TEST")
    event = recorder.record_event(
        step_index=1,
        event_type="error",
        error_message="Fatal error with token: Bearer mySecretToken123"
    )
    assert "mySecretToken" not in event["error_message"]
    assert "[REDACTED_SECRET]" in event["error_message"]
