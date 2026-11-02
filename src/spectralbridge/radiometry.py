"""Authoritative affine reflectance calibration shared by both sensor paths.

Raw rasters remain in storage units. Calibration is applied once on entering a
scientific calculation and inverted once on writing a storage-scale raster.
A value distribution, an identity TIFF scale, or a filename alone is not a
calibration certificate.
"""

from dataclasses import asdict, dataclass
import json
import numpy as np


@dataclass(frozen=True)
class Radiometry:
    scale: float | None
    offset: float | None
    status: str
    provenance: str
    convention: str = "physical = scale * stored + offset"

    def require_valid(self):
        if (
            self.convention != "physical = scale * stored + offset"
            or self.status != "VALID"
            or not self.provenance.strip()
            or self.scale is None
            or self.offset is None
            or not np.isfinite([self.scale, self.offset]).all()
            or self.scale <= 0
        ):
            raise ValueError(
                f"Radiometry {self.status}: authoritative positive scale, offset and provenance required ({self.provenance})."
            )
        return self

    def to_physical(self, values):
        self.require_valid()
        return np.asarray(values, dtype=np.float32) * np.float32(
            self.scale
        ) + np.float32(self.offset)

    def to_stored(self, values):
        self.require_valid()
        return (
            np.asarray(values, dtype=np.float32) - np.float32(self.offset)
        ) / np.float32(self.scale)

    def header(self):
        fields = {
            "radiometry status": self.status,
            "radiometry provenance": self.provenance.replace("\n", " "),
        }
        if self.scale is not None:
            fields["physical reflectance multiplier"] = self.scale
            fields["physical reflectance offset"] = self.offset
        return fields

    def record(self):
        return asdict(self)

    @classmethod
    def from_record(cls, record):
        return cls(**record)

    @classmethod
    def from_header(cls, header):
        return cls(
            float(header["physical reflectance multiplier"])
            if "physical reflectance multiplier" in header
            else None,
            float(header.get("physical reflectance offset", 0)),
            str(header.get("radiometry status", "UNSUPPORTED")),
            str(
                header.get(
                    "radiometry provenance",
                    "Historical header lacks explicit calibration",
                )
            ),
        )


def dataset_radiometry(dataset, *, neon=False):
    """Read a declared affine record or documented NEON divisor, never infer units."""
    record = dataset.attrs.get("spectralbridge_radiometry")
    if record is not None:
        if isinstance(record, bytes):
            record = record.decode()
        return Radiometry.from_record(json.loads(str(record)))
    # This is an explicit NEON-schema interpretation, not a magnitude heuristic.
    if neon and "Scale_Factor" in dataset.attrs:
        divisor = float(np.asarray(dataset.attrs["Scale_Factor"]).reshape(-1)[0])
        if np.isfinite(divisor) and divisor > 0:
            offsets = [
                float(dataset.attrs[k])
                for k in ("Add_Offset", "add_offset", "Offset", "offset")
                if k in dataset.attrs
            ]
            if any(not np.isfinite(value) or value != 0.0 for value in offsets):
                return Radiometry(
                    None,
                    None,
                    "UNSUPPORTED",
                    "Nonzero source offset has no established convention; supply an authoritative affine record",
                )
            return Radiometry(
                1.0 / divisor,
                0.0,
                "VALID",
                "NEON DP1.30006: stored / Scale_Factor; physical offset zero",
            )
    return Radiometry(
        None,
        None,
        "UNSUPPORTED",
        "Source has no authoritative physical-reflectance calibration",
    )


def require_radiometry(cube):
    r = getattr(
        cube,
        "radiometry",
        Radiometry(None, None, "UNSUPPORTED", "Cube has no explicit radiometry record"),
    )
    return r.require_valid()


def require_library_header(header):
    """Fail closed before a historical/unsupported correction enters a library.

    Explicit raw/topographic-only data with verified calibration are allowed;
    BRDF requested but unsupported/invalid is not an approved alternative.
    """
    r = Radiometry.from_header(header).require_valid()
    status = str(header.get("brdf status", "UNSUPPORTED"))
    if status not in {"VALID", "NOT_REQUESTED"}:
        raise ValueError(
            f"BRDF {status}: product is not eligible for approved spectral-library processing"
        )
    if status == "VALID" and int(header.get("brdf model schema", 0)) != 2:
        raise ValueError(
            "BRDF UNSUPPORTED: historical model requires scientific review"
        )
    return r


def library_radiometry(image):
    from pathlib import Path
    from .envi import hdr_to_dict

    return require_library_header(hdr_to_dict(Path(image).with_suffix(".hdr")))


def require_physical_table(path):
    import pyarrow.parquet as pq

    metadata = pq.read_schema(path).metadata or {}
    if metadata.get(b"spectralbridge.reflectance_units") != b"physical_reflectance_v1":
        raise ValueError(
            "Historical table has unverified units; use a fresh output directory for physical-reflectance extraction"
        )


def physical_copy_metadata(paths):
    """Preserve verified units through DuckDB COPY without reading pixel rows."""
    paths = list(paths)
    if not paths:
        return ""
    try:
        for path in paths:
            require_physical_table(path)
    except ValueError:
        return ""
    return (
        ", KV_METADATA {'spectralbridge.reflectance_units': 'physical_reflectance_v1'}"
    )
