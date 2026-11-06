"""Combined transaction intelligence without merging fraud and anomaly scores."""

from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from fraud_detection.explainability.local_explanations import ExplainabilityService
from fraud_detection.explainability.narratives import explanation_narrative
from fraud_detection.ml.anomaly import AnomalyExperiment, anomaly_scores
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.risk.anomaly_intelligence import (
    AnomalyScoreReference,
    anomaly_categories,
    anomaly_percentiles,
)
from fraud_detection.risk.contracts import CONTRACT_VERSION, IntelligenceRecord
from fraud_detection.risk.scoring import RiskScoringService


class RiskIntelligenceService:
    """Reuse trusted artifacts for single or bounded-batch analyst intelligence."""

    def __init__(
        self,
        scoring_service: RiskScoringService,
        *,
        explanation_service: ExplainabilityService | None = None,
        anomaly_experiment: AnomalyExperiment | None = None,
        anomaly_reference: AnomalyScoreReference | None = None,
        max_explanation_batch: int = 100,
    ) -> None:
        if (anomaly_experiment is None) != (anomaly_reference is None):
            raise ValueError(
                "Anomaly experiment and training reference must be configured together"
            )
        if max_explanation_batch < 1:
            raise ValueError("max_explanation_batch must be positive")
        self.scoring_service = scoring_service
        self.bundle: ModelBundle = scoring_service.bundle
        self.explanation_service = explanation_service or ExplainabilityService(self.bundle)
        self.anomaly_experiment = anomaly_experiment
        self.anomaly_reference = anomaly_reference
        self.max_explanation_batch = int(max_explanation_batch)

    def score_batch(
        self,
        features: pd.DataFrame,
        *,
        transaction_ids: list[str | int] | None = None,
    ) -> pd.DataFrame:
        """Return calibrated risk and optional separate anomaly intelligence."""
        ordered = validate_features(features)
        scored = self.scoring_service.score_batch(
            ordered,
            transaction_ids=transaction_ids,
        )
        if self.anomaly_experiment is not None and self.anomaly_reference is not None:
            scores = anomaly_scores(self.anomaly_experiment, ordered)
            percentiles = anomaly_percentiles(scores, self.anomaly_reference)
            scored["anomaly_score"] = scores
            scored["anomaly_percentile"] = percentiles
            scored["anomaly_category"] = anomaly_categories(percentiles)
            scored["anomaly_score_direction"] = "higher = more anomalous"
            scored["anomaly_score_is_probability"] = False
            scored["anomaly_model_version"] = str(
                self.anomaly_experiment.metadata.get("model_version", "unversioned-anomaly")
            )
        return scored

    def intelligence_one(
        self,
        features: pd.DataFrame | dict[str, Any],
        *,
        transaction_id: str | int | None = None,
        include_explanation: bool = True,
        explanation_method: Literal[
            "linear_log_odds", "shap_interventional_log_odds"
        ] = "linear_log_odds",
        top_n: int | None = 10,
    ) -> dict[str, Any]:
        """Return a typed, JSON-ready intelligence record for one transaction."""
        ordered = validate_features(features)
        if len(ordered) != 1:
            raise ValueError("intelligence_one requires exactly one transaction")
        ids = [transaction_id] if transaction_id is not None else None
        scored = self.score_batch(ordered, transaction_ids=ids).iloc[0]
        explanation = None
        if include_explanation:
            if self.explanation_service is None:
                raise ValueError("Detailed explanation service is not configured")
            explanation = self.explanation_service.explain_one(
                ordered,
                transaction_id=transaction_id,
                method=explanation_method,
                top_n=top_n,
            )["explanation"]
        anomaly = self._anomaly_record(scored)
        base = {
            "contract_version": CONTRACT_VERSION,
            "model_version": str(self.bundle.metadata["model_version"]),
            "schema_version": str(self.bundle.metadata["schema_version"]),
            "transaction_id": transaction_id,
            "fraud_probability": float(scored["fraud_probability"]),
            "risk_score": float(scored["risk_score"]),
            "risk_tier": str(scored["risk_tier"]),
            "predicted_class": int(scored["predicted_class"]),
            "decision_threshold": float(scored["decision_threshold"]),
            "decision_status": str(scored["decision_status"]),
            "anomaly": anomaly,
            "explanation": explanation,
        }
        narrative_source = {**base, "explanation": explanation}
        narrative = tuple(explanation_narrative(narrative_source, anomaly=anomaly))
        return IntelligenceRecord(**base, narrative=narrative).to_dict()

    def intelligence_batch(
        self,
        features: pd.DataFrame,
        *,
        transaction_ids: list[str | int] | None = None,
        include_explanations: bool = False,
        explanation_method: Literal[
            "linear_log_odds", "shap_interventional_log_odds"
        ] = "linear_log_odds",
        top_n: int | None = 10,
    ) -> list[dict[str, Any]]:
        """Score a bounded batch; detailed explanations are separately bounded."""
        ordered = validate_features(features)
        if transaction_ids is not None and len(transaction_ids) != len(ordered):
            raise ValueError("transaction_ids must align with the feature batch")
        scored = self.score_batch(ordered, transaction_ids=transaction_ids)
        explanations: list[dict[str, Any] | None] = [None] * len(ordered)
        if include_explanations:
            if len(ordered) > self.max_explanation_batch:
                raise ValueError(
                    f"Detailed explanation batch exceeds limit {self.max_explanation_batch}"
                )
            if self.explanation_service is None:
                raise ValueError("Detailed explanation service is not configured")
            explanations = self.explanation_service.explain_batch(
                ordered,
                transaction_ids=transaction_ids,
                method=explanation_method,
                top_n=top_n,
            )
            explanations = [result["explanation"] for result in explanations]

        output = []
        for position, (_, row) in enumerate(scored.iterrows()):
            transaction_id = transaction_ids[position] if transaction_ids is not None else None
            anomaly = self._anomaly_record(row)
            record = {
                "contract_version": CONTRACT_VERSION,
                "model_version": str(self.bundle.metadata["model_version"]),
                "schema_version": str(self.bundle.metadata["schema_version"]),
                "transaction_id": transaction_id,
                "fraud_probability": float(row["fraud_probability"]),
                "risk_score": float(row["risk_score"]),
                "risk_tier": str(row["risk_tier"]),
                "predicted_class": int(row["predicted_class"]),
                "decision_threshold": float(row["decision_threshold"]),
                "decision_status": str(row["decision_status"]),
                "anomaly": anomaly,
                "explanation": explanations[position],
            }
            record["narrative"] = explanation_narrative(
                record,
                anomaly=anomaly,
            )
            output.append(record)
        return output

    @staticmethod
    def _anomaly_record(row: pd.Series) -> dict[str, Any] | None:
        if "anomaly_score" not in row.index:
            return None
        return {
            "score": float(row["anomaly_score"]),
            "percentile": float(row["anomaly_percentile"]),
            "category": str(row["anomaly_category"]),
            "score_direction": str(row["anomaly_score_direction"]),
            "score_is_probability": False,
            "model_version": str(row["anomaly_model_version"]),
        }
