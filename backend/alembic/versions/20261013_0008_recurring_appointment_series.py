"""Create rules for indefinitely recurring appointments.

Revision ID: 20261013_0008
Revises: 20261013_0007
Create Date: 2026-10-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20261013_0008"
down_revision = "20261013_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "appointment_series",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("professional_id", sa.Integer(), sa.ForeignKey("professionals.id"), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("service_type", sa.String(length=100), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_appointment_series_professional_id", "appointment_series", ["professional_id"])
    op.create_index("ix_appointment_series_starts_on", "appointment_series", ["starts_on"])
    op.create_index("ix_appointment_series_active", "appointment_series", ["active"])


def downgrade() -> None:
    op.drop_index("ix_appointment_series_active", table_name="appointment_series")
    op.drop_index("ix_appointment_series_starts_on", table_name="appointment_series")
    op.drop_index("ix_appointment_series_professional_id", table_name="appointment_series")
    op.drop_table("appointment_series")
