"""Build and validate versioned production drone-translation registries.

The builder consumes only completed compact bulk outputs. It never opens source
rasters, estimates coefficients, or changes the selected production weighting.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.bulk.registry import DEFAULT_PRODUCT_REGISTRY
from spectralbridge.sensor_pairs import (
    SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
    sensor_band_identity,
)
from spectralbridge.utils.paths import get_package_data_path


DRONE_TRANSLATION_REGISTRY_SCHEMA_VERSION = 1
DRONE_TRANSLATION_COEFFICIENT_SET_VERSION = "v1"
DRONE_TRANSLATION_COEFFICIENT_RESOURCE = "drone_translation_coefficients_v1.json"
PRODUCTION_TRANSLATION_WEIGHTING = "site_balanced"
COEFFICIENT_STATUSES = frozenset({"validated", "caution", "reject"})
EXPECTED_TARGET_BANDS: Mapping[str, tuple[int, ...]] = {
    "Landsat_5_TM": (1, 2, 3, 4),
    "Landsat_7_ETM+": (1, 2, 3, 4),
    "Landsat_8_OLI": (1, 2, 3, 4, 5),
    "Landsat_9_OLI-2": (1, 2, 3, 4, 5),
}
L5_TM_B3_CAUTION = (
    "Bulk-derived translation for MicaSense 668 nm -> Landsat 5 TM B3 showed "
    "strong site dependence and poor WREF leave-one-site-out transferability. "
    "Treat this band as lower-confidence."
)
_L5_TM_B3_KEY = (
    "MicaSense_to-match_TM_and_ETM+__to__Landsat_5_TM",
    3,
)
_L5_REQUIRED_FLAGS = frozenset(
    {"weighting_dependence", "site_dependence", "weak_loso_transferability"}
)
_BULK_ARTIFACTS = {
    "candidate_coefficients": Path(
        "coefficients/candidate_translation_coefficients.parquet"
    ),
    "pair_band_summary": Path(
        "analyses/bulk_results/pair_band_summary.parquet"
    ),
    "weighting_comparison": Path(
        "analyses/bulk_results/weighting_comparison.parquet"
    ),
    "flightline_stability": Path(
        "analyses/bulk_results/flightline_stability.parquet"
    ),
    "site_stability": Path("analyses/bulk_results/site_stability.parquet"),
    "loso_transferability": Path(
        "analyses/bulk_results/loso_transferability.parquet"
    ),
    "attention_flags": Path("analyses/bulk_results/attention_flags.parquet"),
    "bulk_results_summary": Path(
        "analyses/bulk_results/bulk_results_summary.json"
    ),
}
_REQUIRED_RECORD_FIELDS = {
    "coefficient_set_version",
    "source_sensor",
    "source_band",
    "source_spectral_identity",
    "source_center_nm",
    "target_sensor",
    "target_band",
    "target_spectral_identity",
    "target_center_nm",
    "translation_pair_key",
    "band_index",
    "slope",
    "intercept",
    "weighting_strategy",
    "weighting_description",
    "fit_status",
    "r2",
    "rmse",
    "fitted_correction_percent",
    "flightline_slope_iqr",
    "site_slope_range",
    "worst_loso_r2",
    "worst_loso_rmse",
    "worst_loso_site",
    "attention_flags",
    "status",
    "status_basis",
    "warnings",
    "evidence_boundary",
    "bulk_analysis_run_id",
    "source_coefficient_artifact",
    "source_coefficient_sha256",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value: Any, *, field: str, allow_none: bool = False) -> float | None:
    if value is None or pd.isna(value):
        if allow_none:
            return None
        raise ValueError(f"Production coefficient field {field!r} is missing")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Production coefficient field {field!r} must be finite")
    return number


def _integer(value: Any, *, field: str) -> int:
    number = _finite(value, field=field)
    assert number is not None
    integer = int(number)
    if number != integer:
        raise ValueError(f"Production coefficient field {field!r} must be an integer")
    return integer


def _key(row: Mapping[str, Any]) -> tuple[str, int, int]:
    return (
        str(row["translation_pair"]),
        _integer(row["source_band_index"], field="source_band_index"),
        _integer(row["target_band_index"], field="target_band_index"),
    )


def _rows_by_key(frame: pd.DataFrame, *, label: str) -> dict[tuple[str, int, int], dict[str, Any]]:
    rows: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        key = _key(row)
        if key in rows:
            raise ValueError(f"{label} contains duplicate pair-band row {key}")
        rows[key] = row
    return rows


def _expected_pairs() -> dict[str, Any]:
    return {
        pair.key: pair
        for pair in DEFAULT_PRODUCT_REGISTRY.translation_pairs
        if pair.target_sensor in EXPECTED_TARGET_BANDS
    }


def _validate_compact_table_identities(
    rows: Mapping[tuple[str, int, int], Mapping[str, Any]],
    *,
    label: str,
    expected_pairs: Mapping[str, Any],
) -> None:
    """Require every compact QA row to describe the same physical pairing."""

    for (pair_key, source_band, target_band), row in rows.items():
        pair = expected_pairs.get(pair_key)
        if pair is None or (source_band, target_band) not in pair.band_pairs:
            raise ValueError(f"{label} contains unexpected pair-band row")
        if (
            str(row["source_sensor"]) != pair.source_sensor
            or str(row["target_sensor"]) != pair.target_sensor
        ):
            raise ValueError(
                f"{label} sensor identity conflicts with {pair_key}"
            )
        expected_band_index = pair.band_pairs.index(
            (source_band, target_band)
        ) + 1
        if _integer(row["band_index"], field="band_index") != expected_band_index:
            raise ValueError(f"{label} band_index conflicts with {pair_key}")


def packaged_drone_translation_coefficients_path() -> Path:
    """Return the packaged production registry or an actionable error."""

    try:
        return get_package_data_path(DRONE_TRANSLATION_COEFFICIENT_RESOURCE)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "No production drone translation coefficient registry is packaged. "
            "Generate it from the exact completed bulk output with "
            "scripts/build_drone_translation_registry.py; coefficients are never "
            "inferred from summary statistics."
        ) from exc


def validate_drone_translation_coefficients(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a complete static production coefficient registry."""

    if payload.get("schema_version") != DRONE_TRANSLATION_REGISTRY_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported drone translation registry schema_version: "
            f"{payload.get('schema_version')!r}"
        )
    version = str(payload.get("coefficient_set_version", "")).strip()
    if not version:
        raise ValueError("Coefficient registry must declare coefficient_set_version")
    if payload.get("production_weighting_strategy") != PRODUCTION_TRANSLATION_WEIGHTING:
        raise ValueError("Production drone coefficients must use site_balanced weighting")
    if payload.get("equation") != "target = slope * source + intercept":
        raise ValueError("Production coefficient equation/orientation is unsupported")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("Coefficient registry records must be a list")
    if payload.get("record_count") != len(records):
        raise ValueError("Coefficient registry record_count does not match records")
    declared_run_id = str(payload.get("bulk_analysis_run_id", "")).strip()
    if not declared_run_id:
        raise ValueError("Coefficient registry must declare bulk_analysis_run_id")
    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, dict) or set(source_artifacts) != set(
        _BULK_ARTIFACTS
    ):
        raise ValueError(
            "Coefficient registry must identify every required compact source artifact"
        )
    for name, relative in _BULK_ARTIFACTS.items():
        artifact = source_artifacts[name]
        if not isinstance(artifact, dict) or artifact.get("path") != relative.as_posix():
            raise ValueError(f"Source artifact path is invalid for {name}")
        sha256 = str(artifact.get("sha256", ""))
        if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
            raise ValueError(f"Source artifact SHA-256 is invalid for {name}")

    expected_pairs = _expected_pairs()
    expected_keys = {
        (pair.key, source_band, target_band)
        for pair in expected_pairs.values()
        for source_band, target_band in pair.band_pairs
    }
    seen: set[tuple[str, int, int]] = set()
    run_ids: set[str] = set()
    validated_records: list[dict[str, Any]] = []
    for original in records:
        if not isinstance(original, dict):
            raise ValueError("Every coefficient record must be an object")
        missing = sorted(_REQUIRED_RECORD_FIELDS - set(original))
        if missing:
            raise ValueError(
                "Coefficient record is missing required field(s): " + ", ".join(missing)
            )
        row = dict(original)
        pair_key = str(row["translation_pair_key"])
        source_band = _integer(row["source_band"], field="source_band")
        target_band = _integer(row["target_band"], field="target_band")
        key = (pair_key, source_band, target_band)
        if key in seen:
            raise ValueError(f"Duplicate/conflicting production coefficient: {key}")
        seen.add(key)
        if key not in expected_keys:
            raise ValueError(f"Unexpected production coefficient pair-band: {key}")
        pair = expected_pairs[pair_key]
        if row["source_sensor"] != pair.source_sensor or row["target_sensor"] != pair.target_sensor:
            raise ValueError(f"Sensor orientation conflicts with registry for {pair_key}")
        source_identity = sensor_band_identity(pair.source_sensor, source_band)
        target_identity = sensor_band_identity(pair.target_sensor, target_band)
        assert source_identity is not None and target_identity is not None
        expected_band_index = pair.band_pairs.index((source_band, target_band)) + 1
        if _integer(row["band_index"], field="band_index") != expected_band_index:
            raise ValueError(f"Coefficient band_index conflicts with registry for {key}")
        if row["source_spectral_identity"] != source_identity.spectral_identity:
            raise ValueError(f"Source spectral identity conflicts with registry for {key}")
        if row["target_spectral_identity"] != target_identity.spectral_identity:
            raise ValueError(f"Target spectral identity conflicts with registry for {key}")
        if not math.isclose(
            float(row["source_center_nm"]), source_identity.wavelength_nm, abs_tol=1e-6
        ):
            raise ValueError(f"Source wavelength conflicts with registry for {key}")
        if not math.isclose(
            float(row["target_center_nm"]), target_identity.wavelength_nm, abs_tol=1e-6
        ):
            raise ValueError(f"Target wavelength conflicts with registry for {key}")
        for field in ("slope", "intercept", "r2", "rmse", "fitted_correction_percent"):
            row[field] = _finite(row[field], field=field)
        for field in (
            "flightline_slope_iqr",
            "site_slope_range",
            "worst_loso_r2",
            "worst_loso_rmse",
        ):
            row[field] = _finite(row[field], field=field, allow_none=True)
        if row["weighting_strategy"] != PRODUCTION_TRANSLATION_WEIGHTING:
            raise ValueError(f"Non-production weighting in coefficient record {key}")
        if row["fit_status"] != "ok":
            raise ValueError(f"Production coefficient fit is not complete for {key}")
        if row["status"] not in COEFFICIENT_STATUSES:
            raise ValueError(f"Unsupported confidence status for {key}: {row['status']!r}")
        if not isinstance(row["attention_flags"], list) or not all(
            isinstance(value, str) for value in row["attention_flags"]
        ):
            raise ValueError(f"attention_flags must be a string list for {key}")
        if not isinstance(row["warnings"], list) or not all(
            isinstance(value, str) for value in row["warnings"]
        ):
            raise ValueError(f"warnings must be a string list for {key}")
        if row["coefficient_set_version"] != version:
            raise ValueError(f"Mixed coefficient_set_version values for {key}")
        if row["evidence_boundary"] != SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY:
            raise ValueError(f"Evidence-boundary language is missing or altered for {key}")
        row_run_id = str(row["bulk_analysis_run_id"]).strip()
        if not row_run_id:
            raise ValueError(f"Coefficient record omits bulk_analysis_run_id for {key}")
        candidate_artifact = source_artifacts["candidate_coefficients"]
        if (
            row["source_coefficient_artifact"] != candidate_artifact["path"]
            or row["source_coefficient_sha256"] != candidate_artifact["sha256"]
        ):
            raise ValueError(f"Coefficient source provenance conflicts for {key}")
        run_ids.add(row_run_id)
        validated_records.append(row)

    missing_keys = expected_keys - seen
    extra_keys = seen - expected_keys
    if missing_keys or extra_keys or len(records) != 18:
        raise ValueError(
            "Production registry must contain exactly the 18 built-in physical "
            f"pair-band coefficients; missing={sorted(missing_keys)}, extra={sorted(extra_keys)}"
        )
    if len(run_ids) != 1 or next(iter(run_ids), "") != declared_run_id:
        raise ValueError("Coefficient registry mixes or omits bulk_analysis_run_id")
    l5_record = next(
        row
        for row in validated_records
        if (row["translation_pair_key"], row["target_band"]) == _L5_TM_B3_KEY
    )
    if l5_record["status"] != "caution" or L5_TM_B3_CAUTION not in l5_record["warnings"]:
        raise ValueError("Landsat 5 TM B3 must retain its caution status and warning")
    return {**dict(payload), "records": validated_records}


