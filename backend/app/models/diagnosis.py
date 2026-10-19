from datetime import datetime
import json
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_result_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    likely_cause: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="medium") # high, medium, low, hypothesis
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    supporting_evidence_json: Mapped[str] = mapped_column(Text, default="{}")
    relevant_trace_event_ids_json: Mapped[str] = mapped_column(Text, default="[]")

    recommended_strategy: Mapped[str] = mapped_column(String(128), nullable=False)
    recommended_patch_template_id: Mapped[str] = mapped_column(String(64), nullable=True)
    limitations: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    repair_proposals = relationship("RepairProposal", back_populates="diagnosis", cascade="all, delete-orphan")
