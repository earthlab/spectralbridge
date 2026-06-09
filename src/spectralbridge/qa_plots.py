"""Utilities for rendering QA panels with paired metrics JSON."""
from __future__ import annotations

import datetime as _dt
import hashlib
import logging
import math
import subprocess
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

try:
    from scipy import ndimage
except ImportError:
    ndimage = None  # type: ignore

try:
    import pandas as pd
except ImportError:
    pd = None  # type: ignore

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from .brightness_config import load_brightness_coefficients
from .envi import hdr_to_dict, read_envi_cube
from .header_utils import wavelengths_from_hdr
from .qa_metrics import (
    ConvolutionReport,
    CorrectionReport,
    HeaderReport,
    MaskReport,
    Provenance,
    QAMetrics,
    write_json,
)

logger = logging.getLogger(__name__)

_DEFAULT_RGB_TARGETS = (660.0, 560.0, 490.0)
_EXPECTED_HEADER_KEYS = ["wavelength", "fwhm", "band names"]
_NEGATIVE_WARN_THRESHOLD = 1.0
_OVERBRIGHT_WARN_THRESHOLD = 1.0
_DELTA_WARN_THRESHOLD = 0.05
_DRONE_OBSERVED_CHANGE_EPS = 1e-6
_DRONE_CHANGE_THRESHOLD = 0.01
# Drone QA needs a denser spectral sample than the generic flightline panel so
# site-to-site variance remains visible, but we still keep it bounded to avoid
# turning the sampled spectral diagnostics into an unbounded memory sink.
_DRONE_QA_MAX_SAMPLES = 250_000
_DRONE_CORRECTION_CHANGE_THRESHOLD = _DRONE_CHANGE_THRESHOLD
_DRONE_QA_TRACE_RNG_SEED = 13
_DRONE_QA_DISPLAY_UPPER_BOUND = 5_000.0
_DRONE_QA_MIN_VALID_BAND_FRACTION = 0.25
_DRONE_NOOP_MEAN_ABS_DIFF_THRESHOLD = 1e-3
_DRONE_NOOP_MEDIAN_ABS_DIFF_THRESHOLD = 1e-4
_DRONE_NOOP_CHANGED_PIXEL_PCT_THRESHOLD = 1.0
_DRONE_NOOP_FRACTION_ABOVE_THRESHOLD_PCT = 0.1
_DRONE_OUTLIER_DOMINATED_MEDIAN_THRESHOLD = 0.005
_DRONE_OUTLIER_DOMINATED_P95_THRESHOLD = 0.05
_DRONE_SUPPORT_COLLAPSE_BAND_PCT = 60.0
_DRONE_SUPPORT_COLLAPSE_GT10_BAND_PCT = 40.0


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _discover_primary_cube(flightline_dir: Path) -> tuple[Path, Path]:
    """
    Discover the raw and corrected ENVI cubes for a flightline.
    
    Handles naming mismatches between raw files (which may use legacy T-separator format)
    and corrected files (which use canonical flight_id format).
    """
    raw_candidates = sorted(
        p
        for p in flightline_dir.glob("*_envi.img")
        if "corrected" not in p.stem and "qa" not in p.stem
    )
    if not raw_candidates:
        raise FileNotFoundError(f"No ENVI cube found in {flightline_dir}")
    raw_path = raw_candidates[0]
    prefix = raw_path.stem.rsplit("_envi", 1)[0]
    
    # Strategy 1: Try exact prefix match first (works if naming is consistent)
    corrected = flightline_dir / f"{prefix}_brdfandtopo_corrected_envi.img"
    if corrected.exists():
        return raw_path, corrected
    
    # Strategy 2: Try to construct canonical flight_id from parsed raw file
    # Raw file might have legacy format: NEON_D13_NIWO_DP1_20200720T163210_20200720_163210_reflectance_envi.img
    # Corrected file uses canonical format: NEON_D13_NIWO_DP1_20200720_163210_reflectance_brdfandtopo_corrected_envi.img
    try:
        from .file_types import NEONReflectanceENVIFile
        
        # Try parsing the raw ENVI filename
        envi_file = NEONReflectanceENVIFile.from_filename(raw_path)
        
        # Extract components for canonical flight_id format
        # Format: NEON_{domain}_{site}_DP1_{date}_{time}_reflectance
        domain = getattr(envi_file, "domain", None)
        site = getattr(envi_file, "site", None)
        date = getattr(envi_file, "date", None)
        time = getattr(envi_file, "time", None)
        
        if domain and site and date and time:
            # Construct canonical flight_id (remove T-separator and duplicate date/time)
            canonical_flight_id = f"NEON_{domain}_{site}_DP1_{date}_{time}_reflectance"
            canonical_corrected = flightline_dir / f"{canonical_flight_id}_brdfandtopo_corrected_envi.img"
            if canonical_corrected.exists():
                return raw_path, canonical_corrected
    except (ValueError, AttributeError):
        # If parsing fails, fall through to Strategy 3
        pass
    except Exception:
        # Catch any other unexpected errors and log them, then fall through to Strategy 3
        pass
    
    # Strategy 3: Fallback - glob search for any corrected file
    corrected_candidates = sorted(
        p
        for p in flightline_dir.glob("*_brdfandtopo_corrected_envi.img")
        if p.is_file()
    )
    if corrected_candidates:
        return raw_path, corrected_candidates[0]
    
    # If all strategies fail, raise error with helpful message
    raise FileNotFoundError(
        f"Missing corrected cube: Could not find corrected ENVI file for raw file {raw_path.name}.\n"
        f"Tried:\n"
        f"  1. {corrected.name} (Strategy 1: exact prefix match)\n"
        f"  2. Canonical format based on flight_id (Strategy 2: parsed from raw file)\n"
        f"  3. Any *_brdfandtopo_corrected_envi.img in {flightline_dir} (Strategy 3: glob search)\n"
        f"Raw file may use legacy format (T-separator) while corrected uses canonical format.\n"
        f"Found {len(corrected_candidates)} corrected file(s) but none matched."
    )


def _list_envi_products(flightline_dir: Path, prefix: str) -> list[Path]:
    """Return all ENVI .img products for this flightline (for page 1 overview).

    Includes the raw ENVI, corrected ENVI, and any convolved ENVI products,
    but excludes QA images and non-ENVI artifacts.
    """

    products: list[Path] = []
    for img_path in sorted(flightline_dir.glob(f"{prefix}*_envi.img")):
        if "qa" in img_path.stem:
            continue
        products.append(img_path)
    if not products:
        for img_path in sorted(flightline_dir.glob("*_envi.img")):
            if "qa" in img_path.stem:
                continue
            products.append(img_path)
    return products


def _flightline_prefix(raw_path: Path) -> str:
    stem = raw_path.stem
    return stem.rsplit("_envi", 1)[0]


def _rgb_targets_from_arg(rgb_bands: str | None) -> tuple[float, float, float]:
    if not rgb_bands:
        return _DEFAULT_RGB_TARGETS
    tokens = [token.strip() for token in rgb_bands.split(",") if token.strip()]
    if len(tokens) != 3:
        return _DEFAULT_RGB_TARGETS
    mapping = {"R": 660.0, "G": 560.0, "B": 490.0}
    resolved: list[float] = []
    for token in tokens:
        upper = token.upper()
        if upper in mapping:
            resolved.append(mapping[upper])
            continue
        try:
            resolved.append(float(token))
        except ValueError:
            return _DEFAULT_RGB_TARGETS
    return tuple(resolved)  # type: ignore[return-value]


def _deterministic_sample(
    cube: np.ndarray,
    mask: np.ndarray,
    n_sample: int,
) -> tuple[np.ndarray, np.ndarray]:
    bands, rows, cols = cube.shape
    total_pixels = rows * cols
    if total_pixels <= n_sample:
        return cube.reshape(bands, -1), mask.reshape(bands, -1)
    step = max(1, int(math.sqrt(total_pixels / n_sample)))
    ys = np.arange(0, rows, step)
    xs = np.arange(0, cols, step)
    sampled = cube[:, ys][:, :, xs]
    sampled_mask = mask[:, ys][:, :, xs]
    flat = sampled.reshape(bands, -1)
    flat_mask = sampled_mask.reshape(bands, -1)
    if flat.shape[1] > n_sample:
        idx = np.linspace(0, flat.shape[1] - 1, num=n_sample, dtype=int)
        flat = flat[:, idx]
        flat_mask = flat_mask[:, idx]
    return flat, flat_mask


