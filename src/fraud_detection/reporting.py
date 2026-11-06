"""Machine-readable and human-readable EDA artifact generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from fraud_detection.analytics import (
    amount_summary,
    class_feature_associations,
    class_imbalance,
    correlation_matrix,
    iqr_outlier_diagnostics,
    time_bin_summary,
)
from fraud_detection.profiling import profile_dataset
from fraud_detection.serialization import to_jsonable, write_json
from fraud_detection.visualization import create_eda_figures


def generate_eda_artifacts(
    frame: pd.DataFrame,
    output_dir: str | Path,
    *,
    data_classification: str = "unverified_input_frame",
    dataset_name: str = "creditcard.csv",
) -> dict[str, Any]:
    """Generate tables, charts, and JSON for a dataset already loaded by the caller."""
    root = Path(output_dir)
    figures_dir = root / "figures"
    tables_dir = root / "tables"
    summaries_dir = root / "summaries"
    for directory in (figures_dir, tables_dir, summaries_dir):
        directory.mkdir(parents=True, exist_ok=True)

    profile = profile_dataset(frame)
    imbalance = class_imbalance(frame)
    amounts = amount_summary(frame)
    time_bins = time_bin_summary(frame)
    associations = class_feature_associations(frame)
    outliers = iqr_outlier_diagnostics(frame)
    pearson = correlation_matrix(frame, method="pearson")
    spearman = correlation_matrix(frame, method="spearman")

    amounts.to_csv(tables_dir / "amounts_by_class.csv", index=False)
    time_bins.to_csv(tables_dir / "time_bins.csv", index=False)
    associations.to_csv(tables_dir / "class_feature_associations.csv", index=False)
    outliers.to_csv(tables_dir / "iqr_outlier_diagnostics.csv", index=False)
    pearson.to_csv(tables_dir / "pearson_correlations.csv", index=True)
    spearman.to_csv(tables_dir / "spearman_correlations.csv", index=True)
    pd.DataFrame(profile["columns"]).to_csv(tables_dir / "column_profile.csv", index=False)

    figures = create_eda_figures(frame, figures_dir)
    summary: dict[str, Any] = {
        "report_version": "mission01-eda-v1",
        "data_classification": data_classification,
        "dataset_name": dataset_name,
        "profile": profile,
        "class_imbalance": imbalance,
        "amount_by_class": amounts.to_dict(orient="records"),
        "time_bins": time_bins.to_dict(orient="records"),
        "class_feature_associations": associations.to_dict(orient="records"),
        "iqr_outlier_diagnostics": outliers.to_dict(orient="records"),
        "correlation_methods": ["pearson", "spearman"],
        "figure_files": [path.name for path in figures],
        "limitations": [
            "Descriptive association does not establish causality.",
            "IQR flags are exploratory diagnostics and do not justify automatic row removal.",
            "An anomaly or model prediction is not proof of financial fraud.",
        ],
    }
    write_json(summary, summaries_dir / "eda_summary.json")
    write_json(profile, summaries_dir / "data_quality_profile.json")
    write_json(imbalance, summaries_dir / "class_imbalance.json")
    _write_markdown_report(summary, amounts, time_bins, associations, root / "EDA_REPORT.md")
    return to_jsonable(summary)


def _write_markdown_report(
    summary: dict[str, Any],
    amounts: pd.DataFrame,
    time_bins: pd.DataFrame,
    associations: pd.DataFrame,
    path: Path,
) -> None:
    profile = summary["profile"]
    label = summary["data_classification"].upper()
    imbalance = summary["class_imbalance"]
    lines = [
        "# Exploratory Data Analysis",
        "",
        f"**Data status:** {label}. **Dataset identifier:** {summary['dataset_name']}.",
        "",
        "## Dataset overview",
        "",
        f"- Rows: {profile['row_count']:,}",
        f"- Columns: {profile['column_count']}",
        f"- Deep memory usage: {profile['memory_usage_bytes']:,} bytes",
        f"- Duplicate rows: {profile['duplicate_row_count']:,} (reported, not removed)",
        f"- Missing values: {sum(column['missing_count'] for column in profile['columns']):,}",
        "",
        "## Label distribution",
        "",
        f"- Legitimate labels (0): {imbalance['legitimate_count']:,}",
        f"- Fraud labels (1): {imbalance['fraud_count']:,}",
        f"- Fraud share: {imbalance['fraud_pct']:.6g}%",
        f"- Majority/minority ratio: {imbalance['majority_minority_ratio']}",
        f"- Majority-class baseline accuracy: {imbalance['majority_class_baseline_accuracy']}",
        "",
        imbalance["baseline_note"],
        "Accuracy alone can hide poor detection when fraud is rare; Mission 02 should report "
        "precision-recall metrics and threshold-specific confusion counts.",
        "",
        "## Amount summaries",
        "",
        _markdown_table(amounts),
        "",
        "Amounts are reported in dataset units. A signed log transform appears only in plots; it "
        "handles zeros and negative values without modifying the loaded values.",
        "",
        "## Elapsed-time activity",
        "",
        _markdown_table(time_bins),
        "",
        "Time is treated as elapsed seconds from the dataset origin. The analysis does not "
        "convert it into calendar timestamps. Bins below the configured minimum are marked low "
        "volume and should not support strong rate comparisons.",
        "",
        "## Feature associations and outliers",
        "",
        "Selected numeric feature associations with the label use Spearman correlation, sorted "
        "by absolute coefficient. They are descriptive, may be unstable for rare labels, and do "
        "not establish causality.",
        "",
        _markdown_table(associations.head(10)),
        "",
        "IQR flags are stored in tables/iqr_outlier_diagnostics.csv. No outliers were removed; "
        "fraudulent observations can be statistically unusual.",
        "",
        "## Scientific limitations",
        "",
        "- PCA-derived V1–V28 values are anonymized and do not map directly to business concepts.",
        "- Predictions, estimated risk, anomaly scores, and confirmed historical labels are "
        "different quantities.",
        "- No model was trained in Mission 01.",
        "- Data-dependent conclusions below apply only to the data status identified at the top.",
        "",
        "## Artifacts",
        "",
        f"Figures: {', '.join(summary['figure_files']) or 'none'}",
        "",
        "Tables and machine-readable summaries are in sibling tables/ and summaries/ directories.",
        "",
    ]
    if summary["data_classification"] == "synthetic_fixture":
        lines[3:3] = [
            "> This output is based on a deterministic synthetic fixture for pipeline validation. "
            "It is not a ULB dataset result and must not be cited as a real-data finding.",
            "",
        ]
    elif summary["data_classification"] != "source_verified_file":
        lines[3:3] = [
            "> This input's source provenance was not verified. Treat these as file-specific "
            "descriptive results, not confirmed findings about the ULB source.",
            "",
        ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _markdown_table(frame: pd.DataFrame) -> str:
    """Format a compact Markdown table without an optional tabulate dependency."""
    if frame.empty:
        return "_No rows._"
    columns = [str(column) for column in frame.columns]
    rows = []
    for record in frame.head(20).itertuples(index=False, name=None):
        rows.append([_format_cell(value) for value in record])
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _format_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|")
