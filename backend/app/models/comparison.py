from datetime import datetime
import json
from sqlalchemy import String, Text, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    baseline_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_run_id: Mapped[str] = mapped_column(String(64), nullable=False)

    baseline_agent_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    candidate_agent_version: Mapped[str] = mapped_column(String(32), default="1.1.0-patch")

    baseline_success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_success_rate: Mapped[float] = mapped_column(Float, default=0.0)

    baseline_recovery_rate: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_recovery_rate: Mapped[float] = mapped_column(Float, default=0.0)

    baseline_unsafe_side_effect_rate: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_unsafe_side_effect_rate: Mapped[float] = mapped_column(Float, default=0.0)

    baseline_median_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_median_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    baseline_p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    regression_rate: Mapped[float] = mapped_column(Float, default=0.0)

    newly_passing_scenarios_json: Mapped[str] = mapped_column(Text, default="[]")
    newly_failing_scenarios_json: Mapped[str] = mapped_column(Text, default="[]")
    safety_regressions_json: Mapped[str] = mapped_column(Text, default="[]")
    per_scenario_comparison_json: Mapped[str] = mapped_column(Text, default="[]")

    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    verification_verdict: Mapped[str] = mapped_column(String(32), default="undetermined") # verified_passed, verified_failed, trade_offs_detected

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
