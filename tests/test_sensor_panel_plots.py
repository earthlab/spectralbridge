from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from spectralbridge import sensor_panel_plots


def _write_synthetic_sensor_parquet(path: Path) -> None:
    x_values = np.linspace(0.05, 0.45, 40, dtype=np.float64)
    frame = pd.DataFrame(
        {
            "MicaSense_to-match_OLI_and_OLI-2_band_1": x_values,
            "Landsat_8_OLI_band_1": 1.75 * x_values + 0.04,
        }
    )
    con = duckdb.connect()
    try:
        con.register("synthetic_sensor_rows", frame)
        con.execute(
            f"COPY synthetic_sensor_rows TO '{path.as_posix()}' (FORMAT PARQUET)"
        )
    finally:
        con.close()


def test_regression_metrics_report_plotted_coefficients() -> None:
    x_values = np.linspace(0.0, 1.0, 20)
    y_values = 1.75 * x_values + 0.04

    metrics = sensor_panel_plots._regression_metrics(x_values, y_values)

    assert metrics["slope"] == pytest.approx(1.75)
    assert metrics["intercept"] == pytest.approx(0.04)
    assert metrics["correlation"] == pytest.approx(1.0)
    assert metrics["r2"] == pytest.approx(1.0)
    assert metrics["sample_count"] == 20


def test_synthetic_sensor_panel_writes_deterministic_coefficient_sidecar(
    tmp_path: Path,
) -> None:
    parquet_path = tmp_path / "flight_merged_pixel_extraction.parquet"
    output_dir = tmp_path / "qa_plots"
    _write_synthetic_sensor_parquet(parquet_path)

    outputs = sensor_panel_plots.make_micasense_vs_landsat_panels(
        tmp_path,
        out_dir=output_dir,
        max_points=16,
    )

    assert len(outputs) == 1
    plot_path = outputs[0]
    sidecar_path = plot_path.with_suffix(".json")
    assert plot_path.is_file()
    assert plot_path.stat().st_size > 0
    assert sidecar_path.is_file()

    first_bytes = sidecar_path.read_bytes()
    payload = json.loads(first_bytes)
    assert payload["diagnostic"] == "synthetic_sensor_linear_regression"
    assert "not empirical sensor calibration" in payload["evidence_boundary"]
    assert payload["sampling"]["seed"] == 20260817
    assert len(payload["regressions"]) == 1
    regression = payload["regressions"][0]
    assert regression["slope"] == pytest.approx(1.75)
    assert regression["intercept"] == pytest.approx(0.04)
    assert regression["correlation"] == pytest.approx(1.0)
    assert regression["r2"] == pytest.approx(1.0)
    assert regression["sample_count"] == 16

    sensor_panel_plots.make_micasense_vs_landsat_panels(
        tmp_path,
        out_dir=output_dir,
        max_points=16,
    )
    assert sidecar_path.read_bytes() == first_bytes
