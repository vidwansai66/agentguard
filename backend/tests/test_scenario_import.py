import pytest

def test_import_single_scenario_object(client):
    single_scenario = {
        "id": "SCEN-CUSTOM-SINGLE-01",
        "name": "Custom Single Imported Scenario",
        "description": "Testing import of a standalone scenario object",
        "category": "ticketing",
        "failure_type": "transient_timeout",
        "severity": "high",
        "task_input": {"action": "create_ticket", "title": "Single Import Ticket"},
        "expected_outcome": {"status": "success"},
        "fault_parameters": {"fault_type": "transient_timeout", "delay_ms": 50},
        "allowed_tools": ["ticket_create", "ticket_query"],
        "policy_constraints": {"max_cost": 1.0},
        "execution_limits": {"max_steps": 15},
        "expected_assertions": ["ASSERT_TASK_OUTCOME"]
    }

    res = client.post("/api/scenarios/import", json=single_scenario)
    assert res.status_code == 200
    data = res.json()
    assert data["imported_count"] == 1
    assert "SCEN-CUSTOM-SINGLE-01" in data["scenario_ids"]

    # Verify scenario exists and is fetchable
    get_res = client.get("/api/scenarios/SCEN-CUSTOM-SINGLE-01")
    assert get_res.status_code == 200
    scen = get_res.json()
    assert scen["name"] == "Custom Single Imported Scenario"
    assert scen["failure_type"] == "transient_timeout"
    assert scen["fault_parameters"]["delay_ms"] == 50

def test_import_scenario_array(client):
    scenarios_array = [
        {
            "id": "SCEN-ARRAY-01",
            "name": "Array Scenario 1",
            "failure_type": "ambiguous_outcome",
            "severity": "critical",
            "task_input": {"title": "Arr 1"}
        },
        {
            "id": "SCEN-ARRAY-02",
            "name": "Array Scenario 2",
            "failure_type": "prompt_injection",
            "severity": "medium",
            "task_input": {"title": "Arr 2"}
        }
    ]

    res = client.post("/api/scenarios/import", json=scenarios_array)
    assert res.status_code == 200
    data = res.json()
    assert data["imported_count"] == 2
    assert "SCEN-ARRAY-01" in data["scenario_ids"]
    assert "SCEN-ARRAY-02" in data["scenario_ids"]

def test_import_export_bundle_wrapper(client):
    bundle = {
        "version": "1.0",
        "exported_at": "2026-10-19T10:00:00Z",
        "scenarios": [
            {
                "id": "SCEN-BUNDLE-01",
                "name": "Bundle Scenario 1",
                "failure_type": "malformed_output",
                "severity": "high"
            }
        ]
    }

    res = client.post("/api/scenarios/import", json=bundle)
    assert res.status_code == 200
    data = res.json()
    assert data["imported_count"] == 1
    assert "SCEN-BUNDLE-01" in data["scenario_ids"]

def test_export_import_roundtrip_preserves_configuration(client):
    # 1. Export current scenarios
    export_res = client.get("/api/scenarios/export")
    assert export_res.status_code == 200
    export_bundle = export_res.json()
    assert "scenarios" in export_bundle
    initial_count = len(export_bundle["scenarios"])
    assert initial_count >= 10

    # 2. Modify one scenario name in export bundle to test roundtrip update
    first_scen = export_bundle["scenarios"][0]
    original_id = first_scen["id"]
    first_scen["description"] = "Updated description during roundtrip test"

    # 3. Re-import the exact exported bundle
    import_res = client.post("/api/scenarios/import", json=export_bundle)
    assert import_res.status_code == 200
    import_data = import_res.json()
    assert import_data["imported_count"] == initial_count

    # 4. Verify preserved configuration
    verify_res = client.get(f"/api/scenarios/{original_id}")
    assert verify_res.status_code == 200
    updated_scen = verify_res.json()
    assert updated_scen["description"] == "Updated description during roundtrip test"
    assert updated_scen["failure_type"] == first_scen["failure_type"]
    assert updated_scen["task_input"] == first_scen["task_input"]
    assert updated_scen["fault_parameters"] == first_scen["fault_parameters"]

