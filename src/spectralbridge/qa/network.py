"""Diagnostics for empirical sensor translations and translation networks.

These functions evaluate supplied predictions. They do not fit translation
models and therefore cannot accidentally turn in-sample fits into validation
evidence.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np

from .metrics import residual_metrics


def translation_edge_metrics(
    observed: np.ndarray,
    predicted: np.ndarray,
) -> dict[str, float | int | None]:
    """Evaluate one sensor-to-sensor edge from paired held-out observations.

    Parameters
    ----------
    observed : np.ndarray
        Paired measured/reference and predicted values in common units; nonfinite pairs are omitted and residuals are predicted minus observed.
    predicted : np.ndarray
        Paired measured/reference and predicted values in common units; nonfinite pairs are omitted and residuals are predicted minus observed.

    Returns
    -------
    dict[str, float | int | None]
        Paired residual metrics in the target units; high R-squared alone does not certify interchangeability.

    See Also
    --------
    spectralbridge.qa.metrics.reflectance_summary : Related source-derived API contract.
    """

    return residual_metrics(observed, predicted)


def grouped_residual_metrics(
    observed: np.ndarray,
    predicted: np.ndarray,
    groups: Iterable[Any],
) -> dict[str, Any]:
    """Return residual metrics by an explicit validation block.

    Parameters
    ----------
    observed : np.ndarray
        Paired measured/reference and predicted values in common units; nonfinite pairs are omitted and residuals are predicted minus observed.
    predicted : np.ndarray
        Paired measured/reference and predicted values in common units; nonfinite pairs are omitted and residuals are predicted minus observed.
    groups : Iterable[Any]
        Aligned independent-unit identifiers; keep repeated observations or parent-connected mixtures in the same group. None uses the function-specific row-based convention described in Notes.

    Returns
    -------
    dict[str, Any]
        Explicit per-group residual summaries and an overall paired summary; the supplied group variable is not independently validated.

    Raises
    ------
    ValueError
        If the supplied options, dimensions, support or provenance violate the input contract.

    Notes
    -----
    ``groups`` should identify held-out sites, dates, campaigns, or flightlines.
    The function reports, but does not invent, the blocking strategy.

    See Also
    --------
    spectralbridge.qa.metrics.reflectance_summary : Related source-derived API contract.
    """

    obs = np.asarray(observed).reshape(-1)
    pred = np.asarray(predicted).reshape(-1)
    group_values = np.asarray(list(groups), dtype=object).reshape(-1)
    if not (obs.size == pred.size == group_values.size):
        raise ValueError("observed, predicted, and groups must have equal length")
    rows = []
    for group in sorted(set(group_values.tolist()), key=str):
        selected = group_values == group
        rows.append(
            {
                "group": str(group),
                "metrics": residual_metrics(obs[selected], pred[selected]),
            }
        )
    return {
        "blocking_variable_supplied": True,
        "groups": rows,
        "overall": residual_metrics(obs, pred),
    }


def path_consistency_metrics(
    direct_prediction: np.ndarray,
    indirect_prediction: np.ndarray,
    *,
    observed_target: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compare a direct translation with a multi-edge translation path.

    Parameters
    ----------
    direct_prediction : np.ndarray
        Matched target-sensor predictions from direct and multi-edge translation paths, in common units and row order.
    indirect_prediction : np.ndarray
        Matched target-sensor predictions from direct and multi-edge translation paths, in common units and row order.
    observed_target : np.ndarray | None, default=None
        Optional independently observed target values for residual summaries of each translation path.

    Returns
    -------
    dict[str, Any]
        Direct-versus-indirect residual summary and optional each-path residuals against observed_target.

    See Also
    --------
    spectralbridge.qa.metrics.reflectance_summary : Related source-derived API contract.
    """

    payload: dict[str, Any] = {
        "indirect_relative_to_direct": residual_metrics(
            direct_prediction, indirect_prediction
        )
    }
    if observed_target is not None:
        payload["direct_relative_to_observed"] = residual_metrics(
            observed_target, direct_prediction
        )
        payload["indirect_relative_to_observed"] = residual_metrics(
            observed_target, indirect_prediction
        )
    return payload


def cycle_consistency_metrics(
    starting_values: np.ndarray,
    cycled_values: np.ndarray,
) -> dict[str, float | int | None]:
    """Measure drift after translating around a sensor cycle back to its start.

    Parameters
    ----------
    starting_values : np.ndarray
        Matched values before and after a translation cycle, expressed on the starting sensor support and scale.
    cycled_values : np.ndarray
        Matched values before and after a translation cycle, expressed on the starting sensor support and scale.

    Returns
    -------
    dict[str, float | int | None]
        Residual drift metrics comparing returned-cycle values with starting values in their common units.

    See Also
    --------
    spectralbridge.qa.metrics.reflectance_summary : Related source-derived API contract.
    """

    return residual_metrics(starting_values, cycled_values)


__all__ = [
    "cycle_consistency_metrics",
    "grouped_residual_metrics",
    "path_consistency_metrics",
    "translation_edge_metrics",
]
