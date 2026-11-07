"""Persist calibration and risk-policy versions with derived predictions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_prediction_semantics"
down_revision = "0001_initial_api_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add immutable output-semantics fields to history rows."""
    op.add_column(
        "predictions",
        sa.Column(
            "probability_calibration_status",
            sa.String(length=512),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "predictions",
        sa.Column(
            "risk_policy_version", sa.String(length=64), nullable=False, server_default="unknown"
        ),
    )


def downgrade() -> None:
    """Refuse to erase persisted semantics from historical prediction rows."""
    raise RuntimeError("Mission 04 data-bearing schema downgrade is intentionally not implemented")
