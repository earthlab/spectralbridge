"""Production contracts for the independent bulk population pipeline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import rasterio
from rasterio.transform import from_origin

from spectralbridge import run_bulk_pipeline
from spectralbridge.bulk.catalog import (
    build_bulk_catalog,
    canonical_identity_from_product,
    discover_bulk_sources,
)
from spectralbridge.bulk.flightline_outputs import (
    ProductValidationError,
    discover_completed_flightlines,
    find_canonical_flightline_directories,
)
from spectralbridge.bulk.registry import (
    DEFAULT_PRODUCT_REGISTRY,
    AnalysisProfile,
    ProductDescriptor,
    ProductRegistry,
    TranslationPair,
)
from spectralbridge.cli.bulk_cli import _build_parser


MS_OLI = "MicaSense_to-match_OLI_and_OLI-2_band_1"
LS8 = "Landsat_8_OLI_band_1"
LS8_ERROR = "Landsat_8_OLI_band_1_error"
R10C_1 = "NEON_D10_R10C_DP1_L001-1_20210915_directional_reflectance"
R10C_2 = "NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance"
NIWO_1 = "NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance"
JORN_1 = "NEON_D14_JORN_DP1_L001-1_20220701_directional_reflectance"
YELL_1 = "NEON_D12_YELL_DP1_L099-1_20230715_directional_reflectance"


GENERIC_PAIR = TranslationPair(
    key="sensor_a_to_sensor_b",
    source_sensor="Sensor_A",
    target_sensor="Sensor_B",
    matching_group="visible_match",
    band_pairs=((1, 1),),
    expected_source_bands=1,
    expected_target_bands=1,
)
UNRELATED_PAIR = TranslationPair(
    key="sensor_c_to_sensor_d",
    source_sensor="Sensor_C",
    target_sensor="Sensor_D",
    matching_group="unrelated_match",
    band_pairs=((1, 1),),
)
GENERIC_REGISTRY = ProductRegistry(
    products=(
        ProductDescriptor(
            key="sensor_a_product",
            product_role="target_sensor",
            sensor_name="Sensor_A",
            matching_group="visible_match",
            filename_patterns=(r"^sensor_a(?:_copy)?\.img$",),
            processing_stage="sensor_translation",
            expected_band_count=1,
        ),
        ProductDescriptor(
            key="sensor_b_product",
            product_role="target_sensor",
            sensor_name="Sensor_B",
            matching_group="visible_match",
            filename_patterns=(r"^sensor_b\.img$",),
            processing_stage="sensor_translation",
            expected_band_count=1,
        ),
        ProductDescriptor(
            key="sensor_c_product",
            product_role="target_sensor",
            sensor_name="Sensor_C",
            matching_group="unrelated_match",
            filename_patterns=(r"^sensor_c\.img$",),
            processing_stage="sensor_translation",
            expected_band_count=1,
        ),
        ProductDescriptor(
            key="sensor_d_product",
            product_role="target_sensor",
            sensor_name="Sensor_D",
            matching_group="unrelated_match",
            filename_patterns=(r"^sensor_d\.img$",),
            processing_stage="sensor_translation",
            expected_band_count=1,
        ),
    ),
    translation_pairs=(GENERIC_PAIR, UNRELATED_PAIR),
)


def test_bulk_runtime_dependencies_and_cli_are_packaged() -> None:
    project = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    runtime_dependencies = project.split("[project.optional-dependencies]", 1)[0]

    for dependency in ('"pyarrow"', '"rasterio"', '"duckdb>=1.0.0"'):
        assert dependency in runtime_dependencies
    assert (
        'spectralbridge-bulk = "spectralbridge.cli.bulk_cli:main"' in project
    )


def test_default_registry_classifies_realistic_micasense_filenames() -> None:
    stem = "NEON_D13_NIWO_DP1_L019-1_20230815_directional_reflectance"
    cases = {
        f"{stem}_micasense_to_match_tm_etm+_envi.img": (
            "micasense_matched_tm_etm",
            "MicaSense_to-match_TM_and_ETM+",
            4,
        ),
        f"{stem}_micasense_to_match_oli_oli2_envi.img": (
            "micasense_matched_oli",
            "MicaSense_to-match_OLI_and_OLI-2",
            5,
        ),
    }

    for filename, expected in cases.items():
        descriptor = DEFAULT_PRODUCT_REGISTRY.recognize(filename)
        assert descriptor is not None
        assert (
            descriptor.key,
            descriptor.sensor_name,
            descriptor.expected_band_count,
        ) == expected


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


def _write_envi(path: Path, values: np.ndarray, *, nodata: float = -9999.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    array = np.asarray(values, dtype="float32")
    if array.ndim == 2:
        array = array[np.newaxis, :, :]
    with rasterio.open(
        path,
        "w",
        driver="ENVI",
        width=array.shape[2],
        height=array.shape[1],
        count=array.shape[0],
        dtype="float32",
        crs="EPSG:32613",
        transform=from_origin(500000, 4420000, 1, 1),
        nodata=nodata,
    ) as dataset:
        dataset.write(array)
    return path


def _completed_flightline(
    root: Path,
    outer: str,
    flightline_id: str,
    *,
    micasense: np.ndarray | None = None,
    landsat: np.ndarray | None = None,
    qa: bool = True,
) -> Path:
    directory = root / outer / flightline_id
    values = np.asarray(
        micasense
        if micasense is not None
        else [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
        dtype="float32",
    )
    target = np.asarray(
        landsat if landsat is not None else values * 2.0 + 0.1,
        dtype="float32",
    )
    micasense_cube = np.stack(
        [
            np.where(values == -9999.0, -9999.0, values + 0.01 * index)
            for index in range(5)
        ]
    )
    landsat_cube = np.stack(
        [
            np.where(target == -9999.0, -9999.0, target + 0.02 * index)
            for index in range(7)
        ]
    )
    _write_envi(
        directory / f"{flightline_id}_brdfandtopo_corrected_envi.img",
        values,
    )
    _write_envi(directory / f"{flightline_id}_envi.img", values)
    _write_envi(
        directory / f"{flightline_id}_micasense_to_match_oli_oli2_envi.img",
        micasense_cube,
    )
    _write_envi(
        directory / f"{flightline_id}_landsat_oli_envi.img",
        landsat_cube,
    )
    if qa:
        qa_path = directory / "qa" / "stages" / "04_spectral_convolution" / "stage_qa.json"
        qa_path.parent.mkdir(parents=True, exist_ok=True)
        qa_path.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    return directory


def _generic_flightline(
    root: Path,
    relative: str,
    flightline_id: str,
    *,
    sensor_a: bool = True,
    sensor_b: bool = True,
    qa: bool = False,
) -> Path:
    directory = root / relative
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "spectralbridge_flightline.json").write_text(
        json.dumps(
            {
                "flightline_id": flightline_id,
                "site": "SITE_GENERIC",
                "acquisition_date": "2024-06-15",
            }
        ),
        encoding="utf-8",
    )
    values = np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype="float32")
    if sensor_a:
        _write_envi(directory / "sensor_a.img", values)
    if sensor_b:
        _write_envi(directory / "sensor_b.img", values * 3.0 + 0.2)
    if qa:
        qa_path = directory / "qa" / "stage_qa.json"
        qa_path.parent.mkdir(parents=True, exist_ok=True)
        qa_path.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    return directory


def _target_only_default_flightline(
    root: Path,
    outer: str,
    flightline_id: str,
) -> Path:
    """Write the six target families used by the production staging contract."""

    directory = root / outer / flightline_id
    base = np.asarray([[0.1, 0.2], [0.3, 0.4]], dtype="float32")
    micasense_tm = np.stack([base + index * 0.01 for index in range(4)])
    micasense_oli = np.stack([base + index * 0.01 for index in range(5)])
    landsat_tm = np.stack(
        [
            *(micasense_tm[index] * 2.0 + 0.1 for index in range(4)),
            base + 0.5,
            base + 0.6,
        ]
    )
    landsat_oli = np.stack(
        [
            *(micasense_oli[index] * 2.0 + 0.1 for index in range(5)),
            base + 0.5,
            base + 0.6,
        ]
    )
    products = {
        "landsat_tm": landsat_tm,
        "landsat_etm+": landsat_tm,
        "landsat_oli": landsat_oli,
        "landsat_oli2": landsat_oli,
        "micasense_to_match_tm_etm+": micasense_tm,
        "micasense_to_match_oli_oli2": micasense_oli,
    }
    for suffix, values in products.items():
        _write_envi(directory / f"{flightline_id}_{suffix}_envi.img", values)
    return directory


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


def test_generic_merged_product_can_use_parent_identity_manifest(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "arbitrary" / "scientific_unit"
    directory.mkdir(parents=True)
    (directory / "spectralbridge_flightline.json").write_text(
        json.dumps({"flightline_id": "flight-generic"}),
        encoding="utf-8",
    )
    product = directory / "analysis_merged_pixel_extraction.parquet"
    _write_parquet(product, [0.1, 0.2], [0.3, 0.5])

    identity = canonical_identity_from_product(product)
    _, flightlines = build_bulk_catalog(tmp_path)

    assert identity["canonical_flightline_id"] == "flight-generic"
    assert identity["identity_source"] == "spectralbridge_flightline_manifest"
    assert flightlines[0].status == "accepted"


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
    assert result["input_mode"] == "merged_parquet"
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
    assert args.input_mode == "auto"
    assert args.input_kind == "full"
    assert args.materialize_observations is False
    assert args.preflight_only is False
    assert args.allow_no_translation is False
    assert args.analysis == "translation"
    assert args.sensors is None
    assert args.translation_pairs is None
    assert args.on_invalid == "exclude"

    selected = parser.parse_args(
        [
            "processed_data",
            "--output-dir",
            "bulk_output",
            "--sensor",
            "Sensor_A",
            "--sensor",
            "Sensor_B",
            "--translation-pair",
            "sensor_a_to_sensor_b",
            "--on-invalid",
            "error",
        ]
    )
    assert selected.sensors == ["Sensor_A", "Sensor_B"]
    assert selected.translation_pairs == ["sensor_a_to_sensor_b"]
    assert selected.on_invalid == "error"


def test_completed_archive_discovery_ignores_outer_batch_names(tmp_path: Path) -> None:
    root = tmp_path / "Aug_2026_Processed_Flightlines"
    niwo = _completed_flightline(root, "NIWO_a01", NIWO_1)
    _completed_flightline(root, "NIWO_a02", R10C_1)
    _completed_flightline(root, "worker_73", YELL_1)
    qa_path = next((niwo / "qa").rglob("stage_qa.json"))
    qa_path.write_text(
        json.dumps({"status": "WARN", "metrics": {"no_data_fraction": 0.125}}),
        encoding="utf-8",
    )

    directories = find_canonical_flightline_directories(root)
    sources, flightlines = discover_completed_flightlines(root)

    assert len(directories) == 3
    assert {item.canonical_flightline_id for item in flightlines} == {
        NIWO_1,
        R10C_1,
        YELL_1,
    }
    assert {item.site for item in flightlines} == {"NIWO", "R10C", "YELL"}
    assert all(item.identity_source == "canonical_neon_directory" for item in flightlines)
    assert all(item.translation_eligible for item in flightlines)
    assert all(item.status == "accepted" for item in flightlines)
    niwo_record = next(item for item in flightlines if item.site == "NIWO")
    assert niwo_record.qa_status == "warn"
    assert "no_data_fraction" in niwo_record.stage_qa_status_json
    assert {item.product_role for item in sources} == {
        "raw_hyperspectral",
        "corrected_hyperspectral",
        "target_sensor",
    }


def test_target_only_six_family_archive_completes_all_default_pairs(
    tmp_path: Path,
) -> None:
    root = tmp_path / "minimal_targets"
    directory = _target_only_default_flightline(
        root,
        "arbitrary_storage_folder",
        R10C_1,
    )

    sources, flightlines = discover_completed_flightlines(root)
    record = flightlines[0]
    source_by_sensor = {source.sensor_name: source for source in sources}
    eligibility = json.loads(record.analysis_eligibility_json)
    expected_sensors = {
        "Landsat_5_TM",
        "Landsat_7_ETM+",
        "Landsat_8_OLI",
        "Landsat_9_OLI-2",
        "MicaSense_to-match_TM_and_ETM+",
        "MicaSense_to-match_OLI_and_OLI-2",
    }

    assert directory.is_dir()
    assert len(sources) == 6
    assert set(source_by_sensor) == expected_sensors
    assert all(source.status == "available" for source in sources)
    assert source_by_sensor["MicaSense_to-match_TM_and_ETM+"].column_count == 4
    assert source_by_sensor["MicaSense_to-match_OLI_and_OLI-2"].column_count == 5
    assert source_by_sensor["MicaSense_to-match_TM_and_ETM+"].header_path == str(
        directory / f"{R10C_1}_micasense_to_match_tm_etm+_envi.hdr"
    )
    assert source_by_sensor["MicaSense_to-match_OLI_and_OLI-2"].header_path == str(
        directory / f"{R10C_1}_micasense_to_match_oli_oli2_envi.hdr"
    )
    assert json.loads(record.available_sensors_json) == sorted(expected_sensors)
    assert eligibility == {
        pair.key: True for pair in DEFAULT_PRODUCT_REGISTRY.translation_pairs
    }
    assert record.translation_eligible is True
    assert record.status == "accepted"
    assert record.processing_completeness == "minimal_analysis_archive"
    assert json.loads(record.corrected_product_json) == {}
    assert not any(source.product_role == "raw_hyperspectral" for source in sources)

    result = _run(root, tmp_path / "bulk", extraction_chunk_size=1)
    with duckdb.connect(str(result["database"]), read_only=True) as con:
        completed_pairs = {
            row[0]
            for row in con.execute(
                "SELECT DISTINCT translation_pair "
                "FROM translation_pixel_pooled WHERE status = 'ok'"
            ).fetchall()
        }

    assert result["accepted_flightline_count"] == 1
    assert completed_pairs == {
        pair.key for pair in DEFAULT_PRODUCT_REGISTRY.translation_pairs
    }


def test_completed_archive_duplicate_ids_are_all_excluded(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    _completed_flightline(root, "batch_A", NIWO_1)
    _completed_flightline(root, "batch_B", NIWO_1)

    sources, flightlines = discover_completed_flightlines(root)

    assert len(flightlines) == 2
    assert {item.status for item in flightlines} == {"duplicate_excluded"}
    assert all(item.duplicate_candidate_count == 2 for item in flightlines)
    assert {item.status for item in sources} == {"duplicate_excluded"}


def test_completed_archive_incomplete_products_are_classified(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    no_qa = _completed_flightline(root, "batch", NIWO_1, qa=False)
    missing_corrected = _completed_flightline(root, "batch", R10C_1)
    for path in missing_corrected.glob("*brdfandtopo_corrected_envi.*"):
        path.unlink()
    missing_micasense = _completed_flightline(root, "batch", YELL_1)
    for path in missing_micasense.glob("*micasense_to_match_oli_oli2_envi.*"):
        path.unlink()
    broken_header = _completed_flightline(root, "batch", JORN_1)
    header = next(broken_header.glob("*landsat_oli_envi.hdr"))
    header.write_text("not an ENVI header", encoding="utf-8")

    _, flightlines = discover_completed_flightlines(root)
    by_id = {item.canonical_flightline_id: item for item in flightlines}

    assert by_id[NIWO_1].status == "accepted"
    assert by_id[NIWO_1].qa_status == "missing"
    assert Path(by_id[NIWO_1].source_directory) == no_qa
    assert by_id[R10C_1].status == "accepted"
    assert by_id[R10C_1].processing_completeness == "partial"
    assert by_id[YELL_1].status == "rejected"
    assert "no requested compatible" in (by_id[YELL_1].rejection_reason or "")
    assert by_id[JORN_1].status == "rejected"
    assert "landsat_8_oli" in by_id[JORN_1].missing_products_json


def test_flightline_output_mode_preflight_is_metadata_only(tmp_path: Path) -> None:
    root = tmp_path / "Aug_2026_Processed_Flightlines"
    _completed_flightline(root, "NIWO_a01", NIWO_1)
    output = tmp_path / "Aug_2026_Bulk_Analysis"

    result = _run(root, output, preflight_only=True)
    census = json.loads(
        (output / "analyses" / "dataset_census" / "dataset_census.json").read_text()
    )

    assert result["input_mode"] == "flightline_outputs"
    assert result["accepted_flightline_count"] == 1
    assert census["observation_scan_performed"] is False
    assert census["candidate_outer_batch_folders"] == 1
    assert census["raw_products_found"] == 1
    assert census["estimated_analysis_cache_bytes"] > 0
    assert not list((output / "cache").rglob("*.parquet"))
    products = pq.read_table(result["source_products"]).to_pylist()
    assert {item["product_role"] for item in products} == {
        "raw_hyperspectral",
        "corrected_hyperspectral",
        "target_sensor",
    }


def test_tiny_chunked_flightline_extraction_and_restart(tmp_path: Path) -> None:
    root = tmp_path / "Aug_2026_Processed_Flightlines"
    micasense = np.asarray([[0.1, 0.2, -9999.0], [0.4, 0.5, 0.6]], dtype="float32")
    landsat = np.where(micasense == -9999.0, -9999.0, micasense * 2.0 + 0.1)
    source_dir = _completed_flightline(
        root,
        "NIWO_a01",
        NIWO_1,
        micasense=micasense,
        landsat=landsat,
    )
    source_hashes = {path: _sha256(path) for path in source_dir.rglob("*") if path.is_file()}
    output = tmp_path / "Aug_2026_Bulk_Analysis"

    first = _run(root, output, extraction_chunk_size=2)
    observations = output / "cache" / NIWO_1 / "observations.parquet"
    sensor_cache = (
        output
        / "cache"
        / NIWO_1
        / "MicaSense_to_match_OLI_and_OLI_2.parquet"
    )
    metadata = json.loads(
        (output / "cache" / NIWO_1 / "extraction_metadata.json").read_text()
    )
    first_mtime = observations.stat().st_mtime_ns
    table = pq.read_table(observations)
    reused = _run(root, output, extraction_chunk_size=2)

    assert first["input_mode"] == "flightline_outputs"
    assert first["row_count"] == 5
    assert table.num_rows == 5
    assert "MicaSense_to-match_OLI_and_OLI-2_band_1" in table.column_names
    assert "Landsat_8_OLI_band_1" in table.column_names
    assert pq.ParquetFile(sensor_cache).metadata.num_row_groups > 1
    assert metadata["validity_filters"] == ["finite", "not ENVI nodata"]
    assert metadata["source_directory"] == source_dir.as_posix()
    assert reused["status"] == "reused"
    assert observations.stat().st_mtime_ns == first_mtime
    assert {path: _sha256(path) for path in source_hashes} == source_hashes
    with duckdb.connect(str(first["database"]), read_only=True) as con:
        slope = con.execute("SELECT slope FROM translation_pixel_pooled").fetchone()[0]
    assert slope == pytest.approx(2.0)


def test_flightline_extraction_failure_isolated_from_other_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "archive"
    _completed_flightline(root, "batch_a", NIWO_1)
    _completed_flightline(root, "batch_b", R10C_1)
    from spectralbridge.pipelines import bulk as bulk_module

    real_extract = bulk_module.extract_flightline_cache

    def fail_one(item, *args, **kwargs):
        if item.canonical_flightline_id == NIWO_1:
            raise RuntimeError("synthetic extraction failure")
        return real_extract(item, *args, **kwargs)

    monkeypatch.setattr(bulk_module, "extract_flightline_cache", fail_one)
    result = _run(root, tmp_path / "bulk", extraction_chunk_size=2)
    records = pq.read_table(result["flightlines"]).to_pylist()

    assert result["accepted_flightline_count"] == 1
    failed = next(item for item in records if item["canonical_flightline_id"] == NIWO_1)
    assert failed["extraction_status"] == "failure"
    assert "synthetic extraction failure" in failed["rejection_reason"]


def test_generic_manifest_identity_and_target_only_archive_are_analysis_ready(
    tmp_path: Path,
) -> None:
    root = tmp_path / "generic_archive"
    _generic_flightline(root, "storage_one/flight_alpha", "flight-alpha")
    _generic_flightline(root, "storage_one/flight_beta", "flight-beta")
    _generic_flightline(
        root,
        "nested/any/layout/flight_gamma",
        "flight-gamma",
        qa=True,
    )

    result = _run(
        root,
        tmp_path / "generic_bulk",
        analysis="translation",
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
        extraction_chunk_size=1,
    )
    records = pq.read_table(result["flightlines"]).to_pylist()

    assert result["accepted_flightline_count"] == 3
    assert {item["canonical_flightline_id"] for item in records} == {
        "flight-alpha",
        "flight-beta",
        "flight-gamma",
    }
    assert {item["processing_completeness"] for item in records} == {
        "minimal_analysis_archive"
    }
    assert all(item["identity_source"] == "spectralbridge_flightline_manifest" for item in records)
    assert result["preflight"]["analysis_profile"] == "translation"
    assert result["preflight"]["census"]["selected_source_bytes"] > 0
    assert result["preflight"]["discovered_flightlines"] == 3
    assert result["preflight"]["available_sensors"] == ["Sensor_A", "Sensor_B"]
    assert result["spectralbridge_version"]
    products = pq.read_table(result["source_products"]).to_pylist()
    target = next(item for item in products if item["sensor_name"] == "Sensor_A")
    assert target["matching_group"] == "visible_match"
    assert target["processing_stage"] == "sensor_translation"
    assert target["dtype"] == "float32"
    assert json.loads(target["dimensions_json"])["bands"] == 1
    with duckdb.connect(result["database"], read_only=True) as con:
        row = con.execute(
            "SELECT source_sensor, target_sensor, slope "
            "FROM translation_pixel_pooled"
        ).fetchone()
    assert row[:2] == ("Sensor_A", "Sensor_B")
    assert row[2] == pytest.approx(3.0)


@pytest.mark.parametrize(
    ("mutation", "reason_code"),
    (
        ("missing_target", "incomplete_translation_pair"),
        ("missing_header", "missing_sidecar"),
        ("zero_byte", "zero_byte_file"),
        ("malformed_header", "unreadable_metadata"),
        ("duplicate_target", "duplicate_product"),
    ),
)
def test_generic_required_product_failures_have_structured_reason_codes(
    tmp_path: Path,
    mutation: str,
    reason_code: str,
) -> None:
    root = tmp_path / "archive"
    directory = _generic_flightline(root, "container/flight", "flight-one")
    if mutation == "missing_target":
        for path in directory.glob("sensor_b.*"):
            path.unlink()
    elif mutation == "missing_header":
        (directory / "sensor_b.hdr").unlink()
    elif mutation == "zero_byte":
        (directory / "sensor_b.img").write_bytes(b"")
    elif mutation == "malformed_header":
        (directory / "sensor_b.hdr").write_text("invalid header", encoding="utf-8")
    elif mutation == "duplicate_target":
        _write_envi(directory / "sensor_a_copy.img", np.ones((2, 2), dtype="float32"))

    result = _run(
        root,
        tmp_path / f"bulk_{mutation}",
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
        preflight_only=True,
    )
    exclusions = pq.read_table(result["exclusions"]).to_pylist()

    assert result["accepted_flightline_count"] == 0
    assert reason_code in {item["reason_code"] for item in exclusions}
    assert Path(result["exclusions_json"]).is_file()
    assert Path(result["exclusions_csv"]).is_file()
    assert not list((tmp_path / f"bulk_{mutation}" / "cache").rglob("*.parquet"))


def test_invalid_flightline_is_excluded_while_valid_population_continues(
    tmp_path: Path,
) -> None:
    root = tmp_path / "archive"
    _generic_flightline(root, "same_parent/valid", "valid-flight")
    invalid = _generic_flightline(root, "same_parent/invalid", "invalid-flight")
    (invalid / "sensor_b.img").write_bytes(b"")

    result = _run(
        root,
        tmp_path / "bulk",
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
        extraction_chunk_size=1,
    )
    exclusions = pq.read_table(result["exclusions"]).to_pylist()

    assert result["accepted_flightline_count"] == 1
    assert result["row_count"] == 4
    assert {item["canonical_flightline_id"] for item in exclusions} == {
        "invalid-flight"
    }
    assert {item["reason_code"] for item in exclusions} >= {
        "zero_byte_file",
        "incomplete_translation_pair",
    }


def test_requested_pair_does_not_require_unrelated_registered_sensors(
    tmp_path: Path,
) -> None:
    root = tmp_path / "archive"
    _generic_flightline(root, "arbitrary/flight", "selected-pair-flight")

    result = _run(
        root,
        tmp_path / "bulk",
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
        preflight_only=True,
    )
    record = pq.read_table(result["flightlines"]).to_pylist()[0]

    assert record["status"] == "accepted"
    assert json.loads(record["analysis_eligibility_json"]) == {
        GENERIC_PAIR.key: True
    }
    assert json.loads(record["missing_products_json"]) == []
    assert result["selected_translation_pairs"] == [GENERIC_PAIR.key]


def test_duplicate_generic_identity_is_explicit_and_on_invalid_can_error(
    tmp_path: Path,
) -> None:
    root = tmp_path / "archive"
    _generic_flightline(root, "copy_a/flight", "duplicate-flight")
    _generic_flightline(root, "copy_b/flight", "duplicate-flight")
    output = tmp_path / "bulk"

    result = _run(
        root,
        output,
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
        preflight_only=True,
    )
    assert result["duplicate_count"] == 2
    assert {
        item["reason_code"]
        for item in pq.read_table(result["exclusions"]).to_pylist()
    } == {"duplicate_scientific_identity"}

    with pytest.raises(ValueError, match="excluded"):
        _run(
            root,
            tmp_path / "bulk_error",
            product_registry=GENERIC_REGISTRY,
            translation_pairs=[GENERIC_PAIR.key],
            preflight_only=True,
            on_invalid="error",
        )


def test_invalid_duplicate_candidates_keep_both_reason_codes(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    for relative in ("copy_a/flight", "copy_b/flight"):
        directory = _generic_flightline(root, relative, "duplicate-invalid")
        (directory / "sensor_b.img").write_bytes(b"")

    result = _run(
        root,
        tmp_path / "bulk",
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
        preflight_only=True,
    )
    reason_codes = {
        item["reason_code"]
        for item in pq.read_table(result["exclusions"]).to_pylist()
    }

    assert result["duplicate_count"] == 2
    assert {"duplicate_scientific_identity", "zero_byte_file"} <= reason_codes


def test_on_invalid_error_ignores_invalid_optional_product(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    directory = _generic_flightline(root, "one/flight", "valid-flight")
    (directory / "raw.img").write_bytes(b"")
    registry = ProductRegistry(
        products=(
            *GENERIC_REGISTRY.products,
            ProductDescriptor(
                key="optional_raw",
                product_role="raw_hyperspectral",
                filename_patterns=(r"^raw\.img$",),
            ),
        ),
        translation_pairs=GENERIC_REGISTRY.translation_pairs,
    )

    result = _run(
        root,
        tmp_path / "bulk",
        product_registry=registry,
        translation_pairs=[GENERIC_PAIR.key],
        preflight_only=True,
        on_invalid="error",
    )

    assert result["accepted_flightline_count"] == 1
    assert {
        item["reason_code"]
        for item in pq.read_table(result["exclusions"]).to_pylist()
    } == {"zero_byte_file"}


def test_transient_disappearance_becomes_a_product_exclusion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "archive"
    _generic_flightline(root, "container/flight", "transient-flight")
    from spectralbridge.bulk import flightline_outputs as outputs_module

    real_metadata = outputs_module._raster_metadata

    def disappear(path, header, **kwargs):
        if path.name == "sensor_b.img":
            path.unlink()
            raise ProductValidationError(
                "transient_source_disappeared",
                "source disappeared during discovery",
            )
        return real_metadata(path, header, **kwargs)

    monkeypatch.setattr(outputs_module, "_raster_metadata", disappear)
    sources, flightlines = discover_completed_flightlines(
        root,
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
    )

    assert flightlines[0].status == "rejected"
    assert "incomplete_translation_pair" in flightlines[0].exclusion_reason_codes_json
    assert "transient_source_disappeared" in {
        source.reason_code for source in sources
    }


def test_profile_can_require_qa_without_requiring_hyperspectral_sources(
    tmp_path: Path,
) -> None:
    root = tmp_path / "archive"
    _generic_flightline(root, "without_qa", "without-qa")
    _generic_flightline(root, "with_qa", "with-qa", qa=True)
    profile = AnalysisProfile(
        name="translation_with_qa",
        required_product_roles=("target_sensor",),
        require_translation_pair=True,
        require_qa=True,
    )

    _, records = discover_completed_flightlines(
        root,
        analysis_profile=profile,
        product_registry=GENERIC_REGISTRY,
        translation_pairs=[GENERIC_PAIR.key],
    )
    by_id = {item.canonical_flightline_id: item for item in records}

    assert by_id["with-qa"].status == "accepted"
    assert by_id["with-qa"].processing_completeness == "minimal_analysis_archive"
    assert by_id["without-qa"].status == "rejected"
    assert "missing_required_product" in by_id["without-qa"].exclusion_reason_codes_json
