"""Typed recognition of calibrated drone storage at the existing affine boundary.

Recognize explicit metadata, checksum-bound sidecars or curated source identities.
Never infer calibration from a range, filename, camera model or TIFF scale alone.
This module does not calibrate raw sensor imagery or modify source pixels.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import numpy as np
from .radiometry import Radiometry

CONTRACT_VERSION = 1
SOURCE_ATTRIBUTE = "spectralbridge_source_encoding"


class DroneEncoding(str, Enum):
    RAW_MICASENSE = "raw_micasense_sensor_dn"
    METASHAPE_MICASENSE = "metashape_micasense_reflectance_uint16_v1"
    HISTORICAL_10K = "metashape_micasense_65535_to_10000_v1"
    FRACTION = "reflectance_fraction"
    REFLECTANCE_10K = "reflectance_times_10000"
    AFFINE = "explicit_calibrated_affine"


def radiometry_from_source_encoding(record):
    """Resolve a declared representation, preserving independent-accuracy limits."""
    if record.get("schema_version") != CONTRACT_VERSION:
        raise ValueError("Unsupported drone source-encoding schema_version")
    try:
        encoding = DroneEncoding(record["input_encoding"])
    except (KeyError, ValueError) as exc:
        raise ValueError(
            "Unknown drone input_encoding; supply a verified source declaration"
        ) from exc
    provenance = record.get("provenance", "")
    if not isinstance(provenance, str) or not provenance.strip():
        raise ValueError("Drone encoding requires source/calibration provenance")
    if record.get("verification_status") != "VERIFIED_ENCODING":
        raise ValueError(
            "Drone encoding needs VERIFIED_ENCODING evidence, not a numeric range"
        )
    if encoding == DroneEncoding.RAW_MICASENSE:
        return Radiometry(
            None,
            None,
            "UNSUPPORTED",
            "Raw sensor DN needs black/exposure/vignetting and irradiance/panel calibration before reflectance",
            encoding={
                "kind": "raw_dn",
                "input_encoding": encoding.value,
                "physical_calibration_status": "UNVERIFIED",
            },
        )
    if record.get("processing_state") != "calibrated_reflectance":
        raise ValueError(
            "Calibrated encoding requires processing_state=calibrated_reflectance; do not double-calibrate raw/source images"
        )
    if record.get("apply_sensor_calibration", False):
        raise ValueError(
            "Double calibration rejected: calibrated reflectance already includes sensor processing"
        )
    scales = {
        DroneEncoding.METASHAPE_MICASENSE: 1 / 32768,
        DroneEncoding.HISTORICAL_10K: 65535 / (10000 * 32768),
        DroneEncoding.FRACTION: 1.0,
        DroneEncoding.REFLECTANCE_10K: 0.0001,
    }
    scale = (
        record.get("scale") if encoding == DroneEncoding.AFFINE else scales[encoding]
    )
    offset = record.get("offset", 0.0)
    if encoding != DroneEncoding.AFFINE:
        if "scale" in record and not np.allclose(
            np.asarray(record["scale"], float), scale, rtol=1e-12, atol=0
        ):
            raise ValueError(
                "Source encoding contradicts supplied scale; possible double scaling"
            )
        if np.any(np.asarray(offset, float) != 0):
            raise ValueError(
                "Named encoding has zero offset; use explicit_calibrated_affine for documented offsets"
            )
    details = dict(
        kind="fractional_physical_reflectance"
        if encoding == DroneEncoding.FRACTION
        else "scaled_physical_reflectance",
        input_encoding=encoding.value,
        source_encoding_contract=record,
        scale_direction="multiplier",
        physical_calibration_status="VERIFIED",
        encoding_verification_status="VERIFIED_ENCODING",
        independent_physical_accuracy=record.get(
            "independent_physical_accuracy", "UNVERIFIED"
        ),
        processing_state="calibrated_reflectance",
        calibration_operations="Already performed upstream; affine decoding only",
    )
    if "nodata" in record:
        details["nodata"] = record["nodata"]
    result = Radiometry(scale, offset, "VALID", provenance, encoding=details)
    return result.require_valid()


def validate_source_wavelengths(record, wavelengths):
    declared = record.get("wavelengths_nm")
    if declared is not None:
        a, b = np.asarray(declared, float), np.asarray(wavelengths, float)
        if a.shape != b.shape or not np.allclose(a, b, atol=0.01, rtol=0):
            raise ValueError(
                "Verified source wavelengths conflict with input metadata; preserve source and repair a declared derived copy"
            )


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _json(value):
    if isinstance(value, bytes):
        value = value.decode()
    return json.loads(value) if isinstance(value, str) else dict(value)


@dataclass(frozen=True)
class DroneSourceResolution:
    radiometry: Radiometry | None
    declaration: dict | None
    recognition: str


def resolve_drone_source(path, *, metadata=None, explicit=None):
    """One recognition boundary for production TIFF/H5 staging.

    A sibling ``filename.ext.radiometry.json`` must bind the exact source SHA256.
    Registry hashes are tried only for matching byte sizes. Explicit old affine
    records remain supported, but cannot contradict a recognized representation.
    """
    path = Path(path)
    record = None
    recognition = "UNRECOGNIZED"
    metadata = metadata or {}
    raw = metadata.get(SOURCE_ATTRIBUTE)
    if raw is not None:
        record = _json(raw)
        recognition = "EMBEDDED_TYPED_ENCODING"
    sidecar = path.with_suffix(path.suffix + ".radiometry.json")
    if sidecar.exists():
        envelope = json.loads(sidecar.read_text())
        if envelope.get("source_sha256") != _sha256(path):
            raise ValueError("Drone radiometry sidecar source SHA256 mismatch")
        side = envelope["declaration"]
        if record is not None and side != record:
            raise ValueError("Embedded and sidecar encoding declarations conflict")
        record = side
        recognition = "CHECKSUM_BOUND_SIDECAR"
    if record is None:
        from importlib.resources import files

        registry = json.loads(
            files("spectralbridge")
            .joinpath("data/drone_radiometric_sources.json")
            .read_text()
        )
        candidates = [
            r for r in registry["sources"] if r["bytes"] == path.stat().st_size
        ]
        if candidates:
            digest = _sha256(path)
            for item in candidates:
                if item["sha256"] == digest:
                    record = item["declaration"]
                    recognition = "VERIFIED_SOURCE_FINGERPRINT"
                    break
    recognized = radiometry_from_source_encoding(record) if record is not None else None
    if explicit is not None:
        supplied = (
            radiometry_from_source_encoding(explicit)
            if "input_encoding" in explicit
            else Radiometry.from_record(explicit)
        )
        if supplied.status == "VALID":
            supplied.require_valid()
        if recognized is not None:
            if record is not None and explicit.get("wavelengths_nm") is not None:
                validate_source_wavelengths(record, explicit["wavelengths_nm"])
            if (
                supplied.status != recognized.status
                or supplied.scale != recognized.scale
                or supplied.offset != recognized.offset
            ):
                raise ValueError(
                    "Explicit radiometry conflicts with recognized source; possible double scaling/calibration"
                )
        else:
            recognized = supplied
            recognition = "EXPLICIT_USER_DECLARATION"
            if "input_encoding" in explicit:
                record = dict(explicit)
    return DroneSourceResolution(recognized, record, recognition)


def source_registry_identity():
    """Compact cache identity for curated source evidence, not a data-range guess."""
    from importlib.resources import files

    return hashlib.sha256(
        files("spectralbridge")
        .joinpath("data/drone_radiometric_sources.json")
        .read_bytes()
    ).hexdigest()
