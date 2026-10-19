# Security & Safety Architecture

AgentGuard operates as a research, testing, and reliability verification platform. It enforces explicit security controls:

## 1. No Arbitrary Code Execution
- The MVP web server never compiles, evaluates, or runs arbitrary uploaded Python scripts or shell commands.
- All testing runs against strictly defined adapters (`AgentAdapter`) and mock tools (`MockTicketingTool`).

## 2. Mock Tool Isolation
- Tools interact exclusively with in-memory state stores per run context.
- No live connections to real ticketing services, emails, cloud providers, or customer databases.

## 3. Tool Policy & Allowlist Enforcement
- The runner acts as an authorization gatekeeper. Tools invoked by agents are validated against the scenario's `allowed_tools` list.
- Disallowed actions like `admin_override` trigger critical evaluation failures.

## 4. Prompt Injection Defense
- Tool returns are treated as untrusted data, never as system instructions.
- The `strict_policy` strategy demonstrates active prompt filtering and schema sanitization.

## 5. Trace Sanitization & Secret Redaction
- All payloads recorded by `TraceRecorder` pass through regex-based sanitizers.
- Keys like `api_key`, `secret`, `password`, `token`, and `authorization` are replaced with `[REDACTED_SECRET]`.

## 6. Controlled Verification Workflow
- Repair proposals are template-bound diffs.
- Approving a proposal accepts it as a verification candidate, never as an unreviewed production deployment.
- Candidate fixes are tested against full regression suites before being classified as verified.
