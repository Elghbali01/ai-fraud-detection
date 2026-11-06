"""Compact real-data reports, machine-readable tables, and evaluation figures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, default=_json_default, allow_nan=False) + "\n", encoding="utf-8"
    )


def _figure(path: Path) -> tuple[plt.Figure, plt.Axes]:
    plt.switch_backend("Agg")
    figure, axes = plt.subplots(figsize=(8.2, 5.0), constrained_layout=True)
    axes.grid(True, alpha=0.22)
    return figure, axes


def _write_figures(
    results: dict[str, Any], plot_data: dict[str, np.ndarray], figures: Path
) -> None:
    figures.mkdir(parents=True, exist_ok=True)
    candidate_rows = results["candidate_metrics"]
    ranked = sorted(candidate_rows, key=lambda row: row["mean_average_precision"], reverse=True)
    fig, ax = _figure(figures / "model_comparison.png")
    ax.barh([row["candidate"] for row in ranked], [row["mean_average_precision"] for row in ranked])
    ax.invert_yaxis()
    ax.set_xlabel("Mean Average Precision across three temporal training folds")
    ax.set_title("Supervised candidate comparison")
    fig.savefig(figures / "model_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    truth = plot_data["test_labels"]
    probabilities = plot_data["test_probabilities"]
    precision, recall, _ = precision_recall_curve(truth, probabilities)
    fig, ax = _figure(figures / "final_precision_recall.png")
    ax.plot(
        recall,
        precision,
        label=f"Selected model (AP={results['final_test']['metrics']['average_precision']:.4f})",
    )
    ax.axhline(
        float(truth.mean()),
        color="gray",
        linestyle="--",
        label=f"Fraud prevalence={truth.mean():.4%}",
    )
    ax.set(
        xlabel="Recall",
        ylabel="Precision",
        title="Sealed chronological test: precision-recall curve",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    ax.legend(loc="best")
    fig.savefig(figures / "final_precision_recall.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    false_positive_rate, true_positive_rate, _ = roc_curve(truth, probabilities)
    fig, ax = _figure(figures / "final_roc.png")
    ax.plot(
        false_positive_rate,
        true_positive_rate,
        label=f"ROC-AUC={results['final_test']['metrics']['roc_auc']:.4f}",
    )
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", label="No-discrimination reference")
    ax.set(
        xlabel="False positive rate",
        ylabel="True positive rate",
        title="Sealed chronological test: ROC curve",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    ax.legend(loc="lower right")
    fig.savefig(figures / "final_roc.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    threshold = results["threshold"]["threshold"]
    predicted = (probabilities >= threshold).astype(np.int8)
    matrix = confusion_matrix(truth, predicted, labels=[0, 1])
    fig, ax = _figure(figures / "final_confusion_matrix.png")
    image = ax.imshow(matrix, cmap="Blues")
    for (row, column), value in np.ndenumerate(matrix):
        ax.text(column, row, f"{value:,}", ha="center", va="center", color="black", fontsize=12)
    ax.set(
        xticks=[0, 1],
        yticks=[0, 1],
        xticklabels=["Predicted 0", "Predicted 1"],
        yticklabels=["Observed 0", "Observed 1"],
        title=f"Final test confusion matrix (threshold={threshold:.6g})",
    )
    fig.colorbar(image, ax=ax, label="Transactions")
    fig.savefig(figures / "final_confusion_matrix.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    validation_labels = plot_data["validation_labels"]
    raw = plot_data["validation_raw_probabilities"]
    calibrated = plot_data["validation_probabilities"]
    bins = min(10, max(2, int(np.sqrt(len(validation_labels)))))
    fig, ax = _figure(figures / "calibration_reliability.png")
    for values, label in ((raw, "Uncalibrated model"), (calibrated, "Training-fold sigmoid")):
        fraction_positive, mean_predicted = calibration_curve(
            validation_labels, values, n_bins=bins, strategy="quantile"
        )
        ax.plot(mean_predicted, fraction_positive, marker="o", label=label)
    ax.plot([0, 1], [0, 1], color="gray", linestyle="--", label="Perfect calibration reference")
    ax.set(
        xlabel="Mean predicted probability",
        ylabel="Observed fraud fraction",
        title="Validation reliability diagram",
    )
    ax.legend(loc="best")
    fig.savefig(figures / "calibration_reliability.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), constrained_layout=True)
    for axis, values, title in (
        (axes[0], raw, "Raw model scores"),
        (axes[1], calibrated, "Training-fold sigmoid"),
    ):
        histogram_bins = np.logspace(-8, 0, 50)
        axis.hist(
            np.clip(values[validation_labels == 0], 1e-8, 1),
            bins=histogram_bins,
            alpha=0.65,
            label="Legitimate",
        )
        axis.hist(
            np.clip(values[validation_labels == 1], 1e-8, 1),
            bins=histogram_bins,
            alpha=0.65,
            label="Fraud",
        )
        axis.set_xscale("log")
        axis.set(xlabel="Model score (log scale)", ylabel="Validation row count", title=title)
        axis.grid(True, alpha=0.22)
        axis.legend(loc="best")
    fig.suptitle("Validation score distributions by historical label")
    fig.savefig(figures / "probability_distributions.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    threshold_frame = pd.DataFrame(results["threshold_table"]).sort_values("threshold")
    fig, ax = _figure(figures / "threshold_analysis.png")
    ax.plot(threshold_frame["threshold"], threshold_frame["precision"], label="Precision")
    ax.plot(threshold_frame["threshold"], threshold_frame["recall"], label="Recall")
    ax.plot(threshold_frame["threshold"], threshold_frame["f2"], label="F2")
    ax.axvline(threshold, color="black", linestyle="--", label="Selected validation threshold")
    ax.set(
        xlabel="Sigmoid-mapped score threshold",
        ylabel="Metric",
        title="Validation threshold analysis",
        ylim=(0, 1),
    )
    ax.legend(loc="best")
    fig.savefig(figures / "threshold_analysis.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    anomaly_scores = plot_data["test_anomaly_scores"]
    fig, ax = _figure(figures / "anomaly_score_distribution.png")
    for label, name in ((0, "Legitimate labels"), (1, "Fraud labels")):
        values = anomaly_scores[truth == label]
        ax.hist(values, bins=35, alpha=0.6, density=True, label=f"{name} (n={len(values)})")
    ax.set(
        xlabel="Isolation Forest score (-score_samples; higher = more anomalous)",
        ylabel="Density",
        title="Final test anomaly-score distributions",
    )
    ax.legend(loc="best")
    fig.savefig(figures / "anomaly_score_distribution.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    budgets = results["final_test"]["alert_budgets"]
    anomaly_budgets = results["anomaly"]["final_test"]["alert_budgets"]
    labels = [f"Top {row['budget_percentage']:g}%" for row in budgets]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = _figure(figures / "alert_budget_comparison.png")
    ax.bar(x - width / 2, [row["recall_at_k"] for row in budgets], width, label="Supervised")
    ax.bar(
        x + width / 2,
        [row["recall_at_k"] for row in anomaly_budgets],
        width,
        label="Isolation Forest",
    )
    ax.set(
        xticks=x,
        xticklabels=labels,
        ylabel="Fraud recall at fixed review capacity",
        title="Final test top-K capture",
    )
    ax.legend(loc="best")
    fig.savefig(figures / "alert_budget_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def _metric(value: Any, digits: int = 4) -> str:
    if value is None:
        return "not defined"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def generate_ml_reports(
    results: dict[str, Any],
    plot_data: dict[str, np.ndarray],
    output_directory: str | Path,
) -> list[Path]:
    """Write all Mission 02 experiment reports and a bounded set of figures."""
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    figures = output / "figures"
    _write_figures(results, plot_data, figures)
    _write_json(output / "artifact_manifest.json", results["artifact"])
    _write_json(output / "anomaly_artifact_manifest.json", results["anomaly"]["artifact"])

    validation_by_name = {item["candidate"]: item for item in results["model_validation"]}
    candidate_frame = pd.DataFrame(results["candidate_metrics"])
    for field in (
        "average_precision",
        "roc_auc",
        "precision",
        "recall",
        "f1",
        "f2",
        "false_positive",
        "false_negative",
        "alert_count",
    ):
        values = {name: validation_by_name[name]["metrics"][field] for name in validation_by_name}
        candidate_frame[f"validation_{field}_at_0_5"] = candidate_frame["candidate"].map(values)
    candidate_frame["validation_fit_seconds"] = candidate_frame["candidate"].map(
        lambda name: validation_by_name[name]["fit_seconds"]
    )
    candidate_frame["validation_prediction_seconds"] = candidate_frame["candidate"].map(
        lambda name: validation_by_name[name]["prediction_seconds"]
    )
    candidate_frame["hyperparameters"] = candidate_frame["hyperparameters"].map(
        lambda value: json.dumps(value, sort_keys=True)
    )
    candidate_frame["fold_average_precision"] = candidate_frame["fold_average_precision"].map(
        lambda value: json.dumps(value)
    )
    candidate_frame["fold_roc_auc"] = candidate_frame["fold_roc_auc"].map(
        lambda value: json.dumps(value)
    )
    candidate_frame["warnings"] = candidate_frame["warnings"].map(lambda value: json.dumps(value))
    comparison_csv = output / "model_comparison.csv"
    candidate_frame.to_csv(comparison_csv, index=False)
    threshold_csv = output / "threshold_analysis.csv"
    pd.DataFrame(results["threshold_table"]).to_csv(threshold_csv, index=False)
    budget_csv = output / "alert_budget_comparison.csv"
    pd.DataFrame(
        [{"model": "supervised", **item} for item in results["final_test"]["alert_budgets"]]
        + [
            {"model": "isolation_forest", **item}
            for item in results["anomaly"]["final_test"]["alert_budgets"]
        ]
    ).to_csv(budget_csv, index=False)

    comparison_rows = "\n".join(
        f"| {item['candidate']} | {item['mean_average_precision']:.5f} | "
        f"{item['std_average_precision']:.5f} | {item['mean_roc_auc']:.5f} | "
        f"{json.dumps(item['hyperparameters'], sort_keys=True)} |"
        for item in sorted(
            results["candidate_metrics"],
            key=lambda row: row["mean_average_precision"],
            reverse=True,
        )
    )
    validation_rows = "\n".join(
        f"| {item['candidate']} | {item['metrics']['average_precision']:.5f} | "
        f"{item['metrics']['roc_auc']:.5f} | {item['metrics']['precision']:.4f} | "
        f"{item['metrics']['recall']:.4f} | {item['metrics']['f1']:.4f} | "
        f"{item['metrics']['f2']:.4f} | {item['metrics']['false_positive']:,} | "
        f"{item['metrics']['false_negative']:,} | {item['fit_seconds']:.1f} | "
        f"{item['prediction_seconds']:.3f} |"
        for item in results["model_validation"]
    )
    comparison_text = [
        "# Supervised model comparison\n\n",
        "All candidates use the same three expanding-window folds inside the ",
        "chronological training ",
        "partition. Average Precision is the primary ranking metric; ROC-AUC is secondary. ",
        "Fold results are noisy because one fold contains only 28 fraud examples. The winner is ",
        "selected by the predeclared one-standard-error rule, preferring lower complexity.\n\n",
        "### Training-fold selection metrics\n\n",
        "| Candidate | Mean AP | Fold AP SD | Mean ROC-AUC | Fixed parameters |\n",
        "|---|---:|---:|---:|---|\n",
        f"{comparison_rows}\n\n",
        "### Post-freeze validation comparison\n\n",
        "These uncalibrated candidate scores use the fixed 0.5 reference threshold. They were ",
        "computed after model and threshold selection was frozen and did not change ",
        "the winner.\n\n",
        "| Candidate | AP | ROC-AUC | Precision | Recall | F1 | F2 | FP | FN | ",
        "Fit sec | Predict sec |\n",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n",
        f"{validation_rows}\n\n",
        f"Selected: **{results['selected_model']['name']}** "
        f"({results['selected_model']['family']}).\n\n",
        f"Selection: `{results['selection']['criterion']}`.\n\n",
        "AP is Average Precision, not trapezoidal PR area. Validation metrics use the ",
        "stated fixed ",
        "0.5 reference and are not the selected operating threshold. The final test set did not ",
        "take part in model selection.\n\n",
        "![Candidate Average Precision](figures/model_comparison.png)\n",
    ]
    (output / "MODEL_COMPARISON.md").write_text("".join(comparison_text), encoding="utf-8")

    split = results["split_manifest"]
    split_rows = "\n".join(
        f"| {name} | {item['rows']:,} | {item['class_counts']['0']:,} | "
        f"{item['class_counts']['1']:,} | {item['time_min']:g}–{item['time_max']:g} |"
        for name, item in split["partitions"].items()
    )
    protocol_text = [
        "# Evaluation protocol\n\n",
        "The primary split is forward-in-time with complete equal-Time groups. ",
        "Split boundaries and all duplicate counts are frozen in `split_manifest.json` ",
        "before training. Folds are expanding windows inside training only. Candidate ",
        "selection uses mean fold Average Precision with a one-standard-error ",
        "simplicity rule. Sigmoid calibration is fitted to out-of-fold predictions ",
        "from those training-only folds. Validation assesses calibration and selects a ",
        "maximum-F2 threshold. Post-freeze candidate validation scores use threshold 0.5 ",
        "for descriptive comparison only. The ",
        "test labels are first used after the model, calibration, and threshold are frozen.\n\n",
        "| Partition | Rows | Class 0 | Class 1 | Time range (elapsed seconds) |\n",
        "|---|---:|---:|---:|---:|\n",
        f"{split_rows}\n\n",
        f"Training fold fraud counts: "
        f"{[fold['validation_fraud'] for fold in split['development_folds']]}. ",
        "The source covers only a short historical window and does not establish later-period ",
        "or production performance.\n",
    ]
    (output / "EVALUATION_PROTOCOL.md").write_text("".join(protocol_text), encoding="utf-8")

    calibration = results["calibration"]
    calibration_table = (
        f"| Raw estimator | {_metric(calibration['raw']['brier_score'])} | "
        f"{_metric(calibration['raw']['log_loss'])} | "
        f"{_metric(calibration['raw']['expected_calibration_error'])} |\n"
        f"| Training-fold sigmoid | {_metric(calibration['sigmoid']['brier_score'])} | "
        f"{_metric(calibration['sigmoid']['log_loss'])} | "
        f"{_metric(calibration['sigmoid']['expected_calibration_error'])} |\n\n"
    )
    calibration_text = [
        "# Probability calibration\n\n",
        "The selected estimator's sigmoid (Platt) mapping was fitted to training-only ",
        "held-out fold ",
        "scores. Validation data was used for assessment, not for fitting the mapping. Isotonic ",
        "calibration was not fit because the limited positive count makes a flexible ",
        "mapping prone ",
        "to overfit.\n\n",
        "| Method | Brier score | Log loss | Equal-frequency ECE |\n",
        "|---|---:|---:|---:|\n",
        calibration_table,
        "Validation probability quantiles (minimum, median, p90, p99, maximum):\n\n",
        f"- Raw model scores: `{calibration['raw']['probability_quantiles']}`\n",
        f"- Training-fold sigmoid: `{calibration['sigmoid']['probability_quantiles']}`\n\n",
        f"Brier improvement: **{calibration['brier_improved']}**. "
        f"Log-loss improvement: **{calibration['log_loss_improved']}**. ",
        "The validation estimate uses 56 fraud rows and can be unstable. A mapped score is not ",
        "automatically a reliable production probability.\n\n",
        "![Validation reliability diagram](figures/calibration_reliability.png)\n",
        "\n![Validation probability distributions](figures/probability_distributions.png)\n",
    ]
    (output / "CALIBRATION_REPORT.md").write_text("".join(calibration_text), encoding="utf-8")

    threshold = results["threshold"]
    validation_metrics = results["validation"]["metrics"]
    threshold_text = [
        "# Decision threshold analysis\n\n",
        "The operating point maximizes F2 on the validation partition. This explicitly ",
        "weights recall ",
        "more than precision; it is a development objective, not an asserted business cost. No ",
        "final-test labels were used.\n\n",
        f"- Selected threshold: **{threshold['threshold']:.8g}**\n",
        f"- Validation precision / recall: **{validation_metrics['precision']:.4f} / "
        f"{validation_metrics['recall']:.4f}**\n",
        f"- F1 / F2: **{validation_metrics['f1']:.4f} / {validation_metrics['f2']:.4f}**\n",
        f"- Alerts: **{validation_metrics['alert_count']:,} of "
        f"{validation_metrics['rows']:,} "
        f"({validation_metrics['alert_percentage']:.3f}%)**\n",
        f"- False positives / missed fraud: **{validation_metrics['false_positive']:,} / "
        f"{validation_metrics['false_negative']:,}**\n\n",
        "Top-K tables use exactly `ceil(partition_rows × budget)` alerts; ties are ",
        "broken by source row order. The threshold table contains a compact quantile ",
        "grid plus the selected point.\n\n",
        "![Validation threshold metrics](figures/threshold_analysis.png)\n",
    ]
    (output / "THRESHOLD_ANALYSIS.md").write_text("".join(threshold_text), encoding="utf-8")

    anomaly = results["anomaly"]
    overlap_rows = "\n".join(
        f"| {validation_item['budget_percentage']:g}% | "
        f"{validation_item['overlap_percentage_of_k']:.2f}% | "
        f"{test_item['overlap_percentage_of_k']:.2f}% |"
        for validation_item, test_item in zip(
            anomaly["top_ranked_overlap_validation"],
            anomaly["top_ranked_overlap_final_test"],
            strict=True,
        )
    )
    anomaly_text = [
        "# Isolation Forest anomaly experiment\n\n",
        "Isolation Forest was fitted on Class 0 rows from the training partition only; ",
        "labels were used ",
        "to define this known-legitimate fit subset and only to evaluate ranking. Higher ",
        "`-score_samples` means more anomalous. The score is continuous and is **not ",
        "a fraud probability**.\n\n",
        f"- Fit rows: **{anomaly['fit']['fit_rows']:,} legitimate transactions**\n",
        "- Input features: **unscaled numeric ULB fields; `Class` excluded**\n",
        f"- Saved artifact: `{anomaly['artifact']['artifact_path']}`\n",
        f"- Artifact SHA-256: `{anomaly['artifact']['artifact_sha256']}`\n",
        f"- Validation Average Precision / ROC-AUC: **"
        f"{anomaly['validation']['average_precision']:.5f} / "
        f"{anomaly['validation']['roc_auc']:.5f}**\n",
        f"- Final-test Average Precision / ROC-AUC: **"
        f"{anomaly['final_test']['average_precision']:.5f} / "
        f"{anomaly['final_test']['roc_auc']:.5f}**\n\n",
        "Unusual transactions are not necessarily fraudulent; many fraud cases may also resemble ",
        "common transactions. Scores are not combined with supervised probabilities.\n\n",
        "## Top-ranked overlap with the supervised model\n\n",
        "Overlap is descriptive and does not combine or recalibrate score scales.\n\n",
        "| Alert budget | Validation overlap of K | Final-test overlap of K |\n",
        "|---:|---:|---:|\n",
        overlap_rows,
        "\n\n",
        "![Isolation Forest score distributions](figures/anomaly_score_distribution.png)\n",
    ]
    (output / "ANOMALY_DETECTION.md").write_text("".join(anomaly_text), encoding="utf-8")

    final_metrics = results["final_test"]["metrics"]
    confusion = (
        f"TN={final_metrics['true_negative']:,}, FP={final_metrics['false_positive']:,}, "
        f"FN={final_metrics['false_negative']:,}, TP={final_metrics['true_positive']:,}"
    )
    budget_rows = "\n".join(
        f"| {supervised['budget_percentage']:g}% | {supervised['k']:,} | "
        f"{supervised['precision_at_k']:.4f} | {supervised['recall_at_k']:.4f} | "
        f"{unsupervised['recall_at_k']:.4f} |"
        for supervised, unsupervised in zip(
            results["final_test"]["alert_budgets"],
            results["anomaly"]["final_test"]["alert_budgets"],
            strict=True,
        )
    )
    final_report = [
        "# Final supervised model report\n\n",
        f"**Selected model:** {results['selected_model']['name']} "
        f"({results['selected_model']['family']})  \n",
        f"**Threshold:** {threshold['threshold']:.8g}, selected by validation maximum F2  \n",
        f"**Final-test rows:** {final_metrics['rows']:,}; "
        f"fraud labels: {final_metrics['positive_count']:,}  \n",
        f"**Dataset SHA-256:** `{results['dataset_sha256']}`  \n",
        f"**Split manifest:** `{split['manifest_id']}`\n\n",
        "| Metric | Final chronological test |\n|---|---:|\n",
        f"| Average Precision | {final_metrics['average_precision']:.5f} |\n",
        f"| Trapezoidal PR area | {final_metrics['pr_auc_trapezoid']:.5f} |\n",
        f"| ROC-AUC | {final_metrics['roc_auc']:.5f} |\n",
        f"| Precision / recall | {final_metrics['precision']:.5f} / "
        f"{final_metrics['recall']:.5f} |\n",
        f"| F1 / F2 | {final_metrics['f1']:.5f} / {final_metrics['f2']:.5f} |\n",
        f"| Brier / log loss | {final_metrics['brier_score']:.6f} / "
        f"{final_metrics['log_loss']:.6f} |\n",
        f"| Confusion counts | {confusion} |\n",
        f"| Alerts | {final_metrics['alert_count']:,} "
        f"({final_metrics['alert_percentage']:.3f}%) |\n\n",
        f"Recall's Wilson 95% interval is `{final_metrics['recall_wilson_95_ci']}`; "
        "this interval assumes independent Bernoulli outcomes and does not account for temporal ",
        "dependence. The 52 fraud cases are too few for fine-grained certainty claims.\n\n",
        "## Alert capacity\n\n",
        "| Budget | K alerts | Supervised precision@K | Supervised recall@K | "
        "Isolation Forest recall@K |\n",
        "|---:|---:|---:|---:|---:|\n",
        budget_rows,
        "\n\n## Limitations\n\n",
        "The test window contains 52 fraud labels and covers only a short historical ",
        "dataset period. ",
        "V1–V28 are anonymous PCA components; Time is elapsed seconds with no calendar origin; no ",
        "customer, merchant, location, or device history is available. Duplicate ",
        "signatures did not cross the frozen partitions, but near-duplicate and entity ",
        "leakage are not assessable. These ",
        "results do not establish production readiness or future-month generalization.\n\n",
        "![Final test precision-recall curve](figures/final_precision_recall.png)\n\n",
        "![Final test confusion matrix](figures/final_confusion_matrix.png)\n",
        "\n![Final test ROC curve](figures/final_roc.png)\n",
        "\n## Local artifacts\n\n",
        f"- Supervised bundle: `{results['artifact']['artifact_path']}`\n",
        f"- Supervised bundle SHA-256: `{results['artifact']['artifact_sha256']}`\n",
        f"- Isolation Forest: `{results['anomaly']['artifact']['artifact_path']}`\n",
        f"- Isolation Forest SHA-256: `{results['anomaly']['artifact']['artifact_sha256']}`\n",
        "- Both joblib files are under ignored `data/models/` and must only be loaded from ",
        "trusted local sources.\n",
    ]
    (output / "FINAL_MODEL_REPORT.md").write_text("".join(final_report), encoding="utf-8")

    _write_json(output / "latest_results.json", results)
    _write_json(output / "EXPERIMENT_REGISTRY.json", results["registry_snapshot"])
    generated = [
        comparison_csv,
        threshold_csv,
        budget_csv,
        output / "MODEL_COMPARISON.md",
        output / "EVALUATION_PROTOCOL.md",
        output / "CALIBRATION_REPORT.md",
        output / "THRESHOLD_ANALYSIS.md",
        output / "ANOMALY_DETECTION.md",
        output / "FINAL_MODEL_REPORT.md",
        output / "latest_results.json",
        output / "EXPERIMENT_REGISTRY.json",
        output / "artifact_manifest.json",
        output / "anomaly_artifact_manifest.json",
        *sorted(figures.glob("*.png")),
    ]
    return generated
