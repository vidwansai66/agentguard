from datetime import datetime
import json
from sqlalchemy import String, Text, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(String(64), default="python_mock_agent")  # e.g., python_sample
    adapter_type: Mapped[str] = mapped_column(String(32), default="python")  # python, http
    registration_source: Mapped[str] = mapped_column(String(32), default="built_in")  # built_in, custom
    status: Mapped[str] = mapped_column(String(32), default="active")  # active, disabled, archived
    observability_level: Mapped[str] = mapped_column(String(32), default="level_3_instrumented_tools")  # level_1_result_only, level_2_structured_events, level_3_instrumented_tools
    current_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    supported_tools_json: Mapped[str] = mapped_column(Text, default="[]")
    declared_capabilities_json: Mapped[str] = mapped_column(Text, default="[]")
    adapter_config_json: Mapped[str] = mapped_column(Text, default="{}")
    config_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship("AgentVersion", back_populates="agent", cascade="all, delete-orphan")

    @property
    def supported_tools(self) -> list:
        try:
            return json.loads(self.supported_tools_json or "[]")
        except Exception:
            return []

    @supported_tools.setter
    def supported_tools(self, val: list):
        self.supported_tools_json = json.dumps(val or [])

    @property
    def declared_capabilities(self) -> list:
        try:
            return json.loads(self.declared_capabilities_json or "[]")
        except Exception:
            return []

    @declared_capabilities.setter
    def declared_capabilities(self, val: list):
        self.declared_capabilities_json = json.dumps(val or [])

    @property
    def adapter_config(self) -> dict:
        try:
            return json.loads(self.adapter_config_json or "{}")
        except Exception:
            return {}

    @adapter_config.setter
    def adapter_config(self, val: dict):
        self.adapter_config_json = json.dumps(val or {})


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(64), ForeignKey("agents.id"), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. 1.0.0, 1.1.0-patch1
    strategy: Mapped[str] = mapped_column(String(64), default="baseline") # baseline, safe_idempotent, bounded_backoff, strict_policy
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="versions")

    @property
    def config(self) -> dict:
        try:
            return json.loads(self.config_json or "{}")
        except Exception:
            return {}

    @config.setter
    def config(self, val: dict):
        self.config_json = json.dumps(val or {})
