import pytest

def test_health_and_system_endpoints(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_sys = client.get("/api/system/status")
    assert res_sys.status_code == 200
    assert res_sys.json()["database_connected"] is True
    assert res_sys.json()["total_scenarios_count"] >= 10

def test_scenarios_listing_and_filtering(client):
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 10

    # Test filtering by failure_type
    res_filtered = client.get("/api/scenarios?failure_type=ambiguous_outcome")
    assert res_filtered.status_code == 200
    for s in res_filtered.json():
        assert s["failure_type"] == "ambiguous_outcome"

def test_scenario_duplication(client):
    res = client.post("/api/scenarios/SCEN-01-NORMAL-CREATE/duplicate")
    assert res.status_code == 201
    dup = res.json()
    assert "(Copy)" in dup["name"]
    assert dup["id"].startswith("SCEN-COPY-")

def test_full_run_execution_and_trace(client):
    # Trigger run on normal scenario
    run_payload = {
        "name": "Test Run Normal",
        "agent_id": "agent-ticket-sample",
        "agent_version": "1.0.0",
        "scenario_id": "SCEN-01-NORMAL-CREATE"
    }
    res_run = client.post("/api/runs", json=run_payload)
    assert res_run.status_code == 201
    run_data = res_run.json()
    assert run_data["status"] == "completed"
    assert run_data["passed_scenarios"] == 1
    assert run_data["failed_scenarios"] == 0

    run_id = run_data["id"]

    # Verify trace retrieval
    res_trace = client.get(f"/api/runs/{run_id}/trace")
    assert res_trace.status_code == 200
    traces = res_trace.json()
    assert len(traces) > 0
    assert any(t["event_type"] == "tool_call" for t in traces)

def test_end_to_end_repair_and_verification_workflow(client):
    # 1. Run baseline agent on Ambiguous Outcome scenario
    run_payload = {
        "name": "Baseline Ambiguous Run",
        "agent_id": "agent-ticket-sample",
        "agent_version": "1.0.0",
        "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
    }
    res_baseline = client.post("/api/runs", json=run_payload)
    assert res_baseline.status_code == 201
    baseline_run = res_baseline.json()
    assert baseline_run["status"] == "completed"
    assert baseline_run["failed_scenarios"] == 1
    assert baseline_run["unsafe_side_effects_count"] == 1

    # 2. Generate Diagnosis
    res_diag = client.post(f"/api/runs/{baseline_run['id']}/diagnose")
    assert res_diag.status_code == 200
    diagnoses = res_diag.json()
    assert len(diagnoses) > 0
    assert "Duplicate" in diagnoses[0]["title"]

    # 3. List Repair Proposals
    res_patches = client.get("/api/patches")
    assert res_patches.status_code == 200
    patches = res_patches.json()
    assert len(patches) > 0
    patch = patches[0]

    # 4. Approve Repair Proposal
    res_approve = client.post(f"/api/patches/{patch['id']}/approve", json={"notes": "Approved for verification"})
    assert res_approve.status_code == 200
    assert res_approve.json()["approval_status"] == "approved"

    # 5. Verify Repair Proposal (Executes candidate run + comparison)
    res_verify = client.post(f"/api/patches/{patch['id']}/verify")
    assert res_verify.status_code == 200
    comparison = res_verify.json()
    assert comparison["verification_verdict"] == "verified_passed"
    assert comparison["candidate_success_rate"] == 1.0
    assert comparison["candidate_unsafe_side_effect_rate"] == 0.0

    # 6. Verify Dashboard Stats are updated from real results
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_runs"] >= 2
