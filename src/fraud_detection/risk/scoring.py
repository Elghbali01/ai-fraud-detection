"""Calibrated probability presentation and validation-derived risk tiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from fraud_detection.ml.inference import predict_batch
from fraud_detection.ml.persistence import ModelBundle
from fraud_detection.ml.preprocessing import validate_features
from fraud_detection.risk.tiers import RiskTierPolicy, assign_risk_tiers


def probability_to_risk_score(probabilities: np.ndarray | list[float]) -> np.ndarray:
    """Map calibrated probabilities to a 0–100 display score without refitting."""
    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("fraud probabilities must be finite values in [0, 1]")
    return 100.0 * values


@dataclass
class RiskScoringService:
    """Apply the persisted classifier and a versioned validation-derived tier policy."""

    bundle: ModelBundle
    tier_policy: RiskTierPolicy
    max_batch_size: int = 10_000

    def __post_init__(self) -> None:
        """Reject policy/model threshold mismatches at service construction."""
        validation = validate_risk_scoring_metadata(
            self.tier_policy,
            model_threshold=self.bundle.threshold,
        )
        if not validation["threshold_consistent"]:
            raise ValueError("Risk-tier policy threshold differs from frozen model threshold")
        if self.max_batch_size < 1:
            raise ValueError("max_batch_size must be positive")

    def score_batch(
        self,
        features: pd.DataFrame,
        *,
        transaction_ids: list[str | int] | None = None,
    ) -> pd.DataFrame:
        """Score a bounded batch without requiring historical labels."""
        ordered = validate_features(features)
        if len(ordered) > self.max_batch_size:
            raise ValueError(f"Scoring batch exceeds configured limit {self.max_batch_size}")
        if transaction_ids is not None and len(transaction_ids) != len(ordered):
            raise ValueError("transaction_ids must align with the feature batch")
        scored = predict_batch(self.bundle, ordered)
        scored["risk_score"] = probability_to_risk_score(
            scored["fraud_probability"].to_numpy(dtype=np.float64)
        )
        scored["risk_tier"] = assign_risk_tiers(
            scored["fraud_probability"].to_numpy(dtype=np.float64),
            self.tier_policy,
        )
        scored["decision_status"] = np.where(
            scored["predicted_class"].to_numpy(dtype=np.int8) == 1,
            "flagged_for_review",
            "not_flagged_by_policy",
        )
        scored["risk_policy_version"] = self.tier_policy.policy_version
        if transaction_ids is not None:
            scored.insert(0, "transaction_id", transaction_ids)
        return scored


def validate_risk_scoring_metadata(
    policy: RiskTierPolicy,
    *,
    model_threshold: float,
) -> dict[str, Any]:
    """Return a small, JSON-safe policy/model consistency summary."""
    return {
        "policy_version": policy.policy_version,
        "decision_threshold": float(model_threshold),
        "policy_decision_threshold": float(policy.decision_threshold),
        "threshold_consistent": bool(
            np.isclose(policy.decision_threshold, model_threshold, rtol=0, atol=1e-15)
        ),
        "risk_score_definition": "100 * calibrated fraud probability",
        "risk_tier_semantics": "configurable analyst triage categories",
    }
