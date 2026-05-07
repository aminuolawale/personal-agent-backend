from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String, nullable=False, default="mock")
    model_name: Mapped[str] = mapped_column(String, nullable=False, default="mock-planner")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    recursion_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    is_root: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tools: Mapped[list["AgentTool"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
    child_connections: Mapped[list["AgentConnection"]] = relationship(
        foreign_keys="AgentConnection.parent_agent_id",
        back_populates="parent_agent",
        cascade="all, delete-orphan",
    )
    parent_connections: Mapped[list["AgentConnection"]] = relationship(
        foreign_keys="AgentConnection.child_agent_id",
        back_populates="child_agent",
        cascade="all, delete-orphan",
    )


class AgentConnection(Base, TimestampMixin):
    __tablename__ = "agent_connections"
    __table_args__ = (
        UniqueConstraint("parent_agent_id", "child_agent_id"),
        UniqueConstraint("parent_agent_id", "alias"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    parent_agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    memory_mode: Mapped[str] = mapped_column(String, nullable=False, default="per_invocation")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parent_agent: Mapped[Agent] = relationship(
        foreign_keys=[parent_agent_id], back_populates="child_connections"
    )
    child_agent: Mapped[Agent] = relationship(
        foreign_keys=[child_agent_id], back_populates="parent_connections"
    )


class AgentTool(Base, TimestampMixin):
    __tablename__ = "agent_tools"
    __table_args__ = (UniqueConstraint("agent_id", "name"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    agent_id: Mapped[UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    agent: Mapped[Agent] = relationship(back_populates="tools")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    root_agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    input: Mapped[str] = mapped_column(Text, nullable=False)
    output: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trace_events.id", ondelete="SET NULL")
    )
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
