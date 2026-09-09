"""Wavelength-aware application of reviewed bulk translation coefficients.

This module is deliberately downstream of drone correction and downstream of
bulk coefficient estimation.  It never fits coefficients and never performs
spectral convolution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import duckdb

from spectralbridge import __version__
from spectralbridge.bulk.registry import DEFAULT_PRODUCT_REGISTRY, TranslationPair
from spectralbridge.envi import hdr_to_dict, memmap_bsq
from spectralbridge.envi_writer import EnviWriter
from spectralbridge.utils.paths import get_package_data_path
from spectralbridge.utils_checks import is_valid_envi_pair


TRANSLATION_EQUATION = "target = slope * source + intercept"
SUPPORTED_WEIGHTINGS = (
    "pixel_pooled",
    "flightline_balanced",
    "site_balanced",
)

_PARAMETER_SENSOR_NAMES = {
    "MicaSense_to-match_TM_and_ETM+": "MicaSense-to-match TM and ETM+",
    "MicaSense_to-match_OLI_and_OLI-2": "MicaSense-to-match OLI and OLI-2",
    "Landsat_5_TM": "Landsat 5 TM",
    "Landsat_7_ETM+": "Landsat 7 ETM+",
    "Landsat_8_OLI": "Landsat 8 OLI",
    "Landsat_9_OLI-2": "Landsat 9 OLI-2",
}

_TARGET_SLUGS = {
    "Landsat_5_TM": "landsat_tm",
    "Landsat_7_ETM+": "landsat_etm+",
    "Landsat_8_OLI": "landsat_oli",
    "Landsat_9_OLI-2": "landsat_oli2",
}


@dataclass(frozen=True)
class DroneTranslationBand:
    """One validated source-band to target-band affine relationship."""

    translation_pair: str
    source_sensor: str
    target_sensor: str
    coefficient_band_index: int
    coefficient_source_band_index: int
    native_source_band_index: int
    target_band_index: int
    source_wavelength_nm: float
    native_source_wavelength_nm: float
    target_wavelength_nm: float
    target_fwhm_nm: float
    slope: float
    intercept: float
    x_min: float | None
    x_max: float | None
    x_mean: float | None
    r2: float | None


@dataclass(frozen=True)
class DroneTranslationPlan:
    """Validated coefficients and band mapping for one Landsat target sensor."""

    analysis_run_id: str
    analysis_level: str
    weighting_description: str
    source_sensor: str
    target_sensor: str
    translation_pair: str
    coefficient_path: str
    coefficient_sha256: str
    evidence_boundary: str | None
    candidate_status: str | None
    bands: tuple[DroneTranslationBand, ...]

    @property
    def output_slug(self) -> str:
        return _TARGET_SLUGS[self.target_sensor]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _optional_number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _load_parameter_definitions() -> dict[str, dict[str, list[float]]]:
    path = get_package_data_path("landsat_band_parameters.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_coefficient_rows(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Translation coefficient artifact not found: {path}")
    suffix = path.suffix.lower()
    metadata: dict[str, Any] = {}
    if suffix == ".parquet":
        frame = pd.read_parquet(path)
        metadata_path = path.with_suffix(".json")
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"Adjacent coefficient provenance JSON is unreadable: {metadata_path}"
                ) from exc
    elif suffix == ".json":
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Translation coefficient JSON is invalid: {path}") from exc
        rows = metadata.get("candidate_coefficients")
        if not isinstance(rows, list):
            raise ValueError(
                "Translation coefficient JSON must contain a candidate_coefficients list"
            )
        frame = pd.DataFrame(rows)
    else:
        raise ValueError("Translation coefficients must be a .parquet or .json artifact")
    return frame, metadata


def _registry_pairs() -> dict[str, TranslationPair]:
    return {pair.key: pair for pair in DEFAULT_PRODUCT_REGISTRY.translation_pairs}


def _nearest_native_band(
    source_wavelengths: np.ndarray,
    expected_wavelength: float,
    expected_fwhm: float,
) -> tuple[int, float]:
    distances = np.abs(source_wavelengths - expected_wavelength)
    if not np.isfinite(distances).all():
        raise ValueError("Drone source wavelengths must all be finite")
    index = int(np.argmin(distances))
    nearest = float(source_wavelengths[index])
    tolerance = max(5.0, float(expected_fwhm) / 2.0)
    if float(distances[index]) > tolerance:
        raise ValueError(
            "No drone band matches the coefficient source wavelength "
            f"{expected_wavelength:g} nm within {tolerance:g} nm; nearest is "
            f"band {index + 1} at {nearest:g} nm"
        )
    tied = np.flatnonzero(np.isclose(distances, distances[index], atol=1e-6))
    if tied.size != 1:
        raise ValueError(
            f"Drone band identity is ambiguous around {expected_wavelength:g} nm"
        )
    return index + 1, nearest


def _validate_required_columns(frame: pd.DataFrame) -> None:
    required = {
        "analysis_run_id",
        "analysis_level",
        "weighting",
        "translation_pair",
        "source_sensor",
        "target_sensor",
        "source_band_index",
        "target_band_index",
        "band_index",
        "equation",
        "status",
        "slope",
        "intercept",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "Translation coefficient artifact is missing required column(s): "
            + ", ".join(missing)
        )


def load_drone_translation_plans(
    coefficient_path: str | Path,
    *,
    weighting: str,
    source_wavelengths_nm: Sequence[float] | np.ndarray,
    target_sensors: Iterable[str] | None = None,
) -> tuple[DroneTranslationPlan, ...]:
    """Load and scientifically validate bulk coefficients for drone application.

    ``weighting`` selects the bulk ``analysis_level`` and is always explicit.
    When ``target_sensors`` is omitted, every complete built-in target present
    in the artifact is returned; the function never silently chooses one.
    """

    path = Path(coefficient_path).expanduser().resolve()
    requested_weighting = str(weighting).strip().lower().replace("-", "_")
    if requested_weighting not in SUPPORTED_WEIGHTINGS:
        raise ValueError(
            "translation_weighting must be one of " + ", ".join(SUPPORTED_WEIGHTINGS)
        )
    source_wavelengths = np.asarray(source_wavelengths_nm, dtype=np.float64).reshape(-1)
    if source_wavelengths.size == 0:
        raise ValueError("Corrected drone product has no source wavelengths")

    frame, metadata = _load_coefficient_rows(path)
    _validate_required_columns(frame)
    selected = frame.loc[frame["analysis_level"].astype(str) == requested_weighting].copy()
    if selected.empty:
        raise ValueError(
            f"Coefficient artifact has no rows for weighting {requested_weighting!r}"
        )
    selected = selected.loc[selected["status"].astype(str) == "ok"].copy()
    if selected.empty:
        raise ValueError(
            f"Coefficient artifact has no usable status='ok' rows for {requested_weighting!r}"
        )

    requested_targets = set(target_sensors or ())
    if requested_targets:
        selected = selected.loc[selected["target_sensor"].isin(requested_targets)].copy()
        missing_targets = requested_targets - set(selected["target_sensor"].astype(str))
        if missing_targets:
            raise ValueError(
                "Coefficient artifact lacks requested target sensor(s): "
                + ", ".join(sorted(missing_targets))
            )

    definitions = _load_parameter_definitions()
    registry_pairs = _registry_pairs()
    coefficient_sha256 = _sha256(path)
    evidence_by_pair = {
        str(item.get("key")): item.get("evidence_boundary")
        for item in metadata.get("translation_pairs", [])
        if isinstance(item, dict)
    }
    for row in selected.itertuples(index=False):
        pair = registry_pairs.get(str(row.translation_pair))
        if pair is None:
            raise ValueError(
                "Unsupported translation_pair in coefficient artifact: "
                f"{row.translation_pair}"
            )
        if (
            pair.source_sensor != str(row.source_sensor)
            or pair.target_sensor != str(row.target_sensor)
        ):
            raise ValueError(
                "Coefficient pair orientation does not match registry definition "
                f"for {row.translation_pair}"
            )
    plans: list[DroneTranslationPlan] = []
    group_columns = ["translation_pair", "source_sensor", "target_sensor"]
    for (pair_key, source_sensor, target_sensor), group in selected.groupby(
        group_columns, sort=True, dropna=False
    ):
        pair_key = str(pair_key)
        source_sensor = str(source_sensor)
        target_sensor = str(target_sensor)
        pair = registry_pairs.get(pair_key)
        if pair is None:
            raise ValueError(f"Unsupported translation_pair in coefficient artifact: {pair_key}")
        if pair.source_sensor != source_sensor or pair.target_sensor != target_sensor:
            raise ValueError(
                f"Coefficient pair orientation does not match registry definition for {pair_key}"
            )
        equations = set(group["equation"].astype(str))
        if equations != {TRANSLATION_EQUATION}:
            raise ValueError(
                f"Coefficient equation/orientation is unsupported for {pair_key}: {sorted(equations)}"
            )
        run_ids = set(group["analysis_run_id"].astype(str))
        if len(run_ids) != 1:
            raise ValueError(f"Coefficient rows mix analysis_run_id values for {pair_key}")
        weighting_descriptions = set(group["weighting"].astype(str))
        if len(weighting_descriptions) != 1:
            raise ValueError(f"Coefficient rows mix weighting descriptions for {pair_key}")

        expected_pairs = tuple(pair.band_pairs)
        found_pairs = [
            (int(row.source_band_index), int(row.target_band_index))
            for row in group.itertuples(index=False)
        ]
        if len(found_pairs) != len(set(found_pairs)):
            raise ValueError(f"Duplicate source/target band coefficient for {pair_key}")
        if set(found_pairs) != set(expected_pairs):
            raise ValueError(
                f"Coefficient bands for {pair_key} are incomplete or unexpected; "
                f"expected {expected_pairs}, found {tuple(sorted(found_pairs))}"
            )

        source_definition = definitions[_PARAMETER_SENSOR_NAMES[source_sensor]]
        target_definition = definitions[_PARAMETER_SENSOR_NAMES[target_sensor]]
        source_centers = source_definition["wavelengths"]
        source_fwhms = source_definition["fwhms"]
        target_centers = target_definition["wavelengths"]
        target_fwhms = target_definition["fwhms"]
        bands: list[DroneTranslationBand] = []
        for row in group.sort_values("target_band_index").itertuples(index=False):
            source_band_index = int(row.source_band_index)
            target_band_index = int(row.target_band_index)
            slope = float(row.slope)
            intercept = float(row.intercept)
            if not math.isfinite(slope) or not math.isfinite(intercept):
                raise ValueError(
                    f"Non-finite slope/intercept for {pair_key} band {row.band_index}"
                )
            expected_source_wavelength = float(source_centers[source_band_index - 1])
            native_band_index, native_wavelength = _nearest_native_band(
                source_wavelengths,
                expected_source_wavelength,
                float(source_fwhms[source_band_index - 1]),
            )
            bands.append(
                DroneTranslationBand(
                    translation_pair=pair_key,
                    source_sensor=source_sensor,
                    target_sensor=target_sensor,
                    coefficient_band_index=int(row.band_index),
                    coefficient_source_band_index=source_band_index,
                    native_source_band_index=native_band_index,
                    target_band_index=target_band_index,
                    source_wavelength_nm=expected_source_wavelength,
                    native_source_wavelength_nm=native_wavelength,
                    target_wavelength_nm=float(target_centers[target_band_index - 1]),
                    target_fwhm_nm=float(target_fwhms[target_band_index - 1]),
                    slope=slope,
                    intercept=intercept,
                    x_min=_optional_number(getattr(row, "x_min", None)),
                    x_max=_optional_number(getattr(row, "x_max", None)),
                    x_mean=_optional_number(getattr(row, "x_mean", None)),
                    r2=_optional_number(getattr(row, "r2", None)),
                )
            )
        native_indices = [band.native_source_band_index for band in bands]
        if len(native_indices) != len(set(native_indices)):
            raise ValueError(
                f"Multiple coefficient bands map to the same native drone band for {pair_key}"
            )
        plans.append(
            DroneTranslationPlan(
                analysis_run_id=next(iter(run_ids)),
                analysis_level=requested_weighting,
                weighting_description=next(iter(weighting_descriptions)),
                source_sensor=source_sensor,
                target_sensor=target_sensor,
                translation_pair=pair_key,
                coefficient_path=str(path),
                coefficient_sha256=coefficient_sha256,
                evidence_boundary=evidence_by_pair.get(pair_key) or pair.evidence_boundary,
                candidate_status=metadata.get("candidate_status"),
                bands=tuple(bands),
            )
        )
    if not plans:
        raise ValueError("No complete supported translation pairs were selected")
    return tuple(plans)


def translated_output_stem(
    flight_dir: str | Path,
    flight_stem: str,
    target_sensor: str,
) -> Path:
    """Return a precise, sensor-specific Landsat-like translated ENVI stem."""

    try:
        slug = _TARGET_SLUGS[target_sensor]
    except KeyError as exc:
        raise ValueError(f"Unsupported translated target sensor: {target_sensor}") from exc
    return Path(flight_dir) / f"{flight_stem}__landsat_like_{slug}_translated_envi"


def _source_fingerprint(img_path: Path, hdr_path: Path) -> dict[str, Any]:
    return {
        "image": str(img_path.resolve()),
        "image_size": img_path.stat().st_size,
        "image_mtime_ns": img_path.stat().st_mtime_ns,
        "header": str(hdr_path.resolve()),
        "header_sha256": _sha256(hdr_path),
    }


def _translation_signature(
    plan: DroneTranslationPlan,
    source_img: Path,
    source_hdr: Path,
) -> str:
    payload = {
        "schema_version": 1,
        "equation": TRANSLATION_EQUATION,
        "plan": asdict(plan),
        "source": _source_fingerprint(source_img, source_hdr),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _range_compatibility(
    source: np.ndarray,
    band: DroneTranslationBand,
    valid: np.ndarray,
) -> dict[str, Any]:
    values = source[valid]
    if values.size == 0:
        return {"status": "no_valid_source_values"}
    observed_min = float(np.min(values))
    observed_max = float(np.max(values))
    result: dict[str, Any] = {
        "observed_min": observed_min,
        "observed_max": observed_max,
        "training_min": band.x_min,
        "training_max": band.x_max,
        "status": "not_evaluated",
    }
    if band.x_min is None or band.x_max is None:
        return result
    overlap = max(observed_min, band.x_min) <= min(observed_max, band.x_max)
    result["status"] = "overlap" if overlap else "no_overlap"
    if not overlap:
        raise ValueError(
            "Corrected drone values do not overlap the coefficient training range "
            f"for {band.translation_pair} target band {band.target_band_index}: "
            f"observed [{observed_min:g}, {observed_max:g}], training "
            f"[{band.x_min:g}, {band.x_max:g}]. Check reflectance units/scale."
        )
    return result


def apply_drone_translation(
    corrected_img: str | Path,
    corrected_hdr: str | Path,
    *,
    output_stem: str | Path,
    plan: DroneTranslationPlan,
    overwrite: bool = False,
    chunk_lines: int = 256,
) -> dict[str, Any]:
    """Apply one validated affine plan to a corrected native MicaSense ENVI."""

    corrected_img = Path(corrected_img)
    corrected_hdr = Path(corrected_hdr)
    output_stem = Path(output_stem)
    output_img = output_stem.with_suffix(".img")
    output_hdr = output_stem.with_suffix(".hdr")
    provenance_path = output_stem.with_name(output_stem.name + "__translation.json")
    signature = _translation_signature(plan, corrected_img, corrected_hdr)
    if not overwrite and is_valid_envi_pair(output_img, output_hdr) and provenance_path.is_file():
        try:
            previous = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
        if previous.get("translation_signature_sha256") == signature:
            return {
                **previous,
                "status": "reused",
                "output_img": str(output_img),
                "output_hdr": str(output_hdr),
                "provenance_json": str(provenance_path),
            }

    header = hdr_to_dict(corrected_hdr)
    wavelengths = np.asarray(header.get("wavelength"), dtype=np.float64).reshape(-1)
    if wavelengths.size != int(header["bands"]):
        raise ValueError("Corrected drone ENVI wavelength count does not match band count")
    source = memmap_bsq(corrected_img, header)
    nodata_raw = header.get("data ignore value", -9999.0)
    if isinstance(nodata_raw, list):
        nodata_raw = nodata_raw[0]
    nodata = float(nodata_raw)
    output_header = dict(header)
    output_header.update(
        {
            "bands": len(plan.bands),
            "wavelength": [band.target_wavelength_nm for band in plan.bands],
            "fwhm": [band.target_fwhm_nm for band in plan.bands],
            "description": (
                "Landsat-like translated reflectance derived from corrected native "
                f"MicaSense using {plan.analysis_level} bulk coefficients; not an "
                "actual Landsat observation"
            ),
        }
    )
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    writer = EnviWriter(output_stem, output_header)
    range_bounds: dict[str, list[float]] = {}
    value_summaries: list[dict[str, Any]] = []
    lines = int(header["lines"])
    samples = int(header["samples"])
    try:
        for row_start in range(0, lines, max(1, int(chunk_lines))):
            row_stop = min(lines, row_start + max(1, int(chunk_lines)))
            translated = np.full(
                (row_stop - row_start, samples, len(plan.bands)),
                np.float32(nodata),
                dtype=np.float32,
            )
            for output_index, band in enumerate(plan.bands):
                values = np.asarray(
                    source[band.native_source_band_index - 1, row_start:row_stop, :],
                    dtype=np.float32,
                )
                valid = np.isfinite(values)
                if math.isnan(nodata):
                    valid &= ~np.isnan(values)
                else:
                    valid &= ~np.isclose(values, nodata, atol=1e-6)
                key = str(band.target_band_index)
                if np.any(valid):
                    valid_values = values[valid]
                    observed_min = float(np.min(valid_values))
                    observed_max = float(np.max(valid_values))
                    if key not in range_bounds:
                        range_bounds[key] = [observed_min, observed_max]
                    else:
                        range_bounds[key][0] = min(
                            range_bounds[key][0], observed_min
                        )
                        range_bounds[key][1] = max(
                            range_bounds[key][1], observed_max
                        )
                target = np.float32(band.slope) * values + np.float32(band.intercept)
                translated[..., output_index] = np.where(valid, target, np.float32(nodata))
            writer.write_chunk(translated, row_start, 0)
    finally:
        writer.close()

    range_checks: dict[str, Any] = {}
    try:
        for band in plan.bands:
            key = str(band.target_band_index)
            if key not in range_bounds:
                range_checks[key] = {"status": "no_valid_source_values"}
                continue
            bounds = np.asarray(range_bounds[key], dtype=np.float32)
            range_checks[key] = _range_compatibility(
                bounds,
                band,
                np.ones(bounds.shape, dtype=bool),
            )
    except Exception:
        output_img.unlink(missing_ok=True)
        output_hdr.unlink(missing_ok=True)
        provenance_path.unlink(missing_ok=True)
        raise

    if not is_valid_envi_pair(output_img, output_hdr):
        output_img.unlink(missing_ok=True)
        output_hdr.unlink(missing_ok=True)
        raise RuntimeError(f"Translation failed to create a valid ENVI pair: {output_img}")

    translated_cube = memmap_bsq(output_img, hdr_to_dict(output_hdr))
    for index, band in enumerate(plan.bands):
        values = np.asarray(translated_cube[index])
        valid = np.isfinite(values)
        if not math.isnan(nodata):
            valid &= ~np.isclose(values, nodata, atol=1e-6)
        selected = values[valid]
        value_summaries.append(
            {
                "target_band_index": band.target_band_index,
                "target_wavelength_nm": band.target_wavelength_nm,
                "valid_fraction": float(valid.mean()),
                "minimum": float(np.min(selected)) if selected.size else None,
                "median": float(np.median(selected)) if selected.size else None,
                "maximum": float(np.max(selected)) if selected.size else None,
            }
        )
    payload = {
        "schema_version": 1,
        "status": "created",
        "product_type": "landsat_like_translated",
        "is_actual_landsat_observation": False,
        "equation": TRANSLATION_EQUATION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "spectralbridge_version": __version__,
        "translation_signature_sha256": signature,
        "source_corrected_img": str(corrected_img),
        "source_corrected_hdr": str(corrected_hdr),
        "source_fingerprint": _source_fingerprint(corrected_img, corrected_hdr),
        "coefficient_path": plan.coefficient_path,
        "coefficient_sha256": plan.coefficient_sha256,
        "analysis_run_id": plan.analysis_run_id,
        "analysis_level": plan.analysis_level,
        "weighting": plan.weighting_description,
        "translation_pair": plan.translation_pair,
        "source_sensor": plan.source_sensor,
        "target_sensor": plan.target_sensor,
        "candidate_status": plan.candidate_status,
        "evidence_boundary": plan.evidence_boundary,
        "bands": [asdict(band) for band in plan.bands],
        "training_range_checks": range_checks,
        "translated_value_summaries": value_summaries,
        "output_img": str(output_img),
        "output_hdr": str(output_hdr),
        "provenance_json": str(provenance_path),
        "warnings": [
            warning
            for warning in (
                plan.evidence_boundary,
                (
                    f"Coefficient candidate status is {plan.candidate_status}."
                    if plan.candidate_status
                    else "Coefficient artifact did not provide candidate_status metadata."
                ),
            )
            if warning
        ],
    }
    provenance_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def coefficient_rows_for_parquet(plan: DroneTranslationPlan) -> list[dict[str, Any]]:
    """Return compact band-level provenance records for table enrichment."""

    return [
        {
            "translation_pair": band.translation_pair,
            "translation_source_sensor": band.source_sensor,
            "translation_target_sensor": band.target_sensor,
            "translation_source_band": band.native_source_band_index,
            "translation_target_band": band.target_band_index,
            "translation_source_wavelength_nm": band.native_source_wavelength_nm,
            "translation_target_wavelength_nm": band.target_wavelength_nm,
            "translation_slope": band.slope,
            "translation_intercept": band.intercept,
            "translation_analysis_run_id": plan.analysis_run_id,
            "translation_weighting": plan.analysis_level,
            "translation_coefficient_sha256": plan.coefficient_sha256,
        }
        for band in plan.bands
    ]


def enrich_translated_spectral_library(
    parquet_path: str | Path,
    *,
    plan: DroneTranslationPlan,
    translation_result: dict[str, Any],
    source_package_path: str,
    working_h5_path: str,
    corrected_micasense_path: str,
    acquisition_datetime: str | None,
    overwrite: bool = False,
) -> Path:
    """Attach constant translation/provenance fields without loading pixel rows."""

    parquet_path = Path(parquet_path)
    if not parquet_path.is_file():
        raise FileNotFoundError(parquet_path)
    provenance_path = parquet_path.with_suffix(".provenance.json")
    signature_payload = {
        "translation_signature_sha256": translation_result[
            "translation_signature_sha256"
        ],
        "source_package_path": source_package_path,
        "working_h5_path": working_h5_path,
        "corrected_micasense_path": corrected_micasense_path,
        "acquisition_datetime": acquisition_datetime,
    }
    signature = hashlib.sha256(
        json.dumps(signature_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if not overwrite and provenance_path.is_file():
        try:
            previous = json.loads(provenance_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
        if previous.get("library_signature_sha256") == signature:
            return parquet_path

    def literal(value: Any) -> str:
        if value is None:
            return "NULL"
        return "'" + str(value).replace("'", "''") + "'"

    mapping_json = json.dumps(
        coefficient_rows_for_parquet(plan), sort_keys=True, separators=(",", ":")
    )
    constants = {
        "drone_platform": "drone",
        "translated_product_semantics": "landsat_like_translated",
        "translation_equation": TRANSLATION_EQUATION,
        "translation_pair": plan.translation_pair,
        "translation_source_sensor": plan.source_sensor,
        "translation_target_sensor": plan.target_sensor,
        "translation_analysis_run_id": plan.analysis_run_id,
        "translation_weighting": plan.analysis_level,
        "translation_coefficient_path": plan.coefficient_path,
        "translation_coefficient_sha256": plan.coefficient_sha256,
        "translation_band_mapping_json": mapping_json,
        "source_package_path": source_package_path,
        "working_h5_path": working_h5_path,
        "corrected_micasense_path": corrected_micasense_path,
        "translated_product_path": translation_result["output_img"],
        "acquisition_datetime": acquisition_datetime,
    }
    temp_path = parquet_path.with_name(parquet_path.stem + "__provenance_tmp.parquet")
    temp_path.unlink(missing_ok=True)
    source_literal = literal(parquet_path.as_posix())
    target_literal = literal(temp_path.as_posix())
    select_constants = ", ".join(
        f"{literal(value)} AS \"{name}\"" for name, value in constants.items()
    )
    con = duckdb.connect()
    try:
        con.execute(
            f"COPY (SELECT *, {select_constants} FROM read_parquet({source_literal})) "
            f"TO {target_literal} (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    finally:
        con.close()
    temp_path.replace(parquet_path)
    provenance_payload = {
        "schema_version": 1,
        "spectralbridge_version": __version__,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "library_signature_sha256": signature,
        **signature_payload,
        **constants,
    }
    provenance_path.write_text(
        json.dumps(provenance_payload, indent=2), encoding="utf-8"
    )
    return parquet_path


__all__ = [
    "DroneTranslationBand",
    "DroneTranslationPlan",
    "SUPPORTED_WEIGHTINGS",
    "TRANSLATION_EQUATION",
    "apply_drone_translation",
    "coefficient_rows_for_parquet",
    "enrich_translated_spectral_library",
    "load_drone_translation_plans",
    "translated_output_stem",
]
