"""Create the configurable specialties catalog.

Revision ID: 20261001_0004
Revises: 20261001_0003
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa

revision = "20261001_0004"
down_revision = "20261001_0003"
branch_labels = None
depends_on = None

DEFAULT_CATEGORIES = (
    "Fonoaudiologia", "Psicologia ABA e TCC", "Psicomotricista", "Psicopedagogia",
    "Terapia Ocupacional", "Terapia Alimentar", "Musicoterapia",
    "Avaliação Neuropsicológica", "Orientação Parental", "Fisioterapia",
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("categories"):
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("name", name="uq_categories_name"),
        )
        op.create_index("ix_categories_name", "categories", ["name"])
        op.create_index("ix_categories_active", "categories", ["active"])
    for name in DEFAULT_CATEGORIES:
        op.execute(sa.text("INSERT INTO categories (name, active) VALUES (:name, true) ON CONFLICT (name) DO NOTHING").bindparams(name=name))
    op.execute(sa.text("INSERT INTO categories (name, active) SELECT DISTINCT name, true FROM professional_categories ON CONFLICT (name) DO NOTHING"))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("categories"):
        op.drop_table("categories")
