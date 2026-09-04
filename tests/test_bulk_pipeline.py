"""Production contracts for the independent bulk population pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from spectralbridge import run_bulk_pipeline
from spectralbridge.bulk.catalog import (
    build_bulk_catalog,
    canonical_identity_from_product,
    discover_bulk_sources,
)
from spectralbridge.cli.bulk_cli import _build_parser


MS_OLI = "MicaSense_to-match_OLI_and_OLI-2_band_1"
LS8 = "Landsat_8_OLI_band_1"
LS8_ERROR = "Landsat_8_OLI_band_1_error"
R10C_1 = "NEON_D10_R10C_DP1_L001-1_20210915_directional_reflectance"
R10C_2 = "NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance"
NIWO_1 = "NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance"
JORN_1 = "NEON_D14_JORN_DP1_L001-1_20220701_directional_reflectance"


def _merged(directory: Path, flightline_id: str, *, polygon: bool = False) -> Path:
    suffix = (
        "_polygons_merged_pixel_extraction.parquet"
        if polygon
        else "_merged_pixel_extraction.parquet"
    )
    return directory / f"{flightline_id}{suffix}"


def _write_parquet(
    path: Path,
    x: list[float],
    y: list[float],
    *,
    extra: dict[str, list[object]] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns: dict[str, list[object]] = {
        "pixel_id": [f"p{index}" for index in range(len(x))],
        MS_OLI: x,
        LS8: y,
        LS8_ERROR: [0] * len(x),
    }
    columns.update(extra or {})
    pq.write_table(pa.table(columns), path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(input_root: Path, output: Path, **kwargs: object) -> dict[str, object]:
    return run_bulk_pipeline(
        input_root,
        output,
        threads=1,
        memory_limit="1GB",
        **kwargs,
    )


def test_identity_comes_from_product_not_outer_folder(tmp_path: Path) -> None:
    product = _merged(
        tmp_path / "machine-77" / "collision-safe-copy-name",
        R10C_1,
    )
    _write_parquet(product, [0.1, 0.2], [0.3, 0.5])

    identity = canonical_identity_from_product(product)
    sources, flightlines = build_bulk_catalog(tmp_path)

    assert identity == {
        "canonical_flightline_id": R10C_1,
        "identity_source": "canonical_product_filename",
        "site": "R10C",
        "acquisition_date": "2021-09-15",
    }
    assert sources[0].relative_path.startswith("machine-77/")
    assert flightlines[0].canonical_flightline_id == R10C_1
    assert flightlines[0].site == "R10C"


def test_sister_runs_stay_independent_and_true_duplicates_are_excluded(
    tmp_path: Path,
) -> None:
    root = tmp_path / "staging"
    _write_parquet(_merged(root / "machine_a" / "sister_one", R10C_1), [1, 2], [3, 5])
    _write_parquet(_merged(root / "machine_a" / "sister_two", R10C_2), [1, 2], [3, 5])
    _write_parquet(_merged(root / "machine_b" / "copy_one", NIWO_1), [1, 2], [3, 5])
    _write_parquet(_merged(root / "machine_c" / "copy_two", NIWO_1), [1, 2], [3, 5])

    sources, flightlines = build_bulk_catalog(root)
    by_id: dict[str, list[object]] = {}
    for record in flightlines:
        by_id.setdefault(record.canonical_flightline_id or "", []).append(record)

    assert [item.status for item in by_id[R10C_1]] == ["accepted"]
    assert [item.status for item in by_id[R10C_2]] == ["accepted"]
    assert {item.status for item in by_id[NIWO_1]} == {"duplicate_excluded"}
    assert all(item.duplicate_candidate_count == 2 for item in by_id[NIWO_1])
    assert sum(source.status == "accepted" for source in sources) == 2
    assert sum(source.status == "duplicate_excluded" for source in sources) == 2


def test_virtual_union_is_default_and_preserves_provenance_and_sources(
    tmp_path: Path,
) -> None:
    root = tmp_path / "staging"
    one = _merged(root / "arbitrary_001", R10C_1)
    two = _merged(root / "arbitrary_002", NIWO_1)
    _write_parquet(one, [0.1, 0.2], [0.3, 0.5])
    _write_parquet(
        two,
        [0.3, 0.4],
        [0.7, 0.9],
        extra={"source_specific_column": [1, 2]},
    )
    hashes = {one: _sha256(one), two: _sha256(two)}

    result = _run(root, tmp_path / "bulk")

    assert result["status"] == "created"
    assert result["accepted_flightline_count"] == 2
    assert result["row_count"] == 4
    assert result["materialized_observations"] is None
    assert not (tmp_path / "bulk" / "database" / "bulk_observations.parquet").exists()
    assert {path: _sha256(path) for path in hashes} == hashes
    with duckdb.connect(str(result["database"]), read_only=True) as con:
        assert con.execute("SELECT COUNT(*) FROM bulk_observations").fetchone()[0] == 4
        assert (
            con.execute(
                "SELECT COUNT(source_specific_column) FROM bulk_observations"
            ).fetchone()[0]
            == 2
        )
        assert {
            row[0]
            for row in con.execute(
                "SELECT DISTINCT bulk_flightline_id FROM bulk_observations"
            ).fetchall()
        } == {R10C_1, NIWO_1}
        sql = con.execute(
            "SELECT sql FROM duckdb_views() WHERE view_name = 'bulk_observations_virtual'"
        ).fetchone()[0]
        assert "read_parquet" in sql


def test_polygon_is_cataloged_but_excluded_unless_requested(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    full = _merged(root / "run", R10C_1)
    polygon = _merged(root / "run", R10C_1, polygon=True)
    _write_parquet(full, [0.1, 0.2], [0.3, 0.5])
    _write_parquet(polygon, [0.4], [0.9])

    default = _run(root, tmp_path / "default")
    both = _run(root, tmp_path / "both", input_kind="both")

    assert len(discover_bulk_sources(root)) == 2
    assert default["row_count"] == 2
    assert both["row_count"] == 3
    with duckdb.connect(str(default["database"]), read_only=True) as con:
        assert con.execute(
            "SELECT DISTINCT bulk_source_kind FROM bulk_observations"
        ).fetchall() == [("full",)]


def test_optional_materialization_and_restart_invalidation(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    source = _merged(root / "run", R10C_1)
    _write_parquet(source, [0.1, 0.2], [0.3, 0.5])
    output = tmp_path / "bulk"

    first = _run(root, output, materialize_observations=True)
    observation = Path(str(first["materialized_observations"]))
    first_manifest = json.loads(Path(str(first["manifest"])).read_text())
    first_mtime = observation.stat().st_mtime_ns
    reused = _run(root, output, materialize_observations=True)
    assert reused["status"] == "reused"
    assert observation.stat().st_mtime_ns == first_mtime

    _write_parquet(source, [0.1, 0.2, 0.3], [0.3, 0.5, 0.7])
    rebuilt = _run(root, output, materialize_observations=True)
    second_manifest = json.loads(Path(str(rebuilt["manifest"])).read_text())
    assert rebuilt["status"] == "created"
    assert rebuilt["row_count"] == 3
    assert (
        first_manifest["input_signature_sha256"]
        != second_manifest["input_signature_sha256"]
    )


def test_incomplete_run_reuses_completed_analysis_modules(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    _write_parquet(_merged(root / "r10c", R10C_1), [0.1, 0.2], [0.3, 0.5])
    _write_parquet(_merged(root / "niwo", NIWO_1), [0.1, 0.2], [0.3, 0.5])
    output = tmp_path / "bulk"

    first = _run(root, output)
    translation = output / "analyses" / "sensor_translation" / "pixel_pooled.parquet"
    loso = output / "analyses" / "leave_one_site_out" / "leave_one_site_out.parquet"
    mtimes = (translation.stat().st_mtime_ns, loso.stat().st_mtime_ns)
    manifest_path = Path(str(first["manifest"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "building"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    resumed = _run(root, output)

    assert resumed["status"] == "created"
    assert (translation.stat().st_mtime_ns, loso.stat().st_mtime_ns) == mtimes
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "complete"


def test_census_reports_duplicates_rejections_and_configuration_state(
    tmp_path: Path,
) -> None:
    root = tmp_path / "staging"
    accepted = _merged(root / "accepted", R10C_1)
    _write_parquet(accepted, [0.1, 0.2], [0.3, 0.5])
    qa = accepted.parent / "qa" / "stages" / "04_spectral_convolution" / "stage_qa.json"
    qa.parent.mkdir(parents=True)
    qa.write_text(
        json.dumps(
            {
                "parameters": {
                    "brightness_coefficient_source": "landsat_to_micasense.json",
                    "brdf_apply_mode": "scene",
                }
            }
        ),
        encoding="utf-8",
    )
    for directory in ("duplicate_a", "duplicate_b"):
        _write_parquet(_merged(root / directory, NIWO_1), [0.1, 0.2], [0.3, 0.5])
    corrupt = _merged(root / "corrupt", JORN_1)
    corrupt.parent.mkdir(parents=True)
    corrupt.write_text("not parquet", encoding="utf-8")

    result = _run(root, tmp_path / "bulk", preflight_only=True)
    census = json.loads(
        (
            tmp_path
            / "bulk"
            / "analyses"
            / "dataset_census"
            / "dataset_census.json"
        ).read_text()
    )
    flightlines = pq.read_table(str(result["flightlines"])).to_pylist()
    accepted_record = next(
        row for row in flightlines if row["canonical_flightline_id"] == R10C_1
    )

    assert census["observation_scan_performed"] is False
    assert census["accepted_canonical_flightlines"] == 1
    assert census["duplicate_candidates"] == 2
    assert census["rejected_flightline_records"] == 3
    assert census["accepted_observation_rows"] == 2
    assert "brightness_coefficient_source" in accepted_record["brightness_state_json"]
    assert "brdf_apply_mode" in accepted_record["correction_state_json"]


def test_translation_levels_balancing_and_loso_are_correct(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    _write_parquet(
        _merged(root / "r10c_large", R10C_1),
        [1, 2, 3, 4],
        [3, 5, 7, 9],
    )
    _write_parquet(
        _merged(root / "r10c_small", R10C_2),
        [1, 4],
        [5, 17],
    )
    _write_parquet(
        _merged(root / "niwo", NIWO_1),
        [1, 2, 3],
        [3, 5, 7],
    )
    result = _run(root, tmp_path / "bulk")

    with duckdb.connect(str(result["database"]), read_only=True) as con:
        pooled = con.execute(
            "SELECT slope, sample_count, flightline_count, site_count "
            "FROM translation_pixel_pooled"
        ).fetchone()
        per_flight = con.execute(
            "SELECT flightline_id, slope FROM translation_per_flightline "
            "ORDER BY flightline_id"
        ).fetchall()
        per_site = con.execute(
            "SELECT site, slope FROM translation_per_site ORDER BY site"
        ).fetchall()
        balanced = con.execute(
            "SELECT slope, replicate_count FROM translation_flightline_balanced"
        ).fetchone()
        loso = con.execute(
            "SELECT held_out_site, status, training_slope, held_out_sample_count, "
            "held_out_flightline_count FROM translation_leave_one_site_out "
            "ORDER BY held_out_site"
        ).fetchall()

    assert pooled[1:] == (9, 3, 2)
    assert dict(per_flight)[R10C_1] == pytest.approx(2.0)
    assert dict(per_flight)[R10C_2] == pytest.approx(4.0)
    assert {site for site, _ in per_site} == {"NIWO", "R10C"}
    assert balanced[1] == 3
    assert balanced[0] != pytest.approx(pooled[0])
    assert len(loso) == 2
    assert all(row[1] == "ok" for row in loso)
    assert {row[4] for row in loso} == {1, 2}


def test_translation_and_loso_exact_relationship_across_sites(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    for directory, flightline in (
        ("r10c", R10C_1),
        ("niwo", NIWO_1),
        ("jorn", JORN_1),
    ):
        _write_parquet(
            _merged(root / directory, flightline),
            [0.1, 0.2, 0.4],
            [0.3, 0.5, 0.9],
        )

    result = _run(root, tmp_path / "bulk")
    with duckdb.connect(str(result["database"]), read_only=True) as con:
        for table in (
            "translation_pixel_pooled",
            "translation_per_flightline",
            "translation_per_site",
            "translation_flightline_balanced",
            "translation_site_balanced",
        ):
            rows = con.execute(
                f"SELECT status, slope, intercept, rmse FROM {table}"
            ).fetchall()
            assert rows
            assert all(row[0] == "ok" for row in rows)
            assert all(row[1] == pytest.approx(2.0) for row in rows)
            assert all(row[2] == pytest.approx(0.1) for row in rows)
            assert all(row[3] == pytest.approx(0.0, abs=1e-12) for row in rows)
        loso = con.execute(
            "SELECT status, training_slope, training_intercept, held_out_rmse, "
            "held_out_mae, held_out_bias FROM translation_leave_one_site_out"
        ).fetchall()
    assert len(loso) == 3
    assert all(row[0] == "ok" for row in loso)
    assert all(row[1] == pytest.approx(2.0) for row in loso)
    assert all(row[2] == pytest.approx(0.1) for row in loso)
    assert all(row[3] == pytest.approx(0.0, abs=1e-12) for row in loso)
    assert all(row[4] == pytest.approx(0.0, abs=1e-12) for row in loso)
    assert all(row[5] == pytest.approx(0.0, abs=1e-12) for row in loso)


def test_loso_reports_insufficient_sites_without_crashing(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    _write_parquet(_merged(root / "only", R10C_1), [1, 2], [3, 5])

    result = _run(root, tmp_path / "bulk")
    with duckdb.connect(str(result["database"]), read_only=True) as con:
        row = con.execute(
            "SELECT status, training_site_count FROM translation_leave_one_site_out"
        ).fetchone()
    assert row == ("insufficient_sites", 0)


def test_constant_predictor_is_reported_as_insufficient_data(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    _write_parquet(_merged(root / "only", R10C_1), [0.2, 0.2], [0.3, 0.5])

    result = _run(root, tmp_path / "bulk")
    with duckdb.connect(str(result["database"]), read_only=True) as con:
        status, slope = con.execute(
            "SELECT status, slope FROM translation_pixel_pooled"
        ).fetchone()
    assert status == "insufficient_data"
    assert slope is None


def test_rejected_source_does_not_block_valid_population(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    _write_parquet(_merged(root / "valid", R10C_1), [1, 2], [3, 5])
    corrupt = _merged(root / "corrupt", NIWO_1)
    corrupt.parent.mkdir(parents=True)
    corrupt.write_text("broken", encoding="utf-8")

    result = _run(root, tmp_path / "bulk")

    assert result["accepted_flightline_count"] == 1
    assert result["rejected_source_count"] == 1
    rejected = pq.read_table(str(result["rejected_sources"])).to_pylist()
    assert rejected[0]["canonical_flightline_id"] == NIWO_1
    assert "Parquet" in rejected[0]["rejection_reason"]


def test_output_must_be_fresh_and_outside_read_only_source(tmp_path: Path) -> None:
    root = tmp_path / "staging"
    _write_parquet(_merged(root / "valid", R10C_1), [1, 2], [3, 5])
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "unrelated.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="outside"):
        _run(root, root / "bulk")
    with pytest.raises(FileExistsError, match="fresh"):
        _run(root, occupied)
    assert (occupied / "unrelated.txt").read_text(encoding="utf-8") == "keep"


def test_cli_requires_clean_output_and_defaults_to_virtual_full_data() -> None:
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["processed_data"])
    args = parser.parse_args(
        ["processed_data", "--output-dir", "bulk_output"]
    )
    assert args.input_kind == "full"
    assert args.materialize_observations is False
    assert args.preflight_only is False
    assert args.allow_no_translation is False
