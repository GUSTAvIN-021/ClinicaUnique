"""Add a distinct professional-absence appointment status.

Revision ID: 20261013_0010
Revises: 20261013_0009
Create Date: 2026-10-13
"""

from alembic import op


revision = "20261013_0010"
down_revision = "20261013_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE appointmentstatus ADD VALUE IF NOT EXISTS 'FALTOU_PROFISSIONAL'")


def downgrade() -> None:
    # PostgreSQL does not support removing a single enum value safely.
    pass
