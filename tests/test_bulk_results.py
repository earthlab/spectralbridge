from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import spectralbridge
from spectralbridge.bulk import results as bulk_results_module
from spectralbridge.bulk.analyses.streaming_translation import (
    _LOSO_SCHEMA as INPUT_LOSO_SCHEMA,
)
from spectralbridge.bulk.analyses.streaming_translation import (
    _TRANSLATION_SCHEMA as INPUT_TRANSLATION_SCHEMA,
)
from spectralbridge.bulk.results import BulkResultsConfig, summarize_bulk_results


def _identity(pair: str, band: int) -> dict[str, object]:
    return {
        "analysis_run_id": "fixture-run",
        "translation_pair": pair,
        "source_sensor": "MicaSense matched",
        "target_sensor": "Landsat fixture",
        "source_band_index": band,
        "target_band_index": band + 1,
        "micasense_sensor": "MicaSense matched",
        "landsat_sensor": "Landsat fixture",
        "band_index": band,
        "x_column": f"source_b{band}",
        "y_column": f"target_b{band + 1}",
    }


def _translation_row(
    pair: str,
    band: int,
    *,
    level: str,
    slope: float,
    intercept: float,
    r2: float,
    flightline_id: str | None = None,
    site: str | None = None,
) -> dict[str, object]:
    return {
        **_identity(pair, band),
        "analysis_level": level,
        "weighting": f"fixture {level}",
        "flightline_id": flightline_id,
        "site": site,
        "equation": "y = slope * x + intercept",
        "status": "ok",
        "slope": slope,
        "intercept": intercept,
        "correlation": r2**0.5,
        "r2": r2,
        "bias": 0.0,
        "rmse": 0.01,
        "mae": 0.008,
        "sample_count": 1_000,
        "source_count": 3,
        "flightline_count": 3 if level not in {"per_flightline"} else 1,
        "site_count": 3 if level not in {"per_flightline", "per_site"} else 1,
        "replicate_count": 3,
        "x_min": 0.01,
        "x_max": 0.5,
        "x_mean": 0.2,
        "y_min": 0.02,
        "y_max": 0.55,
        "y_mean": 0.21,
    }


def _loso_row(
    pair: str,
    band: int,
    *,
    site: str,
    r2: float,
    training_slope: float,
) -> dict[str, object]:
    return {
        **_identity(pair, band),
        "held_out_site": site,
        "status": "ok",
        "training_slope": training_slope,
        "training_intercept": 0.01,
        "training_correlation": 0.99,
        "held_out_rmse": 0.03,
        "held_out_mae": 0.02,
        "held_out_bias": -0.01,
        "held_out_r2": r2,
        "held_out_correlation": r2**0.5,
        "observed_vs_predicted_slope": 0.98,
        "observed_vs_predicted_intercept": 0.01,
        "training_sample_count": 2_000,
        "training_site_count": 2,
        "training_flightline_count": 2,
        "held_out_sample_count": 1_000,
        "held_out_flightline_count": 1,
    }


def _write_table(path: Path, rows: list[dict[str, object]], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path)


