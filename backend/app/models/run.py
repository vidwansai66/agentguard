from datetime import datetime
import json
from sqlalchemy import String, Text, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    suite_id: Mapped[str] = mapped_column(String(64), nullable=True)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=True) # if single scenario run

    status: Mapped[str] = mapped_column(String(32), default="pending") # pending, running, completed, failed, cancelled
    trigger_type: Mapped[str] = mapped_column(String(32), default="manual") # manual, verification, regression

    total_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    passed_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    failed_scenarios: Mapped[int] = mapped_column(Integer, default=0)
    unsafe_side_effects_count: Mapped[int] = mapped_column(Integer, default=0)
    disrupted_count: Mapped[int] = mapped_column(Integer, default=0)
    recovered_count: Mapped[int] = mapped_column(Integer, default=0)

    total_duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    config_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scenario_results = relationship("ScenarioResult", back_populates="run", cascade="all, delete-orphan")


class ScenarioResult(Base):
    __tablename__ = "scenario_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("test_runs.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False)
    scenario_version: Mapped[int] = mapped_column(Integer, default=1)
    failure_type: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="pending") # passed, failed, error, cancelled
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    disrupted: Mapped[bool] = mapped_column(Boolean, default=False)
    recovered: Mapped[bool] = mapped_column(Boolean, default=False)
    has_unsafe_side_effect: Mapped[bool] = mapped_column(Boolean, default=False)

    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    step_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    execution_output_json: Mapped[str] = mapped_column(Text, default="{}")
    scenario_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run = relationship("TestRun", back_populates="scenario_results")
    trace_events = relationship("TraceEvent", back_populates="scenario_result", cascade="all, delete-orphan")
    findings = relationship("EvaluationFinding", back_populates="scenario_result", cascade="all, delete-orphan")
