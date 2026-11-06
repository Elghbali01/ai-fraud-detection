"""Machine-readable and human-readable EDA artifact generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
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
from fraud_detection.schema import PCA_COLUMNS, TIME_COLUMN
from fraud_detection.serialization import to_jsonable, write_json
from fraud_detection.visualization import create_eda_figures


def generate_eda_artifacts(
    frame: pd.DataFrame,
    output_dir: str | Path,
    *,
    data_classification: str = "unverified_input_frame",
    dataset_name: str = "creditcard.csv",
    provenance: dict[str, Any] | None = None,
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
    predictor_pearson = pearson.drop(index="Class", columns="Class", errors="ignore")
    predictor_spearman = spearman.drop(index="Class", columns="Class", errors="ignore")
    class_conditionals = _class_conditional_summaries(frame)
    diagnostics = _dataset_diagnostics(frame)

    amounts.to_csv(tables_dir / "amounts_by_class.csv", index=False)
    time_bins.to_csv(tables_dir / "time_bins.csv", index=False)
    associations.to_csv(tables_dir / "class_feature_associations.csv", index=False)
    outliers.to_csv(tables_dir / "iqr_outlier_diagnostics.csv", index=False)
    pearson.to_csv(tables_dir / "pearson_correlations.csv", index=True)
    spearman.to_csv(tables_dir / "spearman_correlations.csv", index=True)
    pd.DataFrame(profile["columns"]).to_csv(tables_dir / "column_profile.csv", index=False)
    class_conditionals.to_csv(tables_dir / "class_conditional_summaries.csv", index=False)

    figures = create_eda_figures(frame, figures_dir)
    summary: dict[str, Any] = {
        "report_version": "mission01-eda-v1",
        "data_classification": data_classification,
        "dataset_name": dataset_name,
        "provenance": provenance,
        "profile": profile,
        "dataset_diagnostics": diagnostics,
        "class_imbalance": imbalance,
        "amount_by_class": amounts.to_dict(orient="records"),
        "time_bins": time_bins.to_dict(orient="records"),
        "class_feature_associations": associations.to_dict(orient="records"),
        "iqr_outlier_diagnostics": outliers.to_dict(orient="records"),
        "correlation_methods": ["pearson", "spearman"],
        "strongest_predictor_correlations": {
            "pearson": _top_correlation_pairs(predictor_pearson),
            "spearman": _top_correlation_pairs(predictor_spearman),
        },
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
    source_verified = data_classification == "source_verified_file" and provenance is not None
    publisher_counts_verified = profile["row_count"] == 284_807 and imbalance["counts"] == {
        "0": 284_315,
        "1": 492,
    }
    if source_verified:
        status_blockers: list[str] = []
        real_data_status = "complete"
    elif data_classification == "synthetic_fixture":
        status_blockers = ["The real ULB CSV was not used."]
        real_data_status = "synthetic_fixture_only"
    else:
        status_blockers = ["Dataset source provenance was not verified."]
        real_data_status = "unverified"
    write_json(
        {
            "dataset": "ULB Credit Card Fraud Detection",
            "dataset_name": dataset_name,
            "data_classification": data_classification,
            "dataset_file_present": data_classification
            in {"source_verified_file", "unverified_local_file"},
            "local_row_count": profile["row_count"],
            "local_column_count": profile["column_count"],
            "local_class_distribution": imbalance["counts"],
            "real_data_eda_status": real_data_status,
            "blockers": status_blockers,
            "publisher_counts_verified_locally": publisher_counts_verified,
            "sha256": provenance.get("sha256") if source_verified else None,
        },
        summaries_dir / "eda_status.json",
    )
    _write_markdown_report(
        summary,
        amounts,
        time_bins,
        associations,
        outliers,
        root / "EDA_REPORT.md",
    )
    return to_jsonable(summary)


def _write_markdown_report(
    summary: dict[str, Any],
    amounts: pd.DataFrame,
    time_bins: pd.DataFrame,
    associations: pd.DataFrame,
    outliers: pd.DataFrame,
    path: Path,
) -> None:
    profile = summary["profile"]
    label = summary["data_classification"].upper()
    imbalance = summary["class_imbalance"]
    column_stats = {column["name"]: column.get("statistics", {}) for column in profile["columns"]}
    diagnostics = summary["dataset_diagnostics"]
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
        f"- Rows in exact duplicate groups: {diagnostics['duplicate_rows_in_groups']:,}",
        f"- Missing values: {sum(column['missing_count'] for column in profile['columns']):,}",
        "- Infinite values: "
        f"{sum(column.get('non_finite_count', 0) for column in profile['columns']):,}",
        f"- Numeric dtypes: {_format_dtype_counts(profile['columns'])}",
        f"- Time range: {column_stats.get('Time', {}).get('min')}–"
        f"{column_stats.get('Time', {}).get('max')} elapsed seconds",
        f"- Amount range: {column_stats.get('Amount', {}).get('min')}–"
        f"{column_stats.get('Amount', {}).get('max')} dataset units",
        f"- Schema validation: {'valid' if profile['schema_validation']['valid'] else 'invalid'} "
        f"({profile['schema_version']})",
        "",
        "### Provenance",
        "",
        *_provenance_lines(summary.get("provenance")),
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
        "A predict-all-legitimate rule would achieve the displayed accuracy while detecting "
        "none of the fraud cases (0% fraud recall). Accuracy alone is therefore misleading; "
        "Mission 02 should report precision-recall metrics and threshold-specific "
        "confusion counts.",
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
        "volume; bins with fewer than 30 fraud cases are marked low_fraud_count. Neither group "
        "should support strong rate comparisons.",
        "",
        _time_order_lines(diagnostics),
        "",
        "## PCA-derived feature analysis",
        "",
        "V1–V28 are anonymized PCA-derived numeric fields. Their values and associations are "
        "reported without assigning business meanings. The feature-label table below ranks "
        "Spearman associations by absolute magnitude; it is descriptive, not causal or a "
        "feature-selection result.",
        "",
        _markdown_table(associations[associations["feature"].isin(PCA_COLUMNS)].head(10)),
        "",
        "Class-conditional summaries for every numeric predictor are in "
        "tables/class_conditional_summaries.csv. The selected PCA figure shows density "
        "distributions for the four highest absolute Spearman-associated PCA fields; full "
        "feature ranges and quantiles are in tables/column_profile.csv.",
        "",
        "## Feature associations and outliers",
        "",
        "Selected numeric feature associations with the label use Spearman correlation, sorted "
        "by absolute coefficient. They are descriptive, may be unstable for rare labels, and do "
        "not establish causality.",
        "",
        _markdown_table(associations.head(10)),
        "",
        "The full Pearson and Spearman matrices are in tables/pearson_correlations.csv and "
        "tables/spearman_correlations.csv. High absolute correlations are descriptive and may "
        "reflect transformed or anonymized variables.",
        "",
        "Strongest off-diagonal predictor correlations by absolute magnitude (excluding Class):",
        "",
        _markdown_table(pd.DataFrame(summary["strongest_predictor_correlations"]["spearman"][:5])),
        "",
        _markdown_table(
            outliers.sort_values("outlier_pct", ascending=False).head(8)[
                ["feature", "outlier_count", "outlier_pct", "lower_fence", "upper_fence"]
            ]
        ),
        "",
        "The 1.5×IQR rule flags values outside each feature's quartile fences; it is an "
        "exploratory diagnostic, not a fraud definition. "
        f"{_amount_outlier_line(outliers)} No observations were removed. Fraudulent observations "
        "may be statistically unusual, but ordinary values can also be fraud.",
        "",
        "## Leakage-aware evaluation notes",
        "",
        _candidate_split_lines(summary["dataset_diagnostics"]),
        "",
        "Keep repeated exact rows in the same temporal partition by using the Time cutoffs above; "
        "this avoids exact duplicate copies crossing those candidate boundaries. Near-duplicate "
        "similarity was not assessed. Compare a chronological holdout with stratified random "
        "development validation as a secondary view. Fit imputation, scaling, feature selection, "
        "resampling, and calibration only inside training folds. Reserve the latest test period "
        "for one final evaluation and never use it for model or threshold selection.",
        "",
        "## Scientific limitations",
        "",
        "- PCA-derived V1–V28 values are anonymized and do not map directly to business concepts.",
        "- Predictions, estimated risk, anomaly scores, and confirmed historical labels are "
        "different quantities.",
        "- No model was trained in Mission 01.",
        "- Candidate 70/15/15 cutoffs are descriptive and have not been selected as a final split.",
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


def _class_conditional_summaries(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize each numeric predictor by observed class for descriptive review."""
    records: list[dict[str, Any]] = []
    predictors = [
        str(column) for column in frame.select_dtypes(include="number").columns if column != "Class"
    ]
    if "Class" not in frame:
        return pd.DataFrame(
            columns=[
                "feature",
                "class_label",
                "n",
                "mean",
                "median",
                "std",
                "q25",
                "q75",
                "min",
                "max",
            ]
        )
    for feature in predictors:
        for label, group in frame.groupby("Class", dropna=False, sort=True)[feature]:
            values = group.dropna().astype("float64")
            values = values.loc[np.isfinite(values)]
            records.append(
                {
                    "feature": feature,
                    "class_label": label,
                    "n": int(values.size),
                    "mean": float(values.mean()) if len(values) else None,
                    "median": float(values.median()) if len(values) else None,
                    "std": float(values.std()) if len(values) > 1 else None,
                    "q25": float(values.quantile(0.25)) if len(values) else None,
                    "q75": float(values.quantile(0.75)) if len(values) else None,
                    "min": float(values.min()) if len(values) else None,
                    "max": float(values.max()) if len(values) else None,
                }
            )
    return pd.DataFrame.from_records(records)


