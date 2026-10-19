# AgentGuard
### AI Agent Reliability, Safety Testing & Verified Repair Platform

AgentGuard is a full-stack developer tool designed to test AI agents against controlled failure and security scenarios, record execution traces, diagnose root causes, propose safe repairs, and run differential benchmarks to verify whether fixes improve reliability without introducing regressions or unsafe side effects.

---

## Key Features

- **Empirical Dashboard**: Real-time reliability KPIs (Task Success Rate, Fault Recovery Rate, Unsafe Side-Effect Rate, Median Latency) calculated from persisted SQLite execution runs.
- **6 Failure Injection Categories**:
  1. *Transient Timeout*: Simulated 504 network dropouts with recovery.
  2. *Ambiguous Outcome*: Remote action commits, but response is lost (duplicate ticket detection).
  3. *Malformed Output*: Corrupted raw text / missing response schema attributes.
  4. *Repeated Action*: Blind retry amplification.
  5. *Prompt Injection*: Untrusted tool comments attempting instruction override.
  6. *Policy Violation*: Disallowed tool invocation attempts.
- **Deterministic Evaluator**: Independent rule-based assertions (`ASSERT_NO_DUPLICATE_ACTIONS`, `ASSERT_TASK_OUTCOME`, `ASSERT_POLICY_COMPLIANCE`, etc.) without LLM self-grading.
- **Evidence-Based Diagnosis**: Rule-based engine linking failed assertions directly to chronological trace event IDs.
- **Candidate Repair & Verification**: Template-based patch diffs, human approval gating, and differential comparison against baseline runs.
- **Trace Explorer & Sanitizer**: Interactive timeline with expandable payloads and automatic secret redaction.

---

## Technology Stack

- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Lucide Icons, Recharts, React Router
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy, SQLite (PostgreSQL compatible)
- **Testing**: pytest

---

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ & npm

### 2. Backend Setup
```bash
# In project root
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
The FastAPI backend will start at `http://127.0.0.1:8000` with interactive API docs at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
```bash
# In a new terminal window
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. All `/api` requests are automatically proxied to the FastAPI server.

### 4. Running Backend Tests
```bash
# From project root
backend\.venv\Scripts\pytest backend/tests/ -v
```

---

## End-to-End Acceptance Test Workflow

1. Open the dashboard at `http://localhost:5173`.
2. Inspect the registered sample agent on the **Agents** page (`/agents`).
3. Navigate to **Test Scenarios** (`/scenarios`) and pick `SCEN-03-AMBIGUOUS-OUTCOME` (Ambiguous Outcome — Lost Response After Commit).
4. Launch the baseline agent (`1.0.0`) on this scenario in **Run Execution** (`/execution`).
5. Notice that the naive baseline agent creates a duplicate ticket after the dropped response, failing `ASSERT_NO_DUPLICATE_ACTIONS`.
6. Open **Runs & Traces** (`/runs`) and inspect the chronological execution timeline.
7. Click **Diagnose & Propose Fix** to open the **Diagnosis & Repair** page (`/repairs`).
8. Review the diagnosis (Root cause: Missing idempotency / duplicate check) and the proposed patch template (`TEMPLATE_IDEMPOTENCY_CHECK`).
9. Click **Approve Candidate Fix** to approve candidate version `1.1.0-patch`.
10. Click **Run Candidate Verification** to execute the candidate against identical conditions.
11. View the **Comparison Report** (`/comparison`), observing:
    - Candidate success rate improves to 100%
    - Unsafe duplicate side effects drop to 0%
    - Zero regressions detected
    - Verification verdict: `verified_passed`.
12. Return to the **Overview Dashboard** (`/`) and confirm that all metrics reflect actual recorded execution history.
>>>>>>> 7de42e6 (feat: complete AgentGuard platform implementation)
