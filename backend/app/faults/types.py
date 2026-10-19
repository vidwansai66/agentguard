from enum import Enum

class FaultType(str, Enum):
    TRANSIENT_TIMEOUT = "transient_timeout"
    AMBIGUOUS_OUTCOME = "ambiguous_outcome"
    MALFORMED_OUTPUT = "malformed_output"
    REPEATED_ACTION = "repeated_action"
    PROMPT_INJECTION = "prompt_injection"
    POLICY_VIOLATION = "policy_violation"
    NORMAL_EXECUTION = "normal_execution"
