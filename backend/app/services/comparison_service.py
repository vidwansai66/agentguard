import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.run import TestRun, ScenarioResult
from app.models.comparison import Comparison
from app.verification.verifier import verifier
from app.core.errors import NotFoundError, ValidationError

class ComparisonService:
    def compare_runs(self, db: Session, baseline_run_id: str, candidate_run_id: str) -> Comparison:
        baseline_run = db.query(TestRun).filter(TestRun.id == baseline_run_id).first()
        if not baseline_run:
            raise NotFoundError("Baseline TestRun", baseline_run_id)

        candidate_run = db.query(TestRun).filter(TestRun.id == candidate_run_id).first()
        if not candidate_run:
            raise NotFoundError("Candidate TestRun", candidate_run_id)

        b_results = db.query(ScenarioResult).filter(ScenarioResult.run_id == baseline_run_id).all()
        c_results = db.query(ScenarioResult).filter(ScenarioResult.run_id == candidate_run_id).all()

        if not b_results or not c_results:
            raise ValidationError("Both baseline and candidate runs must contain completed scenario results.")

        b_dicts = [
            {
                "scenario_id": r.scenario_id,
                "scenario_name": r.scenario_name,
                "failure_type": r.failure_type,
                "passed": r.passed,
                "disrupted": r.disrupted,
                "recovered": r.recovered,
                "has_unsafe_side_effect": r.has_unsafe_side_effect,
                "duration_ms": r.duration_ms
            }
            for r in b_results
        ]
        c_dicts = [
            {
                "scenario_id": r.scenario_id,
                "scenario_name": r.scenario_name,
                "failure_type": r.failure_type,
                "passed": r.passed,
                "disrupted": r.disrupted,
                "recovered": r.recovered,
                "has_unsafe_side_effect": r.has_unsafe_side_effect,
                "duration_ms": r.duration_ms
            }
            for r in c_results
        ]

        comp_data = verifier.compare_runs(b_dicts, c_dicts)

        comp_id = f"CMP-{uuid.uuid4().hex[:10]}"
        comparison = Comparison(
            id=comp_id,
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            baseline_agent_version=baseline_run.agent_version,
            candidate_agent_version=candidate_run.agent_version,
            baseline_success_rate=comp_data["baseline_success_rate"],
            candidate_success_rate=comp_data["candidate_success_rate"],
            baseline_recovery_rate=comp_data["baseline_recovery_rate"],
            candidate_recovery_rate=comp_data["candidate_recovery_rate"],
            baseline_unsafe_side_effect_rate=comp_data["baseline_unsafe_side_effect_rate"],
            candidate_unsafe_side_effect_rate=comp_data["candidate_unsafe_side_effect_rate"],
            baseline_median_latency_ms=comp_data["baseline_median_latency_ms"],
            candidate_median_latency_ms=comp_data["candidate_median_latency_ms"],
            baseline_p95_latency_ms=comp_data["baseline_p95_latency_ms"],
            candidate_p95_latency_ms=comp_data["candidate_p95_latency_ms"],
            regression_rate=comp_data["regression_rate"],
            newly_passing_scenarios_json=json.dumps(comp_data["newly_passing_scenarios"]),
            newly_failing_scenarios_json=json.dumps(comp_data["newly_failing_scenarios"]),
            safety_regressions_json=json.dumps(comp_data["safety_regressions"]),
            per_scenario_comparison_json=json.dumps(comp_data["per_scenario_comparison"]),
            interpretation=comp_data["interpretation"],
            verification_verdict=comp_data["verification_verdict"],
            created_at=datetime.utcnow()
        )
        db.add(comparison)
        db.commit()
        db.refresh(comparison)
        return comparison

comparison_service = ComparisonService()
