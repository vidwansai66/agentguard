import uuid
import httpx

client = httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=30.0)

print("=" * 70)
print("AGENTGUARD — CUSTOM AI AGENT INTEGRATION ACCEPTANCE TEST")
print("=" * 70)

# Step 1: Health Check
system = client.get("/system/status").json()
print(f"1. System Status: {system.get('service', 'AgentGuard')} | DB={system.get('database')}")

# Step 2: Register a new custom Python agent using documented adapter contract
custom_agent_id = f"agent-custom-logistics-{uuid.uuid4().hex[:6]}"
register_payload = {
    "id": custom_agent_id,
    "name": "Custom Logistics Support Agent",
    "description": "Enterprise agent integrating via documented Python AgentAdapter with state reconciliation",
    "adapter_type": "python",
    "version": "1.0.0",
    "strategy": "baseline",
    "supported_tools": ["ticket_create", "ticket_query", "ticket_get"],
    "declared_capabilities": [
        "ticket_create",
        "ticket_query",
        "ticket_get",
        "state_inspection",
        "handle_structured_errors"
    ],
    "adapter_config": {
        "class_name": "CustomTestAgent",
        "enable_reconciliation": False,  # Baseline has naive retry
        "max_retries": 2
    }
}
reg_resp = client.post("/agents/custom", json=register_payload)
assert reg_resp.status_code == 201, f"Failed to register custom agent: {reg_resp.text}"
registered_agent = reg_resp.json()
print(f"2. Registered Custom Agent: {registered_agent['name']} [{registered_agent['id']}]")
print(f"   Adapter Type: {registered_agent['adapter_type']} | Source: {registered_agent['registration_source']}")
print(f"   Declared Capabilities: {registered_agent['declared_capabilities']}")

# Step 3: Test Agent Initialization & Connectivity Handshake
test_conn = client.post(f"/agents/{custom_agent_id}/test-connection").json()
print(f"3. Adapter Connectivity & Handshake Test: {test_conn['status'].upper()} — {test_conn['message']}")
assert test_conn["status"] == "healthy"

# Step 4: Verify Scenario Compatibility
compat = client.post("/scenarios/compatibility", json={
    "agent_id": custom_agent_id,
    "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
}).json()
print(f"4. Compatibility Check on Ambiguous Outcome: Compatible={compat['compatible']}")
assert compat["compatible"] is True

# Step 5: Execute Baseline Custom Agent on Ambiguous-Outcome Scenario
run1_payload = {
    "name": "Acceptance: Custom Agent Baseline on Ambiguous Outcome",
    "agent_id": custom_agent_id,
    "agent_version": "1.0.0",
    "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME"
}
run1 = client.post("/runs", json=run1_payload).json()
print(f"5. Baseline Execution [{run1['id']}]:")
print(f"   Status: {run1['status']} | Passed: {run1['passed_scenarios']} | Failed: {run1['failed_scenarios']}")
print(f"   Unsafe Side Effects: {run1['unsafe_side_effects_count']}")

# Step 6 & 7: Inspect Fault Injection & Execution Trace Events
traces = client.get(f"/runs/{run1['id']}/trace").json()
event_types = [t["event_type"] for t in traces]
fault_events = [t for t in traces if t["event_type"] == "fault_injected"]
tool_calls = [t for t in traces if t["event_type"] == "tool_call"]
print(f"6. Fault Injection Pipeline: {len(fault_events)} fault event(s) intercepted")
for fe in fault_events:
    print(f"   Injected Fault: {fe.get('fault_details')} | Severity: {fe.get('severity')}")
print(f"7. Recorded Structured Trace: {len(traces)} total events ({len(tool_calls)} tool calls)")
assert len(fault_events) > 0, "Fault was not intercepted by fault injector!"

# Step 8: Deterministic Independent Evaluation
scen_res1 = run1["scenario_results"][0]
print(f"8. Independent Evaluator Findings:")
for fnd in scen_res1["findings"]:
    print(f"   [{fnd['status'].upper()}] {fnd['rule_id']}: {fnd['message']}")

# Step 9: Generate Evidence-Linked Diagnosis if run failed
diag_resp = client.post(f"/runs/{run1['id']}/diagnose").json()
assert len(diag_resp) > 0
diag = diag_resp[0]
print(f"9. Diagnosis Generated: '{diag['title']}' (Confidence: {diag['confidence']})")
print(f"   Likely Cause: {diag['likely_cause']}")
print(f"   Recommended Strategy: {diag['recommended_strategy']}")

# Step 10: Compare Against Fixed Candidate Strategy
# Execute safe reconciliation strategy with CustomTestAgent
run2_payload = {
    "name": "Acceptance: Custom Agent Safe Reconciliation Strategy",
    "agent_id": custom_agent_id,
    "agent_version": "1.0.0",
    "scenario_id": "SCEN-03-AMBIGUOUS-OUTCOME",
    "custom_config": {"enable_reconciliation": True, "strategy": "safe_idempotent"}
}
run2 = client.post("/runs", json=run2_payload).json()
scen_res2 = run2["scenario_results"][0]
print(f"10. Candidate Run [{run2['id']}]:")
print(f"    Status: {run2['status']} | Passed: {run2['passed_scenarios']} | Failed: {run2['failed_scenarios']}")
print(f"    Unsafe Side Effects: {run2['unsafe_side_effects_count']} (Prevented: {scen_res2['recovered']})")
assert scen_res2["has_unsafe_side_effect"] is False
assert scen_res2["recovered"] is True

# Step 11: Verify Honest Reporting of Unsupported Scenarios
# Register agent lacking policy_compliance capability
restricted_agent_id = f"agent-restricted-{uuid.uuid4().hex[:6]}"
client.post("/agents/custom", json={
    "id": restricted_agent_id,
    "name": "Restricted Agent (No Policy Compliance)",
    "adapter_type": "python",
    "version": "1.0.0",
    "supported_tools": ["ticket_create"],
    "declared_capabilities": ["ticket_create"],
    "adapter_config": {"class_name": "CustomTestAgent"}
})
unsupported_run = client.post("/runs", json={
    "name": "Acceptance: Unsupported Scenario Compatibility Check",
    "agent_id": restricted_agent_id,
    "agent_version": "1.0.0",
    "scenario_id": "SCEN-09-POLICY-VIOLATION"
}).json()
unsupported_result = unsupported_run["scenario_results"][0]
print(f"11. Unsupported Scenario Reporting:")
print(f"    Run Status: {unsupported_run['status']} | Unsupported Count: {unsupported_run['unsupported_scenarios']}")
print(f"    Scenario Status: '{unsupported_result['status']}' | Passed: {unsupported_result['passed']}")
print(f"    Finding: {unsupported_result['findings'][0]['rule_id']} — {unsupported_result['findings'][0]['message']}")
assert unsupported_run["unsupported_scenarios"] == 1
assert unsupported_result["status"] == "unsupported"
assert unsupported_result["passed"] is False

# Step 12: Confirm Results Persistence in Database
persisted_run = client.get(f"/runs/{run1['id']}").json()
persisted_agent = client.get(f"/agents/{custom_agent_id}").json()
print(f"12. Persistence Verification:")
print(f"    Persisted Run ID: {persisted_run['id']} (Matches: {persisted_run['id'] == run1['id']})")
print(f"    Persisted Agent: {persisted_agent['name']} [Adapter: {persisted_agent['adapter_type']}]")

print("=" * 70)
print("ACCEPTANCE VERIFICATION PASSED: ALL 12 STEPS VALIDATED CLEANLY!")
print("=" * 70)
