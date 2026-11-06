"""Explicit data source selection shared by the Mission 01 notebooks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from fraud_detection.demo import make_synthetic_ulb_fixture
from fraud_detection.loading import load_ulb_csv
from fraud_detection.provenance import has_verified_kaggle_provenance


def load_notebook_frame(
    dataset_path: str | Path | None = None,
) -> tuple[pd.DataFrame, str]:
    """Load a project data file or return an explicitly labeled smoke fixture."""
    root = Path(__file__).resolve().parents[2]
    source = (
        root / "data" / "raw" / "creditcard.csv" if dataset_path is None else Path(dataset_path)
    )
    if not source.is_absolute():
        source = root / source
    if source.is_file():
        status = (
            "source_verified_file"
            if has_verified_kaggle_provenance(source)
            else "unverified_local_file"
        )
        return load_ulb_csv(source), status
    return make_synthetic_ulb_fixture(), "synthetic_fixture"
