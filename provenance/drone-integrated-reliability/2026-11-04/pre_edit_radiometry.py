"""Authoritative affine reflectance calibration shared by both sensor paths.

Raw rasters remain in storage units. Calibration is applied once on entering a
scientific calculation and inverted once on writing a storage-scale raster.
A value distribution, an identity TIFF scale, or a filename alone is not a
calibration certificate.
"""

from dataclasses import asdict, dataclass, replace
import json
import numpy as np


@dataclass(frozen=True)
class Radiometry:
    """Explicit physical affine calibration plus optional typed storage encoding.

    The four-argument constructor retains its original meaning: an explicit
    declaration of physical calibration, never a magnitude-based inference.
    Actual source readers attach encoding/NoData/quality provenance. Scalar or
    per-band coefficients broadcast over the last axis; single-band consumers
    must provide a zero-based ``band_index`` for nonuniform calibrations.
    """

    scale: float | tuple[float, ...] | None
    offset: float | tuple[float, ...] | None
    status: str
    provenance: str
    convention: str = "physical = scale * stored + offset"
    encoding: dict | None = None

    def __post_init__(self):
        for name in ("scale", "offset"):
            value = getattr(self, name)
            if value is None:
                continue
            a = np.asarray(value, dtype=np.float64)
            if a.ndim > 1 or a.size == 0:
                raise ValueError(
                    "Radiometry coefficients must be scalar or per-band vectors"
                )
            value = (
                float(a.reshape(-1)[0])
                if a.size == 1 or np.all(a == a.flat[0])
                else tuple(a.tolist())
            )
            object.__setattr__(self, name, value)
        if self.encoding is not None:
            kinds = {
                "raw_dn",
                "range_normalized_dn",
                "scaled_physical_reflectance",
                "fractional_physical_reflectance",
                "unknown",
            }
            if self.encoding.get("kind") not in kinds:
                raise ValueError(
                    "Radiometry encoding requires an explicit supported kind"
                )

    def require_valid(self):
        details = self.encoding or {}
        physical_status = details.get(
            "physical_calibration_status", "DECLARED_BY_AFFINE_RECORD"
        )
        coefficients_valid = self.scale is not None and self.offset is not None
        if coefficients_valid:
            coefficients_valid = (
                np.isfinite(self.scale).all()
                and np.isfinite(self.offset).all()
                and np.all(np.asarray(self.scale) > 0)
            )
        if (
            self.convention != "physical = scale * stored + offset"
            or self.status != "VALID"
            or not self.provenance.strip()
            or not coefficients_valid
            or details.get("kind") == "unknown"
            or details.get("scale_direction", "multiplier") != "multiplier"
            or physical_status in {"UNVERIFIED", "UNKNOWN", "DIAGNOSTIC_ONLY"}
            or (
                details.get("kind") in {"raw_dn", "range_normalized_dn"}
                and physical_status != "VERIFIED"
            )
        ):
            raise ValueError(
                f"Radiometry {self.status}: authoritative physical scale, offset, units and provenance required ({self.provenance})."
            )
        return self

    @staticmethod
    def _parameter(value, values, band_index=None):
        a = np.asarray(value, dtype=np.float32)
        if a.ndim == 0 or a.size == 1:
            return a.reshape(())
        if band_index is not None:
            if not 0 <= band_index < a.size:
                raise ValueError("Radiometry band index outside coefficient vector")
            return a[band_index]
        if values.ndim == 0 or values.shape[-1] != a.size:
            raise ValueError(
                "Radiometry per-band coefficient count differs from last data axis; provide band_index for a single band"
            )
        return a

    def _mask_parameters(self, values, band_index=None, nodata=None):
        details = self.encoding or {}
        ignore = details.get("nodata") if nodata is None else nodata
        ignore = (
            np.nan
            if ignore is None or (isinstance(ignore, str) and ignore.lower() == "nan")
            else ignore
        )
        saturation = details.get("saturation", {})
        saturated = (
            saturation.get("value", np.nan)
            if saturation.get("status") == "DOCUMENTED" and saturation.get("provenance")
            else np.nan
        )
        return (
            self._parameter(ignore, values, band_index),
            self._parameter(saturated, values, band_index),
        )

    def valid_stored(self, values, *, band_index=None, nodata=None):
        """Finite stored measurements excluding declared NoData/saturation only.

        Recommended source ranges do not clip measurements. Physical fitting
        eligibility is tested separately after verified conversion. Zeros and
        negative finite measurements survive unless explicitly marked missing.
        """
        a = np.asarray(values)
        ignore, saturated = self._mask_parameters(a, band_index, nodata)
        return np.isfinite(a) & (a != ignore) & (a != saturated)

    def _affine(self, values, scale, offset, *, inverse=False, band_index=None):
        a = np.asarray(values, dtype=np.float32)
        multiplier = self._parameter(scale, a, band_index)
        intercept = self._parameter(offset, a, band_index)
        ignore, saturated = self._mask_parameters(a, band_index)
        out = np.empty_like(a)
        # Bounded temporary masks: no additional full-cube boolean allocation.
        operands = [a, multiplier, intercept, ignore, saturated, out]
        iterator = np.nditer(
            operands,
            flags=["external_loop", "buffered", "zerosize_ok"],
            op_flags=[["readonly"]] * 5 + [["writeonly"]],
            buffersize=262144,
        )
        for stored, mul, off, no_data, sat, result in iterator:
            if inverse:
                np.subtract(stored, off, out=result)
                np.divide(result, mul, out=result)
                valid = np.isfinite(stored)
            else:
                np.multiply(stored, mul, out=result)
                np.add(result, off, out=result)
                valid = np.isfinite(stored) & (stored != no_data) & (stored != sat)
            result[~valid] = np.nan
        return out

    def to_physical(self, values, *, band_index=None):
        self.require_valid()
        return self._affine(values, self.scale, self.offset, band_index=band_index)

    def to_stored(self, values, *, band_index=None):
        self.require_valid()
        return self._affine(
            values, self.scale, self.offset, inverse=True, band_index=band_index
        )

    def to_normalized_fraction(self, values, *, band_index=None):
        """Decode a declared numerical normalization for diagnostics, never calibration."""
        details = self.encoding or {}
        if details.get("kind") != "range_normalized_dn":
            raise ValueError(
                "Diagnostic fraction requires a documented range-normalized DN encoding"
            )
        normalization = details.get("normalization", {})
        lower = np.asarray(normalization.get("stored_min"), dtype=float)
        upper = np.asarray(normalization.get("stored_max"), dtype=float)
        if (
            not np.isfinite(lower).all()
            or not np.isfinite(upper).all()
            or not np.all(upper > lower)
        ):
            raise ValueError(
                "Diagnostic fraction requires documented finite normalization bounds"
            )
        return self._affine(
            values, 1 / (upper - lower), -lower / (upper - lower), band_index=band_index
        )

    def header(self):
        fields = {
            "radiometry status": self.status,
            "radiometry provenance": self.provenance.replace("\n", " "),
        }
        if self.scale is not None:
            fields["physical reflectance multiplier"] = self.scale
            fields["physical reflectance offset"] = self.offset
        # Always replace inherited contracts when a producer changes output units.
        fields["radiometry contract"] = "json:" + json.dumps(
            self.record(), separators=(",", ":"), allow_nan=False
        )
        fields["radiometry encoding"] = (self.encoding or {}).get(
            "kind",
            (
                "fractional_physical_reflectance"
                if self.scale == 1 and self.offset == 0
                else "scaled_physical_reflectance"
            )
            if self.status == "VALID"
            else "unknown",
        )
        return fields

    def record(self):
        record = asdict(self)
        if self.encoding is None:
            record.pop("encoding")  # Preserve legacy explicit affine declarations.
        for name in ("scale", "offset"):
            if isinstance(record[name], tuple):
                record[name] = list(record[name])
        return record

    def matches_declaration(self, expected):
        """Compare supplied calibration fields, allowing source-derived metadata additions."""
        actual, declared = self.record(), expected.record()
        encoding = declared.pop("encoding", None)
        actual_encoding = actual.pop("encoding", {})
        return actual == declared and (
            encoding is None
            or all(actual_encoding.get(k) == v for k, v in encoding.items())
        )

    @classmethod
    def from_record(cls, record):
        return cls(**record)

    @classmethod
    def from_header(cls, header):
        contract = header.get("radiometry contract")
        if contract is not None:
            if not isinstance(contract, str) or not contract.startswith("json:"):
                raise ValueError(
                    "Radiometry INVALID: malformed serialized header contract"
                )
            result = cls.from_record(json.loads(contract[5:]))
            for key, value in [
                ("physical reflectance multiplier", result.scale),
                ("physical reflectance offset", result.offset),
            ]:
                if key in header and (
                    value is None
                    or not np.array_equal(
                        np.atleast_1d(header[key]).astype(float), np.atleast_1d(value)
                    )
                ):
                    raise ValueError(
                        "Radiometry INVALID: header affine fields disagree with serialized contract"
                    )
            if str(header.get("radiometry status", result.status)) != result.status:
                raise ValueError(
                    "Radiometry INVALID: header calibration statuses disagree"
                )
        else:
            result = cls(
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
        if (
            "data ignore value" in header
            and (result.encoding or {}).get("nodata") is None
        ):
            ignore = float(header["data ignore value"])
            details = dict(
                result.encoding
                or {
                    "kind": "fractional_physical_reflectance"
                    if result.scale == 1 and result.offset == 0
                    else "scaled_physical_reflectance"
                    if result.status == "VALID"
                    else "unknown"
                }
            )
            details["nodata"] = ignore if np.isfinite(ignore) else "NaN"
            result = replace(result, encoding=details)
        return result


def _encoding_metadata(dataset, *, kind, verified):
    attrs = dataset.attrs
    ignore = next(
        (
            attrs[k]
            for k in ("Data_Ignore_Value", "_FillValue", "NoData", "no_data")
            if k in attrs
        ),
        None,
    )
    if ignore is not None:
        ignore = float(np.asarray(ignore).reshape(-1)[0])
        if not np.isfinite(ignore):
            ignore = "NaN"
    valid_range = attrs.get("Units_Valid_range")
    details = dict(
        kind=kind,
        source_units="fractional physical reflectance"
        if verified
        else "unverified source units",
        stored_units=(
            "fractional physical reflectance"
            if kind == "fractional_physical_reflectance"
            else "scaled physical reflectance"
        )
        if verified
        else "unknown numerical encoding",
        scale_direction="multiplier",
        physical_calibration_status="VERIFIED" if verified else "UNVERIFIED",
        valid_numerical_range=np.asarray(valid_range).tolist()
        if valid_range is not None
        else None,
        source_units_attribute=str(attrs.get("Units", "not supplied")),
        source_dtype=str(dataset.dtype),
        nodata=ignore,
        saturation={"status": "NOT_PROVIDED"},
        quality_mask={"status": "NOT_PROVIDED; NoData only"},
    )
    if "spectralbridge_valid_mask_path" in attrs:
        details["source_valid_mask_path"] = str(attrs["spectralbridge_valid_mask_path"])
        details["quality_mask"] = dict(
            status="DOCUMENTED",
            convention="true means valid",
            provenance="Explicit source footprint/quality mask in H5",
        )
    if "Saturation_Value" in attrs:
        details["saturation"] = dict(
            status="DOCUMENTED",
            value=np.asarray(attrs["Saturation_Value"]).tolist(),
            provenance="Source dataset Saturation_Value attribute",
        )
    return details


def dataset_radiometry(dataset, *, neon=False):
    """Read explicit calibration or documented NEON divisors, never infer by range."""
    record = dataset.attrs.get("spectralbridge_radiometry")
    if record is not None:
        if isinstance(record, bytes):
            record = record.decode()
        result = Radiometry.from_record(json.loads(str(record)))
        details = _encoding_metadata(
            dataset,
            kind=(
                "fractional_physical_reflectance"
                if result.scale == 1.0 and result.offset == 0.0
                else "scaled_physical_reflectance"
            )
            if result.status == "VALID"
            else "unknown",
            verified=result.status == "VALID",
        )
        incoming = dict(result.encoding or {})
        if (
            incoming.get("source_valid_mask_path")
            and details.get("source_valid_mask_path")
            and incoming["source_valid_mask_path"] != details["source_valid_mask_path"]
        ):
            raise ValueError(
                "Radiometry INVALID: source-validity mask declarations disagree"
            )
        if incoming.get("nodata") is not None and details.get("nodata") is not None:
            first, second = incoming["nodata"], details["nodata"]
            same = (str(first).lower() == str(second).lower()) or (
                np.asarray(first, dtype=float) == np.asarray(second, dtype=float)
            ).all()
            if not same:
                raise ValueError(
                    "Radiometry INVALID: source NoData declarations disagree"
                )
        if incoming.get("nodata") is None:
            incoming.pop("nodata", None)
        details.update(incoming)
        return replace(result, encoding=details)
    if neon and "Scale_Factor" in dataset.attrs:
        divisor = np.asarray(dataset.attrs["Scale_Factor"], dtype=float)
        if (
            divisor.ndim <= 1
            and divisor.size
            and np.isfinite(divisor).all()
            and np.all(divisor > 0)
        ):
            offsets = [
                np.asarray(dataset.attrs[k], dtype=float)
                for k in ("Add_Offset", "add_offset", "Offset", "offset")
                if k in dataset.attrs
            ]
            if any(
                not np.isfinite(value).all() or np.any(value != 0) for value in offsets
            ):
                return Radiometry(
                    None,
                    None,
                    "UNSUPPORTED",
                    "Nonzero source offset has no established convention; supply an authoritative affine record",
                    encoding=_encoding_metadata(
                        dataset, kind="unknown", verified=False
                    ),
                )
            details = _encoding_metadata(
                dataset,
                kind="fractional_physical_reflectance"
                if np.all(divisor == 1)
                else "scaled_physical_reflectance",
                verified=True,
            )
            details.update(
                source_scale_direction="divisor", source_scale_factor=divisor.tolist()
            )
            return Radiometry(
                1 / divisor,
                0.0,
                "VALID",
                "NEON DP1.30006: stored / Scale_Factor; physical offset zero",
                encoding=details,
            )
    return Radiometry(
        None,
        None,
        "UNSUPPORTED",
        "Source has no authoritative physical-reflectance calibration",
        encoding=_encoding_metadata(dataset, kind="unknown", verified=False),
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
    if status == "VALID":
        from .corrections import BRDF_KERNEL_MATH_VERSION, BRDF_VALIDATION_POLICY
        if header.get("brdf kernel math version") != BRDF_KERNEL_MATH_VERSION:
            raise ValueError("BRDF UNSUPPORTED: incompatible kernel mathematics; preserve historical products and use a fresh output directory")
        if header.get("brdf validation policy") != BRDF_VALIDATION_POLICY:
            raise ValueError("BRDF UNSUPPORTED: incompatible validation policy; preserve historical products and use a fresh output directory")
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
