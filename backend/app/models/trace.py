from datetime import datetime
import json
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_result_id: Mapped[str] = mapped_column(String(64), ForeignKey("scenario_results.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False)

    step_index: Mapped[int] = mapped_column(Integer, default=0)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # event types: agent_decision, tool_call, tool_response, fault_injected, retry, policy_check, error, system
    severity: Mapped[str] = mapped_column(String(32), default="info") # info, warning, error, critical

    action_name: Mapped[str] = mapped_column(String(128), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=True)

    sanitized_input_json: Mapped[str] = mapped_column(Text, default="{}")
    sanitized_output_json: Mapped[str] = mapped_column(Text, default="{}")
    fault_details_json: Mapped[str] = mapped_column(Text, default="{}")

    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scenario_result = relationship("ScenarioResult", back_populates="trace_events")
