"""Trusted-local model artifact persistence with checksums and version checks."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import sklearn
from sklearn.base import ClassifierMixin
from sklearn.linear_model import LogisticRegression

from fraud_detection.exceptions import ArtifactError
from fraud_detection.ml.anomaly import AnomalyExperiment
from fraud_detection.ml.calibration import apply_sigmoid_calibrator
from fraud_detection.schema import FEATURE_COLUMNS


@dataclass
class ModelBundle:
    """Inference-ready classifier, sigmoid mapping, threshold, and provenance."""

    estimator: ClassifierMixin
    calibrator: LogisticRegression | None
    threshold: float
    metadata: dict[str, Any]

    def predict_probabilities(self, features):
        """Return raw estimator scores and the persisted sigmoid-mapped values."""
        raw = self.estimator.predict_proba(features.loc[:, list(FEATURE_COLUMNS)])[:, 1]
        if self.calibrator is None:
            return raw, raw
        return raw, apply_sigmoid_calibrator(self.calibrator, raw)


def sha256_file(path: str | Path) -> str:
    """Return a streamed SHA-256 checksum for a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_model_bundle(
    bundle: ModelBundle,
    path: str | Path,
    *,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    """Atomically serialize a model bundle and write its local artifact manifest."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing model artifact: {destination}")
    if tuple(bundle.metadata.get("feature_columns", ())) != FEATURE_COLUMNS:
        raise ArtifactError(
            "Bundle metadata feature schema does not match the current ULB contract"
        )
    if not 0 <= bundle.threshold <= 1:
        raise ArtifactError("Bundle threshold must be in [0, 1]")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
        joblib.dump(bundle, temporary_name, compress=3)
        os.replace(temporary_name, destination)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
    manifest = {
        "artifact_path": str(destination),
        "artifact_type": "supervised_classifier",
        "artifact_sha256": sha256_file(destination),
        "artifact_size_bytes": destination.stat().st_size,
        "artifact_format": "joblib; trusted local files only",
        "model_version": bundle.metadata.get("model_version"),
        "schema_version": bundle.metadata.get("schema_version"),
        "feature_columns": list(FEATURE_COLUMNS),
        "threshold": bundle.threshold,
        "dataset_sha256": bundle.metadata.get("dataset_sha256"),
        "split_manifest_id": bundle.metadata.get("split_manifest_id"),
        "scikit_learn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
    }
    sidecar = Path(manifest_path) if manifest_path else destination.with_suffix(".manifest.json")
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def save_anomaly_artifact(
    experiment: AnomalyExperiment,
    path: str | Path,
    *,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    """Atomically persist the separate Isolation Forest and its score semantics."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing anomaly artifact: {destination}")
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent, delete=False
        ) as temporary:
            temporary_name = temporary.name
        joblib.dump(experiment, temporary_name, compress=3)
        os.replace(temporary_name, destination)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)
    manifest = {
        "artifact_path": str(destination),
        "artifact_type": "anomaly_detector",
        "artifact_sha256": sha256_file(destination),
        "artifact_size_bytes": destination.stat().st_size,
        "artifact_format": "joblib; trusted local files only",
        "model_version": experiment.metadata.get("model_version"),
        "schema_version": experiment.metadata.get("schema_version"),
        "feature_columns": list(FEATURE_COLUMNS),
        "score_direction": "higher = more anomalous",
        "score_is_probability": False,
        "dataset_sha256": experiment.metadata.get("dataset_sha256"),
        "split_manifest_id": experiment.metadata.get("split_manifest_id"),
        "scikit_learn_version": sklearn.__version__,
        "joblib_version": joblib.__version__,
    }
    sidecar = Path(manifest_path) if manifest_path else destination.with_suffix(".manifest.json")
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_artifact_manifest(manifest: dict[str, Any]) -> bool:
    """Check a local artifact's checksum, byte size, and model version metadata."""
    path = Path(manifest["artifact_path"])
    return (
        path.is_file()
        and path.stat().st_size == manifest["artifact_size_bytes"]
        and sha256_file(path) == manifest["artifact_sha256"]
    )


def load_model_bundle(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> ModelBundle:
    """Load a trusted local artifact and reject checksum or library-version mismatch.

    Joblib is based on pickle and can execute code while loading. Only pass paths
    to artifacts generated and verified by this project; never pass user uploads.
    """
    source = Path(path)
    if not source.is_file():
        raise ArtifactError(f"Model artifact does not exist: {source}")
    actual_sha = sha256_file(source)
    if expected_sha256 and actual_sha != expected_sha256:
        raise ArtifactError("Model artifact checksum does not match the trusted manifest")
    try:
        bundle = joblib.load(source)
    except Exception as exc:
        raise ArtifactError(f"Could not load trusted local model artifact: {exc}") from exc
    if not isinstance(bundle, ModelBundle):
        raise ArtifactError("Serialized object is not a fraud detection ModelBundle")
    if bundle.metadata.get("scikit_learn_version") != sklearn.__version__:
        raise ArtifactError(
            "scikit-learn version mismatch: artifact requires "
            f"{bundle.metadata.get('scikit_learn_version')}, "
            f"current runtime is {sklearn.__version__}"
        )
    if tuple(bundle.metadata.get("feature_columns", ())) != FEATURE_COLUMNS:
        raise ArtifactError("Artifact feature schema is incompatible with this runtime")
    if not np_is_probability(bundle.threshold):
        raise ArtifactError("Artifact decision threshold is invalid")
    return bundle


def load_anomaly_artifact(
    path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> AnomalyExperiment:
    """Load a trusted local Isolation Forest artifact with schema/version checks."""
    source = Path(path)
    if not source.is_file():
        raise ArtifactError(f"Anomaly artifact does not exist: {source}")
    if expected_sha256 and sha256_file(source) != expected_sha256:
        raise ArtifactError("Anomaly artifact checksum does not match the trusted manifest")
    try:
        experiment = joblib.load(source)
    except Exception as exc:
        raise ArtifactError(f"Could not load trusted local anomaly artifact: {exc}") from exc
    if not isinstance(experiment, AnomalyExperiment):
        raise ArtifactError("Serialized object is not a fraud detection AnomalyExperiment")
    if experiment.metadata.get("scikit_learn_version") != sklearn.__version__:
        raise ArtifactError("Anomaly artifact scikit-learn version does not match this runtime")
    if tuple(experiment.metadata.get("feature_columns", ())) != FEATURE_COLUMNS:
        raise ArtifactError("Anomaly artifact feature schema is incompatible with this runtime")
    return experiment


def np_is_probability(value: Any) -> bool:
    """Return whether a scalar is a finite numeric value in [0, 1]."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number == number and 0 <= number <= 1 and number not in (float("inf"), float("-inf"))
