"""Stable single-transaction and batch inference contracts for later services."""

from __future__ import annotations

from typing import Any

import pandas as pd

from fraud_detection.ml.anomaly import AnomalyExperiment, anomaly_scores
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.ml.preprocessing import validate_features


def predict_batch(bundle: ModelBundle, features: pd.DataFrame) -> pd.DataFrame:
    """Validate a batch and return model scores plus the persisted decision."""
    ordered = validate_features(features)
    raw, probabilities = bundle.predict_probabilities(ordered)
    status = bundle.metadata.get("probability_calibration_status", "uncalibrated estimator output")
    return pd.DataFrame(
        {
            "fraud_probability": probabilities,
            "raw_model_score": raw,
            "predicted_class": (probabilities >= bundle.threshold).astype("int8"),
            "decision_threshold": bundle.threshold,
            "model_version": bundle.metadata["model_version"],
            "probability_calibration_status": status,
        },
        index=features.index,
    )


def predict_one(bundle: ModelBundle, features: dict[str, Any] | pd.DataFrame) -> dict[str, Any]:
    """Return one validated inference response without the target field."""
    ordered = validate_features(features)
    if len(ordered) != 1:
        raise ValueError("predict_one requires exactly one transaction")
    return predict_batch(bundle, ordered).iloc[0].to_dict()


def predict_anomaly_batch(
    experiment: AnomalyExperiment,
    features: pd.DataFrame,
) -> pd.DataFrame:
    """Return separate anomaly scores; larger values mean more unusual."""
    ordered = validate_features(features)
    return pd.DataFrame(
        {
            "anomaly_score": anomaly_scores(experiment, ordered),
            "score_direction": "higher = more anomalous",
            "score_is_probability": False,
            "model_version": experiment.metadata.get("model_version", "unversioned-anomaly-model"),
        },
        index=features.index,
    )
