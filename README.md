 <div align="center">

# 🛡️ AgentGuard

### AI Agent Reliability Testing & Safety Evaluation

**Test how AI agents fail. Understand why they fail. Verify whether a proposed fix actually works.**

An actively developed research MVP for testing AI agents under controlled failure conditions, analyzing execution traces, detecting unsafe side effects, and verifying candidate fixes against a baseline.

<br />

<a href="https://agentguard-chi.vercel.app/"><strong>🚀 Live Dashboard</strong></a> &nbsp; • &nbsp;
<a href="https://github.com/vidwansai66/agentguard"><strong>💻 Source Code</strong></a> &nbsp; • &nbsp;
<a href="https://agentguard-p14p.onrender.com/docs"><strong>📚 API Documentation</strong></a>

<br />

<img src="https://img.shields.io/badge/Status-Active%20Development-0f9d8a?style=for-the-badge" alt="Active development" />
<img src="https://img.shields.io/badge/Project-Research%20MVP-2563eb?style=for-the-badge" alt="Research MVP" />
<img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
<img src="https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-3178c6?style=for-the-badge&logo=typescript&logoColor=white" alt="React and TypeScript" />

</div>

---

## 🎯 What is AgentGuard?

AI agents can fail in ways that ordinary success/failure checks do not fully capture. They may repeat an action, produce malformed output, encounter ambiguous external responses, or violate an expected safety condition.

**AgentGuard is being built to make these failures observable and testable.**

It executes supported agents against defined scenarios, collects available execution evidence, evaluates explicit assertions, and helps developers investigate failures and assess whether a candidate fix improves behavior.

Rather than relying only on an agent's self-reported success, AgentGuard evaluates observable evidence against defined test expectations.

## ✨ Core Capabilities

| Capability | Description |
|---|---|
| 🧪 Scenario-Based Testing | Run agents against predefined reliability and safety scenarios. |
| ⚡ Fault Injection | Test supported failure conditions, including timeouts, ambiguous outcomes, and malformed outputs. |
| 🔍 Execution Tracing | Capture structured execution evidence according to the selected integration's observability level. |
| 🛡️ Safety Assertions | Evaluate observable behavior against explicit assertions and detect configured unsafe side effects. |
| 🩺 Failure Diagnosis | Produce evidence-linked diagnostic information to help investigate failures. |
| 🔄 Candidate Verification | Compare candidate behavior against a baseline using defined tests. |
| 🔁 Idempotency Testing | Check whether repeated requests cause duplicate actions in supported integrations. |
| 📊 Results Dashboard | Explore test runs, scenarios, outcomes, execution traces, and evaluation metrics. |

## 🖥️ Live Demo

**Explore the deployed application:**  
https://agentguard-chi.vercel.app/

**Backend API:**  
https://agentguard-p14p.onrender.com

**Interactive API documentation:**  
https://agentguard-p14p.onrender.com/docs

> **Demo note:** The backend uses Render's free tier. The first request after inactivity may take time because the service can need to wake up. SQLite data stored on an ephemeral filesystem may not persist across restarts or redeployments.

## 🏗️ Technology Stack

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- React Router
- Lucide React
- Vitest

### Backend
- Python 3.11
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite
- Pytest

### Agent Integration
- Python SDK wrappers
- HTTP/REST adapters
- LangGraph integration
- OpenAI-compatible model integrations

*Supported behavior depends on the adapter contract, agent configuration, and available observability.*

## 🔬 How It Works

1. **Configure an agent** using a supported integration path.
2. **Select a scenario** that defines the expected behavior and relevant failure conditions.
3. **Execute the test** under the configured conditions.
4. **Collect observable evidence** through the integration's available tracing and event mechanisms.
5. **Evaluate assertions** to identify failed expectations and potential unsafe side effects.
6. **Inspect the diagnosis** and the evidence supporting the result.
7. **Verify a candidate fix** against the baseline using the defined evaluation criteria.

## 🧩 Observability Model

AgentGuard uses integration-dependent observability levels:

- **Level 1 — Result-only:** The final result is available, but internal execution details may be limited.
- **Level 2 — Structured events:** Additional execution events are available for evaluation.
- **Level 3 — Instrumented tools:** Tool-level instrumentation can provide more detailed evidence.

Not every test is meaningful with every observability level. AgentGuard may refuse scenarios that require tool-level evidence when the selected integration cannot provide sufficient observability.

## 🧪 Example Scenarios

| Scenario | What it evaluates |
|---|---|
| Normal Create | Expected behavior during a standard operation. |
| Transient Timeout | Behavior when an operation encounters a timeout. |
| Ambiguous Outcome | Handling of uncertain results after a request. |
| Repeated Action | Whether repeated execution causes unintended duplicate effects. |
| Idempotency Check | Whether repeated requests are handled consistently. |
| Malformed Output | Handling of invalid or unexpected output. |

## ✅ Engineering Validation

A completed implementation milestone addressed an idempotency issue in the HTTP adapter.

**Verified behavior:** The same idempotency key is preserved through the supported request path, and a repeated request returns the same ticket identifier rather than creating a redundant ticket.

- Live verification run: `RUN-2507978caa`
- Ticket identifier: `TICK-HTTP-8EA5A20A`
- Duplicate flag: `is_duplicate=True`
- Redundant tickets created by the repeated request: `0`

This demonstrates a tested behavior in the supported integration path; it is not a claim that every agent or external service is automatically protected against duplicate actions.

## 🗺️ Current Scope & Limitations

AgentGuard is a **research MVP in active development**, not a production safety certification platform.

- It supports defined adapters and integration contracts; it does not yet universally import and test arbitrary GitHub repositories with zero configuration.
- Existing projects may require an appropriate entry point, adapter configuration, and sufficient observability.
- Untrusted agent code and external HTTP integrations require appropriate isolation, network restrictions, and credential boundaries.
- Diagnostic results depend on the evidence available to the selected integration.
- The deployed SQLite setup may lose stored history following a restart or redeployment.

These limitations are part of the current scope and guide the next stages of development.

## 🚧 Development Roadmap

- [ ] Broader GitHub repository and local project integration
- [ ] Easier agent entry-point discovery and configuration
- [ ] Stronger isolation for untrusted agent execution
- [ ] Expanded observability and trace collection
- [ ] More reliability and safety scenarios
- [ ] More comprehensive baseline-versus-candidate evaluation
- [ ] Persistent storage for deployed environments

## 🧑‍💻 Run Locally

### Prerequisites
- Node.js and npm
- Python 3.11
- Git

### 1. Clone the repository

```bash
git clone https://github.com/vidwansai66/agentguard.git
cd agentguard
```

### 2. Start the backend

Create and activate a Python virtual environment in your preferred way, then install the backend dependencies listed in the repository's backend dependency files.

Start the FastAPI application using the entry point and environment configuration documented in the backend.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite.

*Consult the repository's current setup instructions for the exact backend entry point, dependency file, and required environment variables.*

## 🧪 Testing

Run the checks supported by the repository:

- Backend tests with `pytest`
- Frontend tests with `npm test`
- Frontend production build with `npm run build`

Use the scripts defined in the current `package.json` and backend configuration if their names differ.

## 🤝 Contributing

Suggestions, bug reports, and ideas for improving agent reliability testing are welcome. Please open an issue to discuss substantial changes before submitting a pull request.

## 📄 License

No license is specified here. Check the repository for an existing license before reusing or distributing this project.

---

<div align="center">

**Built to investigate AI agent failures with evidence, testing, and engineering discipline.** 🛡️

*AgentGuard — Research MVP · Actively in Development*

</div>
