"""Remove financial values from appointment scheduling.

Revision ID: 20261013_0009
Revises: 20261013_0008
Create Date: 2026-10-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20261013_0009"
down_revision = "20261013_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("appointments", "amount_cents")
    op.drop_column("appointment_series", "amount_cents")


def downgrade() -> None:
    op.add_column("appointment_series", sa.Column("amount_cents", sa.Integer(), nullable=True))
    op.add_column("appointments", sa.Column("amount_cents", sa.Integer(), nullable=True))
