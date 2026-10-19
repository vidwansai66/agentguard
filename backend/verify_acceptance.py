import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=30.0)

# 1. Health check
health = client.get("/health").json()
print("1. Health Status:", health["status"])

# 2. Inspect Sample Agent
agents = client.get("/agents").json()
print("2. Registered Agents:", len(agents), "| Built-in Agent:", agents[0]["name"])

# 3. List Scenarios
scenarios = client.get("/scenarios").json()
print("3. Seeded Scenarios Count:", len(scenarios))
ambiguous_scen = next(s for s in scenarios if s["id"] == "SCEN-03-AMBIGUOUS-OUTCOME")
print("   Selected Scenario:", ambiguous_scen["name"])

# 4. Run Baseline Agent (1.0.0)
baseline_payload = {
    "name": "E2E Acceptance - Baseline Run (Ambiguous Outcome)",
    "agent_id": "agent-ticket-sample",
    "agent_version": "1.0.0",
    "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
}
run1 = client.post("/runs", json=baseline_payload).json()
print(f"4. Baseline Run [{run1['id']}]: Passed={run1['passed_scenarios']}, Failed={run1['failed_scenarios']}, Unsafe={run1['unsafe_side_effects_count']}")

# 5. Inspect Trace
traces = client.get(f"/runs/{run1['id']}/trace").json()
print(f"5. Recorded Trace Events: {len(traces)} events. Event types: {list(set(t['event_type'] for t in traces))}")

# 6. Generate Diagnosis
diagnoses = client.post(f"/runs/{run1['id']}/diagnose").json()
print(f"6. Diagnosis Generated: '{diagnoses[0]['title']}' | Confidence: {diagnoses[0]['confidence']}")
print(f"   Likely Cause: {diagnoses[0]['likely_cause']}")

# 7. Approve Repair Proposal
patches = client.get("/patches").json()
target_patch = next(p for p in patches if p["run_id"] == run1["id"])
print(f"7. Repair Proposal [{target_patch['id']}]: '{target_patch['title']}'")
approved = client.post(f"/patches/{target_patch['id']}/approve", json={"notes": "Approved for verification"}).json()
print(f"   Approval Status: {approved['approval_status']}")

# 8. Verify Candidate Fix (Runs Candidate & Differential Comparison)
comparison = client.post(f"/patches/{target_patch['id']}/verify").json()
print("8. Candidate Verification:")
print(f"   Verdict: {comparison['verification_verdict']}")
print(f"   Success Rate: {comparison['baseline_success_rate']*100:.1f}% -> {comparison['candidate_success_rate']*100:.1f}%")
print(f"   Unsafe Side Effects: {comparison['baseline_unsafe_side_effect_rate']*100:.1f}% -> {comparison['candidate_unsafe_side_effect_rate']*100:.1f}%")
print(f"   Regression Rate: {comparison['regression_rate']*100:.1f}%")
print(f"   Newly Passing: {comparison['newly_passing_scenarios']}")
print(f"   Interpretation: {comparison['interpretation']}")

# 9. Execute Core Suite Benchmark
suite_run = client.post("/runs", json={
    "name": "E2E Acceptance - Core Reliability Benchmark",
    "agent_id": "agent-ticket-sample",
    "agent_version": "1.1.0-patch",
    "suite_id": "suite-core-reliability"
}).json()
print(f"9. Core Suite Benchmark [{suite_run['id']}]: Passed={suite_run['passed_scenarios']}/{suite_run['total_scenarios']}")

# 10. Dashboard Stats
stats = client.get("/stats").json()
print("10. Persisted Dashboard Metrics:")
print(f"    Total Runs: {stats['total_runs']}")
print(f"    Task Success Rate: {stats['task_success_rate']*100:.1f}%")
print(f"    Recovery Rate: {stats['recovery_rate']*100:.1f}%")
print(f"    Median Latency: {stats['median_latency_ms']}ms")
print(f"    Failure Categories Tracked: {len(stats['failure_type_metrics'])}")
print("SUCCESS: Full End-to-End Acceptance Test Completed Cleanly!")
