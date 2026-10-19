from pydantic import BaseModel, Field
from typing import Any

class SystemStatusResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    database_connected: bool = True
    database_url_type: str = "sqlite"
    registered_agents_count: int = 0
    total_scenarios_count: int = 0
    total_runs_count: int = 0
    uptime_seconds: float = 0.0

class CategoryMetric(BaseModel):
    category: str
    total: int
    passed: int
    failed: int
    pass_rate: float

class TrendPoint(BaseModel):
    run_id: str
    run_name: str
    timestamp: str
    success_rate: float
    unsafe_side_effect_rate: float
    duration_ms: float

class DashboardStatsResponse(BaseModel):
    total_runs: int = 0
    task_success_rate: float = 0.0
    recovery_rate: float = 0.0
    unsafe_side_effect_rate: float = 0.0
    total_failures: int = 0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    cost_per_successful_task: str = "N/A (Local Mock Environment)"
    recent_runs: list[dict[str, Any]] = Field(default_factory=list)
    failure_type_metrics: list[CategoryMetric] = Field(default_factory=list)
    trend_history: list[TrendPoint] = Field(default_factory=list)
    active_regressions_count: int = 0
