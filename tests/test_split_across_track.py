from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from spectralbridge.half_flight import (
    across_track_slices,
    along_track_slices,
    classify_footprint_orientation,
    half_flight_id,
    plan_half_flight,
)
from spectralbridge.pipelines.pipeline import go_forth_and_multiply

from tests.test_neon_cube import _create_fake_neon_file


def _create_shaped_fake_neon_file(path: Path, *, n_lines: int, n_samples: int) -> None:
    wavelengths = np.array([400, 410, 420, 430, 440], dtype=np.float32)
    fwhm = np.array([10, 10, 10, 10, 10], dtype=np.float32)
    map_info = [
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
    ]
    data = np.zeros((n_lines, n_samples, 5), dtype=np.float32)
    for y in range(n_lines):
        for x in range(n_samples):
            for b in range(5):
                data[y, x, b] = y * 1000 + x * 10 + b

    with h5py.File(path, "w") as h5_file:
        base_group = h5_file.create_group("TEST_KEY")
        reflectance_group = base_group.create_group("Reflectance")
        reflectance_dataset = reflectance_group.create_dataset(
            "Reflectance_Data", data=data, dtype=np.float32
        )
        reflectance_dataset.attrs["Data_Ignore_Value"] = np.float32(-9999.0)
        reflectance_dataset.attrs["Scale_Factor"] = np.float32(1.0)

        metadata_group = reflectance_group.create_group("Metadata")
        spectral_group = metadata_group.create_group("Spectral_Data")
        wavelength_ds = spectral_group.create_dataset("Wavelength", data=wavelengths)
        wavelength_ds.attrs["Units"] = "Nanometers"
        spectral_group.create_dataset("FWHM", data=fwhm)

        coordinate_group = metadata_group.create_group("Coordinate_System")
        coordinate_group.create_dataset("Map_Info", data=np.array(map_info, dtype="S"))
        coordinate_group.create_dataset(
            "Coordinate_System_String",
            data=np.bytes_("PROJCS[\"WGS_1984_UTM_Zone_13N\"]"),
        )


def test_across_track_slices_gives_right_the_remainder() -> None:
    assert across_track_slices(20) == {"left": (0, 10), "right": (10, 20)}
    assert across_track_slices(21) == {"left": (0, 10), "right": (10, 21)}


def test_along_track_slices_gives_right_the_remainder() -> None:
    assert along_track_slices(20) == {"left": (0, 10), "right": (10, 20)}
    assert along_track_slices(21) == {"left": (0, 10), "right": (10, 21)}


def test_classify_footprint_orientation() -> None:
    assert (
        classify_footprint_orientation(n_lines=100, n_samples=40)
        == "north_south"
    )
    assert (
        classify_footprint_orientation(n_lines=40, n_samples=100)
        == "east_west"
    )
    assert (
        classify_footprint_orientation(n_lines=50, n_samples=50)
        == "north_south"
    )


def test_half_flight_id() -> None:
    orig = "NEON_D12_YELL_DP1_L050-1_20230703_directional_reflectance"
    assert half_flight_id(orig, "left").endswith("_left")
    assert half_flight_id(orig, "right").endswith("_right")


def test_plan_half_flight_ns_uses_left_right_line_windows(tmp_path: Path) -> None:
    h5 = tmp_path / "ns.h5"
    _create_shaped_fake_neon_file(h5, n_lines=20, n_samples=10)
    orientation, windows = plan_half_flight(h5)
    assert orientation == "north_south"
    assert [w.side for w in windows] == ["left", "right"]
    assert windows[0].line_start == 0 and windows[0].line_stop == 10
    assert windows[1].line_start == 10 and windows[1].line_stop == 20
    assert windows[0].sample_start == 0 and windows[0].sample_stop == 10


def test_plan_half_flight_ew_uses_left_right(tmp_path: Path) -> None:
    h5 = tmp_path / "ew.h5"
    _create_shaped_fake_neon_file(h5, n_lines=10, n_samples=20)
    orientation, windows = plan_half_flight(h5)
    assert orientation == "east_west"
    assert [w.side for w in windows] == ["left", "right"]
    assert windows[0].sample_start == 0 and windows[0].sample_stop == 10
    assert windows[1].sample_start == 10 and windows[1].sample_stop == 20
    assert windows[0].line_start == 0 and windows[0].line_stop == 10