def _top_correlation_pairs(matrix: pd.DataFrame, limit: int = 5) -> list[dict[str, Any]]:
    """Return the strongest unique off-diagonal numeric feature pairs."""
    values = matrix.to_numpy(dtype="float64")
    row_indices, column_indices = np.where(np.triu(np.isfinite(values), k=1))
    pairs = [
        {
            "feature_a": str(matrix.index[row]),
            "feature_b": str(matrix.columns[column]),
            "correlation": float(values[row, column]),
            "absolute_correlation": float(abs(values[row, column])),
        }
        for row, column in zip(row_indices, column_indices, strict=True)
    ]
    return sorted(pairs, key=lambda record: record["absolute_correlation"], reverse=True)[:limit]


def _amount_outlier_line(outliers: pd.DataFrame) -> str:
    amount = outliers.loc[outliers["feature"] == "Amount"]
    if amount.empty:
        return "Amount IQR diagnostics are unavailable."
    record = amount.iloc[0]
    return (
        f"For Amount, the fences are {record['lower_fence']:.6g} and "
        f"{record['upper_fence']:.6g}, flagging {int(record['outlier_count']):,} rows "
        f"({record['outlier_pct']:.3f}%)."
    )


def _dataset_diagnostics(frame: pd.DataFrame) -> dict[str, Any]:
    """Collect exact duplicate and temporal ordering diagnostics without mutation."""
    diagnostics: dict[str, Any] = {
        "duplicate_rows_in_groups": int(frame.duplicated(keep=False).sum()),
        "duplicate_extra_rows_by_class": {},
        "dtype_counts": {
            str(key): int(value) for key, value in frame.dtypes.astype(str).value_counts().items()
        },
        "time_monotonic_increasing": None,
        "time_decrease_count": None,
        "time_unique_count": None,
        "candidate_time_splits": [],
    }
    if "Class" in frame:
        extras = frame.loc[frame.duplicated()].groupby("Class", dropna=False).size()
        diagnostics["duplicate_extra_rows_by_class"] = {
            str(label): int(count) for label, count in extras.items()
        }
    if TIME_COLUMN not in frame or frame.empty:
        return diagnostics

    time = pd.to_numeric(frame[TIME_COLUMN], errors="coerce")
    diagnostics["time_monotonic_increasing"] = bool(time.is_monotonic_increasing)
    diagnostics["time_decrease_count"] = int((time.diff() < 0).sum())
    diagnostics["time_unique_count"] = int(time.nunique(dropna=True))
    if "Class" not in frame or len(time.dropna()) != len(frame):
        return diagnostics

    sorted_time = time.sort_values(kind="stable").reset_index(drop=True)
    cutoffs = [
        float(sorted_time.iloc[min(int(len(frame) * fraction), len(frame) - 1)])
        for fraction in (0.70, 0.85)
    ]
    partitions = [
        ("train_candidate", time <= cutoffs[0]),
        ("validation_candidate", (time > cutoffs[0]) & (time <= cutoffs[1])),
        ("test_candidate", time > cutoffs[1]),
    ]
    for name, mask in partitions:
        part = frame.loc[mask]
        counts = part["Class"].value_counts().sort_index()
        diagnostics["candidate_time_splits"].append(
            {
                "name": name,
                "rows": int(len(part)),
                "class_counts": {str(label): int(count) for label, count in counts.items()},
                "time_min": float(part[TIME_COLUMN].min()) if len(part) else None,
                "time_max": float(part[TIME_COLUMN].max()) if len(part) else None,
            }
        )
    diagnostics["candidate_time_cutoffs"] = cutoffs
    diagnostics["cutoff_time_multiplicities"] = {
        str(cutoff): int((time == cutoff).sum()) for cutoff in cutoffs
    }
    return diagnostics


