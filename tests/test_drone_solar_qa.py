"""Read-only, time-explicit drone solar-position diagnostics."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import csv
import subprocess
import sys

import h5py
import numpy as np
import pytest

from spectralbridge.neon_cube import NeonCube
from spectralbridge.pipelines.drone import (
    _circular_angle_difference,
    diagnose_drone_h5_solar_geometry,
)


def _write_h5(path: Path, *, zenith: float = 89.0, azimuth: float = 12.0) -> Path:
    with h5py.File(path, "w") as h5_file:
        reflectance = h5_file.create_group("GOLDHILL/Reflectance")
        data = reflectance.create_dataset("Reflectance_Data", data=np.ones((4, 4, 2), dtype="f4"))
        data.attrs["Data_Ignore_Value"] = -9999.0
        metadata = reflectance.create_group("Metadata")
        spectral = metadata.create_group("Spectral_Data")
        wavelength = spectral.create_dataset("Wavelength", data=np.array([560.0, 650.0]))
        wavelength.attrs["Units"] = "Nanometers"
        spectral.create_dataset("FWHM", data=np.array([10.0, 10.0]))
        coords = metadata.create_group("Coordinate_System")
        coords.create_dataset("Map_Info", data=np.bytes_("UTM, 1, 1, 500000, 4430000, 1, -1, 13, North, WGS-84"))
        coords.create_dataset("Coordinate_System_String", data=np.bytes_("EPSG:32613"))
        logs = metadata.create_group("Logs")
        logs.create_dataset("Solar_Zenith_Angle", data=np.full((4, 4), zenith, dtype="f4"))
        logs.create_dataset("Solar_Azimuth_Angle", data=np.full((4, 4), azimuth, dtype="f4"))
        metadata["Solar_Zenith_Angle"] = logs["Solar_Zenith_Angle"]
        metadata["Solar_Azimuth_Angle"] = logs["Solar_Azimuth_Angle"]
    return path


def test_aware_time_agreement_preserves_source_angles(tmp_path: Path) -> None:
    path = _write_h5(tmp_path / "flight.h5")
    acquisition = datetime(2023, 8, 15, 19, 53, 7, tzinfo=timezone.utc)
    first = diagnose_drone_h5_solar_geometry(path, acquisition_datetime=acquisition)
    expected = first["candidate_positions"]["timezone-aware"]
    with h5py.File(path, "r+") as h5_file:
        logs = h5_file["GOLDHILL/Reflectance/Metadata/Logs"]
        logs["Solar_Zenith_Angle"][:] = expected["zenith_deg"]
        logs["Solar_Azimuth_Angle"][:] = expected["azimuth_deg"]
    mtime = path.stat().st_mtime_ns
    result = diagnose_drone_h5_solar_geometry(path, acquisition_datetime=acquisition)
    assert result["solar_geometry_consistency_status"] == "PASS"
    assert result["source_solar_zenith"]["original_path"].endswith("Logs/Solar_Zenith_Angle")
    assert result["solar_zenith_difference_deg"] == pytest.approx(0, abs=1e-4)
    assert path.stat().st_mtime_ns == mtime
    np.testing.assert_allclose(
        NeonCube(path).get_ancillary("solar_zn", radians=True),
        np.deg2rad(expected["zenith_deg"]),
        atol=1e-6,
    )


def test_in_range_89_degrees_is_flagged_with_verified_utc_time(tmp_path: Path) -> None:
    path = _write_h5(tmp_path / "flight.h5")
    result = diagnose_drone_h5_solar_geometry(
        path,
        acquisition_datetime=datetime(2023, 8, 15, 19, 53, 7, tzinfo=timezone.utc),
    )
    assert result["solar_geometry_consistency_status"] == "FAIL"
    assert result["expected_solar_zenith_deg"] < 50
    assert result["solar_zenith_difference_deg"] > 30


def test_naive_time_keeps_timezone_ambiguity_visible(tmp_path: Path) -> None:
    path = _write_h5(tmp_path / "flight.h5")
    when = datetime(2023, 8, 15, 19, 53, 7)
    unknown = diagnose_drone_h5_solar_geometry(
        path,
        acquisition_datetime=when,
        candidate_timezones=("UTC", "America/Denver"),
    )
    assert unknown["solar_geometry_consistency_status"] == "NOT_EVALUATED"
    assert unknown["expected_solar_zenith_deg"] is None
    assert abs(
        unknown["candidate_positions"]["UTC"]["zenith_deg"]
        - unknown["candidate_positions"]["America/Denver"]["zenith_deg"]
    ) > 20
    explicit = diagnose_drone_h5_solar_geometry(
        path, acquisition_datetime=when, naive_timezone="UTC"
    )
    assert explicit["solar_geometry_consistency_status"] == "FAIL"


def test_circular_azimuth_difference_wraps() -> None:
    assert _circular_angle_difference(359.0, 1.0) == pytest.approx(-2.0)
    assert _circular_angle_difference(1.0, 359.0) == pytest.approx(2.0)


def test_h5_azimuth_mean_is_circular_at_north(tmp_path: Path) -> None:
    path = _write_h5(tmp_path / "flight.h5")
    with h5py.File(path, "r+") as h5_file:
        h5_file["GOLDHILL/Reflectance/Metadata/Logs/Solar_Azimuth_Angle"][:] = (
            np.tile([359.0, 1.0, 359.0, 1.0], (4, 1))
        )
    result = diagnose_drone_h5_solar_geometry(
        path, acquisition_datetime=datetime(2023, 8, 15, 19, 53, tzinfo=timezone.utc)
    )
    assert result["supplied_solar_azimuth_circular_mean_deg"] == pytest.approx(0.0, abs=1e-5)
    assert result["solar_azimuth_mean"] == pytest.approx(180.0)


def test_source_fill_contamination_is_not_mistaken_for_position(tmp_path: Path) -> None:
    path = _write_h5(tmp_path / "flight.h5")
    with h5py.File(path, "r+") as h5_file:
        h5_file["GOLDHILL/Reflectance/Metadata/Logs/Solar_Zenith_Angle"][0, 0] = -9999.0
    result = diagnose_drone_h5_solar_geometry(
        path, acquisition_datetime=datetime(2023, 8, 15, 19, 53, tzinfo=timezone.utc)
    )
    assert result["solar_geometry_consistency_status"] == "NOT_EVALUATED"
    assert "fill" in result["solar_geometry_consistency_reason"]


def test_missing_time_or_georeference_is_not_evaluated(tmp_path: Path) -> None:
    path = _write_h5(tmp_path / "flight.h5")
    missing_time = diagnose_drone_h5_solar_geometry(path)
    assert missing_time["solar_geometry_consistency_status"] == "NOT_EVALUATED"
    assert "datetime" in missing_time["solar_geometry_consistency_reason"]
    with h5py.File(path, "r+") as h5_file:
        del h5_file["GOLDHILL/Reflectance/Metadata/Coordinate_System/Map_Info"]
    missing_position = diagnose_drone_h5_solar_geometry(
        path, acquisition_datetime=datetime(2023, 8, 15, 19, 53, tzinfo=timezone.utc)
    )
    assert missing_position["solar_geometry_consistency_status"] == "NOT_EVALUATED"
    assert "georeference" in missing_position["solar_geometry_consistency_reason"]


def test_read_only_census_reports_manifest_date_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "flights"
    root.mkdir()
    path = _write_h5(root / "AOP_GOLDHILL_20230814__working.h5")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "Plot,Day of data collection,Mean Time of data collection (24 hr clock)\n"
        "AOP-GOLDHILL,2023-08-15,19:53:07\n",
        encoding="utf-8",
    )
    output = tmp_path / "validation" / "solar.csv"
    script = Path(__file__).resolve().parents[1] / "scripts" / "diagnose_drone_solar_geometry.py"
    original_mtime = path.stat().st_mtime_ns
    subprocess.run(
        [sys.executable, str(script), str(root), "--output", str(output), "--manifest", str(manifest), "--candidate-timezone", "UTC"],
        check=True,
        capture_output=True,
        text=True,
    )
    with output.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["h5_path"] == str(path)
    assert rows[0]["manifest_date_matches_filename"] == "False"
    assert rows[0]["status"] == "NOT_EVALUATED"
    assert "UTC" in rows[0]["candidate_positions_json"]
    assert path.stat().st_mtime_ns == original_mtime
