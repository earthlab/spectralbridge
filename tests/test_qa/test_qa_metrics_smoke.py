from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import spectralbridge.qa_plots as qa_plots
from spectralbridge.qa_plots import render_flightline_panel


def test_render_panel_writes_png_and_json(qa_fixture_dir: Path) -> None:
    png_path, metrics = render_flightline_panel(qa_fixture_dir, quick=True)
    json_path = png_path.with_suffix(".json")

    assert png_path.exists()
    assert json_path.exists()

    data = json.loads(json_path.read_text())
    assert data["provenance"]["flightline_id"] == qa_fixture_dir.name
    assert data["mask"]["valid_pct"] >= 0
    assert data["negatives_pct"] >= 0
    assert data["overbright_pct"] >= 0
    assert isinstance(metrics["header"]["n_bands"], int)
    assert len(data["correction"]["delta_median"]) == data["header"]["n_bands"]
    assert all(isinstance(idx, int) for idx in data["correction"]["largest_delta_indices"])
    assert "wavelength_source" in data["header"]


def test_metrics_arrays_are_serialisable(qa_fixture_dir: Path) -> None:
    _, metrics = render_flightline_panel(qa_fixture_dir, quick=True)
    correction = metrics["correction"]
    delta = np.array(correction["delta_median"], dtype=float)
    assert np.isfinite(delta).all()
    assert set(metrics.keys()) == {
        "provenance",
        "header",
        "mask",
        "correction",
        "convolution",
        "negatives_pct",
        "overbright_pct",
        "issues",
    }


def test_aop_qa_png_shows_raw_corrected_and_diagnostics(
    qa_fixture_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plt = pytest.importorskip("matplotlib.pyplot")

    captured: dict[str, object] = {}
    original_subplots = qa_plots.plt.subplots

    def _capture_subplots(*args, **kwargs):
        fig, axes = original_subplots(*args, **kwargs)
        if args[:2] == (2, 3) and "axes" not in captured:
            captured["fig"] = fig
            captured["axes"] = axes
        return fig, axes

    monkeypatch.setattr(qa_plots.plt, "subplots", _capture_subplots)
    monkeypatch.setattr(qa_plots.plt, "close", lambda fig=None: None)

    png_path, _ = render_flightline_panel(qa_fixture_dir, quick=True)

    assert png_path.exists()
    axes = captured["axes"]
    assert axes[0, 0].get_title().startswith("Original ENVI RGB")
    assert axes[0, 1].get_title().startswith("Corrected ENVI RGB")
    assert axes[0, 2].get_title() == "Pre vs Post Histograms"
    assert axes[1, 0].get_title() == "Correction Distribution By Wavelength"
    assert axes[1, 1].get_title() == "Convolved vs Corrected"
    assert axes[1, 2].get_title() == "QA Summary And Flags"

    plt.close(captured["fig"])