def _make_completed_bulk_output(root: Path) -> dict[str, Path]:
    candidate_rows: list[dict[str, object]] = []
    flightline_rows: list[dict[str, object]] = []
    site_rows: list[dict[str, object]] = []
    loso_rows: list[dict[str, object]] = []

    for level, slope, intercept, r2 in (
        ("pixel_pooled", 0.80, 0.10, 0.99),
        ("flightline_balanced", 0.95, 0.04, 0.96),
        ("site_balanced", 1.05, 0.00, 0.70),
    ):
        candidate_rows.append(
            _translation_row(
                "unstable_pair",
                1,
                level=level,
                slope=slope,
                intercept=intercept,
                r2=r2,
            )
        )
    for level, slope in (
        ("pixel_pooled", 0.98),
        ("flightline_balanced", 0.99),
        ("site_balanced", 1.00),
    ):
        candidate_rows.append(
            _translation_row(
                "stable_pair",
                2,
                level=level,
                slope=slope,
                intercept=0.0,
                r2=0.99,
            )
        )

    sites = ("NIWO", "WREF", "YELL")
    for index, (site, unstable_slope, unstable_r2) in enumerate(
        zip(sites, (0.70, 1.00, 1.30), (0.50, 0.90, 0.95)), start=1
    ):
        flightline_rows.extend(
            (
                _translation_row(
                    "unstable_pair",
                    1,
                    level="per_flightline",
                    slope=unstable_slope,
                    intercept=0.0,
                    r2=unstable_r2,
                    flightline_id=f"flight-{index}",
                    site=site,
                ),
                _translation_row(
                    "stable_pair",
                    2,
                    level="per_flightline",
                    slope=0.98 + index * 0.005,
                    intercept=0.0,
                    r2=0.99,
                    flightline_id=f"flight-{index}",
                    site=site,
                ),
            )
        )
    for site, unstable_slope, unstable_r2 in zip(
        sites, (0.80, 1.00, 1.20), (0.60, 0.90, 0.95)
    ):
        site_rows.extend(
            (
                _translation_row(
                    "unstable_pair",
                    1,
                    level="per_site",
                    slope=unstable_slope,
                    intercept=0.0,
                    r2=unstable_r2,
                    site=site,
                ),
                _translation_row(
                    "stable_pair",
                    2,
                    level="per_site",
                    slope=0.99,
                    intercept=0.0,
                    r2=0.99,
                    site=site,
                ),
            )
        )
    for site, unstable_r2 in zip(sites, (0.30, 0.85, 0.90)):
        loso_rows.extend(
            (
                _loso_row(
                    "unstable_pair",
                    1,
                    site=site,
                    r2=unstable_r2,
                    training_slope=0.9,
                ),
                _loso_row(
                    "stable_pair",
                    2,
                    site=site,
                    r2=0.98,
                    training_slope=0.99,
                ),
            )
        )

    paths = {
        "manifest": root / "catalog" / "bulk_manifest.json",
        "candidates": root
        / "coefficients"
        / "candidate_translation_coefficients.parquet",
        "flightline": root
        / "analyses"
        / "sensor_translation"
        / "per_flightline.parquet",
        "site": root / "analyses" / "sensor_translation" / "per_site.parquet",
        "loso": root
        / "analyses"
        / "leave_one_site_out"
        / "leave_one_site_out.parquet",
    }
    paths["manifest"].parent.mkdir(parents=True, exist_ok=True)
    paths["manifest"].write_text(
        json.dumps(
            {
                "analysis_run_id": "fixture-run",
                "status": "complete",
                "counts": {"accepted_flightlines": 3, "accepted_rows": 12_345},
            }
        ),
        encoding="utf-8",
    )
    _write_table(paths["candidates"], candidate_rows, INPUT_TRANSLATION_SCHEMA)
    _write_table(paths["flightline"], flightline_rows, INPUT_TRANSLATION_SCHEMA)
    _write_table(paths["site"], site_rows, INPUT_TRANSLATION_SCHEMA)
    _write_table(paths["loso"], loso_rows, INPUT_LOSO_SCHEMA)
    return paths


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_summarize_bulk_results_uses_compact_outputs_only(tmp_path: Path) -> None:
    bulk_output = tmp_path / "portable_bulk_output"
    inputs = _make_completed_bulk_output(bulk_output)
    before = {name: _sha256(path) for name, path in inputs.items()}

    result = summarize_bulk_results(bulk_output, make_figures=True, make_report=True)

    assert result["status"] == "created"
    assert result["source_data_policy"] == "completed_compact_bulk_outputs_only"
    assert result["source_rasters_opened"] is False
    assert result["sufficient_statistics_regenerated"] is False
    assert result["pixel_cache_created"] is False
    assert result["overview"]["accepted_flightlines"] == 3
    assert result["overview"]["selected_observation_rows"] == 12_345
    assert result["overview"]["sites"] == ["NIWO", "WREF", "YELL"]
    assert result["overview"]["pair_band_count"] == 2
    assert result["overview"]["candidate_coefficient_count"] == 6
    assert result["overview"]["candidate_slope_median"] == pytest.approx(0.985)
    assert result["overview"]["candidate_r2_min"] == pytest.approx(0.70)
    assert "never equality of sensor-local band numbers" in result[
        "band_matching_basis"
    ]

    summaries = {
        row["translation_pair"]: row for row in result["pair_band_summaries"]
    }
    assert summaries["unstable_pair"]["candidate_slope_spread"] == pytest.approx(
        0.25
    )
    assert summaries["unstable_pair"][
        "maximum_absolute_fitted_correction_percent"
    ] == pytest.approx(30.0)
    assert summaries["unstable_pair"]["flightline_slope_iqr"] == pytest.approx(
        0.30
    )
    assert summaries["unstable_pair"]["site_slope_range"] == pytest.approx(0.40)
    assert summaries["unstable_pair"]["loso_held_out_r2_min"] == pytest.approx(0.30)
    assert summaries["unstable_pair"]["screening_status"] == "review_required"
    assert (
        summaries["stable_pair"]["screening_status"]
        == "no_configured_warning_triggered"
    )
    unstable_flags = {
        row["flag_code"]
        for row in result["attention_flags"]
        if row["translation_pair"] == "unstable_pair"
    }
    assert {
        "large_fitted_correction",
        "weighting_dependence",
        "weak_global_fit",
        "flightline_heterogeneity",
        "weak_flightline_fit",
        "site_dependence",
        "weak_site_fit",
        "weak_loso_transferability",
    } <= unstable_flags

    assert before == {name: _sha256(path) for name, path in inputs.items()}
    assert not (bulk_output / "cache").exists()
    assert not (bulk_output / "database" / "bulk_observations.parquet").exists()
    for path in result["compact_outputs"].values():
        assert Path(path).is_file()
    for path in result["figures"]:
        assert Path(path).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    report = Path(result["report"]).read_text(encoding="utf-8")
    assert "does not establish\nsensor interchangeability" in report
    assert "not universal scientific\nacceptance criteria" in report

    reused = summarize_bulk_results(bulk_output, make_figures=True, make_report=True)
    assert reused["status"] == "reused"
    assert reused["results_signature_sha256"] == result["results_signature_sha256"]