def test_imported_scenario_executes_in_runner(client):
    imported_scenario = {
        "id": "SCEN-RUNNABLE-IMPORT",
        "name": "Runnable Imported Scenario",
        "failure_type": "normal_execution",
        "severity": "low",
        "task_input": {"action": "create_ticket", "title": "Run Test Ticket", "priority": "low"},
        "expected_outcome": {"status": "success"},
        "allowed_tools": ["ticket_create", "ticket_query", "ticket_get"],
        "execution_limits": {"max_steps": 10}
    }

    import_res = client.post("/api/scenarios/import", json=imported_scenario)
    assert import_res.status_code == 200

    # Execute test run on imported scenario
    run_payload = {
        "name": "Execution of Imported Scenario",
        "agent_id": "agent-ticket-sample",
        "agent_version": "1.0.0",
        "scenario_id": "SCEN-RUNNABLE-IMPORT"
    }
    run_res = client.post("/api/runs", json=run_payload)
    assert run_res.status_code == 201
    run_data = run_res.json()
    assert run_data["status"] == "completed"
    assert run_data["passed_scenarios"] == 1
    assert run_data["failed_scenarios"] == 0

def test_import_rejects_empty_payload_and_empty_list(client):
    # Empty dictionary
    res_empty_dict = client.post("/api/scenarios/import", json={})
    assert res_empty_dict.status_code in [400, 422]

    # Empty list
    res_empty_list = client.post("/api/scenarios/import", json=[])
    assert res_empty_list.status_code in [400, 422]

    # Empty scenarios list inside wrapper
    res_empty_wrapper = client.post("/api/scenarios/import", json={"scenarios": []})
    assert res_empty_wrapper.status_code in [400, 422]

def test_import_rejects_invalid_schema_fields(client):
    # Invalid failure_type
    invalid_failure_type = {
        "name": "Bad Scenario",
        "failure_type": "non_existent_failure_type",
        "severity": "medium"
    }
    res_bad_type = client.post("/api/scenarios/import", json=invalid_failure_type)
    assert res_bad_type.status_code in [400, 422]
    assert "Invalid failure_type" in res_bad_type.text or "validation" in res_bad_type.text.lower()

    # Invalid severity
    invalid_severity = {
        "name": "Bad Severity Scenario",
        "failure_type": "transient_timeout",
        "severity": "extreme_catastrophe"
    }
    res_bad_sev = client.post("/api/scenarios/import", json=invalid_severity)
    assert res_bad_sev.status_code in [400, 422]
    assert "Invalid severity" in res_bad_sev.text or "validation" in res_bad_sev.text.lower()

    # Missing name
    missing_name = {
        "name": "",
        "failure_type": "transient_timeout",
        "severity": "medium"
    }
    res_no_name = client.post("/api/scenarios/import", json=missing_name)
    assert res_no_name.status_code in [400, 422]

def test_import_transactional_rollback_on_partial_failure(client):
    # Batch with 1 valid scenario and 1 invalid scenario
    batch = [
        {
            "id": "SCEN-ROLLBACK-VALID-01",
            "name": "Valid Scenario in Broken Batch",
            "failure_type": "transient_timeout",
            "severity": "medium"
        },
        {
            "id": "SCEN-ROLLBACK-INVALID-02",
            "name": "Invalid Scenario",
            "failure_type": "invalid_bad_fault",
            "severity": "medium"
        }
    ]

    res = client.post("/api/scenarios/import", json=batch)
    assert res.status_code in [400, 422]

    # Transaction rollback check: SCEN-ROLLBACK-VALID-01 must NOT exist in the database!
    check_res = client.get("/api/scenarios/SCEN-ROLLBACK-VALID-01")
    assert check_res.status_code == 404

def test_import_updates_existing_scenario_and_creates_version_snapshot(client):
    scen_id = "SCEN-VERSION-TEST"
    v1 = {
        "id": scen_id,
        "name": "Version Test Initial",
        "failure_type": "transient_timeout",
        "severity": "low"
    }
    res1 = client.post("/api/scenarios/import", json=v1)
    assert res1.status_code == 200

    scen_v1 = client.get(f"/api/scenarios/{scen_id}").json()
    assert scen_v1["version"] == 1
    assert scen_v1["name"] == "Version Test Initial"

    # Re-import updated version
    v2 = {
        "id": scen_id,
        "name": "Version Test Updated",
        "failure_type": "ambiguous_outcome",
        "severity": "high"
    }
    res2 = client.post("/api/scenarios/import", json=v2)
    assert res2.status_code == 200

    scen_v2 = client.get(f"/api/scenarios/{scen_id}").json()
    assert scen_v2["version"] == 2
    assert scen_v2["name"] == "Version Test Updated"
    assert scen_v2["failure_type"] == "ambiguous_outcome"
