"""Deterministic, non-causal explanation language for analyst-facing responses."""

from __future__ import annotations

from typing import Any


def explanation_narrative(
    response: dict[str, Any],
    *,
    anomaly: dict[str, Any] | None = None,
) -> list[str]:
    """Render neutral statements from computed scores and attribution records."""
    probability = float(response["fraud_probability"])
    threshold = float(response["decision_threshold"])
    if int(response["predicted_class"]) == 1:
        summary = (
            f"The estimated fraud-risk probability is {probability:.4%}, above the stored "
            f"{threshold:.4%} review threshold; the transaction is flagged for analyst review."
        )
    else:
        summary = (
            f"The estimated fraud-risk probability is {probability:.4%}, below the stored "
            f"{threshold:.4%} review threshold; the transaction is not flagged by this policy."
        )

    explanation = response.get("explanation") or {}
    positive = explanation.get("top_positive_features", [])
    negative = explanation.get("top_negative_features", [])
    messages = [summary]
    if positive:
        names = ", ".join(item["feature"] for item in positive[:3])
        messages.append(
            f"The strongest positive raw-score contributions are from anonymized model "
            f"features {names}."
        )
    if negative:
        names = ", ".join(item["feature"] for item in negative[:3])
        messages.append(
            f"The strongest negative raw-score contributions are from anonymized model "
            f"features {names}."
        )
    messages.append(
        "These contributions describe the fitted model's statistical behavior; they do not "
        "establish a cause or prove fraud."
    )
    if anomaly is not None:
        category = str(anomaly.get("anomaly_category", anomaly.get("category", "unclassified")))
        percentile = float(anomaly.get("anomaly_percentile", anomaly.get("percentile", 0.0)))
        messages.append(
            f"The separate Isolation Forest ranks this observation at approximately the "
            f"{percentile:.1%} anomaly percentile ({category}); this is not a fraud probability."
        )
    return messages
