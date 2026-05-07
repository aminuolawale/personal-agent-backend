"""initial neon schema

Revision ID: 202605071800
Revises:
Create Date: 2026-05-07 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605071800"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("model_provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("max_iterations", sa.Integer(), nullable=False),
        sa.Column("recursion_limit", sa.Integer(), nullable=False),
        sa.Column("is_root", sa.Boolean(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_agents_slug"), "agents", ["slug"], unique=False)

    op.create_table(
        "agent_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_agent_id", sa.Uuid(), nullable=False),
        sa.Column("child_agent_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("memory_mode", sa.String(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["child_agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_agent_id", "alias"),
        sa.UniqueConstraint("parent_agent_id", "child_agent_id"),
    )
    op.create_index(
        op.f("ix_agent_connections_child_agent_id"),
        "agent_connections",
        ["child_agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_connections_parent_agent_id"),
        "agent_connections",
        ["parent_agent_id"],
        unique=False,
    )

    op.create_table(
        "agent_tools",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "name"),
    )
    op.create_index(op.f("ix_agent_tools_agent_id"), "agent_tools", ["agent_id"], unique=False)

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("root_agent_id", sa.Uuid(), nullable=False),
        sa.Column("thread_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["root_agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_root_agent_id"), "agent_runs", ["root_agent_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_thread_id"), "agent_runs", ["thread_id"], unique=False)

    op.create_table(
        "trace_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("parent_event_id", sa.Uuid(), nullable=True),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["parent_event_id"], ["trace_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trace_events_agent_id"), "trace_events", ["agent_id"], unique=False)
    op.create_index(op.f("ix_trace_events_run_id"), "trace_events", ["run_id"], unique=False)
    op.create_index("idx_trace_events_run_created", "trace_events", ["run_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_trace_events_run_created", table_name="trace_events")
    op.drop_index(op.f("ix_trace_events_run_id"), table_name="trace_events")
    op.drop_index(op.f("ix_trace_events_agent_id"), table_name="trace_events")
    op.drop_table("trace_events")
    op.drop_index(op.f("ix_agent_runs_thread_id"), table_name="agent_runs")
    op.drop_index(op.f("ix_agent_runs_root_agent_id"), table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index(op.f("ix_agent_tools_agent_id"), table_name="agent_tools")
    op.drop_table("agent_tools")
    op.drop_index(op.f("ix_agent_connections_parent_agent_id"), table_name="agent_connections")
    op.drop_index(op.f("ix_agent_connections_child_agent_id"), table_name="agent_connections")
    op.drop_table("agent_connections")
    op.drop_index(op.f("ix_agents_slug"), table_name="agents")
    op.drop_table("agents")

