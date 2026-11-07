"""Load and cross-check only Mission 02/03 artifacts named by tracked manifests."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backend.app.core.config import Settings
from fraud_detection.explainability.local_explanations import ExplainabilityService
from fraud_detection.explainability.shap_engine import build_linear_explainer
from fraud_detection.ml.anomaly import AnomalyExperiment
from fraud_detection.ml.persistence import (
    ModelBundle,
    load_anomaly_artifact,
    load_model_bundle,
    sha256_file,
)
from fraud_detection.risk.anomaly_intelligence import (
    AnomalyScoreReference,
    load_anomaly_reference,
)
from fraud_detection.risk.scoring import RiskScoringService
from fraud_detection.risk.service import RiskIntelligenceService
from fraud_detection.risk.tiers import RiskTierPolicy
from fraud_detection.schema import FEATURE_COLUMNS, SCHEMA_VERSION


class ArtifactConfigurationError(RuntimeError):
    """Trusted local model or report artifacts do not form a consistent release."""


@dataclass
class RuntimeServices:
    """Loaded inference services and verified, precomputed global explainability data."""

    bundle: ModelBundle
    anomaly_experiment: AnomalyExperiment
    anomaly_reference: AnomalyScoreReference
    policy: RiskTierPolicy
    scoring: RiskScoringService
    explainability: ExplainabilityService
    intelligence: RiskIntelligenceService
    global_summary: list[dict[str, Any]]
    artifact_metadata: dict[str, Any]
    shap_metadata: dict[str, Any]

    @property
    def current_model(self) -> dict[str, Any]:
        """Expose immutable version and decision metadata without local paths."""
        return {
            "model_version": self.bundle.metadata["model_version"],
            "model_family": self.bundle.metadata.get(
                "model_family", "balanced_logistic_regression"
            ),
            "schema_version": self.bundle.metadata["schema_version"],
            "feature_count": len(FEATURE_COLUMNS),
            "feature_columns": list(FEATURE_COLUMNS),
            "threshold": float(self.bundle.threshold),
            "probability_calibration_status": self.bundle.metadata.get(
                "probability_calibration_status", "uncalibrated estimator output"
            ),
            "risk_policy_version": self.policy.policy_version,
            "anomaly_model_version": self.anomaly_experiment.metadata["model_version"],
            "anomaly_score_direction": "higher = more anomalous",
            "anomaly_score_is_probability": False,
        }

    @property
    def capabilities(self) -> dict[str, Any]:
        """Expose the available local operations and their output semantics."""
        return {
            "schema_version": SCHEMA_VERSION,
            "feature_count": len(FEATURE_COLUMNS),
            "target_column_accepted": False,
            "max_batch_rows": 1_000,
            "max_explanation_batch": self.intelligence.max_explanation_batch,
            "explanation_methods": [
                "linear_log_odds",
                "shap_interventional_log_odds",
            ],
            "explanation_output_space": "raw_log_odds",
            "calibrated_probability_additivity_claim": False,
            "anomaly_available": True,
            "anomaly_score_direction": "higher = more anomalous",
            "anomaly_score_is_probability": False,
            "global_explanation_available": True,
            "analysis_mode": "synchronous; bounded rows and chunked processing",
            "authentication": "none; trusted local single-user boundary only",
        }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactConfigurationError(
            "A required trusted artifact manifest is unreadable"
        ) from exc
    if not isinstance(value, dict):
        raise ArtifactConfigurationError("A trusted artifact manifest must contain a JSON object")
    return value


def _trusted_path(root: Path, manifest_path: Path, stored_path: str) -> Path:
    candidate = Path(stored_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        root_relative = (root / candidate).resolve()
        manifest_relative = (manifest_path.parent / candidate).resolve()
        resolved = root_relative if root_relative.exists() else manifest_relative
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ArtifactConfigurationError(
            "A trusted artifact path points outside the project"
        ) from exc
    return resolved


def _load_feature_background(
    root: Path, mission03: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest_path = root / "reports" / "explainability" / "api_background_manifest.json"
    manifest = _read_json(manifest_path)
    if manifest.get("source_partition") != "training" or manifest.get("feature_columns") != list(
        FEATURE_COLUMNS
    ):
        raise ArtifactConfigurationError("SHAP background provenance or schema is incompatible")
    if manifest.get("dataset_sha256") != mission03.get("dataset_sha256"):
        raise ArtifactConfigurationError("SHAP background does not match the Mission 03 dataset")
    if manifest.get("split_manifest_id") != mission03.get("split_manifest_id"):
        raise ArtifactConfigurationError("SHAP background does not match the frozen data split")
    if manifest.get("background_sha256") != mission03.get("shap", {}).get("background_sha256"):
        raise ArtifactConfigurationError(
            "Persisted SHAP background differs from Mission 03 results"
        )
    artifact_path = _trusted_path(root, manifest_path, str(manifest.get("artifact_path", "")))
    if (
        not artifact_path.is_file()
        or artifact_path.stat().st_size != manifest.get("artifact_size_bytes")
        or sha256_file(artifact_path) != manifest.get("artifact_sha256")
    ):
        raise ArtifactConfigurationError("SHAP background artifact checksum does not match")
    try:
        with np.load(artifact_path, allow_pickle=False) as archive:
            values = np.asarray(archive["features"], dtype=np.float64)
    except Exception as exc:
        raise ArtifactConfigurationError("SHAP background artifact could not be loaded") from exc
    if values.shape != (manifest.get("sample_size"), len(FEATURE_COLUMNS)):
        raise ArtifactConfigurationError("SHAP background shape differs from its manifest")
    if not np.isfinite(values).all():
        raise ArtifactConfigurationError("SHAP background contains non-finite values")
    digest = hashlib.sha256()
    digest.update(json.dumps(list(FEATURE_COLUMNS), separators=(",", ":")).encode())
    digest.update(values.tobytes(order="C"))
    if digest.hexdigest() != manifest.get("background_sha256"):
        raise ArtifactConfigurationError("SHAP background content digest does not match")
    return pd.DataFrame(values, columns=list(FEATURE_COLUMNS)), manifest


def _load_global_summary(
    root: Path,
    mission03: dict[str, Any],
    bundle: ModelBundle,
    classifier_sha256: str,
) -> list[dict[str, Any]]:
    if mission03.get("model", {}).get("classifier_sha256") != classifier_sha256:
        raise ArtifactConfigurationError("Global SHAP summary references a different classifier")
    report = mission03.get("shap", {})
    if report.get("output_space") != "raw_log_odds":
        raise ArtifactConfigurationError("Global SHAP summary does not use raw log-odds")
    path = root / "reports" / "explainability" / "global_shap_feature_summary.csv"
    if not path.is_file():
        raise ArtifactConfigurationError("Precomputed global SHAP summary is missing")
    frame = pd.read_csv(path)
    required = {"feature", "mean_abs_shap_log_odds", "mean_shap_log_odds"}
    if not required.issubset(frame.columns) or set(frame["feature"].astype(str)) != set(
        FEATURE_COLUMNS
    ):
        raise ArtifactConfigurationError("Global SHAP summary schema differs from the model")
    for column in ("mean_abs_shap_log_odds", "mean_shap_log_odds"):
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=np.float64)
        if not np.isfinite(values).all():
            raise ArtifactConfigurationError("Global SHAP summary contains non-finite values")
    frame = frame.sort_values("mean_abs_shap_log_odds", ascending=False, kind="stable")
    return frame.to_dict(orient="records")


def load_runtime(settings: Settings) -> RuntimeServices:
    """Load checksummed, manifest-pinned model and precomputed explanation artifacts."""
    root = settings.project_root.resolve()
    supervised_manifest_path = root / "reports" / "ml" / "artifact_manifest.json"
    anomaly_manifest_path = root / "reports" / "ml" / "anomaly_artifact_manifest.json"
    reference_manifest_path = root / "reports" / "risk" / "anomaly_reference_manifest.json"
    policy_path = root / "reports" / "risk" / "risk_tier_policy.json"
    mission03_path = root / "reports" / "risk" / "mission03_results.json"
    supervised_manifest = _read_json(supervised_manifest_path)
    anomaly_manifest = _read_json(anomaly_manifest_path)
    mission03 = _read_json(mission03_path)
    artifact_path = _trusted_path(
        root, supervised_manifest_path, str(supervised_manifest.get("artifact_path", ""))
    )
    anomaly_path = _trusted_path(
        root, anomaly_manifest_path, str(anomaly_manifest.get("artifact_path", ""))
    )
    bundle = load_model_bundle(
        artifact_path,
        expected_sha256=str(supervised_manifest.get("artifact_sha256", "")),
    )
    anomaly_experiment = load_anomaly_artifact(
        anomaly_path,
        expected_sha256=str(anomaly_manifest.get("artifact_sha256", "")),
    )
    if bundle.metadata.get("model_version") != supervised_manifest.get("model_version"):
        raise ArtifactConfigurationError("Classifier version differs from its manifest")
    if anomaly_experiment.metadata.get("model_version") != anomaly_manifest.get("model_version"):
        raise ArtifactConfigurationError("Anomaly model version differs from its manifest")
    if bundle.metadata.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactConfigurationError("Classifier schema is incompatible with the API")
    if mission03.get("model", {}).get("classifier_sha256") != supervised_manifest.get(
        "artifact_sha256"
    ):
        raise ArtifactConfigurationError("Mission 03 results refer to another classifier")
    if mission03.get("model", {}).get("anomaly_sha256") != anomaly_manifest.get("artifact_sha256"):
        raise ArtifactConfigurationError("Mission 03 results refer to another anomaly detector")
    if mission03.get("dataset_sha256") != supervised_manifest.get("dataset_sha256"):
        raise ArtifactConfigurationError("Model and Mission 03 dataset provenance differ")
    policy_values = _read_json(policy_path)
    policy = RiskTierPolicy.from_dict(policy_values)
    if not np.isclose(policy.decision_threshold, bundle.threshold, rtol=0, atol=1e-15):
        raise ArtifactConfigurationError("Risk policy threshold differs from the classifier")
    reference = load_anomaly_reference(reference_manifest_path)
    if reference.metadata.get("dataset_sha256") != mission03.get(
        "dataset_sha256"
    ) or reference.metadata.get("model_version") != anomaly_experiment.metadata.get(
        "model_version"
    ):
        raise ArtifactConfigurationError("Anomaly reference provenance does not match the model")
    background, shap_metadata = _load_feature_background(root, mission03)
    explainer, _transformed_background = build_linear_explainer(bundle, background)
    explanation_service = ExplainabilityService(
        bundle,
        shap_explainer=explainer,
        shap_background_metadata=shap_metadata,
        max_batch_size=settings.max_explanation_batch,
    )
    scoring = RiskScoringService(bundle, policy, max_batch_size=settings.max_batch_rows)
    intelligence = RiskIntelligenceService(
        scoring,
        explanation_service=explanation_service,
        anomaly_experiment=anomaly_experiment,
        anomaly_reference=reference,
        max_explanation_batch=settings.max_explanation_batch,
    )
    global_summary = _load_global_summary(
        root,
        mission03,
        bundle,
        str(supervised_manifest["artifact_sha256"]),
    )
    metadata = {
        "classifier_sha256": supervised_manifest["artifact_sha256"],
        "anomaly_sha256": anomaly_manifest["artifact_sha256"],
        "dataset_sha256": supervised_manifest["dataset_sha256"],
        "split_manifest_id": supervised_manifest["split_manifest_id"],
        "global_summary_rows": len(global_summary),
    }
    return RuntimeServices(
        bundle=bundle,
        anomaly_experiment=anomaly_experiment,
        anomaly_reference=reference,
        policy=policy,
        scoring=scoring,
        explainability=explanation_service,
        intelligence=intelligence,
        global_summary=global_summary,
        artifact_metadata=metadata,
        shap_metadata=shap_metadata,
    )
