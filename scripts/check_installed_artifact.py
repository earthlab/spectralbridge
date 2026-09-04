#!/usr/bin/env python3
"""Smoke-test an installed SpectralBridge artifact outside the checkout.

Run this script with the Python interpreter from a clean environment where a
built wheel or sdist has been installed. It deliberately uses tiny generated
inputs and never contacts NEON.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "spectralbridge-matplotlib-cache"),
)
os.environ.setdefault(
    "XDG_CACHE_HOME",
    str(Path(tempfile.gettempdir()) / "spectralbridge-xdg-cache"),
)

import h5py
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import spectralbridge
from spectralbridge import (
    go_forth_and_multiply,
    run_bulk_pipeline,
    run_drone_pipeline,
)
from spectralbridge.neon_to_envi import neon_to_envi_no_hytools
from spectralbridge.utils.paths import get_package_data_path


RUNTIME_RESOURCES = (
    "hyperspectral_bands.json",
    "landsat_band_parameters.json",
    "drone_field_manifest.csv",
    "brightness/landsat_to_micasense.json",
    "brightness/landsat_tm_etm_to_micasense.json",
)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _write_h5(path: Path, *, group_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavelengths = np.asarray([444.0, 560.0, 650.0, 862.0], dtype=np.float32)
    data = np.linspace(0.05, 0.8, 4 * 4 * 4, dtype=np.float32).reshape(4, 4, 4)
    map_info = np.asarray(
        [
            "UTM",
            "1",
            "1",
            "500000",
            "4420000",
            "1",
            "1",
            "13",
            "North",
            "WGS-84",
        ],
        dtype="S",
    )
    with h5py.File(path, "w") as h5_file:
        reflectance = h5_file.create_group(group_name).create_group("Reflectance")
        dataset = reflectance.create_dataset("Reflectance_Data", data=data)
        dataset.attrs["Data_Ignore_Value"] = np.float32(-9999.0)
        metadata = reflectance.create_group("Metadata")
        spectral = metadata.create_group("Spectral_Data")
        wave = spectral.create_dataset("Wavelength", data=wavelengths)
        wave.attrs["Units"] = "Nanometers"
        spectral.create_dataset(
            "FWHM", data=np.full(4, 10.0, dtype=np.float32)
        )
        coordinates = metadata.create_group("Coordinate_System")
        coordinates.create_dataset("Map_Info", data=map_info)
        coordinates.create_dataset(
            "Coordinate_System_String",
            data=np.asarray("EPSG:32613", dtype="S"),
        )


def _run_smoke(root: Path, *, expected_version: str | None) -> dict[str, object]:
    checkout = Path(__file__).resolve().parents[1]
    installed = Path(spectralbridge.__file__).resolve()
    if _is_within(installed, checkout):
        raise RuntimeError(
            "spectralbridge imported from the repository checkout instead of an "
            f"installed artifact: {installed}"
        )
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

    resources = [get_package_data_path(name) for name in RUNTIME_RESOURCES]
    missing = [path for path in resources if not path.is_file()]
    if missing:
        raise RuntimeError(f"Installed runtime resources are missing: {missing}")

    neon_h5 = (
        root
        / "normal"
        / "NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance.h5"
    )
    _write_h5(neon_h5, group_name="NIWO")
    normal_result = neon_to_envi_no_hytools(
        [str(neon_h5)],
        str(root / "normal_output"),
        interactive_mode=False,
    )[0]
    for kind in ("img", "hdr"):
        if not Path(normal_result[kind]).is_file():
            raise RuntimeError(f"Normal H5-to-ENVI smoke did not write {kind}")

    drone_h5 = root / "AOP-TEST-09-04-26-ExportPackage" / "drone.h5"
    _write_h5(drone_h5, group_name="DRONE")
    drone_result = run_drone_pipeline(
        drone_h5,
        output_dir=root / "drone_output",
        apply_topo=False,
        apply_brdf=False,
    )
    if len(drone_result["processed"]) != 1 or drone_result["failed"]:
        raise RuntimeError(f"Drone orchestration smoke failed: {drone_result}")
    if not Path(drone_result["qa_summary_path"]).is_file():
        raise RuntimeError("Drone orchestration smoke did not write its QA summary")

    bulk_source = root / "bulk_sources"
    identifiers = (
        "NEON_D10_R10C_DP1_L001-1_20210915_directional_reflectance",
        "NEON_D13_NIWO_DP1_L001-1_20230815_directional_reflectance",
        "NEON_D14_JORN_DP1_L001-1_20220701_directional_reflectance",
    )
    for index, flightline_id in enumerate(identifiers):
        table = pa.table(
            {
                "pixel_id": [f"p{index}_{row}" for row in range(4)],
                "MicaSense_to-match_OLI_and_OLI-2_band_1": [0.1, 0.2, 0.3, 0.4],
                "Landsat_8_OLI_band_1": [0.25, 0.45, 0.65, 0.85],
                "Landsat_8_OLI_band_1_error": [0, 0, 0, 0],
            }
        )
        path = (
            bulk_source
            / f"machine-{index}"
            / f"{flightline_id}_merged_pixel_extraction.parquet"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, path)

    bulk_result = run_bulk_pipeline(
        bulk_source,
        root / "bulk_output",
        threads=1,
        memory_limit="512MB",
    )
    if bulk_result["accepted_flightline_count"] != 3:
        raise RuntimeError(f"Bulk discovery smoke failed: {bulk_result}")
    if bulk_result["row_count"] != 12:
        raise RuntimeError(f"Bulk observation smoke failed: {bulk_result}")
    for key in ("database", "manifest", "coefficients_parquet", "coefficients_json"):
        if not Path(bulk_result[key]).is_file():
            raise RuntimeError(f"Bulk smoke did not write {key}: {bulk_result[key]}")
    loso = (
        root
        / "bulk_output"
        / "analyses"
        / "leave_one_site_out"
        / "leave_one_site_out.parquet"
    )
    if not loso.is_file():
        raise RuntimeError("Bulk smoke did not write leave-one-site-out results")

    return {
        "python": sys.version.split()[0],
        "spectralbridge_version": spectralbridge.__version__,
        "installed_from": str(installed),
        "runtime_resources": [str(path) for path in resources],
        "normal": "abbreviated_h5_to_envi_passed",
        "drone": "orchestration_passed_with_corrections_disabled",
        "bulk": "catalog_database_census_translation_loso_passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-version",
        help="Fail unless the installed package reports this exact version.",
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="spectralbridge-artifact-smoke-") as tmp:
        result = _run_smoke(Path(tmp), expected_version=args.expected_version)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
