from __future__ import annotations

from pathlib import Path

import pytest

from spectralbridge.half_flight import across_track_slices, half_flight_id
from spectralbridge.pipelines.pipeline import go_forth_and_multiply

from tests.test_neon_cube import _create_fake_neon_file


def test_across_track_slices_gives_right_the_remainder() -> None:
    assert across_track_slices(20) == {"left": (0, 10), "right": (10, 20)}
    assert across_track_slices(21) == {"left": (0, 10), "right": (10, 21)}


def test_half_flight_id() -> None:
    orig = "NEON_D12_YELL_DP1_L050-1_20230703_directional_reflectance"
    assert half_flight_id(orig, "left").endswith("_left")
    assert half_flight_id(orig, "right").endswith("_right")


def test_go_forth_split_across_track_expands_two_halves_from_one_h5(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    orig = "NEON_D12_YELL_DP1_L050-1_20230703_directional_reflectance"
    captured: list[dict] = []

    def _fake_download(*, base_folder, flight_stem, **_kwargs):
        dest = Path(base_folder) / f"{flight_stem}.h5"
        _create_fake_neon_file(dest)
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
    source = str((tmp_path / f"{orig}.h5").resolve())
    assert all(item["source_h5"] == str(tmp_path / f"{orig}.h5") or Path(item["source_h5"]).resolve() == Path(source) for item in captured)
    assert captured[0]["sample_start"] == 0
    assert captured[0]["sample_stop"] == 10
    assert captured[1]["sample_start"] == 10
    assert captured[1]["sample_stop"] == 20
    assert (tmp_path / f"{orig}.h5").is_file()
    assert (tmp_path / f"{orig}_left").is_dir()
    assert (tmp_path / f"{orig}_right").is_dir()
    assert not (tmp_path / orig).exists()


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
