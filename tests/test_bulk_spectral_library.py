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
    inspect_spectral_library,
    iter_group_spectra,
    run_spectral_library_analysis,
    trace_alpha,
)
from spectralbridge.bulk.models import BulkAnalysisPaths
from spectralbridge import run_bulk_pipeline
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
    assert metadata["reports"]["species_quantiles"]["pages"] == 2
    assert metadata["reports"]["hierarchical_variability"]["pages"] == 2
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
