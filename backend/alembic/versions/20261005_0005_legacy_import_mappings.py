"""Track idempotent legacy data imports.

Revision ID: 20261005_0005
Revises: 20261001_0004
Create Date: 2026-10-05
"""
from alembic import op
import sqlalchemy as sa

revision = "20261005_0005"
down_revision = "20261001_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("legacy_import_mappings"):
        return
    op.create_table(
        "legacy_import_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="emergent"),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("legacy_id", sa.String(length=100), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("source", "entity_type", "legacy_id", name="uq_legacy_import_mapping"),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("legacy_import_mappings"):
        op.drop_table("legacy_import_mappings")
