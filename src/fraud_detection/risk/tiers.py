"""Configurable, ordered risk tiers anchored to the frozen model threshold."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RiskTierPolicy:
    """Versioned score boundaries; tiers are operational categories, not labels."""

    policy_version: str
    low_upper_exclusive: float
    decision_threshold: float
    critical_lower_inclusive: float
    validation_quantile_low: float
    validation_quantile_critical: float
    validation_rows: int
    validation_flagged_rows: int
    source_partition: str = "validation"
    policy_semantics: str = "operational triage; not independently calibrated"

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe policy metadata."""
        return asdict(self)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> RiskTierPolicy:
        """Reconstruct a policy from its persisted JSON metadata."""
        return cls(**values)


def fit_risk_tier_policy(
    validation_probabilities: np.ndarray | list[float],
    *,
    decision_threshold: float,
    low_quantile: float = 0.95,
    critical_quantile: float = 0.75,
    policy_version: str = "risk-tier-policy-v1",
) -> RiskTierPolicy:
    """Derive descriptive tier cutpoints from validation scores, never labels.

    The Low/Elevated boundary is the validation 95th percentile, capped at the
    frozen decision threshold. The High/Critical boundary is the 75th percentile
    among validation scores at or above that threshold, and is never below it.
    """
    scores = np.asarray(validation_probabilities, dtype=np.float64)
    threshold = float(decision_threshold)
    if scores.ndim != 1 or not len(scores) or not np.isfinite(scores).all():
        raise ValueError("validation probabilities must be a nonempty finite vector")
    if np.any((scores < 0) | (scores > 1)):
        raise ValueError("validation probabilities must be in [0, 1]")
    if not 0 <= threshold <= 1:
        raise ValueError("decision_threshold must be in [0, 1]")
    if not 0 < low_quantile < 1 or not 0 < critical_quantile < 1:
        raise ValueError("risk-tier quantiles must be strictly between 0 and 1")

    low_boundary = min(float(np.quantile(scores, low_quantile)), threshold)
    flagged = scores[scores >= threshold]
    critical_boundary = (
        max(threshold, float(np.quantile(flagged, critical_quantile)))
        if len(flagged)
        else threshold
    )
    if not 0 <= low_boundary <= threshold <= critical_boundary <= 1:
        raise ValueError("Derived risk-tier boundaries are not ordered in [0, 1]")
    return RiskTierPolicy(
        policy_version=policy_version,
        low_upper_exclusive=low_boundary,
        decision_threshold=threshold,
        critical_lower_inclusive=critical_boundary,
        validation_quantile_low=float(low_quantile),
        validation_quantile_critical=float(critical_quantile),
        validation_rows=int(len(scores)),
        validation_flagged_rows=int(len(flagged)),
    )


def validate_risk_tier_policy(policy: RiskTierPolicy) -> None:
    """Require full-range, nonoverlapping ordered boundaries."""
    values = (
        policy.low_upper_exclusive,
        policy.decision_threshold,
        policy.critical_lower_inclusive,
    )
    if not all(np.isfinite(values)) or not (0 <= values[0] <= values[1] <= values[2] <= 1):
        raise ValueError(
            "Risk-tier policy boundaries must satisfy 0 <= low <= threshold <= critical <= 1"
        )
    if policy.source_partition != "validation":
        raise ValueError("Risk-tier boundaries must be derived from validation scores")


def assign_risk_tiers(
    probabilities: np.ndarray | list[float],
    policy: RiskTierPolicy,
) -> np.ndarray:
    """Assign mutually exclusive Low, Elevated, High, or Critical tiers."""
    validate_risk_tier_policy(policy)
    values = np.asarray(probabilities, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("probabilities must be finite values in [0, 1]")
    tiers = np.full(len(values), "Critical", dtype=object)
    tiers[values < policy.critical_lower_inclusive] = "High"
    tiers[values < policy.decision_threshold] = "Elevated"
    tiers[values < policy.low_upper_exclusive] = "Low"
    return tiers


def evaluate_risk_tiers(
    probabilities: np.ndarray | list[float],
    labels: np.ndarray | list[int],
    policy: RiskTierPolicy,
) -> list[dict[str, Any]]:
    """Report validation-only tier counts, fraud prevalence, and alert metrics."""
    scores = np.asarray(probabilities, dtype=np.float64)
    truth = np.asarray(labels, dtype=np.int8)
    if scores.ndim != 1 or truth.ndim != 1 or len(scores) != len(truth):
        raise ValueError("validation probabilities and labels must be aligned vectors")
    if not np.isin(truth, [0, 1]).all():
        raise ValueError("validation labels must be binary")
    tiers = assign_risk_tiers(scores, policy)
    predicted = scores >= policy.decision_threshold
    total_fraud = int(truth.sum())
    summaries = []
    for tier in ("Low", "Elevated", "High", "Critical"):
        mask = tiers == tier
        count = int(mask.sum())
        fraud_count = int(truth[mask].sum())
        alert_count = int(np.sum(predicted & mask))
        true_alerts = int(np.sum(predicted & mask & (truth == 1)))
        false_alerts = alert_count - true_alerts
        summaries.append(
            {
                "tier": tier,
                "rows": count,
                "fraud_labels": fraud_count,
                "fraud_prevalence": float(fraud_count / count) if count else None,
                "predicted_alerts": alert_count,
                "true_alerts": true_alerts,
                "false_alerts": false_alerts,
                "precision_among_alerts": (
                    float(true_alerts / alert_count) if alert_count else None
                ),
                "recall_of_all_fraud": (float(fraud_count / total_fraud) if total_fraud else None),
            }
        )
    return summaries
