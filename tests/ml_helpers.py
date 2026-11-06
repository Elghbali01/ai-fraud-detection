"""Small schema-complete synthetic transactions for Mission 02 unit tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from fraud_detection.schema import EXPECTED_COLUMNS, PCA_COLUMNS


def make_transaction_frame(rows: int = 120, *, seed: int = 31) -> pd.DataFrame:
    """Build deterministic mixed-class rows in tied, ordered time groups."""
    if rows % 2:
        raise ValueError("rows must be even so each synthetic timestamp has a pair")
    rng = np.random.default_rng(seed)
    frame = pd.DataFrame({column: rng.normal(size=rows) for column in PCA_COLUMNS})
    frame.insert(0, "Time", np.repeat(np.arange(rows // 2, dtype=np.float64), 2))
    frame["Amount"] = np.abs(rng.normal(loc=25, scale=12, size=rows))
    frame["Class"] = (np.arange(rows) % 7 == 0).astype("int64")
    return frame.loc[:, EXPECTED_COLUMNS]