def test_go_forth_split_across_track_ns_expands_left_right_line_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    orig = "NEON_D12_YELL_DP1_L050-1_20230703_directional_reflectance"
    captured: list[dict] = []

    def _fake_download(*, base_folder, flight_stem, **_kwargs):
        dest = Path(base_folder) / f"{flight_stem}.h5"
        _create_shaped_fake_neon_file(dest, n_lines=20, n_samples=10)
        return dest

    def _fake_process(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(
        "spectralbridge.pipelines.pipeline.stage_download_h5", _fake_download
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.pipeline.process_one_flightline", _fake_process
    )

    go_forth_and_multiply(
        base_folder=tmp_path,
        site_code="YELL",
        year_month="2023-07",
        flight_lines=[orig],
        engine="thread",
        max_workers=1,
        split_across_track=True,
    )

    assert [item["flight_stem"] for item in captured] == [
        f"{orig}_left",
        f"{orig}_right",
    ]
    source = (tmp_path / f"{orig}.h5").resolve()
    assert all(Path(item["source_h5"]).resolve() == source for item in captured)
    assert captured[0]["line_start"] == 0
    assert captured[0]["line_stop"] == 10
    assert captured[1]["line_start"] == 10
    assert captured[1]["line_stop"] == 20
    assert captured[0]["sample_start"] == 0
    assert captured[0]["sample_stop"] == 10
    assert (tmp_path / f"{orig}_left").is_dir()
    assert (tmp_path / f"{orig}_right").is_dir()
    assert not (tmp_path / orig).exists()


def test_go_forth_split_across_track_ew_expands_left_right(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    orig = "NEON_D16_WREF_DP1_L052-1_20230625_directional_reflectance"
    captured: list[dict] = []

    def _fake_download(*, base_folder, flight_stem, **_kwargs):
        dest = Path(base_folder) / f"{flight_stem}.h5"
        _create_shaped_fake_neon_file(dest, n_lines=10, n_samples=20)
        return dest

    monkeypatch.setattr(
        "spectralbridge.pipelines.pipeline.stage_download_h5", _fake_download
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.pipeline.process_one_flightline",
        lambda **kwargs: captured.append(kwargs),
    )

    go_forth_and_multiply(
        base_folder=tmp_path,
        site_code="WREF",
        year_month="2023-06",
        flight_lines=[orig],
        engine="thread",
        max_workers=1,
        split_across_track=True,
    )

    assert [item["flight_stem"] for item in captured] == [
        f"{orig}_left",
        f"{orig}_right",
    ]
    assert captured[0]["sample_start"] == 0
    assert captured[0]["sample_stop"] == 10
    assert captured[1]["sample_start"] == 10
    assert captured[1]["sample_stop"] == 20
    assert captured[0]["line_start"] == 0
    assert captured[0]["line_stop"] == 10


def test_go_forth_default_is_still_one_task_per_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    orig = "NEON_D12_YELL_DP1_L050-1_20230703_directional_reflectance"
    captured: list[dict] = []

    monkeypatch.setattr(
        "spectralbridge.pipelines.pipeline.stage_download_h5",
        lambda **kwargs: tmp_path / f"{kwargs['flight_stem']}.h5",
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.pipeline.process_one_flightline",
        lambda **kwargs: captured.append(kwargs),
    )
    (tmp_path / f"{orig}.h5").write_bytes(b"")

    go_forth_and_multiply(
        base_folder=tmp_path,
        site_code="YELL",
        year_month="2023-07",
        flight_lines=[orig],
        engine="thread",
        max_workers=1,
    )

    assert [item["flight_stem"] for item in captured] == [orig]
    assert captured[0]["source_h5"] is None
    assert captured[0]["sample_start"] is None
    assert captured[0]["sample_stop"] is None
    assert captured[0]["line_start"] is None
    assert captured[0]["line_stop"] is None


def test_read_neon_cube_line_slice_shifts_northing(tmp_path: Path) -> None:
    from spectralbridge.io.neon import read_neon_cube

    h5 = tmp_path / "fake_neon.h5"
    _create_fake_neon_file(h5)
    full, _, full_meta = read_neon_cube(h5)
    bottom, _, bottom_meta = read_neon_cube(h5, line_slice=(10, 20))

    assert bottom.shape == (10, 20, 5)
    np.testing.assert_array_equal(bottom, full[10:20, :, :])
    assert bottom_meta["line_start"] == 10
    assert bottom_meta["line_stop"] == 20
    assert float(bottom_meta["map_info"][4]) == float(full_meta["map_info"][4]) - 10.0
    assert bottom_meta["uly"] == pytest.approx(full_meta["uly"] - 10.0)
