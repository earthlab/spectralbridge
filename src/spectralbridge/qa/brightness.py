"""Numerical diagnostics for the persisted brightness-correction step.

These helpers audit before/after products.  They do not apply, refit, or
otherwise change the correction coefficients used by the pipeline.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np


def brightness_correction_metrics(
    before: np.ndarray,
    after: np.ndarray,
    *,
    expected_percent: Mapping[int, float] | None = None,
) -> dict[str, Any]:
    """Summarize a bandwise multiplicative brightness correction.

    Parameters
    ----------
    before, after
        Matching band-first arrays in unit reflectance. Invalid cells must be
        represented by ``NaN`` before calling this function.
    expected_percent
        One-based band indices mapped to the configured percent adjustment.

    Returns
    -------
    dict
        Per-band fitted gains, intercepts, fit quality, quantiles, and the
        difference between fitted and configured gain.
    """

    before_values = np.asarray(before, dtype=np.float64)
    after_values = np.asarray(after, dtype=np.float64)
    if before_values.shape != after_values.shape:
        raise ValueError(
            "Brightness before/after arrays must have identical shapes; "
            f"got {before_values.shape} and {after_values.shape}."
        )
    if before_values.ndim < 2:
        raise ValueError("Brightness diagnostics require a band-first array.")

    expected = {
        int(key): float(value) for key, value in (expected_percent or {}).items()
    }
    rows: list[dict[str, Any]] = []
    for band_index in range(before_values.shape[0]):
        source = before_values[band_index].reshape(-1)
        corrected = after_values[band_index].reshape(-1)
        valid = np.isfinite(source) & np.isfinite(corrected)
        x = source[valid]
        y = corrected[valid]
        expected_adjustment = expected.get(band_index + 1)
        expected_gain = (
            1.0 + expected_adjustment / 100.0
            if expected_adjustment is not None
            else None
        )
        if x.size >= 2 and float(np.nanstd(x)) > 0:
            fitted_gain, fitted_intercept = np.polyfit(x, y, 1)
            predicted = fitted_gain * x + fitted_intercept
            residual_sum = float(np.sum((y - predicted) ** 2))
            total_sum = float(np.sum((y - np.mean(y)) ** 2))
            r_squared = 1.0 - residual_sum / total_sum if total_sum > 0 else 1.0
        elif x.size:
            fitted_gain = float(np.nanmedian(y / x)) if np.all(x != 0) else np.nan
            fitted_intercept = 0.0
            r_squared = None
        else:
            fitted_gain = fitted_intercept = np.nan
            r_squared = None
        rows.append(
            {
                "band_index": band_index + 1,
                "n": int(x.size),
                "expected_percent": expected_adjustment,
                "expected_gain": expected_gain,
                "fitted_gain": float(fitted_gain) if np.isfinite(fitted_gain) else None,
                "fitted_intercept": (
                    float(fitted_intercept) if np.isfinite(fitted_intercept) else None
                ),
                "gain_error": (
                    float(fitted_gain - expected_gain)
                    if expected_gain is not None and np.isfinite(fitted_gain)
                    else None
                ),
                "r_squared": float(r_squared) if r_squared is not None else None,
                "before_median": float(np.median(x)) if x.size else None,
                "after_median": float(np.median(y)) if y.size else None,
                "before_q05": float(np.quantile(x, 0.05)) if x.size else None,
                "before_q95": float(np.quantile(x, 0.95)) if x.size else None,
                "after_q05": float(np.quantile(y, 0.05)) if y.size else None,
                "after_q95": float(np.quantile(y, 0.95)) if y.size else None,
            }
        )

    errors = [abs(row["gain_error"]) for row in rows if row["gain_error"] is not None]
    return {
        "method": "bandwise_ordinary_least_squares_after_on_before",
        "data_modified": False,
        "bands": rows,
        "bands_evaluated": sum(row["fitted_gain"] is not None for row in rows),
        "bands_with_expected_coefficients": sum(
            row["expected_gain"] is not None for row in rows
        ),
        "maximum_absolute_gain_error": max(errors) if errors else None,
    }


__all__ = ["brightness_correction_metrics"]
