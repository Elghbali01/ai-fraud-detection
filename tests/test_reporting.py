from __future__ import annotations

import json
import math

import numpy as np

from fraud_detection.reporting import generate_eda_artifacts
from fraud_detection.serialization import to_jsonable, write_json


def test_json_serialization_handles_numpy_and_nonfinite_values(tmp_path):
    path = write_json(
        {"integer": np.int64(2), "float": np.float64(1.5), "nan": float("nan")},
        tmp_path / "report.json",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload == {"float": 1.5, "integer": 2, "nan": None}
    assert math.isfinite(payload["float"])
    assert to_jsonable(np.array([np.int64(1), np.float64(np.inf)])) == [1, None]


def test_eda_report_contains_required_fields_tables_and_figures(transaction_frame, tmp_path):
    result = generate_eda_artifacts(
        transaction_frame,
        tmp_path,
        data_classification="synthetic_fixture",
        dataset_name="explicit test fixture",
    )
    summary_path = tmp_path / "summaries" / "eda_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["data_classification"] == "synthetic_fixture"
    assert summary["profile"]["row_count"] == len(transaction_frame)
    assert summary["class_imbalance"]["fraud_count"] == 1
    assert result["report_version"] == "mission01-eda-v1"
    assert (tmp_path / "EDA_REPORT.md").is_file()
    assert "not a ULB dataset result" in (tmp_path / "EDA_REPORT.md").read_text(encoding="utf-8")
    assert (tmp_path / "tables" / "amounts_by_class.csv").is_file()
    assert (tmp_path / "tables" / "iqr_outlier_diagnostics.csv").is_file()
    assert (tmp_path / "figures" / "class_distribution.png").is_file()


def test_eda_report_marks_unverified_input_and_finite_json(transaction_frame, tmp_path):
    generate_eda_artifacts(transaction_frame, tmp_path)
    payload = (tmp_path / "summaries" / "eda_summary.json").read_text(encoding="utf-8")

    assert '"data_classification": "unverified_input_frame"' in payload
    assert "source provenance was not verified" in (tmp_path / "EDA_REPORT.md").read_text(
        encoding="utf-8"
    )
    assert "NaN" not in payload
