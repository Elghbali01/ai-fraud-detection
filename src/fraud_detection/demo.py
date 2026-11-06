"""Deterministic synthetic fixtures for tests and pipeline smoke checks only."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_detection.schema import EXPECTED_COLUMNS, PCA_COLUMNS


def make_synthetic_ulb_fixture(*, row_count: int = 200, random_state: int = 42) -> pd.DataFrame:
    """Create a small schema-compatible fixture; values do not represent real fraud data."""
    if row_count < 10:
        raise ValueError("row_count must be at least 10")
    rng = np.random.default_rng(random_state)
    frame = pd.DataFrame({name: rng.normal(size=row_count) for name in PCA_COLUMNS})
    frame.insert(0, "Time", np.sort(rng.uniform(0, 172_800, size=row_count)))
    frame["Amount"] = rng.lognormal(mean=3.0, sigma=1.0, size=row_count)
    frame["Class"] = np.zeros(row_count, dtype="int64")
    fraud_indices = np.arange(max(1, row_count // 50))
    frame.loc[fraud_indices, "Class"] = 1
    frame.loc[fraud_indices, "V1"] += 2.5
    frame.loc[fraud_indices, "Amount"] *= 2.0
    return frame.loc[:, EXPECTED_COLUMNS]
