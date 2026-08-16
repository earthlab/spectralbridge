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
    """Evaluate one sensor-to-sensor edge from paired held-out observations."""

    return residual_metrics(observed, predicted)


def grouped_residual_metrics(
    observed: np.ndarray,
    predicted: np.ndarray,
    groups: Iterable[Any],
) -> dict[str, Any]:
    """Return residual metrics by an explicit validation block.

    ``groups`` should identify held-out sites, dates, campaigns, or flightlines.
    The function reports, but does not invent, the blocking strategy.
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
    """Compare a direct translation with a multi-edge translation path."""

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
    """Measure drift after translating around a sensor cycle back to its start."""

    return residual_metrics(starting_values, cycled_values)


__all__ = [
    "cycle_consistency_metrics",
    "grouped_residual_metrics",
    "path_consistency_metrics",
    "translation_edge_metrics",
]
