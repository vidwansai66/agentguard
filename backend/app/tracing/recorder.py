import uuid
from datetime import datetime
from typing import Any
from app.tracing.sanitizer import sanitize_dict, sanitize_text

class TraceRecorder:
    def __init__(self, run_id: str, scenario_result_id: str, scenario_id: str):
        self.run_id = run_id
        self.scenario_result_id = scenario_result_id
        self.scenario_id = scenario_id
        self.events: list[dict[str, Any]] = []

    def record_event(
        self,
        step_index: int,
        event_type: str,
        action_name: str | None = None,
        tool_name: str | None = None,
        severity: str = "info",
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        fault_details: dict[str, Any] | None = None,
        retry_count: int = 0,
        duration_ms: float = 0.0,
        error_message: str | None = None
    ) -> dict[str, Any]:
        event_id = f"EVT-{uuid.uuid4().hex[:12]}"
        event = {
            "id": event_id,
            "run_id": self.run_id,
            "scenario_result_id": self.scenario_result_id,
            "scenario_id": self.scenario_id,
            "step_index": step_index,
            "event_type": event_type,
            "severity": severity,
            "action_name": action_name,
            "tool_name": tool_name,
            "sanitized_input": sanitize_dict(input_data or {}),
            "sanitized_output": sanitize_dict(output_data or {}),
            "fault_details": sanitize_dict(fault_details or {}),
            "retry_count": retry_count,
            "duration_ms": duration_ms,
            "error_message": sanitize_text(error_message),
            "timestamp": datetime.utcnow()
        }
        self.events.append(event)
        return event

    def get_events(self) -> list[dict[str, Any]]:
        return self.events