def test_bulk_qa_band_context_uses_wavelength_identity_and_rejects_index_match() -> None:
    blue_tm = {
        "translation_pair": "tm-blue",
        "source_sensor": "MicaSense_to-match_TM_and_ETM+",
        "target_sensor": "Landsat_5_TM",
        "source_band_index": 1,
        "target_band_index": 1,
        "band_index": 1,
    }
    blue_oli = {
        "translation_pair": "oli-blue",
        "source_sensor": "MicaSense_to-match_OLI_and_OLI-2",
        "target_sensor": "Landsat_8_OLI",
        "source_band_index": 2,
        "target_band_index": 2,
        "band_index": 2,
    }

    tm_context = bulk_results_module._band_match_context(blue_tm)
    oli_context = bulk_results_module._band_match_context(blue_oli)
    assert tm_context["spectral_identity"] == "blue"
    assert oli_context["spectral_identity"] == "blue"
    assert tm_context["target_wavelength_nm"] == pytest.approx(485.0)
    assert oli_context["target_wavelength_nm"] == pytest.approx(482.0)
    assert "Blue" in bulk_results_module._report_band_label(
        {**blue_oli, **oli_context}
    )
    plot_label = bulk_results_module._plot_band_label({**blue_oli, **oli_context})
    assert "Blue" in plot_label
    assert "Landsat_8_OLI B2 (482 nm)" in plot_label

    with pytest.raises(ValueError, match="wavelength-incompatible"):
        bulk_results_module._band_match_context(
            {
                **blue_tm,
                "target_sensor": "Landsat_8_OLI",
                "target_band_index": 1,
            }
        )


def test_summarize_bulk_results_config_and_validation(tmp_path: Path) -> None:
    bulk_output = tmp_path / "bulk"
    inputs = _make_completed_bulk_output(bulk_output)
    configured = summarize_bulk_results(
        bulk_output,
        config=BulkResultsConfig(representative_source_value=0.4),
        make_figures=False,
        make_report=False,
    )
    assert {
        row["representative_source_value"]
        for row in configured["pair_band_summaries"]
    } == {0.4}
    assert {
        row["representative_source_value_method"]
        for row in configured["pair_band_summaries"]
    } == {"configured_common_value"}

    table = pq.read_table(inputs["candidates"])
    broken = table.drop(["x_mean"])
    pq.write_table(broken, inputs["candidates"])
    with pytest.raises(ValueError, match="missing required columns.*x_mean"):
        summarize_bulk_results(
            bulk_output,
            make_figures=False,
            make_report=False,
        )


def test_summarize_bulk_results_surfaces_incomplete_compact_fits(
    tmp_path: Path,
) -> None:
    bulk_output = tmp_path / "bulk"
    inputs = _make_completed_bulk_output(bulk_output)
    for name, predicate, schema in (
        (
            "candidates",
            lambda row: not (
                row["translation_pair"] == "stable_pair"
                and row["analysis_level"] == "site_balanced"
            ),
            INPUT_TRANSLATION_SCHEMA,
        ),
        (
            "flightline",
            lambda row: not (
                row["translation_pair"] == "stable_pair"
                and row["flightline_id"] == "flight-3"
            ),
            INPUT_TRANSLATION_SCHEMA,
        ),
        (
            "site",
            lambda row: not (
                row["translation_pair"] == "stable_pair" and row["site"] == "YELL"
            ),
            INPUT_TRANSLATION_SCHEMA,
        ),
        (
            "loso",
            lambda row: not (
                row["translation_pair"] == "stable_pair"
                and row["held_out_site"] == "YELL"
            ),
            INPUT_LOSO_SCHEMA,
        ),
    ):
        rows = [row for row in pq.read_table(inputs[name]).to_pylist() if predicate(row)]
        _write_table(inputs[name], rows, schema)

    result = summarize_bulk_results(
        bulk_output,
        make_figures=False,
        make_report=False,
    )
    stable_flags = {
        row["flag_code"]
        for row in result["attention_flags"]
        if row["translation_pair"] == "stable_pair"
    }
    assert {
        "incomplete_candidate_weightings",
        "incomplete_flightline_fits",
        "incomplete_site_fits",
        "incomplete_loso_evaluation",
    } <= stable_flags


def test_summarize_bulk_results_is_a_lazy_public_api() -> None:
    assert spectralbridge.summarize_bulk_results is summarize_bulk_results
