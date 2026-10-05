"""Preserve template instructions from legacy anamneses.

Revision ID: 20261005_0006
Revises: 20261005_0005
Create Date: 2026-10-05
"""
from alembic import op
import sqlalchemy as sa

revision = "20261005_0006"
down_revision = "20261005_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("anamnesis_templates")}
    if "instructions" not in columns:
        op.add_column("anamnesis_templates", sa.Column("instructions", sa.Text(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("anamnesis_templates")}
    if "instructions" in columns:
        op.drop_column("anamnesis_templates", "instructions")
