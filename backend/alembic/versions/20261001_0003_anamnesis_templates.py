"""Create structured anamnesis templates.

Revision ID: 20261001_0003
Revises: 20261001_0002
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261001_0003"
down_revision = "20261001_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("anamnesis_templates"):
        return
    op.create_table(
        "anamnesis_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("category", name="uq_anamnesis_template_category"),
    )
    op.create_index("ix_anamnesis_templates_category", "anamnesis_templates", ["category"])
    op.create_index("ix_anamnesis_templates_active", "anamnesis_templates", ["active"])


def downgrade() -> None:
    op.drop_index("ix_anamnesis_templates_active", table_name="anamnesis_templates")
    op.drop_index("ix_anamnesis_templates_category", table_name="anamnesis_templates")
    op.drop_table("anamnesis_templates")
