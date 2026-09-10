"""Shared wavelength-matched synthetic sensor-pair definitions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from importlib import resources
from typing import Mapping


MICASENSE_LANDSAT_PAIRS: Mapping[str, tuple[str, ...]] = {
    "MicaSense_to-match_TM_and_ETM+": ("Landsat_5_TM", "Landsat_7_ETM+"),
    "MicaSense_to-match_OLI_and_OLI-2": ("Landsat_8_OLI", "Landsat_9_OLI-2"),
}

SPECTRAL_IDENTITY_ORDER = (
    "coastal aerosol",
    "blue",
    "green",
    "red",
    "near infrared",
    "shortwave infrared 1",
    "shortwave infrared 2",
)

_PARAMETER_KEYS: Mapping[str, str] = {
    "MicaSense": "MicaSense",
    "MicaSense_to-match_TM_and_ETM+": "MicaSense-to-match TM and ETM+",
    "MicaSense_to-match_OLI_and_OLI-2": "MicaSense-to-match OLI and OLI-2",
    "Landsat_5_TM": "Landsat 5 TM",
    "Landsat_7_ETM+": "Landsat 7 ETM+",
    "Landsat_8_OLI": "Landsat 8 OLI",
    "Landsat_9_OLI-2": "Landsat 9 OLI-2",
}

_SPECTRAL_IDENTITIES: Mapping[str, tuple[str, ...]] = {
    "MicaSense": (
        "coastal aerosol",
        "blue",
        "green 531 nm",
        "green",
        "red 650 nm",
        "red",
        "red edge 705 nm",
        "red edge 717 nm",
        "red edge 740 nm",
        "near infrared",
    ),
    "MicaSense_to-match_TM_and_ETM+": (
        "blue",
        "green",
        "red",
        "near infrared",
    ),
    "MicaSense_to-match_OLI_and_OLI-2": (
        "coastal aerosol",
        "blue",
        "green",
        "red",
        "near infrared",
    ),
    "Landsat_5_TM": (
        "blue",
        "green",
        "red",
        "near infrared",
        "shortwave infrared 1",
        "shortwave infrared 2",
    ),
    "Landsat_7_ETM+": (
        "blue",
        "green",
        "red",
        "near infrared",
        "shortwave infrared 1",
        "shortwave infrared 2",
    ),
    "Landsat_8_OLI": SPECTRAL_IDENTITY_ORDER,
    "Landsat_9_OLI-2": SPECTRAL_IDENTITY_ORDER,
}


@dataclass(frozen=True)
class SensorBandIdentity:
    """Physical identity for one one-based sensor band."""

    sensor: str
    band_index: int
    spectral_identity: str
    wavelength_nm: float
    fwhm_nm: float


@lru_cache(maxsize=1)
def _sensor_parameters() -> dict[str, dict[str, list[float]]]:
    with resources.files("spectralbridge.data").joinpath(
        "landsat_band_parameters.json"
    ).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sensor_band_identity(
    sensor: str, band_index: int
) -> SensorBandIdentity | None:
    """Return packaged physical metadata, or ``None`` for a custom sensor."""

    parameter_key = _PARAMETER_KEYS.get(sensor)
    identities = _SPECTRAL_IDENTITIES.get(sensor)
    if parameter_key is None or identities is None:
        return None
    parameters = _sensor_parameters()[parameter_key]
    wavelengths = parameters["wavelengths"]
    fwhms = parameters["fwhms"]
    if not 1 <= int(band_index) <= len(identities):
        raise ValueError(
            f"Band {band_index} is outside the packaged definition for {sensor}"
        )
    offset = int(band_index) - 1
    return SensorBandIdentity(
        sensor=sensor,
        band_index=int(band_index),
        spectral_identity=identities[offset],
        wavelength_nm=float(wavelengths[offset]),
        fwhm_nm=float(fwhms[offset]),
    )


def wavelength_matched_band_pairs(
    source_sensor: str, target_sensor: str
) -> tuple[tuple[int, int], ...]:
    """Pair shared spectral identities using packaged wavelength definitions.

    Band numbers are local to a sensor. For example, Landsat 5 TM blue band 1
    corresponds to Landsat 8 OLI blue band 2 because OLI adds coastal aerosol
    as band 1. Matches also require the packaged source and target passbands to
    overlap, protecting the named identity table from inconsistent metadata.
    """

    source_identities = _SPECTRAL_IDENTITIES.get(source_sensor)
    target_identities = _SPECTRAL_IDENTITIES.get(target_sensor)
    if source_identities is None or target_identities is None:
        raise ValueError(
            "Wavelength matching is unavailable for custom sensor pair "
            f"{source_sensor!r} -> {target_sensor!r}"
        )
    target_by_identity = {
        identity: index for index, identity in enumerate(target_identities, start=1)
    }
    pairs: list[tuple[int, int]] = []
    for source_index, identity in enumerate(source_identities, start=1):
        target_index = target_by_identity.get(identity)
        if target_index is None:
            continue
        source_band = sensor_band_identity(source_sensor, source_index)
        target_band = sensor_band_identity(target_sensor, target_index)
        assert source_band is not None and target_band is not None
        source_limits = (
            source_band.wavelength_nm - source_band.fwhm_nm / 2.0,
            source_band.wavelength_nm + source_band.fwhm_nm / 2.0,
        )
        target_limits = (
            target_band.wavelength_nm - target_band.fwhm_nm / 2.0,
            target_band.wavelength_nm + target_band.fwhm_nm / 2.0,
        )
        if max(source_limits[0], target_limits[0]) > min(
            source_limits[1], target_limits[1]
        ):
            raise ValueError(
                "Named spectral bands do not overlap: "
                f"{source_sensor} B{source_index} ({source_band.wavelength_nm:g} nm) "
                f"and {target_sensor} B{target_index} "
                f"({target_band.wavelength_nm:g} nm)"
            )
        pairs.append((source_index, target_index))
    return tuple(pairs)

SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY = (
    "Both axes are synthetic products convolved from the same corrected NEON "
    "source. Coefficients are descriptive diagnostics, not empirical sensor "
    "calibration."
)


__all__ = [
    "MICASENSE_LANDSAT_PAIRS",
    "SPECTRAL_IDENTITY_ORDER",
    "SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY",
    "SensorBandIdentity",
    "sensor_band_identity",
    "wavelength_matched_band_pairs",
]
