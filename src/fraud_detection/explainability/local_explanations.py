"""Single and bounded-batch local explanations for the persisted fraud bundle."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from fraud_detection.exceptions import ExplainabilityError
from fraud_detection.explainability.linear import LinearAttributionBatch, exact_linear_attributions
from fraud_detection.explainability.shap_engine import ShapExplanationBatch, explain_with_shap
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.schema import FEATURE_COLUMNS

ExplanationMethod = Literal["linear_log_odds", "shap_interventional_log_odds"]


class ExplainabilityService:
    """Reuse one trusted model bundle and optional SHAP explainer across requests."""

    def __init__(
        self,
        bundle: ModelBundle,
        *,
        model_schema_version: str | None = None,
        shap_explainer: Any | None = None,
        shap_background_metadata: dict[str, Any] | None = None,
        max_batch_size: int = 100,
    ) -> None:
        if max_batch_size < 1:
            raise ValueError("max_batch_size must be positive")
        self.bundle = bundle
        self.model_schema_version = model_schema_version or str(
            bundle.metadata.get("schema_version", "unknown")
        )
        self.shap_explainer = shap_explainer
        self.shap_background_metadata = shap_background_metadata or {}
        self.max_batch_size = int(max_batch_size)

    def explain_one(
        self,
        features: pd.DataFrame | dict[str, Any],
        *,
        transaction_id: str | int | None = None,
        method: ExplanationMethod = "linear_log_odds",
        top_n: int | None = 10,
    ) -> dict[str, Any]:
        """Explain one validated transaction in raw log-odds space."""
        ordered = validate_features(features)
        if len(ordered) != 1:
            raise ValueError("explain_one requires exactly one transaction")
        ids = [transaction_id] if transaction_id is not None else None
        return self.explain_batch(ordered, transaction_ids=ids, method=method, top_n=top_n)[0]

    def explain_batch(
        self,
        features: pd.DataFrame,
        *,
        transaction_ids: list[str | int] | None = None,
        method: ExplanationMethod = "linear_log_odds",
        top_n: int | None = 10,
    ) -> list[dict[str, Any]]:
        """Explain a small batch with shared model transforms and one SHAP call."""
        ordered = validate_features(features)
        if len(ordered) > self.max_batch_size:
            raise ValueError(
                f"Detailed explanation batch exceeds configured limit {self.max_batch_size}"
            )
        if top_n is not None and top_n < 1:
            raise ValueError("top_n must be positive or None for the full explanation")
        if transaction_ids is not None and len(transaction_ids) != len(ordered):
            raise ValueError("transaction_ids must align with the explanation batch")
        if method not in ("linear_log_odds", "shap_interventional_log_odds"):
            raise ValueError(f"Unsupported explanation method: {method}")

        linear = exact_linear_attributions(self.bundle, ordered)
        shap_batch = self._shap_batch(ordered) if method == "shap_interventional_log_odds" else None
        return [
            self._row_response(
                linear,
                shap_batch,
                row_position=position,
                transaction_id=transaction_ids[position] if transaction_ids is not None else None,
                method=method,
                top_n=top_n,
            )
            for position in range(len(ordered))
        ]

    def _shap_batch(self, features: pd.DataFrame) -> ShapExplanationBatch:
        if self.shap_explainer is None:
            raise ExplainabilityError("A training-background SHAP explainer was not configured")
        return explain_with_shap(
            self.bundle,
            self.shap_explainer,
            features,
            background_metadata=self.shap_background_metadata,
        )

    def _row_response(
        self,
        linear: LinearAttributionBatch,
        shap_batch: ShapExplanationBatch | None,
        *,
        row_position: int,
        transaction_id: str | int | None,
        method: ExplanationMethod,
        top_n: int | None,
    ) -> dict[str, Any]:
        if method == "linear_log_odds":
            contribution_values = linear.contributions.iloc[row_position].to_numpy(dtype=float)
            base_value = linear.intercept
            reconstruction_error = float(linear.reconstruction_error[row_position])
            baseline_semantics = (
                "Logistic intercept at zero transformed feature values; not a population average."
            )
        else:
            if shap_batch is None:
                raise ExplainabilityError("SHAP output was not computed")
            contribution_values = shap_batch.values.iloc[row_position].to_numpy(dtype=float)
            base_value = float(shap_batch.base_values[row_position])
            reconstruction_error = float(
                abs(
                    base_value
                    + contribution_values.sum()
                    - shap_batch.decision_function[row_position]
                )
            )
            baseline_semantics = (
                "Expected raw model log-odds over the deterministic training-only SHAP background."
            )

        transformed_values = linear.transformed_features.iloc[row_position].to_numpy(dtype=float)
        coefficient_values = linear.coefficients.to_numpy(dtype=float)
        details = []
        for feature_index, feature in enumerate(FEATURE_COLUMNS):
            contribution = float(contribution_values[feature_index])
            direction = (
                "increases_raw_log_odds"
                if contribution > 1e-12
                else "decreases_raw_log_odds"
                if contribution < -1e-12
                else "negligible"
            )
            details.append(
                {
                    "feature": feature,
                    "transformed_feature_value": float(transformed_values[feature_index]),
                    "coefficient": float(coefficient_values[feature_index]),
                    "contribution": contribution,
                    "direction": direction,
                }
            )
        ranked = sorted(details, key=lambda item: (-abs(item["contribution"]), item["feature"]))
        limit = len(ranked) if top_n is None else min(top_n, len(ranked))
        positive = sorted(
            (item for item in details if item["contribution"] > 1e-12),
            key=lambda item: (-item["contribution"], item["feature"]),
        )
        negative = sorted(
            (item for item in details if item["contribution"] < -1e-12),
            key=lambda item: (item["contribution"], item["feature"]),
        )
        result = {
            "contract_version": "mission03-intelligence-v1",
            "model_version": str(self.bundle.metadata["model_version"]),
            "schema_version": self.model_schema_version,
            "transaction_id": transaction_id,
            "fraud_probability": float(linear.calibrated_probability[row_position]),
            "raw_estimator_probability": float(linear.raw_estimator_probability[row_position]),
            "raw_decision_score": float(linear.decision_function[row_position]),
            "risk_score": float(100 * linear.calibrated_probability[row_position]),
            "decision_threshold": float(linear.threshold),
            "predicted_class": int(linear.predicted_class[row_position]),
            "decision_status": (
                "flagged_for_review"
                if linear.predicted_class[row_position] == 1
                else "not_flagged_by_policy"
            ),
            "probability_calibration_status": str(
                self.bundle.metadata.get("probability_calibration_status", "uncalibrated")
            ),
            "explanation": {
                "method": method,
                "output_space": "raw_log_odds",
                "base_value": float(base_value),
                "linear_intercept": float(linear.intercept),
                "baseline_semantics": baseline_semantics,
                "feature_contributions": ranked[:limit],
                "top_positive_features": positive[:limit],
                "top_negative_features": negative[:limit],
                "feature_count": len(FEATURE_COLUMNS),
                "all_contributions_returned": top_n is None or top_n >= len(FEATURE_COLUMNS),
                "reconstruction_error": reconstruction_error,
                "sigmoid_probability_error": float(linear.sigmoid_probability_error[row_position]),
                "calibrated_probability_additivity_claim": False,
                "background": (
                    dict(self.shap_background_metadata)
                    if method == "shap_interventional_log_odds"
                    else None
                ),
            },
        }
        return result
