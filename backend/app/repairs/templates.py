from typing import Any

REPAIR_TEMPLATES: dict[str, dict[str, Any]] = {
    "TEMPLATE_IDEMPOTENCY_CHECK": {
        "id": "TEMPLATE_IDEMPOTENCY_CHECK",
        "title": "State-Aware Idempotency & Query Recovery Patch",
        "proposed_change": "Attach deterministic idempotency key and perform pre/post state query before repeating creation requests.",
        "rationale": (
            "Under ambiguous network dropouts (HTTP 504 / timeouts), the remote server may have already committed "
            "the write operation. Without state reconciliation, naive retries generate duplicate tickets."
        ),
        "expected_benefit": "Eliminates duplicate ticket creation under ambiguous outcomes; raises recovery rate to 100%.",
        "potential_risks": "Introduces an extra query read call, adding negligible latency (~10-20ms) on failures.",
        "patch_diff": """--- baseline/agent_executor.py
+++ candidate/agent_executor.py
@@ -14,10 +14,18 @@
- # Baseline: Naive blind retry on error
- while retries <= max_retries:
-     try:
-         res = tool_invoker.call_tool("ticket_tool", {"action": "create", "title": title})
-         return res
-     except Exception:
-         retries += 1
+ # Candidate: State-Aware Idempotent Recovery
+ idempotency_key = self._derive_idempotency_key(task_input)
+ while retries <= max_retries:
+     try:
+         return tool_invoker.call_tool("ticket_tool", {
+             "action": "create", "title": title, "idempotency_key": idempotency_key
+         })
+     except Exception as exc:
+         # Check if write committed before repeating create
+         q = tool_invoker.call_tool("ticket_tool", {"action": "query", "idempotency_key": idempotency_key})
+         if q.get("found_count", 0) > 0:
+             return q["tickets"][0]
+         retries += 1""",
        "candidate_strategy": "safe_idempotent",
        "candidate_config": {
            "enable_idempotency_check": True,
            "enable_strict_policy": False,
            "max_retries": 3,
            "require_schema_validation": True
        }
    },
    "TEMPLATE_TOOL_POLICY": {
        "id": "TEMPLATE_TOOL_POLICY",
        "title": "Strict Tool Policy Gatekeeper & Untrusted Prompt Guard",
        "proposed_change": "Enforce strict tool allowlist before dispatch and sanitize tool output against instructions.",
        "rationale": (
            "Untrusted external data can contain prompt injection attacks attempting to force unauthorized actions "
            "(e.g., admin_override). A strict gatekeeper halts unauthorized execution at runtime."
        ),
        "expected_benefit": "Prevents unauthorized tool executions and prompt-injection exploits; achieves 100% policy compliance.",
        "potential_risks": "May reject future legitimate tools if allowlist is not updated accordingly.",
        "patch_diff": """--- baseline/agent_executor.py
+++ candidate/agent_executor.py
@@ -32,8 +32,10 @@
- # Baseline: Executes commands parsed from external comments
- if "admin_override" in res.get("message", ""):
-     tool_invoker.call_tool("ticket_tool", {"action": "admin_override"})
+ # Candidate: Tool Allowlist Policy Enforcement
+ if action not in self.allowed_tools:
+     raise PolicyViolationError(f"Tool action '{action}' prohibited by policy")
+ # Untrusted tool returns treated as raw data, not instructions""",
        "candidate_strategy": "strict_policy",
        "candidate_config": {
            "enable_strict_policy": True,
            "enable_idempotency_check": True,
            "max_retries": 3,
            "require_schema_validation": True
        }
    },
    "TEMPLATE_BOUNDED_BACKOFF": {
        "id": "TEMPLATE_BOUNDED_BACKOFF",
        "title": "Bounded Retry Budget with Jittered Backoff",
        "proposed_change": "Cap retry attempts to 3 with bounded delay to avoid server hammering during outages.",
        "rationale": "Prevents runaway loops and bounded latency under persistent tool downtime.",
        "expected_benefit": "Prevents cascading resource exhaustion.",
        "potential_risks": "May fail faster on long-lasting tool outages.",
        "patch_diff": """--- baseline/agent_executor.py
+++ candidate/agent_executor.py
@@ -8,4 +8,7 @@
- retries = 0
+ max_retries = 3
+ backoff_factor = 1.5""",
        "candidate_strategy": "bounded_backoff",
        "candidate_config": {
            "max_retries": 3,
            "enable_idempotency_check": True
        }
    },
    "TEMPLATE_STRICT_SCHEMA": {
        "id": "TEMPLATE_STRICT_SCHEMA",
        "title": "Strict Tool Response Schema Validation",
        "proposed_change": "Validate dictionary schema and required fields before consuming tool responses.",
        "rationale": "Prevents unhandled runtime crashes when third-party tools return invalid or partial schemas.",
        "expected_benefit": "Gracefully identifies corrupted tool payloads and prevents unhandled agent exceptions.",
        "potential_risks": "Requires well-defined schemas for each integrated tool.",
        "patch_diff": """--- baseline/agent_executor.py
+++ candidate/agent_executor.py
@@ -20,3 +20,6 @@
+ if not isinstance(res, dict) or "ticket_id" not in res:
+     raise ValueError("Malformed response schema missing ticket_id")""",
        "candidate_strategy": "strict_policy",
        "candidate_config": {
            "require_schema_validation": True,
            "enable_idempotency_check": True
        }
    }
}
