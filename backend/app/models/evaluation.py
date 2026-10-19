from datetime import datetime
import json
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class EvaluationFinding(Base):
    __tablename__ = "evaluation_findings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_result_id: Mapped[str] = mapped_column(String(64), ForeignKey("scenario_results.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False)

    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False) # passed, failed, warning
    severity: Mapped[str] = mapped_column(String(32), default="medium") # low, medium, high, critical

    message: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    trace_event_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scenario_result = relationship("ScenarioResult", back_populates="findings")
