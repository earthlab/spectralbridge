"""Opt-in half-flight helpers for ``split_across_track=True``.

Default full-flightline processing does not use this module. When
``split_across_track=True``, one original H5 is shared and two renamed
flight folders receive heading-aware half-route windows. Folder names are
always ``_left`` / ``_right``:

* North–south elongated footprints → line windows
  (``left`` = northern/first lines, ``right`` = southern/second lines)
* East–west elongated footprints → sample windows
  (``left`` = western/first samples, ``right`` = eastern/second samples)

This matches half of the flight *route* (not half of the sensor swath).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import h5py

from spectralbridge.io.neon import (
    _map_info_core,
    _prepare_map_info,
    peek_neon_raster_shape,
)

FootprintOrientation = Literal["north_south", "east_west"]
HalfSide = Literal["left", "right"]

HALF_SIDES: tuple[HalfSide, HalfSide] = ("left", "right")


@dataclass(frozen=True)
class HalfWindow:
    """Half-open raster window for one half-flight product."""

    side: HalfSide
    orientation: FootprintOrientation
    sample_start: int
    sample_stop: int
    line_start: int
    line_stop: int
    full_samples: int
    full_lines: int

    @property
    def sample_slice(self) -> slice | None:
        if self.sample_start == 0 and self.sample_stop == self.full_samples:
            return None
        return slice(self.sample_start, self.sample_stop)

    @property
    def line_slice(self) -> slice | None:
        if self.line_start == 0 and self.line_stop == self.full_lines:
            return None
        return slice(self.line_start, self.line_stop)


def classify_footprint_orientation(
    *,
    n_lines: int,
    n_samples: int,
    pixel_x: float = 1.0,
    pixel_y: float = 1.0,
) -> FootprintOrientation:
    """Classify corridor orientation from geographic footprint extents.

    North–south corridors are taller in northing and are halved along lines.
    East–west corridors are wider in easting and are halved along samples.
    Both modes still name products ``left`` / ``right``.
    """

    if n_lines < 1 or n_samples < 1:
        raise ValueError(f"Invalid raster shape ({n_lines}, {n_samples})")
    northing_extent = float(n_lines) * abs(float(pixel_y))
    easting_extent = float(n_samples) * abs(float(pixel_x))
    if northing_extent >= easting_extent:
        return "north_south"
    return "east_west"


def _halve_axis(n: int) -> tuple[tuple[int, int], tuple[int, int]]:
    if n < 2:
        raise ValueError(f"Need at least 2 elements to split, got {n}")
    mid = n // 2
    return (0, mid), (mid, n)


def across_track_slices(n_samples: int) -> dict[HalfSide, tuple[int, int]]:
    """Return left/right column windows (east–west half-route mode).

    The right half receives the extra column when ``n_samples`` is odd.
    """

    left, right = _halve_axis(n_samples)
    return {"left": left, "right": right}


def along_track_slices(n_lines: int) -> dict[HalfSide, tuple[int, int]]:
    """Return left/right line windows (north–south half-route mode).

    ``left`` is lines ``[0:mid]`` (north in standard NEON north-up map info).
    ``right`` is lines ``[mid:n]`` and receives the extra line when odd.
    """

    left, right = _halve_axis(n_lines)
    return {"left": left, "right": right}


def half_flight_id(original_flight_id: str, side: HalfSide) -> str:
    if side not in HALF_SIDES:
        raise ValueError(f"side must be one of {HALF_SIDES}, got {side!r}")
    return f"{original_flight_id}_{side}"


def _peek_pixel_sizes(h5_path: Path) -> tuple[float, float]:
    """Return ``(pixel_x, |pixel_y|)`` from Map_Info when present."""

    path = Path(h5_path)
    with h5py.File(path, "r") as h5_file:
        map_info_path = None

        def visit(name, obj) -> None:
            nonlocal map_info_path
            if map_info_path is None and isinstance(obj, h5py.Dataset):
                if name.lower().endswith("map_info"):
                    map_info_path = name

        h5_file.visititems(visit)
        if map_info_path is None:
            return 1.0, 1.0
        map_info_list = _prepare_map_info(h5_file[map_info_path][()])
        try:
            _ref_x, _ref_y, _e, _n, pixel_x, pixel_y = _map_info_core(map_info_list)
        except Exception:
            return 1.0, 1.0
        return float(pixel_x), abs(float(pixel_y))


def plan_half_flight(h5_path: Path | str) -> tuple[FootprintOrientation, tuple[HalfWindow, HalfWindow]]:
    """Plan heading-aware half-route windows for one NEON H5."""

    path = Path(h5_path)
    n_lines, n_samples = peek_neon_raster_shape(path)
    pixel_x, pixel_y = _peek_pixel_sizes(path)
    orientation = classify_footprint_orientation(
        n_lines=n_lines,
        n_samples=n_samples,
        pixel_x=pixel_x,
        pixel_y=pixel_y,
    )

    if orientation == "north_south":
        windows = along_track_slices(n_lines)
        ordered = (
            HalfWindow(
                side="left",
                orientation=orientation,
                sample_start=0,
                sample_stop=n_samples,
                line_start=windows["left"][0],
                line_stop=windows["left"][1],
                full_samples=n_samples,
                full_lines=n_lines,
            ),
            HalfWindow(
                side="right",
                orientation=orientation,
                sample_start=0,
                sample_stop=n_samples,
                line_start=windows["right"][0],
                line_stop=windows["right"][1],
                full_samples=n_samples,
                full_lines=n_lines,
            ),
        )
    else:
        windows = across_track_slices(n_samples)
        ordered = (
            HalfWindow(
                side="left",
                orientation=orientation,
                sample_start=windows["left"][0],
                sample_stop=windows["left"][1],
                line_start=0,
                line_stop=n_lines,
                full_samples=n_samples,
                full_lines=n_lines,
            ),
            HalfWindow(
                side="right",
                orientation=orientation,
                sample_start=windows["right"][0],
                sample_stop=windows["right"][1],
                line_start=0,
                line_stop=n_lines,
                full_samples=n_samples,
                full_lines=n_lines,
            ),
        )
    return orientation, ordered
