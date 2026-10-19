import pytest
from app.diagnosis.engine import DiagnosisEngine
from app.repairs.proposer import repair_proposer
from app.verification.verifier import verifier

def test_diagnosis_generation_for_duplicate_action():
    engine = DiagnosisEngine()

    scenario_result = {
        "failure_type": "ambiguous_outcome",
        "has_unsafe_side_effect": True,
        "retry_count": 1,
        "error_message": None
    }
    findings = [
        {
            "rule_id": "ASSERT_NO_DUPLICATE_ACTIONS",
            "rule_name": "No Duplicate Unsafe Side Effects",
            "status": "failed",
            "passed": False,
            "severity": "critical",
            "message": "Duplicate side effect detected: 2 tickets created",
            "trace_event_ids": ["EVT-1", "EVT-2"],
            "evidence": {"tickets_created_count": 2, "ticket_ids": ["TICK-1", "TICK-2"]}
        }
    ]
    traces = [{"id": "EVT-1"}, {"id": "EVT-2"}]

    diagnoses = engine.diagnose_scenario_result(scenario_result, findings, traces)

    assert len(diagnoses) > 0
    d = diagnoses[0]
    assert "Duplicate" in d.title
    assert "Idempotency" in d.likely_cause or "Duplicate" in d.likely_cause
    assert d.recommended_patch_template_id == "TEMPLATE_IDEMPOTENCY_CHECK"
    assert "tickets_created_count" in d.supporting_evidence

def test_repair_proposal_creation():
    proposal = repair_proposer.create_proposal_for_diagnosis(
        diagnosis_id="DIAG-123",
        run_id="RUN-456",
        target_agent_id="agent-ticket-sample",
        base_version="1.0.0",
        template_id="TEMPLATE_IDEMPOTENCY_CHECK"
    )

    assert proposal["template_id"] == "TEMPLATE_IDEMPOTENCY_CHECK"
    assert "State-Aware" in proposal["title"]
    assert "idempotency_key" in proposal["patch_diff"]
    assert proposal["approval_status"] == "pending"
    assert proposal["verification_status"] == "unverified"

def test_verifier_comparison_and_regression_detection():
    baseline_results = [
        {"scenario_id": "s1", "scenario_name": "S1", "failure_type": "ambiguous_outcome", "passed": False, "disrupted": True, "recovered": False, "has_unsafe_side_effect": True, "duration_ms": 100},
        {"scenario_id": "s2", "scenario_name": "S2", "failure_type": "normal_execution", "passed": True, "disrupted": False, "recovered": False, "has_unsafe_side_effect": False, "duration_ms": 50}
    ]
    # Candidate fixes s1 and keeps s2 passing -> verified_passed
    candidate_results_good = [
        {"scenario_id": "s1", "scenario_name": "S1", "failure_type": "ambiguous_outcome", "passed": True, "disrupted": True, "recovered": True, "has_unsafe_side_effect": False, "duration_ms": 120},
        {"scenario_id": "s2", "scenario_name": "S2", "failure_type": "normal_execution", "passed": True, "disrupted": False, "recovered": False, "has_unsafe_side_effect": False, "duration_ms": 52}
    ]

    comp_good = verifier.compare_runs(baseline_results, candidate_results_good)
    assert comp_good["verification_verdict"] == "verified_passed"
    assert comp_good["candidate_success_rate"] > comp_good["baseline_success_rate"]
    assert comp_good["candidate_unsafe_side_effect_rate"] == 0.0
    assert "s1" in comp_good["newly_passing_scenarios"]
    assert len(comp_good["newly_failing_scenarios"]) == 0

    # Candidate introduces regression on s2 -> verified_failed
    candidate_results_bad = [
        {"scenario_id": "s1", "scenario_name": "S1", "failure_type": "ambiguous_outcome", "passed": True, "disrupted": True, "recovered": True, "has_unsafe_side_effect": False, "duration_ms": 120},
        {"scenario_id": "s2", "scenario_name": "S2", "failure_type": "normal_execution", "passed": False, "disrupted": False, "recovered": False, "has_unsafe_side_effect": False, "duration_ms": 52}
    ]
    comp_bad = verifier.compare_runs(baseline_results, candidate_results_bad)
    assert comp_bad["verification_verdict"] == "verified_failed"
    assert "s2" in comp_bad["newly_failing_scenarios"]
    assert comp_bad["regression_rate"] > 0