def _deterministic_drone_valid_sample(
    cube: np.ndarray,
    mask: np.ndarray,
    n_sample: int,
    *,
    min_valid_band_fraction: float = _DRONE_QA_MIN_VALID_BAND_FRACTION,
    rng_seed: int = _DRONE_QA_TRACE_RNG_SEED,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    """Sample drone QA spectra from eligible valid pixels rather than the full grid.

    Drone orthomosaics can contain large nodata skirts. Filtering to pixels with
    at least a modest fraction of valid bands preserves the same downstream
    sampled-spectrum shape while preventing nodata-heavy edges from consuming
    most of the sampling budget.
    """

    bands, rows, cols = cube.shape
    total_pixels = int(rows * cols)
    if total_pixels == 0:
        empty = cube.reshape(bands, -1)
        return empty, mask.reshape(bands, -1), {
            "total_pixels": 0,
            "eligible_pixels_for_sampling": 0,
            "eligible_pixel_pct": 0.0,
            "sampled_pixels": 0,
            "sampled_vs_eligible_pct": 0.0,
            "min_valid_band_fraction_for_sampling": float(min_valid_band_fraction),
        }

    pixel_valid_fraction = np.mean(mask, axis=0)
    pixel_valid = pixel_valid_fraction >= float(min_valid_band_fraction)
    eligible_coords = np.argwhere(pixel_valid)
    if eligible_coords.size == 0:
        eligible_coords = np.argwhere(np.any(mask, axis=0))

    eligible_pixels = int(eligible_coords.shape[0])
    if eligible_pixels == 0:
        return np.empty((bands, 0), dtype=cube.dtype), np.empty((bands, 0), dtype=bool), {
            "total_pixels": total_pixels,
            "eligible_pixels_for_sampling": 0,
            "eligible_pixel_pct": 0.0,
            "sampled_pixels": 0,
            "sampled_vs_eligible_pct": 0.0,
            "min_valid_band_fraction_for_sampling": float(min_valid_band_fraction),
        }

    sample_count = min(max(1, int(n_sample)), eligible_pixels)
    if eligible_pixels <= sample_count:
        selected = eligible_coords
    else:
        rng = np.random.default_rng(int(rng_seed))
        take = np.sort(rng.choice(eligible_pixels, size=sample_count, replace=False))
        selected = eligible_coords[take]

    row_idx = selected[:, 0]
    col_idx = selected[:, 1]
    sampled = cube[:, row_idx, col_idx]
    sampled_mask = mask[:, row_idx, col_idx]
    sampled_pixels = int(sampled.shape[1])
    diagnostics = {
        "total_pixels": total_pixels,
        "eligible_pixels_for_sampling": eligible_pixels,
        "eligible_pixel_pct": float((eligible_pixels / total_pixels) * 100.0),
        "sampled_pixels": sampled_pixels,
        "sampled_vs_eligible_pct": float((sampled_pixels / eligible_pixels) * 100.0),
        "min_valid_band_fraction_for_sampling": float(min_valid_band_fraction),
    }
    return sampled, sampled_mask, diagnostics


def _percentile_stretch(arr: np.ndarray, lo: float = 2.0, hi: float = 98.0) -> np.ndarray:
    lo_val = np.nanpercentile(arr, lo)
    hi_val = np.nanpercentile(arr, hi)
    if not np.isfinite(lo_val) or not np.isfinite(hi_val) or hi_val == lo_val:
        return np.zeros_like(arr)
    scaled = np.clip((arr - lo_val) / (hi_val - lo_val), 0.0, 1.0)
    return scaled


def _rgb_preview(
    cube: np.ndarray,
    wavelengths: np.ndarray,
    rgb_targets: Sequence[float],
) -> tuple[np.ndarray, tuple[int, int, int]]:
    bands, rows, cols = cube.shape
    if wavelengths.size:
        # Filter out NaN values before using nanargmin
        finite_mask = np.isfinite(wavelengths)
        if not np.any(finite_mask):
            # All wavelengths are NaN - fall back to first few bands
            indices = [0, min(1, bands - 1), min(2, bands - 1)]
        else:
            # Use only finite wavelengths for band selection
            finite_wavelengths = wavelengths[finite_mask]
            finite_indices = np.where(finite_mask)[0]
            indices = []
            for target in rgb_targets:
                try:
                    idx = int(np.nanargmin(np.abs(finite_wavelengths - target)))
                    indices.append(finite_indices[idx])
                except ValueError:
                    # Fallback if nanargmin fails
                    indices.append(0)
    else:
        indices = [0, min(1, bands - 1), min(2, bands - 1)]
    rgb = np.stack([_percentile_stretch(cube[idx]) for idx in indices], axis=-1)
    return rgb, (indices[0], indices[1], indices[2])


def _header_report(header: dict, wavelengths: np.ndarray, source: str) -> HeaderReport:
    keys_present = [key for key in _EXPECTED_HEADER_KEYS if key in header]
    keys_missing = [key for key in _EXPECTED_HEADER_KEYS if key not in keys_present]
    unit = header.get("wavelength units") or header.get("wavelength_units")
    unit = unit if isinstance(unit, str) else None
    finite = wavelengths[np.isfinite(wavelengths)]
    first_nm = float(finite[0]) if finite.size else None
    last_nm = float(finite[-1]) if finite.size else None
    monotonic = bool(np.all(np.diff(finite) > 0)) if finite.size > 1 else None
    n_bands = int(header.get("bands") or wavelengths.size or 0)
    return HeaderReport(
        keys_present=keys_present,
        keys_missing=keys_missing,
        wavelength_unit=unit,
        n_bands=n_bands,
        n_wavelengths_finite=int(finite.size),
        first_nm=first_nm,
        last_nm=last_nm,
        wavelengths_monotonic=monotonic,
        wavelength_source=source,
    )


def _correction_report(
    raw_sample: np.ndarray,
    corr_sample: np.ndarray,
    sample_mask: np.ndarray,
) -> CorrectionReport:
    # Exclude -9999 (no-data) values from delta calculation
    # -9999 values can cause spurious large deltas (e.g., -9999 - 0.5 = -9999.5, or 0.5 - (-9999) = 9999.5)
    # Use a more lenient threshold to catch values close to -9999
    no_data_threshold = -9990.0  # Anything <= -9990 is considered no-data
    
    # Mask out pixels where either raw or corrected is no-data
    raw_is_nodata = raw_sample <= no_data_threshold
    corr_is_nodata = corr_sample <= no_data_threshold
    either_is_nodata = raw_is_nodata | corr_is_nodata
    
    # Combined mask: valid pixels AND not no-data
    combined_mask = sample_mask & ~either_is_nodata
    
    # Calculate difference only for valid, non-no-data pixels
    diff = np.where(combined_mask, corr_sample - raw_sample, np.nan)
    
    # CRITICAL: Exclude deltas that are suspiciously large (likely -9999 contamination)
    # If absolute delta is > 1000, it's almost certainly from a -9999 value
    # This catches cases like: -9999 - 76 = -10075 or 76 - (-9999) = 10075
    # Use a threshold of 1000 to be safe (reflectance deltas should be < 1 typically)
    suspicious_deltas = np.abs(diff) > 1000.0
    n_suspicious = np.sum(suspicious_deltas)
    if n_suspicious > 0:
        print(f"[QA] ⚠️  Excluding {n_suspicious:,} suspicious deltas (|delta| > 1000) likely from -9999 contamination")
    diff = np.where(suspicious_deltas, np.nan, diff)
    
    delta_median = np.nanmedian(diff, axis=1)
    q10 = np.nanpercentile(diff, 10, axis=1)
    q25 = np.nanpercentile(diff, 25, axis=1)
    q75 = np.nanpercentile(diff, 75, axis=1)
    q90 = np.nanpercentile(diff, 90, axis=1)
    delta_abs_median = np.nanmedian(np.abs(diff), axis=1)
    delta_iqr = q75 - q25
    
    # Count how many bands had -9999 contamination
    nodata_bands = np.sum(either_is_nodata, axis=1)
    if np.any(nodata_bands > 0):
        max_contaminated = np.max(nodata_bands)
        print(f"[QA] ⚠️  Excluded -9999 values from delta calculation (max {max_contaminated} pixels per band)")
    
    order = np.argsort(np.abs(delta_median))[::-1]
    top = order[:3].tolist()
    return CorrectionReport(
        delta_median=delta_median.astype(float).tolist(),
        delta_iqr=delta_iqr.astype(float).tolist(),
        delta_q10=q10.astype(float).tolist(),
        delta_q25=q25.astype(float).tolist(),
        delta_q75=q75.astype(float).tolist(),
        delta_q90=q90.astype(float).tolist(),
        delta_abs_median=delta_abs_median.astype(float).tolist(),
        largest_delta_indices=[int(idx) for idx in top],
    )


def _spectral_angle(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.nansum(a * b, axis=0)
    norm_a = np.sqrt(np.nansum(a * a, axis=0))
    norm_b = np.sqrt(np.nansum(b * b, axis=0))
    denom = np.maximum(norm_a * norm_b, 1e-6)
    cos_theta = np.clip(dot / denom, -1.0, 1.0)
    angles = np.arccos(cos_theta)
    return float(np.nanmean(angles))


def _load_filtered_parquet_stats(flightline_dir: Path, prefix: str) -> dict | None:
    """Load statistics from filtered merged parquet file if available."""
    if pd is None:
        return None
    
    # Check for both regular and polygon mode merged parquet files
    merged_parquet = flightline_dir / f"{prefix}_merged_pixel_extraction.parquet"
    if not merged_parquet.exists():
        # Try polygon mode merged file
        merged_parquet = flightline_dir / f"{prefix}_polygons_merged_pixel_extraction.parquet"
        if not merged_parquet.exists():
            return None
    
    try:
        # Read a sample to get statistics
        df = pd.read_parquet(merged_parquet)
        
        # Identify spectral columns (excluding raw_* and metadata)
        import re
        spectral_cols = [col for col in df.columns 
                        if re.search(r'_wl\d+nm|^wl\d+nm', col, re.IGNORECASE) 
                        and not col.lower().startswith('raw_')
                        and col.lower() not in ['pixel_id', 'row', 'col', 'x', 'y', 'lon', 'lat']]
        
        if not spectral_cols:
            return None
        
        # Convert to numeric
        spectral_df = df[spectral_cols].apply(pd.to_numeric, errors='coerce')
        
        # Calculate statistics
        # First identify no-data values (close to -9999)
        no_data_mask = (np.abs(spectral_df - (-9999.0)) < 0.01) & spectral_df.notna()
        # Valid cells exclude no-data
        valid_mask = spectral_df.notna() & ~no_data_mask
        
        # Calculate statistics on VALID cells only (exclude no-data)
        negative_mask = (spectral_df < 0) & valid_mask
        overbright_mask = (spectral_df > 1.2) & valid_mask
        
        total_cells = spectral_df.notna().sum().sum()  # All non-NaN cells (including no-data)
        no_data_cells = no_data_mask.sum().sum()
        valid_cells = valid_mask.sum().sum()  # Non-NaN, non-no-data cells
        negative_cells = negative_mask.sum().sum()  # Only on valid cells
        overbright_cells = overbright_mask.sum().sum()  # Only on valid cells
        
        return {
            'n_rows': len(df),
            'n_spectral_cols': len(spectral_cols),
            'negatives_pct': (negative_cells / valid_cells * 100) if valid_cells > 0 else 0.0,
            'overbright_pct': (overbright_cells / valid_cells * 100) if valid_cells > 0 else 0.0,
            'no_data_pct': (no_data_cells / total_cells * 100) if total_cells > 0 else 0.0,
            'valid_pct': (valid_cells / total_cells * 100) if total_cells > 0 else 0.0,
        }
    except Exception as e:
        logger.warning(f"Failed to load filtered parquet stats: {e}")
        return None


def _safe_extract_geometry_value(value) -> float | None:
    """Safely extract geometry value, handling dict, tuple, or float."""
    if isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, dict):
        return value.get("mean") if "mean" in value else None
    elif isinstance(value, (list, tuple)):
        # If it's a tuple/list, try to get mean or first element
        if len(value) > 0:
            try:
                return float(value[0])
            except (ValueError, TypeError):
                return None
    return None


def _build_brightness_summary_table(
    brightness_map: dict[str, dict[int, float]]
) -> dict[str, list[dict[str, float | str]]]:
    summary: dict[str, list[dict[str, float | str]]] = {}

    if not brightness_map:
        default_coeffs = load_brightness_coefficients()
        summary["landsat_to_micasense"] = [
            {
                "band": band_idx,
                "config_coeff_pct": coeff,
                "applied_coeff_pct": coeff,
                "brightness_coeff_pct": coeff,
                "brightness_coeff_label": f"{coeff:+.3f}%",
            }
            for band_idx, coeff in sorted(default_coeffs.items())
        ]
        return summary

    for system_pair, applied in brightness_map.items():
        config_coeffs = load_brightness_coefficients(system_pair)
        rows: list[dict[str, float | str]] = []
        for band_idx, config_value in sorted(config_coeffs.items()):
            applied_value = applied.get(band_idx, config_value)
            rows.append(
                {
                    "band": band_idx,
                    "config_coeff_pct": config_value,
                    "applied_coeff_pct": applied_value,
                    "brightness_coeff_pct": applied_value,
                    "brightness_coeff_label": f"{applied_value:+.3f}%",
                }
            )
        summary[system_pair] = rows

    return summary


def _convolution_reports(
    base_dir: Path,
    prefix: str,
    corr_cube: np.ndarray,
    sample_mask: np.ndarray,
) -> tuple[
    list[ConvolutionReport],
    dict[str, tuple[np.ndarray, np.ndarray]],
    dict[str, dict[int, float]],
]:
    reports: list[ConvolutionReport] = []
    scatter_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    brightness_map: dict[str, dict[int, float]] = {}
    patterns = [
        f"{prefix}_*_convolved_envi.img",
        f"{prefix}_resampled_*_envi.img",
        f"{prefix}_resampled_*_envi_masked.img",
        f"{prefix}_*landsat*_envi.img",  # Add Landsat patterns
        f"{prefix}_*micasense*_envi.img",  # Add MicaSense patterns
        f"{prefix}_*etm*_envi.img",  # Add ETM+ patterns
        f"{prefix}_*oli*_envi.img",  # Add OLI patterns
        f"{prefix}_*tm*_envi.img",  # Add TM patterns
    ]
    candidates: set[Path] = set()
    for pattern in patterns:
        for match in base_dir.rglob(pattern):
            # Exclude raw and corrected ENVI files, but include convolved/resampled
            stem = match.stem.lower()
            if ("corrected" not in stem and 
                "brdfandtopo" not in stem and
                stem != f"{prefix.lower()}_envi" and
                ("convolved" in stem or "resampled" in stem or 
                 "landsat" in stem or "micasense" in stem or 
                 "etm" in stem or "oli" in stem or "tm" in stem)):
                candidates.add(match)

    for img_path in sorted(candidates):
        sensor = img_path.stem.replace(f"{prefix}_", "").replace("_convolved_envi", "")
        hdr = hdr_to_dict(img_path.with_suffix(".hdr"))
        cube = read_envi_cube(img_path, hdr)
        if cube.shape != corr_cube.shape:
            continue
        brightness_entry = hdr.get("brightness_coefficients")
        if isinstance(brightness_entry, str):
            try:
                parsed = json.loads(brightness_entry)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                for system_pair, coeffs in parsed.items():
                    if not isinstance(coeffs, dict):
                        continue
                    dest = brightness_map.setdefault(system_pair, {})
                    for key, value in coeffs.items():
                        try:
                            dest[int(key)] = float(value)
                        except (TypeError, ValueError):
                            continue
        flat_cube = cube.reshape(cube.shape[0], -1)
        flat_corr = corr_cube.reshape(corr_cube.shape[0], -1)
        rmse = np.sqrt(np.nanmean((flat_corr - flat_cube) ** 2, axis=1))
        sam = _spectral_angle(flat_corr, flat_cube)
        reports.append(
            ConvolutionReport(sensor=sensor, rmse=rmse.astype(float).tolist(), sam=sam)
        )
        valid = sample_mask.any(axis=0)
        if not np.any(valid):
            continue
        corrected_vals = flat_corr[:, valid].flatten()
        convolved_vals = flat_cube[:, valid].flatten()
        scatter_data[sensor] = (corrected_vals, convolved_vals)
    return reports, scatter_data, brightness_map


def _scatter_from_merged_parquet(
    flightline_dir: Path,
    prefix: str,
    *,
    max_points: int = 50_000,
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """
    Fallback for the "Convolved vs corrected" scatter plot when no convolved ENVI cubes
    are found on disk.

    We build scatter pairs from the merged parquet by matching sensor band columns
    (e.g., olioli_*_wl####nm, tmtm_*_wl####nm, micasense_*_wl####nm) to the nearest
    corrected hyperspectral column (corr_*_wl####nm).
    """
    if pd is None:
        return {}

    # Check for both regular and polygon mode merged parquet files
    merged_parquet = flightline_dir / f"{prefix}_merged_pixel_extraction.parquet"
    if not merged_parquet.exists():
        merged_parquet = flightline_dir / f"{prefix}_polygons_merged_pixel_extraction.parquet"
        if not merged_parquet.exists():
            return {}

    try:
        df = pd.read_parquet(merged_parquet)
    except Exception:
        return {}

    import re

    wl_re = re.compile(r"_wl(\d+)nm", re.IGNORECASE)

    def _wl_nm(col: str) -> int | None:
        m = wl_re.search(col)
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None

    # corrected hyperspectral columns
    corr_cols = [
        c
        for c in df.columns
        if c.lower().startswith("corr_") and wl_re.search(c) is not None
    ]
    corr_by_wl: dict[int, str] = {}
    for c in corr_cols:
        wl = _wl_nm(c)
        if wl is not None and wl not in corr_by_wl:
            corr_by_wl[wl] = c
    if not corr_by_wl:
        return {}

    corr_wls = np.array(sorted(corr_by_wl.keys()), dtype=int)

    # candidate "convolved/resampled sensor" columns from parquet
    sensor_cols = [
        c
        for c in df.columns
        if (wl_re.search(c) is not None)
        and (not c.lower().startswith("raw_"))
        and (not c.lower().startswith("corr_"))
    ]
    if not sensor_cols:
        return {}

    def _sensor_name(col: str) -> str:
        # Common pattern: <sensor>_b###_wl####nm or <sensor>_undarkened_b###_wl####nm
        # Fall back to prefix before first "_b".
        parts = col.split("_b", 1)
        return parts[0]

    scatter: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    rng = np.random.default_rng(0)

    for c in sensor_cols:
        sensor = _sensor_name(c)
        wl = _wl_nm(c)
        if wl is None:
            continue

        # Find nearest corrected wavelength column.
        idx = int(np.argmin(np.abs(corr_wls - wl)))
        corr_col = corr_by_wl[int(corr_wls[idx])]

        x = pd.to_numeric(df[corr_col], errors="coerce").to_numpy(dtype=float)
        y = pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=float)

        # Valid values: finite, not -9999-ish, and not negative (for plotting clarity).
        valid = (
            np.isfinite(x)
            & np.isfinite(y)
            & (np.abs(x - (-9999.0)) >= 0.01)
            & (np.abs(y - (-9999.0)) >= 0.01)
        )
        if not np.any(valid):
            continue

        xv = x[valid]
        yv = y[valid]

        # Downsample to keep plots light.
        if xv.size > max_points:
            take = rng.choice(xv.size, size=max_points, replace=False)
            xv = xv[take]
            yv = yv[take]

        if sensor in scatter:
            # Append more points for the same sensor (up to max_points total).
            prev_x, prev_y = scatter[sensor]
            remaining = max(0, max_points - prev_x.size)
            if remaining <= 0:
                continue
            if xv.size > remaining:
                take = rng.choice(xv.size, size=remaining, replace=False)
                xv = xv[take]
                yv = yv[take]
            scatter[sensor] = (np.concatenate([prev_x, xv]), np.concatenate([prev_y, yv]))
        else:
            scatter[sensor] = (xv, yv)

    return scatter


def _render_page1_envi_overview(
    pdf: PdfPages,
    flightline_dir: Path,
    prefix: str,
    rgb_targets: Sequence[float],
) -> None:
    """Page 1: one row with one panel per ENVI product, to show they exist & render."""

    envi_paths = _list_envi_products(flightline_dir, prefix)
    if not envi_paths:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.text(0.5, 0.5, "No ENVI products found", ha="center", va="center")
        ax.axis("off")
        fig.suptitle(f"ENVI overview – {prefix}")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
        return

    n = len(envi_paths)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), squeeze=False)
    fig.suptitle(f"ENVI product overview – {prefix}")
    axes_row = axes[0]

    for ax, img_path in zip(axes_row, envi_paths):
        hdr = hdr_to_dict(img_path.with_suffix(".hdr"))
        cube = read_envi_cube(img_path, hdr)
        if cube.ndim != 3:
            ax.text(0.5, 0.5, "Non-3D ENVI cube", ha="center", va="center")
            ax.axis("off")
            continue
        wavelengths, _ = wavelengths_from_hdr(hdr)
        rgb_image, _ = _rgb_preview(cube, wavelengths, rgb_targets)
        ax.imshow(np.clip(rgb_image, 0, 1))
        
        # Shorten product name for display - extract key identifier
        stem = img_path.stem
        # Remove long prefix if present
        if stem.startswith(prefix):
            short_name = stem[len(prefix):].lstrip('_')
        else:
            short_name = stem
        
        # Further shorten common suffixes
        short_name = short_name.replace('_brdfandtopo_corrected_envi', '_corrected')
        short_name = short_name.replace('_envi', '')
        short_name = short_name.replace('_convolved', '_conv')
        short_name = short_name.replace('_resampled', '_resamp')
        
        # Wrap long names
        if len(short_name) > 30:
            # Try to split at underscores
            parts = short_name.split('_')
            if len(parts) > 2:
                # Take first and last parts
                short_name = f"{parts[0]}_{parts[-1]}"
            else:
                short_name = short_name[:27] + "..."
        
        ax.set_title(short_name, fontsize=8, wrap=True)
        ax.axis("off")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _load_correction_geometry_json(
    flightline_dir: Path,
    corr_path: Path,
) -> dict | None:
    """Try to load the BRDF/topo correction JSON for extra diagnostics (optional)."""

    json_path = corr_path.with_suffix(".json")
    if not json_path.exists():
        candidates = sorted(flightline_dir.glob("*brdfandtopo_corrected_envi.json"))
        json_path = candidates[0] if candidates else None
    if not json_path or not json_path.exists():
        return None
    try:
        with json_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _render_page2_topo_brdf(
    pdf: PdfPages,
    prefix: str,
    wavelengths: np.ndarray,
    correction_report: CorrectionReport,
    raw_sample: np.ndarray,
    corr_sample: np.ndarray,
    sample_mask: np.ndarray,
    corr_path: Path,
    filtered_stats: dict | None = None,
) -> None:
    """Page 2: diagnostics specific to topo (row 1) and BRDF (row 2) corrections."""

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"Topographic + BRDF diagnostics – {prefix}")

    ax_topo_hist = axes[0, 0]
    _render_hist(ax_topo_hist, raw_sample, corr_sample, sample_mask)
    ax_topo_hist.set_title("Topographic + BRDF: pre vs post histograms")

    ax_topo_delta = axes[0, 1]
    _render_delta(ax_topo_delta, wavelengths, correction_report)
    title = "Topographic + BRDF: Δ median vs λ (before filtering)"
    if filtered_stats:
        title += "\n(Note: -9999 values excluded from delta calculation)"
    ax_topo_delta.set_title(title, fontsize=9)

    params = _load_correction_geometry_json(corr_path.parent, corr_path) or {}
    geom = params.get("geometry", {}) if isinstance(params, dict) else {}
    topo_keys = ["slope", "aspect"]
    brdf_keys = ["solar_zn", "solar_az", "sensor_zn", "sensor_az"]

    ax_brdf_geom = axes[1, 0]
    if geom:
        topo_present = [k for k in topo_keys if k in geom]
        if topo_present:
            means = []
            valid_keys = []
            for k in topo_present:
                value = _safe_extract_geometry_value(geom[k])
                if value is not None:
                    means.append(value)
                    valid_keys.append(k)
            if valid_keys and means:
                ax_brdf_geom.bar(valid_keys, means)
                ax_brdf_geom.set_title("Topographic geometry (mean)")
                ax_brdf_geom.set_ylabel("Value (radians)")
                # Set reasonable y-axis limits
                y_range = max(means) - min(means) if len(means) > 1 else abs(means[0]) if means else 1
                if y_range > 0:
                    ax_brdf_geom.set_ylim(min(means) - 0.1 * y_range, max(means) + 0.1 * y_range)
            else:
                ax_brdf_geom.text(0.5, 0.5, "No valid topo geometry values", ha="center", va="center")
        else:
            ax_brdf_geom.text(
                0.5,
                0.5,
                "No topo geometry stats in JSON",
                ha="center",
                va="center",
            )
        ax_brdf_geom.grid(True, alpha=0.2)
    else:
        ax_brdf_geom.text(
            0.5, 0.5, "No BRDF/topo JSON geometry available", ha="center", va="center"
        )
        ax_brdf_geom.grid(False)

    ax_brdf_geom2 = axes[1, 1]
    if geom:
        brdf_present = [k for k in brdf_keys if k in geom]
        if brdf_present:
            means = []
            valid_keys = []
            for k in brdf_present:
                value = _safe_extract_geometry_value(geom[k])
                if value is not None:
                    means.append(value)
                    valid_keys.append(k)
            if valid_keys and means:
                ax_brdf_geom2.bar(valid_keys, means)
                ax_brdf_geom2.set_title("BRDF geometry (mean)")
                ax_brdf_geom2.set_ylabel("Value (radians)")
                # Set reasonable y-axis limits
                y_range = max(means) - min(means) if len(means) > 1 else abs(means[0]) if means else 1
                if y_range > 0:
                    ax_brdf_geom2.set_ylim(min(means) - 0.1 * y_range, max(means) + 0.1 * y_range)
            else:
                ax_brdf_geom2.text(0.5, 0.5, "No valid BRDF geometry values", ha="center", va="center")
        else:
            ax_brdf_geom2.text(
                0.5, 0.5, "No BRDF geometry stats in JSON", ha="center", va="center"
            )
    else:
        ax_brdf_geom2.text(
            0.5, 0.5, "No BRDF/topo JSON available", ha="center", va="center"
        )
    ax_brdf_geom2.grid(True, alpha=0.2)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _render_page3_remaining(
    pdf: PdfPages,
    prefix: str,
    metrics: QAMetrics,
    scatter_data: dict[str, tuple[np.ndarray, np.ndarray]],
    filtered_stats: dict | None = None,
    flightline_dir: Path | None = None,
    wavelengths: np.ndarray | None = None,
) -> None:
    """Page 3: remaining QA diagnostics (convolution + header/mask/issue summary)."""

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"Additional QA diagnostics – {prefix}")

    ax_wavelength = axes[0, 0]
    # Use new wavelength-based plot instead of scatter plot
    if flightline_dir is not None:
        _render_wavelength_reflectance_plot(ax_wavelength, flightline_dir, prefix, wavelengths)
    else:
        # Fallback to old scatter plot if flightline_dir not provided
        _render_scatter(ax_wavelength, scatter_data)
        title = "Convolved vs corrected (all sensors)"
        if not scatter_data:
            title += "\n⚠ No convolved sensors found - check ENVI files"
        ax_wavelength.set_title(title, fontsize=9)

    ax_header = axes[0, 1]
    header = metrics.header
    lines = [
        f"Header keys present: {', '.join(header.keys_present) or 'none'}",
        f"Header keys missing: {', '.join(header.keys_missing) or 'none'}",
        f"Wavelength unit: {header.wavelength_unit or 'unknown'}",
        f"n_bands: {header.n_bands}",
        f"finite wavelengths: {header.n_wavelengths_finite}",
        f"first_nm: {header.first_nm}",
        f"last_nm: {header.last_nm}",
        f"monotonic: {header.wavelengths_monotonic}",
        f"source: {header.wavelength_source}",
    ]
    ax_header.text(0.01, 0.99, "\n".join(lines), va="top", ha="left", fontsize=9)
    ax_header.axis("off")
    ax_header.set_title("Header / wavelength integrity")

    ax_mask = axes[1, 0]
    mask = metrics.mask
    negatives_pct = metrics.negatives_pct
    overbright_pct = metrics.overbright_pct
    lines = [
        "=== ENVI Cube (Before Filtering) ===",
        f"Total pixels: {mask.n_total:,}",
        f"Valid pixels: {mask.n_valid:,}",
        f"Valid %: {mask.valid_pct:.2f}%",
        f"Negatives %: {negatives_pct:.2f}%",
        f">1.2 reflectance %: {overbright_pct:.2f}%",
    ]
    if filtered_stats:
        overbright_val = filtered_stats.get('overbright_pct', 0.0)
        if overbright_val is None:
            overbright_val = 0.0
        lines.extend([
            "",
            "=== Filtered Parquet (After Filtering) ===",
            f"Rows: {filtered_stats.get('n_rows', 0):,}",
            f"Spectral columns: {filtered_stats.get('n_spectral_cols', 0)}",
            f"Valid %: {filtered_stats.get('valid_pct', 0.0):.2f}%",
            f"Negatives %: {filtered_stats.get('negatives_pct', 0.0):.2f}%",
            f">1.2 reflectance %: {overbright_val:.2f}%",
            f"No-data %: {filtered_stats.get('no_data_pct', 0.0):.2f}%",
        ])
    else:
        lines.append("\n(Filtered parquet stats not available)")
    ax_mask.text(0.01, 0.99, "\n".join(lines), va="top", ha="left", fontsize=8, family='monospace')
    ax_mask.axis("off")
    ax_mask.set_title("Mask coverage & negatives")

    ax_issues = axes[1, 1]
    lines = []
    if metrics.issues:
        lines.extend(f"⚠ {issue}" for issue in metrics.issues)
    else:
        lines.append("No general QA issues flagged.")

    if metrics.brightness_coefficients:
        lines.append("")
        lines.append("Brightness coefficients (percent):")
        for system_pair, coeffs in metrics.brightness_coefficients.items():
            lines.append(f"{system_pair}:")
            for band_idx in sorted(coeffs):
                lines.append(f"  Band {band_idx}: {coeffs[band_idx]:.3f}%")
    else:
        lines.append("")
        lines.append("No brightness adjustment applied.")

    ax_issues.text(0.01, 0.99, "\n".join(lines), va="top", ha="left", fontsize=9)
    ax_issues.axis("off")
    ax_issues.set_title("Issues & brightness adjustments")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _render_page4_parquet_merge_quality(
    pdf: PdfPages,
    flightline_dir: Path,
    prefix: str,
) -> None:
    """Page 4: Parquet and merge quality analysis."""
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"Parquet & Merge Quality Analysis – {prefix}")
    
    # Top-left: Parquet file inventory
    ax_parquet = axes[0, 0]
    parquet_files = sorted(flightline_dir.glob("*.parquet"))
    parquet_info = []
    total_size = 0
    
    for pq in parquet_files:
        size_mb = pq.stat().st_size / (1024 * 1024)
        total_size += size_mb
        parquet_info.append(f"{pq.name[:50]}: {size_mb:.1f} MB")
    
    if parquet_info:
        text = "=== Parquet Files ===\n" + "\n".join(parquet_info[:15])  # Limit to 15 files
        if len(parquet_info) > 15:
            text += f"\n... and {len(parquet_info) - 15} more files"
        text += f"\n\nTotal: {len(parquet_files)} files, {total_size:.1f} MB"
    else:
        text = "No parquet files found"
    
    ax_parquet.text(0.01, 0.99, text, va="top", ha="left", fontsize=8, family='monospace')
    ax_parquet.axis("off")
    ax_parquet.set_title("Parquet File Inventory")
    
    # Top-right: Merge status
    ax_merge = axes[0, 1]
    # Check for both regular and polygon mode merged parquet files
    merged_parquet = flightline_dir / f"{prefix}_merged_pixel_extraction.parquet"
    if not merged_parquet.exists():
        # Try polygon mode merged file
        merged_parquet = flightline_dir / f"{prefix}_polygons_merged_pixel_extraction.parquet"
    
    if merged_parquet.exists():
        try:
            if pd is not None:
                df = pd.read_parquet(merged_parquet)
                n_rows = len(df)
                n_cols = len(df.columns)
                
                # Count expected parquet types
                original_parquets = list(flightline_dir.glob("*_envi.parquet"))
                corrected_parquets = list(flightline_dir.glob("*_corrected*.parquet"))
                resampled_parquets = [p for p in flightline_dir.glob("*.parquet") 
                                    if "merged" not in p.name and "corrected" not in p.name 
                                    and "_envi.parquet" not in p.name]
                
                lines = [
                    "=== Merge Status ===",
                    "✅ Merged file exists",
                    f"Rows: {n_rows:,}",
                    f"Columns: {n_cols}",
                    "",
                    "=== Input Files ===",
                    f"Original: {len(original_parquets)}",
                    f"Corrected: {len(corrected_parquets)}",
                    f"Resampled: {len(resampled_parquets)}",
                    f"Total inputs: {len(original_parquets) + len(corrected_parquets) + len(resampled_parquets)}",
                ]
            else:
                lines = [
                    "=== Merge Status ===",
                    "✅ Merged file exists",
                    f"Size: {merged_parquet.stat().st_size / (1024*1024):.1f} MB",
                    "(pandas not available for detailed stats)",
                ]
        except Exception as e:
            lines = [
                "=== Merge Status ===",
                f"⚠️ Error reading merged file: {e}",
            ]
    else:
        lines = [
            "=== Merge Status ===",
            "❌ Merged file not found",
            f"Expected: {merged_parquet.name}",
        ]
    
    ax_merge.text(0.01, 0.99, "\n".join(lines), va="top", ha="left", fontsize=9, family='monospace')
    ax_merge.axis("off")
    ax_merge.set_title("Merge Status")
    
    # Bottom-left: Column listing
    ax_cols = axes[1, 0]
    if merged_parquet.exists() and pd is not None:
        try:
            df = pd.read_parquet(merged_parquet)
            import re
            
            # Categorize columns
            spectral_cols = [c for c in df.columns if re.search(r'_wl\d+nm|^wl\d+nm', c, re.IGNORECASE)]
            raw_cols = [c for c in spectral_cols if c.lower().startswith('raw_')]
            corr_cols = [c for c in spectral_cols if 'corr' in c.lower() and not c.lower().startswith('raw_')]
            conv_cols = [c for c in spectral_cols if any(x in c.lower() for x in ['etm', 'oli', 'tm', 'micasense']) and not c.lower().startswith('raw_')]
            meta_cols = [c for c in df.columns if c not in spectral_cols]
            
            lines = [
                "=== Column Summary ===",
                f"Total columns: {len(df.columns)}",
                "",
                "Spectral columns:",
                f"  Total: {len(spectral_cols)}",
                f"  Raw: {len(raw_cols)}",
                f"  Corrected: {len(corr_cols)}",
                f"  Convolved: {len(conv_cols)}",
                "",
                f"Metadata columns: {len(meta_cols)}",
                "",
                "=== Sample Column Names ===",
            ]
            
            # Show sample columns from each category
            max_samples = 8
            if corr_cols:
                lines.append(f"Corrected (showing {min(max_samples, len(corr_cols))} of {len(corr_cols)}):")
                for col in sorted(corr_cols)[:max_samples]:
                    lines.append(f"  • {col}")
                if len(corr_cols) > max_samples:
                    lines.append(f"  ... and {len(corr_cols) - max_samples} more")
                lines.append("")
            
            # Group convolved columns by sensor
            sensor_groups: dict[str, list[str]] = {}
            for col in conv_cols:
                col_lower = col.lower()
                sensor = None
                if 'etm' in col_lower:
                    sensor = 'ETM+'
                elif 'oli' in col_lower:
                    sensor = 'OLI'
                elif 'tm' in col_lower and 'etm' not in col_lower:
                    sensor = 'TM'
                elif 'micasense' in col_lower:
                    sensor = 'MicaSense'
                if sensor:
                    if sensor not in sensor_groups:
                        sensor_groups[sensor] = []
                    sensor_groups[sensor].append(col)
            
            if sensor_groups:
                lines.append("Convolved sensors:")
                for sensor in sorted(sensor_groups.keys()):
                    cols = sensor_groups[sensor]
                    lines.append(f"  {sensor} ({len(cols)} bands):")
                    for col in sorted(cols)[:5]:  # Show first 5 per sensor
                        lines.append(f"    • {col}")
                    if len(cols) > 5:
                        lines.append(f"    ... and {len(cols) - 5} more")
                lines.append("")
            
            if meta_cols:
                lines.append(f"Metadata (showing {min(max_samples, len(meta_cols))} of {len(meta_cols)}):")
                for col in sorted(meta_cols)[:max_samples]:
                    lines.append(f"  • {col}")
                if len(meta_cols) > max_samples:
                    lines.append(f"  ... and {len(meta_cols) - max_samples} more")
            
        except Exception as e:
            lines = [f"Error analyzing columns: {e}"]
    else:
        lines = ["Column analysis requires merged parquet file"]
    
    ax_cols.text(0.01, 0.99, "\n".join(lines), va="top", ha="left", fontsize=7, family='monospace')
    ax_cols.axis("off")
    ax_cols.set_title("Column Listing & Summary")
    
    # Bottom-right: Quality checks
    ax_quality = axes[1, 1]
    quality_checks = []
    
    # Check 1: Merged file exists
    if merged_parquet.exists():
        quality_checks.append("✅ Merged parquet exists")
    else:
        quality_checks.append("❌ Merged parquet missing")
    
    # Check 2: Expected parquet files
    expected_types = {
        "Original ENVI": list(flightline_dir.glob("*_envi.parquet")),
        "Corrected": list(flightline_dir.glob("*_corrected*.parquet")),
    }
    for name, files in expected_types.items():
        if files:
            quality_checks.append(f"✅ {name}: {len(files)} file(s)")
        else:
            quality_checks.append(f"⚠️ {name}: 0 files")
    
    # Check 3: Resampled products
    resampled = [p for p in flightline_dir.glob("*.parquet") 
                if "merged" not in p.name and "corrected" not in p.name 
                and "_envi.parquet" not in p.name and "polygon" not in p.name]
    if resampled:
        quality_checks.append(f"✅ Resampled products: {len(resampled)} file(s)")
    else:
        quality_checks.append("⚠️ No resampled products found")
    
    ax_quality.text(0.01, 0.99, "\n".join(quality_checks), va="top", ha="left", fontsize=9, family='monospace')
    ax_quality.axis("off")
    ax_quality.set_title("Quality Checks")
    
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _package_version() -> str:
    try:
        return version("cross-sensor-cal")
    except PackageNotFoundError:
        from . import __version__

        return __version__


