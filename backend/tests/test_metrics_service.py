import pytest
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.models.run import TestRun, ScenarioResult
from app.services.metrics_service import MetricsService

TestRun.__test__ = False

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_metrics_service_empty_db(test_db):
    service = MetricsService()
    stats = service.get_dashboard_metrics(test_db)
    assert stats["total_runs"] == 0
    assert stats["total_scenarios_count"] == 0
    assert stats["task_success_rate"] == 0.0
    assert stats["recovery_rate"] is None
    assert stats["unsafe_side_effect_rate"] == 0.0
    assert stats["total_failures"] == 0
    assert stats["median_latency_ms"] == 0.0
    assert stats["p95_latency_ms"] == 0.0
    assert stats["cost_per_successful_task"] == "$0.00 (Local Mock Environment)"

def test_metrics_service_normal_run_without_disruptions(test_db):
    service = MetricsService()
    run = TestRun(
        id="RUN-TEST-1",
        name="Normal Run",
        agent_id="agent-test",
        agent_version="1.0.0",
        status="completed",
        total_scenarios=1,
        passed_scenarios=1,
        failed_scenarios=0,
        disrupted_count=0,
        recovered_count=0,
        unsafe_side_effects_count=0,
        total_duration_ms=1.2,
        created_at=datetime.datetime.utcnow()
    )
    test_db.add(run)
    res = ScenarioResult(
        id="RES-TEST-1",
        run_id=run.id,
        scenario_id="SCEN-01",
        scenario_name="Normal Scenario",
        failure_type="normal_execution",
        status="passed",
        passed=True,
        disrupted=False,
        recovered=False,
        has_unsafe_side_effect=False,
        duration_ms=1.2
    )
    test_db.add(res)
    test_db.commit()

    stats = service.get_dashboard_metrics(test_db)
    assert stats["total_runs"] == 1
    assert stats["total_scenarios_count"] == 1
    assert stats["passed_scenarios_count"] == 1
    assert stats["failed_scenarios_count"] == 0
    assert stats["disrupted_scenarios_count"] == 0
    assert stats["recovered_scenarios_count"] == 0
    assert stats["task_success_rate"] == 1.0
    # No disruptions evaluated, so recovery_rate is None (represented as N/A, not misleading 0%)
    assert stats["recovery_rate"] is None
    assert stats["unsafe_side_effect_rate"] == 0.0
    assert stats["median_latency_ms"] == 1.2

def test_metrics_service_suite_with_disruptions_and_recovery(test_db):
    service = MetricsService()
    run = TestRun(
        id="RUN-SUITE-1",
        name="Reliability Suite",
        agent_id="agent-order",
        agent_version="1.0.0",
        status="completed",
        total_scenarios=6,
        passed_scenarios=4,
        failed_scenarios=2,
        disrupted_count=4,
        recovered_count=3,
        unsafe_side_effects_count=0,
        total_duration_ms=4.21,
        created_at=datetime.datetime.utcnow()
    )
    test_db.add(run)

    # 4 passed (3 recovered), 2 failed (1 unrecovered, 1 normal failed)
    scenarios_data = [
        ("SCEN-1", "normal_execution", True, False, False, False, 0.5),
        ("SCEN-2", "transient_timeout", False, True, False, False, 0.78),
        ("SCEN-3", "ambiguous_outcome", True, True, True, False, 0.65),
        ("SCEN-4", "repeated_action", True, True, True, False, 0.71),
        ("SCEN-5", "ambiguous_outcome", True, True, True, False, 0.67),
        ("SCEN-6", "normal_execution", False, False, False, False, 0.9),
    ]

    for i, (scen_id, ft, passed, disrupted, recovered, unsafe, dur) in enumerate(scenarios_data):
        test_db.add(ScenarioResult(
            id=f"RES-{i}",
            run_id=run.id,
            scenario_id=scen_id,
            scenario_name=scen_id,
            failure_type=ft,
            status="passed" if passed else "failed",
            passed=passed,
            disrupted=disrupted,
            recovered=recovered,
            has_unsafe_side_effect=unsafe,
            duration_ms=dur
        ))
    test_db.commit()

    stats = service.get_dashboard_metrics(test_db)
    assert stats["total_runs"] == 1
    assert stats["total_scenarios_count"] == 6
    assert stats["passed_scenarios_count"] == 4
    assert stats["failed_scenarios_count"] == 2
    assert stats["disrupted_scenarios_count"] == 4
    assert stats["recovered_scenarios_count"] == 3
    assert stats["task_success_rate"] == round(4 / 6, 4)
    # Recovery rate is exactly 3/4 = 0.75
    assert stats["recovery_rate"] == 0.75
    assert stats["unsafe_side_effect_rate"] == 0.0
    # Median of [0.5, 0.65, 0.67, 0.71, 0.78, 0.9] -> index 3 -> 0.71
    assert stats["median_latency_ms"] == 0.71

def test_metrics_service_self_healing_stale_counters(test_db):
    service = MetricsService()
    # Simulate a run where db.refresh previously corrupted the counters
    stale_run = TestRun(
        id="RUN-STALE-1",
        name="Corrupted Run",
        agent_id="agent-custom",
        agent_version="1.0.0",
        status="completed",
        total_scenarios=6,
        passed_scenarios=0, # corrupted
        failed_scenarios=1, # corrupted
        disrupted_count=0,  # corrupted
        recovered_count=0,  # corrupted
        unsafe_side_effects_count=0,
        total_duration_ms=5.0,
        created_at=datetime.datetime.utcnow()
    )
    test_db.add(stale_run)

    # Actual results: 4 passed, 2 failed
    for i in range(4):
        test_db.add(ScenarioResult(
            id=f"RES-PASS-{i}",
            run_id=stale_run.id,
            scenario_id=f"SCEN-P{i}",
            scenario_name=f"Pass {i}",
            failure_type="normal_execution",
            status="passed",
            passed=True,
            disrupted=False,
            recovered=False,
            has_unsafe_side_effect=False,
            duration_ms=1.0
        ))
    for i in range(2):
        test_db.add(ScenarioResult(
            id=f"RES-FAIL-{i}",
            run_id=stale_run.id,
            scenario_id=f"SCEN-F{i}",
            scenario_name=f"Fail {i}",
            failure_type="transient_timeout",
            status="failed",
            passed=False,
            disrupted=True,
            recovered=False,
            has_unsafe_side_effect=False,
            duration_ms=1.5
        ))
    test_db.commit()

    stats = service.get_dashboard_metrics(test_db)
    # Metrics should be derived from the ground truth results, not the corrupted passed_scenarios=0
    assert stats["passed_scenarios_count"] == 4
    assert stats["failed_scenarios_count"] == 2
    assert stats["total_scenarios_count"] == 6
    assert stats["task_success_rate"] == round(4 / 6, 4)
    assert stats["disrupted_scenarios_count"] == 2
    assert stats["recovered_scenarios_count"] == 0
    assert stats["recovery_rate"] == 0.0

    # Confirm the run record in DB was healed
    test_db.refresh(stale_run)
    assert stale_run.passed_scenarios == 4
    assert stale_run.failed_scenarios == 2
    assert stale_run.disrupted_count == 2
