"""SQLite records for derived scores, uploads, and analyst investigations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def new_id() -> str:
    """Return a UUID suitable for a database primary key."""
    return str(uuid4())


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class Upload(Base):
    """Metadata for a validated CSV stored under a server-generated name."""

    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    storage_name: Mapped[str] = mapped_column(String(48), unique=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    analyses: Mapped[list[AnalysisJob]] = relationship(
        back_populates="upload", passive_deletes=True
    )


class AnalysisJob(Base):
    """Durable state and aggregate results for one synchronous CSV analysis."""

    __tablename__ = "analyses"
    __table_args__ = (CheckConstraint("status IN ('pending','running','completed','failed')"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    requested_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_version: Mapped[str | None] = mapped_column(String(160))
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    failure_code: Mapped[str | None] = mapped_column(String(48))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    upload: Mapped[Upload] = relationship(back_populates="analyses")
    predictions: Mapped[list[PredictionRecord]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class PredictionRecord(Base):
    """Persist only derived model outputs; never persist the input feature vector."""

    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("predicted_class IN (0,1)"),
        Index("ix_predictions_created", "created_at"),
        Index("ix_predictions_tier", "risk_tier"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"), index=True
    )
    row_number: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    model_version: Mapped[str] = mapped_column(String(160), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    probability_calibration_status: Mapped[str] = mapped_column(String(512), nullable=False)
    risk_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    fraud_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    predicted_class: Mapped[int] = mapped_column(Integer, nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    decision_status: Mapped[str] = mapped_column(String(32), nullable=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float)
    anomaly_percentile: Mapped[float | None] = mapped_column(Float)
    anomaly_category: Mapped[str | None] = mapped_column(String(32))
    analysis: Mapped[AnalysisJob | None] = relationship(back_populates="predictions")
    investigations: Mapped[list[Investigation]] = relationship(back_populates="prediction")


class Investigation(Base):
    """Analyst workflow metadata, separate from model predictions and truth labels."""

    __tablename__ = "investigations"
    __table_args__ = (
        CheckConstraint("status IN ('Open','In Review','Escalated','Closed')"),
        CheckConstraint(
            "outcome IS NULL OR outcome IN "
            "('Unconfirmed','Legitimate','Confirmed Fraud','Inconclusive')"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    prediction_id: Mapped[str | None] = mapped_column(
        ForeignKey("predictions.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(String(1_000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="Open")
    outcome: Mapped[str | None] = mapped_column(String(24))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    prediction: Mapped[PredictionRecord | None] = relationship(back_populates="investigations")
    notes: Mapped[list[InvestigationNote]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    events: Mapped[list[InvestigationEvent]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )


class InvestigationNote(Base):
    """Analyst-authored note without identity claims or automated ground-truth status."""

    __tablename__ = "investigation_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(String(4_000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    investigation: Mapped[Investigation] = relationship(back_populates="notes")


class InvestigationEvent(Base):
    """Append-only workflow event record."""

    __tablename__ = "investigation_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(32))
    new_value: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    investigation: Mapped[Investigation] = relationship(back_populates="events")
