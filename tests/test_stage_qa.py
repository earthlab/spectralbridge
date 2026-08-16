from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import spectralbridge.qa.plots as qa_plots
import spectralbridge.qa.reporting as qa_reporting
import spectralbridge.qa.runner as qa_runner
import spectralbridge.qa.stages as qa_stages
from spectralbridge.qa import (
    QAStatus,
    QAThresholds,
    assemble_combined_report,
    brightness_correction_metrics,
    chunk_invariance_metrics,
    cycle_consistency_metrics,
    emit_stage_qa,
    grouped_residual_metrics,
    path_consistency_metrics,
    residual_metrics,
    seam_score,
    spectral_response_support,
)
from spectralbridge.qa.paths import CombinedQAPaths, StageQAPaths
from spectralbridge.qa.plots import (
    STANDARD_BRIGHTNESS_PERCENT_RANGE,
    STANDARD_CORRECTION_DIFFERENCE_RANGE,
    STANDARD_NEGATIVE_FRACTION_RANGE,
    STANDARD_REFLECTANCE_RANGE,
    STANDARD_SEAM_SCORE_RANGE,
    STANDARD_VALID_FRACTION_RANGE,
    STANDARD_WAVELENGTH_RANGE_NM,
    format_location_label,
    qa_plot_contract,
    spatial_plot_context,
)
from spectralbridge.qa.thresholds import classify_high_bad, classify_low_bad


def _qa_fixture(tmp_path: Path) -> Path:
    stem = "NEON_TEST_FLIGHT"
    flight_dir = tmp_path / stem
    flight_dir.mkdir()
    rng = np.random.default_rng(42)
    raw = 0.2 + rng.random((4, 12, 10)).astype(np.float32) * 0.05
    corrected = raw * 0.92 + 0.01
    wavelengths = [490.0, 560.0, 660.0, 820.0]
    for suffix, data in (
        ("_envi", raw),
        ("_brdfandtopo_corrected_envi", corrected),
    ):
        base = flight_dir / f"{stem}{suffix}"
        data.tofile(base.with_suffix(".img"))
        base.with_suffix(".hdr").write_text(
            "\n".join(
                [
                    "ENVI",
                    f"samples = {data.shape[2]}",
                    f"lines = {data.shape[1]}",
                    f"bands = {data.shape[0]}",
                    "data type = 4",
                    "interleave = bsq",
                    "byte order = 0",
                    "wavelength units = Nanometers",
                    "wavelength = {" + ", ".join(map(str, wavelengths)) + "}",
                ]
            ),
            encoding="utf-8",
        )
    return flight_dir


def _write_scaled_fixture(tmp_path: Path) -> Path:
    flight_dir = tmp_path / "NEON_SCALED_FLIGHT"
    flight_dir.mkdir()
    data = np.array([[[2000.0, -9999.0], [4000.0, 8000.0]]], dtype=np.float32)
    base = flight_dir / f"{flight_dir.name}_envi"
    data.tofile(base.with_suffix(".img"))
    base.with_suffix(".hdr").write_text(
        "\n".join(
            [
                "ENVI",
                "samples = 2",
                "lines = 2",
                "bands = 1",
                "data type = 4",
                "interleave = bsq",
                "byte order = 0",
                "reflectance scale factor = 10000",
                "data ignore value = -9999",
                "wavelength = {660}",
                "map info = {UTM, 1, 1, 500000, 4420000, 1, 1, 13, North}",
            ]
        ),
        encoding="utf-8",
    )
    return flight_dir


def _write_retained_bad_band_fixture(tmp_path: Path) -> Path:
    flight_dir = tmp_path / "NEON_RETAINED_BAD_BANDS"
    flight_dir.mkdir()
    data = np.array(
        [
            [[0.20, 0.21], [0.22, 0.23]],
            [[1.4998, 1.4998], [1.4998, 1.4998]],
            [[1.4998, 1.4998], [1.4998, 1.4998]],
        ],
        dtype=np.float32,
    )
    base = flight_dir / f"{flight_dir.name}_envi"
    data.tofile(base.with_suffix(".img"))
    base.with_suffix(".hdr").write_text(
        "\n".join(
            [
                "ENVI",
                "samples = 2",
                "lines = 2",
                "bands = 3",
                "data type = 4",
                "interleave = bsq",
                "byte order = 0",
                "wavelength = {660, 1380, 1880}",
            ]
        ),
        encoding="utf-8",
    )
    return flight_dir


