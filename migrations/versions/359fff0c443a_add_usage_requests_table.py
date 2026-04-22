"""Add usage_requests table for LiteLLM traffic ingestion.

Revision ID: 359fff0c443a
Revises: b356c861829f
Create Date: 2025-01-21 21:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "359fff0c443a"
down_revision: Union[str, None] = "b356c861829f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create usage_requests table with indexes and idempotency constraint."""
    op.create_table(
        "usage_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("litellm_call_id", sa.String(255), nullable=False),
        sa.Column("request_id", sa.String(255), nullable=True),
        sa.Column("key_alias", sa.String(255), nullable=True),
        sa.Column("litellm_key_id", sa.String(255), nullable=True),
        sa.Column("proxy_key_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("benchmark_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(255), nullable=True),
        sa.Column("provider_route", sa.String(255), nullable=True),
        sa.Column("requested_model", sa.String(255), nullable=True),
        sa.Column("resolved_model", sa.String(255), nullable=True),
        sa.Column("route", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("ttft_ms", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_write_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=True),
        sa.Column("request_metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("litellm_call_id", name="uq_usage_requests_litellm_call_id"),
        sa.ForeignKeyConstraint(
            ["proxy_key_id"],
            ["proxy_keys.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["benchmark_session_id"],
            ["sessions.id"],
            ondelete="SET NULL",
        ),
    )

    # Core lookup indexes
    op.create_index(
        "ix_usage_requests_started_at", "usage_requests", ["started_at"]
    )
    op.create_index(
        "ix_usage_requests_key_alias", "usage_requests", ["key_alias"]
    )
    op.create_index(
        "ix_usage_requests_litellm_key_id", "usage_requests", ["litellm_key_id"]
    )
    op.create_index(
        "ix_usage_requests_proxy_key_id", "usage_requests", ["proxy_key_id"]
    )
    op.create_index(
        "ix_usage_requests_benchmark_session_id",
        "usage_requests",
        ["benchmark_session_id"],
    )
    op.create_index(
        "ix_usage_requests_resolved_model", "usage_requests", ["resolved_model"]
    )
    op.create_index(
        "ix_usage_requests_provider", "usage_requests", ["provider"]
    )
    op.create_index(
        "ix_usage_requests_status", "usage_requests", ["status"]
    )
    op.create_index(
        "ix_usage_requests_error_code", "usage_requests", ["error_code"]
    )
    # Composite for time-window + key attribution queries
    op.create_index(
        "ix_usage_requests_key_alias_started_at",
        "usage_requests",
        ["key_alias", "started_at"],
    )
    # Composite for provider + model queries
    op.create_index(
        "ix_usage_requests_provider_resolved_model",
        "usage_requests",
        ["provider", "resolved_model"],
    )
    # Composite for session + time queries
    op.create_index(
        "ix_usage_requests_session_started_at",
        "usage_requests",
        ["benchmark_session_id", "started_at"],
    )


def downgrade() -> None:
    """Drop usage_requests table and indexes."""
    op.drop_index("ix_usage_requests_session_started_at", table_name="usage_requests")
    op.drop_index("ix_usage_requests_provider_resolved_model", table_name="usage_requests")
    op.drop_index("ix_usage_requests_key_alias_started_at", table_name="usage_requests")
    op.drop_index("ix_usage_requests_error_code", table_name="usage_requests")
    op.drop_index("ix_usage_requests_status", table_name="usage_requests")
    op.drop_index("ix_usage_requests_provider", table_name="usage_requests")
    op.drop_index("ix_usage_requests_resolved_model", table_name="usage_requests")
    op.drop_index("ix_usage_requests_benchmark_session_id", table_name="usage_requests")
    op.drop_index("ix_usage_requests_proxy_key_id", table_name="usage_requests")
    op.drop_index("ix_usage_requests_litellm_key_id", table_name="usage_requests")
    op.drop_index("ix_usage_requests_key_alias", table_name="usage_requests")
    op.drop_index("ix_usage_requests_started_at", table_name="usage_requests")
    op.drop_table("usage_requests")