def load_drone_translation_coefficients(
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Load the packaged or explicitly supplied static production registry."""

    resolved = (
        packaged_drone_translation_coefficients_path()
        if path is None
        else Path(path).expanduser().resolve()
    )
    if not resolved.is_file():
        raise FileNotFoundError(f"Drone translation coefficient registry not found: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unreadable drone translation coefficient registry: {resolved}") from exc
    return validate_drone_translation_coefficients(payload)


def get_drone_translation_coefficient(
    target_sensor: str,
    target_band: int,
    *,
    path: str | Path | None = None,
) -> dict[str, Any]:
    """Return one unambiguous production target-band coefficient."""

    payload = load_drone_translation_coefficients(path)
    matches = [
        row
        for row in payload["records"]
        if row["target_sensor"] == target_sensor
        and int(row["target_band"]) == int(target_band)
    ]
    if len(matches) != 1:
        raise KeyError(
            f"Expected one coefficient for {target_sensor} B{target_band}, found {len(matches)}"
        )
    return matches[0]


def build_drone_translation_coefficient_registry(
    bulk_output: str | Path,
    output_path: str | Path,
    *,
    coefficient_set_version: str = DRONE_TRANSLATION_COEFFICIENT_SET_VERSION,
    overwrite: bool = False,
) -> Path:
    """Build a static registry from exact compact bulk result artifacts."""

    root = Path(bulk_output).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    paths = {name: root / relative for name, relative in _BULK_ARTIFACTS.items()}
    missing = [path for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Completed compact bulk output is missing required registry inputs: "
            + ", ".join(path.as_posix() for path in missing)
        )
    if output.exists() and not overwrite:
        raise FileExistsError(f"Coefficient registry already exists: {output}")

    candidates = pd.read_parquet(paths["candidate_coefficients"])
    selected = candidates.loc[
        candidates["analysis_level"].astype(str) == PRODUCTION_TRANSLATION_WEIGHTING
    ].copy()
    if len(selected) != 18 or set(selected["status"].astype(str)) != {"ok"}:
        raise ValueError(
            "Expected exactly 18 completed site-balanced candidate coefficients; "
            f"found {len(selected)} rows with statuses {sorted(set(selected['status'].astype(str)))}"
        )
    selected_by_key = _rows_by_key(selected, label="candidate coefficients")
    summary_by_key = _rows_by_key(
        pd.read_parquet(paths["pair_band_summary"]), label="pair-band summary"
    )
    weighting = pd.read_parquet(paths["weighting_comparison"])
    weighting = weighting.loc[
        weighting["analysis_level"].astype(str) == PRODUCTION_TRANSLATION_WEIGHTING
    ]
    weighting_by_key = _rows_by_key(weighting, label="weighting comparison")
    flightline_by_key = _rows_by_key(
        pd.read_parquet(paths["flightline_stability"]),
        label="flightline stability",
    )
    site_by_key = _rows_by_key(
        pd.read_parquet(paths["site_stability"]), label="site stability"
    )
    loso_by_key = _rows_by_key(
        pd.read_parquet(paths["loso_transferability"]),
        label="LOSO transferability",
    )
    flag_frame = pd.read_parquet(paths["attention_flags"])
    flags_by_key: dict[tuple[str, int, int], list[str]] = {}
    for row in flag_frame.to_dict(orient="records"):
        flags_by_key.setdefault(_key(row), []).append(str(row["flag_code"]))
    summary_payload = json.loads(
        paths["bulk_results_summary"].read_text(encoding="utf-8")
    )

    run_ids = set(selected["analysis_run_id"].astype(str))
    if len(run_ids) != 1:
        raise ValueError("Site-balanced coefficient rows mix analysis_run_id values")
    run_id = next(iter(run_ids))
    reported_run_id = str(summary_payload.get("bulk_analysis_run_id") or "")
    if reported_run_id and reported_run_id != run_id:
        raise ValueError(
            "Bulk results summary and candidate coefficients disagree on analysis_run_id"
        )

    expected_keys = {
        (pair.key, source_band, target_band)
        for pair in _expected_pairs().values()
        for source_band, target_band in pair.band_pairs
    }
    table_keys = {
        "candidate coefficients": set(selected_by_key),
        "pair-band summary": set(summary_by_key),
        "weighting comparison": set(weighting_by_key),
        "flightline stability": set(flightline_by_key),
        "site stability": set(site_by_key),
        "LOSO transferability": set(loso_by_key),
    }
    for label, keys in table_keys.items():
        if keys != expected_keys:
            raise ValueError(
                f"{label} does not match the expected 18 pair-band keys; "
                f"missing={sorted(expected_keys - keys)}, extra={sorted(keys - expected_keys)}"
            )
    expected_pairs = _expected_pairs()
    table_rows = {
        "candidate coefficients": selected_by_key,
        "pair-band summary": summary_by_key,
        "weighting comparison": weighting_by_key,
        "flightline stability": flightline_by_key,
        "site stability": site_by_key,
        "LOSO transferability": loso_by_key,
    }
    for label, rows in table_rows.items():
        _validate_compact_table_identities(
            rows,
            label=label,
            expected_pairs=expected_pairs,
        )
    unexpected_flag_keys = set(flags_by_key) - expected_keys
    if unexpected_flag_keys:
        raise ValueError(
            "Attention flags contain unexpected pair-band keys: "
            f"{sorted(unexpected_flag_keys)}"
        )

    l5_flags = set(flags_by_key.get((_L5_TM_B3_KEY[0], 3, 3), []))
    if not _L5_REQUIRED_FLAGS <= l5_flags:
        raise ValueError(
            "Bulk QA does not support the required Landsat 5 TM B3 caution; "
            f"missing flags={sorted(_L5_REQUIRED_FLAGS - l5_flags)}"
        )

    records: list[dict[str, Any]] = []
    candidate_relative = _BULK_ARTIFACTS["candidate_coefficients"].as_posix()
    candidate_sha = _sha256(paths["candidate_coefficients"])
    for key in sorted(expected_keys):
        candidate = selected_by_key[key]
        weighting_row = weighting_by_key[key]
        flightline = flightline_by_key[key]
        site = site_by_key[key]
        loso = loso_by_key[key]
        pair_key, source_band, target_band = key
        source_sensor = str(candidate["source_sensor"])
        target_sensor = str(candidate["target_sensor"])
        source_identity = sensor_band_identity(source_sensor, source_band)
        target_identity = sensor_band_identity(target_sensor, target_band)
        assert source_identity is not None and target_identity is not None
        flags = sorted(set(flags_by_key.get(key, [])))
        is_l5_b3 = (pair_key, target_band) == _L5_TM_B3_KEY
        status = "caution" if flags or is_l5_b3 else "validated"
        warnings = [L5_TM_B3_CAUTION] if is_l5_b3 else []
        records.append(
            {
                "coefficient_set_version": coefficient_set_version,
                "source_sensor": source_sensor,
                "source_band": source_band,
                "source_spectral_identity": source_identity.spectral_identity,
                "source_center_nm": source_identity.wavelength_nm,
                "target_sensor": target_sensor,
                "target_band": target_band,
                "target_spectral_identity": target_identity.spectral_identity,
                "target_center_nm": target_identity.wavelength_nm,
                "translation_pair_key": pair_key,
                "band_index": _integer(candidate["band_index"], field="band_index"),
                "slope": _finite(candidate["slope"], field="slope"),
                "intercept": _finite(candidate["intercept"], field="intercept"),
                "weighting_strategy": PRODUCTION_TRANSLATION_WEIGHTING,
                "weighting_description": str(candidate["weighting"]),
                "fit_status": str(candidate["status"]),
                "r2": _finite(candidate["r2"], field="r2"),
                "rmse": _finite(candidate["rmse"], field="rmse"),
                "fitted_correction_percent": _finite(
                    weighting_row["fitted_correction_percent"],
                    field="fitted_correction_percent",
                ),
                "flightline_slope_iqr": _finite(
                    flightline.get("slope_iqr"),
                    field="flightline_slope_iqr",
                    allow_none=True,
                ),
                "site_slope_range": _finite(
                    site.get("slope_range"), field="site_slope_range", allow_none=True
                ),
                "worst_loso_r2": _finite(
                    loso.get("held_out_r2_min"),
                    field="worst_loso_r2",
                    allow_none=True,
                ),
                "worst_loso_rmse": _finite(
                    loso.get("held_out_rmse_max"),
                    field="worst_loso_rmse",
                    allow_none=True,
                ),
                "worst_loso_site": loso.get("weakest_held_out_site"),
                "attention_flags": flags,
                "status": status,
                "status_basis": (
                    "caution: one or more configured bulk QA attention flags"
                    if status == "caution"
                    else "validated: complete fit with no configured bulk QA attention flag"
                ),
                "warnings": warnings,
                "evidence_boundary": SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
                "bulk_analysis_run_id": run_id,
                "source_coefficient_artifact": candidate_relative,
                "source_coefficient_sha256": candidate_sha,
            }
        )

    payload = {
        "schema_version": DRONE_TRANSLATION_REGISTRY_SCHEMA_VERSION,
        "coefficient_set_version": coefficient_set_version,
        "production_weighting_strategy": PRODUCTION_TRANSLATION_WEIGHTING,
        "equation": "target = slope * source + intercept",
        "product_semantics": "corrected MicaSense to translated Landsat-like reflectance",
        "evidence_boundary": SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
        "bulk_analysis_run_id": run_id,
        "record_count": len(records),
        "source_artifacts": {
            name: {
                "path": relative.as_posix(),
                "sha256": _sha256(paths[name]),
            }
            for name, relative in _BULK_ARTIFACTS.items()
        },
        "records": records,
    }
    validated = validate_drone_translation_coefficients(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output, validated)
    return output


__all__ = [
    "COEFFICIENT_STATUSES",
    "DRONE_TRANSLATION_COEFFICIENT_RESOURCE",
    "DRONE_TRANSLATION_COEFFICIENT_SET_VERSION",
    "DRONE_TRANSLATION_REGISTRY_SCHEMA_VERSION",
    "EXPECTED_TARGET_BANDS",
    "L5_TM_B3_CAUTION",
    "PRODUCTION_TRANSLATION_WEIGHTING",
    "build_drone_translation_coefficient_registry",
    "get_drone_translation_coefficient",
    "load_drone_translation_coefficients",
    "packaged_drone_translation_coefficients_path",
    "validate_drone_translation_coefficients",
]
