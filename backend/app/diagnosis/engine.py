from typing import Any

class DiagnosisResult:
    def __init__(
        self,
        title: str,
        likely_cause: str,
        confidence: str,
        explanation: str,
        supporting_evidence: dict[str, Any],
        relevant_trace_event_ids: list[str],
        recommended_strategy: str,
        recommended_patch_template_id: str | None = None,
        limitations: str | None = None
    ):
        self.title = title
        self.likely_cause = likely_cause
        self.confidence = confidence
        self.explanation = explanation
        self.supporting_evidence = supporting_evidence
        self.relevant_trace_event_ids = relevant_trace_event_ids
        self.recommended_strategy = recommended_strategy
        self.recommended_patch_template_id = recommended_patch_template_id
        self.limitations = limitations

class DiagnosisEngine:
    """
    Deterministic rule-based diagnosis engine.
    Analyzes failed evaluation findings, execution traces, and fault metadata.
    """
    def diagnose_scenario_result(
        self,
        scenario_result: dict[str, Any],
        findings: list[dict[str, Any]],
        trace_events: list[dict[str, Any]]
    ) -> list[DiagnosisResult]:
        diagnoses: list[DiagnosisResult] = []

        failed_rules = {f["rule_id"]: f for f in findings if f.get("status") == "failed" or not f.get("passed", True)}
        failure_type = scenario_result.get("failure_type", "")

        # 1. Duplicate side effect diagnosis
        if "ASSERT_NO_DUPLICATE_ACTIONS" in failed_rules or scenario_result.get("has_unsafe_side_effect"):
            duplicate_finding = failed_rules.get("ASSERT_NO_DUPLICATE_ACTIONS", {})
            evidence = duplicate_finding.get("evidence", {})
            trace_ids = duplicate_finding.get("trace_event_ids", [])
            diagnoses.append(DiagnosisResult(
                title="Unsafe Duplicate Retry After Ambiguous Outcome",
                likely_cause="State-Blind Retry Loop Missing Idempotency Key or State Query",
                confidence="High (Supported by DB state evidence of >1 ticket)",
                explanation=(
                    "The agent received a network timeout or dropped response while creating a ticket. "
                    "Because it lacked an idempotency key and did not query existing tickets before retrying, "
                    "a second duplicate ticket was created in the database. In an enterprise system, this leads to billing duplicates or fragmented workflows."
                ),
                supporting_evidence={
                    "tickets_created_count": evidence.get("tickets_created_count", 2),
                    "ticket_ids": evidence.get("ticket_ids", []),
                    "failure_type": failure_type
                },
                relevant_trace_event_ids=trace_ids,
                recommended_strategy="safe_idempotent",
                recommended_patch_template_id="TEMPLATE_IDEMPOTENCY_CHECK",
                limitations="Relies on mock tool query capability; if ticketing API does not support search or idempotency headers, deduplication requires an external transaction journal."
            ))

        # 2. Tool policy / prompt injection diagnosis
        if "ASSERT_NO_PROMPT_INJECTION_EXPLOIT" in failed_rules or "ASSERT_POLICY_COMPLIANCE" in failed_rules:
            policy_finding = failed_rules.get("ASSERT_NO_PROMPT_INJECTION_EXPLOIT") or failed_rules.get("ASSERT_POLICY_COMPLIANCE")
            trace_ids = policy_finding.get("trace_event_ids", []) if policy_finding else []
            diagnoses.append(DiagnosisResult(
                title="Untrusted Tool Output Instruction Hijack",
                likely_cause="Agent Context Lacks Policy Guardrail Against Untrusted Tool Content",
                confidence="High (Disallowed tool action executed directly from injected string)",
                explanation=(
                    "External tool responses were treated as authoritative execution instructions. "
                    "The agent parsed an injected payload ('admin_override') and invoked a disallowed tool action without checking policy boundaries."
                ),
                supporting_evidence={
                    "finding_message": policy_finding.get("message") if policy_finding else "",
                    "failure_type": failure_type
                },
                relevant_trace_event_ids=trace_ids,
                recommended_strategy="strict_policy",
                recommended_patch_template_id="TEMPLATE_TOOL_POLICY",
                limitations="Rule-based prompt filtering may not catch highly obfuscated adversarial LLM jailbreaks in complex multi-modal environments."
            ))

        # 3. Malformed tool schema diagnosis
        if "ASSERT_SCHEMA_VALIDITY" in failed_rules or failure_type == "malformed_output":
            schema_finding = failed_rules.get("ASSERT_SCHEMA_VALIDITY", {})
            trace_ids = schema_finding.get("trace_event_ids", [])
            diagnoses.append(DiagnosisResult(
                title="Malformed Tool Response Crash",
                likely_cause="Absence of Pydantic / Typed Schema Validation on External Tool Returns",
                confidence="High (Tool payload lacked required 'ticket_id' and 'status' keys)",
                explanation=(
                    "The mock tool returned malformed or corrupted data. The agent assumed a well-formed JSON object and failed or crashed without a graceful fallback."
                ),
                supporting_evidence={
                    "failure_type": failure_type,
                    "error": scenario_result.get("error_message")
                },
                relevant_trace_event_ids=trace_ids,
                recommended_strategy="strict_policy",
                recommended_patch_template_id="TEMPLATE_STRICT_SCHEMA",
                limitations="Schema validation detects invalid responses but cannot invent missing data if the upstream tool is fundamentally broken."
            ))

        # 4. Transient timeout / retry bounds diagnosis
        if "ASSERT_TASK_OUTCOME" in failed_rules and failure_type == "transient_timeout" and not diagnoses:
            diagnoses.append(DiagnosisResult(
                title="Transient Tool Timeout Exhaustion",
                likely_cause="Insufficient Retries or Missing Backoff for Transient Failures",
                confidence="Medium (Hypothesis based on timeout fault injection)",
                explanation=(
                    "A transient network delay occurred during ticket creation. The agent's retry policy did not accommodate the recovery window."
                ),
                supporting_evidence={
                    "retries_used": scenario_result.get("retry_count"),
                    "failure_type": failure_type
                },
                relevant_trace_event_ids=[e["id"] for e in trace_events if e.get("event_type") == "fault_injected"],
                recommended_strategy="bounded_backoff",
                recommended_patch_template_id="TEMPLATE_BOUNDED_BACKOFF",
                limitations="Increasing retries increases latency and potential backend load during outages."
            ))

        return diagnoses