def _git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
    except Exception:
        return "unknown"
    return out.decode("utf-8").strip()


def _provenance(prefix: str, inputs: Iterable[Path]) -> Provenance:
    hashes = {path.name: _hash_file(path) for path in inputs if path.exists()}
    return Provenance(
        flightline_id=prefix,
        created_utc=_dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        package_version=_package_version(),
        git_sha=_git_sha(),
        input_hashes=hashes,
    )


def _render_hist(ax: Axes, raw: np.ndarray, corr: np.ndarray, mask: np.ndarray) -> None:
    ax.set_title("Pre vs Post Histograms")
    masked_raw = np.where(mask, raw, np.nan)
    masked_corr = np.where(mask, corr, np.nan)
    bins = np.linspace(0, 1.2, 40)
    ax.hist(masked_raw.flatten(), bins=bins, alpha=0.4, label="Raw", color="#1f77b4")
    ax.hist(masked_corr.flatten(), bins=bins, alpha=0.4, label="Corrected", color="#ff7f0e")
    ax.set_xlabel("Reflectance")
    ax.legend(loc="upper right")


def _deterministic_trace_indices(count: int, max_traces: int) -> np.ndarray:
    if count <= 0 or max_traces <= 0:
        return np.array([], dtype=int)
    if count <= max_traces:
        return np.arange(count, dtype=int)
    rng = np.random.default_rng(_DRONE_QA_TRACE_RNG_SEED)
    return np.sort(rng.choice(count, size=max_traces, replace=False))