def test_stage_qa_paths_are_deterministic(tmp_path: Path) -> None:
    first = StageQAPaths(tmp_path, "BRDF topographic correction")
    second = StageQAPaths(tmp_path, "brdf_topographic_correction")

    assert first.json == second.json
    assert first.json == (
        tmp_path / "qa" / "stages" / "03_brdf_topographic_correction" / "stage_qa.json"
    )
    assert CombinedQAPaths(tmp_path).html == (
        tmp_path / "qa" / "combined" / "combined_qa.html"
    )


def test_plot_contract_has_fixed_ranges_and_location_labels() -> None:
    contract = qa_plot_contract()
    assert contract["version"] == "1.1"
    assert contract["display_only"] is True
    assert contract["values_outside_limits_retained_in_metrics"] is True
    assert contract["wavelength_nm"] == [350.0, 2600.0]
    assert contract["reflectance"] == [-0.1, 1.6]
    assert contract["brightness_adjustment_percent"] == [-15.0, 5.0]
    assert (
        format_location_label(
            "NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance"
        )
        == "R10C · D10 · L002 · 2021-09-15"
    )


def test_spatial_plot_context_uses_envi_map_coordinates() -> None:
    context = spatial_plot_context(
        {
            "map info": [
                "UTM",
                "1",
                "1",
                "500000",
                "4420000",
                "1",
                "1",
                "13",
                "North",
            ]
        },
        (4, 3, 4),
    )

    assert context["mode"] == "projected_map_coordinates"
    assert context["extent"] == [499999.5, 500003.5, 4419997.5, 4420000.5]
    assert context["x_label"] == "Easting (m)"
    assert context["y_label"] == "Northing (m)"
    assert context["coordinate_system"] == "UTM zone 13 North"


def test_envi_overview_embeds_location_and_standardizes_axes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cube = np.full((3, 4, 5), 0.2, dtype=np.float32)
    wavelengths = np.array([490.0, 560.0, 660.0])
    spatial = {
        "mode": "projected_map_coordinates",
        "extent": [500000.0, 500005.0, 4419996.0, 4420000.0],
        "x_label": "Easting (m)",
        "y_label": "Northing (m)",
        "coordinate_system": "UTM zone 13 North",
    }
    original_close = qa_plots.plt.close
    monkeypatch.setattr(qa_plots.plt, "close", lambda figure: None)

    qa_plots.render_envi_overview(
        cube,
        wavelengths,
        tmp_path / "overview.png",
        title="Input reflectance",
        location_label="R10C · D10 · L002 · 2021-09-15",
        spatial_context=spatial,
    )

    figure = qa_plots.plt.gcf()
    spectral_axis = next(
        axis for axis in figure.axes if axis.get_title() == "Spectral distribution"
    )
    rgb_axis = next(axis for axis in figure.axes if axis.get_title().startswith("RGB"))
    assert spectral_axis.get_xlim() == STANDARD_WAVELENGTH_RANGE_NM
    assert spectral_axis.get_ylim() == STANDARD_REFLECTANCE_RANGE
    assert rgb_axis.get_xlabel() == "Easting (m)"
    assert rgb_axis.get_ylabel() == "Northing (m)"
    assert "Location: R10C · D10 · L002" in figure._suptitle.get_text()
    original_close(figure)


