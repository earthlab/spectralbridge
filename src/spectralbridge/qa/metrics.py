"""Reusable deterministic numerical diagnostics for scientific QA."""

from __future__ import annotations

from typing import Any

import numpy as np


def _finite_values(values: np.ndarray, nodata: float | None = None) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    valid = np.isfinite(arr)
    if nodata is not None:
        if np.isnan(nodata):
            valid &= ~np.isnan(arr)
        else:
            valid &= ~np.isclose(arr, float(nodata), atol=1e-6)
    return arr[valid]


def reflectance_summary(
    values: np.ndarray,
    *,
    nodata: float | None = None,
    plausible_max: float = 1.2,
) -> dict[str, float | int | None]:
    """Summarize valid support and distribution without changing reflectance scale."""

    arr = np.asarray(values, dtype=np.float64)
    finite = _finite_values(arr, nodata)
    total = int(arr.size)
    valid_count = int(finite.size)
    valid_fraction = float(valid_count / total) if total else 0.0
    if valid_count == 0:
        return {
            "n_total": total,
            "n_valid": 0,
            "valid_fraction": valid_fraction,
            "missing_fraction": 1.0 if total else 0.0,
            "q01": None,
            "q05": None,
            "q50": None,
            "q95": None,
            "q99": None,
            "minimum": None,
            "maximum": None,
            "negative_fraction": None,
            "overbright_fraction": None,
        }
    quantiles = np.quantile(finite, [0.01, 0.05, 0.5, 0.95, 0.99])
    return {
        "n_total": total,
        "n_valid": valid_count,
        "valid_fraction": valid_fraction,
        "missing_fraction": float(1.0 - valid_fraction),
        "q01": float(quantiles[0]),
        "q05": float(quantiles[1]),
        "q50": float(quantiles[2]),
        "q95": float(quantiles[3]),
        "q99": float(quantiles[4]),
        "minimum": float(np.min(finite)),
        "maximum": float(np.max(finite)),
        "negative_fraction": float(np.mean(finite < 0)),
        "overbright_fraction": float(np.mean(finite > plausible_max)),
    }


def linear_diagnostic(x: np.ndarray, y: np.ndarray) -> dict[str, float | int | None]:
    """Fit ``y = intercept + slope*x`` for diagnostic, not inferential, use."""

    x_arr = np.asarray(x, dtype=np.float64).reshape(-1)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_valid = x_arr[valid]
    y_valid = y_arr[valid]
    n = int(x_valid.size)
    if n < 3 or float(np.ptp(x_valid)) == 0.0:
        return {
            "n": n,
            "slope": None,
            "intercept": None,
            "correlation": None,
            "r2": None,
            "rmse": None,
        }
    design = np.column_stack([np.ones(n, dtype=np.float64), x_valid])
    intercept, slope = np.linalg.lstsq(design, y_valid, rcond=None)[0]
    predicted = intercept + slope * x_valid
    residual = y_valid - predicted
    correlation = float(np.corrcoef(x_valid, y_valid)[0, 1])
    return {
        "n": n,
        "slope": float(slope),
        "intercept": float(intercept),
        "correlation": correlation,
        "r2": float(correlation**2),
        "rmse": float(np.sqrt(np.mean(residual**2))),
    }


def residual_metrics(
    observed: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, float | int | None]:
    """Return held-out-style residual metrics for paired observations."""

    obs = np.asarray(observed, dtype=np.float64).reshape(-1)
    pred = np.asarray(predicted, dtype=np.float64).reshape(-1)
    valid = np.isfinite(obs) & np.isfinite(pred)
    obs = obs[valid]
    pred = pred[valid]
    n = int(obs.size)
    if n == 0:
        return {
            "n": 0,
            "bias": None,
            "mae": None,
            "rmse": None,
            "ub_rmse": None,
            "r2": None,
            "slope": None,
            "intercept": None,
        }
    residual = pred - obs
    bias = float(np.mean(residual))
    diagnostic = linear_diagnostic(obs, pred)
    return {
        "n": n,
        "bias": bias,
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "ub_rmse": float(np.sqrt(np.mean((residual - bias) ** 2))),
        "r2": diagnostic["r2"],
        "slope": diagnostic["slope"],
        "intercept": diagnostic["intercept"],
    }


def _as_band_first(image: np.ndarray) -> np.ndarray:
    arr = np.asarray(image, dtype=np.float64)
    if arr.ndim == 2:
        return arr[np.newaxis, ...]
    if arr.ndim != 3:
        raise ValueError("image must be 2D or 3D")
    # SpectralBridge ENVI arrays are band-first. For small test/consumer arrays,
    # accept band-last when the final axis is clearly the smallest dimension.
    if arr.shape[-1] < arr.shape[0] and arr.shape[-1] < arr.shape[1]:
        return np.moveaxis(arr, -1, 0)
    return arr


