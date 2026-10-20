# AgentGuard 🛡️
### AI Agent Reliability Testing, Safety Evaluation & Verified Repair Platform

**Test how AI agents fail. Understand why they fail. Verify whether a proposed fix actually works.**

AgentGuard is an AI agent reliability-testing platform that executes agents under controlled failure conditions, captures structured execution traces, detects unsafe side effects, generates evidence-linked diagnoses, and verifies candidate repairs against an empirical baseline.

Instead of trusting an agent's self-reported claim that a task succeeded, AgentGuard evaluates observable tool actions and system state against explicit, deterministic assertions.

---

### 🌐 Live Deployments & Interactive Links

| Component | Target URL | Description |
|---|---|---|
| **Web Dashboard** | [https://agentguard-chi.vercel.app/](https://agentguard-chi.vercel.app/) | React + TypeScript + Vite interactive evaluation UI |
| **Backend API** | [https://agentguard-p14p.onrender.com](https://agentguard-p14p.onrender.com) | FastAPI reliability engine and execution runner |
| **Interactive Docs** | [https://agentguard-p14p.onrender.com/docs](https://agentguard-p14p.onrender.com/docs) | OpenAPI / Swagger interactive API documentation |
| **API Health** | [https://agentguard-p14p.onrender.com/health](https://agentguard-p14p.onrender.com/health) | Live system health and database status probe |
| **Recruiter Walkthrough** | [docs/recruiter-demo-script.md](docs/recruiter-demo-script.md) | 3–5 minute step-by-step demonstration script |

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5.2-3178C6?logo=typescript" alt="TypeScript">
  <img src="https://img.shields.io/badge/Backend_Tests-75%20Passing-success?logo=pytest" alt="Backend Tests">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/Status-Research_MVP-orange" alt="Research MVP">
</p>

---

## 🏗️ Architecture & Execution Flow

```mermaid
graph TD
    UI[AgentGuard React + Vite Dashboard] -->|REST API / Trace Events| API[FastAPI Backend Engine]
    API --> Adapters[Adapter Layer: Python SDK | HTTP/REST | LangGraph | OpenAI-Compatible]
    Adapters --> Interceptor[Fault Injection & Interception Engine]
    Interceptor --> Tools[Controlled Tool Registry / Mock Sandbox]
    Interceptor --> Trace[Structured Trace Recorder]
    Trace --> Eval[Deterministic Evaluator: Explicit Safety Assertions]
    Eval --> Diag[Evidence-Linked Diagnosis Engine]
    Diag --> Patches[Candidate Repair Proposals]
    Patches --> Verifier[Baseline vs Candidate Verifier]
    API <--> DB[(SQLite Database / PostgreSQL)]
```

---

## 📌 The Problem: Silent Agent Failures

AI agents interacting with real-world APIs fail in ways that conventional status codes and LLM benchmarks cannot detect:

1. **Blind Retries After Lost Acknowledgments**: An external API creates a resource (e.g. charging a payment or creating an enterprise support ticket), but the network acknowledgment times out. A naive agent assumes failure and retries blindly, creating duplicate records or charging twice.
2. **False Success Reports**: The LLM responds with a polite confirmation message (`"Successfully created your ticket"`), while the underlying system suffered an unsafe duplicate side effect or state corruption.
3. **Unverified Fixes**: Engineers patch prompts or agent logic without regression verification, unaware that fixing one failure mode introduced regressions across other scenarios.

AgentGuard addresses this by providing **controlled fault injection, deterministic trace assertion, and empirical candidate-versus-baseline verification**.

---

## 💡 What AgentGuard Does

| Capability | Technical Implementation | What It Solves |
|---|---|---|
| **Multi-Adapter Support** | Python SDK wrappers, HTTP/REST endpoints, LangGraph StateGraph, and OpenAI-compatible models | Evaluates any agent without requiring an architecture rewrite |
| **Contract-Driven Observability** | Enforces Level 1 (Result-Only), Level 2 (Structured Events), and Level 3 (Instrumented Tools) | Prevents claiming tool fault coverage for uninstrumented agents |
| **Fault Injection** | Transient timeouts, ambiguous dropped packets, malformed outputs, repeated actions, prompt injection, and policy violations | Reproduces edge cases deterministically |
| **Trace-Level Assertions** | Independent evaluator checks actual tool calls, arguments, and side-effect counts | Catches duplicate actions and policy violations regardless of HTTP status |
| **Evidence-Linked Diagnosis** | Rules-based diagnostic engine maps trace event IDs directly to root causes | Eliminates guesswork when debugging agent failures |
| **Candidate Verification** | Side-by-side baseline vs candidate repair comparison under identical faults | Validates that a fix works and introduces 0 regressions before deployment |

---

## 🔬 Featured Case Study: Scenario 12 (Duplicate Action Prevention via Idempotency)

Scenario 12 (`SCEN-12-DUPLICATE-PREVENTION`) exercises an agent with two equivalent creation requests carrying the same idempotency key (`idemp-vpn-duplicate-001`).

```text
                  SCENARIO 12 EXECUTION FLOW
                             │
                             ▼
                 [Request 1: Idempotency Key K1]
                             │
                             ▼
                    Create Ticket Record
                  (Ticket: TICK-HTTP-8EA5A20A)
                  (is_duplicate: False)
                             │
                             ▼
                 [Request 2: Idempotency Key K1]
                             │
                             ▼
               Target Recognizes Idempotency Key
                  (Reuses: TICK-HTTP-8EA5A20A)
                  (is_duplicate: True)
                             │
                             ▼
              Evaluator Safety Assertions:
              ✓ Both requests return identical ticket ID
              ✓ Second request explicitly reports is_duplicate=True
              ✓ Exactly 1 ticket created in store (0 redundant tickets)
              ✓ ASSERT_NO_DUPLICATE_ACTIONS: PASSED
```

### The Real Integration Bug Diagnosed by AgentGuard
During live integration testing of the registered HTTP adapter `agent-home`, Scenario 12 initially failed:
- **First request** returned ticket `TICK-HTTP-10F0D719` (`is_duplicate: false`).
- **Second request** returned ticket `TICK-HTTP-CFCE415C` (`is_duplicate: false`).
- Both requests succeeded with HTTP 200, but a duplicate ticket was created in the database.

### The Root Cause & Verified Fix (Commit `de6f89b`)
1. **The Bug**: When users configured external HTTP agents using custom `request_mapping` (e.g. `{"query": "prompt", "session_id": "run_id"}`), `HttpAgentAdapter` built the outbound payload by iterating only over mapped keys. Consequently, `idempotency_key` was omitted from the outbound JSON payload and no idempotency headers were transmitted.
2. **The Fix**:
   - `HttpAgentAdapter` automatically preserves `idempotency_key` in the request body unless explicitly mapped to a custom key.
   - Automatically injects standard `X-Idempotency-Key` and `Idempotency-Key` HTTP request headers.
   - Trace event `http_dispatch_start` logs `idempotency_key` and outbound `payload_keys` for auditability.
   - `ScenarioRunner` enforces strict verification: if `is_duplicate` is false, missing, or ticket IDs differ, the duplicate probe fails honestly and flags an unsafe side effect.
3. **Live Production Proof (`RUN-2507978caa`)**:
   Executed live on Render against `agent-home`:
   - Request 1: `TICK-HTTP-8EA5A20A` (`is_duplicate: False`)
   - Request 2: `TICK-HTTP-8EA5A20A` (`is_duplicate: True`)
   - Evaluator confirmed `duplicate_prevented: True` with 0 redundant tickets created.

---

## 🧪 Core Experiment: The Ambiguous Timeout

AgentGuard compares naive retry behavior against safer state-recovery implementations under an ambiguous network timeout (lost ACK after commit):

| Metric | Baseline Agent (Blind Retry) | Candidate Agent (Query / Idempotent) |
|---|---:|---:|
| **Task Success Rate** | **0%** | **100%** |
| **Unsafe Side-Effect Rate** | **100%** (Duplicate ticket created) | **0%** (Idempotent reuse) |
| **Regressions Detected** | — | **0** |

*Note: Results are measured from controlled mock scenarios within AgentGuard and demonstrate the verification workflow.*

---

## 🔌 Supported Adapter Types & Observability Levels

AgentGuard integrates agents through standardized adapter contracts:

| Adapter Type | Implementation | Observability Level |
|---|---|---|
| **Python SDK Wrapper** | Callable wrapper with signature `(prompt, tools) -> dict` | **Level 2** (Structured Events) |
| **HTTP / REST Agent** | Endpoint invocation (`/run`) with request/response mapping | **Level 1** (Result-Only) or **Level 2** |
| **LangGraph** | Compiled StateGraph with tool intercept routing | **Level 3** (Instrumented Tools) |
| **Model-Backed Agent** | OpenAI-compatible API with controlled tool allowlists | **Level 3** (Instrumented Tools) |

### Observability Enforcement
If an agent only provides Level 1 (Result-Only) observability, AgentGuard **refuses to run tool-fault injection scenarios** (e.g. ambiguous outcomes or tool timeouts). Because the agent's internal tool invocations cannot be observed without instrumentation, AgentGuard honestly marks the scenario as unsupported rather than fabricating passing results.

---

## 🛠️ Getting Started Locally

### Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Node.js 18+ and npm
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/vidwansai66/agentguard.git
cd agentguard
```

### 2. Set Up and Run the Backend
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 3. Set Up and Run the Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
The application will open at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Running Automated Tests

### Backend Automated Test Suite
From the repository root (with virtual environment active):
```bash
pytest backend/tests -v
```
**Outcome**: 75 tests passing covering adapters, faults, evaluator rules, idempotency propagation, and security boundaries.

### Universal Integration Acceptance Suite
```bash
python backend/verify_universal_acceptance.py
```
**Outcome**: Validates all 6 integration paths (Python wrapper, HTTP service, LangGraph, Model-backed, Observability boundaries, and Evaluator verifier).

### Frontend Unit Tests & Production Build
```bash
cd frontend
npm test        # Runs Vitest unit tests
npm run build   # Type-checks (tsc) and generates production Vite bundle
```

---

## 🔐 Architecture Boundaries & Limitations

1. **Research MVP Scope**: AgentGuard is an engineering research platform designed for reproducible reliability testing. It does not replace formal safety certifications.
2. **SQLite Persistence on Free-Tier Hosting**: The backend currently uses SQLite (`sqlite:///./agentguard.db`). On free-tier platforms like Render without persistent disks, container redeployments reset dynamic run history to the seeded demo scenarios. For persistent multi-instance deployments, standard PostgreSQL is supported via `DATABASE_URL`.
3. **Sandboxing Boundary**: Built-in sample tools run within controlled Python mock sandboxes. External HTTP agents and custom Python callables execute with standard process permissions and require network/credential scoping in production.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) — see the `LICENSE` file for details.

Copyright (c) 2026 AgentGuard Contributors.

---

## 👤 Author

**B. Sai Vidwan**
- **GitHub**: [https://github.com/vidwansai66](https://github.com/vidwansai66)
- **LinkedIn**: [https://linkedin.com/in/vidwansai](https://linkedin.com/in/vidwansai)
- **Portfolio Repository**: [https://github.com/vidwansai66/agentguard](https://github.com/vidwansai66/agentguard)
