"""SHAP LinearExplainer setup and additivity checks for the frozen logistic model."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import shap

from fraud_detection.exceptions import ExplainabilityError
from fraud_detection.explainability.linear import get_logistic_pipeline_parts
from fraud_detection.explainability.validation import validate_shap_additivity
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.schema import FEATURE_COLUMNS


@dataclass(frozen=True)
class ShapExplanationBatch:
    """Aligned interventional SHAP values in the raw decision-function space."""

    values: pd.DataFrame
    base_values: np.ndarray
    decision_function: np.ndarray
    additivity: dict[str, Any]
    background_metadata: dict[str, Any]


def make_training_background(
    training_features: pd.DataFrame,
    *,
    sample_size: int = 512,
    random_state: int = 17,
    dataset_sha256: str,
    split_manifest_id: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Select a deterministic natural-prevalence sample from training features only."""
    ordered = validate_features(training_features)
    if sample_size < 1:
        raise ValueError("SHAP background sample_size must be positive")
    count = min(int(sample_size), len(ordered))
    rng = np.random.default_rng(random_state)
    selected_positions = np.sort(rng.choice(len(ordered), size=count, replace=False))
    background = ordered.iloc[selected_positions].copy()
    digest = hashlib.sha256()
    digest.update(json.dumps(list(FEATURE_COLUMNS), separators=(",", ":")).encode())
    digest.update(background.to_numpy(dtype=np.float64).tobytes(order="C"))
    metadata: dict[str, Any] = {
        "partition": "training",
        "label_filter": "none; natural training prevalence",
        "sample_method": "uniform row sample without replacement",
        "sample_size": int(count),
        "random_state": int(random_state),
        "feature_columns": list(FEATURE_COLUMNS),
        "dataset_sha256": dataset_sha256,
        "split_manifest_id": split_manifest_id,
        "background_sha256": digest.hexdigest(),
        "feature_space": "StandardScaler-transformed model input",
        "output_space": "raw_log_odds",
        "explainer": "SHAP LinearExplainer with Independent interventional masker",
        "shap_version": shap.__version__,
    }
    return background, metadata


def build_linear_explainer(
    bundle: ModelBundle,
    training_background: pd.DataFrame,
    *,
    random_state: int = 17,
) -> tuple[Any, pd.DataFrame]:
    """Create a bounded interventional LinearExplainer in scaled feature space."""
    _, scaler, classifier = get_logistic_pipeline_parts(bundle)
    background = validate_features(training_background)
    transformed = pd.DataFrame(
        scaler.transform(background),
        columns=list(FEATURE_COLUMNS),
        index=background.index,
    )
    masker = shap.maskers.Independent(transformed, max_samples=len(transformed))
    explainer = shap.Explainer(
        classifier,
        masker=masker,
        algorithm="linear",
        feature_names=list(FEATURE_COLUMNS),
        output_names=["raw_log_odds"],
        seed=random_state,
    )
    return explainer, transformed


def explain_with_shap(
    bundle: ModelBundle,
    explainer: Any,
    features: pd.DataFrame,
    *,
    background_metadata: dict[str, Any],
    tolerance: float = 1e-7,
) -> ShapExplanationBatch:
    """Explain rows in raw log-odds and require additive reconstruction."""
    ordered = validate_features(features)
    estimator, scaler, _ = get_logistic_pipeline_parts(bundle)
    transformed = pd.DataFrame(
        scaler.transform(ordered),
        columns=list(FEATURE_COLUMNS),
        index=ordered.index,
    )
    explanation = explainer(transformed)
    values = np.asarray(explanation.values, dtype=np.float64)
    if values.ndim == 3 and values.shape[-1] == 1:
        values = values[..., 0]
    if values.shape != transformed.shape:
        raise ExplainabilityError(
            f"Unexpected SHAP shape {values.shape}; expected {transformed.shape}"
        )
    base_values = np.asarray(explanation.base_values, dtype=np.float64).reshape(-1)
    if base_values.size == 1 and len(ordered) > 1:
        base_values = np.repeat(base_values, len(ordered))
    if base_values.size != len(ordered):
        raise ExplainabilityError(
            f"Unexpected SHAP base-value count {base_values.size}; expected {len(ordered)}"
        )
    decision = np.asarray(estimator.decision_function(ordered), dtype=np.float64).reshape(-1)
    additivity = validate_shap_additivity(
        values,
        base_values,
        decision,
        tolerance=tolerance,
    )
    if not additivity["passed"]:
        raise ExplainabilityError(
            "SHAP values do not reconstruct the raw logistic decision function within tolerance"
        )
    return ShapExplanationBatch(
        values=pd.DataFrame(values, index=ordered.index, columns=list(FEATURE_COLUMNS)),
        base_values=base_values,
        decision_function=decision,
        additivity=additivity,
        background_metadata=dict(background_metadata),
    )
