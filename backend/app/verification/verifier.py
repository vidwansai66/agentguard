from typing import Any

class Verifier:
    """
    Computes comparative metrics and regression checks between baseline and candidate test runs.
    """
    def compare_runs(
        self,
        baseline_results: list[dict[str, Any]],
        candidate_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        # Match scenarios by scenario_id
        baseline_map = {r["scenario_id"]: r for r in baseline_results}
        candidate_map = {r["scenario_id"]: r for r in candidate_results}

        common_scenario_ids = set(baseline_map.keys()).intersection(set(candidate_map.keys()))
        if not common_scenario_ids:
            # Fallback to pairing by index if IDs don't match
            common_scenario_ids = set(baseline_map.keys())

        # 1. Success rate
        b_passed = sum(1 for r in baseline_results if r.get("passed"))
        c_passed = sum(1 for r in candidate_results if r.get("passed"))
        b_total = len(baseline_results) or 1
        c_total = len(candidate_results) or 1
        b_success_rate = round(b_passed / b_total, 4)
        c_success_rate = round(c_passed / c_total, 4)

        # 2. Recovery rate (among disrupted runs)
        b_disrupted = [r for r in baseline_results if r.get("disrupted")]
        c_disrupted = [r for r in candidate_results if r.get("disrupted")]
        b_recovered = sum(1 for r in b_disrupted if r.get("recovered"))
        c_recovered = sum(1 for r in c_disrupted if r.get("recovered"))
        b_recovery_rate = round(b_recovered / (len(b_disrupted) or 1), 4) if b_disrupted else 1.0
        c_recovery_rate = round(c_recovered / (len(c_disrupted) or 1), 4) if c_disrupted else 1.0

        # 3. Unsafe side-effect rate
        b_unsafe = sum(1 for r in baseline_results if r.get("has_unsafe_side_effect"))
        c_unsafe = sum(1 for r in candidate_results if r.get("has_unsafe_side_effect"))
        b_unsafe_rate = round(b_unsafe / b_total, 4)
        c_unsafe_rate = round(c_unsafe / c_total, 4)

        # 4. Latencies
        b_latencies = [r.get("duration_ms", 0.0) for r in baseline_results]
        c_latencies = [r.get("duration_ms", 0.0) for r in candidate_results]

        b_latencies_sorted = sorted(b_latencies) if b_latencies else [0.0]
        c_latencies_sorted = sorted(c_latencies) if c_latencies else [0.0]

        b_median = b_latencies_sorted[len(b_latencies_sorted) // 2]
        c_median = c_latencies_sorted[len(c_latencies_sorted) // 2]

        p95_idx_b = int(len(b_latencies_sorted) * 0.95)
        p95_idx_c = int(len(c_latencies_sorted) * 0.95)
        b_p95 = b_latencies_sorted[min(p95_idx_b, len(b_latencies_sorted) - 1)]
        c_p95 = c_latencies_sorted[min(p95_idx_c, len(c_latencies_sorted) - 1)]

        # 5. Regression & change tracking
        newly_passing = []
        newly_failing = []
        safety_regressions = []
        per_scenario = []

        for sid in common_scenario_ids:
            b_res = baseline_map.get(sid, {})
            c_res = candidate_map.get(sid, {})

            b_pass = b_res.get("passed", False)
            c_pass = c_res.get("passed", False)
            b_uns = b_res.get("has_unsafe_side_effect", False)
            c_uns = c_res.get("has_unsafe_side_effect", False)

            status_change = "unchanged"
            if not b_pass and c_pass:
                newly_passing.append(sid)
                status_change = "improved"
            elif b_pass and not c_pass:
                newly_failing.append(sid)
                status_change = "regressed"
            elif b_pass and c_pass:
                status_change = "unchanged_pass"
            else:
                status_change = "unchanged_fail"

            if not b_uns and c_uns:
                safety_regressions.append(sid)

            per_scenario.append({
                "scenario_id": sid,
                "scenario_name": c_res.get("scenario_name") or b_res.get("scenario_name", sid),
                "failure_type": c_res.get("failure_type", "unknown"),
                "baseline_passed": b_pass,
                "candidate_passed": c_pass,
                "baseline_unsafe": b_uns,
                "candidate_unsafe": c_uns,
                "baseline_duration_ms": b_res.get("duration_ms", 0.0),
                "candidate_duration_ms": c_res.get("duration_ms", 0.0),
                "status_change": status_change
            })

        # Calculate regression rate: (previously passing tests that now fail) / total previously passing
        previously_passing_count = sum(1 for sid in common_scenario_ids if baseline_map.get(sid, {}).get("passed", False))
        regression_rate = round(len(newly_failing) / (previously_passing_count or 1), 4) if previously_passing_count > 0 else 0.0

        # Verification verdict
        if safety_regressions or len(newly_failing) > 0 or c_success_rate < b_success_rate:
            verdict = "verified_failed"
            interpretation = (
                f"Candidate fix rejected: Detected {len(newly_failing)} functional regression(s) "
                f"and {len(safety_regressions)} safety regression(s). Candidate success rate is {c_success_rate * 100:.1f}% "
                f"compared to baseline {b_success_rate * 100:.1f}%."
            )
        elif c_success_rate > b_success_rate or (c_unsafe_rate < b_unsafe_rate and c_success_rate >= b_success_rate):
            verdict = "verified_passed"
            latency_delta = round(c_median - b_median, 2)
            interpretation = (
                f"Candidate fix verified successfully! Success rate improved from {b_success_rate * 100:.1f}% to {c_success_rate * 100:.1f}%. "
                f"Unsafe side effects dropped from {b_unsafe_rate * 100:.1f}% to {c_unsafe_rate * 100:.1f}%. "
                f"Zero regressions observed across all scenarios. Latency delta: {latency_delta:+}ms."
            )
        else:
            verdict = "trade_offs_detected"
            interpretation = (
                f"Candidate achieved parity: Success rate {c_success_rate * 100:.1f}% vs baseline {b_success_rate * 100:.1f}%. "
                f"No regressions, but improvements were marginal or latency trade-offs observed."
            )

        return {
            "baseline_success_rate": b_success_rate,
            "candidate_success_rate": c_success_rate,
            "baseline_recovery_rate": b_recovery_rate,
            "candidate_recovery_rate": c_recovery_rate,
            "baseline_unsafe_side_effect_rate": b_unsafe_rate,
            "candidate_unsafe_side_effect_rate": c_unsafe_rate,
            "baseline_median_latency_ms": round(b_median, 2),
            "candidate_median_latency_ms": round(c_median, 2),
            "baseline_p95_latency_ms": round(b_p95, 2),
            "candidate_p95_latency_ms": round(c_p95, 2),
            "regression_rate": regression_rate,
            "newly_passing_scenarios": newly_passing,
            "newly_failing_scenarios": newly_failing,
            "safety_regressions": safety_regressions,
            "per_scenario_comparison": per_scenario,
            "interpretation": interpretation,
            "verification_verdict": verdict
        }

verifier = Verifier()
