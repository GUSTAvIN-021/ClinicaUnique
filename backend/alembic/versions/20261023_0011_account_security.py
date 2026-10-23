"""Add session invalidation and authenticator-app MFA to user accounts.

Revision ID: 20261023_0011
Revises: 20261013_0010
"""

from alembic import op
import sqlalchemy as sa

revision = "20261023_0011"
down_revision = "20261013_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The initial migration creates this table in new installations.  Existing
    # installations created before audit logging need it here as well.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100) NOT NULL,
            resource_id VARCHAR(100) NOT NULL,
            details JSON NOT NULL DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action)")
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("mfa_secret", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("users", "token_version", server_default=None)
    op.alter_column("users", "mfa_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "token_version")
