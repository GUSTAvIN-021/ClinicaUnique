"""Store service type and amount on appointments.

Revision ID: 20261013_0007
Revises: 20261005_0006
Create Date: 2026-10-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20261013_0007"
down_revision = "20261005_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("service_type", sa.String(length=100), nullable=True))
    op.add_column("appointments", sa.Column("amount_cents", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("appointments", "amount_cents")
    op.drop_column("appointments", "service_type")
