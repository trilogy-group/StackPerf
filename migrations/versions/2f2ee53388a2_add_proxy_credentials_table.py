"""Add proxy_credentials table for session-scoped credential metadata.

Revision ID: 2f2ee53388a2
Revises: 03e22a58f3a7
Create Date: 2025-03-27 02:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2f2ee53388a2"
down_revision: Union[str, None] = "03e22a58f3a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create proxy_credentials table and add column to sessions."""
    # Create proxy_credentials table
    op.create_table(
        "proxy_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_alias", sa.String(255), nullable=False),
        sa.Column("experiment_id", sa.String(255), nullable=False),
        sa.Column("variant_id", sa.String(255), nullable=False),
        sa.Column("harness_profile", sa.String(255), nullable=False),
        sa.Column("litellm_key_id", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_alias"),
        sa.UniqueConstraint("session_id"),
    )

    # Add index on key_alias for fast lookups
    op.create_index("ix_proxy_credentials_key_alias", "proxy_credentials", ["key_alias"])

    # Add index on session_id
    op.create_index("ix_proxy_credentials_session_id", "proxy_credentials", ["session_id"])

    # Add column to sessions table for credential alias reference (not a FK)
    op.add_column(
        "sessions",
        sa.Column("proxy_credential_alias", sa.String(255), nullable=True)
    )

    # Create index on the alias column for joins
    op.create_index("ix_sessions_proxy_credential_alias", "sessions", ["proxy_credential_alias"])


def downgrade() -> None:
    """Remove proxy_credentials table and revert sessions changes."""
    # Drop index from sessions
    op.drop_index("ix_sessions_proxy_credential_alias", table_name="sessions")
    op.drop_column("sessions", "proxy_credential_alias")

    # Drop indexes from proxy_credentials
    op.drop_index("ix_proxy_credentials_session_id", table_name="proxy_credentials")
    op.drop_index("ix_proxy_credentials_key_alias", table_name="proxy_credentials")

    # Drop proxy_credentials table
    op.drop_table("proxy_credentials")
