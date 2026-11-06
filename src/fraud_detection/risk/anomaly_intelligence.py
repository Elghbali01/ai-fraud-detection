"""Training-reference percentiles and categories for the separate Isolation Forest score."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fraud_detection.exceptions import ArtifactError
from fraud_detection.ml.anomaly import AnomalyExperiment, anomaly_scores
from fraud_detection.ml.persistence import sha256_file
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.schema import FEATURE_COLUMNS, TARGET_COLUMN


@dataclass(frozen=True)
class AnomalyScoreReference:
    """Sorted training-known-legitimate anomaly scores and provenance metadata."""

    sorted_scores: np.ndarray
    metadata: dict[str, Any]


def build_training_anomaly_reference(
    experiment: AnomalyExperiment,
    training_frame: pd.DataFrame,
    *,
    dataset_sha256: str,
    split_manifest_id: str,
) -> AnomalyScoreReference:
    """Score the known-legitimate training rows to define a local reference CDF."""
    if TARGET_COLUMN not in training_frame:
        raise ValueError("Training target is required to select known-legitimate reference rows")
    legitimate = training_frame.loc[training_frame[TARGET_COLUMN].eq(0), list(FEATURE_COLUMNS)]
    if len(legitimate) < 2:
        raise ValueError("At least two legitimate training rows are required for a reference")
    values = np.asarray(anomaly_scores(experiment, validate_features(legitimate)), dtype=np.float64)
    if not np.isfinite(values).all():
        raise ArtifactError("Isolation Forest produced non-finite training reference scores")
    sorted_values = np.sort(values)
    metadata: dict[str, Any] = {
        "reference_version": "anomaly-reference-v1",
        "source_partition": "training",
        "label_filter": "Class == 0 known-legitimate training rows",
        "reference_rows": int(len(sorted_values)),
        "score_direction": "higher = more anomalous",
        "score_is_probability": False,
        "percentile_method": "empirical midrank among sorted reference scores",
        "category_policy": {
            "typical": "percentile < 0.95",
            "unusual": "0.95 <= percentile < 0.99",
            "highly_unusual": "percentile >= 0.99",
        },
        "score_quantiles": {
            "p50": float(np.quantile(sorted_values, 0.50)),
            "p95": float(np.quantile(sorted_values, 0.95)),
            "p99": float(np.quantile(sorted_values, 0.99)),
        },
        "dataset_sha256": dataset_sha256,
        "split_manifest_id": split_manifest_id,
        "model_version": str(experiment.metadata.get("model_version", "unknown")),
        "scikit_learn_version": experiment.metadata.get("scikit_learn_version"),
    }
    return AnomalyScoreReference(sorted_scores=sorted_values, metadata=metadata)


def anomaly_percentiles(
    scores: np.ndarray | list[float],
    reference: AnomalyScoreReference,
) -> np.ndarray:
    """Return empirical midrank percentiles relative to a training-only reference."""
    values = np.asarray(scores, dtype=np.float64)
    ref = np.asarray(reference.sorted_scores, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("Anomaly scores must be a finite one-dimensional vector")
    if ref.ndim != 1 or not len(ref) or not np.isfinite(ref).all():
        raise ValueError("Anomaly reference must contain finite training scores")
    lower = np.searchsorted(ref, values, side="left")
    upper = np.searchsorted(ref, values, side="right")
    return (lower + 0.5 * (upper - lower)) / len(ref)


def anomaly_categories(percentiles: np.ndarray | list[float]) -> np.ndarray:
    """Assign descriptive anomaly categories, not fraud-risk labels."""
    values = np.asarray(percentiles, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("Anomaly percentiles must be finite values in [0, 1]")
    categories = np.full(len(values), "Typical", dtype=object)
    categories[values >= 0.95] = "Unusual"
    categories[values >= 0.99] = "Highly unusual"
    return categories


def save_anomaly_reference(
    reference: AnomalyScoreReference,
    artifact_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    """Save the compact derived reference locally and a JSON manifest for verification."""
    destination = Path(artifact_path)
    manifest_file = Path(manifest_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.", suffix=".npz", dir=destination.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
        np.savez_compressed(temporary_name, sorted_scores=reference.sorted_scores)
        os.replace(temporary_name, destination)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
    try:
        portable_artifact_path = os.path.relpath(
            destination.resolve(), manifest_file.parent.resolve()
        )
    except ValueError:
        portable_artifact_path = str(destination.resolve())
    manifest = {
        **reference.metadata,
        "artifact_path": portable_artifact_path.replace(os.sep, "/"),
        "artifact_sha256": sha256_file(destination),
        "artifact_size_bytes": destination.stat().st_size,
        "artifact_format": "NumPy compressed archive; sorted anomaly scores only",
    }
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def load_anomaly_reference(manifest_path: str | Path) -> AnomalyScoreReference:
    """Verify and load a project-generated anomaly reference from a trusted local path."""
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    artifact = Path(manifest["artifact_path"])
    if not artifact.is_absolute():
        artifact = (manifest_file.parent / artifact).resolve()
    if (
        not artifact.is_file()
        or artifact.stat().st_size != manifest.get("artifact_size_bytes")
        or sha256_file(artifact) != manifest.get("artifact_sha256")
    ):
        raise ArtifactError("Anomaly reference checksum or byte size does not match its manifest")
    try:
        with np.load(artifact, allow_pickle=False) as archive:
            scores = np.asarray(archive["sorted_scores"], dtype=np.float64)
    except Exception as exc:
        raise ArtifactError(f"Could not load trusted anomaly reference: {exc}") from exc
    if scores.ndim != 1 or not len(scores) or np.any(np.diff(scores) < 0):
        raise ArtifactError("Anomaly reference scores are not a sorted finite vector")
    if not np.isfinite(scores).all() or len(scores) != manifest.get("reference_rows"):
        raise ArtifactError("Anomaly reference scores do not match manifest metadata")
    metadata = {key: value for key, value in manifest.items() if key != "artifact_path"}
    return AnomalyScoreReference(sorted_scores=scores, metadata=metadata)
