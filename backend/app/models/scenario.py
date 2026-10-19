from datetime import datetime
import json
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="ticketing")
    failure_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="medium") # low, medium, high, critical
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_seeded: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

    task_input_json: Mapped[str] = mapped_column(Text, default="{}")
    expected_outcome_json: Mapped[str] = mapped_column(Text, default="{}")
    fault_parameters_json: Mapped[str] = mapped_column(Text, default="{}")
    allowed_tools_json: Mapped[str] = mapped_column(Text, default="[]")
    policy_constraints_json: Mapped[str] = mapped_column(Text, default="{}")
    execution_limits_json: Mapped[str] = mapped_column(Text, default="{}")
    expected_assertions_json: Mapped[str] = mapped_column(Text, default="[]")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship("ScenarioVersion", back_populates="scenario", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "failure_type": self.failure_type,
            "severity": self.severity,
            "is_enabled": self.is_enabled,
            "is_seeded": self.is_seeded,
            "version": self.version,
            "task_input": json.loads(self.task_input_json or "{}"),
            "expected_outcome": json.loads(self.expected_outcome_json or "{}"),
            "fault_parameters": json.loads(self.fault_parameters_json or "{}"),
            "allowed_tools": json.loads(self.allowed_tools_json or "[]"),
            "policy_constraints": json.loads(self.policy_constraints_json or "{}"),
            "execution_limits": json.loads(self.execution_limits_json or "{}"),
            "expected_assertions": json.loads(self.expected_assertions_json or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScenarioVersion(Base):
    __tablename__ = "scenario_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), ForeignKey("scenarios.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scenario = relationship("Scenario", back_populates="versions")
