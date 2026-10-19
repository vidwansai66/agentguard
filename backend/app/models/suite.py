from datetime import datetime
import json
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class TestSuite(Base):
    __tablename__ = "test_suites"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_regression_suite: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    suite_scenarios = relationship("SuiteScenario", back_populates="suite", cascade="all, delete-orphan")


class SuiteScenario(Base):
    __tablename__ = "suite_scenarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    suite_id: Mapped[str] = mapped_column(String(64), ForeignKey("test_suites.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(64), nullable=False)
    order: Mapped[int] = mapped_column(default=0)

    suite = relationship("TestSuite", back_populates="suite_scenarios")
