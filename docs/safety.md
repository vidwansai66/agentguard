# Security & Safety Architecture

AgentGuard operates as a research, testing, and reliability verification platform. It enforces explicit security controls:

## 1. No Arbitrary Code Execution
- The web server never compiles, evaluates, or runs arbitrary uploaded Python scripts or shell commands.
- Python adapters execute strictly through verified classes registered in the application's trusted registry (`AgentRegistry`).

## 2. HTTP Adapter SSRF Protection & Isolation
- HTTP adapters restrict targets to authorized endpoints.
- Unconditionally blocks access to cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`), multicast (`224.0.0.0/4`), and invalid schemes (`file://`, `ftp://`).
- Loopback and private network targets (`127.0.0.1`, `localhost`) are disabled in production unless explicit development authorization (`allow_local_dev: true`) is enabled.
- TLS certificate verification is enforced by default. HTTP redirects to unauthorized destinations are rejected.

## 3. Secret & Credential Protection
- API credentials are never stored as plaintext in database records.
- HTTP adapters reference secrets via environment variable names (`secret_env_var`).
- `TraceRecorder` applies recursive pattern redaction so bearer tokens, API keys, and authorization headers are sanitized to `[REDACTED_SECRET]` before persistence or transmission to the frontend.

## 4. Controlled Mock Tool Interception
- All agent interactions with simulated tools (e.g., ticketing, search) must pass through `ToolInvoker`.
- Tool calls cannot bypass fault injection or assertion rules.
- Execution steps are strictly bounded by `max_steps` and timeouts to halt runaway retry loops.

## 5. Honest Capability Reporting
- Scenarios declare required capabilities (`state_inspection`, `handle_structured_errors`).
- Agents declare supported capabilities.
- When an agent cannot exercise a scenario meaningfully, AgentGuard reports the status as `unsupported` rather than silently passing.

## 6. Controlled Verification Workflow
- Repair proposals are template-bound diffs.
- Approving a proposal accepts it as a verification candidate, never as an unreviewed production deployment.
- Candidate fixes are tested against full regression suites before being classified as verified.
