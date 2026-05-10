"""fix agents slug index

Revision ID: 202605091200
Revises: 202605071800
Create Date: 2026-05-09 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202605091200"
down_revision: str | None = "202605071800"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Replace the separate UniqueConstraint + non-unique index with a single unique index,
    # which is what SQLAlchemy 2.x generates for unique=True, index=True on a mapped column.
    op.drop_constraint("agents_slug_key", "agents", type_="unique")
    op.drop_index("ix_agents_slug", table_name="agents")
    op.create_index("ix_agents_slug", "agents", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_agents_slug", table_name="agents")
    op.create_index("ix_agents_slug", "agents", ["slug"], unique=False)
    op.create_unique_constraint("agents_slug_key", "agents", ["slug"])
