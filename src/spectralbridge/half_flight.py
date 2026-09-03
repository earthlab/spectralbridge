"""Opt-in across-track half-flight helpers.

Default full-flightline processing does not use this module. When
``split_across_track=True``, one original H5 is shared and two renamed
flight folders receive left/right column windows.
"""

from __future__ import annotations

from typing import Literal

HalfSide = Literal["left", "right"]

HALF_SIDES: tuple[HalfSide, HalfSide] = ("left", "right")


def across_track_slices(n_samples: int) -> dict[HalfSide, tuple[int, int]]:
    """Return half-open column windows ``(start, stop)`` for left/right halves.

    The right half receives the extra column when ``n_samples`` is odd.
    """

    if n_samples < 2:
        raise ValueError(
            f"Need at least 2 samples to split across-track, got {n_samples}"
        )
    mid = n_samples // 2
    return {"left": (0, mid), "right": (mid, n_samples)}


def half_flight_id(original_flight_id: str, side: HalfSide) -> str:
    if side not in HALF_SIDES:
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    return f"{original_flight_id}_{side}"
