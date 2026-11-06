"""Exact raw-log-odds contributions for the persisted scaled logistic pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from fraud_detection.exceptions import ArtifactError
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.schema import FEATURE_COLUMNS


@dataclass(frozen=True)
class LinearAttributionBatch:
    """Aligned transformed values, raw linear contributions, scores, and checks."""

    transformed_features: pd.DataFrame
    contributions: pd.DataFrame
    coefficients: pd.Series
    intercept: float
    decision_function: np.ndarray
    raw_estimator_probability: np.ndarray
    calibrated_probability: np.ndarray
    predicted_class: np.ndarray
    threshold: float
    reconstruction_error: np.ndarray
    sigmoid_probability_error: np.ndarray


def get_logistic_pipeline_parts(
    bundle: ModelBundle,
) -> tuple[Pipeline, StandardScaler, LogisticRegression]:
    """Return and validate the fitted scaler and binary Logistic Regression."""
    estimator = bundle.estimator
    if not isinstance(estimator, Pipeline):
        raise ArtifactError("Explainability requires the persisted fitted sklearn Pipeline")
    steps = dict(estimator.named_steps)
    scaler = steps.get("scaler")
    classifier = steps.get("classifier")
    if not isinstance(scaler, StandardScaler) or not isinstance(classifier, LogisticRegression):
        raise ArtifactError("Expected the Mission 02 StandardScaler/LogisticRegression pipeline")
    if classifier.coef_.shape != (1, len(FEATURE_COLUMNS)):
        raise ArtifactError(
            "The persisted classifier does not have the expected binary feature shape"
        )
    if tuple(getattr(scaler, "feature_names_in_", FEATURE_COLUMNS)) != FEATURE_COLUMNS:
        raise ArtifactError("Scaler feature order differs from the versioned ULB schema")
    return estimator, scaler, classifier


def exact_linear_attributions(
    bundle: ModelBundle,
    features: pd.DataFrame | dict[str, Any],
    *,
    tolerance: float = 1e-10,
) -> LinearAttributionBatch:
    """Compute transformed-space coefficient contributions and verify reconstruction."""
    ordered = validate_features(features)
    estimator, scaler, classifier = get_logistic_pipeline_parts(bundle)
    transformed_array = np.asarray(scaler.transform(ordered), dtype=np.float64)
    transformed = pd.DataFrame(
        transformed_array,
        columns=list(FEATURE_COLUMNS),
        index=ordered.index,
    )
    coefficients = np.asarray(classifier.coef_[0], dtype=np.float64)
    contributions_array = transformed_array * coefficients.reshape(1, -1)
    contributions = pd.DataFrame(
        contributions_array,
        columns=list(FEATURE_COLUMNS),
        index=ordered.index,
    )
    intercept = float(classifier.intercept_[0])
    reconstructed = intercept + contributions_array.sum(axis=1)
    decision = np.asarray(estimator.decision_function(ordered), dtype=np.float64).reshape(-1)
    reconstruction_error = np.abs(reconstructed - decision)
    if not np.allclose(reconstructed, decision, rtol=tolerance, atol=tolerance):
        raise ArtifactError("Linear contributions do not reconstruct the raw decision function")

    raw_probability = np.asarray(estimator.predict_proba(ordered)[:, 1], dtype=np.float64)
    sigmoid_error = np.abs(expit(decision) - raw_probability)
    if not np.allclose(expit(decision), raw_probability, rtol=tolerance, atol=tolerance):
        raise ArtifactError(
            "Sigmoid of the decision function differs from raw estimator probability"
        )

    _, calibrated_probability = bundle.predict_probabilities(ordered)
    calibrated = np.asarray(calibrated_probability, dtype=np.float64)
    predicted_class = (calibrated >= bundle.threshold).astype(np.int8)
    return LinearAttributionBatch(
        transformed_features=transformed,
        contributions=contributions,
        coefficients=pd.Series(coefficients, index=FEATURE_COLUMNS, name="coefficient"),
        intercept=intercept,
        decision_function=decision,
        raw_estimator_probability=raw_probability,
        calibrated_probability=calibrated,
        predicted_class=predicted_class,
        threshold=float(bundle.threshold),
        reconstruction_error=reconstruction_error,
        sigmoid_probability_error=sigmoid_error,
    )
