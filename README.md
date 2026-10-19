# AgentGuard
### Universal AI Agent Reliability, Safety Testing & Verified Repair Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/Frontend-React%2018%20%7C%20Vite-61DAFB.svg)](https://vitejs.dev/)
[![TypeScript](https://img.shields.io/badge/Language-TypeScript-3178C6.svg)](https://www.typescriptlang.org/)
[![LangGraph](https://img.shields.io/badge/Framework-LangGraph-purple.svg)](https://langchain-ai.github.io/langgraph/)

AgentGuard is a full-stack evaluation and reliability platform for testing AI agents against controlled failure and security scenarios. It records execution traces, diagnoses root causes, proposes safe repairs, and runs differential benchmarks to verify whether fixes improve reliability without introducing regressions or unsafe duplicate side effects.

---

## Architecture & Integration Modes

AgentGuard provides a **Universal Integration Contract** supporting four connection architectures:

```
                  +-------------------------------------------------------+
                  |               AgentGuard Platform Core               |
                  |  (Registry, Runner, Fault Injector, Evaluator, Trace) |
                  +-------------------------------------------------------+
                                              |
                   +--------------------------+--------------------------+
                   |                          |                          |
                   v                          v                          v
          [Type A: Python]             [Type B: HTTP]          [Type C: Frameworks]
       CallableAgentWrapper          HttpAgentAdapter        LangGraphAgentAdapter
       (In-process callables)      (Remote microservices)     (Compiled StateGraphs)
                                              |
                                              v
                                   [Type D: Model-Backed]
                                  ModelBackedAgentAdapter
                                 (OpenAI-compatible LLMs)
```

### The 4 Connection Paradigms

1. **Connection Type A — Existing Python Projects (`CallableAgentWrapper`)**:
   - Wrap existing standalone Python functions or classes without altering their internal code.
   - Automatically provides instrumented mock tools to functions that accept a `tools` parameter.
   - In-process execution is strictly restricted to vetted, registered adapters; arbitrary file uploads and dynamic `eval`/`exec` are strictly prohibited.
2. **Connection Type B — HTTP / REST API Agents (`HttpAgentAdapter`)**:
   - Connect remote agent services over HTTP/REST.
   - Dot-notation JSON response extraction (`result_path`, `status_path`, `events_path`, `error_path`).
   - Server-Side Request Forgery (SSRF) defense: blocks AWS/GCP/Azure cloud metadata (`169.254.169.254`), multicast, broadcast, and private subnets unless local dev mode is explicitly enabled.
   - Secrets are configured by environment variable reference (`secret_env_var`) and scrubbed from traces. Includes a built-in mock HTTP service for local development.
3. **Connection Type C — Agent Frameworks (`LangGraphAgentAdapter`)**:
   - **LangGraph (Supported & Verified)**: Executes compiled `StateGraph` workflows, captures node execution events into the trace timeline, and routes node-initiated tool calls through AgentGuard's `ToolInvoker`.
   - **CrewAI & AutoGen (Planned Roadmap)**: Adapter contracts designed; cataloged as planned future integrations. *CrewAI and AutoGen are not currently supported in this release.*
4. **Connection Type D — Model-Backed Agents (`ModelBackedAgentAdapter`)**:
   - Orchestrates multi-turn reasoning loops with OpenAI-compatible chat completion endpoints.
   - Enforces a strict tool allowlist (`create_ticket`, `get_ticket_status`, `query_tickets`). Unauthorized tool calls proposed by the model are blocked and recorded in the trace.
   - Routes tool calls through the controlled `ToolInvoker` for fault injection.
   - Bounded execution safeguards: maximum model calls (default 5), maximum tool calls (default 5), and request timeouts.
   - *Requirement Notice*: Live provider execution requires setting the API key environment variable (e.g. `OPENAI_API_KEY`). Default test suites run with local mock providers and require **no paid credentials**.

---

## Unified Execution Observability Levels

AgentGuard distinguishes three explicit levels of observability:

| Observability Level | Description | Capabilities & Fault Injections Supported | Evaluation Guarantees |
| :--- | :--- | :--- | :--- |
| **LEVEL 1 — Result-only** (`level_1_result_only`) | The external agent returns only task output strings or final payloads. Internal steps are opaque. | Evaluates final outputs against schema assertions. **Cannot** inject or observe tool-level faults. | Output evaluation only. Evaluator explicitly records opaque tool visibility. |
| **LEVEL 2 — Structured-event** (`level_2_structured_events`) | The external agent reports intermediate step timings, node transitions, and errors. | Reconstructs the complete execution timeline. Tool calls are visible for post-hoc inspection. | Full timeline observability and step-count tracking. Fault injection remains external. |
| **LEVEL 3 — Instrumented-tools** (`level_3_instrumented_tools`) | The agent routes tool operations through AgentGuard's controlled tool registry. | **Full reliability testing**: Injects transient timeouts, duplicate actions, ambiguous outcomes, and malformed outputs. | Comprehensive fault injection, trace coverage, policy verification, and side-effect guarantees. |

### Pre-Flight Observability Compatibility
Before executing a scenario, AgentGuard verifies whether the agent's observability level satisfies scenario requirements:
- If a scenario requires tool-level fault injection (`ambiguous_outcome`, `transient_timeout`, `repeated_action`, `malformed_output`, `policy_violation`) but the connected agent provides only **Level 1 (Result-Only)**:
  - The UI flags an observability mismatch and disables run execution.
  - The runner records `status="unsupported"` with rule finding `ASSERT_OBSERVABILITY_COMPATIBILITY`.
  - **Unsupported tests are never counted as passing tests.**

---

## 6 Controlled Failure Scenarios

1. **Transient Timeout**: Simulated 504 network dropouts with bounded retry recovery.
2. **Ambiguous Outcome**: Remote action commits, but response is lost (duplicate ticket detection).
3. **Malformed Output**: Corrupted raw text or missing required response schema attributes.
4. **Repeated Action**: Blind retry amplification without state verification.
5. **Prompt Injection**: Untrusted tool output containing prompt-injection escape instructions.
6. **Policy Violation**: Unauthorized tool calls blocked by access-control allowlists.

---

## Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Recharts, React Router v6
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, SQLite (PostgreSQL compatible)
- **Agent Frameworks**: LangGraph v0.2+ / v1.0+ (`langgraph.graph.StateGraph`)
- **Testing**: pytest, Starlette TestClient, httpx

---

## Quick Start (Windows Setup Instructions)

### Prerequisites
- Python 3.11 or newer (`python --version`)
- Node.js 18 or newer (`node --version`)
- Git (`git --version`)

### 1. Clone the Repository
```powershell
git clone <repository-url>
cd AgentGuard
```

### 2. Configure Environment
```powershell
# Copy the example environment file
Copy-Item .env.example .env
```
*(The default configuration uses SQLite and local development defaults with zero external dependencies.)*

### 3. Backend Setup (PowerShell)
```powershell
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The FastAPI backend will start at `http://127.0.0.1:8000` with Swagger documentation at `http://127.0.0.1:8000/docs`.

### 4. Frontend Setup (PowerShell)
In a new PowerShell terminal:
```powershell
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5174` (or `http://localhost:5173`) in your browser. All `/api` requests are automatically proxied to `http://127.0.0.1:8000`.

---

## Test Commands & Verification

### Run the Backend Pytest Suite (54 Tests)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
```
*Expected: 54 passed in ~4s (Exit code: 0).*

### Run the End-to-End Acceptance Suite
```powershell
cd backend
python verify_universal_acceptance.py
```
*Expected: All 6 acceptance workflows (Python Callable, HTTP Mock, LangGraph StateGraph, Model-Backed Agent, Observability Compatibility, Baseline/Candidate Verification) succeed with zero errors (Exit code: 0).*

### Run the Frontend Production Build
```powershell
cd frontend
npm run build
```
*Expected: TypeScript compilation (`tsc`) and Vite bundling succeed with exit code 0.*

---

## Understanding the Sample Agent Benchmark

When running `SCEN-03-AMBIGUOUS-OUTCOME` against the built-in sample agent:

1. **Baseline Run (`1.0.0`)**:
   - The naive baseline strategy does not check state or supply an idempotency key.
   - When the response is lost after commit, the agent retries blindly, creating a second ticket.
   - AgentGuard's deterministic evaluator independently catches the defect:
     - `ASSERT_NO_DUPLICATE_ACTIONS (failed): Duplicate side effect detected: 2 tickets were created in backend state instead of 1.`
     - Result: `passed=0, unsafe_side_effects=1`.
   - **This failure is the intended ground truth**: it demonstrates that the fault injector and evaluator correctly detect unhandled side effects.
2. **Candidate Run (`1.1.0-patch`)**:
   - The candidate version employs the `safe_idempotent` strategy (`enable_idempotency_check=True`).
   - It performs pre-flight state inspection, detects that the ticket was already committed, and prevents duplicate creation.
   - Result: `passed=1, unsafe_side_effects=0, recovered=1`.
3. **Differential Verifier Pass**:
   - The Verifier compares baseline vs candidate runs:
   - Success rate improves: `0% -> 100%`.
   - Unsafe duplicate rate drops: `100% -> 0%`.
   - Verification verdict: **`verified_passed`**.

---

## Security Boundaries & Known Limitations

1. **Not an Operating System Sandbox**:
   - In-process Python adapters run with host process permissions. Only pre-registered, trusted Python classes and callables from `app.agents.registry` may be instantiated.
   - Arbitrary script uploading or dynamic expression evaluation is prohibited.
2. **HTTP Egress Filtering**:
   - Outbound HTTP requests block private networks, cloud metadata services (`169.254.169.254`), and loopback addresses unless `allow_local_dev=True` is explicitly authorized.
   - Redirects are disabled by default. TLS certificate verification is enforced.
3. **Model Integration Boundaries**:
   - External models never execute arbitrary tools directly; all invocations are validated against the tool allowlist.
   - Live model execution requires setting credentials in the host environment (`OPENAI_API_KEY`).
4. **Research Disclaimer**:
   - AgentGuard is a developer testing and verification prototype designed for local reliability benchmarking; it is not claimed as a production-hardened platform.

---

## License

This project is licensed under the [MIT License](LICENSE).
