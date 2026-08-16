"""Stage QA emission from canonical on-disk pipeline artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from spectralbridge.envi import hdr_to_dict, read_envi_cube
from spectralbridge.brightness_config import load_brightness_coefficients

from .brightness import brightness_correction_metrics
from .metrics import reflectance_summary, residual_metrics, seam_score
from .paths import StageQAPaths, normalize_stage_id
from .plots import (
    format_location_label,
    qa_plot_contract,
    render_artifact_inventory,
    render_brightness_diagnostics,
    render_correction_parameters,
    render_correction_overview,
    render_envi_overview,
    render_parquet_overview,
    spatial_plot_context,
)
from .reporting import render_stage_html
from .schema import SCHEMA_VERSION, QACheck, QAStatus, StageQAReport, overall_status
from .thresholds import (
    KNOWN_BAD_WAVELENGTH_RANGES_NM,
    QAThresholds,
    classify_high_bad,
    classify_low_bad,
)


_STAGE_NAMES = {
    "acquisition": "Source acquisition",
    "input_data": "Input reflectance",
    "correction_parameters": "Correction parameters",
    "brdf_topographic_correction": "BRDF and topographic correction",
    "spectral_convolution": "Spectral convolution",
    "analysis_tables": "Parquet extraction and merge",
}


# Artifact identity and provenance -------------------------------------------------


def _package_version() -> str:
    """Return the installed distribution version used in report provenance."""

    try:
        return version("spectralbridge")
    except PackageNotFoundError:
        return "unknown"


def _git_sha() -> str:
    """Return the repository revision without making Git a runtime dependency."""

    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _fingerprint(path: Path) -> tuple[str | None, str]:
    """Return a bounded deterministic artifact fingerprint and method label."""

    if not path.exists() or not path.is_file():
        return None, "unavailable"
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(str(size).encode("ascii"))
    block = 1024 * 1024
    with path.open("rb") as stream:
        if size <= 64 * block:
            for chunk in iter(lambda: stream.read(block), b""):
                digest.update(chunk)
            method = "sha256_full_v1"
        else:
            digest.update(stream.read(4 * block))
            stream.seek(max(0, size - 4 * block))
            digest.update(stream.read(4 * block))
            method = "sha256_size_head_tail_v1"
    return digest.hexdigest(), method


def _artifact(path: Path) -> dict[str, Any]:
    """Describe one declared input or output using JSON-safe values."""

    path = Path(path)
    digest, method = _fingerprint(path)
    return {
        "path": str(path.resolve(strict=False)),
        "name": path.name,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "fingerprint": digest,
        "fingerprint_method": method,
    }


# ENVI metadata, sampling, and unit conversion ------------------------------------


def _nodata(header: dict[str, Any]) -> float | None:
    """Read a scalar ENVI NoData value when one is available."""

    value = header.get("data ignore value")
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _scale_factor(header: dict[str, Any]) -> float | None:
    """Read a positive ENVI reflectance divisor when one is available."""

    value = header.get("reflectance scale factor")
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    try:
        factor = float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    return factor if factor is not None and factor > 0 else None


def _h5_reflectance_metadata(path: Path) -> tuple[float | None, float | None]:
    """Read scale/no-data attributes without loading the source reflectance cube."""

    try:
        import h5py
    except ImportError:
        return None, None
    try:
        with h5py.File(path, "r") as source:
            matches: list[Any] = []

            def _visitor(name: str, obj: Any) -> None:
                if isinstance(obj, h5py.Dataset) and name.lower().endswith(
                    "reflectance_data"
                ):
                    matches.append(obj)

            source.visititems(_visitor)
            if not matches:
                return None, None
            dataset = matches[0]
            scale = next(
                (
                    dataset.attrs[key]
                    for key in ("Scale_Factor", "scale_factor", "Scale Factor")
                    if key in dataset.attrs
                ),
                None,
            )
            nodata = next(
                (
                    dataset.attrs[key]
                    for key in ("Data_Ignore_Value", "_FillValue", "NoData")
                    if key in dataset.attrs
                ),
                None,
            )
            return (
                float(np.asarray(scale).reshape(-1)[0]) if scale is not None else None,
                (
                    float(np.asarray(nodata).reshape(-1)[0])
                    if nodata is not None
                    else None
                ),
            )
    except (OSError, TypeError, ValueError):
        return None, None


def _input_reflectance_metadata(
    input_paths: list[Path],
) -> tuple[float | None, float | None]:
    scale = nodata = None
    for path in input_paths:
        if path.suffix.lower() == ".hdr" and path.exists():
            header = hdr_to_dict(path)
            scale = scale or _scale_factor(header)
            nodata = nodata if nodata is not None else _nodata(header)
        elif path.suffix.lower() in {".h5", ".hdf5"} and path.exists():
            h5_scale, h5_nodata = _h5_reflectance_metadata(path)
            scale = scale or h5_scale
            nodata = nodata if nodata is not None else h5_nodata
    return scale, nodata


def _unit_reflectance(
    values: np.ndarray,
    *,
    scale_factor: float,
    nodata: float | None,
) -> np.ndarray:
    """Return a diagnostic copy in unit reflectance with NoData represented by NaN."""

    result = np.asarray(values, dtype=np.float32).copy()
    invalid = ~np.isfinite(result)
    if nodata is not None:
        invalid |= np.isclose(result, nodata, atol=1e-6)
    result = result / np.float32(scale_factor)
    result[invalid] = np.nan
    return result


def _wavelengths(header: dict[str, Any], bands: int) -> np.ndarray:
    """Return a complete numeric wavelength vector or an explicit empty array."""

    try:
        values = np.asarray(header.get("wavelength"), dtype=np.float64).reshape(-1)
    except (TypeError, ValueError):
        return np.array([], dtype=np.float64)
    return values if values.size == bands else np.array([], dtype=np.float64)


def _preview(cube: np.ndarray, max_pixels: int) -> np.ndarray:
    """Sample a band-first cube on a deterministic regular spatial grid."""

    _, rows, cols = cube.shape
    step = max(1, int(np.sqrt((rows * cols) / max(1, max_pixels))))
    return np.asarray(cube[:, ::step, ::step], dtype=np.float32)


# Reflectance and spatial-support interpretation ----------------------------------


def _known_bad_band_mask(wavelengths: np.ndarray, bands: int) -> np.ndarray:
    """Classify established poor-quality wavelengths without changing data."""

    mask = np.zeros(bands, dtype=bool)
    if wavelengths.size != bands:
        return mask
    for wavelength_range in KNOWN_BAD_WAVELENGTH_RANGES_NM:
        mask |= (wavelengths >= wavelength_range["minimum_nm"]) & (
            wavelengths <= wavelength_range["maximum_nm"]
        )
    return mask


def _known_bad_band_reason(wavelength_nm: float) -> str | None:
    for wavelength_range in KNOWN_BAD_WAVELENGTH_RANGES_NM:
        if (
            wavelength_range["minimum_nm"]
            <= wavelength_nm
            <= wavelength_range["maximum_nm"]
        ):
            return str(wavelength_range["reason"])
    return None


def _footprint_summary(preview: np.ndarray) -> dict[str, Any]:
    """Separate structural bounding-box background from observed support."""

    finite = np.isfinite(preview)
    footprint = np.any(finite, axis=0)
    bounding_box_pixels = int(footprint.size)
    footprint_pixels = int(np.count_nonzero(footprint))
    within_footprint_cells = footprint_pixels * int(preview.shape[0])
    within_footprint_valid = int(np.count_nonzero(finite[:, footprint]))
    occupancy = (
        float(footprint_pixels / bounding_box_pixels) if bounding_box_pixels else 0.0
    )
    return {
        "method": "any_band_finite_on_deterministic_sample",
        "bounding_box_pixels": bounding_box_pixels,
        "footprint_pixels": footprint_pixels,
        "bounding_box_footprint_fraction": occupancy,
        "structural_background_fraction": float(1.0 - occupancy),
        "within_footprint_cells": within_footprint_cells,
        "within_footprint_valid_cells": within_footprint_valid,
        "within_footprint_valid_fraction": (
            float(within_footprint_valid / within_footprint_cells)
            if within_footprint_cells
            else None
        ),
        "data_modified": False,
    }


def _spectral_quality_summary(
    preview: np.ndarray,
    wavelengths: np.ndarray,
    known_bad: np.ndarray,
    all_band_overbright_fraction: float | None,
) -> dict[str, Any]:
    """Report retained bad-band and usable-band distributions separately."""

    has_wavelengths = wavelengths.size == preview.shape[0]
    usable = ~known_bad if has_wavelengths else np.zeros(preview.shape[0], dtype=bool)
    usable_summary = reflectance_summary(preview[usable]) if np.any(usable) else None
    bad_summary = reflectance_summary(preview[known_bad]) if np.any(known_bad) else None
    bad_indices = np.flatnonzero(known_bad)
    return {
        "classification_mode": "report_only_no_masking",
        "data_modified": False,
        "classification_available": has_wavelengths,
        "known_bad_wavelength_ranges_nm": [
            dict(item) for item in KNOWN_BAD_WAVELENGTH_RANGES_NM
        ],
        "known_bad_band_count": int(bad_indices.size) if has_wavelengths else None,
        "known_bad_band_fraction": (
            float(bad_indices.size / preview.shape[0]) if has_wavelengths else None
        ),
        "known_bad_band_indices": bad_indices.tolist(),
        "known_bad_band_wavelengths_nm": (
            wavelengths[known_bad].astype(float).tolist() if has_wavelengths else []
        ),
        "usable_band_count": int(np.count_nonzero(usable)) if has_wavelengths else None,
        "all_band_overbright_fraction": all_band_overbright_fraction,
        "known_bad_band_overbright_fraction": (
            bad_summary["overbright_fraction"] if bad_summary else None
        ),
        "usable_band_overbright_fraction": (
            usable_summary["overbright_fraction"] if usable_summary else None
        ),
    }


def _bandwise(
    preview: np.ndarray,
    wavelengths: np.ndarray,
    known_bad: np.ndarray,
) -> list[dict[str, Any]]:
    """Return report-only summaries for every retained source band."""

    rows = []
    has_wavelengths = wavelengths.size == preview.shape[0]
    for index in range(preview.shape[0]):
        summary = reflectance_summary(preview[index], nodata=-9999.0)
        wavelength_nm = float(wavelengths[index]) if has_wavelengths else None
        rows.append(
            {
                "band_index": index,
                "wavelength_nm": wavelength_nm,
                "valid_fraction": summary["valid_fraction"],
                "median": summary["q50"],
                "q05": summary["q05"],
                "q95": summary["q95"],
                "negative_fraction": summary["negative_fraction"],
                "overbright_fraction": summary["overbright_fraction"],
                "quality_label": (
                    "known_bad_retained"
                    if known_bad[index]
                    else "usable"
                    if has_wavelengths
                    else "unclassified_retained"
                ),
                "quality_reason": (
                    _known_bad_band_reason(wavelength_nm)
                    if known_bad[index] and wavelength_nm is not None
                    else None
                ),
                "data_retained": True,
            }
        )
    return rows


def _representative_seams(
    cube: np.ndarray,
    *,
    chunk_shape: tuple[int, int] | None,
    mode: str,
    nodata: float | None,
) -> dict[str, Any] | None:
    if chunk_shape is None:
        return None
    chunk_rows, chunk_cols = chunk_shape
    if chunk_rows >= cube.shape[1] and chunk_cols >= cube.shape[2]:
        return None
    count = min(cube.shape[0], 25 if mode == "deep" else 5)
    indices = np.unique(np.linspace(0, cube.shape[0] - 1, count, dtype=int))
    subset = np.asarray(cube[indices], dtype=np.float32)
    result = seam_score(
        subset,
        chunk_rows=chunk_rows,
        chunk_cols=chunk_cols,
        nodata=nodata,
    )
    for item, source_index in zip(result["bands"], indices, strict=True):
        item["source_band_index"] = int(source_index)
    return result


# Stage-specific non-raster diagnostics -------------------------------------------


def _parquet_metrics(paths: Iterable[Path]) -> dict[str, Any]:
    """Read Parquet counts and schemas through DuckDB without materializing tables."""

    tables: list[dict[str, Any]] = []
    try:
        import duckdb
    except ImportError:
        return {"tables": [], "not_evaluated_reason": "DuckDB is not installed."}
    connection = duckdb.connect()
    try:
        for path in paths:
            path = Path(path)
            if not path.exists() or path.suffix != ".parquet":
                continue
            quoted = str(path).replace("'", "''")
            try:
                row_count = int(
                    connection.execute(
                        f"SELECT count(*) FROM read_parquet('{quoted}')"
                    ).fetchone()[0]
                )
                columns = [
                    row[0]
                    for row in connection.execute(
                        f"DESCRIBE SELECT * FROM read_parquet('{quoted}')"
                    ).fetchall()
                ]
                tables.append(
                    {
                        "path": str(path),
                        "rows": row_count,
                        "columns": len(columns),
                        "column_names": columns,
                        "size_bytes": path.stat().st_size,
                    }
                )
            except Exception as exc:
                tables.append(
                    {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}
                )
    finally:
        connection.close()
    return {"tables": tables}


def _array_summary(value: Any) -> dict[str, Any] | None:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    finite = array[np.isfinite(array)]
    if not finite.size:
        return {"shape": list(array.shape), "finite_count": 0}
    return {
        "shape": list(array.shape),
        "finite_count": int(finite.size),
        "minimum": float(np.min(finite)),
        "median": float(np.median(finite)),
        "maximum": float(np.max(finite)),
    }


def _geometry_range_review(geometry: dict[str, Any]) -> dict[str, Any]:
    """Flag physically implausible persisted summaries without altering them."""

    limits = {
        "solar_zn": (0.0, np.pi / 2.0),
        "sensor_zn": (0.0, np.pi / 2.0),
        "slope": (0.0, np.pi / 2.0),
        "solar_az": (0.0, 2.0 * np.pi),
        "sensor_az": (0.0, 2.0 * np.pi),
        "aspect": (0.0, 2.0 * np.pi),
    }
    fields = []
    for name, (minimum, maximum) in limits.items():
        summary = geometry.get(name)
        if not isinstance(summary, dict):
            continue
        values = {}
        for key in ("min", "mean", "max"):
            if summary.get(key) is None:
                continue
            try:
                values[key] = float(summary[key])
            except (TypeError, ValueError):
                values[key] = np.nan
        out_of_range = [
            key
            for key, value in values.items()
            if not np.isfinite(value) or value < minimum or value > maximum
        ]
        fields.append(
            {
                "field": name,
                "expected_range_radians": [minimum, maximum],
                "out_of_range_summaries": out_of_range,
                "requires_review": bool(out_of_range),
            }
        )
    return {
        "method": "review_persisted_min_mean_max_without_masking",
        "data_modified": False,
        "fields": fields,
        "fields_checked": len(fields),
        "fields_requiring_review": sum(row["requires_review"] for row in fields),
    }


def _brightness_pairs(output_paths: list[Path]) -> list[tuple[Path, Path]]:
    """Find persisted undarkened/final Landsat image pairs by naming contract."""

    pairs = []
    for after in output_paths:
        name = after.name.lower()
        if (
            after.suffix.lower() != ".img"
            or "landsat" not in name
            or "undarkened" in name
            or not name.endswith("_envi.img")
        ):
            continue
        before = after.with_name(
            f"{after.name[: -len('_envi.img')]}_undarkened_envi.img"
        )
        if before.exists() and before.with_suffix(".hdr").exists():
            pairs.append((before, after))
    return pairs


def _brightness_product_label(path: Path) -> str:
    """Derive a concise sensor label for report text and figures."""

    name = path.stem
    marker = "_landsat_"
    if marker in name:
        return f"Landsat {name.split(marker, 1)[1].removesuffix('_envi').upper()}"
    return name


def _brightness_diagnostics(
    output_paths: list[Path],
    *,
    max_pixels: int,
) -> list[dict[str, Any]]:
    """Audit every discoverable Landsat brightness pair on bounded previews."""

    expected = load_brightness_coefficients("landsat_to_micasense")
    diagnostics: list[dict[str, Any]] = []
    for before_path, after_path in _brightness_pairs(output_paths):
        before_header = hdr_to_dict(before_path.with_suffix(".hdr"))
        after_header = hdr_to_dict(after_path.with_suffix(".hdr"))
        before_cube = read_envi_cube(before_path, before_header)
        after_cube = read_envi_cube(after_path, after_header)
        if before_cube.shape != after_cube.shape:
            diagnostics.append(
                {
                    "product": _brightness_product_label(after_path),
                    "before_path": str(before_path),
                    "after_path": str(after_path),
                    "error": (
                        "Before/after shape mismatch: "
                        f"{before_cube.shape} vs {after_cube.shape}"
                    ),
                }
            )
            continue
        before_preview = _unit_reflectance(
            _preview(before_cube, max_pixels),
            scale_factor=_scale_factor(before_header) or 1.0,
            nodata=_nodata(before_header),
        )
        after_preview = _unit_reflectance(
            _preview(after_cube, max_pixels),
            scale_factor=_scale_factor(after_header) or 1.0,
            nodata=_nodata(after_header),
        )
        result = brightness_correction_metrics(
            before_preview,
            after_preview,
            expected_percent=expected,
        )
        result.update(
            {
                "product": _brightness_product_label(after_path),
                "before_path": str(before_path),
                "after_path": str(after_path),
                "coefficient_source": "landsat_to_micasense.json",
                "before_preview": before_preview,
                "after_preview": after_preview,
            }
        )
        diagnostics.append(result)
    return diagnostics


# Report assembly -----------------------------------------------------------------


def _context_fingerprint(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def emit_stage_qa(
    *,
    flightline_dir: Path,
    stage_id: str,
    inputs: Iterable[Path] = (),
    outputs: Iterable[Path] = (),
    parameters: dict[str, Any] | None = None,
    mode: str = "standard",
    primary_img: Path | None = None,
    reference_img: Path | None = None,
    chunk_shape: tuple[int, int] | None = None,
    thresholds: QAThresholds | None = None,
    force: bool = False,
) -> tuple[Path, dict[str, Any]]:
    """Emit or reuse one deterministic stage QA JSON/HTML report.

    Missing scientific inputs are recorded as ``NOT EVALUATED`` rather than
    being silently omitted.  ``mode='deep'`` increases sampling and seam-band
    coverage but does not rerun the scientific correction itself.
    """

    mode = mode.strip().lower()
    if mode not in {"standard", "deep"}:
        raise ValueError("QA mode must be 'standard' or 'deep'")
    stage_id = normalize_stage_id(stage_id)
    paths = StageQAPaths(Path(flightline_dir), stage_id)
    location_label = format_location_label(Path(flightline_dir).name)
    input_paths = [Path(path) for path in inputs]
    input_records = [_artifact(path) for path in input_paths]
    output_paths = [Path(path) for path in outputs]
    output_records = [_artifact(path) for path in output_paths]
    thresholds = thresholds or QAThresholds()
    parameters = dict(parameters or {})
    fingerprint_payload = {
        "schema": SCHEMA_VERSION,
        "stage_id": stage_id,
        "mode": mode,
        "inputs": input_records,
        "outputs": output_records,
        "parameters": parameters,
        "thresholds": thresholds.to_dict(),
        "package_version": _package_version(),
    }
    context_fingerprint = _context_fingerprint(fingerprint_payload)
    if not force and paths.json.exists() and paths.html.exists():
        existing = json.loads(paths.json.read_text(encoding="utf-8"))
        if (
            existing.get("provenance", {}).get("context_fingerprint")
            == context_fingerprint
        ):
            return paths.html, existing

    checks: list[QACheck] = []
    metrics: dict[str, Any] = {
        "plot_contract": {
            **qa_plot_contract(),
            "location_label": location_label,
            "spatial": None,
        }
    }
    unavailable: list[dict[str, str]] = []
    plot_paths: list[str] = []
    sample: dict[str, Any] = {"strategy": "none", "max_pixels": 0}
    fallback_scale, fallback_nodata = _input_reflectance_metadata(input_paths)

    if not output_records:
        checks.append(
            QACheck(
                check_id="stage_outputs_present",
                status=QAStatus.FAIL,
                value=0,
                provisional=False,
                interpretation="A stage must declare at least one output artifact.",
            )
        )
    for record in output_records:
        checks.append(
            QACheck(
                check_id=f"output_exists:{record['name']}",
                status=QAStatus.PASS if record["exists"] else QAStatus.FAIL,
                value=bool(record["exists"]),
                provisional=False,
                interpretation="The canonical stage output exists on disk.",
            )
        )

    if stage_id == "acquisition":
        render_artifact_inventory(
            output_records,
            paths.overview_png,
            title=_STAGE_NAMES[stage_id],
            location_label=location_label,
        )
        plot_paths.append(paths.overview_png.name)

    primary_cube = None
    primary_header: dict[str, Any] | None = None
    wavelengths = np.array([], dtype=np.float64)
    if primary_img is not None and Path(primary_img).exists():
        primary_img = Path(primary_img)
        primary_header = hdr_to_dict(primary_img.with_suffix(".hdr"))
        primary_cube = read_envi_cube(primary_img, primary_header)
        max_pixels = 100_000 if mode == "deep" else 25_000
        primary_scale = _scale_factor(primary_header) or fallback_scale or 1.0
        nodata = _nodata(primary_header)
        if nodata is None:
            nodata = fallback_nodata
        preview = _unit_reflectance(
            _preview(primary_cube, max_pixels),
            scale_factor=primary_scale,
            nodata=nodata,
        )
        wavelengths = _wavelengths(primary_header, primary_cube.shape[0])
        spatial_context = spatial_plot_context(primary_header, primary_cube.shape)
        summary = reflectance_summary(preview)
        footprint = _footprint_summary(preview)
        known_bad = _known_bad_band_mask(wavelengths, preview.shape[0])
        spectral_quality = _spectral_quality_summary(
            preview,
            wavelengths,
            known_bad,
            summary["overbright_fraction"],
        )
        metrics["reflectance"] = summary
        metrics["spatial_footprint"] = footprint
        metrics["spectral_quality"] = spectral_quality
        metrics["plot_contract"] = {
            **qa_plot_contract(),
            "location_label": location_label,
            "spatial": spatial_context,
        }
        metrics["reflectance_scaling"] = {
            "stored_value_divisor": primary_scale,
            "nodata_value": nodata,
            "source": (
                "primary_header"
                if _scale_factor(primary_header) is not None
                else "input_artifact_metadata"
                if fallback_scale is not None
                else "unit_default"
            ),
        }
        metrics["bandwise"] = _bandwise(preview, wavelengths, known_bad)
        sample = {
            "strategy": "deterministic_regular_grid",
            "max_pixels": max_pixels,
            "sampled_shape": list(preview.shape),
            "source_shape": list(primary_cube.shape),
        }
        checks.extend(
            [
                classify_low_bad(
                    "within_footprint_valid_reflectance_fraction",
                    footprint["within_footprint_valid_fraction"],
                    warn=thresholds.valid_fraction_warn,
                    fail=thresholds.valid_fraction_fail,
                    units="fraction",
                    interpretation="Valid spectral support should remain high inside the observed flight footprint; structural background outside it is reported separately.",
                ),
                classify_high_bad(
                    "negative_reflectance_fraction",
                    summary["negative_fraction"],
                    warn=thresholds.negative_fraction_warn,
                    fail=thresholds.negative_fraction_fail,
                    units="fraction",
                    interpretation="Large negative fractions may indicate correction or scaling artifacts.",
                ),
                classify_high_bad(
                    "usable_band_reflectance_above_1_2_fraction",
                    spectral_quality["usable_band_overbright_fraction"],
                    warn=thresholds.overbright_fraction_warn,
                    fail=thresholds.overbright_fraction_fail,
                    units="fraction",
                    interpretation="Unexpected values above 1.2 are evaluated on wavelengths not already labeled as known poor-quality regions; the all-band fraction remains reported.",
                ),
            ]
        )
        if spectral_quality["classification_available"]:
            known_bad_count = spectral_quality["known_bad_band_count"]
            checks.append(
                QACheck(
                    check_id="known_bad_spectral_bands_retained",
                    status=QAStatus.WARN if known_bad_count else QAStatus.PASS,
                    value=known_bad_count,
                    units="bands",
                    provisional=False,
                    interpretation="Established poor-quality wavelength regions are labeled in QA and retained in the product.",
                    reason=(
                        "No masking, filtering, replacement, or file modification was applied."
                        if known_bad_count
                        else None
                    ),
                )
            )
        else:
            checks.append(
                QACheck(
                    check_id="known_bad_spectral_bands_retained",
                    status=QAStatus.NOT_EVALUATED,
                    provisional=False,
                    interpretation="Known poor-quality wavelength regions require a complete wavelength vector.",
                    reason="The ENVI header did not provide one wavelength for every band; no data were changed.",
                )
            )
            unavailable.append(
                {
                    "diagnostic": "known_bad_spectral_band_classification",
                    "reason": "The ENVI header did not provide one wavelength for every band.",
                }
            )
        render_envi_overview(
            preview,
            wavelengths,
            paths.overview_png,
            title=_STAGE_NAMES.get(stage_id, stage_id),
            location_label=location_label,
            spatial_context=spatial_context,
        )
        plot_paths.append(paths.overview_png.name)
        if stage_id == "input_data":
            unavailable.append(
                {
                    "diagnostic": "cloud_shadow_water_saturation_masks",
                    "reason": "The raw ENVI contract does not encode all source QA mask classes in a common field.",
                }
            )

    if (
        reference_img is not None
        and primary_cube is not None
        and Path(reference_img).exists()
    ):
        reference_img = Path(reference_img)
        reference_header = hdr_to_dict(reference_img.with_suffix(".hdr"))
        reference_cube = read_envi_cube(reference_img, reference_header)
        if reference_cube.shape != primary_cube.shape:
            unavailable.append(
                {
                    "diagnostic": "paired_before_after_metrics",
                    "reason": f"Input and output shapes differ: {reference_cube.shape} vs {primary_cube.shape}.",
                }
            )
        else:
            max_pixels = 100_000 if mode == "deep" else 25_000
            primary_scale = _scale_factor(primary_header or {}) or fallback_scale or 1.0
            primary_nodata = _nodata(primary_header or {})
            if primary_nodata is None:
                primary_nodata = fallback_nodata
            reference_scale = _scale_factor(reference_header) or primary_scale
            reference_nodata = _nodata(reference_header)
            if reference_nodata is None:
                reference_nodata = primary_nodata
            before_preview = _unit_reflectance(
                _preview(reference_cube, max_pixels),
                scale_factor=reference_scale,
                nodata=reference_nodata,
            )
            after_preview = _unit_reflectance(
                _preview(primary_cube, max_pixels),
                scale_factor=primary_scale,
                nodata=primary_nodata,
            )
            valid = np.isfinite(before_preview) & np.isfinite(after_preview)
            difference = np.where(valid, after_preview - before_preview, np.nan)
            finite_difference = difference[np.isfinite(difference)]
            correction_metrics = residual_metrics(
                before_preview[valid], after_preview[valid]
            )
            correction_metrics["absolute_difference_q95"] = (
                float(np.quantile(np.abs(finite_difference), 0.95))
                if finite_difference.size
                else None
            )
            correction_metrics["absolute_difference_q99"] = (
                float(np.quantile(np.abs(finite_difference), 0.99))
                if finite_difference.size
                else None
            )
            metrics["paired_change"] = correction_metrics
            checks.append(
                classify_high_bad(
                    "absolute_correction_q99",
                    correction_metrics["absolute_difference_q99"],
                    warn=thresholds.correction_abs_q99_warn,
                    fail=thresholds.correction_abs_q99_fail,
                    units="reflectance",
                    interpretation="Extreme correction magnitude can signal overcorrection or invalid support.",
                )
            )
            nodata = primary_nodata
            seam_before = _representative_seams(
                reference_cube,
                chunk_shape=chunk_shape,
                mode=mode,
                nodata=nodata,
            )
            seam_after = _representative_seams(
                primary_cube,
                chunk_shape=chunk_shape,
                mode=mode,
                nodata=nodata,
            )
            metrics["seam_before"] = seam_before or {}
            metrics["seam_after"] = seam_after or {}
            if seam_after:
                checks.append(
                    classify_high_bad(
                        "maximum_chunk_seam_score_after",
                        seam_after["max_seam_score"],
                        warn=thresholds.seam_score_warn,
                        fail=thresholds.seam_score_fail,
                        units="ratio",
                        interpretation="Chunk-boundary gradients should resemble ordinary neighboring-pixel gradients.",
                    )
                )
            else:
                checks.append(
                    classify_high_bad(
                        "maximum_chunk_seam_score_after",
                        None,
                        warn=thresholds.seam_score_warn,
                        fail=thresholds.seam_score_fail,
                        units="ratio",
                        interpretation="Chunk-boundary gradients should resemble ordinary neighboring-pixel gradients.",
                        reason="This run has no internal application boundary or the chunk layout was unavailable.",
                    )
                )
                unavailable.append(
                    {
                        "diagnostic": "chunk_seam_score",
                        "reason": "No internal application boundary was present or recorded for this stage.",
                    }
                )
            render_correction_overview(
                before_preview,
                after_preview,
                wavelengths,
                seam_before,
                seam_after,
                paths.overview_png,
                location_label=location_label,
                spatial_context=spatial_context,
            )
            if paths.overview_png.name not in plot_paths:
                plot_paths.append(paths.overview_png.name)
            if stage_id == "brdf_topographic_correction":
                unavailable.extend(
                    [
                        {
                            "diagnostic": "separate_topographic_and_brdf_attribution",
                            "reason": "The canonical stage persists only the combined corrected cube, not a topographic-only intermediate.",
                        },
                        {
                            "diagnostic": "illumination_and_geometry_residual_models",
                            "reason": "Standard QA does not reopen the source HDF5 ancillary rasters; enable a future ancillary-aware deep run.",
                        },
                        {
                            "diagnostic": "chunk_invariance_rerun",
                            "reason": "This report inspects the produced cube but does not rerun correction under an alternate chunk configuration.",
                        },
                    ]
                )

    if stage_id == "correction_parameters":
        json_outputs = [
            path for path in output_paths if path.suffix == ".json" and path.exists()
        ]
        if json_outputs:
            correction_path = next(
                (path for path in json_outputs if "brdfandtopo_corrected" in path.name),
                json_outputs[0],
            )
            model_path = next(
                (path for path in json_outputs if "brdf_model" in path.name),
                None,
            )
            payload = json.loads(correction_path.read_text(encoding="utf-8"))
            model = (
                json.loads(model_path.read_text(encoding="utf-8"))
                if model_path is not None
                else {}
            )
            geometry = payload.get("geometry", {})
            metrics["geometry_summary"] = geometry
            geometry_review = _geometry_range_review(geometry)
            metrics["geometry_physical_range_review"] = geometry_review
            metrics["brdf_model_summary"] = {
                key: summary
                for key in ("iso", "vol", "geo")
                if (summary := _array_summary(model.get(key))) is not None
            }
            required = {
                "solar_zn",
                "solar_az",
                "sensor_zn",
                "sensor_az",
                "slope",
                "aspect",
            }
            coverage = float(len(required.intersection(geometry)) / len(required))
            metrics["geometry_field_fraction"] = coverage
            checks.append(
                classify_low_bad(
                    "geometry_field_fraction",
                    coverage,
                    warn=0.99,
                    fail=0.5,
                    units="fraction",
                    interpretation="Correction QA requires the physical geometry fields used by the model.",
                )
            )
            fields_requiring_review = geometry_review["fields_requiring_review"]
            checks.append(
                QACheck(
                    check_id="persisted_geometry_physical_range_review",
                    status=(
                        QAStatus.WARN if fields_requiring_review else QAStatus.PASS
                    ),
                    value=fields_requiring_review,
                    units="fields",
                    provisional=False,
                    interpretation=(
                        "Persisted geometry min/mean/max values should lie within "
                        "their physical radian ranges."
                    ),
                    reason=(
                        "Out-of-range summaries are retained and shown; they may "
                        "indicate source no-data contamination and are not masked by QA."
                        if fields_requiring_review
                        else None
                    ),
                )
            )
            try:
                parameter_wavelengths = np.asarray(
                    payload.get("wavelength_nm", []), dtype=np.float64
                ).reshape(-1)
            except (TypeError, ValueError):
                parameter_wavelengths = np.array([], dtype=np.float64)
            render_correction_parameters(
                model,
                geometry,
                parameter_wavelengths,
                paths.overview_png,
                location_label=location_label,
            )
            plot_paths.append(paths.overview_png.name)
        else:
            render_artifact_inventory(
                output_records,
                paths.overview_png,
                title=_STAGE_NAMES[stage_id],
                location_label=location_label,
            )
            plot_paths.append(paths.overview_png.name)

    if stage_id == "spectral_convolution":
        unavailable.append(
            {
                "diagnostic": "per_band_srf_valid_coverage",
                "reason": "The stage output contract does not currently persist the sampled SRF weights used for each output band.",
            }
        )
        brightness = _brightness_diagnostics(
            output_paths,
            max_pixels=100_000 if mode == "deep" else 25_000,
        )
        serializable_brightness = []
        for index, diagnostic in enumerate(brightness):
            before_preview = diagnostic.pop("before_preview", None)
            after_preview = diagnostic.pop("after_preview", None)
            serializable_brightness.append(diagnostic)
            gain_error = diagnostic.get("maximum_absolute_gain_error")
            diagnostic_error = diagnostic.get("error")
            if diagnostic_error:
                brightness_status = QAStatus.FAIL
            elif gain_error is None:
                brightness_status = QAStatus.NOT_EVALUATED
            elif gain_error <= 1e-4:
                brightness_status = QAStatus.PASS
            else:
                brightness_status = QAStatus.FAIL
            checks.append(
                QACheck(
                    check_id=(
                        "brightness_coefficient_application:"
                        f"{diagnostic.get('product', index + 1)}"
                    ),
                    status=brightness_status,
                    value=gain_error,
                    units="absolute gain",
                    fail_threshold=1e-4,
                    provisional=False,
                    interpretation=(
                        "The fitted before/after gain must reproduce the configured "
                        "brightness coefficient in the persisted product."
                    ),
                    reason=(
                        str(diagnostic_error)
                        if diagnostic_error
                        else (
                            "The paired product has no valid varying reflectance "
                            "values from which to estimate a gain."
                            if gain_error is None
                            else None
                        )
                    ),
                )
            )
            if before_preview is not None and after_preview is not None:
                brightness_path = (
                    paths.brightness_png
                    if index == 0
                    else paths.directory / f"brightness_{index + 1:02d}.png"
                )
                render_brightness_diagnostics(
                    before_preview,
                    after_preview,
                    diagnostic,
                    brightness_path,
                    product_label=str(diagnostic["product"]),
                    location_label=location_label,
                )
                plot_paths.append(brightness_path.name)
        metrics["brightness_correction"] = {
            "audit_mode": "persisted_before_after_products_no_refit_or_modification",
            "products": serializable_brightness,
        }
        if not brightness:
            unavailable.append(
                {
                    "diagnostic": "brightness_correction_application",
                    "reason": "No matching Landsat undarkened/final ENVI pair was found.",
                }
            )
    if stage_id == "analysis_tables":
        metrics["parquet"] = _parquet_metrics(output_paths)
        tables = metrics["parquet"].get("tables", [])
        readable = [table for table in tables if "rows" in table]
        checks.append(
            QACheck(
                check_id="readable_parquet_outputs",
                status=QAStatus.PASS if readable else QAStatus.FAIL,
                value=len(readable),
                provisional=False,
                interpretation="At least one declared Parquet output must be readable.",
            )
        )
        render_parquet_overview(
            metrics["parquet"],
            paths.overview_png,
            location_label=location_label,
        )
        plot_paths.append(paths.overview_png.name)

    status = overall_status(checks)
    problems = [
        check.check_id
        for check in checks
        if check.status in {QAStatus.WARN, QAStatus.FAIL}
    ]
    interpretation = []
    if status == QAStatus.PASS:
        interpretation.append("All evaluated checks passed their current thresholds.")
    elif status == QAStatus.WARN:
        interpretation.append(f"Review provisional warnings: {', '.join(problems)}.")
    elif status == QAStatus.FAIL:
        interpretation.append(
            f"One or more required or scientific checks failed: {', '.join(problems)}."
        )
    else:
        interpretation.append("No scientific check could be evaluated for this stage.")
    if unavailable:
        interpretation.append(
            f"{len(unavailable)} diagnostic(s) were explicitly not evaluated; see reasons below."
        )

    report = StageQAReport(
        stage_id=stage_id,
        stage_name=_STAGE_NAMES.get(stage_id, stage_id.replace("_", " ").title()),
        mode=mode,
        status=status,
        inputs=input_records,
        outputs=output_records,
        parameters=parameters,
        sample=sample,
        metrics=metrics,
        checks=checks,
        warnings=problems,
        plots=plot_paths,
        interpretation=interpretation,
        provenance={
            "package_version": _package_version(),
            "git_sha": _git_sha(),
            "context_fingerprint": context_fingerprint,
            "thresholds": thresholds.to_dict(),
            "deterministic": True,
        },
        unavailable_diagnostics=unavailable,
    )
    report.write_json(paths.json)
    render_stage_html(report, paths.html)
    return paths.html, report.to_dict()


__all__ = ["emit_stage_qa"]
