# AgentGuard — 3–5 Minute Recruiter & Technical Demonstration Script

This script provides a concise, reproducible walkthrough of the AgentGuard platform for technical interviewers, hiring managers, and recruiters.

---

## ⏱️ Demonstration Timeline (3–5 Minutes)

| Time | Stage | Screen / Action | What It Proves |
|---|---|---|---|
| **0:00 – 0:45** | **The Problem & Platform Overview** | Dashboard (`/`) | Sets the context: LLM benchmarks measure prompt answers, but production AI agents fail via silent side effects, lost acknowledgments, and naive retries. |
| **0:45 – 1:30** | **Agent Integration & Observability** | Agents Catalog (`/agents`) | Demonstrates universal connectivity: Python SDK callable wrappers (Level 2), HTTP endpoints (Level 1/2), LangGraph (Level 3), and OpenAI-compatible models. Highlights observability levels. |
| **1:30 – 2:45** | **Scenario 12: Duplicate Action Prevention** | Run Execution (`/execution`) & Run Details (`/runs/:id`) | Executes `SCEN-12-DUPLICATE-PREVENTION`. Shows the live trace proving: request 1 created ticket, request 2 reused the identical ticket ID with `is_duplicate=True`, and zero redundant tickets were created. |
| **2:45 – 3:30** | **The Real Production Bug & Verified Fix** | Trace Viewer & Diff | Explains the real bug: adapter `request_mapping` previously dropped idempotency keys. Explains how the fix in `de6f89b` preserves headers and payload, and how strict verification flags unsafe side effects if duplicate flags are missing or false. |
| **3:30 – 4:30** | **Diagnosis & Verified Candidate Repair** | Diagnosis (`/repairs`) & Comparison (`/comparison`) | Shows the diagnosis engine linking trace evidence to root causes, and shows candidate verification comparing baseline (naive retry, duplicate ticket) vs candidate (idempotent recovery) with 0 regressions. |

---

## 📋 Step-by-Step Script

### Step 1: Dashboard Overview (0:00 – 0:45)
* **Navigate to**: `https://agentguard-chi.vercel.app/` (or `http://localhost:5173`)
* **Talking Points**:
  > *"Most agent evaluation platforms today look like prompt benchmarks: they grade whether the LLM produced a polite answer. But in real-world systems, AI agents fail when interacting with stateful tools: an API timeout causes a blind retry, and a customer is billed twice or two support tickets are created for one issue.*
  >
  > *AgentGuard was built to solve this: it executes agents against controlled fault scenarios, captures structured traces, validates explicit safety assertions, and deterministically compares candidate fixes against baselines."*
* **Highlights to Show**:
  - Live reliability metrics: Task Success Rate, Recovery Rate, Unsafe Side-Effect Rate.
  - Active agents and seeded scenario catalog.

---

### Step 2: Agent Registry & Observability Contracts (0:45 – 1:30)
* **Navigate to**: Agents Catalog (`/agents`)
* **Talking Points**:
  > *"To test external agents without forcing a rewrite, AgentGuard supports four integration paths: trusted Python SDK wrappers, HTTP microservices, LangGraph graphs, and OpenAI-compatible model-backed agents.*
  >
  > *Crucially, we enforce three distinct Observability Levels: Level 1 (Result-Only), Level 2 (Structured Events), and Level 3 (Instrumented Tools). If an agent only provides Level 1 result-only observability, AgentGuard honestly blocks tool-level fault scenarios because internal tool interceptions cannot be verified without instrumentation."*
* **Highlights to Show**:
  - `agent-ticket-sample`: Built-in instrumented baseline & candidate (Level 3).
  - `agent-home`: Connected external HTTP agent service (`/run`).
  - Observability compatibility badges.

---

