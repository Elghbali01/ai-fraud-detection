"""Bounded, deterministic plots for transaction EDA."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from fraud_detection.analytics import class_feature_associations, time_bin_summary
from fraud_detection.schema import AMOUNT_COLUMN, PCA_COLUMNS, TARGET_COLUMN, TIME_COLUMN


def create_eda_figures(frame: pd.DataFrame, output_dir: str | Path) -> list[Path]:
    """Export a small set of readable, deterministic charts and close each figure."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="notebook", palette="colorblind")
    written: list[Path] = []

    class_counts = frame[TARGET_COLUMN].value_counts().reindex([0, 1], fill_value=0)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sns.barplot(x=["Legitimate (0)", "Fraud (1)"], y=class_counts.to_numpy(), ax=ax)
    ax.set_yscale("log")
    ax.set_ylim(bottom=1)
    ax.set(
        title="Observed label counts (logarithmic scale)",
        xlabel="Dataset label",
        ylabel="Transactions",
    )
    total_labels = int(class_counts.sum())
    for index, count in enumerate(class_counts.to_numpy()):
        share = 100 * count / total_labels if total_labels else 0.0
        ax.annotate(
            f"{int(count):,} ({share:.3f}%)",
            (index, max(int(count), 1)),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=9,
        )
    _save(fig, destination / "class_distribution.png", written)

    amount = frame[AMOUNT_COLUMN].dropna().to_numpy(dtype="float64")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    signed_log_amount = np.sign(amount) * np.log10(1 + np.abs(amount))
    ax.hist(signed_log_amount, bins=60)
    ax.set(
        title="Transaction amount distribution (signed log10 transform)",
        xlabel="sign(amount) × log10(1 + abs(amount)); dataset units",
        ylabel="Transactions",
    )
    _save(fig, destination / "amount_distribution.png", written)

    amount_frame = frame[[AMOUNT_COLUMN, TARGET_COLUMN]].dropna().copy()
    raw_amounts = amount_frame[AMOUNT_COLUMN].to_numpy(dtype="float64")
    amount_frame["signed_log_amount"] = np.sign(raw_amounts) * np.log1p(np.abs(raw_amounts))
    fig, ax = plt.subplots(figsize=(7, 4.5))
    class_amounts = [
        amount_frame.loc[amount_frame[TARGET_COLUMN] == label, "signed_log_amount"].to_numpy()
        for label in (0, 1)
    ]
    ax.boxplot(class_amounts, showfliers=False)
    ax.set(
        title="Amount by observed class",
        xlabel="Observed dataset label",
        ylabel="sign(amount) × ln(1 + abs(amount))",
    )
    ax.set_xticks([1, 2], ["Legitimate (0)", "Fraud (1)"])
    _save(fig, destination / "amount_by_class.png", written)

    bins = time_bin_summary(frame, minimum_transactions=1_000)
    if TIME_COLUMN in frame and not bins.empty:
        fig, left = plt.subplots(figsize=(9, 4.5))
        x_hours = bins["elapsed_start_seconds"] / 3_600
        left.bar(x_hours, bins["transactions"], width=5.5, alpha=0.75, label="Transactions")
        left.set(
            title="Transaction volume and fraud rate by elapsed-time bin",
            xlabel="Elapsed hours from dataset origin",
            ylabel="Transactions (6-hour bins)",
        )
        right = left.twinx()
        right.plot(
            x_hours, bins["fraud_rate"] * 100, marker="o", color="#b23a48", label="Fraud rate"
        )
        right.set_ylabel("Fraud rate (%)")
        for index, is_low_volume in enumerate(bins["low_volume"]):
            if is_low_volume:
                right.annotate(
                    "low volume",
                    (x_hours.iloc[index], bins["fraud_rate"].iloc[index] * 100),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                )
            elif bins["low_fraud_count"].iloc[index]:
                right.annotate(
                    f"few fraud cases ({int(bins['fraud_count'].iloc[index])})",
                    (x_hours.iloc[index], bins["fraud_rate"].iloc[index] * 100),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8,
                )
        lines, labels = left.get_legend_handles_labels()
        lines2, labels2 = right.get_legend_handles_labels()
        left.legend(lines + lines2, labels + labels2, loc="upper right")
        _save(fig, destination / "time_activity.png", written)

    associations = class_feature_associations(frame)
    pca_associations = associations[associations["feature"].isin(PCA_COLUMNS)]
    selected = pca_associations["feature"].head(4).tolist()
    if selected:
        plot_frame = frame[[*selected, TARGET_COLUMN]]
        pieces = []
        for _, group in plot_frame.groupby(TARGET_COLUMN, sort=True):
            pieces.append(group.sample(n=min(len(group), 20_000), random_state=42))
        sampled = pd.concat(pieces, ignore_index=True)
        fig, axes = plt.subplots(2, 2, figsize=(11, 7))
        for feature, ax in zip(selected, axes.flat, strict=False):
            sns.histplot(
                data=sampled,
                x=feature,
                hue=TARGET_COLUMN,
                stat="density",
                common_norm=False,
                element="step",
                fill=False,
                bins=40,
                ax=ax,
            )
            ax.set_title(f"{feature}: class-conditional distribution")
            ax.set_xlabel(feature + " (PCA-derived)")
            ax.set_ylabel("Density")
        for ax in axes.flat[len(selected) :]:
            ax.set_visible(False)
        fig.suptitle("Selected PCA features by observed class", y=1.02)
        fig.tight_layout()
        _save(fig, destination / "selected_pca_distributions.png", written)

    heatmap_features = list(dict.fromkeys([TIME_COLUMN, AMOUNT_COLUMN, *selected, TARGET_COLUMN]))
    heatmap_features = [name for name in heatmap_features if name in frame]
    if len(heatmap_features) >= 2:
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(
            frame[heatmap_features].corr(method="spearman"),
            annot=True,
            fmt=".2f",
            cmap="vlag",
            center=0,
            square=True,
            ax=ax,
        )
        ax.set_title("Spearman correlations for selected numeric features")
        _save(fig, destination / "selected_correlations.png", written)

    return written


def _save(fig: plt.Figure, path: Path, written: list[Path]) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    written.append(path)
