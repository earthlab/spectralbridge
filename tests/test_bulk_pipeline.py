"""Contracts for the independent cross-run bulk analysis pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from spectralbridge import run_bulk_pipeline
from spectralbridge.cli.bulk_cli import _build_parser
from spectralbridge.pipelines.bulk import discover_bulk_sources


MS_OLI = "MicaSense_to-match_OLI_and_OLI-2_band_1"
LS8 = "Landsat_8_OLI_band_1"
LS8_ERROR = "Landsat_8_OLI_band_1_error"


def _write_parquet(path: Path, columns: dict[str, list[object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(columns), path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_bulk_pipeline_discovers_merges_and_fits_all_full_sources(
    tmp_path: Path,
) -> None:
    input_root = tmp_path / "processed_tree"
    source_one = input_root / "site_a" / "flight_a_merged_pixel_extraction.parquet"
    source_two = input_root / "nested" / "site_b" / "flight_b_merged_pixel_extraction.parquet"
    polygon = (
        input_root
        / "site_a"
        / "flight_a_polygons_merged_pixel_extraction.parquet"
    )
    invalid = input_root / "broken" / "bad_merged_pixel_extraction.parquet"

    _write_parquet(
        source_one,
        {
            "pixel_id": ["a", "b", "negative"],
            MS_OLI: [0.1, 0.2, -0.1],
            LS8: [0.3, 0.5, -0.1],
            LS8_ERROR: [0, 0, 0],
        },
    )
    _write_parquet(
        source_two,
        {
            "pixel_id": ["c", "d", "flagged"],
            MS_OLI: [0.3, 0.4, 0.5],
            LS8: [0.7, 0.9, 99.0],
            LS8_ERROR: [0, 0, 1],
            "source_specific_column": [1, 2, 3],
        },
    )
    _write_parquet(polygon, {"pixel_id": ["polygon"], MS_OLI: [0.1], LS8: [9.0]})
    invalid.parent.mkdir(parents=True)
    invalid.write_text("not parquet", encoding="utf-8")
    source_hashes = {_sha256(source_one), _sha256(source_two), _sha256(polygon)}

    output_dir = input_root / "bulk_products"
    result = run_bulk_pipeline(
        input_root,
        output_dir,
        threads=1,
        memory_limit="1GB",
        temp_directory=tmp_path / "duckdb_spill",
    )

    assert result["status"] == "created"
    assert result["source_count"] == 2
    assert result["rejected_source_count"] == 1
    assert result["row_count"] == 6
    assert result["regression_count"] == 1
    assert {_sha256(source_one), _sha256(source_two), _sha256(polygon)} == source_hashes

    observations = Path(result["observations"])
    coefficients = json.loads(
        Path(result["coefficients_json"]).read_text(encoding="utf-8")
    )
    regression = coefficients["regressions"][0]
    assert regression["equation"] == "landsat = slope * micasense + intercept"
    assert regression["slope"] == pytest.approx(2.0)
    assert regression["intercept"] == pytest.approx(0.1)
    assert regression["r2"] == pytest.approx(1.0)
    assert regression["sample_count"] == 4
    assert regression["source_count"] == 2

    with duckdb.connect(result["database"], read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM bulk_observations").fetchone()[0] == 6
        assert con.execute("SELECT COUNT(*) FROM bulk_sources").fetchone()[0] == 3
        assert (
            con.execute(
                "SELECT COUNT(*) FROM bulk_sources WHERE status = 'rejected'"
            ).fetchone()[0]
            == 1
        )
        paths = {
            row[0]
            for row in con.execute(
                "SELECT DISTINCT bulk_source_relative_path FROM bulk_observations"
            ).fetchall()
        }
        assert paths == {
            "site_a/flight_a_merged_pixel_extraction.parquet",
            "nested/site_b/flight_b_merged_pixel_extraction.parquet",
        }

    output_mtime = observations.stat().st_mtime_ns
    rerun = run_bulk_pipeline(input_root, output_dir, threads=1)
    assert rerun["status"] == "reused"
    assert observations.stat().st_mtime_ns == output_mtime


def test_discovery_separates_full_and_polygon_products(tmp_path: Path) -> None:
    full = tmp_path / "flight_merged_pixel_extraction.parquet"
    polygon = tmp_path / "flight_polygons_merged_pixel_extraction.parquet"
    _write_parquet(full, {"pixel_id": ["full"]})
    _write_parquet(polygon, {"pixel_id": ["polygon"]})

    assert [source.input_kind for source in discover_bulk_sources(tmp_path)] == ["full"]
    assert [
        source.input_kind
        for source in discover_bulk_sources(tmp_path, input_kind="polygon")
    ] == ["polygon"]
    assert {
        source.input_kind
        for source in discover_bulk_sources(tmp_path, input_kind="both")
    } == {"full", "polygon"}


def test_bulk_pipeline_can_build_collection_without_translation_columns(
    tmp_path: Path,
) -> None:
    source = tmp_path / "flight_merged_pixel_extraction.parquet"
    _write_parquet(source, {"pixel_id": ["a", "b"], "value": [1.0, 2.0]})

    with pytest.raises(ValueError, match="do not contain paired synthetic"):
        run_bulk_pipeline(source, tmp_path / "strict")

    result = run_bulk_pipeline(
        source,
        tmp_path / "aggregation_only",
        require_translation_pairs=False,
    )
    assert result["row_count"] == 2
    assert result["regression_count"] == 0
    assert pq.read_table(result["coefficients_parquet"]).num_rows == 0


def test_bulk_cli_defaults_protect_against_polygon_double_counting() -> None:
    args = _build_parser().parse_args(["processed_data"])

    assert args.input_kind == "full"
    assert args.allow_no_translation is False
    assert args.row_group_size == 50_000


def test_bulk_pipeline_records_degenerate_pair_as_insufficient_data(
    tmp_path: Path,
) -> None:
    source = tmp_path / "constant_merged_pixel_extraction.parquet"
    _write_parquet(
        source,
        {
            MS_OLI: [0.2, 0.2, 0.2],
            LS8: [0.3, 0.4, 0.5],
        },
    )

    result = run_bulk_pipeline(source, tmp_path / "bulk")
    payload = json.loads(
        Path(result["coefficients_json"]).read_text(encoding="utf-8")
    )

    regression = payload["regressions"][0]
    assert regression["status"] == "insufficient_data"
    assert regression["slope"] is None
    assert regression["intercept"] is None
