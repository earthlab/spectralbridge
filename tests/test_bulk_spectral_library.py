"""Contracts for bounded spectral-library summaries and variability PDFs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from spectralbridge.bulk.analyses.spectral_library import (
    SpectralLibraryPaths,
    SpectralLibraryPlotConfig,
    _layered_trace_raster,
    inspect_spectral_library,
    inspect_spectral_library_preflight,
    iter_group_spectra,
    run_spectral_library_analysis,
    trace_alpha,
)
from spectralbridge.bulk.models import BulkAnalysisPaths
from spectralbridge import run_bulk_pipeline
from spectralbridge import (
    inspect_spectral_library_preflight as public_spectral_library_preflight,
)
from spectralbridge import run_spectral_library_analysis as public_spectral_library_analysis


_MS_OLI = "MicaSense_to-match_OLI_and_OLI-2_band_1"
_LS8 = "Landsat_8_OLI_band_1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pdf_page_count(path: Path) -> int:
    """Count Matplotlib page objects without adding a PDF test dependency."""

    return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))


def _spectral_library(path: Path, *, species_count: int = 5) -> Path:
    rows: list[dict[str, object]] = []
    for species_index in range(species_count):
        species = f"species_{chr(ord('a') + species_index)}"
        observation_count = species_index + 3
        for observation in range(observation_count):
            baseline = species_index * 0.08 + observation * 0.01
            rows.append(
                {
                    "pixel_id": f"pixel-{species_index}-{observation}",
                    "species": species,
                    "polygon_id": species_index * 10 + observation // 2,
                    "flightline_id": f"flight-{species_index}",
                    "site": "site-west" if species_index % 2 else "site-east",
                    "acquisition_date": f"202{species_index}-07-01",
                    # Intentionally store columns out of wavelength order.
                    "corr_b003_wl0700nm": baseline + 0.30,
                    "corr_b001_wl0450nm": baseline + 0.10,
                    "corr_b002_wl0550nm": baseline + 0.20,
                    "raw_b003_wl0700nm": baseline + 0.35,
                    "raw_b001_wl0450nm": baseline + 0.15,
                    "raw_b002_wl0550nm": baseline + 0.25,
                    _MS_OLI: baseline + 0.05,
                    _LS8: 1.5 * (baseline + 0.05) + 0.02,
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path, row_group_size=4)
    return path


def _spectral_library_with_extremes(path: Path) -> Path:
    rows = [
        {
            "pixel_id": "negative-valid",
            "species": "species_a",
            "polygon_id": 1,
            "flightline_id": "flight-1",
            "site": "site-east",
            "corr_b003_wl0700nm": 0.20,
            "corr_b001_wl0450nm": -0.02,
            "corr_b002_wl0550nm": 0.10,
        },
        {
            "pixel_id": "ordinary-a",
            "species": "species_a",
            "polygon_id": 1,
            "flightline_id": "flight-1",
            "site": "site-east",
            "corr_b003_wl0700nm": 0.30,
            "corr_b001_wl0450nm": 0.10,
            "corr_b002_wl0550nm": 0.20,
        },
        {
            "pixel_id": "high-valid",
            "species": "species_a",
            "polygon_id": 2,
            "flightline_id": "flight-2",
            "site": "site-west",
            "corr_b003_wl0700nm": 10.0,
            "corr_b001_wl0450nm": 0.20,
            "corr_b002_wl0550nm": 0.30,
        },
        {
            "pixel_id": "nodata-invalid",
            "species": "species_a",
            "polygon_id": 2,
            "flightline_id": "flight-2",
            "site": "site-west",
            "corr_b003_wl0700nm": 0.30,
            "corr_b001_wl0450nm": -9999.0,
            "corr_b002_wl0550nm": 0.20,
        },
        {
            "pixel_id": "null-invalid",
            "species": "species_b",
            "polygon_id": 3,
            "flightline_id": "flight-3",
            "site": "site-west",
            "corr_b003_wl0700nm": 0.40,
            "corr_b001_wl0450nm": None,
            "corr_b002_wl0550nm": 0.30,
        },
        {
            "pixel_id": "ordinary-b",
            "species": "species_b",
            "polygon_id": 3,
            "flightline_id": "flight-3",
            "site": "site-west",
            "corr_b003_wl0700nm": 0.40,
            "corr_b001_wl0450nm": 0.20,
            "corr_b002_wl0550nm": 0.30,
        },
    ]
    table = pa.Table.from_pylist(rows).replace_schema_metadata({b"nodata": b"-9999"})
    pq.write_table(table, path, row_group_size=2)
    return path


def test_inspection_finds_actual_polygon_library_schema_and_sorts_wavelengths(
    tmp_path: Path,
) -> None:
    source = _spectral_library(tmp_path / "spectral_library.parquet")

    schema = inspect_spectral_library(source)

    assert schema.species_field == "species"
    assert schema.polygon_field == "polygon_id"
    assert schema.flightline_field == "flightline_id"
    assert schema.site_field == "site"
    assert schema.acquisition_date_field == "acquisition_date"
    assert schema.pixel_field == "pixel_id"
    assert schema.available_spectral_stages == ("corr", "raw")
    assert schema.spectral_stage == "corr"
    assert schema.wavelengths_nm == (450.0, 550.0, 700.0)
    assert [band.column for band in schema.bands] == [
        "corr_b001_wl0450nm",
        "corr_b002_wl0550nm",
        "corr_b003_wl0700nm",
    ]


def test_inspection_rejects_ambiguous_or_nonphysical_spectral_schemas(
    tmp_path: Path,
) -> None:
    ambiguous = tmp_path / "ambiguous.parquet"
    pq.write_table(
        pa.table(
            {
                "species": ["one"],
                "first_b001_wl0500nm": [0.1],
                "second_b001_wl0600nm": [0.2],
            }
        ),
        ambiguous,
    )
    with pytest.raises(ValueError, match="multiple spectral stages"):
        inspect_spectral_library(ambiguous)
    assert inspect_spectral_library(ambiguous, spectral_stage="first").wavelengths_nm == (
        500.0,
    )

    band_numbers_only = tmp_path / "band_numbers_only.parquet"
    pq.write_table(
        pa.table({"species": ["one"], "corr_band_1": [0.1]}),
        band_numbers_only,
    )
    with pytest.raises(ValueError, match="No wavelength-bearing"):
        inspect_spectral_library(band_numbers_only)


def test_trace_alpha_is_deterministic_and_decreases_with_population() -> None:
    values = [trace_alpha(count) for count in (10, 100, 1_000, 10_000, 100_000)]

    assert values == sorted(values, reverse=True)
    assert values[0] == 0.03
    assert values[-1] == 0.003
    assert trace_alpha(1_000) == pytest.approx(0.2 / np.sqrt(1_000))
    assert trace_alpha(10_000) == 0.003
    assert trace_alpha(100_000) == 0.003
    # Ten exactly overlapping traces still leave most of the background visible;
    # dense loci can accumulate without the raster saturating immediately.
    ten_trace_opacity = 1.0 - (1.0 - trace_alpha(10)) ** 10
    assert ten_trace_opacity < 0.30


def test_all_raster_batches_accumulate_deterministically() -> None:
    wavelengths = np.asarray([450.0, 550.0, 700.0])
    first = np.asarray([[0.20, 0.20, 0.20]])
    second = np.asarray([[0.80, 0.80, 0.80]])
    kwargs = {
        "x_limits": (450.0, 700.0),
        "y_limits": (0.0, 1.0),
        "dpi": 72,
    }
    both = _layered_trace_raster(
        wavelengths,
        ((iter((first, second)), "#000000", 0.5, 1.0),),
        **kwargs,
    )
    both_again = _layered_trace_raster(
        wavelengths,
        ((iter((first, second)), "#000000", 0.5, 1.0),),
        **kwargs,
    )
    last_only = _layered_trace_raster(
        wavelengths,
        ((iter((second,)), "#000000", 0.5, 1.0),),
        **kwargs,
    )

    assert np.array_equal(both, both_again)
    assert np.count_nonzero(np.any(both != last_only, axis=2)) > 0
    assert both.shape == last_only.shape


def test_preflight_reports_schema_counts_and_render_cost_without_pdfs(
    tmp_path: Path,
) -> None:
    source = _spectral_library(tmp_path / "spectral_library.parquet")
    source_hash = _sha256(source)

    result = inspect_spectral_library_preflight(source)

    assert result["source"] == source.resolve().as_posix()
    assert result["source_size_bytes"] == source.stat().st_size
    assert result["schema"]["species_field"] == "species"
    assert result["counts"] == {
        "source_rows": 25,
        "valid_spectra": 25,
        "species": 5,
        "polygons": 14,
        "flightlines": 5,
        "sites": 2,
    }
    assert result["largest_species"] == {
        "species": "species_e",
        "valid_spectrum_count": 7,
    }
    assert result["median_valid_spectra_per_species"] == 5.0
    assert result["species_over_10k_traces"] == 0
    assert result["species_over_100k_traces"] == 0
    assert result["estimated_total_raw_traces_to_render"] == 100
    assert result["all_valid_traces_requested"] is True
    assert result["expected_pages"]["species_variability"] == 2
    assert result["expected_pages"]["species_variability_full_range"] == 2
    assert result["pdfs_generated"] is False
    assert callable(public_spectral_library_preflight)
    assert _sha256(source) == source_hash


def test_group_scanning_is_bounded_and_optional_sampling_is_deterministic(
    tmp_path: Path,
) -> None:
    source = _spectral_library(tmp_path / "spectral_library.parquet")
    schema = inspect_spectral_library(source)
    with duckdb.connect() as con:
        batches = list(
            iter_group_spectra(
                con,
                schema,
                grouping_field="species",
                group_value="species_e",
                batch_size=2,
            )
        )
        first_sample = list(
            iter_group_spectra(
                con,
                schema,
                grouping_field="species",
                group_value="species_e",
                batch_size=1,
                max_traces=2,
                sampling_seed=42,
            )
        )
        second_sample = list(
            iter_group_spectra(
                con,
                schema,
                grouping_field="species",
                group_value="species_e",
                batch_size=2,
                max_traces=2,
                sampling_seed=42,
            )
        )

    assert sum(batch.shape[0] for batch in batches) == 7
    assert all(batch.shape[0] <= 2 for batch in batches)
    assert np.vstack(first_sample) == pytest.approx(np.vstack(second_sample))
    assert np.vstack(first_sample).shape == (2, 3)


def test_full_reports_write_compact_summaries_and_multipage_pdfs_without_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _spectral_library(tmp_path / "spectral_library.parquet")
    source_hash = _sha256(source)
    output = tmp_path / "bulk_output"
    bulk_paths = BulkAnalysisPaths(output)
    bulk_paths.ensure_directories()
    config = SpectralLibraryPlotConfig(
        panels_per_page=4,
        trace_batch_size=2,
        summary_band_batch_size=2,
        raster_dpi=90,
    )

    # Guard against an accidental convenience regression to full-table pandas IO.
    import pandas as pd

    monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("full-table pandas read is forbidden")
        ),
    )
    with duckdb.connect() as con:
        metadata = run_spectral_library_analysis(
            con,
            bulk_paths,
            spectral_library=source,
            analysis_run_id="fixture-run",
            config=config,
            make_summary_plots=True,
            make_full_spectral_reports=True,
        )
        registered = con.execute(
            "SELECT COUNT(*) FROM spectral_library_species_medians"
        ).fetchone()[0]

    paths = SpectralLibraryPaths.from_bulk_paths(bulk_paths)
    summary = pq.read_table(paths.species_summary).to_pylist()
    medians = pq.read_table(paths.species_medians).to_pylist()
    quantiles = pq.read_table(paths.species_quantiles).to_pylist()
    counts = pq.read_table(paths.group_counts).to_pylist()
    species_a = next(row for row in summary if row["species"] == "species_a")
    species_a_medians = [
        row["median_reflectance"]
        for row in medians
        if row["species"] == "species_a"
    ]

    assert _sha256(source) == source_hash
    assert species_a["observation_count"] == 3
    assert species_a["valid_spectrum_count"] == 3
    assert species_a["polygon_count"] == 2
    assert species_a["flightline_count"] == 1
    assert species_a["site_count"] == 1
    assert species_a_medians == pytest.approx([0.11, 0.21, 0.31], abs=1e-12)
    assert {row["quantile"] for row in quantiles} == {
        0.025,
        0.10,
        0.25,
        0.50,
        0.75,
        0.90,
        0.975,
    }
    assert {row["grouping_field"] for row in counts} == {
        "species",
        "polygon_id",
        "flightline_id",
        "site",
    }
    assert registered == 15
    assert metadata["sampling"]["enabled"] is False
    assert metadata["trace_layer_rasterized"] is True
    assert metadata["schema"]["wavelengths_nm"] == [450.0, 550.0, 700.0]
    assert metadata["reports"]["species_variability"]["pages"] == 2
    assert metadata["reports"]["species_variability"]["display_mode"] == (
        "global_robust"
    )
    assert metadata["reports"]["species_variability"]["graphical_clipping_only"]
    assert metadata["reports"]["species_variability_full_range"]["pages"] == 2
    assert metadata["reports"]["species_variability_full_range"]["display_mode"] == (
        "global_full"
    )
    assert not metadata["reports"]["species_variability_full_range"][
        "graphical_clipping_only"
    ]
    assert metadata["reports"]["species_quantiles"]["pages"] == 2
    assert metadata["reports"]["hierarchical_variability"]["pages"] == 2
    assert metadata["report_cost"]["source_rows"] == 25
    assert metadata["report_cost"]["source_size_bytes"] == source.stat().st_size
    assert metadata["report_cost"]["largest_species"] == {
        "species": "species_e",
        "valid_spectrum_count": 7,
    }
    assert metadata["report_cost"]["expected_repeated_parquet_scans"][
        "full_report_group_filtered_scans"
    ] > 0
    assert metadata["species_order"] == [
        "species_e",
        "species_d",
        "species_c",
        "species_b",
        "species_a",
    ]
    assert callable(public_spectral_library_analysis)
    for report in metadata["reports"].values():
        report_path = Path(report["path"])
        assert report_path.is_file()
        assert 1_000 < report_path.stat().st_size < 5_000_000
        assert _pdf_page_count(report_path) == report["pages"]
    assert b"/Subtype /Image" in paths.species_variability.read_bytes()
    assert b"/Type /Font" in paths.species_variability.read_bytes()
    assert not list(output.rglob("observations.parquet"))
    assert not list(output.rglob("*cache*.parquet"))
    persisted = json.loads(paths.metadata.read_text(encoding="utf-8"))
    assert persisted["source"] == source.resolve().as_posix()
    assert persisted["source_signature_sha256"]


def test_summary_plots_do_not_implicitly_create_expensive_full_reports(
    tmp_path: Path,
) -> None:
    source = _spectral_library(tmp_path / "spectral_library.parquet", species_count=2)
    bulk_paths = BulkAnalysisPaths(tmp_path / "bulk_output")
    bulk_paths.ensure_directories()
    with duckdb.connect() as con:
        metadata = run_spectral_library_analysis(
            con,
            bulk_paths,
            spectral_library=source,
            analysis_run_id="summary-only",
            config=SpectralLibraryPlotConfig(
                species_sort="alphabetical",
                raster_dpi=72,
            ),
            make_summary_plots=True,
            make_full_spectral_reports=False,
        )

    assert set(metadata["reports"]) == {"species_medians", "observation_counts"}
    assert metadata["species_order"] == ["species_a", "species_b"]
    paths = SpectralLibraryPaths.from_bulk_paths(bulk_paths)
    assert not paths.species_variability.exists()
    assert not paths.species_quantile_report.exists()


def test_visualization_validity_robust_ranges_and_extremes_are_separate(
    tmp_path: Path,
) -> None:
    source = _spectral_library_with_extremes(tmp_path / "spectral_library.parquet")
    source_hash = _sha256(source)
    bulk_paths = BulkAnalysisPaths(tmp_path / "bulk_output")
    bulk_paths.ensure_directories()
    config = SpectralLibraryPlotConfig(
        plot_y_quantiles=(0.20, 0.80),
        max_extreme_spectra_per_species=1,
    )

    with duckdb.connect() as con:
        metadata = run_spectral_library_analysis(
            con,
            bulk_paths,
            spectral_library=source,
            analysis_run_id="robust-validity",
            config=config,
            make_summary_plots=False,
            make_full_spectral_reports=False,
        )

    paths = SpectralLibraryPaths.from_bulk_paths(bulk_paths)
    summaries = {
        row["species"]: row for row in pq.read_table(paths.species_summary).to_pylist()
    }
    ranges = {
        row["species"]: row
        for row in pq.read_table(paths.species_plot_ranges).to_pylist()
    }
    extremes = pq.read_table(paths.extreme_spectra).to_pylist()
    source_rows = pq.read_table(source).to_pylist()
    lower = ranges["species_a"]["global_robust_lower"]
    upper = ranges["species_a"]["global_robust_upper"]
    valid_rows = [
        row
        for row in source_rows
        if row["pixel_id"] not in {"nodata-invalid", "null-invalid"}
    ]
    spectral_columns = [
        "corr_b001_wl0450nm",
        "corr_b002_wl0550nm",
        "corr_b003_wl0700nm",
    ]
    species_a_rows = [row for row in valid_rows if row["species"] == "species_a"]
    expected_below = sum(
        row[column] < lower for row in species_a_rows for column in spectral_columns
    )
    expected_above = sum(
        row[column] > upper for row in species_a_rows for column in spectral_columns
    )

    assert metadata["visualization_validity"]["finite_negative_reflectance_allowed"]
    assert metadata["schema"]["detected_nodata_values"] == [-9999.0]
    assert metadata["visualization_validity"]["minimum_reflectance"] is None
    assert metadata["visualization_validity"]["nodata_values_excluded"] == [-9999.0]
    assert summaries["species_a"]["observation_count"] == 4
    assert summaries["species_a"]["valid_spectrum_count"] == 3
    assert summaries["species_a"]["reflectance_min"] == pytest.approx(-0.02)
    assert summaries["species_a"]["reflectance_max"] == pytest.approx(10.0)
    assert summaries["species_b"]["valid_spectrum_count"] == 1
    assert ranges["species_a"]["full_minimum"] == pytest.approx(-0.02)
    assert ranges["species_a"]["full_maximum"] == pytest.approx(10.0)
    assert ranges["species_a"]["global_values_below"] == expected_below
    assert ranges["species_a"]["global_values_above"] == expected_above
    assert metadata["plot_ranges"]["analytical_summaries_unchanged"] is True
    assert len(extremes) <= 2
    assert any(row["pixel_id"] == "high-valid" for row in extremes)
    assert all(row["rank_within_species"] == 1 for row in extremes)
    assert _sha256(source) == source_hash
    assert not list(bulk_paths.output_dir.rglob("observations.parquet"))
    assert not list(bulk_paths.output_dir.rglob("*cache*.parquet"))


def test_optional_visualization_minimum_threshold_excludes_negative_spectrum(
    tmp_path: Path,
) -> None:
    source = _spectral_library_with_extremes(tmp_path / "spectral_library.parquet")
    schema = inspect_spectral_library(source)

    with duckdb.connect() as con:
        default_values = np.vstack(
            list(
                iter_group_spectra(
                    con,
                    schema,
                    grouping_field="species",
                    group_value="species_a",
                    batch_size=2,
                )
            )
        )
        threshold_values = np.vstack(
            list(
                iter_group_spectra(
                    con,
                    schema,
                    grouping_field="species",
                    group_value="species_a",
                    batch_size=2,
                    config=SpectralLibraryPlotConfig(
                        spectral_plot_minimum_reflectance=0.0
                    ),
                )
            )
        )

    assert default_values.shape[0] == 3
    assert default_values.min() == pytest.approx(-0.02)
    assert threshold_values.shape[0] == 2
    assert threshold_values.min() >= 0.0


def test_per_group_robust_scaling_keeps_separate_full_range_audit(
    tmp_path: Path,
) -> None:
    source = _spectral_library_with_extremes(tmp_path / "spectral_library.parquet")
    bulk_paths = BulkAnalysisPaths(tmp_path / "bulk_output")
    bulk_paths.ensure_directories()

    with duckdb.connect() as con:
        metadata = run_spectral_library_analysis(
            con,
            bulk_paths,
            spectral_library=source,
            analysis_run_id="per-group-scaling",
            config=SpectralLibraryPlotConfig(
                species_y_scale="per_group_robust",
                plot_y_quantiles=(0.20, 0.80),
                panels_per_page=2,
                trace_batch_size=1,
                raster_dpi=72,
            ),
            make_summary_plots=False,
            make_full_spectral_reports=True,
        )

    assert metadata["reports"]["species_variability"]["display_mode"] == (
        "per_group_robust"
    )
    assert metadata["reports"]["species_variability_full_range"]["display_mode"] == (
        "global_full"
    )
    assert Path(metadata["reports"]["species_variability"]["path"]).is_file()
    assert Path(
        metadata["reports"]["species_variability_full_range"]["path"]
    ).is_file()


def test_compact_summaries_preserve_extreme_valid_spectra(tmp_path: Path) -> None:
    source = _spectral_library(tmp_path / "spectral_library.parquet", species_count=1)
    table = pq.read_table(source)
    values = table["corr_b003_wl0700nm"].to_pylist()
    values[0] = -9999.0
    values[-1] = 9.0
    table = table.set_column(
        table.schema.get_field_index("corr_b003_wl0700nm"),
        "corr_b003_wl0700nm",
        pa.array(values),
    )
    pq.write_table(table, source)
    bulk_paths = BulkAnalysisPaths(tmp_path / "bulk_output")
    bulk_paths.ensure_directories()

    with duckdb.connect() as con:
        run_spectral_library_analysis(
            con,
            bulk_paths,
            spectral_library=source,
            analysis_run_id="outlier-preservation",
            make_summary_plots=False,
            make_full_spectral_reports=False,
        )

    summary = pq.read_table(
        SpectralLibraryPaths.from_bulk_paths(bulk_paths).species_summary
    ).to_pylist()
    assert summary[0]["observation_count"] == 3
    assert summary[0]["valid_spectrum_count"] == 2
    assert summary[0]["reflectance_min"] == pytest.approx(0.11)
    assert summary[0]["reflectance_max"] == 9.0


def test_bulk_pipeline_integrates_opt_in_library_reports_and_restart(
    tmp_path: Path,
) -> None:
    flightline = "NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance"
    source = _spectral_library(
        tmp_path
        / "archive"
        / f"{flightline}_polygons_merged_pixel_extraction.parquet",
        species_count=2,
    )
    output = tmp_path / "bulk_output"
    kwargs = {
        "input_kind": "polygon",
        "input_mode": "merged_parquet",
        "spectral_library": source,
        "make_summary_plots": True,
        "spectral_library_config": SpectralLibraryPlotConfig(raster_dpi=72),
    }

    created = run_bulk_pipeline(source.parent, output, **kwargs)
    reused = run_bulk_pipeline(source.parent, output, **kwargs)

    assert created["status"] == "created"
    assert reused["status"] == "reused"
    assert created["preflight"]["spectral_library_schema"]["species_field"] == "species"
    assert created["preflight"]["spectral_library_schema"]["band_count"] == 3
    assert created["preflight"]["spectral_library"]["counts"]["source_rows"] == 7
    assert created["preflight"]["spectral_library"]["counts"]["species"] == 2
    assert created["preflight"]["spectral_library"]["pdfs_generated"] is False
    assert set(created["spectral_library"]["reports"]) == {
        "species_medians",
        "observation_counts",
    }
    with duckdb.connect(created["database"], read_only=True) as con:
        assert con.execute(
            "SELECT COUNT(*) FROM spectral_library_species_summary"
        ).fetchone()[0] == 2
    assert not list(output.rglob("observations.parquet"))
    assert not list(output.rglob("*cache*.parquet"))

    changed = run_bulk_pipeline(
        source.parent,
        output,
        **{
            **kwargs,
            "spectral_library_config": SpectralLibraryPlotConfig(
                raster_dpi=72,
                species_y_scale="per_group_robust",
            ),
        },
    )
    assert changed["status"] == "created"
    assert changed["spectral_library"]["configuration"]["species_y_scale"] == (
        "per_group_robust"
    )


def test_bulk_pipeline_library_only_builds_compact_summaries_without_pdfs(
    tmp_path: Path,
) -> None:
    flightline = "NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance"
    source = _spectral_library(
        tmp_path
        / "archive"
        / f"{flightline}_polygons_merged_pixel_extraction.parquet",
        species_count=2,
    )
    output = tmp_path / "bulk_output"

    result = run_bulk_pipeline(
        source.parent,
        output,
        input_kind="polygon",
        input_mode="merged_parquet",
        spectral_library=source,
    )

    paths = SpectralLibraryPaths.from_bulk_paths(BulkAnalysisPaths(output))
    assert result["status"] == "created"
    assert result["spectral_library"]["reports"] == {}
    assert paths.species_summary.is_file()
    assert paths.species_plot_ranges.is_file()
    assert paths.extreme_spectra.is_file()
    assert not list(paths.figures_dir.glob("*.pdf"))


def test_bulk_pipeline_requires_library_for_requested_reports(tmp_path: Path) -> None:
    source = _spectral_library(
        tmp_path / "archive" / "fixture_polygons_merged_pixel_extraction.parquet",
        species_count=1,
    )
    with pytest.raises(ValueError, match="spectral_library is required"):
        run_bulk_pipeline(
            source.parent,
            tmp_path / "bulk_output",
            input_kind="polygon",
            input_mode="merged_parquet",
            make_summary_plots=True,
        )
