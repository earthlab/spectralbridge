#!/usr/bin/env python3
"""Run bounded, stage-complete smoke tests against an installed artifact.

Run this script with the Python interpreter from a clean environment where the
exact wheel or sdist under review has been installed. The generated fixtures
are deliberately tiny and non-representative. They exercise production code
paths and package wiring; they are not scientific or production-scale
validation.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
from typing import Iterator, Sequence

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "spectralbridge-matplotlib-cache"),
)
os.environ.setdefault(
    "XDG_CACHE_HOME",
    str(Path(tempfile.gettempdir()) / "spectralbridge-xdg-cache"),
)
os.environ.setdefault("RAY_DISABLE_AUTO_CONNECT", "1")
os.environ.setdefault("RAY_DISABLE_IMPORT_WARNING", "1")

import h5py
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.transform import from_origin

import spectralbridge
from spectralbridge import (
    go_forth_and_multiply,
    run_bulk_pipeline,
    run_drone_pipeline,
)
from spectralbridge.paths import FlightlinePaths
from spectralbridge.utils.paths import get_package_data_path


NORMAL_SHAPE = (8, 8, 32)
DRONE_SHAPE = (8, 8, 10)
PARQUET_CHUNK_SIZE = 8
MAX_WORKERS = 1
MAX_FIXTURE_BYTES = 2 * 1024 * 1024
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
NORMAL_FLIGHTLINE = "NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance"
DRONE_WAVELENGTHS_NM = (
    444.0,
    475.0,
    531.0,
    560.0,
    650.0,
    668.0,
    705.0,
    717.0,
    740.0,
    862.0,
)
RUNTIME_RESOURCES = (
    "hyperspectral_bands.json",
    "landsat_band_parameters.json",
    "drone_field_manifest.csv",
    "brightness/landsat_to_micasense.json",
    "brightness/landsat_tm_etm_to_micasense.json",
)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _assert_installed_outside_checkout(installed: Path, checkout: Path) -> None:
    if _is_within(installed, checkout):
        raise RuntimeError(
            "spectralbridge imported from the repository checkout instead of an "
            f"installed artifact: {installed}"
        )


def _assert_small_shape(shape: Sequence[int], *, label: str) -> None:
    values = tuple(int(value) for value in shape)
    if len(values) != 3 or any(value < 1 for value in values):
        raise RuntimeError(f"{label} must be a positive 3-D fixture shape: {values}")
    if values[0] > 16 or values[1] > 16 or values[2] > 64:
        raise RuntimeError(f"{label} exceeds the installed-smoke bounds: {values}")


def _tree_size(root: Path) -> int:
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def _assert_tree_is_bounded(root: Path, *, maximum_bytes: int) -> int:
    root = root.resolve()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"Smoke output contains an unexpected symlink: {path}")
        if not _is_within(path, root):
            raise RuntimeError(f"Smoke output escaped its temporary root: {path}")
    size = _tree_size(root)
    if size > maximum_bytes:
        raise RuntimeError(
            f"Smoke output used {size} bytes, exceeding the {maximum_bytes}-byte budget"
        )
    return size


@contextmanager
def _block_network() -> Iterator[None]:
    """Fail loudly if any smoke stage attempts an outbound socket connection."""

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def blocked_connect(self: socket.socket, address: object) -> None:
        del self
        raise RuntimeError(f"Network access is forbidden during artifact smoke: {address!r}")

    def blocked_connect_ex(self: socket.socket, address: object) -> int:
        blocked_connect(self, address)
        return 1  # pragma: no cover - blocked_connect always raises

    socket.socket.connect = blocked_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = blocked_connect_ex  # type: ignore[method-assign]
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = original_connect_ex  # type: ignore[method-assign]


def _fixture_data(lines: int, columns: int, wavelengths: np.ndarray) -> np.ndarray:
    y = np.linspace(0.0, 1.0, lines, dtype=np.float32)[:, None, None]
    x = np.linspace(0.0, 1.0, columns, dtype=np.float32)[None, :, None]
    wave = wavelengths.astype(np.float32)[None, None, :]
    spectral_slope = (wave - np.float32(wavelengths.min())) * np.float32(0.00008)
    red_absorption = np.float32(0.025) * np.exp(
        -((wave - np.float32(665.0)) / np.float32(45.0)) ** 2
    )
    spatial = np.float32(0.08) + np.float32(0.06) * y + np.float32(0.04) * x
    interaction = np.float32(0.01) * y * x
    return np.asarray(
        spatial + interaction + spectral_slope - red_absorption,
        dtype=np.float32,
    )


def _ancillary_data(lines: int, columns: int) -> dict[str, np.ndarray]:
    y, x = np.meshgrid(
        np.linspace(0.0, 1.0, lines, dtype=np.float32),
        np.linspace(0.0, 1.0, columns, dtype=np.float32),
        indexing="ij",
    )
    return {
        "Slope": np.asarray(4.0 + 8.0 * y + 2.0 * x, dtype=np.float32),
        "Aspect": np.asarray(20.0 + 110.0 * x + 15.0 * y, dtype=np.float32),
        "Solar_Zenith_Angle": np.asarray(28.0 + 5.0 * y + 2.0 * x, dtype=np.float32),
        "Solar_Azimuth_Angle": np.asarray(120.0 + 18.0 * x + 4.0 * y, dtype=np.float32),
        "To_Sensor_Zenith_Angle": np.asarray(3.0 + 9.0 * x + 2.0 * y, dtype=np.float32),
        "To_Sensor_Azimuth_Angle": np.asarray(15.0 + 35.0 * y + 8.0 * x, dtype=np.float32),
    }


def _write_h5(
    path: Path,
    *,
    group_name: str,
    shape: tuple[int, int, int],
    wavelengths_nm: Sequence[float] | None = None,
) -> None:
    _assert_small_shape(shape, label=path.name)
    lines, columns, bands = shape
    if wavelengths_nm is None:
        wavelengths = np.linspace(400.0, 2400.0, bands, dtype=np.float32)
    else:
        wavelengths = np.asarray(wavelengths_nm, dtype=np.float32)
    if wavelengths.shape != (bands,):
        raise RuntimeError(
            f"Wavelength count {wavelengths.size} does not match fixture bands {bands}"
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    map_info = np.asarray(
        [
            "UTM",
            "1.0",
            "1.0",
            "500000.0",
            "4420000.0",
            "1.0",
            "-1.0",
            "13",
            "North",
            "WGS-84",
        ],
        dtype="S",
    )
    with h5py.File(path, "w") as h5_file:
        reflectance = h5_file.create_group(group_name).create_group("Reflectance")
        dataset = reflectance.create_dataset(
            "Reflectance_Data",
            data=_fixture_data(lines, columns, wavelengths),
            dtype=np.float32,
        )
        dataset.attrs["Data_Ignore_Value"] = np.float32(-9999.0)
        dataset.attrs["Scale_Factor"] = np.float32(1.0)
        metadata = reflectance.create_group("Metadata")
        spectral = metadata.create_group("Spectral_Data")
        wave = spectral.create_dataset("Wavelength", data=wavelengths)
        wave.attrs["Units"] = "Nanometers"
        spectral.create_dataset(
            "FWHM", data=np.full(bands, 10.0, dtype=np.float32)
        )
        coordinates = metadata.create_group("Coordinate_System")
        coordinates.create_dataset("Map_Info", data=map_info)
        coordinates.create_dataset(
            "Coordinate_System_String",
            data=np.asarray("EPSG:32613", dtype="S"),
        )
        for name, values in _ancillary_data(lines, columns).items():
            metadata.create_dataset(name, data=values, dtype=np.float32)

    if path.stat().st_size > MAX_FIXTURE_BYTES:
        raise RuntimeError(f"Synthetic HDF5 fixture is unexpectedly large: {path}")


def _write_intersecting_polygon(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "FeatureCollection",
        "name": "installed_smoke_polygon",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::32613"},
        },
        "features": [
            {
                "type": "Feature",
                "properties": {"polygon_id": 1},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [500001.0, 4420001.0],
                            [500005.0, 4420001.0],
                            [500005.0, 4420005.0],
                            [500001.0, 4420005.0],
                            [500001.0, 4420001.0],
                        ]
                    ],
                },
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _assert_nonempty(path: Path) -> Path:
    path = Path(path)
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError(f"Expected nonempty smoke artifact: {path}")
    return path


def _assert_json(path: Path) -> dict[str, object]:
    payload = json.loads(_assert_nonempty(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")
    return payload


def _assert_envi(img: Path, hdr: Path) -> None:
    _assert_nonempty(img)
    _assert_nonempty(hdr)
    with rasterio.open(img) as dataset:
        if dataset.width < 1 or dataset.height < 1 or dataset.count < 1:
            raise RuntimeError(f"Unreadable ENVI dimensions: {img}")
        sample = dataset.read(1)
    if not np.any(np.isfinite(sample)):
        raise RuntimeError(f"ENVI sample contains no finite values: {img}")


def _assert_parquet(path: Path, *, minimum_rows: int = 1) -> pq.FileMetaData:
    path = _assert_nonempty(path)
    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows < minimum_rows or parquet.metadata.num_columns < 1:
        raise RuntimeError(f"Unreadable or empty Parquet artifact: {path}")
    table = parquet.read_row_group(0)
    finite_numeric = False
    for field in table.schema:
        if pa.types.is_floating(field.type) or pa.types.is_integer(field.type):
            values = table[field.name].to_numpy(zero_copy_only=False)
            if values.size and np.any(np.isfinite(values.astype(float, copy=False))):
                finite_numeric = True
                break
    if not finite_numeric:
        raise RuntimeError(f"Parquet sample contains no finite numeric values: {path}")
    return parquet.metadata


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_state(paths: Sequence[Path]) -> dict[str, tuple[int, int, str]]:
    return {
        str(path): (path.stat().st_size, path.stat().st_mtime_ns, _sha256(path))
        for path in paths
    }


def _run_normal(root: Path) -> dict[str, object]:
    started = time.monotonic()
    normal_root = root / "normal"
    h5_path = normal_root / f"{NORMAL_FLIGHTLINE}.h5"
    _write_h5(h5_path, group_name="NIWO", shape=NORMAL_SHAPE)

    kwargs = {
        "base_folder": normal_root,
        "site_code": "NIWO",
        "year_month": "2023-08",
        "flight_lines": [NORMAL_FLIGHTLINE],
        "engine": "thread",
        "max_workers": MAX_WORKERS,
        "parquet_chunk_size": PARQUET_CHUNK_SIZE,
        "merge_memory_limit_gb": 0.5,
        "merge_threads": 1,
        "merge_row_group_size": PARQUET_CHUNK_SIZE,
        "extraction_mode": "full",
        "topo_fit_mode": "scene",
        "qa_mode": "standard",
    }
    go_forth_and_multiply(**kwargs)

    paths = FlightlinePaths(normal_root, NORMAL_FLIGHTLINE)
    if paths.h5 != h5_path:
        raise RuntimeError("Normal smoke did not use the canonical HDF5 filename")
    _assert_envi(paths.envi_img, paths.envi_hdr)
    _assert_json(paths.corrected_json)
    _assert_nonempty(paths.brdf_model)
    _assert_envi(paths.corrected_img, paths.corrected_hdr)
    _assert_parquet(paths.envi_parquet)
    _assert_parquet(paths.corrected_parquet)
    for product in paths.sensor_products.values():
        _assert_envi(product.img, product.hdr)
        _assert_parquet(product.parquet)
    _assert_parquet(paths.merged_parquet)
    _assert_nonempty(paths.qa_png)
    _assert_json(paths.qa_json)
    stage_reports = sorted((paths.flight_dir / "qa").rglob("*.json"))
    if not stage_reports:
        raise RuntimeError("Normal smoke did not create stage QA JSON")

    restart_guarded = [
        paths.envi_img,
        paths.envi_hdr,
        paths.corrected_json,
        paths.brdf_model,
        paths.corrected_img,
        paths.corrected_hdr,
    ]
    for product in paths.sensor_products.values():
        restart_guarded.extend((product.img, product.hdr, product.parquet))
    before = _artifact_state(restart_guarded)
    go_forth_and_multiply(**kwargs)
    after = _artifact_state(restart_guarded)
    if before != after:
        changed = sorted(path for path in before if before[path] != after.get(path))
        raise RuntimeError(f"Normal restart recomputed valid stage artifacts: {changed}")

    return {
        "status": "stage_complete",
        "fixture_shape": list(NORMAL_SHAPE),
        "sensor_products": len(paths.sensor_products),
        "stage_qa_json_count": len(stage_reports),
        "restart_reused_core_artifacts": True,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def _assert_drone_result(result: dict[str, object], *, mode: str) -> None:
    if len(result["processed"]) != 1 or result["failed"]:
        raise RuntimeError(f"Drone {mode} smoke failed: {result}")
    audits = result["qa_summary"]["files"]
    if len(audits) != 1:
        raise RuntimeError(f"Drone {mode} smoke did not record one file audit")
    flags = audits[0]["flags"]
    if not flags.get("topo_applied") or not flags.get("brdf_applied"):
        raise RuntimeError(f"Drone {mode} corrections did not execute: {flags}")
    if not flags.get("convolution_skipped"):
        raise RuntimeError("Drone smoke unexpectedly ran convolution")
    _assert_nonempty(Path(str(audits[0]["working_raster_path"])))
    _assert_nonempty(Path(str(audits[0]["corrected_raster_path"])))
    _assert_nonempty(Path(str(audits[0]["qa_plot_path"])))
    _assert_json(Path(str(audits[0]["qa_json_path"])))
    _assert_json(Path(str(result["qa_summary_path"])))
    _assert_parquet(Path(str(result["merged"])))


def _run_drone(root: Path) -> dict[str, object]:
    started = time.monotonic()
    input_root = root / "drone_inputs"
    full_h5 = input_root / "AOP-FULL-09-04-26-ExportPackage" / "drone.h5"
    polygon_h5 = input_root / "AOP-POLYGON-09-04-26-ExportPackage" / "drone.h5"
    _write_h5(
        full_h5,
        group_name="DRONE",
        shape=DRONE_SHAPE,
        wavelengths_nm=DRONE_WAVELENGTHS_NM,
    )
    _write_h5(
        polygon_h5,
        group_name="DRONE",
        shape=DRONE_SHAPE,
        wavelengths_nm=DRONE_WAVELENGTHS_NM,
    )
    polygon_path = root / "drone_polygon.geojson"
    _write_intersecting_polygon(polygon_path)

    full = run_drone_pipeline(
        full_h5.parent,
        output_dir=root / "drone_full_output",
        apply_topo=True,
        apply_brdf=True,
        extraction_mode="full",
        parquet_chunk_size=PARQUET_CHUNK_SIZE,
    )
    _assert_drone_result(full, mode="full")
    full_audit = full["qa_summary"]["files"][0]
    _assert_parquet(Path(str(full_audit["full_extraction_path"])))

    polygon = run_drone_pipeline(
        polygon_h5.parent,
        polygon_path=polygon_path,
        output_dir=root / "drone_polygon_output",
        apply_topo=True,
        apply_brdf=True,
        extraction_mode="polygon",
        parquet_chunk_size=PARQUET_CHUNK_SIZE,
    )
    _assert_drone_result(polygon, mode="polygon")
    polygon_audit = polygon["qa_summary"]["files"][0]
    _assert_parquet(Path(str(polygon_audit["polygon_index_path"])))
    _assert_parquet(Path(str(polygon_audit["polygon_path"])))

    return {
        "status": "stage_complete_full_and_polygon",
        "fixture_shapes": [list(DRONE_SHAPE), list(DRONE_SHAPE)],
        "corrections": "topographic_and_brdf",
        "convolution": "intentionally_not_applicable",
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def _run_bulk(root: Path) -> dict[str, object]:
    started = time.monotonic()
    bulk_source = root / "Aug_2026_Processed_Flightlines"
    identifiers = (
        "NEON_D10_R10C_DP1_L001-1_20210915_directional_reflectance",
        NORMAL_FLIGHTLINE,
        "NEON_D14_JORN_DP1_L001-1_20220701_directional_reflectance",
    )
    for index, flightline_id in enumerate(identifiers):
        flightline_dir = bulk_source / f"worker-{index}" / flightline_id
        micasense = np.asarray(
            [[0.1, 0.2], [0.3, 0.4]], dtype=np.float32
        )
        landsat = micasense * np.float32(2.0) + np.float32(0.05)
        for suffix, values in (
            ("envi", micasense),
            ("brdfandtopo_corrected_envi", micasense),
            ("micasense_to_match_oli_oli2_envi", micasense),
            ("landsat_oli_envi", landsat),
        ):
            path = flightline_dir / f"{flightline_id}_{suffix}.img"
            path.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(
                path,
                "w",
                driver="ENVI",
                width=2,
                height=2,
                count=1,
                dtype="float32",
                crs="EPSG:32613",
                transform=from_origin(500000, 4420000, 1, 1),
                nodata=-9999.0,
            ) as dataset:
                dataset.write(values, 1)
        qa = flightline_dir / "qa" / "stages" / "04_spectral_convolution" / "stage_qa.json"
        qa.parent.mkdir(parents=True, exist_ok=True)
        qa.write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

    bulk_result = run_bulk_pipeline(
        bulk_source,
        root / "bulk_output",
        threads=1,
        memory_limit="512MB",
        row_group_size=PARQUET_CHUNK_SIZE,
        extraction_chunk_size=2,
        extraction_workers=1,
        materialize_observations=True,
    )
    if bulk_result["input_mode"] != "flightline_outputs":
        raise RuntimeError(f"Bulk archive auto-detection smoke failed: {bulk_result}")
    if bulk_result["accepted_flightline_count"] != 3:
        raise RuntimeError(f"Bulk discovery smoke failed: {bulk_result}")
    if bulk_result["row_count"] != 12:
        raise RuntimeError(f"Bulk observation smoke failed: {bulk_result}")
    for key in (
        "database",
        "manifest",
        "flightlines",
        "source_files",
        "source_products",
        "coefficients_parquet",
        "coefficients_json",
        "materialized_observations",
    ):
        _assert_nonempty(Path(str(bulk_result[key])))
    _assert_parquet(Path(str(bulk_result["flightlines"])))
    _assert_parquet(Path(str(bulk_result["source_files"])))
    _assert_parquet(Path(str(bulk_result["source_products"])))
    _assert_parquet(Path(str(bulk_result["coefficients_parquet"])))
    _assert_parquet(Path(str(bulk_result["materialized_observations"])), minimum_rows=12)
    _assert_json(Path(str(bulk_result["manifest"])))
    census = root / "bulk_output" / "analyses" / "dataset_census" / "dataset_census.json"
    loso = root / "bulk_output" / "analyses" / "leave_one_site_out" / "leave_one_site_out.parquet"
    _assert_json(census)
    _assert_parquet(loso)

    reused = run_bulk_pipeline(
        bulk_source,
        root / "bulk_output",
        threads=1,
        memory_limit="512MB",
        row_group_size=PARQUET_CHUNK_SIZE,
        extraction_chunk_size=2,
        extraction_workers=1,
        materialize_observations=True,
    )
    if reused["status"] != "reused":
        raise RuntimeError(f"Bulk restart did not reuse valid outputs: {reused}")

    return {
        "status": "flightline_archive_cache_database_translation_loso_materialization",
        "input_mode": "flightline_outputs",
        "fixture_flightlines": 3,
        "fixture_rows": 12,
        "restart_reused_outputs": True,
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def _resolve_runtime_resources() -> list[Path]:
    resources = [get_package_data_path(name) for name in RUNTIME_RESOURCES]
    missing = [path for path in resources if not path.is_file()]
    if missing:
        raise RuntimeError(f"Installed runtime resources are missing: {missing}")
    return resources


def _run_smoke(root: Path, *, expected_version: str | None) -> dict[str, object]:
    started = time.monotonic()
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    checkout = Path(__file__).resolve().parents[1]
    installed = Path(spectralbridge.__file__).resolve()
    _assert_installed_outside_checkout(installed, checkout)
    if expected_version is not None and spectralbridge.__version__ != expected_version:
        raise RuntimeError(
            f"Expected version {expected_version}, found {spectralbridge.__version__}"
        )
    for entry_point in (
        go_forth_and_multiply,
        run_drone_pipeline,
        run_bulk_pipeline,
    ):
        if not callable(entry_point):
            raise RuntimeError(f"Public entry point is not callable: {entry_point!r}")

    _assert_small_shape(NORMAL_SHAPE, label="normal fixture")
    _assert_small_shape(DRONE_SHAPE, label="drone fixture")
    resources = _resolve_runtime_resources()
    with _block_network():
        normal = _run_normal(root)
        drone = _run_drone(root)
        bulk = _run_bulk(root)
    output_bytes = _assert_tree_is_bounded(root, maximum_bytes=MAX_OUTPUT_BYTES)

    return {
        "validation_kind": "bounded_installed_artifact_smoke_not_scientific_validation",
        "python": sys.version.split()[0],
        "spectralbridge_version": spectralbridge.__version__,
        "installed_from": str(installed),
        "runtime_resources": [str(path) for path in resources],
        "normal": normal,
        "drone": drone,
        "bulk": bulk,
        "guardrails": {
            "network": "blocked",
            "max_workers": MAX_WORKERS,
            "parquet_chunk_size": PARQUET_CHUNK_SIZE,
            "maximum_output_bytes": MAX_OUTPUT_BYTES,
            "actual_output_bytes": output_bytes,
            "temporary_root": str(root),
        },
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-version",
        help="Fail unless the installed package reports this exact version.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Use an explicit empty work directory instead of a temporary directory.",
    )
    args = parser.parse_args()
    if args.work_dir is not None:
        work_dir = args.work_dir.expanduser().resolve()
        if work_dir.exists() and any(work_dir.iterdir()):
            raise RuntimeError(f"--work-dir must be empty: {work_dir}")
        result = _run_smoke(work_dir, expected_version=args.expected_version)
    else:
        with tempfile.TemporaryDirectory(prefix="spectralbridge-artifact-smoke-") as tmp:
            result = _run_smoke(Path(tmp), expected_version=args.expected_version)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