def _clean_plot_values(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    finite = arr[np.isfinite(arr)]
    if not finite.size:
        return finite
    return finite[(finite > -9990.0) & (np.abs(finite) <= _DRONE_QA_DISPLAY_UPPER_BOUND)]


def _set_percentile_ylim(
    ax: Axes,
    values: np.ndarray,
    *,
    lower_pct: float = 2.0,
    upper_pct: float = 98.0,
) -> None:
    clean = _clean_plot_values(values)
    if not clean.size:
        return
    ymin = float(np.nanpercentile(clean, lower_pct))
    ymax = float(np.nanpercentile(clean, upper_pct))
    if not np.isfinite(ymin) or not np.isfinite(ymax):
        return
    if ymax <= ymin:
        span = max(abs(ymax), 1.0) * 0.05
        ymin -= span
        ymax += span
    pad = max((ymax - ymin) * 0.08, 1e-6)
    lower = ymin - pad
    upper = ymax + pad
    if lower >= 0.0:
        lower = max(0.0, lower)
    ax.set_ylim(lower, upper)


def _preview_counts(values: np.ndarray) -> str:
    counts = np.asarray(values, dtype=int)
    return np.array2string(counts, threshold=12, edgeitems=4, max_line_width=160)


def _support_range_label(
    wavelengths: np.ndarray,
    support_mask: np.ndarray,
) -> str:
    idx = np.flatnonzero(np.asarray(support_mask, dtype=bool))
    if idx.size == 0:
        return "none"
    if wavelengths.size == support_mask.size:
        selected = np.asarray(wavelengths, dtype=float)[idx]
        finite = selected[np.isfinite(selected)]
        if finite.size:
            return f"{finite[0]:.1f}-{finite[-1]:.1f} nm ({idx.size} bands)"
    return f"b{int(idx[0])}-b{int(idx[-1])} ({idx.size} bands)"


def _support_wavelength_preview(
    wavelengths: np.ndarray,
    support_mask: np.ndarray,
    *,
    limit: int = 8,
) -> list[float | int]:
    idx = np.flatnonzero(np.asarray(support_mask, dtype=bool))
    if idx.size == 0:
        return []
    idx = idx[:limit]
    if wavelengths.size == support_mask.size:
        selected = np.asarray(wavelengths, dtype=float)[idx]
        return [round(float(value), 1) for value in selected if np.isfinite(value)]
    return [int(value) for value in idx]


def _top_outlier_band_labels(
    abs_diff: np.ndarray,
    wavelengths: np.ndarray,
    *,
    top_n: int = 3,
) -> list[str]:
    flat = abs_diff.reshape(abs_diff.shape[0], -1)
    band_abs_max = np.full(flat.shape[0], np.nan, dtype=float)
    finite_rows = np.any(np.isfinite(flat), axis=1)
    if np.any(finite_rows):
        band_abs_max[finite_rows] = np.nanmax(flat[finite_rows], axis=1)
    finite_idx = np.flatnonzero(np.isfinite(band_abs_max))
    if finite_idx.size == 0:
        return []
    ordered = finite_idx[np.argsort(band_abs_max[finite_idx])[::-1][:top_n]]
    labels: list[str] = []
    for idx in ordered:
        if wavelengths.size == band_abs_max.size and np.isfinite(wavelengths[idx]):
            labels.append(f"b{idx}@{float(wavelengths[idx]):.1f}nm={band_abs_max[idx]:.4f}")
        else:
            labels.append(f"b{idx}={band_abs_max[idx]:.4f}")
    return labels


def _summarize_sample_support(
    wavelengths: np.ndarray,
    sample_mask: np.ndarray,
) -> dict[str, Any]:
    sample_valid_counts = np.sum(sample_mask, axis=1).astype(int)
    support_any = sample_valid_counts > 0
    support_gt10 = sample_valid_counts > 10
    support_gt100 = sample_valid_counts > 100
    weak_support = sample_valid_counts <= 10
    return {
        "bands_with_any_support": int(np.count_nonzero(support_any)),
        "bands_with_gt10_support": int(np.count_nonzero(support_gt10)),
        "bands_with_gt100_support": int(np.count_nonzero(support_gt100)),
        "band_support_pct": {
            "any": float(100.0 * np.mean(support_any)) if support_any.size else 0.0,
            "gt10": float(100.0 * np.mean(support_gt10)) if support_gt10.size else 0.0,
            "gt100": float(100.0 * np.mean(support_gt100)) if support_gt100.size else 0.0,
        },
        "sample_valid_counts_summary": {
            "min": int(np.min(sample_valid_counts)) if sample_valid_counts.size else 0,
            "median": float(np.median(sample_valid_counts)) if sample_valid_counts.size else 0.0,
            "max": int(np.max(sample_valid_counts)) if sample_valid_counts.size else 0,
        },
        "support_wavelength_ranges_nm": {
            "any": _support_range_label(wavelengths, support_any),
            "gt10": _support_range_label(wavelengths, support_gt10),
            "gt100": _support_range_label(wavelengths, support_gt100),
        },
        "weak_support_wavelengths_preview": _support_wavelength_preview(
            wavelengths, weak_support
        ),
        "zero_support_wavelengths_preview": _support_wavelength_preview(
            wavelengths, sample_valid_counts == 0
        ),
    }


def _summarize_full_diff(
    full_diff: np.ndarray,
    wavelengths: np.ndarray,
) -> dict[str, Any]:
    full_abs_diff = np.abs(full_diff)
    finite_abs_diff = full_abs_diff[np.isfinite(full_abs_diff)]
    finite_count = int(finite_abs_diff.size)

    pixel_max_abs_diff = np.full(full_abs_diff.shape[1:], np.nan, dtype=float)
    finite_pixel_support = np.any(np.isfinite(full_abs_diff), axis=0)
    if np.any(finite_pixel_support):
        pixel_max_abs_diff[finite_pixel_support] = np.nanmax(
            full_abs_diff[:, finite_pixel_support], axis=0
        )

    comparisons_above_threshold = int(
        np.count_nonzero(finite_abs_diff > _DRONE_CHANGE_THRESHOLD)
    )
    pixels_with_any_nontrivial_change_pct = float(
        np.nanmean(pixel_max_abs_diff > _DRONE_CHANGE_THRESHOLD) * 100.0
    ) if np.any(np.isfinite(pixel_max_abs_diff)) else 0.0

    summary = {
        "global_mean_abs_diff": float(np.nanmean(finite_abs_diff)) if finite_count else 0.0,
        "global_median_abs_diff": float(np.nanmedian(finite_abs_diff)) if finite_count else 0.0,
        "global_p95_abs_diff": float(np.nanpercentile(finite_abs_diff, 95)) if finite_count else 0.0,
        "global_max_abs_diff": float(np.nanmax(finite_abs_diff)) if finite_count else 0.0,
        "finite_comparison_count": finite_count,
        "fraction_above_change_threshold": (
            float(100.0 * comparisons_above_threshold / finite_count) if finite_count else 0.0
        ),
        "pixels_with_any_nontrivial_change_pct": pixels_with_any_nontrivial_change_pct,
        "comparisons_above_change_threshold": comparisons_above_threshold,
        "n_abs_diff_gt_1": int(np.count_nonzero(finite_abs_diff > 1.0)),
        "n_abs_diff_gt_10": int(np.count_nonzero(finite_abs_diff > 10.0)),
        "n_abs_diff_gt_100": int(np.count_nonzero(finite_abs_diff > 100.0)),
        "top_outlier_bands": _top_outlier_band_labels(full_abs_diff, wavelengths),
        "change_threshold": float(_DRONE_CHANGE_THRESHOLD),
    }
    return summary


def _classify_drone_scene(
    diff_summary: dict[str, Any],
    support_summary: dict[str, Any],
) -> list[str]:
    flags: list[str] = []

    # Keep the QA scene labels deliberately simple and threshold-based so they
    # explain the observed failure mode rather than acting like a black box.
    is_effective_noop_correction = (
        diff_summary["global_mean_abs_diff"] <= _DRONE_NOOP_MEAN_ABS_DIFF_THRESHOLD
        and diff_summary["global_median_abs_diff"] <= _DRONE_NOOP_MEDIAN_ABS_DIFF_THRESHOLD
        and diff_summary["fraction_above_change_threshold"] <= _DRONE_NOOP_FRACTION_ABOVE_THRESHOLD_PCT
        and diff_summary["pixels_with_any_nontrivial_change_pct"] <= _DRONE_NOOP_CHANGED_PIXEL_PCT_THRESHOLD
    )
    if is_effective_noop_correction:
        flags.append("effective_noop_correction")

    is_outlier_dominated = (
        diff_summary["global_median_abs_diff"] <= _DRONE_OUTLIER_DOMINATED_MEDIAN_THRESHOLD
        and (
            diff_summary["global_p95_abs_diff"] >= _DRONE_OUTLIER_DOMINATED_P95_THRESHOLD
            or diff_summary["global_max_abs_diff"] >= 1.0
        )
        and (
            diff_summary["n_abs_diff_gt_1"] > 0
            or diff_summary["n_abs_diff_gt_10"] > 0
            or diff_summary["n_abs_diff_gt_100"] > 0
        )
    )
    if is_outlier_dominated:
        flags.append("outlier_dominated_correction")

    is_band_support_collapsed = (
        support_summary["band_support_pct"]["any"] < _DRONE_SUPPORT_COLLAPSE_BAND_PCT
        or support_summary["band_support_pct"]["gt10"] < _DRONE_SUPPORT_COLLAPSE_GT10_BAND_PCT
    )
    if is_band_support_collapsed:
        flags.append("band_support_collapsed")

    if not flags:
        flags.append("healthy_correction")
    return flags


def _scene_classification_messages(scene_classification: Sequence[str]) -> list[str]:
    lookup = {
        "healthy_correction": "Healthy correction signature",
        "effective_noop_correction": "Effective no-op correction detected",
        "outlier_dominated_correction": "Outlier-dominated correction detected",
        "band_support_collapsed": "Band-support collapse detected",
    }
    return [lookup.get(flag, flag.replace("_", " ")) for flag in scene_classification]


def _drone_sampling_debug(
    *,
    scene_id: str,
    wavelengths: np.ndarray,
    raw_cube: np.ndarray,
    corr_cube: np.ndarray,
    raw_valid: np.ndarray,
    corr_valid: np.ndarray,
    both_valid: np.ndarray,
    raw_sample: np.ndarray,
    corr_sample: np.ndarray,
    sample_mask: np.ndarray,
    sampling_diagnostics: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    """Summarize the full-raster QA sampling path for debugging polygon-mode drift.

    The spectral and wavelength-wise correction panels intentionally use sampled
    raster cubes (`raw_cube`, `corr_cube`, `raw_sample`, `corr_sample`) rather
    than polygon parquet rows. This helper makes that provenance explicit and
    captures whether valid support collapses upstream.
    """
    support_summary = _summarize_sample_support(wavelengths, sample_mask)
    diff = np.where(both_valid, corr_cube - raw_cube, np.nan)
    diff_summary = _summarize_full_diff(diff, wavelengths)
    scene_classification = _classify_drone_scene(diff_summary, support_summary)

    debug = {
        "scene_id": scene_id,
        "raw_cube_shape": list(raw_cube.shape),
        "corr_cube_shape": list(corr_cube.shape),
        "wavelength_count": int(wavelengths.size),
        "raw_valid_pct": float(np.mean(raw_valid) * 100.0) if raw_valid.size else 0.0,
        "corr_valid_pct": float(np.mean(corr_valid) * 100.0) if corr_valid.size else 0.0,
        "both_valid_pct": float(np.mean(both_valid) * 100.0) if both_valid.size else 0.0,
        "sample_shape": list(raw_sample.shape),
        "sample_mask_shape": list(sample_mask.shape),
        "scene_classification": scene_classification,
        **support_summary,
        **diff_summary,
    }
    if sampling_diagnostics:
        debug.update(sampling_diagnostics)
    # Backward-compatible aliases for existing debug consumers.
    debug["sample_valid_counts_per_band_summary"] = debug["sample_valid_counts_summary"]
    debug["bands_with_any_sample_support"] = debug["bands_with_any_support"]
    return debug


def _log_drone_sampling_debug(debug: dict[str, Any], sample_valid_counts: np.ndarray) -> None:
    scene_id = str(debug["scene_id"])
    logger.info(
        "[drone-qa] %s spectral panels use sampled full-raster cubes: top-right uses raw_cube/corr_cube samples; "
        "row-2-left uses diff=corr_sample-raw_sample; polygon parquet rows are not the direct source.",
        scene_id,
    )
    logger.info(
        "[drone-qa] %s cubes raw=%s corr=%s wavelengths=%d valid(raw/corr/both)=%.2f/%.2f/%.2f%% "
        "sample(raw/corr/mask)=%s/%s/%s",
        scene_id,
        tuple(debug["raw_cube_shape"]),
        tuple(debug["corr_cube_shape"]),
        int(debug["wavelength_count"]),
        float(debug["raw_valid_pct"]),
        float(debug["corr_valid_pct"]),
        float(debug["both_valid_pct"]),
        tuple(debug["sample_shape"]),
        tuple(debug["sample_shape"]),
        tuple(debug["sample_mask_shape"]),
    )
    logger.info(
        "[drone-qa] %s sampling eligible=%d/%d pixels (%.2f%%) sampled=%d (%.2f%% of eligible) min_valid_band_fraction=%.2f",
        scene_id,
        int(debug.get("eligible_pixels_for_sampling", 0)),
        int(debug.get("total_pixels", 0)),
        float(debug.get("eligible_pixel_pct", 0.0)),
        int(debug.get("sampled_pixels", 0)),
        float(debug.get("sampled_vs_eligible_pct", 0.0)),
        float(debug.get("min_valid_band_fraction_for_sampling", 0.0)),
    )
    logger.info(
        "[drone-qa] %s sample support counts_per_band=%s min/median/max=%d/%.1f/%d "
        "bands(any/>10/>100)=%d/%d/%d (%.1f/%.1f/%.1f%%) support_nm(any/>10/>100)=%s/%s/%s",
        scene_id,
        _preview_counts(sample_valid_counts),
        int(debug["sample_valid_counts_summary"]["min"]),
        float(debug["sample_valid_counts_summary"]["median"]),
        int(debug["sample_valid_counts_summary"]["max"]),
        int(debug["bands_with_any_support"]),
        int(debug["bands_with_gt10_support"]),
        int(debug["bands_with_gt100_support"]),
        float(debug["band_support_pct"]["any"]),
        float(debug["band_support_pct"]["gt10"]),
        float(debug["band_support_pct"]["gt100"]),
        debug["support_wavelength_ranges_nm"]["any"],
        debug["support_wavelength_ranges_nm"]["gt10"],
        debug["support_wavelength_ranges_nm"]["gt100"],
    )
    logger.info(
        "[drone-qa] %s |Δ| mean/median/max=%.6f/%.6f/%.6f finite>%0.3f=%d (%.3f%%) "
        "pixels_any>%0.3f=%.3f%% outliers(>1/>10/>100)=%d/%d/%d top_bands=%s",
        scene_id,
        float(debug["global_mean_abs_diff"]),
        float(debug["global_median_abs_diff"]),
        float(debug["global_max_abs_diff"]),
        float(debug["change_threshold"]),
        int(debug["comparisons_above_change_threshold"]),
        float(debug["fraction_above_change_threshold"]),
        float(debug["change_threshold"]),
        float(debug["pixels_with_any_nontrivial_change_pct"]),
        int(debug["n_abs_diff_gt_1"]),
        int(debug["n_abs_diff_gt_10"]),
        int(debug["n_abs_diff_gt_100"]),
        ", ".join(debug["top_outlier_bands"]) if debug["top_outlier_bands"] else "none",
    )


def _render_delta(
    ax: Axes,
    wavelengths: np.ndarray,
    report: CorrectionReport,
    *,
    sample_valid_counts: np.ndarray | None = None,
    scene_classification: Sequence[str] | None = None,
) -> None:
    xs = wavelengths if wavelengths.size == len(report.delta_median) else np.arange(len(report.delta_median))
    delta_median = np.asarray(report.delta_median, dtype=float)
    delta_q10 = np.asarray(report.delta_q10, dtype=float)
    delta_q25 = np.asarray(report.delta_q25, dtype=float)
    delta_q75 = np.asarray(report.delta_q75, dtype=float)
    delta_q90 = np.asarray(report.delta_q90, dtype=float)
    delta_abs_median = np.asarray(report.delta_abs_median, dtype=float)
    ax.set_title("Correction Distribution By Wavelength")
    ax.fill_between(xs, delta_q10, delta_q90, alpha=0.15, color="#4c78a8", label="10-90%")
    ax.fill_between(xs, delta_q25, delta_q75, alpha=0.25, color="#4c78a8", label="IQR")
    ax.plot(xs, delta_median, color="#1f77b4", linewidth=2.0, label="signed median Δ")
    ax.plot(
        xs,
        delta_abs_median,
        color="#e15759",
        linewidth=2.0,
        linestyle="--",
        label="median |Δ|",
    )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Wavelength (nm)" if wavelengths.size == len(report.delta_median) else "Band index")
    ax.set_ylabel("Reflectance Δ")
    _set_percentile_ylim(
        ax,
        np.concatenate([delta_q10, delta_q25, delta_q75, delta_q90, delta_median, delta_abs_median]),
        lower_pct=1.0,
        upper_pct=99.0,
    )
    if sample_valid_counts is not None and sample_valid_counts.size == delta_median.size:
        counts = np.asarray(sample_valid_counts, dtype=float)
        if np.nanmax(counts) > 0:
            ax2 = ax.twinx()
            normalized = counts / np.nanmax(counts)
            ax2.fill_between(xs, 0.0, normalized, color="0.75", alpha=0.18)
            ax2.plot(xs, normalized, color="0.45", linewidth=1.0, alpha=0.8, label="normalized support")
            ax2.set_ylim(0.0, 1.05)
            ax2.set_ylabel("Normalized support", fontsize=8, color="0.35")
            ax2.tick_params(axis="y", labelsize=7, colors="0.35")
            weak_mask = counts <= 10
            if np.any(weak_mask):
                ax.scatter(
                    xs[weak_mask],
                    np.full(np.count_nonzero(weak_mask), ax.get_ylim()[0]),
                    s=6,
                    color="#6b7280",
                    alpha=0.5,
                    clip_on=False,
                    zorder=5,
                )
            support_lines = [
                f"support min/med/max: {int(np.min(counts))}/{float(np.median(counts)):.0f}/{int(np.max(counts))}",
                f"bands >10 samples: {int(np.count_nonzero(counts > 10))}/{counts.size}",
                "missing chunks can reflect insufficient valid support",
            ]
            if scene_classification:
                support_lines.append(", ".join(_scene_classification_messages(scene_classification[:2])))
            ax.text(
                0.02,
                0.98,
                "\n".join(support_lines),
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=8,
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.75, edgecolor="none"),
            )
    ax.legend(loc="upper right")


def _render_scatter(ax: Axes, data: dict[str, tuple[np.ndarray, np.ndarray]]) -> None:
    ax.set_title("Convolved vs Corrected")
    if not data:
        ax.text(0.5, 0.5, "No convolved sensors", ha="center", va="center")
        return
    for sensor, pair in data.items():
        corrected, convolved = pair
        ax.scatter(corrected, convolved, s=3, alpha=0.3, label=sensor)
    limits_x = ax.get_xlim()
    limits_y = ax.get_ylim()
    low = min(limits_x[0], limits_y[0])
    high = max(limits_x[1], limits_y[1])
    ax.plot([low, high], [low, high], color="black", linestyle="--", linewidth=0.8)
    ax.set_xlim(low, high)
    ax.set_ylim(low, high)
    ax.set_xlabel("Corrected reflectance")
    ax.set_ylabel("Convolved reflectance")
    ax.legend(loc="upper left", fontsize="small")


def _render_wavelength_reflectance_plot(
    ax: Axes,
    flightline_dir: Path,
    prefix: str,
    wavelengths: np.ndarray | None = None,
) -> None:
    """
    Render a wavelength-based reflectance plot showing:
    - Corrected hyperspectral reflectance vs wavelength
    - Convolved sensor bands overlaid
    - Highlighted regions showing where convolutions occur
    """
    print(f"[QA]   📊 Starting wavelength reflectance plot for {prefix}")
    
    if pd is None:
        ax.text(0.5, 0.5, "Pandas required for wavelength plot", ha="center", va="center")
        print("[QA]   ⚠️  Pandas not available")
        return
    
    # Find merged parquet
    merged_parquet = flightline_dir / f"{prefix}_merged_pixel_extraction.parquet"
    if not merged_parquet.exists():
        merged_parquet = flightline_dir / f"{prefix}_polygons_merged_pixel_extraction.parquet"
        if not merged_parquet.exists():
            ax.text(0.5, 0.5, "Merged parquet not found", ha="center", va="center")
            print(f"[QA]   ⚠️  Merged parquet not found in {flightline_dir}")
            return
    
    print(f"[QA]   📂 Reading parquet: {merged_parquet.name}")
    try:
        df = pd.read_parquet(merged_parquet)
        print(f"[QA]   ✅ Loaded parquet: {df.shape[0]} rows, {df.shape[1]} columns")
    except Exception as e:
        ax.text(0.5, 0.5, f"Error reading parquet: {e}", ha="center", va="center")
        print(f"[QA]   ❌ Error reading parquet: {e}")
        import traceback
        traceback.print_exc()
        return
    
    import re
    wl_re = re.compile(r"_wl(\d+)nm", re.IGNORECASE)
    
    def _wl_nm(col: str) -> int | None:
        m = wl_re.search(col)
        if not m:
            return None
        try:
            return int(m.group(1))
        except ValueError:
            return None
    
    # Get corrected hyperspectral columns
    corr_cols = [
        c for c in df.columns
        if c.lower().startswith("corr_") and wl_re.search(c) is not None
    ]
    print(f"[QA]   🔍 Found {len(corr_cols)} corrected spectral columns")
    if not corr_cols:
        ax.text(0.5, 0.5, "No corrected spectral columns found", ha="center", va="center")
        print(f"[QA]   ⚠️  No corr_* columns found. Sample columns: {list(df.columns[:10])}")
        return
    
    # Build wavelength -> corrected column mapping
    corr_by_wl: dict[int, str] = {}
    for c in corr_cols:
        wl = _wl_nm(c)
        if wl is not None:
            corr_by_wl[wl] = c
    
    if not corr_by_wl:
        ax.text(0.5, 0.5, "No valid corrected wavelengths found", ha="center", va="center")
        return
    
    # Use wavelengths from column names (most reliable)
    # The provided wavelengths might not match column names exactly
    wl_array = np.array(sorted(corr_by_wl.keys()), dtype=float)
    
    if len(wl_array) == 0:
        ax.text(0.5, 0.5, "No wavelengths found in columns", ha="center", va="center", fontsize=10)
        print(f"[QA]   ⚠️  No wavelengths extracted from {len(corr_cols)} columns")
        return
    
    # Log wavelength range for debugging
    print(f"[QA]   📊 Wavelength plot: {len(wl_array)} bands, range {wl_array.min():.1f}-{wl_array.max():.1f} nm")
    
    # Sample a subset of rows for plotting (to avoid memory issues)
    n_sample = min(1000, len(df))
    if len(df) > n_sample:
        sample_df = df.sample(n=n_sample, random_state=42)
    else:
        sample_df = df
    
    # Plot corrected hyperspectral data (median across samples)
    # Match wavelengths to columns more flexibly
    corr_values = []
    matched_wls = []
    
    for wl in wl_array:
        wl_int = int(round(wl))
        # Try exact match first
        if wl_int in corr_by_wl:
            col = corr_by_wl[wl_int]
        else:
            # Try to find nearest wavelength
            available_wls = np.array(list(corr_by_wl.keys()))
            nearest_idx = np.argmin(np.abs(available_wls - wl_int))
            nearest_wl = int(available_wls[nearest_idx])
            if abs(nearest_wl - wl_int) <= 5:  # Within 5 nm
                col = corr_by_wl[nearest_wl]
                wl_int = nearest_wl
            else:
                corr_values.append(np.nan)
                matched_wls.append(wl)
                continue
        
        vals = pd.to_numeric(sample_df[col], errors="coerce")
        # Filter out -9999, negative values, and invalid values
        valid_vals = vals[(vals > -9990) & (vals >= 0) & (vals < 1000) & np.isfinite(vals)]
        if len(valid_vals) > 0:
            corr_values.append(np.median(valid_vals))
            matched_wls.append(wl)
        else:
            corr_values.append(np.nan)
            matched_wls.append(wl)
    
    corr_values = np.array(corr_values)
    matched_wls = np.array(matched_wls)
    valid_mask = np.isfinite(corr_values)
    
    if not np.any(valid_mask):
        error_msg = (
            f"No valid corrected reflectance data\n"
            f"Found {len(corr_by_wl)} wavelength columns\n"
            f"Wavelength range: {wl_array.min():.1f}-{wl_array.max():.1f} nm\n"
            f"DataFrame shape: {df.shape}\n"
            f"Sample size: {len(sample_df)} rows"
        )
        ax.text(0.5, 0.5, error_msg, ha="center", va="center", fontsize=8, family='monospace')
        print(f"[QA] ⚠️  No valid data for wavelength plot: {len(corr_by_wl)} cols, {len(wl_array)} wls, {df.shape}")
        return
    
    # Use matched wavelengths for plotting
    plot_wls = matched_wls[valid_mask]
    plot_vals = corr_values[valid_mask]
    
    print(f"[QA]   ✅ Plotting {len(plot_wls)} valid points (range: {plot_wls.min():.1f}-{plot_wls.max():.1f} nm, values: {plot_vals.min():.3f}-{plot_vals.max():.3f})")
    
    # Smooth the corrected hyperspectral spectrum to reduce vertical noise
    # Use Gaussian smoothing for a smoother, straighter curve
    if len(plot_vals) > 20:
        # Use a larger smoothing window: ~6% of data points for stronger smoothing
        # This makes the curve straighter and less wavy
        window_size = max(5, min(35, int(len(plot_vals) * 0.06)))
        if window_size % 2 == 0:
            window_size += 1  # Make odd for symmetric smoothing
        
        # Use Gaussian smoothing if scipy is available, otherwise use larger moving average
        if ndimage is not None:
            sigma = window_size / 6.0  # Standard deviation for Gaussian
            smoothed_vals = ndimage.gaussian_filter1d(plot_vals, sigma=sigma, mode='nearest')
            print(f"[QA]   🔄 Applied Gaussian smoothing (sigma: {sigma:.1f}, effective window: {window_size}) for straighter curve")
        else:
            # Fallback: larger moving average with Gaussian-like weights
            # Create a simple Gaussian-like kernel
            kernel = np.exp(-0.5 * ((np.arange(window_size) - window_size // 2) / (window_size / 6.0)) ** 2)
            kernel = kernel / kernel.sum()
            smoothed_vals = np.convolve(plot_vals, kernel, mode='same')
            print(f"[QA]   🔄 Applied weighted smoothing (window size: {window_size}) for straighter curve")
    else:
        smoothed_vals = plot_vals
    
    # Plot corrected hyperspectral spectrum as a smooth continuous line (the "mountain curve")
    ax.plot(plot_wls, smoothed_vals, 
            color='black', linewidth=2.0, alpha=0.8, label='Corrected hyperspectral (smoothed)', zorder=1)
    
    # Find convolved sensor columns and plot them directly on the line
    sensor_patterns = {
        'etm+etm+': ('olive', 'ETM+', '^'),
        'etm+etm+_undarkened': ('darkolivegreen', 'ETM+ (undark)', '^'),
        'olioli': ('blue', 'OLI', 's'),
        'olioli_undarkened': ('lightblue', 'OLI (undark)', 's'),
        'tmtm': ('red', 'TM', 'D'),
        'tmtm_undarkened': ('coral', 'TM (undark)', 'D'),
        'micasense': ('purple', 'MicaSense', 'o'),
        'micasense_undarkened': ('plum', 'MicaSense (undark)', 'o'),
    }
    
    # Group sensor columns by sensor name
    sensor_cols_by_sensor: dict[str, list[tuple[int, str]]] = {}
    for col in df.columns:
        if wl_re.search(col) and not col.lower().startswith(('raw_', 'corr_')):
            wl = _wl_nm(col)
            if wl is None:
                continue
            # Extract sensor name (prefix before _b or _undarkened_b)
            col_lower = col.lower()
            for pattern, (color, label, marker) in sensor_patterns.items():
                # More flexible pattern matching
                pattern_lower = pattern.lower().replace('+', '')
                if pattern_lower in col_lower or pattern.replace('+', r'\+') in col_lower:
                    if pattern not in sensor_cols_by_sensor:
                        sensor_cols_by_sensor[pattern] = []
                    sensor_cols_by_sensor[pattern].append((wl, col))
                    break
    
    print(f"[QA]   🔍 Found {sum(len(v) for v in sensor_cols_by_sensor.values())} convolved sensor columns across {len(sensor_cols_by_sensor)} sensors")
    for pattern, cols in sensor_cols_by_sensor.items():
        print(f"[QA]     - {pattern}: {len(cols)} bands")
    
    # Plot each sensor's bands, showing both corrected value (on line) and convolved value
    plotted_sensors = []
    all_conv_values = []  # Collect all convolved values for y-axis limits
    total_plotted_bands = 0  # Track total bands plotted across all sensors
    
    for pattern, (color, label, marker) in sensor_patterns.items():
        if pattern not in sensor_cols_by_sensor:
            continue
        
        sensor_wls = sorted([wl for wl, _ in sensor_cols_by_sensor[pattern]])
        if not sensor_wls:
            continue
        
        # For each convolved band, find the corrected value at that wavelength
        corr_at_sensor_wls = []
        conv_values = []
        conv_wavelengths = []
        
        # Track filtering reasons
        total_bands = len(sensor_cols_by_sensor[pattern])
        filtered_no_data = 0
        filtered_negative = 0
        filtered_no_corr_match = 0
        
        for wl, col in sensor_cols_by_sensor[pattern]:
            # Get convolved value - exclude negative values and no-data
            vals = pd.to_numeric(sample_df[col], errors="coerce")
            # Filter: exclude -9999 (no-data), negative values, and very large values
            valid_vals = vals[(vals > -9990) & (vals >= 0) & (vals < 1000) & np.isfinite(vals)]
            
            if len(valid_vals) == 0:
                # Check why it was filtered
                all_vals = vals[np.isfinite(vals)]
                if len(all_vals) == 0:
                    filtered_no_data += 1
                elif np.any(all_vals < 0):
                    filtered_negative += 1
                else:
                    filtered_no_data += 1
                continue
            
            conv_val = np.median(valid_vals)
            conv_values.append(conv_val)
            conv_wavelengths.append(wl)
            
            # Find corrected value at this wavelength
            # Interpolate from the plot data if exact match not found
            wl_int = int(round(wl))
            corr_val = None
            
            if wl_int in corr_by_wl:
                corr_col = corr_by_wl[wl_int]
                corr_vals = pd.to_numeric(sample_df[corr_col], errors="coerce")
                # Also exclude negative values for corrected
                valid_corr = corr_vals[(corr_vals > -9990) & (corr_vals >= 0) & (corr_vals < 1000) & np.isfinite(corr_vals)]
                if len(valid_corr) > 0:
                    corr_val = np.median(valid_corr)
            else:
                # Interpolate from smoothed plot data (use smoothed values for consistency with the line)
                if len(plot_wls) > 0:
                    # Find nearest wavelength in plot data
                    nearest_idx = np.argmin(np.abs(plot_wls - wl))
                    if abs(plot_wls[nearest_idx] - wl) < 10:  # Within 10 nm
                        # Use smoothed value for consistency with the displayed line
                        corr_val = smoothed_vals[nearest_idx]
                        # Only use if non-negative
                        if corr_val < 0:
                            corr_val = None
            
            if corr_val is not None:
                corr_at_sensor_wls.append((wl, corr_val, conv_val))
            else:
                filtered_no_corr_match += 1
        
        if not corr_at_sensor_wls:
            print(f"[QA]     ⚠️  {label}: No valid data points after filtering")
            continue
        
        # Report statistics
        plotted_count = len(corr_at_sensor_wls)
        filtered_count = total_bands - plotted_count
        print(f"[QA]     ✅ {label}: Plotting {plotted_count}/{total_bands} bands", end="")
        if filtered_count > 0:
            reasons = []
            if filtered_no_data > 0:
                reasons.append(f"{filtered_no_data} no-data")
            if filtered_negative > 0:
                reasons.append(f"{filtered_negative} negative")
            if filtered_no_corr_match > 0:
                reasons.append(f"{filtered_no_corr_match} no corrected match")
            if reasons:
                print(f" (filtered: {', '.join(reasons)})")
            else:
                print()
        else:
            print()
        
        total_plotted_bands += plotted_count
        
        # Plot vertical lines from corrected (on line) to convolved (point)
        for wl, corr_val, conv_val in corr_at_sensor_wls:
            # Draw a vertical line from the corrected line to the convolved point
            # This shows where convolution occurred and the difference
            ax.plot([wl, wl], [corr_val, conv_val], 
                   color=color, linewidth=1.5, alpha=0.6, linestyle='--', zorder=2)
        
        # Plot convolved values as colored markers
        if conv_wavelengths:
            ax.scatter(conv_wavelengths, conv_values, 
                      color=color, s=100, alpha=0.9, marker=marker, 
                      edgecolors='black', linewidths=1.5, zorder=4,
                      label=label)
            all_conv_values.extend(conv_values)
        
        # Mark the corrected values at these wavelengths on the line with small markers
        corr_wls = [wl for wl, _, _ in corr_at_sensor_wls]
        corr_vals_at_wls = [corr_val for _, corr_val, _ in corr_at_sensor_wls]
        if corr_wls:
            ax.scatter(corr_wls, corr_vals_at_wls,
                      color=color, s=40, alpha=0.7, marker='|', 
                      linewidths=3.0, zorder=3)
        
        plotted_sensors.append(label)
    
    ax.set_xlabel("Wavelength (nm)", fontsize=10)
    ax.set_ylabel("Reflectance", fontsize=10)
    ax.set_title("Corrected Reflectance vs Wavelength\n(Convolved bands marked on spectrum)", fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Only show legend if we have sensors
    if plotted_sensors:
        ax.legend(loc='upper right', fontsize=7, ncol=1, framealpha=0.9)
    
    # Set y-axis limits with fixed maximum to show more data and make curve appear smoother
    # Use a reasonable maximum (5000) since values above this are likely invalid
    # This wider range makes the curve appear less wavy by reducing relative variation
    Y_AXIS_MAX = 5000  # Maximum reflectance value to display (values above are likely invalid)
    
    if len(plot_vals) > 0:
        y_data = plot_vals
        # Filter out invalid values
        y_valid = y_data[np.isfinite(y_data) & (y_data >= 0)]
        
        if len(y_valid) > 0:
            # Count how many points are above the maximum threshold
            points_above_max = np.sum(y_valid > Y_AXIS_MAX)
            # Always use the full Y_AXIS_MAX range to make the curve appear smoother
            # This wider range reduces relative variation, making the curve less wavy
            y_min = 0
            y_max = Y_AXIS_MAX
            
            # Check convolved values to see if any extend beyond threshold
            if all_conv_values:
                conv_valid = np.array([v for v in all_conv_values if np.isfinite(v) and v >= 0])
                if len(conv_valid) > 0:
                    points_above_max += np.sum(conv_valid > Y_AXIS_MAX)
            
            ax.set_ylim(y_min, y_max)
            print(f"[QA]   📊 Y-axis range: [{y_min:.1f}, {y_max:.1f}] (full range up to {Y_AXIS_MAX} for smoother visualization)")
            if points_above_max > 0:
                print(f"[QA]   📉 {points_above_max} points above {Y_AXIS_MAX} threshold (likely invalid, excluded from display)")
            else:
                print(f"[QA]   ✅ All {len(y_valid)} points within display range")
        else:
            # Fallback: use full range
            y_max_data = np.nanmax(y_data) if len(y_data) > 0 else 1.0
            ax.set_ylim(0, min(Y_AXIS_MAX, max(1.0, y_max_data * 1.1)))
            print("[QA]   ⚠️  Using fallback y-axis range (no valid data)")
    
    # Summary statistics
    total_found_bands = sum(len(v) for v in sensor_cols_by_sensor.values())
    
    if plotted_sensors:
        print(f"[QA]   ✅ Successfully plotted {len(plotted_sensors)} sensors: {', '.join(plotted_sensors)}")
        if total_found_bands > total_plotted_bands:
            filtered_count = total_found_bands - total_plotted_bands
            print(f"[QA]   📊 Summary: {total_plotted_bands}/{total_found_bands} convolved bands plotted ({filtered_count} filtered out)")
        else:
            print(f"[QA]   📊 Summary: All {total_plotted_bands} convolved bands plotted")
    else:
        print(f"[QA]   ⚠️  No convolved sensors plotted (found {len(sensor_cols_by_sensor)} sensor groups)")
    
    # Check for missing sensors
    found_sensor_patterns = set(sensor_cols_by_sensor.keys())
    expected_sensor_patterns = set(sensor_patterns.keys())
    missing_patterns = expected_sensor_patterns - found_sensor_patterns
    if missing_patterns:
        missing_labels = [sensor_patterns[s][1] for s in missing_patterns if s in sensor_patterns]
        if missing_labels:
            print(f"[QA]   ℹ️  Sensors not found in data: {', '.join(missing_labels)}")


def _render_footer(fig: Figure, metrics: QAMetrics) -> None:
    prov = metrics.provenance
    hashes = ", ".join(f"{k}:{v[:8]}" for k, v in prov.input_hashes.items())
    footer = (
        f"Flightline: {prov.flightline_id} | UTC: {prov.created_utc} | "
        f"Package: {prov.package_version} | Git: {prov.git_sha}\nInputs: {hashes}"
    )
    fig.text(0.01, 0.02, footer, fontsize=8, ha="left", va="bottom")


def _render_issues(ax: Axes, issues: list[str]) -> None:
    if not issues:
        return
    message = "\n".join(f"⚠ {issue}" for issue in issues[:4])
    ax.text(
        0.01,
        0.99,
        message,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8,
        color="white",
        bbox=dict(boxstyle="round", facecolor="#c1121f", alpha=0.8, edgecolor="none"),
    )


def _render_aop_qa_summary(ax: Axes, metrics: QAMetrics) -> None:
    """Render a compact text summary for the normal AOP QA PNG."""

    header = metrics.header
    mask = metrics.mask
    issue_lines = metrics.issues[:5] if metrics.issues else ["No general QA issues flagged."]
    lines = [
        f"Flightline: {metrics.provenance.flightline_id}",
        f"Bands: {header.n_bands}",
        f"Wavelengths: {header.first_nm} - {header.last_nm} nm",
        f"Wavelength source: {header.wavelength_source}",
        f"Valid pixels: {mask.valid_pct:.2f}%",
        f"Negative reflectance: {metrics.negatives_pct:.2f}%",
        f">1.2 reflectance: {metrics.overbright_pct:.2f}%",
        "",
        "Flags:",
        *[f"- {issue}" for issue in issue_lines],
    ]
    if metrics.brightness_summary:
        lines.extend(["", f"Brightness tables: {len(metrics.brightness_summary)}"])

    ax.text(
        0.02,
        0.98,
        "\n".join(lines),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        family="monospace",
    )
    ax.axis("off")
    ax.set_title("QA Summary And Flags")


def _nodata_mask(cube: np.ndarray, nodata_value: float | None) -> np.ndarray:
    mask = ~np.isfinite(cube)
    if nodata_value is not None and np.isfinite(nodata_value):
        mask |= np.isclose(cube, float(nodata_value), atol=1e-6)
    return mask


def _cube_valid_mask(cube: np.ndarray, nodata_value: float | None) -> np.ndarray:
    return np.isfinite(cube) & ~_nodata_mask(cube, nodata_value)


def _drone_correction_status(
    qa_summary: dict[str, Any] | None,
    *,
    correction_median: float,
    correction_max: float,
    scene_debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    audit = qa_summary if isinstance(qa_summary, dict) else {}
    flags = audit.get("flags", {}) if isinstance(audit.get("flags", {}), dict) else {}
    observed_change = bool(
        np.isfinite(correction_max) and abs(float(correction_max)) > _DRONE_OBSERVED_CHANGE_EPS
    )
    scene_debug = scene_debug if isinstance(scene_debug, dict) else {}
    scene_classification = list(scene_debug.get("scene_classification", []))
    return {
        "topo_requested": bool(flags.get("topo_requested", False)),
        "brdf_requested": bool(flags.get("brdf_requested", False)),
        "topo_applied": bool(flags.get("topo_applied", False)),
        "brdf_applied": bool(flags.get("brdf_applied", False)),
        "reused_existing_corrected": bool(flags.get("reused_existing_corrected", False)),
        "correction_failed": bool(flags.get("correction_failed", False)),
        "status_source": str(audit.get("correction_status_source", "unknown")),
        "observed_change": observed_change,
        "observed_change_threshold": _DRONE_OBSERVED_CHANGE_EPS,
        "spatial_abs_delta_median": float(correction_median),
        "spatial_abs_delta_max": float(correction_max),
        "scene_classification": scene_classification,
        "scene_classification_messages": _scene_classification_messages(scene_classification),
    }


def _render_drone_correction_status_box(ax: Axes, status: dict[str, Any]) -> None:
    source_lookup = {
        "live_run": "current run",
        "existing_qa_json": "existing QA JSON",
        "reuse_without_prior_audit": "reused output; prior audit unavailable",
        "unknown": "unknown",
    }
    source_label = source_lookup.get(str(status.get("status_source")), str(status.get("status_source")))
    lines = [
        "Correction status",
        f"Topo requested/applied: {'yes' if status.get('topo_requested') else 'no'} / {'yes' if status.get('topo_applied') else 'no'}",
        f"BRDF requested/applied: {'yes' if status.get('brdf_requested') else 'no'} / {'yes' if status.get('brdf_applied') else 'no'}",
        f"Reused corrected output: {'yes' if status.get('reused_existing_corrected') else 'no'}",
        f"Observed change in panel: {'yes' if status.get('observed_change') else 'no'}",
        f"Status source: {source_label}",
    ]
    scene_messages = list(status.get("scene_classification_messages", []))
    if scene_messages:
        lines.append(f"Scene QA: {', '.join(scene_messages)}")
    if status.get("correction_failed"):
        lines.insert(1, "Correction failure recorded in audit")
    ax.text(
        0.02,
        0.02,
        "\n".join(lines),
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="none"),
    )


def _median_spectrum(cube: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
    masked = np.where(valid_mask, cube, np.nan)
    return np.nanmedian(masked, axis=(1, 2))


def _despike_spectrum_for_display(
    xs: np.ndarray,
    spectrum: np.ndarray,
) -> tuple[np.ndarray, list[int]]:
    """Suppress isolated spectral spikes for display without changing source data."""

    display = np.asarray(spectrum, dtype=np.float64).copy()
    xs = np.asarray(xs, dtype=np.float64)
    finite_idx = np.flatnonzero(np.isfinite(display) & np.isfinite(xs))
    if finite_idx.size < 3:
        return display, []

    band_steps = np.abs(np.diff(display[finite_idx]))
    typical_step = float(np.nanmedian(band_steps)) if band_steps.size else 0.0
    if not np.isfinite(typical_step) or typical_step <= 0.0:
        typical_step = max(float(np.nanmedian(np.abs(display[finite_idx]))), 1.0)

    spikes: list[int] = []
    for pos in range(1, finite_idx.size - 1):
        left_i = int(finite_idx[pos - 1])
        band_i = int(finite_idx[pos])
        right_i = int(finite_idx[pos + 1])
        left_x = xs[left_i]
        band_x = xs[band_i]
        right_x = xs[right_i]
        if np.isfinite(left_x) and np.isfinite(right_x) and right_x != left_x:
            expected = float(
                np.interp(band_x, [left_x, right_x], [display[left_i], display[right_i]])
            )
        else:
            expected = float(0.5 * (display[left_i] + display[right_i]))
        deviation = abs(float(display[band_i]) - expected)
        local_scale = max(
            abs(float(display[right_i]) - float(display[left_i])),
            typical_step,
            1.0,
        )
        if deviation > (6.0 * local_scale) and deviation > (4.0 * typical_step):
            display[band_i] = expected
            spikes.append(band_i)
    return display, spikes


def _render_drone_band_fidelity(
    ax: Axes,
    wavelengths: np.ndarray,
    raw_spectrum: np.ndarray,
    corr_spectrum: np.ndarray,
    band_map: dict[str, dict[str, float | int]] | None,
    raw_sample: np.ndarray | None = None,
    corr_sample: np.ndarray | None = None,
    sample_mask: np.ndarray | None = None,
    *,
    max_traces: int = 150,
) -> None:
    xs = wavelengths if wavelengths.size == raw_spectrum.size else np.arange(raw_spectrum.size)
    raw_display, _ = _despike_spectrum_for_display(xs, raw_spectrum)
    corr_display, _ = _despike_spectrum_for_display(xs, corr_spectrum)
    valid_samples = (
        raw_sample is not None
        and corr_sample is not None
        and sample_mask is not None
        and raw_sample.shape == corr_sample.shape == sample_mask.shape
        and raw_sample.ndim == 2
        and raw_sample.shape[0] == xs.size
        and raw_sample.shape[1] > 0
    )
    sampled_values: list[np.ndarray] = []
    if valid_samples:
        trace_idx = _deterministic_trace_indices(raw_sample.shape[1], max_traces)
        for idx in trace_idx:
            band_valid = sample_mask[:, idx]
            raw_trace = np.asarray(raw_sample[:, idx], dtype=float)
            corr_trace = np.asarray(corr_sample[:, idx], dtype=float)
            raw_trace = np.where(band_valid & (raw_trace > -9990.0), raw_trace, np.nan)
            corr_trace = np.where(band_valid & (corr_trace > -9990.0), corr_trace, np.nan)
            if np.any(np.isfinite(raw_trace)):
                ax.plot(xs, raw_trace, color="#1f77b4", linewidth=0.5, alpha=0.035, zorder=1)
                sampled_values.append(raw_trace)
            if np.any(np.isfinite(corr_trace)):
                ax.plot(xs, corr_trace, color="#ff7f0e", linewidth=0.5, alpha=0.035, zorder=1)
                sampled_values.append(corr_trace)
    ax.plot(xs, raw_display, color="#1f77b4", linewidth=2.0, label="raw median", zorder=3)
    ax.plot(xs, corr_display, color="#ff7f0e", linewidth=1.8, label="corrected median", zorder=3)
    ax.set_title("Median Spectra And Sampled Pixel Traces")
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Reflectance")

    if band_map:
        for name, info in band_map.items():
            idx = int(info.get("index", 0))
            wl = float(info.get("wavelength", np.nan))
            if 0 <= idx < raw_spectrum.size:
                ax.scatter(
                    [wl],
                    [raw_display[idx]],
                    s=40,
                    zorder=4,
                    label=f"{name} -> {wl:.1f} nm",
                )
            ax.axvline(wl, color="gray", linewidth=0.8, linestyle="--", alpha=0.4)
        summary = "\n".join(
            f"{name}: b{int(info.get('index', 0))} @ {float(info.get('wavelength', np.nan)):.1f} nm"
            for name, info in band_map.items()
        )
        ax.text(
            0.02,
            0.98,
            summary,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="none"),
        )
    finite_display = np.concatenate(
        [
            raw_display[np.isfinite(raw_display)],
            corr_display[np.isfinite(corr_display)],
        ]
    )
    if sampled_values:
        sampled_flat = np.concatenate([trace[np.isfinite(trace)] for trace in sampled_values if np.any(np.isfinite(trace))])
        if sampled_flat.size:
            finite_display = np.concatenate([finite_display, sampled_flat])
    _set_percentile_ylim(ax, finite_display, lower_pct=1.0, upper_pct=99.0)
    ax.legend(loc="best", fontsize=8)
    ax.grid(True, alpha=0.2)


def _render_drone_nodata_map(
    ax: Axes,
    nodata_fraction: np.ndarray,
    title: str,
) -> None:
    image = ax.imshow(nodata_fraction, cmap="magma", vmin=0.0, vmax=100.0)
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="% bands flagged")


def _render_drone_correction_magnitude(
    ax: Axes,
    full_diff: np.ndarray,
    scene_debug: dict[str, Any] | None = None,
) -> dict[str, float]:
    scene_debug = scene_debug if isinstance(scene_debug, dict) else {}
    full_abs_diff = np.abs(full_diff)
    abs_delta = np.nanmedian(full_abs_diff, axis=0)
    abs_delta_p90_map = np.nanpercentile(full_abs_diff, 90, axis=0)
    changed_frac = np.nanmean(full_abs_diff > _DRONE_CORRECTION_CHANGE_THRESHOLD, axis=0) * 100.0
    valid_mask = np.isfinite(full_diff)
    valid_band_count = np.sum(valid_mask, axis=0)
    valid_band_fraction = np.mean(valid_mask, axis=0) * 100.0
    finite = abs_delta[np.isfinite(abs_delta)]
    vmax = float(np.nanpercentile(finite, 95)) if finite.size else 1.0
    image = ax.imshow(abs_delta, cmap="viridis", vmin=0.0, vmax=max(vmax, 1e-6))
    ax.set_title("Spatial Median Absolute Correction Across Bands")
    ax.set_xticks([])
    ax.set_yticks([])
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="|delta|")
    finite_changed = changed_frac[np.isfinite(changed_frac)]
    finite_valid_band_count = valid_band_count[np.isfinite(valid_band_count)]
    finite_valid_band_fraction = valid_band_fraction[np.isfinite(valid_band_fraction)]
    pixels_above_threshold_pct = (
        float(np.mean(finite_changed > 0.0) * 100.0) if finite_changed.size else 0.0
    )
    summary = {
        "spatial_abs_delta_median": float(np.nanmedian(abs_delta)) if finite.size else 0.0,
        "spatial_abs_delta_p95": float(np.nanpercentile(abs_delta, 95)) if finite.size else 0.0,
        "spatial_abs_delta_p90": float(np.nanmedian(abs_delta_p90_map[np.isfinite(abs_delta_p90_map)]))
        if np.any(np.isfinite(abs_delta_p90_map))
        else 0.0,
        "spatial_abs_delta_max": float(np.nanmax(abs_delta)) if finite.size else 0.0,
        "pixels_above_change_threshold_pct": pixels_above_threshold_pct,
        "spatial_changed_frac_median": float(np.nanmedian(finite_changed)) if finite_changed.size else 0.0,
        "spatial_changed_frac_p95": float(np.nanpercentile(finite_changed, 95)) if finite_changed.size else 0.0,
        "median_valid_bands_per_pixel": (
            float(np.nanmedian(finite_valid_band_count)) if finite_valid_band_count.size else 0.0
        ),
        "median_valid_band_fraction_per_pixel": (
            float(np.nanmedian(finite_valid_band_fraction)) if finite_valid_band_fraction.size else 0.0
        ),
        "display_vmax": float(max(vmax, 1e-6)),
        "display_percentile": 95.0,
        "change_threshold": float(_DRONE_CORRECTION_CHANGE_THRESHOLD),
    }
    scene_messages = _scene_classification_messages(scene_debug.get("scene_classification", []))
    stats_text = "\n".join(
        [
            f"median |Δ|: {summary['spatial_abs_delta_median']:.4f}",
            f"95th pct |Δ|: {summary['spatial_abs_delta_p95']:.4f}",
            f"pixels > {summary['change_threshold']:.3f}: {summary['pixels_above_change_threshold_pct']:.1f}%",
            f"changed frac median/p95: {summary['spatial_changed_frac_median']:.1f}/{summary['spatial_changed_frac_p95']:.1f}%",
            f"median valid bands: {summary['median_valid_bands_per_pixel']:.0f}",
            f"display vmax: {summary['display_vmax']:.4f}",
        ]
    )
    if scene_messages:
        stats_text += "\n" + "; ".join(scene_messages[:2])
    ax.text(
        0.02,
        0.02,
        stats_text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="none"),
    )
    return summary


def _render_drone_polygon_overlay(
    ax: Axes,
    raster_img: Path,
    polygon_path: Path | None,
) -> str | None:
    ax.set_title("Polygon Overlay On Corrected Raster")

    if polygon_path is None:
        ax.text(0.5, 0.5, "No polygon path provided", ha="center", va="center", transform=ax.transAxes)
        return None

    try:
        geopandas = __import__("geopandas")
        rasterio = __import__("rasterio")

        polygons = geopandas.read_file(polygon_path)
        if polygons.empty:
            ax.text(0.5, 0.5, "Polygon file is empty", ha="center", va="center", transform=ax.transAxes)
            return "empty"

        with rasterio.open(raster_img) as src:
            dataset_crs = src.crs
            bounds = src.bounds

        if polygons.crs is None and dataset_crs is not None:
            polygons = polygons.set_crs(dataset_crs)
        elif dataset_crs is not None and polygons.crs != dataset_crs:
            polygons = polygons.to_crs(dataset_crs)

        ax.clear()
        minx, miny, maxx, maxy = (
            float(bounds.left),
            float(bounds.bottom),
            float(bounds.right),
            float(bounds.top),
        )
        width = max(maxx - minx, 1.0)
        height = max(maxy - miny, 1.0)
        pad_x = width * 0.05
        pad_y = height * 0.05
        ax.add_patch(
            Rectangle(
                (minx, miny),
                width,
                height,
                fill=False,
                linewidth=2.0,
                edgecolor="tab:blue",
                label="raster bounds",
            )
        )
        polygons.boundary.plot(ax=ax, color="tab:orange", linewidth=1.0, label="polygons")
        ax.set_xlim(minx - pad_x, maxx + pad_x)
        ax.set_ylim(miny - pad_y, maxy + pad_y)
        ax.set_aspect("equal", adjustable="box")
        if hasattr(ax, "set_box_aspect"):
            ax.set_box_aspect(1)
        ax.legend(loc="best")
        ax.set_title("Drone Overlay Debug")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        return None
    except Exception as exc:
        ax.text(
            0.5,
            0.5,
            f"Polygon overlay unavailable\n{type(exc).__name__}: {exc}",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        return str(exc)


def _render_drone_merged_preview(
    ax: Axes,
    merged_path: Path | None,
    base_name: str,
    qa_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ax.axis("off")
    ax.set_title("Merged Polygon Parquet Preview")

    summary: dict[str, Any] = {
        "path": str(merged_path) if merged_path is not None else None,
        "rows_total": 0,
        "rows_previewed": 0,
        "columns_previewed": [],
        "filter_applied": None,
    }
    if merged_path is None or not merged_path.exists():
        status = str((qa_summary or {}).get("status") or "")
        if status == "success_qa_only_no_polygon_overlap":
            message = "QA generated; no merged parquet available because polygon extraction did not run"
        elif status == "success_qa_only_no_polygons":
            message = "QA generated; no merged parquet available because no polygons were provided"
        else:
            message = "No merged parquet available"
        ax.text(0.5, 0.5, message, ha="center", va="center", transform=ax.transAxes)
        return summary
    if pd is None:
        ax.text(0.5, 0.5, "Pandas required for merged preview", ha="center", va="center", transform=ax.transAxes)
        return summary

    try:
        df = pd.read_parquet(merged_path)
        summary["rows_total"] = int(len(df))
        filtered = df
        if "flight_id" in df.columns:
            filtered = df[df["flight_id"].astype(str) == str(base_name)]
            summary["filter_applied"] = f"flight_id == {base_name}"
        elif "base_name" in df.columns:
            filtered = df[df["base_name"].astype(str) == str(base_name)]
            summary["filter_applied"] = f"base_name == {base_name}"

        # Prefer preview rows that contain actual spectral data rather than rows
        # whose numeric payload is entirely no-data. Without this, the QA table can
        # misleadingly look like the whole polygon extraction failed even when the
        # parquet also contains valid rows further down.
        numeric_exclude = {
            "pixel_id",
            "row",
            "col",
            "x",
            "y",
            "lon",
            "lat",
            "epsg",
            "polygon_id",
        }
        numeric_cols = [
            col
            for col in filtered.columns
            if col not in numeric_exclude and pd.api.types.is_numeric_dtype(filtered[col])
        ]
        if len(numeric_cols) >= 3:
            numeric_block = filtered.loc[:, numeric_cols]
            nodata_like = (numeric_block <= -9990.0) | numeric_block.isna()
            usable_rows = ~nodata_like.all(axis=1)
            if usable_rows.any():
                filtered = filtered.loc[usable_rows]
                suffix = "non-nodata spectral rows"
                if summary["filter_applied"]:
                    summary["filter_applied"] = f"{summary['filter_applied']}; {suffix}"
                else:
                    summary["filter_applied"] = suffix

        preview = filtered.head(5)
        anchor_cols = [
            col
            for col in ("pixel_id", "row", "col", "x", "y")
            if col in preview.columns
        ]
        rightmost_cols = [
            col for col in reversed(list(preview.columns)) if col not in anchor_cols
        ]
        display_cols = anchor_cols[:4]
        for col in rightmost_cols:
            if len(display_cols) >= 10:
                break
            display_cols.append(col)
        display_cols = [col for col in preview.columns if col in display_cols]
        summary["rows_previewed"] = int(len(preview))
        summary["columns_previewed"] = display_cols
        if preview.empty:
            ax.text(0.5, 0.5, "Merged parquet exists but no rows matched this flight", ha="center", va="center", transform=ax.transAxes)
            return summary

        preview = preview.loc[:, display_cols].copy()
        for col in preview.columns:
            preview[col] = preview[col].map(
                lambda value: f"{value:.4g}" if isinstance(value, (int, float, np.floating, np.integer)) else str(value)
            )

        table = ax.table(
            cellText=preview.values,
            colLabels=preview.columns,
            loc="center",
            cellLoc="left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(6)
        table.scale(1.15, 1.15)
        ax.text(
            0.01,
            0.99,
            f"Rows total: {len(df)}\nRows shown: {len(preview)}\nCols shown: {len(display_cols)}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
        )
        return summary
    except Exception as exc:
        ax.text(
            0.5,
            0.5,
            f"Merged preview unavailable\n{type(exc).__name__}: {exc}",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        summary["error"] = str(exc)
        return summary


def render_drone_panel(
    *,
    raw_path: Path,
    corrected_path: Path,
    output_png: Path,
    band_map: dict[str, dict[str, float | int]] | None = None,
    polygon_path: Path | None = None,
    merged_path: Path | None = None,
    qa_summary: dict[str, Any] | None = None,
    save_json: bool = True,
    rgb_bands: str | None = None,
    qa_max_samples: int = _DRONE_QA_MAX_SAMPLES,
) -> tuple[Path, dict[str, Any]]:
    raw_path = Path(raw_path)
    corrected_path = Path(corrected_path)
    output_png = Path(output_png)

    raw_hdr = hdr_to_dict(raw_path.with_suffix(".hdr"))
    corr_hdr = hdr_to_dict(corrected_path.with_suffix(".hdr"))
    raw_cube = read_envi_cube(raw_path, raw_hdr)
    corr_cube = read_envi_cube(corrected_path, corr_hdr)
    if raw_cube.shape != corr_cube.shape:
        raise ValueError("Drone raw and corrected cubes must share shape for QA")

    rgb_targets = _rgb_targets_from_arg(rgb_bands)
    wavelengths, wavelength_source = wavelengths_from_hdr(corr_hdr)
    nodata_value = corr_hdr.get("data ignore value")
    if nodata_value is None:
        nodata_value = raw_hdr.get("data ignore value")
    if nodata_value is None and qa_summary is not None:
        nodata_value = qa_summary.get("metadata", {}).get("nodata")
    try:
        nodata_value = float(nodata_value) if nodata_value is not None else -9999.0
    except (TypeError, ValueError):
        nodata_value = -9999.0

    raw_nodata = _nodata_mask(raw_cube, nodata_value)
    corr_nodata = _nodata_mask(corr_cube, nodata_value)
    raw_valid = _cube_valid_mask(raw_cube, nodata_value)
    corr_valid = _cube_valid_mask(corr_cube, nodata_value)
    both_valid = raw_valid & corr_valid

    raw_nodata_fraction = raw_nodata.mean(axis=0) * 100.0
    corr_nodata_fraction = corr_nodata.mean(axis=0) * 100.0
    raw_spectrum = _median_spectrum(raw_cube, both_valid)
    corr_spectrum = _median_spectrum(corr_cube, both_valid)
    full_diff = np.where(both_valid, corr_cube - raw_cube, np.nan)
    max_samples = min(max(1, int(qa_max_samples)), raw_cube.shape[1] * raw_cube.shape[2])
    corr_sample, sample_mask, sampling_diagnostics = _deterministic_drone_valid_sample(
        corr_cube,
        both_valid,
        max_samples,
    )
    raw_sample, _, _ = _deterministic_drone_valid_sample(
        raw_cube,
        both_valid,
        max_samples,
    )
    scene_id = raw_path.stem.replace("__envi", "")
    sample_valid_counts = np.sum(sample_mask, axis=1).astype(int)
    debug_sampling = _drone_sampling_debug(
        scene_id=scene_id,
        wavelengths=wavelengths,
        raw_cube=raw_cube,
        corr_cube=corr_cube,
        raw_valid=raw_valid,
        corr_valid=corr_valid,
        both_valid=both_valid,
        raw_sample=raw_sample,
        corr_sample=corr_sample,
        sample_mask=sample_mask,
        sampling_diagnostics=sampling_diagnostics,
    )
    _log_drone_sampling_debug(debug_sampling, sample_valid_counts)
    correction_report = _correction_report(raw_sample, corr_sample, sample_mask)
    rgb_image, rgb_indices = _rgb_preview(raw_cube, wavelengths, rgb_targets)
    header_report = _header_report(corr_hdr, wavelengths, wavelength_source)
    provenance_inputs = [raw_path, corrected_path]
    if merged_path is not None and Path(merged_path).exists():
        provenance_inputs.append(Path(merged_path))
    provenance = _provenance(scene_id, provenance_inputs)

    fig, axes = plt.subplots(4, 2, figsize=(14, 18))
    fig.suptitle(f"Drone QA – {raw_path.stem.replace('__envi', '')}")

    axes[0, 0].imshow(np.clip(rgb_image, 0, 1))
    axes[0, 0].set_title(
        f"Raw Reflectance RGB Preview (bands {rgb_indices[0]+1}/{rgb_indices[1]+1}/{rgb_indices[2]+1})"
    )
    axes[0, 0].axis("off")
    axes[0, 0].text(
        0.02,
        0.02,
        f"Bands: {header_report.n_bands}\nWavelength range: {header_report.first_nm} - {header_report.last_nm} nm\nSource: {header_report.wavelength_source}",
        transform=axes[0, 0].transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8, edgecolor="none"),
    )

    _render_drone_band_fidelity(
        axes[0, 1],
        wavelengths,
        raw_spectrum,
        corr_spectrum,
        band_map,
        raw_sample=raw_sample,
        corr_sample=corr_sample,
        sample_mask=sample_mask,
    )
    _render_delta(
        axes[1, 0],
        wavelengths,
        correction_report,
        sample_valid_counts=sample_valid_counts,
        scene_classification=debug_sampling.get("scene_classification", []),
    )
    spatial_correction_summary = _render_drone_correction_magnitude(
        axes[1, 1], full_diff, debug_sampling
    )
    correction_status = _drone_correction_status(
        qa_summary,
        correction_median=spatial_correction_summary["spatial_abs_delta_median"],
        correction_max=spatial_correction_summary["spatial_abs_delta_max"],
        scene_debug=debug_sampling,
    )
    _render_drone_correction_status_box(axes[0, 1], correction_status)
    polygon_warning = _render_drone_polygon_overlay(axes[2, 0], corrected_path, polygon_path)
    merged_preview = _render_drone_merged_preview(
        axes[2, 1],
        Path(merged_path) if merged_path is not None else None,
        raw_path.stem.replace("__envi", ""),
        qa_summary=qa_summary,
    )
    _render_drone_nodata_map(
        axes[3, 0],
        raw_nodata_fraction,
        "Raw Invalid / NoData Band Fraction",
    )
    _render_drone_nodata_map(
        axes[3, 1],
        corr_nodata_fraction,
        "Corrected Invalid / NoData Band Fraction",
    )

    for ax in axes.flat:
        if ax not in {axes[0, 0], axes[2, 0], axes[2, 1], axes[3, 0], axes[3, 1], axes[1, 1]}:
            ax.grid(True, alpha=0.2)

    nodata_summary = {
        "nodata_value": nodata_value,
        "raw_nodata_pct": float(np.mean(raw_nodata) * 100.0),
        "corrected_nodata_pct": float(np.mean(corr_nodata) * 100.0),
    }
    qa_payload: dict[str, Any] = {
        "platform": "drone",
        "provenance": {
            "flightline_id": provenance.flightline_id,
            "created_utc": provenance.created_utc,
            "package_version": provenance.package_version,
            "git_sha": provenance.git_sha,
            "input_hashes": provenance.input_hashes,
        },
        "header": {
            "n_bands": header_report.n_bands,
            "wavelength_source": header_report.wavelength_source,
            "first_nm": header_report.first_nm,
            "last_nm": header_report.last_nm,
            "wavelengths_monotonic": header_report.wavelengths_monotonic,
        },
        "band_map": band_map or {},
        "nodata": nodata_summary,
        "debug_sampling": debug_sampling,
        "correction": {
            "delta_median": correction_report.delta_median,
            "delta_iqr": correction_report.delta_iqr,
            "delta_q10": correction_report.delta_q10,
            "delta_q25": correction_report.delta_q25,
            "delta_q75": correction_report.delta_q75,
            "delta_q90": correction_report.delta_q90,
            "delta_abs_median": correction_report.delta_abs_median,
            "largest_delta_indices": correction_report.largest_delta_indices,
            **spatial_correction_summary,
            "global_mean_abs_diff": debug_sampling["global_mean_abs_diff"],
            "global_median_abs_diff": debug_sampling["global_median_abs_diff"],
            "global_p95_abs_diff": debug_sampling["global_p95_abs_diff"],
            "global_max_abs_diff": debug_sampling["global_max_abs_diff"],
            "fraction_above_change_threshold": debug_sampling["fraction_above_change_threshold"],
            "pixels_with_any_nontrivial_change_pct": debug_sampling["pixels_with_any_nontrivial_change_pct"],
            "n_abs_diff_gt_1": debug_sampling["n_abs_diff_gt_1"],
            "n_abs_diff_gt_10": debug_sampling["n_abs_diff_gt_10"],
            "n_abs_diff_gt_100": debug_sampling["n_abs_diff_gt_100"],
            "bands_with_any_support": debug_sampling["bands_with_any_support"],
            "bands_with_gt10_support": debug_sampling["bands_with_gt10_support"],
            "bands_with_gt100_support": debug_sampling["bands_with_gt100_support"],
            "sample_valid_counts_summary": debug_sampling["sample_valid_counts_summary"],
            "scene_classification": debug_sampling["scene_classification"],
            "topo_requested": correction_status["topo_requested"],
            "brdf_requested": correction_status["brdf_requested"],
            "topo_applied": correction_status["topo_applied"],
            "brdf_applied": correction_status["brdf_applied"],
            "reused_existing_corrected": correction_status["reused_existing_corrected"],
            "correction_failed": correction_status["correction_failed"],
            "status_source": correction_status["status_source"],
            "observed_change": correction_status["observed_change"],
            "observed_change_threshold": correction_status["observed_change_threshold"],
            "change_threshold": debug_sampling["change_threshold"],
        },
        "polygon": {
            "path": str(polygon_path) if polygon_path is not None else None,
            "warning": polygon_warning,
        },
        "merged_preview": merged_preview,
        "audit": qa_summary or {},
    }

    footer = (
        f"Drone QA | UTC: {provenance.created_utc} | Package: {provenance.package_version} | "
        f"Git: {provenance.git_sha}"
    )
    fig.text(0.01, 0.01, footer, ha="left", va="bottom", fontsize=8)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=200, bbox_inches="tight")
    plt.close(fig)

    if save_json:
        output_png.with_suffix(".json").write_text(
            json.dumps(qa_payload, indent=2), encoding="utf-8"
        )

    return output_png, qa_payload


def render_flightline_panel(
    flightline_dir: Path,
    quick: bool = False,
    save_json: bool = True,
    n_sample: int = 100_000,
    rgb_bands: str | None = None,
) -> tuple[Path, dict]:
    """Return (png_path, metrics_dict); also writes _qa.json/_qa.pdf when requested."""
    
    # Debug: Print which file is being used and version identifier
    import inspect
    import os
    try:
        current_file = inspect.getfile(render_flightline_panel)
        print(f"[QA] 📍 QA plots module file: {current_file}")
        print("[QA] ✅ QA plots version: 2025-01-20-v2 (includes Page 4: Parquet & Merge Quality)")
        
        # Verify file modification time
        if os.path.exists(current_file):
            mtime = os.path.getmtime(current_file)
            import datetime
            mod_time = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"[QA] 📅 File modification time: {mod_time}")
        
        # Verify Page 4 function exists
        if '_render_page4_parquet_merge_quality' in globals():
            print("[QA] ✅ Page 4 function found in module")
        else:
            print("[QA] ❌ WARNING: Page 4 function NOT found in module!")
    except Exception as e:
        print(f"[QA] ⚠️  Could not inspect module file: {e}")
    
    flightline_dir = Path(flightline_dir)
    raw_path, corr_path = _discover_primary_cube(flightline_dir)
    prefix = _flightline_prefix(raw_path)
    
    # Check if header files exist before trying to read them
    raw_hdr_path = raw_path.with_suffix(".hdr")
    corr_hdr_path = corr_path.with_suffix(".hdr")
    
    if not raw_hdr_path.exists():
        raise FileNotFoundError(
            f"Missing raw ENVI header: {raw_hdr_path}\n"
            f"Raw ENVI image exists at: {raw_path}\n"
            f"Flightline directory: {flightline_dir}"
        )
    if not corr_hdr_path.exists():
        raise FileNotFoundError(
            f"Missing corrected ENVI header: {corr_hdr_path}\n"
            f"Corrected ENVI image exists at: {corr_path}\n"
            f"Flightline directory: {flightline_dir}"
        )
    
    raw_hdr = hdr_to_dict(raw_hdr_path)
    corr_hdr = hdr_to_dict(corr_hdr_path)
    raw_cube = read_envi_cube(raw_path, raw_hdr)
    corr_cube = read_envi_cube(corr_path, corr_hdr)
    if raw_cube.shape != corr_cube.shape:
        raise ValueError("Raw and corrected cubes must share shape for QA panel")

    rgb_targets = _rgb_targets_from_arg(rgb_bands)

    wavelengths, wavelength_source = wavelengths_from_hdr(corr_hdr)
    header_report = _header_report(corr_hdr, wavelengths, wavelength_source)

    valid_mask = np.isfinite(corr_cube)
    mask_report = MaskReport(
        n_total=int(valid_mask.size),
        n_valid=int(np.count_nonzero(valid_mask)),
        valid_pct=float(100.0 * np.count_nonzero(valid_mask) / valid_mask.size if valid_mask.size else 0.0),
    )

    max_samples = min(n_sample, 25_000 if quick else n_sample)
    corr_sample, sample_mask = _deterministic_sample(corr_cube, valid_mask, max_samples)
    raw_sample, _ = _deterministic_sample(raw_cube, valid_mask, max_samples)

    correction_report = _correction_report(raw_sample, corr_sample, sample_mask)

    negatives_pct = float(
        100.0
        * np.count_nonzero((corr_cube < 0) & valid_mask)
        / mask_report.n_valid
        if mask_report.n_valid
        else 0.0
    )

    issues: list[str] = []
    if header_report.keys_missing:
        issues.append(f"Header missing: {', '.join(header_report.keys_missing)}")
    if header_report.wavelengths_monotonic is False:
        issues.append("Wavelengths not strictly increasing")
    if wavelength_source == "sensor_default":
        issues.append("Wavelengths missing from header – using sensor defaults")
    elif wavelength_source == "absent":
        issues.append("Wavelength metadata absent from header")
    if negatives_pct > _NEGATIVE_WARN_THRESHOLD:
        issues.append(f"{negatives_pct:.2f}% negative pixels")
    overbright_pct = float(
        100.0
        * np.count_nonzero((corr_cube > 1.2) & valid_mask)
        / mask_report.n_valid
        if mask_report.n_valid
        else 0.0
    )
    if overbright_pct > _OVERBRIGHT_WARN_THRESHOLD:
        issues.append(f"{overbright_pct:.2f}% pixels > 1.2 reflectance")
    if any(abs(val) > _DELTA_WARN_THRESHOLD for val in correction_report.delta_median):
        issues.append("Large correction deltas detected")

    conv_reports, scatter_data, brightness_map = _convolution_reports(
        flightline_dir, prefix, corr_cube, sample_mask
    )
    # Fallback: polygon mode often doesn't have convolved ENVI cubes on disk.
    # If we have sensor band columns in the merged parquet, build the scatter from there.
    if not scatter_data:
        scatter_data = _scatter_from_merged_parquet(flightline_dir, prefix)

    brightness_summary = _build_brightness_summary_table(brightness_map)

    provenance = _provenance(prefix, [raw_path, corr_path])

    metrics = QAMetrics(
        provenance=provenance,
        header=header_report,
        mask=mask_report,
        correction=correction_report,
        convolution=conv_reports,
        negatives_pct=negatives_pct,
        overbright_pct=overbright_pct,
        issues=issues,
        brightness_coefficients=brightness_map,
        brightness_summary=brightness_summary,
    )

    raw_rgb_image, raw_rgb_indices = _rgb_preview(raw_cube, wavelengths, rgb_targets)
    corr_rgb_image, corr_rgb_indices = _rgb_preview(corr_cube, wavelengths, rgb_targets)

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(f"QA panel – {prefix}")

    ax_raw_rgb = axes[0, 0]
    ax_raw_rgb.imshow(np.clip(raw_rgb_image, 0, 1))
    ax_raw_rgb.set_title(
        f"Original ENVI RGB (bands {raw_rgb_indices[0]+1}/{raw_rgb_indices[1]+1}/{raw_rgb_indices[2]+1})"
    )
    ax_raw_rgb.axis("off")

    ax_corr_rgb = axes[0, 1]
    ax_corr_rgb.imshow(np.clip(corr_rgb_image, 0, 1))
    ax_corr_rgb.set_title(
        f"Corrected ENVI RGB (bands {corr_rgb_indices[0]+1}/{corr_rgb_indices[1]+1}/{corr_rgb_indices[2]+1})"
    )
    ax_corr_rgb.axis("off")

    _render_hist(axes[0, 2], raw_sample, corr_sample, sample_mask)
    _render_delta(axes[1, 0], wavelengths, correction_report)
    _render_scatter(axes[1, 1], scatter_data)
    _render_aop_qa_summary(axes[1, 2], metrics)

    for ax in axes.flat:
        if ax not in {ax_raw_rgb, ax_corr_rgb, axes[1, 2]}:
            ax.grid(True, alpha=0.2)

    _render_footer(fig, metrics)

    png_path = flightline_dir / f"{prefix}_qa.png"
    fig.savefig(png_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    metrics_dict_full = json.loads(metrics.to_json())
    core_keys = [
        "provenance",
        "header",
        "mask",
        "correction",
        "convolution",
        "negatives_pct",
        "overbright_pct",
        "issues",
    ]
    metrics_dict = {key: metrics_dict_full[key] for key in core_keys}

    if save_json:
        json_path = flightline_dir / f"{prefix}_qa.json"
        write_json(metrics, json_path)

    pdf_path = flightline_dir / f"{prefix}_qa.pdf"
    print(f"[QA] 📄 Generating QA PDF with 4 pages: {pdf_path.name}")
    with PdfPages(pdf_path) as pdf:
        print("[QA]   📑 Rendering Page 1: ENVI overview...")
        _render_page1_envi_overview(pdf, flightline_dir, prefix, rgb_targets)
        
        # Load filtered parquet statistics if available
        print("[QA]   📊 Loading filtered parquet statistics...")
        filtered_stats = _load_filtered_parquet_stats(flightline_dir, prefix)
        if filtered_stats:
            print(f"[QA]     ✅ Found filtered stats: {filtered_stats['n_rows']:,} rows")
        else:
            print("[QA]     ⚠️  No filtered parquet stats available")
        
        print("[QA]   📑 Rendering Page 2: Topographic + BRDF diagnostics...")
        _render_page2_topo_brdf(
            pdf=pdf,
            prefix=prefix,
            wavelengths=wavelengths,
            correction_report=correction_report,
            raw_sample=raw_sample,
            corr_sample=corr_sample,
            sample_mask=sample_mask,
            corr_path=corr_path,
            filtered_stats=filtered_stats,
        )
        print("[QA]   📑 Rendering Page 3: Additional QA diagnostics...")
        _render_page3_remaining(
            pdf=pdf,
            prefix=prefix,
            metrics=metrics,
            scatter_data=scatter_data,
            filtered_stats=filtered_stats,
            flightline_dir=flightline_dir,
            wavelengths=wavelengths,
        )
        
        # Add Page 4: Parquet and merge quality
        print("[QA]   📑 Rendering Page 4: Parquet & Merge Quality Analysis...")
        try:
            _render_page4_parquet_merge_quality(
                pdf=pdf,
                flightline_dir=flightline_dir,
                prefix=prefix,
            )
            print("[QA]   ✅ Page 4 rendered successfully")
        except Exception as e:
            print(f"[QA]   ❌ ERROR rendering Page 4: {e}")
            import traceback
            traceback.print_exc()
            # Continue anyway - 3 pages is still useful
    
    # Verify PDF was created and count pages
    try:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
            print(f"[QA] ✅ QA PDF complete: {pdf_path.name} ({num_pages} pages)")
            if num_pages < 4:
                print(f"[QA] ⚠️  WARNING: Expected 4 pages but PDF has {num_pages} pages!")
                print("[QA]     This may indicate the old code is still being used.")
            elif num_pages == 4:
                print("[QA] ✅ PDF has 4 pages as expected!")
        except ImportError:
            print(f"[QA] ✅ QA PDF complete: {pdf_path.name} (PyPDF2 not available to verify page count)")
    except Exception as e:
        print(f"[QA] ✅ QA PDF complete: {pdf_path.name} (could not verify page count: {e})")

    return png_path, metrics_dict


__all__ = ["render_flightline_panel", "render_drone_panel"]
