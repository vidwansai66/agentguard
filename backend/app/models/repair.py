from datetime import datetime
import json
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class RepairProposal(Base):
    __tablename__ = "repair_proposals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    diagnosis_id: Mapped[str] = mapped_column(String(64), ForeignKey("diagnoses.id"), nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)

    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    proposed_change: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_benefit: Mapped[str] = mapped_column(Text, nullable=False)
    potential_risks: Mapped[str] = mapped_column(Text, nullable=False)
    patch_diff: Mapped[str] = mapped_column(Text, nullable=False)

    target_agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    base_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    candidate_version_tag: Mapped[str] = mapped_column(String(32), nullable=False)
    candidate_strategy: Mapped[str] = mapped_column(String(64), default="safe_idempotent")
    candidate_config_json: Mapped[str] = mapped_column(Text, default="{}")

    approval_status: Mapped[str] = mapped_column(String(32), default="pending") # pending, approved, rejected
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    rejected_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    verification_status: Mapped[str] = mapped_column(String(32), default="unverified") # unverified, verifying, verified_passed, verified_failed
    candidate_run_id: Mapped[str] = mapped_column(String(64), nullable=True)
    comparison_id: Mapped[str] = mapped_column(String(64), nullable=True)
    verification_summary_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    diagnosis = relationship("Diagnosis", back_populates="repair_proposals")


class PatchVersion(Base):
    __tablename__ = "patch_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
