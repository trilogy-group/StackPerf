"""Add proxy_keys table for LiteLLM virtual key metadata registry.

Revision ID: b356c861829f
Revises: 2f2ee53388a2
Create Date: 2025-04-21 19:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b356c861829f"
down_revision: Union[str, None] = "2f2ee53388a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create proxy_keys table with indexes."""
    op.create_table(
        "proxy_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_alias", sa.String(255), nullable=False),
        sa.Column("litellm_key_id", sa.String(255), nullable=True),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("team", sa.String(255), nullable=True),
        sa.Column("customer", sa.String(255), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("allowed_models", sa.JSON(), nullable=True, default=list),
        sa.Column("budget_duration", sa.String(50), nullable=True),
        sa.Column("budget_amount", sa.Float(), nullable=True),
        sa.Column("budget_currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column(
            "status", sa.String(50), nullable=False, default="active", server_default="active"
        ),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'expired')", name="ck_proxy_keys_status"
        ),
        sa.Column("key_metadata", sa.JSON(), nullable=True, default=dict),
        sa.Column("proxy_credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_alias"),
        sa.ForeignKeyConstraint(
            ["proxy_credential_id"],
            ["proxy_credentials.id"],
            ondelete="SET NULL",
        ),
    )

    # Indexes for lookup patterns (key_alias already has unique constraint index)
    op.create_index("ix_proxy_keys_litellm_key_id", "proxy_keys", ["litellm_key_id"])
    op.create_index("ix_proxy_keys_owner", "proxy_keys", ["owner"])
    op.create_index("ix_proxy_keys_team", "proxy_keys", ["team"])
    op.create_index("ix_proxy_keys_customer", "proxy_keys", ["customer"])
    op.create_index("ix_proxy_keys_status", "proxy_keys", ["status"])
    op.create_index(
        "ix_proxy_keys_owner_team_customer",
        "proxy_keys",
        ["owner", "team", "customer"],
    )
    op.create_index(
        "ix_proxy_keys_status_created_at",
        "proxy_keys",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_proxy_keys_proxy_credential_id",
        "proxy_keys",
        ["proxy_credential_id"],
    )


def downgrade() -> None:
    """Drop proxy_keys table and indexes."""
    op.drop_index("ix_proxy_keys_proxy_credential_id", table_name="proxy_keys")
    op.drop_index("ix_proxy_keys_status_created_at", table_name="proxy_keys")
    op.drop_index("ix_proxy_keys_owner_team_customer", table_name="proxy_keys")
    op.drop_index("ix_proxy_keys_status", table_name="proxy_keys")
    op.drop_index("ix_proxy_keys_customer", table_name="proxy_keys")
    op.drop_index("ix_proxy_keys_team", table_name="proxy_keys")
    op.drop_index("ix_proxy_keys_owner", table_name="proxy_keys")
    op.drop_index("ix_proxy_keys_litellm_key_id", table_name="proxy_keys")
    op.drop_table("proxy_keys")
