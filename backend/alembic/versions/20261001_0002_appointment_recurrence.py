"""Add recurrence group to appointments.

Revision ID: 20261001_0002
Revises: 20260818_0001
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261001_0002"
down_revision = "20260818_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("appointments")}
    indexes = {index["name"] for index in inspector.get_indexes("appointments")}
    # The initial migration creates from SQLAlchemy metadata. These guards also
    # make a fresh database and an already-running development database safe.
    if "recurrence_group_id" not in columns:
        op.add_column("appointments", sa.Column("recurrence_group_id", sa.String(length=36), nullable=True))
    if "ix_appointments_recurrence_group_id" not in indexes:
        op.create_index("ix_appointments_recurrence_group_id", "appointments", ["recurrence_group_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("appointments")}
    columns = {column["name"] for column in inspector.get_columns("appointments")}
    if "ix_appointments_recurrence_group_id" in indexes:
        op.drop_index("ix_appointments_recurrence_group_id", table_name="appointments")
    if "recurrence_group_id" in columns:
        op.drop_column("appointments", "recurrence_group_id")
