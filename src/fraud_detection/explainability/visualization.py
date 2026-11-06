"""Bounded visualizations for exact linear and SHAP explanation outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd
import shap

from fraud_detection.explainability.linear import LinearAttributionBatch
from fraud_detection.explainability.shap_engine import ShapExplanationBatch
from fraud_detection.schema import FEATURE_COLUMNS


def _finish_figure(path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(destination, dpi=160, bbox_inches="tight")
    plt.close()
    return destination


def plot_global_shap_importance(summary: pd.DataFrame, path: str | Path) -> Path:
    """Plot mean absolute raw-log-odds SHAP importance."""
    top = summary.nlargest(20, "mean_abs_shap_log_odds").sort_values(
        "mean_abs_shap_log_odds", ascending=True
    )
    _, ax = plt.subplots(figsize=(9, 7))
    ax.barh(top["feature"], top["mean_abs_shap_log_odds"], color="#356a9a")
    ax.set_xlabel("Mean absolute SHAP value (raw log-odds)")
    ax.set_title("Global model attribution on validation observations")
    return _finish_figure(path)


def plot_shap_beeswarm(
    shap_batch: ShapExplanationBatch,
    transformed_features: pd.DataFrame,
    path: str | Path,
) -> Path:
    """Render a bounded beeswarm from the validation SHAP matrix."""
    explanation = shap.Explanation(
        values=shap_batch.values.to_numpy(dtype=np.float64),
        base_values=shap_batch.base_values,
        data=transformed_features.loc[:, list(FEATURE_COLUMNS)].to_numpy(dtype=np.float64),
        feature_names=list(FEATURE_COLUMNS),
    )
    plt.figure(figsize=(10, 8))
    shap.plots.beeswarm(explanation, max_display=20, show=False, plot_size=None)
    plt.title("Validation SHAP distribution in raw log-odds")
    return _finish_figure(path)


def plot_coefficient_vs_shap(summary: pd.DataFrame, path: str | Path) -> Path:
    """Compare scaled coefficient magnitude with empirical validation SHAP magnitude."""
    _, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(
        summary["absolute_coefficient"],
        summary["mean_abs_shap_log_odds"],
        color="#38836a",
        alpha=0.8,
    )
    for row in summary.nlargest(10, "mean_abs_shap_log_odds").itertuples():
        ax.annotate(
            row.feature,
            (row.absolute_coefficient, row.mean_abs_shap_log_odds),
            xytext=(4, 3),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xlabel("Absolute coefficient in standardized feature space")
    ax.set_ylabel("Mean absolute validation SHAP (raw log-odds)")
    ax.set_title("Coefficient magnitude and observed attribution magnitude")
    return _finish_figure(path)


def plot_local_shap_waterfall(
    shap_batch: ShapExplanationBatch,
    transformed_features: pd.DataFrame,
    row_position: int,
    path: str | Path,
    *,
    title: str,
) -> Path:
    """Render one interventional SHAP waterfall in raw log-odds space."""
    explanation = shap.Explanation(
        values=shap_batch.values.iloc[row_position].to_numpy(dtype=np.float64),
        base_values=float(shap_batch.base_values[row_position]),
        data=transformed_features.iloc[row_position].to_numpy(dtype=np.float64),
        feature_names=list(FEATURE_COLUMNS),
    )
    plt.figure(figsize=(10, 7))
    shap.plots.waterfall(explanation, max_display=12, show=False)
    plt.title(title)
    return _finish_figure(path)


def plot_linear_contribution_waterfall(
    attributions: LinearAttributionBatch,
    row_position: int,
    path: str | Path,
    *,
    title: str,
    max_features: int = 12,
) -> Path:
    """Plot exact coefficient contributions around the zero-transformed intercept."""
    values = attributions.contributions.iloc[row_position]
    ranked = values.reindex(values.abs().sort_values(ascending=False).index)
    shown = ranked.iloc[:max_features]
    other = float(ranked.iloc[max_features:].sum())
    if len(ranked) > max_features:
        shown = pd.concat([shown, pd.Series({"Other features": other})])
    ordered = shown.sort_values()
    colors = ["#c5534f" if value > 0 else "#4d78a8" for value in ordered.to_numpy()]
    _, ax = plt.subplots(figsize=(9, 7))
    ax.barh(ordered.index.astype(str), ordered.to_numpy(), color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Contribution to raw model log-odds")
    ax.set_title(title)
    ax.text(
        0.99,
        0.02,
        f"Intercept: {attributions.intercept:.3f}  |  "
        f"Decision score: {attributions.decision_function[row_position]:.3f}",
        transform=ax.transAxes,
        ha="right",
        fontsize=8,
    )
    return _finish_figure(path)


def plot_risk_score_distribution(
    probabilities: np.ndarray,
    threshold: float,
    path: str | Path,
) -> Path:
    """Plot validation calibrated probabilities with the frozen decision threshold."""
    values = np.asarray(probabilities, dtype=np.float64)
    _, ax = plt.subplots(figsize=(8, 5))
    ax.hist(values, bins=60, color="#527da6", alpha=0.9)
    ax.axvline(threshold, color="#b4413e", linestyle="--", label="Frozen decision threshold")
    ax.set_xlabel("Calibrated fraud probability")
    ax.set_ylabel("Validation transactions")
    ax.set_title("Validation risk-score distribution")
    ax.legend()
    return _finish_figure(path)


def plot_risk_tier_analysis(summaries: list[dict[str, Any]], path: str | Path) -> Path:
    """Show validation counts and fraud prevalence by operational tier."""
    frame = (
        pd.DataFrame(summaries).set_index("tier").reindex(["Low", "Elevated", "High", "Critical"])
    )
    _, left = plt.subplots(figsize=(9, 5))
    x = np.arange(len(frame))
    left.bar(x - 0.18, frame["rows"], width=0.36, color="#5f84a7", label="Transactions")
    right = left.twinx()
    rates = frame["fraud_prevalence"].fillna(0).to_numpy() * 100
    right.bar(x + 0.18, rates, width=0.36, color="#d08a46", label="Fraud prevalence")
    left.set_xticks(x, frame.index)
    left.set_ylabel("Validation transactions")
    right.set_ylabel("Historical fraud labels in tier (%)")
    left.set_title("Validation distribution by policy tier")
    left.legend(loc="upper left")
    right.legend(loc="upper right")
    return _finish_figure(path)


def plot_alert_capacity(metrics: list[dict[str, Any]], path: str | Path) -> Path:
    """Plot validation Precision@K and Recall@K across alert budgets."""
    frame = pd.DataFrame(metrics).dropna(subset=["precision_at_k", "recall_at_k"])
    frame = frame.sort_values("k")
    _, ax = plt.subplots(figsize=(8, 5))
    ax.plot(frame["k"], frame["precision_at_k"], marker="o", label="Precision@K")
    ax.plot(frame["k"], frame["recall_at_k"], marker="s", label="Recall@K")
    for row in frame.itertuples():
        ax.annotate(row.name, (row.k, row.recall_at_k), xytext=(3, 4), textcoords="offset points")
    ax.set_ylim(0, 1)
    ax.set_xlabel("Review capacity K (validation rows)")
    ax.set_ylabel("Fraction")
    ax.set_title("Validation alert-capacity diagnostics")
    ax.legend()
    return _finish_figure(path)


def plot_supervised_anomaly_quadrants(
    probabilities: np.ndarray,
    anomaly_percentiles: np.ndarray,
    labels: np.ndarray,
    *,
    decision_threshold: float,
    anomaly_threshold: float,
    path: str | Path,
) -> Path:
    """Show separate validation signals with policy boundaries and label markers."""
    probabilities = np.asarray(probabilities, dtype=np.float64)
    anomaly_percentiles = np.asarray(anomaly_percentiles, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int8)
    _, ax = plt.subplots(figsize=(8, 6))
    for label, color, name in ((0, "#6c91b3", "Class 0 label"), (1, "#c4554f", "Class 1 label")):
        mask = labels == label
        ax.scatter(
            probabilities[mask],
            anomaly_percentiles[mask],
            s=10 if label == 0 else 18,
            alpha=0.4 if label == 0 else 0.8,
            color=color,
            label=name,
            rasterized=True,
        )
    ax.axvline(decision_threshold, color="#333333", linestyle="--", label="Frozen fraud threshold")
    ax.axhline(anomaly_threshold, color="#7f6c9a", linestyle=":", label="Training-reference p95")
    ax.set_xlabel("Calibrated fraud probability")
    ax.set_ylabel("Percentile vs known-legitimate training reference")
    ax.set_title("Validation: supervised risk and anomaly are separate signals")
    ax.legend(loc="best")
    return _finish_figure(path)


def plot_top_k_overlap(comparison: dict[str, Any], path: str | Path) -> Path:
    """Plot side-by-side top-K overlap as a fraction of each review budget."""
    rows = comparison["alert_budgets"]
    labels = [f"{row['budget_percentage']:g}%" for row in rows]
    values = [row["overlap_fraction_of_k"] for row in rows]
    _, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color="#6e8f78")
    ax.set_ylim(0, 1)
    ax.set_ylabel("Overlap fraction of K")
    ax.set_xlabel("Validation review budget")
    ax.set_title("Supervised and anomaly top-K overlap")
    return _finish_figure(path)
