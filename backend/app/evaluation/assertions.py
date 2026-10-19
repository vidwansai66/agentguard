from dataclasses import dataclass, field
from typing import Any

@dataclass
class AssertionResult:
    rule_id: str
    rule_name: str
    passed: bool
    severity: str # low, medium, high, critical
    message: str
    explanation: str
    trace_event_ids: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