### Step 3: Scenario 12 — Duplicate Prevention via Idempotency (1:30 – 2:45)
* **Navigate to**: Run Execution (`/execution`), select `agent-home`, select scenario `SCEN-12-DUPLICATE-PREVENTION`, click **"Start Controlled Test Run"**.
* **Navigate to**: Run Details (`/runs/<run_id>`)
* **Talking Points**:
  > *"Here we run Scenario 12: Duplicate Ticket Prevention via Idempotency. This scenario issues an initial ticket creation request with idempotency key `idemp-vpn-duplicate-001`, and then immediately probes with an equivalent second request.*
  >
  > *Let's look at the actual trace in the trace inspector:*
  > 1. *`http_dispatch_start`: Transmits `idempotency_key=idemp-vpn-duplicate-001` via JSON payload and `X-Idempotency-Key` / `Idempotency-Key` headers.*
  > 2. *`http_response` (First call): Target creates ticket `TICK-HTTP-...` with `is_duplicate: False`.*
  > 3. *`duplicate_probe_start`: Dispatches the second equivalent request.*
  > 4. *`http_response` (Second call): Target recognizes the key, reuses the identical ticket ID `TICK-HTTP-...`, and reports `is_duplicate: True`.*
  > 5. *`duplicate_probe_verified`: Confirms matching ticket IDs, explicit `is_duplicate=True`, and zero redundant records.*
  > 6. *Assertion `ASSERT_NO_DUPLICATE_ACTIONS`: Evaluates to PASSED."*

---

### Step 4: The Real Engineering Bug & Verified Fix (2:45 – 3:30)
* **Talking Points**:
  > *"This scenario actually caught a real integration bug during our live deployment testing:*
  >
  > *When connecting external HTTP agents with custom `request_mapping` (like `query: prompt`, `session_id: run_id`), the adapter built the outbound payload by iterating only through the mapped keys. As a result, `idempotency_key` was stripped from the request payload and headers! The backend service received no idempotency key, generated two completely different tickets (`TICK-HTTP-10F0D719` and `TICK-HTTP-CFCE415C`), and returned `is_duplicate: false`.*
  >
  > *Our fix in commit `de6f89b`:*
  > - *Preserves `idempotency_key` in the request payload even when `request_mapping` is present, without overwriting custom mappings.*
  > - *Automatically sends `X-Idempotency-Key` and `Idempotency-Key` HTTP headers.*
  > - *Enforces strict duplicate verification in the evaluator: if `is_duplicate` is false, missing, or the ticket IDs differ, the scenario fails honestly and records an unsafe side effect.*
  >
  > *We verified this with 75 unit tests and confirmed the fix on the live Render backend (`RUN-2507978caa`)."*

---

### Step 5: Diagnosis, Repair & Baseline Comparison (3:30 – 4:30)
* **Navigate to**: Comparison (`/comparison`) or Repairs (`/repairs`)
* **Talking Points**:
  > *"Finally, when an agent fails (for instance, the baseline agent under an ambiguous outcome dropped-packet fault), AgentGuard's Diagnosis Engine parses the trace events, identifies the root cause (e.g., duplicate action after timeout), and generates a verified repair candidate.*
  >
  > *In the Comparison view, we compare the baseline version against the patched candidate version under the identical fault scenario. The baseline has a 0% success rate and 100% unsafe side effect rate. The candidate recovers state via query/idempotency, achieving a 100% success rate with 0 regressions."*

---

## 🎯 Key Takeaways for Technical Interviewers
1. **Empirical Verification Over LLM Self-Reports**: Does not trust the agent's claim that a task succeeded; independently evaluates observable database/tool state.
2. **Strict Safety Invariants**: Flags unsafe side effects (e.g. duplicate payments, duplicate tickets) as hard failures even if the final HTTP status code is 200.
3. **Universal Adapter Architecture**: Modular design for Python, HTTP, LangGraph, and model-backed agents with contract-driven observability enforcement.
4. **Reproducible Test Suite**: 75 automated pytest backend tests and frontend Vitest suite passing with zero flaky tests.
