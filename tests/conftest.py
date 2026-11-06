"""Small controlled data fixture for unit tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fraud_detection.schema import EXPECTED_COLUMNS, PCA_COLUMNS


@pytest.fixture
def transaction_frame() -> pd.DataFrame:
    """Return an explicit, schema-compatible fixture with known edge cases."""
    rows = 12
    frame = pd.DataFrame({name: np.arange(rows, dtype=float) for name in PCA_COLUMNS})
    frame.insert(0, "Time", np.arange(rows, dtype=float) * 100)
    frame["Amount"] = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 1_000]
    frame["Class"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    return frame.loc[:, EXPECTED_COLUMNS]
