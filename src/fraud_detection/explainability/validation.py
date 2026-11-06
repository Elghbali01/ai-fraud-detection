"""Numerical checks for exact and SHAP explanation additivity."""

from __future__ import annotations

from typing import Any

import numpy as np


def validate_linear_reconstruction(
    intercept: float,
    contributions: np.ndarray,
    decision_function: np.ndarray,
    *,
    tolerance: float = 1e-10,
) -> dict[str, Any]:
    """Check that intercept plus exact linear contributions matches the raw logit."""
    values = np.asarray(contributions, dtype=np.float64)
    raw = np.asarray(decision_function, dtype=np.float64).reshape(-1)
    if values.ndim != 2 or values.shape[0] != len(raw):
        raise ValueError("Linear contributions must align with the decision function")
    errors = np.abs(float(intercept) + values.sum(axis=1) - raw)
    passed = bool(
        np.allclose(float(intercept) + values.sum(axis=1), raw, rtol=tolerance, atol=tolerance)
    )
    return {
        "passed": passed,
        "tolerance": float(tolerance),
        "maximum_absolute_error": float(errors.max(initial=0.0)),
        "mean_absolute_error": float(errors.mean()) if len(errors) else 0.0,
        "rows": int(len(raw)),
    }


def validate_shap_additivity(
    shap_values: np.ndarray,
    base_values: np.ndarray,
    model_output: np.ndarray,
    *,
    tolerance: float = 1e-7,
) -> dict[str, Any]:
    """Check that SHAP values reconstruct the documented model output space."""
    values = np.asarray(shap_values, dtype=np.float64)
    bases = np.asarray(base_values, dtype=np.float64).reshape(-1)
    output = np.asarray(model_output, dtype=np.float64).reshape(-1)
    if values.ndim != 2 or values.shape[0] != len(output) or len(bases) not in (1, len(output)):
        raise ValueError("SHAP values, bases, and model outputs must align")
    if len(bases) == 1 and len(output) != 1:
        bases = np.repeat(bases, len(output))
    reconstructed = bases + values.sum(axis=1)
    errors = np.abs(reconstructed - output)
    passed = bool(np.allclose(reconstructed, output, rtol=tolerance, atol=tolerance))
    return {
        "passed": passed,
        "tolerance": float(tolerance),
        "maximum_absolute_error": float(errors.max(initial=0.0)),
        "mean_absolute_error": float(errors.mean()) if len(errors) else 0.0,
        "rows": int(len(output)),
    }