def test_correction_overview_uses_fixed_map_and_diagnostic_scales(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = np.full((3, 4, 5), 0.2, dtype=np.float32)
    corrected = raw + 0.001
    wavelengths = np.array([490.0, 660.0, 820.0])
    spatial = {
        "mode": "sampled_pixel_coordinates",
        "extent": None,
        "x_label": "Sampled column",
        "y_label": "Sampled row",
        "coordinate_system": None,
    }
    original_close = qa_plots.plt.close
    monkeypatch.setattr(qa_plots.plt, "close", lambda figure: None)

    qa_plots.render_correction_overview(
        raw,
        corrected,
        wavelengths,
        None,
        None,
        tmp_path / "correction.png",
        location_label="R10C · D10 · L002 · 2021-09-15",
        spatial_context=spatial,
    )

    figure = qa_plots.plt.gcf()
    correction_axis = next(
        axis
        for axis in figure.axes
        if axis.get_title() == "Median correction by wavelength"
    )
    seam_axis = next(
        axis for axis in figure.axes if axis.get_title() == "Chunk seam score"
    )
    before_axis = next(
        axis for axis in figure.axes if axis.get_title().startswith("Before:")
    )
    difference_axis = next(
        axis for axis in figure.axes if axis.get_title().startswith("After − before")
    )
    assert correction_axis.get_xlim() == STANDARD_WAVELENGTH_RANGE_NM
    assert correction_axis.get_ylim() == STANDARD_CORRECTION_DIFFERENCE_RANGE
    assert seam_axis.get_ylim() == STANDARD_SEAM_SCORE_RANGE
    assert before_axis.images[0].norm.vmin == 0.0
    assert before_axis.images[0].norm.vmax == 1.2
    assert difference_axis.images[0].norm.vmin == -0.2
    assert difference_axis.images[0].norm.vmax == 0.2
    original_close(figure)


def test_brightness_metrics_recover_configured_gain_and_ignore_nan() -> None:
    before = np.array(
        [
            [[0.1, 0.2], [0.3, np.nan]],
            [[0.2, 0.4], [0.6, 0.8]],
        ],
        dtype=np.float32,
    )
    expected = {1: -10.0, 2: -5.0}
    after = before.copy()
    after[0] *= 0.90
    after[1] *= 0.95

    metrics = brightness_correction_metrics(
        before,
        after,
        expected_percent=expected,
    )

    assert metrics["data_modified"] is False
    assert metrics["bands_evaluated"] == 2
    assert metrics["bands"][0]["n"] == 3
    assert metrics["bands"][0]["fitted_gain"] == pytest.approx(0.90)
    assert metrics["bands"][1]["fitted_gain"] == pytest.approx(0.95)
    assert metrics["maximum_absolute_gain_error"] < 1e-6


def test_brightness_plot_uses_standard_axes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = np.linspace(0.05, 0.8, 40, dtype=np.float32).reshape(2, 4, 5)
    after = before.copy()
    after[0] *= 0.90
    after[1] *= 0.95
    metrics = brightness_correction_metrics(
        before,
        after,
        expected_percent={1: -10.0, 2: -5.0},
    )
    original_close = qa_plots.plt.close
    monkeypatch.setattr(qa_plots.plt, "close", lambda figure: None)

    qa_plots.render_brightness_diagnostics(
        before,
        after,
        metrics,
        tmp_path / "brightness.png",
        product_label="Landsat TM",
        location_label="R10C · D10 · L002 · 2021-09-15",
    )

    figure = qa_plots.plt.gcf()
    axes = {axis.get_title(): axis for axis in figure.axes}
    assert axes["Paired reflectance"].get_xlim() == STANDARD_REFLECTANCE_RANGE
    assert axes["Paired reflectance"].get_ylim() == STANDARD_REFLECTANCE_RANGE
    assert axes["Coefficient profile"].get_ylim() == (STANDARD_BRIGHTNESS_PERCENT_RANGE)
    assert "Location: R10C · D10 · L002" in figure._suptitle.get_text()
    original_close(figure)


def test_non_cube_stages_each_emit_a_figure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flight_dir = tmp_path / "NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance"
    flight_dir.mkdir()
    h5_path = flight_dir / "source.h5"
    h5_path.write_bytes(b"source artifact")
    correction = flight_dir / "scene_brdfandtopo_corrected_envi.json"
    correction.write_text(
        json.dumps(
            {
                "wavelength_nm": [500.0, 600.0],
                "geometry": {
                    name: {"mean": 0.2, "min": 0.1, "max": 0.3}
                    for name in (
                        "solar_zn",
                        "solar_az",
                        "sensor_zn",
                        "sensor_az",
                        "slope",
                        "aspect",
                    )
                },
            }
        ),
        encoding="utf-8",
    )
    model = flight_dir / "scene_brdf_model.json"
    model.write_text(
        json.dumps({"iso": [[1.0, 1.0]], "vol": [[0.0, 0.0]], "geo": [[0.0, 0.0]]}),
        encoding="utf-8",
    )
    parquet = flight_dir / "scene_merged.parquet"
    parquet.write_bytes(b"placeholder")
    monkeypatch.setattr(
        qa_stages,
        "_parquet_metrics",
        lambda paths: {
            "tables": [
                {
                    "path": str(parquet),
                    "rows": 10,
                    "columns": 7,
                    "column_names": ["pixel_id"],
                    "size_bytes": parquet.stat().st_size,
                }
            ]
        },
    )

    stage_outputs = {
        "acquisition": [h5_path],
        "correction_parameters": [correction, model],
        "analysis_tables": [parquet],
    }
    for stage_id, outputs in stage_outputs.items():
        _, report = emit_stage_qa(
            flightline_dir=flight_dir,
            stage_id=stage_id,
            outputs=outputs,
            force=True,
        )
        assert report["plots"] == ["overview.png"]
        assert StageQAPaths(flight_dir, stage_id).overview_png.exists()


def test_geometry_review_marks_out_of_range_summaries_without_masking() -> None:
    geometry = {
        "solar_zn": {"min": 0.2, "mean": 0.3, "max": 0.4},
        "sensor_zn": {"min": -174.5, "mean": -74.2, "max": 0.5},
    }

    review = qa_stages._geometry_range_review(geometry)

    assert review["data_modified"] is False
    assert review["fields_checked"] == 2
    assert review["fields_requiring_review"] == 1
    sensor = next(row for row in review["fields"] if row["field"] == "sensor_zn")
    assert sensor["out_of_range_summaries"] == ["min", "mean"]


def test_convolution_stage_audits_and_plots_brightness_application(
    tmp_path: Path,
) -> None:
    flight_dir = tmp_path / "NEON_TEST_BRIGHTNESS"
    flight_dir.mkdir()
    before = np.linspace(0.05, 0.8, 36, dtype=np.float32).reshape(3, 3, 4)
    coefficients = [-7.395941, -2.754196, -6.936788]
    after = before.copy()
    for index, percent in enumerate(coefficients):
        after[index] *= 1.0 + percent / 100.0
    final = flight_dir / f"{flight_dir.name}_landsat_tm_envi.img"
    undarkened = flight_dir / f"{flight_dir.name}_landsat_tm_undarkened_envi.img"
    header_text = "\n".join(
        [
            "ENVI",
            "samples = 4",
            "lines = 3",
            "bands = 3",
            "data type = 4",
            "interleave = bsq",
            "byte order = 0",
            "reflectance scale factor = 1",
            "data ignore value = -9999",
            "wavelength = {485, 560, 660}",
        ]
    )
    before.tofile(undarkened)
    after.tofile(final)
    undarkened.with_suffix(".hdr").write_text(header_text, encoding="utf-8")
    final.with_suffix(".hdr").write_text(header_text, encoding="utf-8")

    _, report = emit_stage_qa(
        flightline_dir=flight_dir,
        stage_id="spectral_convolution",
        outputs=[final, final.with_suffix(".hdr")],
        primary_img=final,
        force=True,
    )

    brightness = report["metrics"]["brightness_correction"]["products"]
    assert len(brightness) == 1
    assert brightness[0]["maximum_absolute_gain_error"] < 1e-6
    checks = {check["check_id"]: check for check in report["checks"]}
    brightness_check = next(
        check
        for check_id, check in checks.items()
        if check_id.startswith("brightness_coefficient_application:")
    )
    assert brightness_check["status"] == "PASS"
    assert report["plots"] == ["overview.png", "brightness.png"]
    assert StageQAPaths(flight_dir, "spectral_convolution").brightness_png.exists()


def test_pipeline_evolution_uses_fixed_axes_and_embedded_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stages = [
        {
            "stage_name": "Input reflectance",
            "metrics": {
                "reflectance": {
                    "q50": 0.25,
                    "valid_fraction": 0.6,
                    "negative_fraction": 0.0,
                },
                "spatial_footprint": {"within_footprint_valid_fraction": 1.0},
            },
        }
    ]
    original_close = qa_reporting.plt.close
    monkeypatch.setattr(qa_reporting.plt, "close", lambda figure: None)

    qa_reporting._render_pipeline_evolution(
        stages,
        tmp_path / "pipeline.png",
        location_label="R10C · D10 · L002 · 2021-09-15",
    )

    figure = qa_reporting.plt.gcf()
    axes = {axis.get_title(): axis for axis in figure.axes}
    assert axes["Median reflectance"].get_ylim() == STANDARD_REFLECTANCE_RANGE
    assert axes["Valid fraction within footprint"].get_ylim() == (
        STANDARD_VALID_FRACTION_RANGE
    )
    assert axes["Negative fraction"].get_ylim() == STANDARD_NEGATIVE_FRACTION_RANGE
    assert "Location: R10C · D10 · L002" in figure._suptitle.get_text()
    original_close(figure)


def test_threshold_logic_includes_not_evaluated() -> None:
    assert (
        classify_high_bad("high", 3.0, warn=1.5, fail=2.5, interpretation="test").status
        == QAStatus.FAIL
    )
    assert (
        classify_low_bad("low", 0.8, warn=0.9, fail=0.7, interpretation="test").status
        == QAStatus.WARN
    )
    missing = classify_high_bad(
        "missing",
        None,
        warn=1.5,
        fail=2.5,
        interpretation="test",
        reason="ancillary unavailable",
    )
    assert missing.status == QAStatus.NOT_EVALUATED
    assert missing.reason == "ancillary unavailable"
    assert QAThresholds().provisional is True


def test_stage_qa_scales_stored_reflectance_and_excludes_nodata(
    tmp_path: Path,
) -> None:
    flight_dir = _write_scaled_fixture(tmp_path)
    image = flight_dir / f"{flight_dir.name}_envi.img"

    _, report = emit_stage_qa(
        flightline_dir=flight_dir,
        stage_id="input_data",
        outputs=[image, image.with_suffix(".hdr")],
        primary_img=image,
        force=True,
    )

    summary = report["metrics"]["reflectance"]
    assert summary["n_valid"] == 3
    assert summary["valid_fraction"] == 0.75
    assert summary["minimum"] == pytest.approx(0.2)
    assert summary["maximum"] == pytest.approx(0.8)
    assert summary["negative_fraction"] == 0.0
    assert report["metrics"]["reflectance_scaling"]["stored_value_divisor"] == 10000
    footprint = report["metrics"]["spatial_footprint"]
    assert footprint["bounding_box_footprint_fraction"] == 0.75
    assert footprint["structural_background_fraction"] == 0.25
    assert footprint["within_footprint_valid_fraction"] == 1.0
    plot_contract = report["metrics"]["plot_contract"]
    assert plot_contract["location_label"] == "NEON_SCALED_FLIGHT"
    assert plot_contract["spatial"]["mode"] == "projected_map_coordinates"
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["within_footprint_valid_reflectance_fraction"]["status"] == "PASS"


def test_stage_qa_labels_bad_bands_without_masking_or_removing_values(
    tmp_path: Path,
) -> None:
    flight_dir = _write_retained_bad_band_fixture(tmp_path)
    image = flight_dir / f"{flight_dir.name}_envi.img"
    original_bytes = image.read_bytes()

    html_path, report = emit_stage_qa(
        flightline_dir=flight_dir,
        stage_id="input_data",
        outputs=[image, image.with_suffix(".hdr")],
        primary_img=image,
        force=True,
    )

    assert image.read_bytes() == original_bytes
    assert report["status"] == "WARN"
    assert report["metrics"]["reflectance"]["n_valid"] == 12
    assert report["metrics"]["reflectance"]["overbright_fraction"] == pytest.approx(
        8 / 12
    )
    quality = report["metrics"]["spectral_quality"]
    assert quality["classification_mode"] == "report_only_no_masking"
    assert quality["data_modified"] is False
    assert quality["known_bad_band_indices"] == [1, 2]
    assert quality["known_bad_band_wavelengths_nm"] == [1380.0, 1880.0]
    assert quality["known_bad_band_overbright_fraction"] == 1.0
    assert quality["usable_band_overbright_fraction"] == 0.0
    assert [row["quality_label"] for row in report["metrics"]["bandwise"]] == [
        "usable",
        "known_bad_retained",
        "known_bad_retained",
    ]
    assert all(row["data_retained"] for row in report["metrics"]["bandwise"])
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["usable_band_reflectance_above_1_2_fraction"]["status"] == "PASS"
    assert checks["known_bad_spectral_bands_retained"]["status"] == "WARN"
    assert "No masking" in checks["known_bad_spectral_bands_retained"]["reason"]
    html = html_path.read_text(encoding="utf-8")
    assert "2</strong> known poor-quality wavelength bands" in html
    assert "No values were masked, filtered, replaced, or removed" in html


def test_residual_metrics_are_deterministic() -> None:
    observed = np.array([0.1, 0.2, 0.3, 0.4])
    predicted = observed + 0.05

    metrics = residual_metrics(observed, predicted)

    assert metrics["n"] == 4
    assert np.isclose(metrics["bias"], 0.05)
    assert np.isclose(metrics["mae"], 0.05)
    assert np.isclose(metrics["ub_rmse"], 0.0, atol=1e-15)
    assert np.isclose(metrics["slope"], 1.0)


def test_seam_score_detects_known_seam_and_no_seam() -> None:
    y, x = np.mgrid[:8, :8]
    smooth = (x + y).astype(np.float32)
    with_seam = smooth.copy()
    with_seam[4:, :] += 10.0

    smooth_score = seam_score(smooth, chunk_rows=4, chunk_cols=4)
    artifact_score = seam_score(with_seam, chunk_rows=4, chunk_cols=4)

    assert np.isclose(smooth_score["max_seam_score"], 1.0)
    assert artifact_score["max_seam_score"] > 2.5


def test_chunk_invariance_reports_tolerance_exceedance() -> None:
    baseline = np.arange(24, dtype=np.float32).reshape(2, 3, 4)
    identical = chunk_invariance_metrics(baseline, baseline.copy())
    changed = baseline.copy()
    changed[0, 1, 1] += 0.01
    different = chunk_invariance_metrics(baseline, changed, tolerance=1e-6)

    assert identical["max_abs_difference"] == 0.0
    assert identical["fraction_exceeding_tolerance"] == 0.0
    assert different["max_abs_difference"] > 0.009
    assert different["fraction_exceeding_tolerance"] > 0


def test_spectral_response_support_tracks_masked_wavelengths() -> None:
    wavelengths = np.array([500.0, 510.0, 520.0, 530.0])
    response = np.array([0.0, 0.25, 0.50, 0.25])
    support = spectral_response_support(
        wavelengths,
        response,
        valid_source_mask=np.array([True, True, False, True]),
    )

    assert np.isclose(support["srf_weight_sum"], 1.0)
    assert np.isclose(support["valid_coverage_fraction"], 0.5)
    assert np.isclose(support["effective_wavelength_nm"], 520.0)


def test_translation_network_metrics_use_supplied_validation_predictions() -> None:
    observed = np.array([0.10, 0.20, 0.30, 0.40])
    direct = observed + 0.01
    indirect = observed + np.array([0.02, 0.01, 0.00, -0.01])

    paths = path_consistency_metrics(
        direct,
        indirect,
        observed_target=observed,
    )
    cycle = cycle_consistency_metrics(observed, observed + 0.005)
    grouped = grouped_residual_metrics(
        observed,
        direct,
        groups=["site-a", "site-a", "site-b", "site-b"],
    )

    assert paths["indirect_relative_to_direct"]["n"] == 4
    assert paths["direct_relative_to_observed"]["bias"] > 0
    assert np.isclose(cycle["bias"], 0.005)
    assert [row["group"] for row in grouped["groups"]] == ["site-a", "site-b"]


def test_stage_and_combined_reports_are_restart_safe(
    tmp_path: Path,
) -> None:
    qa_fixture_dir = _qa_fixture(tmp_path)
    raw_img = qa_fixture_dir / f"{qa_fixture_dir.name}_envi.img"
    corrected_img = (
        qa_fixture_dir / f"{qa_fixture_dir.name}_brdfandtopo_corrected_envi.img"
    )
    input_html, input_payload = emit_stage_qa(
        flightline_dir=qa_fixture_dir,
        stage_id="input_data",
        outputs=[raw_img, raw_img.with_suffix(".hdr")],
        primary_img=raw_img,
    )
    correction_html, correction_payload = emit_stage_qa(
        flightline_dir=qa_fixture_dir,
        stage_id="brdf_topographic_correction",
        inputs=[raw_img],
        outputs=[corrected_img, corrected_img.with_suffix(".hdr")],
        primary_img=corrected_img,
        reference_img=raw_img,
        chunk_shape=(4, 5),
    )
    first_json = StageQAPaths(qa_fixture_dir, "input_data").json.read_text()
    second_html, second_payload = emit_stage_qa(
        flightline_dir=qa_fixture_dir,
        stage_id="input_data",
        outputs=[raw_img, raw_img.with_suffix(".hdr")],
        primary_img=raw_img,
    )

    assert input_html.exists()
    assert correction_html.exists()
    assert input_payload["status"] in {"PASS", "WARN"}
    assert correction_payload["metrics"]["paired_change"]["n"] > 0
    assert second_html == input_html
    assert second_payload == input_payload
    assert StageQAPaths(qa_fixture_dir, "input_data").json.read_text() == first_json

    combined_html, combined = assemble_combined_report(qa_fixture_dir)
    assert combined_html.exists()
    assert len(combined["stages"]) == 2
    assert combined["schema_version"] == "1.3"
    assert combined["plot_contract"]["location_label"] == "NEON_TEST_FLIGHT"
    assert combined["stages"][0]["report"].endswith("stage_qa.html")
    assert "valid_fraction" in combined["stages"][0]["highlights"]
    assert "within_footprint_valid_fraction" in combined["stages"][0]["highlights"]
    assert "known_bad_band_count" in combined["stages"][0]["highlights"]
    assert combined["what_we_learn_from_the_full_pipeline"]
    assert "sensor_triangle_path_and_cycle_consistency" in json.dumps(combined)


def test_completed_runner_does_not_mistake_sensor_product_for_raw_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    flight_id = "NEON_D13_NIWO_DP1_L019-1_20230815_directional_reflectance"
    flight_dir = tmp_path / flight_id
    flight_dir.mkdir()
    (tmp_path / f"{flight_id}.h5").write_bytes(b"h5")
    raw = flight_dir / f"{flight_id}_envi.img"
    corrected = flight_dir / f"{flight_id}_brdfandtopo_corrected_envi.img"
    sensor = flight_dir / f"{flight_id}_landsat_oli_envi.img"
    for image in (raw, corrected, sensor):
        image.write_bytes(b"img")
        image.with_suffix(".hdr").write_text("ENVI", encoding="utf-8")

    calls: list[dict] = []

    def _emit(**kwargs):
        calls.append(kwargs)
        return flight_dir / "stage.html", {"stage_id": kwargs["stage_id"]}

    monkeypatch.setattr(qa_runner, "emit_stage_qa", _emit)
    monkeypatch.setattr(
        qa_runner,
        "assemble_combined_report",
        lambda path: (path / "combined.html", {"status": "PASS"}),
    )

    qa_runner.run_completed_flightline_qa(flight_dir)

    input_call = next(call for call in calls if call["stage_id"] == "input_data")
    convolution_call = next(
        call for call in calls if call["stage_id"] == "spectral_convolution"
    )
    assert input_call["primary_img"] == raw
    assert convolution_call["primary_img"] == sensor
