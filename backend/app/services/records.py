"""Persistence and public serialization helpers for derived API records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.db.models import (
    AnalysisJob,
    Investigation,
    InvestigationEvent,
    InvestigationNote,
    PredictionRecord,
    new_id,
    utcnow,
)


def iso_utc(value: datetime | None) -> str | None:
    """Serialize an aware UTC timestamp consistently, including SQLite values."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def save_prediction(
    session: Session,
    result: dict[str, Any],
    *,
    source: str = "api",
    analysis_id: str | None = None,
    row_number: int | None = None,
) -> PredictionRecord:
    """Persist a prediction without its input vector or client-supplied filename."""
    anomaly = result.get("anomaly") or {}
    record = PredictionRecord(
        id=new_id(),
        source=source,
        analysis_id=analysis_id,
        row_number=row_number,
        model_version=str(result["model_version"]),
        schema_version=str(result["schema_version"]),
        probability_calibration_status=str(result["probability_calibration_status"]),
        risk_policy_version=str(result["risk_policy_version"]),
        fraud_probability=float(result["fraud_probability"]),
        risk_score=float(result["risk_score"]),
        risk_tier=str(result["risk_tier"]),
        predicted_class=int(result["predicted_class"]),
        decision_threshold=float(result["decision_threshold"]),
        decision_status=str(result["decision_status"]),
        anomaly_score=(float(anomaly["score"]) if anomaly else None),
        anomaly_percentile=(float(anomaly["percentile"]) if anomaly else None),
        anomaly_category=(str(anomaly["category"]) if anomaly else None),
    )
    session.add(record)
    return record


def prediction_dict(record: PredictionRecord) -> dict[str, Any]:
    """Return the prediction history fields; input features are never included."""
    return {
        "record_id": record.id,
        "source": record.source,
        "analysis_id": record.analysis_id,
        "row_number": record.row_number,
        "created_at": iso_utc(record.created_at),
        "model_version": record.model_version,
        "schema_version": record.schema_version,
        "probability_calibration_status": record.probability_calibration_status,
        "risk_policy_version": record.risk_policy_version,
        "fraud_probability": record.fraud_probability,
        "risk_score": record.risk_score,
        "risk_tier": record.risk_tier,
        "predicted_class": record.predicted_class,
        "decision_threshold": record.decision_threshold,
        "decision_status": record.decision_status,
        "anomaly": (
            {
                "score": record.anomaly_score,
                "percentile": record.anomaly_percentile,
                "category": record.anomaly_category,
                "score_direction": "higher = more anomalous",
                "score_is_probability": False,
            }
            if record.anomaly_score is not None
            else None
        ),
    }


def analysis_dict(job: AnalysisJob) -> dict[str, Any]:
    """Return durable bounded job state and its aggregate-only summary."""
    return {
        "analysis_id": job.id,
        "upload_id": job.upload_id,
        "status": job.status,
        "requested_rows": job.requested_rows,
        "processed_rows": job.processed_rows,
        "model_version": job.model_version,
        "failure_code": job.failure_code,
        "created_at": iso_utc(job.created_at),
        "started_at": iso_utc(job.started_at),
        "completed_at": iso_utc(job.completed_at),
        "summary": job.summary,
    }


def investigation_dict(item: Investigation, *, include_notes: bool = False) -> dict[str, Any]:
    """Serialize an investigation and optionally its notes and append-only events."""
    result: dict[str, Any] = {
        "investigation_id": item.id,
        "prediction_id": item.prediction_id,
        "title": item.title,
        "reason": item.reason,
        "status": item.status,
        "outcome": item.outcome,
        "outcome_is_analyst_recorded": item.outcome is not None,
        "outcome_is_ground_truth": False,
        "created_at": iso_utc(item.created_at),
        "updated_at": iso_utc(item.updated_at),
    }
    if include_notes:
        result["notes"] = [
            {"note_id": note.id, "body": note.body, "created_at": iso_utc(note.created_at)}
            for note in sorted(item.notes, key=lambda note: note.created_at)
        ]
        result["events"] = [
            {
                "event_id": event.id,
                "event_type": event.event_type,
                "old_value": event.old_value,
                "new_value": event.new_value,
                "created_at": iso_utc(event.created_at),
            }
            for event in sorted(item.events, key=lambda event: event.created_at)
        ]
    return result


def add_investigation_event(
    session: Session,
    investigation_id: str,
    event_type: str,
    old_value: str | None,
    new_value: str | None,
) -> None:
    """Append a small workflow event without inferring analyst identity."""
    session.add(
        InvestigationEvent(
            id=new_id(),
            investigation_id=investigation_id,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
            created_at=utcnow(),
        )
    )


def new_note(session: Session, investigation_id: str, body: str) -> InvestigationNote:
    """Persist one analyst note with a generated identifier and timestamp."""
    note = InvestigationNote(
        id=new_id(), investigation_id=investigation_id, body=body.strip(), created_at=utcnow()
    )
    session.add(note)
    return note
