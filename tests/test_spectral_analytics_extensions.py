"""Threshold and checkpoint contracts for secondary audit diagnostics."""

import numpy as np
import pytest

pytest.importorskip("sklearn", reason="optional analytics extra")
from spectralbridge.spectral_analytics_extensions import (  # noqa: E402
    novelty_threshold,
    unknown_metrics,
    checkpoint,
)


def test_known_threshold_clusters_before_quantile():
    assert novelty_threshold([1, 10, 2, 3], ["a", "a", "b", "c"], 0.5) == 3
    with pytest.raises(ValueError):
        novelty_threshold([np.nan], ["a"])


def test_unknown_detection_distinguishes_recall_and_false_rejection():
    result = unknown_metrics([False, False, True, True], [0, 2, 3, 1], 1)
    assert result["known_false_rejection"] == 0.5
    assert result["unknown_recall"] == 0.5
    assert result["unknown_precision"] == 0.5
    assert result["unknown_average_precision"] == pytest.approx(5 / 6)


def test_checkpoint_no_rewrite_and_corruption(tmp_path):
    calls = []

    def action(path):
        calls.append(1)
        (path / "result.txt").write_text("evidence")

    checkpoint(tmp_path, {"seed": 1}, action)
    timestamp = (tmp_path / "manifest.json").stat().st_mtime_ns
    checkpoint(tmp_path, {"seed": 1}, action)
    assert calls == [1]
    assert (tmp_path / "manifest.json").stat().st_mtime_ns == timestamp
    (tmp_path / "result.txt").write_text("changed")
    with pytest.raises(ValueError, match="Altered"):
        checkpoint(tmp_path, {"seed": 1}, action)
