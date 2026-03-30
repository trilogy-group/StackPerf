"""Add session notes, outcome states, and artifact experiment linking

Revision ID: 520517cac40b
Revises: 03e22a58f3a7
Create Date: 2025-03-26 21:02:52.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "520517cac40b"
down_revision: str | Sequence[str] | None = "03e22a58f3a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### Add session notes and outcome_state ###
    op.add_column("sessions", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("outcome_state", sa.String(length=50), nullable=True))
    op.create_index("ix_sessions_outcome_state", "sessions", ["outcome_state"])

    # ### Add experiment_id to artifacts and make session_id nullable ###
    op.add_column("artifacts", sa.Column("experiment_id", sa.Uuid(), nullable=True))
    op.create_index("ix_artifacts_experiment_id", "artifacts", ["experiment_id"])

    # Make session_id nullable for artifacts
    op.alter_column("artifacts", "session_id", existing_type=sa.Uuid(), nullable=True)

    # Add FK constraint for experiment_id
    op.create_foreign_key(
        "fk_artifacts_experiment_id",
        "artifacts",
        "experiments",
        ["experiment_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop FK constraint
    op.drop_constraint("fk_artifacts_experiment_id", "artifacts", type_="foreignkey")

    # Revert session_id to non-nullable
    op.alter_column("artifacts", "session_id", existing_type=sa.Uuid(), nullable=False)

    # Drop artifact changes
    op.drop_index("ix_artifacts_experiment_id", table_name="artifacts")
    op.drop_column("artifacts", "experiment_id")

    # Drop session changes
    op.drop_index("ix_sessions_outcome_state", table_name="sessions")
    op.drop_column("sessions", "outcome_state")
    op.drop_column("sessions", "notes")