def _format_dtype_counts(columns: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for column in columns:
        dtype = column["dtype"]
        counts[dtype] = counts.get(dtype, 0) + 1
    return ", ".join(f"{count} {dtype}" for dtype, count in sorted(counts.items()))


def _provenance_lines(provenance: dict[str, Any] | None) -> list[str]:
    if not provenance:
        return [
            "No verified acquisition sidecar was supplied; treat source identity as unverified."
        ]
    schema = provenance.get("schema_validation", {})
    source_url = provenance.get("source_url", "")
    return [
        f"- Source: [{source_url or 'not recorded'}]({source_url})",
        f"- Dataset identifier: `{provenance.get('dataset_id', 'not recorded')}`",
        f"- Retrieved at (UTC): {provenance.get('retrieved_at_utc', 'not recorded')}",
        f"- File size: {int(provenance.get('file_size_bytes', 0)):,} bytes",
        f"- SHA-256: `{provenance.get('sha256', 'not recorded')}`",
        f"- Acquisition schema check: `{schema.get('schema_version', 'unknown')}`, "
        f"valid={schema.get('valid', False)}; the current file hash was verified before analysis.",
    ]


def _time_order_lines(diagnostics: dict[str, Any]) -> str:
    if diagnostics.get("time_monotonic_increasing") is None:
        return "Time ordering diagnostics are unavailable for this input."
    return (
        f"Time ordering check: monotonic_increasing={diagnostics['time_monotonic_increasing']}; "
        f"decreases={diagnostics['time_decrease_count']:,}; "
        f"unique Time values={diagnostics['time_unique_count']:,}. "
        "This is elapsed-time ordering, not a calendar timestamp."
    )


def _candidate_split_lines(diagnostics: dict[str, Any]) -> str:
    candidates = diagnostics.get("candidate_time_splits", [])
    cutoffs = diagnostics.get("candidate_time_cutoffs")
    if not candidates or not cutoffs:
        return "No candidate temporal split summary is available for this input."
    lines = [
        "A descriptive 70/15/15 chronological candidate was formed by selecting row-quantile "
        f"Time cutoffs {cutoffs[0]:g} and {cutoffs[1]:g} seconds, then keeping equal Time "
        "values together:",
        "",
        _markdown_table(
            pd.DataFrame(
                [
                    {
                        "candidate": item["name"],
                        "rows": item["rows"],
                        "Class 0": item["class_counts"].get("0", 0),
                        "Class 1": item["class_counts"].get("1", 0),
                        "Time min": item["time_min"],
                        "Time max": item["time_max"],
                    }
                    for item in candidates
                ]
            )
        ),
        "",
        "This is a split diagnostic only, not a trained or selected evaluation partition.",
    ]
    return "\n".join(lines)


def _format_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|")
