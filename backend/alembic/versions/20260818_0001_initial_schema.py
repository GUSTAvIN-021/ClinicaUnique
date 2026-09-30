"""Initial Unique clinical management schema.

Revision ID: 20260818_0001
Revises:
Create Date: 2026-08-18
"""
from alembic import op

from app.core.database import Base
import app.models.entities  # noqa: F401 - loads all mapped models into metadata

revision = "20260818_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the initial schema from the reviewed SQLAlchemy metadata."""
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    """Remove only the tables introduced by this initial revision."""
    Base.metadata.drop_all(bind=op.get_bind())
