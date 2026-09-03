"""Shared wavelength-matched synthetic sensor-pair definitions."""

from __future__ import annotations

from typing import Mapping


MICASENSE_LANDSAT_PAIRS: Mapping[str, tuple[str, ...]] = {
    "MicaSense_to-match_TM_and_ETM+": ("Landsat_5_TM", "Landsat_7_ETM+"),
    "MicaSense_to-match_OLI_and_OLI-2": ("Landsat_8_OLI", "Landsat_9_OLI-2"),
}

SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY = (
    "Both axes are synthetic products convolved from the same corrected NEON "
    "source. Coefficients are descriptive diagnostics, not empirical sensor "
    "calibration."
)


__all__ = [
    "MICASENSE_LANDSAT_PAIRS",
    "SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY",
]