def seam_score(
    image: np.ndarray,
    *,
    chunk_rows: int,
    chunk_cols: int,
    nodata: float | None = None,
) -> dict[str, Any]:
    """Compare gradients crossing chunk boundaries with interior neighbors.

    A score near one means chunk boundaries are not unusually discontinuous.
    Scores above one require interpretation because genuine landscape edges can
    coincide with a computational boundary.
    """

    if chunk_rows < 1 or chunk_cols < 1:
        raise ValueError("chunk_rows and chunk_cols must be positive")
    cube = _as_band_first(image)
    _, rows, cols = cube.shape
    vertical = np.abs(np.diff(cube, axis=1))
    horizontal = np.abs(np.diff(cube, axis=2))
    vertical_boundary = np.zeros(rows - 1, dtype=bool)
    horizontal_boundary = np.zeros(cols - 1, dtype=bool)
    vertical_boundary[np.arange(chunk_rows - 1, rows - 1, chunk_rows)] = True
    horizontal_boundary[np.arange(chunk_cols - 1, cols - 1, chunk_cols)] = True

    band_results: list[dict[str, float | int | None]] = []
    for band_index in range(cube.shape[0]):
        boundary_values = np.concatenate(
            [
                vertical[band_index, vertical_boundary, :].reshape(-1),
                horizontal[band_index, :, horizontal_boundary].reshape(-1),
            ]
        )
        interior_values = np.concatenate(
            [
                vertical[band_index, ~vertical_boundary, :].reshape(-1),
                horizontal[band_index, :, ~horizontal_boundary].reshape(-1),
            ]
        )
        boundary_values = _finite_values(boundary_values, nodata)
        interior_values = _finite_values(interior_values, nodata)
        boundary_median = (
            float(np.median(boundary_values)) if boundary_values.size else None
        )
        interior_median = (
            float(np.median(interior_values)) if interior_values.size else None
        )
        score = None
        if boundary_median is not None and interior_median not in {None, 0.0}:
            score = float(boundary_median / interior_median)
        band_results.append(
            {
                "band_index": band_index,
                "boundary_n": int(boundary_values.size),
                "interior_n": int(interior_values.size),
                "boundary_median_abs_gradient": boundary_median,
                "interior_median_abs_gradient": interior_median,
                "seam_score": score,
            }
        )
    valid_scores = [
        float(item["seam_score"])
        for item in band_results
        if item["seam_score"] is not None
    ]
    return {
        "chunk_rows": int(chunk_rows),
        "chunk_cols": int(chunk_cols),
        "bands": band_results,
        "median_seam_score": float(np.median(valid_scores)) if valid_scores else None,
        "p95_seam_score": float(np.quantile(valid_scores, 0.95))
        if valid_scores
        else None,
        "max_seam_score": float(np.max(valid_scores)) if valid_scores else None,
    }


def chunk_invariance_metrics(
    baseline: np.ndarray,
    candidate: np.ndarray,
    *,
    tolerance: float = 1e-6,
) -> dict[str, float | int | None]:
    """Compare two outputs that should be scientifically identical."""

    a = np.asarray(baseline, dtype=np.float64)
    b = np.asarray(candidate, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(f"chunk outputs must share shape; got {a.shape} and {b.shape}")
    valid = np.isfinite(a) & np.isfinite(b)
    diff = np.abs(a[valid] - b[valid])
    if diff.size == 0:
        return {
            "n": 0,
            "max_abs_difference": None,
            "median_abs_difference": None,
            "rmse": None,
            "p95_abs_difference": None,
            "p99_abs_difference": None,
            "fraction_exceeding_tolerance": None,
            "tolerance": float(tolerance),
        }
    signed = a[valid] - b[valid]
    return {
        "n": int(diff.size),
        "max_abs_difference": float(np.max(diff)),
        "median_abs_difference": float(np.median(diff)),
        "rmse": float(np.sqrt(np.mean(signed**2))),
        "p95_abs_difference": float(np.quantile(diff, 0.95)),
        "p99_abs_difference": float(np.quantile(diff, 0.99)),
        "fraction_exceeding_tolerance": float(np.mean(diff > tolerance)),
        "tolerance": float(tolerance),
    }


def spectral_response_support(
    source_wavelengths: np.ndarray,
    response: np.ndarray,
    *,
    valid_source_mask: np.ndarray | None = None,
) -> dict[str, float | int | None]:
    """Quantify SRF normalization and support on available source wavelengths."""

    wavelengths = np.asarray(source_wavelengths, dtype=np.float64).reshape(-1)
    weights = np.asarray(response, dtype=np.float64).reshape(-1)
    if wavelengths.shape != weights.shape:
        raise ValueError("source_wavelengths and response must have the same shape")
    finite = np.isfinite(wavelengths) & np.isfinite(weights) & (weights >= 0)
    if valid_source_mask is not None:
        supplied = np.asarray(valid_source_mask, dtype=bool).reshape(-1)
        if supplied.shape != weights.shape:
            raise ValueError("valid_source_mask must match response shape")
    else:
        supplied = finite.copy()
    total_weight = float(np.sum(weights[finite]))
    valid_weight = float(np.sum(weights[finite & supplied]))
    effective_wavelength = None
    if total_weight > 0:
        effective_wavelength = float(
            np.sum(wavelengths[finite] * weights[finite]) / total_weight
        )
    return {
        "srf_weight_sum": total_weight,
        "effective_wavelength_nm": effective_wavelength,
        "valid_coverage_fraction": (
            float(valid_weight / total_weight) if total_weight > 0 else None
        ),
        "valid_source_wavelengths": int(np.count_nonzero(finite & supplied)),
        "source_wavelengths": int(np.count_nonzero(finite)),
    }


__all__ = [
    "chunk_invariance_metrics",
    "linear_diagnostic",
    "reflectance_summary",
    "residual_metrics",
    "seam_score",
    "spectral_response_support",
]
