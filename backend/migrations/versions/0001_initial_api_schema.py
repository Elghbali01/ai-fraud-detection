"""Create the Mission 04 local API tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial_api_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create uploads, analyses, derived prediction history, and investigations."""
    op.create_table(
        "uploads",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("storage_name", sa.String(length=48), nullable=False, unique=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "upload_id",
            sa.String(length=36),
            sa.ForeignKey("uploads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_rows", sa.Integer(), nullable=False),
        sa.Column("processed_rows", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=160)),
        sa.Column("summary", sa.JSON()),
        sa.Column("failure_code", sa.String(length=48)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending','running','completed','failed')"),
    )
    op.create_index("ix_analyses_upload_id", "analyses", ["upload_id"])
    op.create_table(
        "predictions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column(
            "analysis_id", sa.String(length=36), sa.ForeignKey("analyses.id", ondelete="CASCADE")
        ),
        sa.Column("row_number", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_version", sa.String(length=160), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("fraud_probability", sa.Float(), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_tier", sa.String(length=16), nullable=False),
        sa.Column("predicted_class", sa.Integer(), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("decision_status", sa.String(length=32), nullable=False),
        sa.Column("anomaly_score", sa.Float()),
        sa.Column("anomaly_percentile", sa.Float()),
        sa.Column("anomaly_category", sa.String(length=32)),
        sa.CheckConstraint("predicted_class IN (0,1)"),
    )
    op.create_index("ix_predictions_analysis_id", "predictions", ["analysis_id"])
    op.create_index("ix_predictions_created", "predictions", ["created_at"])
    op.create_index("ix_predictions_tier", "predictions", ["risk_tier"])
    op.create_table(
        "investigations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "prediction_id",
            sa.String(length=36),
            sa.ForeignKey("predictions.id", ondelete="SET NULL"),
        ),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("outcome", sa.String(length=24)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('Open','In Review','Escalated','Closed')"),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN "
            "('Unconfirmed','Legitimate','Confirmed Fraud','Inconclusive')"
        ),
    )
    op.create_index("ix_investigations_prediction_id", "investigations", ["prediction_id"])
    op.create_table(
        "investigation_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "investigation_id",
            sa.String(length=36),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.String(length=4000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_investigation_notes_investigation_id", "investigation_notes", ["investigation_id"]
    )
    op.create_table(
        "investigation_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "investigation_id",
            sa.String(length=36),
            sa.ForeignKey("investigations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("old_value", sa.String(length=32)),
        sa.Column("new_value", sa.String(length=32)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_investigation_events_investigation_id", "investigation_events", ["investigation_id"]
    )


def downgrade() -> None:
    """Refuse an automatic destructive downgrade on analyst and prediction data."""
    raise RuntimeError("Mission 04 data-bearing schema downgrade is intentionally not implemented")
