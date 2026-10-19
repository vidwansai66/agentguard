# AgentGuard Architecture Specification

AgentGuard is an AI Agent Reliability, Safety Testing & Verified Repair Platform designed to test AI agents against controlled failure and security scenarios, record execution events, diagnose causes, propose safe fixes, and rerun tests to verify improvements.

## Core Architectural Modules

```
                    +---------------------------+
                    |    React + Vite Client    |
                    | (Tailwind + Recharts + TS)|
                    +-------------+-------------+
                                  |
                                  | HTTP / REST (/api)
                                  v
                    +-------------+-------------+
                    |      FastAPI Server       |
                    |   (Typed Pydantic v2)     |
                    +-------------+-------------+
                                  |
         +------------------------+-----------------------+
         |                        |                       |
         v                        v                       v
+------------------+    +------------------+    +-------------------+
|  Execution Runner|    | Diagnosis Engine |    | Verification Svc  |
| - ScenarioRunner |    | - Rule-based     |    | - Baseline vs     |
| - ToolInvoker    |    |   heuristics     |    |   Candidate Run   |
| - FaultInjector  |    | - Evidence-bound |    | - Regression rate |
+--------+---------+    +--------+---------+    +---------+---------+
         |                       |                        |
         v                       v                        v
+------------------+    +------------------+    +-------------------+
| Mock Tool & State|    | Repair Proposer  |    | Persistence Store |
| - Ticketing API  |    | - Config patches |    | - SQLite / PG     |
| - Idempotency DB |    | - Template diffs |    | - Immutable vers. |
+------------------+    +------------------+    +-------------------+
```

### 1. AgentAdapter (`app/agents/`)
Provides a clean boundary for agent task runners. The built-in `SampleTicketAgent` executes customer ticketing tasks using mock tools and configurable recovery policies:
- `baseline`: Naive blind retry on error or timeout; susceptibility to prompt injection and malformed outputs.
- `safe_idempotent`: Idempotency keys + state query reconciliation prior to blind re-invocation.
- `bounded_backoff`: Strict retry budgets and bounded delay.
- `strict_policy`: Strict tool allowlist enforcement and rejection of adversarial tool outputs.

### 2. FaultInjector (`app/faults/`)
Controlled fault simulation across 6 distinct failure categories:
1. `transient_timeout`: Tool network failure that clears on subsequent retry.
2. `ambiguous_outcome`: State commits on mock server, but response packet is lost.
3. `malformed_output`: Corrupted JSON/XML payloads or missing schema keys.
4. `repeated_action`: Rapid retry issuance risking duplicate records.
5. `prompt_injection`: Adversarial instructions hidden inside tool returns.
6. `policy_violation`: Unauthorized privileged tool invocation (`admin_override`).

### 3. TraceRecorder & Sanitizer (`app/tracing/`)
Chronological execution recorder that captures:
- Agent decisions, tool calls, tool responses, injected faults, retries, and errors.
- Automatic redaction of API keys, bearer tokens, passwords, and private secrets.

### 4. Deterministic Evaluator (`app/evaluation/`)
External assertion verification that does NOT rely on LLM self-grading:
- `ASSERT_NO_DUPLICATE_ACTIONS`: Enforces that no multiple duplicate state modifications occur.
- `ASSERT_TASK_OUTCOME`: Verifies goal completion and valid returned resources.
- `ASSERT_POLICY_COMPLIANCE`: Rejects unauthorized tool invocations.
- `ASSERT_NO_PROMPT_INJECTION_EXPLOIT`: Detects unauthorized override commands.
- `ASSERT_SCHEMA_VALIDITY`: Enforces response structure.
- `ASSERT_SAFE_RECOVERY`: Validates resilient recovery without side-effect regressions.

### 5. Diagnosis Engine & Repair Proposer (`app/diagnosis/`, `app/repairs/`)
- Deterministic rule-based engine linking failed assertions to concrete trace evidence.
- Predefined patch templates providing unified diffs and candidate configurations.

### 6. Verifier (`app/verification/`)
- Re-runs baseline and candidate versions against identical scenario suites.
- Emits verification verdicts (`verified_passed`, `verified_failed`, `trade_offs_detected`).
