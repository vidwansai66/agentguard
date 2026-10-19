# AgentGuard API Guide

All endpoints are served under the `/api` prefix. OpenAPI documentation is available interactively at `/docs` or `/redoc`.

## Endpoints Summary

### System & Health
- `GET /api/health`: Health status and version.
- `GET /api/stats`: Real aggregated metrics computed across all stored runs.
- `GET /api/system/status`: Diagnostics, database health, scenario count, uptime.
- `POST /api/system/reset-demo-data`: Resets historical runs and re-seeds the 11 baseline scenarios.

### Agents
- `GET /api/agents`: Lists registered agents and their version strategies.
- `POST /api/agents`: Registers an agent adapter.
- `GET /api/agents/{agent_id}`: Agent details, supported tools, and version history.
- `PATCH /api/agents/{agent_id}`: Updates agent status or active version.
- `GET /api/agents/{agent_id}/runs`: Historical runs executed on this agent.

### Scenarios
- `GET /api/scenarios`: Lists scenarios with query filters (`failure_type`, `severity`, `search`).
- `POST /api/scenarios`: Creates a scenario with validation.
- `GET /api/scenarios/{id}`: Retrieves scenario definition.
- `PATCH /api/scenarios/{id}`: Updates scenario parameters and increments version.
- `DELETE /api/scenarios/{id}`: Deletes a scenario.
- `POST /api/scenarios/{id}/duplicate`: Clones an existing scenario.
- `POST /api/scenarios/import`: Imports scenario list from JSON.
- `GET /api/scenarios/export`: Exports all scenarios as JSON.

### Test Suites
- `GET /api/suites`: Lists test suites.
- `POST /api/suites`: Creates a test suite.
- `GET /api/suites/{id}`: Suite details and associated scenario IDs.
- `PATCH /api/suites/{id}`: Updates suite metadata and scenario order.

### Runs & Execution
- `POST /api/runs`: Executes a scenario or test suite with an agent version.
- `GET /api/runs`: Lists runs with pagination.
- `GET /api/runs/{id}`: Detailed run results with scenario breakdowns.
- `GET /api/runs/{id}/trace`: Chronological timeline trace events.
- `GET /api/runs/{id}/results`: Scenario results and evaluator findings.
- `POST /api/runs/{id}/cancel`: Safely marks a running execution as cancelled.
- `GET /api/runs/{id}/export`: Exports run results, traces, and findings as JSON.

### Diagnoses & Repairs
- `POST /api/runs/{id}/diagnose`: Runs deterministic diagnosis and drafts repair proposals.
- `GET /api/runs/{id}/diagnoses`: Lists diagnoses for a run.
- `GET /api/patches`: Lists all repair proposals.
- `GET /api/patches/{id}`: Proposal details and unified patch diff.
- `POST /api/patches/{id}/approve`: Approves proposal as a candidate.
- `POST /api/patches/{id}/reject`: Rejects proposal.
- `POST /api/patches/{id}/verify`: Runs candidate against baseline conditions and executes comparison.

### Comparisons
- `POST /api/comparisons`: Computes differential metrics between baseline and candidate runs.
- `GET /api/comparisons/{id}`: Retrieves comparison report and verification verdict.
