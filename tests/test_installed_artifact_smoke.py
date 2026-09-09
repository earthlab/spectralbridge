"""Focused contracts for the installed-artifact smoke framework."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import socket
import sys
from types import ModuleType
from types import SimpleNamespace

import pytest

from spectralbridge.neon_cube import NeonCube


def _load_smoke_module() -> ModuleType:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_installed_artifact.py"
    spec = importlib.util.spec_from_file_location("spectralbridge_artifact_smoke", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load installed-artifact smoke script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SMOKE = _load_smoke_module()


def test_synthetic_h5_fixtures_are_tiny_and_structurally_valid(tmp_path: Path) -> None:
    normal = tmp_path / "normal.h5"
    drone = tmp_path / "drone.h5"
    SMOKE._write_h5(normal, group_name="NIWO", shape=SMOKE.NORMAL_SHAPE)
    SMOKE._write_h5(
        drone,
        group_name="DRONE",
        shape=SMOKE.DRONE_SHAPE,
        wavelengths_nm=SMOKE.DRONE_WAVELENGTHS_NM,
    )

    normal_cube = NeonCube(normal)
    drone_cube = NeonCube(drone)
    assert normal_cube.data.shape == SMOKE.NORMAL_SHAPE
    assert drone_cube.data.shape == SMOKE.DRONE_SHAPE
    assert normal.stat().st_size < SMOKE.MAX_FIXTURE_BYTES
    assert drone.stat().st_size < SMOKE.MAX_FIXTURE_BYTES
    assert normal_cube.get_ancillary("slope").shape == SMOKE.NORMAL_SHAPE[:2]
    assert drone_cube.get_ancillary("sensor_zn").shape == SMOKE.DRONE_SHAPE[:2]


def test_fixture_bounds_fail_loudly() -> None:
    with pytest.raises(RuntimeError, match="exceeds the installed-smoke bounds"):
        SMOKE._assert_small_shape((17, 8, 10), label="oversized")


def test_output_budget_and_temp_root_containment(tmp_path: Path) -> None:
    artifact = tmp_path / "nested" / "artifact.bin"
    artifact.parent.mkdir()
    artifact.write_bytes(b"1234")
    assert SMOKE._assert_tree_is_bounded(tmp_path, maximum_bytes=4) == 4
    with pytest.raises(RuntimeError, match="exceeding"):
        SMOKE._assert_tree_is_bounded(tmp_path, maximum_bytes=3)


def test_network_guard_rejects_socket_connections() -> None:
    with SMOKE._block_network(), socket.socket() as client:
        with pytest.raises(RuntimeError, match="Network access is forbidden"):
            client.connect(("127.0.0.1", 9))


def test_checkout_import_is_rejected(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    installed = checkout / "src" / "spectralbridge" / "__init__.py"
    installed.parent.mkdir(parents=True)
    installed.touch()
    with pytest.raises(RuntimeError, match="repository checkout"):
        SMOKE._assert_installed_outside_checkout(installed, checkout)


def test_missing_runtime_resource_fails_loudly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing-resource"
    monkeypatch.setattr(SMOKE, "get_package_data_path", lambda _name: missing)
    with pytest.raises(RuntimeError, match="runtime resources are missing"):
        SMOKE._resolve_runtime_resources()


def test_bulk_smoke_runs_streaming_statistics_and_restart(tmp_path: Path) -> None:
    result = SMOKE._run_bulk(tmp_path)
    assert result["input_mode"] == "flightline_outputs"
    assert result["fixture_flightlines"] == 3
    assert result["fixture_rows"] == 12
    assert result["restart_reused_outputs"] is True
    assert result["pixel_materialization"] is False
    assert all(path.is_relative_to(tmp_path) for path in tmp_path.rglob("*"))


def test_spectral_library_smoke_runs_preflight_and_reporting(tmp_path: Path) -> None:
    result = SMOKE._run_spectral_library(tmp_path)
    assert result["status"] == "preflight_and_compact_reporting"
    assert result["fixture_rows"] == 4
    assert result["source_reused_in_place"] is True


def test_primary_console_script_contract_is_complete() -> None:
    assert SMOKE._validate_console_scripts() == list(SMOKE.PRIMARY_CONSOLE_SCRIPTS)


def test_distribution_metadata_is_distinct_from_import_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed = SimpleNamespace(
        metadata={"Name": "earthlab-spectralbridge"}, version="2.3.0rc1"
    )
    monkeypatch.setattr(SMOKE, "distribution", lambda _name: installed)
    assert SMOKE._validate_distribution_metadata("2.3.0rc1") == {
        "distribution_name": "earthlab-spectralbridge",
        "distribution_version": "2.3.0rc1",
        "import_package": "spectralbridge",
    }


def test_distribution_metadata_rejects_old_distribution_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed = SimpleNamespace(metadata={"Name": "spectralbridge"}, version="2.3.0rc1")
    monkeypatch.setattr(SMOKE, "distribution", lambda _name: installed)
    with pytest.raises(RuntimeError, match="Expected distribution earthlab-spectralbridge"):
        SMOKE._validate_distribution_metadata("2.3.0rc1")
