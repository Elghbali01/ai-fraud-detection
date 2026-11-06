"""Stable review ranking, alert budgets, and validation-only capacity diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral, Real
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PriorityResult:
    """Paginated ranking rows and the policy used to produce them."""

    rows: pd.DataFrame
    metadata: dict[str, Any]


def _identifier_sort_keys(values: list[Any] | pd.Series) -> pd.Series:
    """Keep numeric identifiers in numeric order and strings in lexical order."""
    series = pd.Series(values, dtype="object")
    numeric = series.map(lambda value: isinstance(value, Real) and not isinstance(value, bool))
    if bool(numeric.all()):
        return pd.to_numeric(series)
    return series.map(lambda value: f"{type(value).__name__}:{value}")


def percentage_budget_to_k(row_count: int, percentage: float) -> int:
    """Convert a percentage budget to K using ceiling and at least one for nonempty data."""
    if row_count < 0:
        raise ValueError("row_count must be nonnegative")
    value = float(percentage)
    if not np.isfinite(value) or not 0 < value <= 100:
        raise ValueError("percentage budget must be finite and in (0, 100]")
    if row_count == 0:
        return 0
    return min(row_count, max(1, int(np.ceil(row_count * value / 100))))


def _ranked(
    records: pd.DataFrame,
    *,
    probability_column: str,
    transaction_id_column: str,
) -> pd.DataFrame:
    if probability_column not in records:
        raise ValueError(f"Missing ranking probability column: {probability_column}")
    probabilities = records[probability_column].to_numpy(dtype=np.float64)
    if not np.isfinite(probabilities).all() or np.any((probabilities < 0) | (probabilities > 1)):
        raise ValueError("Ranking probabilities must be finite values in [0, 1]")
    ranked = records.copy()
    ranked["input_position"] = np.arange(len(ranked), dtype=np.int64)
    if transaction_id_column in ranked:
        if ranked[transaction_id_column].isna().any():
            raise ValueError("transaction identifiers used for tie-breaking cannot be missing")
        ranked["_stable_id_key"] = _identifier_sort_keys(ranked[transaction_id_column]).to_numpy()
        sort_columns = [probability_column, "_stable_id_key", "input_position"]
        ascending = [False, True, True]
    else:
        ranked["_stable_id_key"] = ""
        sort_columns = [probability_column, "input_position"]
        ascending = [False, True]
    ranked = ranked.sort_values(sort_columns, ascending=ascending, kind="mergesort")
    ranked["priority_rank"] = np.arange(1, len(ranked) + 1, dtype=np.int64)
    return ranked.drop(columns="_stable_id_key")


def prioritize_transactions(
    records: pd.DataFrame,
    *,
    top_k: int | None = None,
    budget_percentage: float | None = None,
    min_probability: float | None = None,
    risk_tiers: set[str] | None = None,
    transaction_id_column: str = "transaction_id",
    offset: int = 0,
    page_size: int = 100,
) -> PriorityResult:
    """Rank by calibrated probability with deterministic ties and pagination."""
    if (top_k is None) == (budget_percentage is None):
        raise ValueError("Specify exactly one of top_k or budget_percentage")
    if top_k is not None and (
        isinstance(top_k, bool) or not isinstance(top_k, Integral) or top_k < 0
    ):
        raise ValueError("top_k must be a nonnegative integer")
    if offset < 0 or page_size < 1 or page_size > 1_000:
        raise ValueError("offset must be nonnegative and page_size must be in [1, 1000]")
    if records.empty:
        empty = records.copy()
        if "priority_rank" not in empty:
            empty["priority_rank"] = pd.Series(dtype=np.int64)
        return PriorityResult(
            rows=empty,
            metadata={
                "total_ranked": 0,
                "selected_k": 0,
                "returned_rows": 0,
                "offset": int(offset),
                "page_size": int(page_size),
                "tie_break": "transaction identifier ascending, then stable input order",
            },
        )

    filtered = records.copy()
    if "fraud_probability" not in filtered:
        raise ValueError("Missing ranking probability column: fraud_probability")
    if min_probability is not None:
        minimum = float(min_probability)
        if not np.isfinite(minimum) or not 0 <= minimum <= 1:
            raise ValueError("min_probability must be finite and in [0, 1]")
        filtered = filtered.loc[filtered["fraud_probability"].ge(minimum)].copy()
    if risk_tiers is not None:
        if "risk_tier" not in filtered:
            raise ValueError("risk_tiers filtering requires a risk_tier column")
        filtered = filtered.loc[filtered["risk_tier"].isin(risk_tiers)].copy()
    ranked = _ranked(
        filtered,
        probability_column="fraud_probability",
        transaction_id_column=transaction_id_column,
    )
    ranked_count = len(ranked)
    if top_k is not None:
        selected_k = min(int(top_k), ranked_count)
        budget_description: dict[str, Any] = {"kind": "count", "requested": int(top_k)}
    else:
        selected_k = percentage_budget_to_k(ranked_count, float(budget_percentage))
        budget_description = {
            "kind": "percentage",
            "requested": float(budget_percentage),
            "rounding": "ceil",
        }
    selected = ranked.iloc[:selected_k]
    page = selected.iloc[offset : offset + page_size].drop(columns="input_position")
    metadata = {
        "ranking_key": "fraud_probability descending",
        "tie_break": (
            f"{transaction_id_column} ascending, then stable input order"
            if transaction_id_column in filtered
            else "stable input order"
        ),
        "budget": budget_description,
        "total_ranked_after_filters": int(ranked_count),
        "selected_k": int(selected_k),
        "returned_rows": int(len(page)),
        "offset": int(offset),
        "page_size": int(page_size),
        "min_probability": min_probability,
        "risk_tiers": sorted(risk_tiers) if risk_tiers is not None else None,
    }
    return PriorityResult(rows=page.reset_index(drop=True), metadata=metadata)


def validation_alert_budget_metrics(
    labels: np.ndarray | list[int],
    probabilities: np.ndarray | list[float],
    *,
    transaction_ids: list[str | int] | None = None,
    percentage_budgets: tuple[float, ...] = (0.1, 0.5, 1.0),
    count_budgets: tuple[int, ...] = (10, 50, 100),
) -> list[dict[str, Any]]:
    """Compute Precision@K and Recall@K on explicitly supplied validation labels."""
    truth = np.asarray(labels, dtype=np.int8)
    scores = np.asarray(probabilities, dtype=np.float64)
    if truth.ndim != 1 or scores.ndim != 1 or len(truth) != len(scores):
        raise ValueError("validation labels and probabilities must be aligned vectors")
    if not np.isin(truth, [0, 1]).all():
        raise ValueError("validation labels must be binary")
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("validation probabilities must be finite values in [0, 1]")
    if transaction_ids is not None and len(transaction_ids) != len(scores):
        raise ValueError("transaction_ids must align with validation scores")
    if not len(scores):
        return []

    if transaction_ids is None:
        order = np.lexsort((np.arange(len(scores)), -scores))
        tie_rule = "stable source/input row order"
    else:
        id_keys = _identifier_sort_keys(transaction_ids).to_numpy()
        order = np.lexsort((np.arange(len(scores)), id_keys, -scores))
        tie_rule = "transaction identifier ascending, then stable source/input row order"

    budgets = [
        {"budget_type": "count", "budget_value": int(value), "name": f"top_{value}"}
        for value in count_budgets
    ]
    budgets.extend(
        {
            "budget_type": "percentage",
            "budget_value": float(value),
            "name": f"top_{value:g}_percent",
        }
        for value in percentage_budgets
    )
    total_fraud = int(truth.sum())
    output = []
    for budget in budgets:
        if budget["budget_type"] == "count":
            requested = int(budget["budget_value"])
            if requested < 0:
                raise ValueError("count budgets must be nonnegative")
            k = min(len(scores), requested)
        else:
            k = percentage_budget_to_k(len(scores), float(budget["budget_value"]))
        selected = order[:k]
        true_positives = int(truth[selected].sum())
        output.append(
            {
                **budget,
                "k": int(k),
                "alerts": int(k),
                "fraud_captured": true_positives,
                "false_alerts": int(k - true_positives),
                "precision_at_k": float(true_positives / k) if k else None,
                "recall_at_k": (float(true_positives / total_fraud) if total_fraud else None),
                "fraud_prevalence_in_alerts": (float(true_positives / k) if k else None),
                "validation_rows": int(len(scores)),
                "validation_fraud_count": total_fraud,
                "tie_break": tie_rule,
            }
        )
    return output
