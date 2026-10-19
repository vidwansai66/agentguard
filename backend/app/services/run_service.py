import uuid
import json
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
# pyrefly: ignore[missing-import]
from app.models.agent import Agent, AgentVersion
from app.models.scenario import Scenario
from app.models.suite import TestSuite, SuiteScenario
from app.models.run import TestRun, ScenarioResult
from app.models.trace import TraceEvent
from app.models.evaluation import EvaluationFinding
from app.runner.executor import scenario_runner
from app.core.errors import NotFoundError, ExecutionError

class RunService:
    def execute_run(
        self,
        db: Session,
        agent_id: str,
        agent_version: str = "1.0.0",
        suite_id: str | None = None,
        scenario_id: str | None = None,
        custom_config: dict[str, Any] | None = None,
        trigger_type: str = "manual",
        run_name: str | None = None
    ) -> TestRun:
        # 1. Resolve Agent & Version Strategy
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise NotFoundError("Agent", agent_id)

        version_obj = db.query(AgentVersion).filter(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version_tag == agent_version
        ).first()

        agent_strategy = version_obj.strategy if version_obj else "baseline"
        agent_cfg = dict(version_obj.config if version_obj else {})
        if custom_config:
            agent_cfg.update(custom_config)

        # 2. Resolve Scenarios
        scenarios: list[Scenario] = []
        if scenario_id:
            scen = db.query(Scenario).filter(Scenario.id == scenario_id).first()
            if not scen:
                raise NotFoundError("Scenario", scenario_id)
            scenarios = [scen]
        elif suite_id:
            suite = db.query(TestSuite).filter(TestSuite.id == suite_id).first()
            if not suite:
                raise NotFoundError("TestSuite", suite_id)
            suite_scens = db.query(SuiteScenario).filter(SuiteScenario.suite_id == suite_id).order_by(SuiteScenario.order).all()
            scen_ids = [ss.scenario_id for ss in suite_scens]
            scenarios = db.query(Scenario).filter(Scenario.id.in_(scen_ids)).all()
            # Preserve order
            order_map = {sid: idx for idx, sid in enumerate(scen_ids)}
            scenarios.sort(key=lambda s: order_map.get(s.id, 999))
        else:
            scenarios = db.query(Scenario).filter(Scenario.is_enabled == True).all()

        if not scenarios:
            raise ExecutionError("No scenarios available to execute.")

        # 3. Create TestRun record
        run_id = f"RUN-{uuid.uuid4().hex[:10]}"
        default_name = f"Run {agent_version} on {suite_id or (scenarios[0].name if len(scenarios) == 1 else 'All Scenarios')}"
        agent_obs_level = getattr(agent, "observability_level", "level_3_instrumented_tools")
        test_run = TestRun(
            id=run_id,
            name=run_name or default_name,
            agent_id=agent_id,
            agent_version=agent_version,
            suite_id=suite_id,
            scenario_id=scenario_id,
            status="running",
            observability_level=agent_obs_level,
            trigger_type=trigger_type,
            total_scenarios=len(scenarios),
            passed_scenarios=0,
            failed_scenarios=0,
            unsafe_side_effects_count=0,
            disrupted_count=0,
            recovered_count=0,
            total_duration_ms=0.0,
            config_snapshot_json=json.dumps({
                "agent_strategy": agent_strategy,
                "agent_config": agent_cfg,
                "observability_level": agent_obs_level,
                "scenario_ids": [s.id for s in scenarios]
            }),
            started_at=datetime.utcnow()
        )
        db.add(test_run)
        db.commit()

        total_run_duration = 0.0

        # 4. Execute Scenarios sequentially
        try:
            for scen in scenarios:
                # Check if run was cancelled mid-flight
                db.refresh(test_run)
                if test_run.status == "cancelled":
                    break

                scen_dict = scen.to_dict()
                adapter_cfg = dict(getattr(agent, "adapter_config", {}) or {})
                adapter_cfg["observability_level"] = agent_obs_level
                if agent.declared_capabilities is not None:
                    adapter_cfg["declared_capabilities"] = agent.declared_capabilities
                if agent.supported_tools is not None:
                    adapter_cfg["supported_tools"] = agent.supported_tools

                result = scenario_runner.run_scenario(
                    scenario_data=scen_dict,
                    agent_id=agent_id,
                    agent_version=agent_version,
                    agent_strategy=agent_strategy,
                    custom_config=agent_cfg,
                    run_id=run_id,
                    adapter_type=getattr(agent, "adapter_type", "python"),
                    agent_adapter_config=adapter_cfg
                )

                total_run_duration += result["duration_ms"]

                # Create ScenarioResult
                scen_res = ScenarioResult(
                    id=result["id"],
                    run_id=run_id,
                    scenario_id=scen.id,
                    scenario_name=scen.name,
                    scenario_version=scen.version,
                    failure_type=scen.failure_type,
                    status=result["status"],
                    passed=result["passed"],
                    disrupted=result["disrupted"],
                    recovered=result["recovered"],
                    has_unsafe_side_effect=result["has_unsafe_side_effect"],
                    duration_ms=result["duration_ms"],
                    retry_count=result["retry_count"],
                    step_count=result["step_count"],
                    error_message=result["error_message"],
                    execution_output_json=json.dumps(result["execution_output"]),
                    scenario_snapshot_json=json.dumps(result["scenario_snapshot"])
                )
                db.add(scen_res)
                db.flush()

                # Add TraceEvents
                for evt in result["trace_events"]:
                    trace_evt = TraceEvent(
                        id=evt["id"],
                        run_id=run_id,
                        scenario_result_id=scen_res.id,
                        scenario_id=scen.id,
                        step_index=evt["step_index"],
                        event_type=evt["event_type"],
                        severity=evt["severity"],
                        action_name=evt.get("action_name"),
                        tool_name=evt.get("tool_name"),
                        sanitized_input_json=json.dumps(evt.get("sanitized_input", {})),
                        sanitized_output_json=json.dumps(evt.get("sanitized_output", {})),
                        fault_details_json=json.dumps(evt.get("fault_details", {})),
                        retry_count=evt.get("retry_count", 0),
                        duration_ms=evt.get("duration_ms", 0.0),
                        error_message=evt.get("error_message")
                    )
                    db.add(trace_evt)

                # Add EvaluationFindings
                for fnd in result["findings"]:
                    eval_fnd = EvaluationFinding(
                        id=f"FND-{uuid.uuid4().hex[:10]}",
                        run_id=run_id,
                        scenario_result_id=scen_res.id,
                        scenario_id=scen.id,
                        rule_id=fnd["rule_id"],
                        rule_name=fnd["rule_name"],
                        status=fnd["status"],
                        severity=fnd["severity"],
                        message=fnd["message"],
                        explanation=fnd.get("explanation"),
                        trace_event_ids_json=json.dumps(fnd.get("trace_event_ids", [])),
                        evidence_json=json.dumps(fnd.get("evidence", {}))
                    )
                    db.add(eval_fnd)

                # Update aggregate counts
                if result["status"] == "unsupported":
                    test_run.unsupported_scenarios += 1
                elif result["passed"]:
                    test_run.passed_scenarios += 1
                else:
                    test_run.failed_scenarios += 1

                if result["has_unsafe_side_effect"]:
                    test_run.unsafe_side_effects_count += 1

                if result["disrupted"]:
                    test_run.disrupted_count += 1

                if result["recovered"]:
                    test_run.recovered_count += 1

            if test_run.status != "cancelled":
                test_run.status = "completed"
            test_run.total_duration_ms = round(total_run_duration, 2)
            test_run.completed_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            test_run.status = "failed"
            test_run.completed_at = datetime.utcnow()
            db.commit()
            raise ExecutionError(f"Run execution encountered error: {str(e)}")

        return test_run

run_service = RunService()
