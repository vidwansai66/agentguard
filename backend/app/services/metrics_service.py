from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.run import TestRun, ScenarioResult
from app.models.comparison import Comparison

class MetricsService:
    def get_dashboard_metrics(self, db: Session) -> dict:
        all_runs = db.query(TestRun).order_by(desc(TestRun.created_at)).all()
        completed_runs = [r for r in all_runs if r.status == "completed"]

        total_runs = len(all_runs)
        if total_runs == 0 or len(completed_runs) == 0:
            return {
                "total_runs": total_runs,
                "task_success_rate": 0.0,
                "recovery_rate": 0.0,
                "unsafe_side_effect_rate": 0.0,
                "total_failures": 0,
                "median_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "cost_per_successful_task": "N/A (Local Mock Environment)",
                "recent_runs": [],
                "failure_type_metrics": [],
                "trend_history": [],
                "active_regressions_count": 0
            }

        total_scenarios_all = sum(r.total_scenarios for r in completed_runs)
        passed_scenarios_all = sum(r.passed_scenarios for r in completed_runs)
        failed_scenarios_all = sum(r.failed_scenarios for r in completed_runs)
        unsafe_all = sum(r.unsafe_side_effects_count for r in completed_runs)
        disrupted_all = sum(r.disrupted_count for r in completed_runs)
        recovered_all = sum(r.recovered_count for r in completed_runs)

        task_success_rate = round(passed_scenarios_all / total_scenarios_all, 4) if total_scenarios_all > 0 else 0.0
        recovery_rate = round(recovered_all / disrupted_all, 4) if disrupted_all > 0 else 0.0
        unsafe_rate = round(unsafe_all / total_scenarios_all, 4) if total_scenarios_all > 0 else 0.0

        # Compute latency percentiles across scenario results
        all_results = db.query(ScenarioResult).all()
        latencies = sorted([r.duration_ms for r in all_results if r.duration_ms > 0])
        median_lat = latencies[len(latencies) // 2] if latencies else 0.0
        p95_idx = int(len(latencies) * 0.95)
        p95_lat = latencies[min(p95_idx, len(latencies) - 1)] if latencies else 0.0

        # Group by failure_type
        failure_type_map = {}
        for r in all_results:
            ft = r.failure_type or "normal_execution"
            if ft not in failure_type_map:
                failure_type_map[ft] = {"total": 0, "passed": 0, "failed": 0}
            failure_type_map[ft]["total"] += 1
            if r.passed:
                failure_type_map[ft]["passed"] += 1
            else:
                failure_type_map[ft]["failed"] += 1

        category_metrics = [
            {
                "category": ft,
                "total": data["total"],
                "passed": data["passed"],
                "failed": data["failed"],
                "pass_rate": round(data["passed"] / (data["total"] or 1), 4)
            }
            for ft, data in failure_type_map.items()
        ]

        # Trend history (last 10 completed runs in chronological order)
        trend_history = []
        for r in reversed(completed_runs[:10]):
            trend_history.append({
                "run_id": r.id,
                "run_name": r.name,
                "timestamp": r.created_at.strftime("%H:%M:%S") if r.created_at else "",
                "success_rate": round(r.passed_scenarios / (r.total_scenarios or 1), 4),
                "unsafe_side_effect_rate": round(r.unsafe_side_effects_count / (r.total_scenarios or 1), 4),
                "duration_ms": r.total_duration_ms
            })

        # Recent runs list
        recent_runs = [
            {
                "id": r.id,
                "name": r.name,
                "agent_id": r.agent_id,
                "agent_version": r.agent_version,
                "status": r.status,
                "passed_scenarios": r.passed_scenarios,
                "total_scenarios": r.total_scenarios,
                "unsafe_side_effects_count": r.unsafe_side_effects_count,
                "duration_ms": r.total_duration_ms,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in all_runs[:10]
        ]

        # Active regressions count from latest comparisons
        latest_comparisons = db.query(Comparison).order_by(desc(Comparison.created_at)).limit(5).all()
        active_regressions = sum(1 for c in latest_comparisons if c.verification_verdict == "verified_failed")

        return {
            "total_runs": total_runs,
            "task_success_rate": task_success_rate,
            "recovery_rate": recovery_rate,
            "unsafe_side_effect_rate": unsafe_rate,
            "total_failures": failed_scenarios_all,
            "median_latency_ms": round(median_lat, 2),
            "p95_latency_ms": round(p95_lat, 2),
            "cost_per_successful_task": "N/A (Local Mock Environment)",
            "recent_runs": recent_runs,
            "failure_type_metrics": category_metrics,
            "trend_history": trend_history,
            "active_regressions_count": active_regressions
        }

metrics_service = MetricsService()
