from __future__ import annotations

import inspect
import json
import logging
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import duckdb
import h5py
import numpy as np
import pandas as pd

from spectralbridge.corrections import (
    HYTOOLS_BRDF_KERNEL_CONFIG,
    NDVIBinningConfig,
    apply_brdf_correct,
    apply_topo_correct,
    fit_and_save_brdf_model,
)
from spectralbridge.envi_writer import EnviWriter
from spectralbridge.neon_cube import NeonCube
from spectralbridge.polygons import (
    _describe_parquet_columns,
    _quote_identifier,
    _quote_path,
    _write_dataframe_parquet,
    extract_polygon_parquet_from_envi,
    validate_coordinate_match,
)
from spectralbridge.progress_utils import TileProgressReporter
from spectralbridge.utils.paths import get_package_data_path
from spectralbridge.utils_checks import is_valid_envi_pair

from cross_sensor_cal.exports.schema_utils import ensure_coord_columns

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - tqdm is optional in minimal environments
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover - fallback handled locally
    tqdm = None

DRONE_TARGET_BANDS: dict[str, int] = {
    "blue": 444,
    "green": 560,
    "red": 650,
    "nir": 862,
}

_RECOGNISED_NODATA_ATTRS = (
    "Data_Ignore_Value",
    "_FillValue",
    "NoData",
    "no_data",
)
_DRONE_NODATA_PATCH_ATTRS = (
    "Data_Ignore_Value",
    "_FillValue",
    "NoData",
    "NoDataValue",
    "nodata",
    "no_data",
    "missing_value",
    "fill_value",
)
_DRONE_FALLBACK_NODATA = np.float32(-9999.0)
_DRONE_PACKAGE_DATE_RE = re.compile(r"(?P<month>\d{2})-(?P<day>\d{2})-(?P<year>\d{2})")
_DRONE_TIFF_DEFAULT_WAVELENGTHS_NM = (
    444.0,
    475.0,
    531.0,
    560.0,
    650.0,
    668.0,
    705.0,
    717.0,
    740.0,
    862.0,
)
_DRONE_TIFF_DEFAULT_FWHM_NM = (
    28.0,
    32.0,
    14.0,
    27.0,
    16.0,
    14.0,
    10.0,
    12.0,
    18.0,
    57.0,
)
_DRONE_TIFF_ANCILLARY_KEYWORDS = {
    "slope": (("slope",),),
    "aspect": (("aspect",),),
    "sensor_zenith": (("sensor", "zenith"), ("view", "zenith")),
    "sensor_azimuth": (("sensor", "azimuth"), ("view", "azimuth")),
    "solar_zenith": (("solar", "zenith"), ("sun", "zenith")),
    "solar_azimuth": (("solar", "azimuth"), ("sun", "azimuth")),
}
_DRONE_STATUS_SUCCESS_EXTRACTED = "success_extracted"
_DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP = "success_qa_only_no_polygon_overlap"
_DRONE_STATUS_SUCCESS_QA_ONLY_NO_POLYGONS = "success_qa_only_no_polygons"
_DRONE_STATUS_FAILED_OTHER = "failed_other"
_DRONE_NO_OVERLAP_REASONS = (
    "No pixels intersected the supplied polygons",
    "zero intersected pixels",
)
_ANSI_RESET = "\033[0m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_RED = "\033[31m"
_DRONE_MANIFEST_ID_COLUMN = "Plot"
_DRONE_MANIFEST_DATE_COLUMN = "Day of data collection"
_DRONE_MANIFEST_TIME_COLUMN = "Mean Time of data collection (24 hr clock)"
_DRONE_DEFAULT_MANIFEST_FILENAME = "drone_field_manifest.csv"
_DRONE_DEFAULT_MANIFEST_ALIASES = {
    _DRONE_DEFAULT_MANIFEST_FILENAME,
    "Drone Field Data Macrosystems - UAS Data Processing For Extraction.csv",
}
_DRONE_SUPPORTED_INPUT_EXTENSIONS = (".h5", ".tif", ".tiff")
_DRONE_SOLAR_GEOMETRY_ATTRS = (
    "solar_geometry_source",
    "acquisition_datetime_used",
    "solar_zenith_mean",
    "solar_zenith_min",
    "solar_zenith_max",
    "solar_azimuth_mean",
    "solar_azimuth_min",
    "solar_azimuth_max",
)


class DroneCorrectionUnavailableError(RuntimeError):
    """Raised when a requested drone correction cannot produce a valid output."""

    def __init__(self, message: str, audit: dict[str, Any]):
        super().__init__(message)
        self.audit = dict(audit)


@dataclass(frozen=True)
class DroneInputSource:
    source_path: Path
    source_type: str
    flight_stem: str


def _normalise_drone_manifest_id(value: Any) -> str:
    """Normalize manifest/package identifiers for tolerant flight matching."""

    if value is None or pd.isna(value):
        return ""
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip().upper())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized


def _compact_drone_manifest_id(value: str) -> str:
    """Return an alphanumeric-only key for separator-tolerant matching."""

    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def _strip_trailing_manifest_date(value: str) -> str:
    """Remove a trailing date token used in derived drone flight stems."""

    return re.sub(r"[_-]?\d{8}$", "", value).strip("_-")


def _find_manifest_column(columns: Sequence[str], expected: str) -> str | None:
    expected_norm = re.sub(r"[^a-z0-9]+", "", expected.lower())
    for column in columns:
        column_norm = re.sub(r"[^a-z0-9]+", "", str(column).lower())
        if column_norm == expected_norm:
            return str(column)
    return None


def load_drone_manifest(manifest_path: str | Path) -> dict[str, datetime]:
    """Load drone flight acquisition datetimes from a CSV manifest.

    The manifest is expected to include ``Plot``, ``Day of data collection``,
    and ``Mean Time of data collection (24 hr clock)`` columns. Flight
    identifiers are normalized to uppercase underscore-separated tokens such as
    ``AOP_GOLDHILL``. Rows with missing identifiers or malformed datetimes are
    skipped with warnings so a partially messy field manifest can still support
    valid flights.
    """

    manifest_path = Path(manifest_path)
    frame = pd.read_csv(manifest_path)
    plot_col = _find_manifest_column(frame.columns, _DRONE_MANIFEST_ID_COLUMN)
    date_col = _find_manifest_column(frame.columns, _DRONE_MANIFEST_DATE_COLUMN)
    time_col = _find_manifest_column(frame.columns, _DRONE_MANIFEST_TIME_COLUMN)
    missing = [
        label
        for label, column in (
            (_DRONE_MANIFEST_ID_COLUMN, plot_col),
            (_DRONE_MANIFEST_DATE_COLUMN, date_col),
            (_DRONE_MANIFEST_TIME_COLUMN, time_col),
        )
        if column is None
    ]
    if missing:
        raise ValueError(
            "Drone manifest is missing required column(s): "
            + ", ".join(missing)
            + f" in {manifest_path}"
        )

    manifest: dict[str, datetime] = {}
    for row_number, row in frame.iterrows():
        flight_id = _normalise_drone_manifest_id(row.get(plot_col))
        if not flight_id:
            LOGGER.warning(
                "[drone] Skipping manifest row %s with missing Plot value in %s",
                row_number + 2,
                manifest_path,
            )
            continue

        date_value = str(row.get(date_col, "")).strip()
        time_value = str(row.get(time_col, "")).strip()
        parsed = pd.to_datetime(
            f"{date_value} {time_value}",
            errors="coerce",
        )
        if pd.isna(parsed):
            LOGGER.warning(
                "[drone] Skipping manifest row %s for %s with malformed "
                "acquisition datetime: %r %r",
                row_number + 2,
                flight_id,
                date_value,
                time_value,
            )
            continue

        acquisition_datetime = parsed.to_pydatetime()
        if flight_id in manifest:
            LOGGER.warning(
                "[drone] Duplicate manifest flight id %s in %s; keeping the first datetime %s",
                flight_id,
                manifest_path,
                manifest[flight_id].isoformat(),
            )
            continue
        manifest[flight_id] = acquisition_datetime

    return manifest


def _resolve_drone_manifest_path(
    manifest_path: str | Path | None,
    *,
    input_path: str | Path,
) -> Path:
    """Resolve a drone manifest path with notebook-friendly relative fallbacks."""

    bundled_manifest = get_package_data_path(_DRONE_DEFAULT_MANIFEST_FILENAME)
    if manifest_path is None:
        return bundled_manifest

    requested = Path(manifest_path)
    input_path = Path(input_path)
    if requested.is_absolute():
        candidates = [requested]
    else:
        cwd = Path.cwd()
        input_candidates = (
            [input_path, cwd / input_path]
            if not input_path.is_absolute()
            else [input_path]
        )
        input_bases: list[Path] = []
        for candidate in input_candidates:
            input_bases.append(candidate)
            input_bases.append(candidate.parent)
        candidates = [cwd / requested, requested]
        for base in input_bases:
            candidates.append(base / requested)
        if requested.name in _DRONE_DEFAULT_MANIFEST_ALIASES:
            candidates.append(bundled_manifest)

    checked: list[Path] = []
    for candidate in candidates:
        candidate = candidate.expanduser()
        if candidate in checked:
            continue
        checked.append(candidate)
        if candidate.exists():
            return candidate.resolve()

    checked_text = "\n".join(f"  - {path}" for path in checked)
    raise FileNotFoundError(
        "Drone manifest CSV not found. Pass an absolute path or place/upload "
        "the manifest into the notebook working directory or drone input "
        f"folder.\nRequested: {manifest_path}\nChecked:\n{checked_text}"
    )


def lookup_flight_datetime(
    flight_id: str,
    manifest: dict[str, datetime] | None,
) -> datetime | None:
    """Return a manifest datetime for a derived drone flight identifier.

    Matching rules are deliberately conservative and deterministic:

    - identifiers are compared after uppercasing and collapsing separators to
      underscores;
    - an exact match wins first;
    - a trailing ``YYYYMMDD`` token is ignored, so ``AOP_GOLDHILL_20230814``
      matches manifest row ``AOP_GOLDHILL``;
    - if needed, separators are ignored for compact matching, so ``SPR1``
      matches manifest row ``SPR-1``;
    - if neither rule matches, the longest manifest key that prefixes the
      derived flight stem wins.
    """

    if not manifest:
        return None

    normalized = _normalise_drone_manifest_id(flight_id)
    if normalized in manifest:
        return manifest[normalized]

    without_date = _strip_trailing_manifest_date(normalized)
    if without_date in manifest:
        return manifest[without_date]

    compact_without_date = _compact_drone_manifest_id(without_date)
    for candidate, acquisition_datetime in sorted(
        manifest.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        if compact_without_date == _compact_drone_manifest_id(candidate):
            return acquisition_datetime

    for candidate in sorted(manifest, key=len, reverse=True):
        if normalized.startswith(f"{candidate}_"):
            return manifest[candidate]
    return None


def clean_name(name: str) -> str:
    """Normalise a source name minimally for filesystem-safe output filenames."""

    safe = "".join(
        ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(name)
    )
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("._") or "drone"


def _drone_package_dir(h5_path: str | Path) -> Path:
    """Return the nearest drone export package folder, or the direct parent."""

    path = Path(h5_path)
    for parent in path.parents:
        if "exportpackage" in parent.name.lower():
            return parent
    return path.parent


def derive_drone_flight_stem(h5_path: str | Path) -> str:
    """Derive a drone flight stem from the package folder rather than the inner HDF5."""

    package_name = _drone_package_dir(h5_path).name
    package_core = re.sub(r"(?i)(?:[-_\s]*exportpackage)$", "", package_name).strip(
        "-_ "
    )

    date_match = _DRONE_PACKAGE_DATE_RE.search(package_core)
    if date_match:
        prefix = clean_name(
            package_core[: date_match.start()].strip("-_ ").replace("-", "_")
        )
        date_token = (
            f"20{date_match.group('year')}"
            f"{date_match.group('month')}"
            f"{date_match.group('day')}"
        )
        stem = "_".join(part for part in (prefix, date_token) if part)
        return stem or date_token

    stem = clean_name(package_core.replace("-", "_"))
    return stem or clean_name(package_name.replace("-", "_"))


def build_drone_output_paths(
    output_root: str | Path,
    *,
    flight_stem: str,
) -> dict[str, Path]:
    """Return per-flight drone paths under a dedicated flight directory."""

    flight_dir = Path(output_root) / flight_stem
    return {
        "flight_dir": flight_dir,
        "working_h5": flight_dir / f"{flight_stem}__working.h5",
        "envi_stem": flight_dir / f"{flight_stem}__envi",
        "corrected_stem": flight_dir / f"{flight_stem}__corrected",
        "polygon_parquet": flight_dir / f"{flight_stem}__polygons.parquet",
        "polygon_index": flight_dir / f"{flight_stem}__polygon_index.parquet",
        "overlay_debug_png": flight_dir / f"{flight_stem}__overlay_debug.png",
        "qa_png": flight_dir / f"{flight_stem}__qa.png",
        "qa_json": flight_dir / f"{flight_stem}__qa.json",
    }


def _drone_path_matches_keywords(path: Path, keyword_groups: Sequence[Sequence[str]]) -> bool:
    stem_lower = path.stem.lower()
    return any(all(token in stem_lower for token in group) for group in keyword_groups)


def _is_drone_ancillary_tiff(path: str | Path) -> bool:
    candidate = Path(path)
    return any(
        _drone_path_matches_keywords(candidate, keyword_groups)
        for keyword_groups in _DRONE_TIFF_ANCILLARY_KEYWORDS.values()
    )


def _discover_drone_input_sources(input_path: str | Path) -> list[DroneInputSource]:
    root = Path(input_path)
    if root.is_file():
        candidates = [root]
    elif root.exists():
        tif_candidates = sorted(root.rglob("*.tif")) + sorted(root.rglob("*.tiff"))
        candidates = sorted(root.rglob("*.h5")) + tif_candidates
    else:
        return []

    sources_by_stem: dict[str, DroneInputSource] = {}
    for candidate in candidates:
        suffix = candidate.suffix.lower()
        if suffix == ".h5":
            source_type = "h5"
        elif suffix in {".tif", ".tiff"}:
            if _is_drone_ancillary_tiff(candidate):
                continue
            source_type = "tiff"
        else:
            continue

        flight_stem = derive_drone_flight_stem(candidate)
        existing = sources_by_stem.get(flight_stem)
        if existing is not None:
            if existing.source_type == "h5":
                continue
            if source_type == "h5":
                sources_by_stem[flight_stem] = DroneInputSource(
                    source_path=candidate,
                    source_type=source_type,
                    flight_stem=flight_stem,
                )
                continue
            raise ValueError(
                "Duplicate drone flight stem derived within one run: "
                f"{flight_stem} from {existing.source_path} and {candidate}. "
                "Package-folder naming must remain unique per flight."
            )

        sources_by_stem[flight_stem] = DroneInputSource(
            source_path=candidate,
            source_type=source_type,
            flight_stem=flight_stem,
        )

    return sorted(
        sources_by_stem.values(),
        key=lambda item: (str(_drone_package_dir(item.source_path)), item.source_path.name),
    )


def _find_drone_tiff_ancillary(package_dir: Path, key: str) -> Path | None:
    keyword_groups = _DRONE_TIFF_ANCILLARY_KEYWORDS[key]
    for candidate in sorted(package_dir.glob("*.tif")) + sorted(package_dir.glob("*.tiff")):
        if _drone_path_matches_keywords(candidate, keyword_groups):
            return candidate
    return None


def _normalise_tiff_spectral_vector(
    values: Sequence[float] | np.ndarray | None,
    *,
    field_name: str,
    band_count: int,
    default_values: Sequence[float],
) -> np.ndarray:
    if values is None:
        if band_count != len(default_values):
            raise ValueError(
                f"TIFF source has {band_count} bands but no explicit {field_name} were provided. "
                f"Default {field_name} are only available for {len(default_values)}-band sources."
            )
        values = default_values

    array = np.asarray(values, dtype=np.float32).reshape(-1)
    if array.size != band_count:
        raise ValueError(
            f"TIFF {field_name} length {array.size} does not match reflectance band count {band_count}."
        )
    return array


def _read_drone_tiff_raster(path: str | Path) -> tuple[np.ndarray, str, Any, float | None]:
    try:
        import rasterio
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError(
            "rasterio is required for TIFF-backed drone inputs."
        ) from exc

    with rasterio.open(path) as src:
        data = src.read()
        crs_wkt = src.crs.to_wkt() if src.crs is not None else ""
        transform = src.transform
        nodata = src.nodata
    return np.asarray(data, dtype=np.float32), crs_wkt, transform, nodata


def _validate_drone_tiff_ancillary_alignment(
    reflectance_path: Path,
    reflectance_shape: tuple[int, int],
    reflectance_transform: Any,
    reflectance_crs_wkt: str,
    ancillary_path: Path,
) -> np.ndarray:
    try:
        import rasterio
    except Exception as exc:  # pragma: no cover - optional dependency guard
        raise RuntimeError(
            "rasterio is required for TIFF-backed drone inputs."
        ) from exc

    with rasterio.open(ancillary_path) as src:
        array = src.read(1)
        if array.shape != reflectance_shape:
            raise ValueError(
                f"Ancillary TIFF {ancillary_path} has shape {array.shape} which does not match "
                f"reflectance TIFF {reflectance_path} shape {reflectance_shape}."
            )
        if src.transform != reflectance_transform:
            raise ValueError(
                f"Ancillary TIFF {ancillary_path} transform does not match reflectance TIFF {reflectance_path}."
            )
        ancillary_crs_wkt = src.crs.to_wkt() if src.crs is not None else ""
        if ancillary_crs_wkt != reflectance_crs_wkt:
            raise ValueError(
                f"Ancillary TIFF {ancillary_path} CRS does not match reflectance TIFF {reflectance_path}."
            )
        return np.asarray(array, dtype=np.float32)


def _build_drone_tiff_map_info(transform: Any, crs_wkt: str) -> str:
    xres = abs(float(transform.a))
    yres = abs(float(transform.e))
    ulx = float(transform.c)
    uly = float(transform.f)
    zone = 0
    hemisphere = "North"

    epsg_match = re.search(r"EPSG\",\"(\d+)\"", crs_wkt) or re.search(r"ID\[\"EPSG\",(\d+)\]", crs_wkt)
    if epsg_match:
        epsg = int(epsg_match.group(1))
        if 32601 <= epsg <= 32660:
            zone = epsg - 32600
            hemisphere = "North"
        elif 32701 <= epsg <= 32760:
            zone = epsg - 32700
            hemisphere = "South"

    if zone > 0:
        return (
            f"UTM, 1.000, 1.000, {ulx:.3f}, {uly:.3f}, {xres:.3f}, {yres:.3f}, "
            f"{zone}, {hemisphere}, WGS-84, units=Meters"
        )

    return f"Arbitrary, 1.000, 1.000, {ulx:.3f}, {uly:.3f}, {xres:.3f}, {yres:.3f}"


def _coerce_acquisition_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    parsed = pd.to_datetime(str(value), errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Could not parse acquisition datetime: {value!r}")
    return parsed.to_pydatetime()


def _datetime_to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _drone_pixel_lon_lat(
    *,
    transform: Any,
    crs_wkt: str,
    shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Return per-pixel longitude/latitude arrays from a raster transform/CRS."""

    try:
        import rasterio.transform
        from rasterio.crs import CRS
        from rasterio.warp import transform as warp_transform
    except Exception as exc:  # pragma: no cover - rasterio is a runtime dependency
        raise RuntimeError(
            "rasterio is required to compute manifest-derived drone solar geometry."
        ) from exc

    rows, cols = np.indices(shape, dtype=np.float64)
    xs, ys = rasterio.transform.xy(transform, rows, cols, offset="center")
    x_flat = np.asarray(xs, dtype=np.float64).ravel()
    y_flat = np.asarray(ys, dtype=np.float64).ravel()

    if not crs_wkt:
        raise ValueError(
            "Cannot compute manifest-derived solar geometry because the "
            "reflectance TIFF has no CRS."
        )
    source_crs = CRS.from_wkt(crs_wkt)
    lon_flat, lat_flat = warp_transform(source_crs, "EPSG:4326", x_flat, y_flat)
    lon = np.asarray(lon_flat, dtype=np.float64).reshape(shape)
    lat = np.asarray(lat_flat, dtype=np.float64).reshape(shape)
    return lon, lat


def _compute_solar_geometry_arrays(
    *,
    acquisition_datetime: datetime,
    longitude: np.ndarray,
    latitude: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute approximate solar zenith/azimuth rasters for a UTC acquisition time."""

    dt_utc = _datetime_to_utc_naive(acquisition_datetime)
    day_of_year = dt_utc.timetuple().tm_yday
    fractional_hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3_600_000_000.0
    )
    gamma = 2.0 * np.pi / 365.0 * (day_of_year - 1.0 + (fractional_hour - 12.0) / 24.0)
    declination = (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2.0 * gamma)
        + 0.000907 * np.sin(2.0 * gamma)
        - 0.002697 * np.cos(3.0 * gamma)
        + 0.00148 * np.sin(3.0 * gamma)
    )
    equation_of_time = 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2.0 * gamma)
        - 0.040849 * np.sin(2.0 * gamma)
    )
    minutes_utc = fractional_hour * 60.0
    true_solar_time = (minutes_utc + equation_of_time + 4.0 * longitude) % 1440.0
    hour_angle = np.deg2rad(true_solar_time / 4.0 - 180.0)
    lat_rad = np.deg2rad(latitude)

    cos_zenith = (
        np.sin(lat_rad) * np.sin(declination)
        + np.cos(lat_rad) * np.cos(declination) * np.cos(hour_angle)
    )
    zenith = np.rad2deg(np.arccos(np.clip(cos_zenith, -1.0, 1.0)))
    azimuth = (
        np.rad2deg(
            np.arctan2(
                np.sin(hour_angle),
                np.cos(hour_angle) * np.sin(lat_rad)
                - np.tan(declination) * np.cos(lat_rad),
            )
        )
        + 180.0
    ) % 360.0
    return zenith.astype(np.float32), azimuth.astype(np.float32)


def _solar_geometry_stats(
    solar_zenith: np.ndarray | float,
    solar_azimuth: np.ndarray | float,
) -> dict[str, float]:
    zenith = np.asarray(solar_zenith, dtype=np.float32)
    azimuth = np.asarray(solar_azimuth, dtype=np.float32)
    return {
        "solar_zenith_mean": float(np.nanmean(zenith)),
        "solar_zenith_min": float(np.nanmin(zenith)),
        "solar_zenith_max": float(np.nanmax(zenith)),
        "solar_azimuth_mean": float(np.nanmean(azimuth)),
        "solar_azimuth_min": float(np.nanmin(azimuth)),
        "solar_azimuth_max": float(np.nanmax(azimuth)),
    }


def _write_solar_geometry_attrs(
    metadata_group: h5py.Group,
    *,
    source: str,
    acquisition_datetime: datetime | None,
    solar_zenith: np.ndarray | float,
    solar_azimuth: np.ndarray | float,
) -> None:
    stats = _solar_geometry_stats(solar_zenith, solar_azimuth)
    metadata_group.attrs["solar_geometry_source"] = source
    metadata_group.attrs["acquisition_datetime_used"] = (
        _datetime_to_utc_naive(acquisition_datetime).isoformat()
        if acquisition_datetime is not None
        else ""
    )
    for key, value in stats.items():
        metadata_group.attrs[key] = value


def summarize_drone_h5_solar_geometry(h5_path: str | Path) -> dict[str, Any]:
    """Return solar geometry provenance and summary stats for a drone working H5."""

    h5_path = Path(h5_path)
    summary: dict[str, Any] = {
        "solar_geometry_source": "missing",
        "acquisition_datetime_used": None,
        "solar_zenith_mean": None,
        "solar_zenith_min": None,
        "solar_zenith_max": None,
        "solar_azimuth_mean": None,
        "solar_azimuth_min": None,
        "solar_azimuth_max": None,
    }

    try:
        h5_file_context = h5py.File(h5_path, "r")
    except OSError as exc:
        LOGGER.warning(
            "[drone] Could not read solar geometry summary from %s: %s",
            h5_path,
            exc,
        )
        return summary

    with h5_file_context as h5_file:
        metadata_group = None
        for candidate in h5_file.values():
            if isinstance(candidate, h5py.Group) and "Reflectance/Metadata" in candidate:
                metadata_group = candidate["Reflectance/Metadata"]
                break
        if metadata_group is None:
            metadata_group = h5_file.get("Reflectance/Metadata")
        if not isinstance(metadata_group, h5py.Group):
            return summary

        source = metadata_group.attrs.get("solar_geometry_source")
        if isinstance(source, bytes):
            source = source.decode("utf-8")
        acquisition = metadata_group.attrs.get("acquisition_datetime_used")
        if isinstance(acquisition, bytes):
            acquisition = acquisition.decode("utf-8")
        summary["solar_geometry_source"] = str(source or "missing")
        summary["acquisition_datetime_used"] = str(acquisition or "") or None

        if "Solar_Zenith_Angle" in metadata_group and "Solar_Azimuth_Angle" in metadata_group:
            stats = _solar_geometry_stats(
                metadata_group["Solar_Zenith_Angle"][()],
                metadata_group["Solar_Azimuth_Angle"][()],
            )
            summary.update(stats)
            if summary["solar_geometry_source"] == "missing":
                summary["solar_geometry_source"] = "raster"
        else:
            for key in _DRONE_SOLAR_GEOMETRY_ATTRS[2:]:
                if key in metadata_group.attrs:
                    summary[key] = float(metadata_group.attrs[key])

    return summary


def convert_drone_tiff_to_h5(
    reflectance_tiff_path: str | Path,
    *,
    output_h5_path: str | Path,
    wavelengths_nm: Sequence[float] | np.ndarray | None = None,
    fwhm_nm: Sequence[float] | np.ndarray | None = None,
    sensor_zenith_tiff: str | Path | None = None,
    sensor_azimuth_tiff: str | Path | None = None,
    slope_tiff: str | Path | None = None,
    aspect_tiff: str | Path | None = None,
    solar_zenith_tiff: str | Path | None = None,
    solar_azimuth_tiff: str | Path | None = None,
    solar_zenith_deg: float | None = None,
    solar_azimuth_deg: float | None = None,
    sensor_zenith_deg: float | None = None,
    sensor_azimuth_deg: float | None = None,
    acquisition_datetime: datetime | str | None = None,
    require_solar_geometry: bool = False,
    overwrite: bool = False,
) -> Path:
    reflectance_tiff_path = Path(reflectance_tiff_path)
    output_h5_path = Path(output_h5_path)
    if output_h5_path.exists() and not overwrite:
        return output_h5_path

    reflectance_raw, crs_wkt, transform, nodata = _read_drone_tiff_raster(reflectance_tiff_path)
    if reflectance_raw.ndim != 3:
        raise ValueError(
            f"Reflectance TIFF must be a multiband raster; received shape {reflectance_raw.shape}."
        )

    reflectance_cube = np.moveaxis(reflectance_raw, 0, 2).astype(np.float32, copy=False)
    lines, columns, band_count = reflectance_cube.shape
    nodata_value = np.float32(_DRONE_FALLBACK_NODATA if nodata is None else nodata)
    wavelengths_arr = _normalise_tiff_spectral_vector(
        wavelengths_nm,
        field_name="wavelengths_nm",
        band_count=band_count,
        default_values=_DRONE_TIFF_DEFAULT_WAVELENGTHS_NM,
    )
    fwhm_arr = _normalise_tiff_spectral_vector(
        fwhm_nm,
        field_name="fwhm_nm",
        band_count=band_count,
        default_values=_DRONE_TIFF_DEFAULT_FWHM_NM,
    )

    reflectance_shape = (lines, columns)
    ancillary_arrays: dict[str, np.ndarray | float] = {}
    optional_tiffs = {
        "slope": slope_tiff,
        "aspect": aspect_tiff,
        "sensor_zenith": sensor_zenith_tiff,
        "sensor_azimuth": sensor_azimuth_tiff,
    }
    scalar_fallbacks = {
        "sensor_zenith": sensor_zenith_deg,
        "sensor_azimuth": sensor_azimuth_deg,
    }

    for key, ancillary in optional_tiffs.items():
        if ancillary is not None:
            ancillary_arrays[key] = _validate_drone_tiff_ancillary_alignment(
                reflectance_tiff_path,
                reflectance_shape,
                transform,
                crs_wkt,
                Path(ancillary),
            )
        elif scalar_fallbacks.get(key) is not None:
            ancillary_arrays[key] = float(scalar_fallbacks[key])

    acquisition_dt = _coerce_acquisition_datetime(acquisition_datetime)
    solar_geometry_source = "missing"
    if solar_zenith_tiff is not None and solar_azimuth_tiff is not None:
        ancillary_arrays["solar_zenith"] = _validate_drone_tiff_ancillary_alignment(
            reflectance_tiff_path,
            reflectance_shape,
            transform,
            crs_wkt,
            Path(solar_zenith_tiff),
        )
        ancillary_arrays["solar_azimuth"] = _validate_drone_tiff_ancillary_alignment(
            reflectance_tiff_path,
            reflectance_shape,
            transform,
            crs_wkt,
            Path(solar_azimuth_tiff),
        )
        solar_geometry_source = "raster"
    elif solar_zenith_deg is not None and solar_azimuth_deg is not None:
        ancillary_arrays["solar_zenith"] = float(solar_zenith_deg)
        ancillary_arrays["solar_azimuth"] = float(solar_azimuth_deg)
        solar_geometry_source = "scalar"
    elif acquisition_dt is not None:
        longitude, latitude = _drone_pixel_lon_lat(
            transform=transform,
            crs_wkt=crs_wkt,
            shape=reflectance_shape,
        )
        solar_zenith, solar_azimuth = _compute_solar_geometry_arrays(
            acquisition_datetime=acquisition_dt,
            longitude=longitude,
            latitude=latitude,
        )
        ancillary_arrays["solar_zenith"] = solar_zenith
        ancillary_arrays["solar_azimuth"] = solar_azimuth
        solar_geometry_source = "manifest_computed"
    else:
        if solar_zenith_tiff is not None or solar_azimuth_tiff is not None:
            LOGGER.warning(
                "[drone] Incomplete solar geometry TIFF pair for %s; both "
                "zenith and azimuth are required.",
                reflectance_tiff_path,
            )
        if solar_zenith_deg is not None or solar_azimuth_deg is not None:
            LOGGER.warning(
                "[drone] Incomplete scalar solar geometry for %s; both zenith "
                "and azimuth are required.",
                reflectance_tiff_path,
            )
        if require_solar_geometry:
            raise RuntimeError(
                "Drone TIFF conversion requires solar geometry for requested correction, "
                "but no complete solar geometry TIFF pair, scalar solar angles, or "
                "manifest acquisition datetime was available."
            )

    output_h5_path.parent.mkdir(parents=True, exist_ok=True)
    site_group_name = clean_name(_drone_package_dir(reflectance_tiff_path).name) or "DRONE"
    map_info = _build_drone_tiff_map_info(transform, crs_wkt)

    with h5py.File(output_h5_path, "w") as h5_file:
        site_group = h5_file.create_group(site_group_name)
        reflectance_group = site_group.create_group("Reflectance")
        metadata_group = reflectance_group.create_group("Metadata")
        coordinate_group = metadata_group.create_group("Coordinate_System")
        spectral_group = metadata_group.create_group("Spectral_Data")
        ancillary_group = metadata_group.create_group("Ancillary_Imagery")

        reflectance_ds = reflectance_group.create_dataset(
            "Reflectance_Data",
            data=reflectance_cube,
            dtype=np.float32,
        )
        reflectance_ds.attrs["Data_Ignore_Value"] = nodata_value
        reflectance_ds.attrs["_FillValue"] = nodata_value
        reflectance_ds.attrs["NoData"] = nodata_value
        reflectance_ds.attrs["no_data"] = nodata_value
        reflectance_ds.attrs["Scale_Factor"] = np.float32(1.0)

        wavelength_ds = spectral_group.create_dataset(
            "Wavelength",
            data=wavelengths_arr,
            dtype=np.float32,
        )
        wavelength_ds.attrs["Units"] = "nanometers"
        fwhm_ds = spectral_group.create_dataset(
            "FWHM",
            data=fwhm_arr,
            dtype=np.float32,
        )
        fwhm_ds.attrs["Units"] = "nanometers"

        str_dtype = h5py.string_dtype(encoding="utf-8")
        coordinate_group.create_dataset(
            "Coordinate_System_String",
            data=crs_wkt,
            dtype=str_dtype,
        )
        coordinate_group.create_dataset("Map_Info", data=map_info, dtype=str_dtype)

        ancillary_group.create_dataset(
            "Path_Length",
            data=np.ones(reflectance_shape, dtype=np.float32),
            dtype=np.float32,
        )
        if "slope" in ancillary_arrays:
            ancillary_group.create_dataset("Slope", data=ancillary_arrays["slope"], dtype=np.float32)
        if "aspect" in ancillary_arrays:
            ancillary_group.create_dataset("Aspect", data=ancillary_arrays["aspect"], dtype=np.float32)
        if "sensor_zenith" in ancillary_arrays:
            metadata_group.create_dataset("to-sensor_Zenith_Angle", data=ancillary_arrays["sensor_zenith"])
        if "sensor_azimuth" in ancillary_arrays:
            metadata_group.create_dataset("to-sensor_Azimuth_Angle", data=ancillary_arrays["sensor_azimuth"])
        if "solar_zenith" in ancillary_arrays:
            metadata_group.create_dataset("Solar_Zenith_Angle", data=ancillary_arrays["solar_zenith"])
        if "solar_azimuth" in ancillary_arrays:
            metadata_group.create_dataset("Solar_Azimuth_Angle", data=ancillary_arrays["solar_azimuth"])
        if "solar_zenith" in ancillary_arrays and "solar_azimuth" in ancillary_arrays:
            _write_solar_geometry_attrs(
                metadata_group,
                source=solar_geometry_source,
                acquisition_datetime=acquisition_dt,
                solar_zenith=ancillary_arrays["solar_zenith"],
                solar_azimuth=ancillary_arrays["solar_azimuth"],
            )

    return output_h5_path


def _prepare_drone_source_working_h5(
    source_path: str | Path,
    *,
    source_type: str,
    working_path: str | Path,
    overwrite: bool = False,
    tiff_wavelengths_nm: Sequence[float] | np.ndarray | None = None,
    tiff_fwhm_nm: Sequence[float] | np.ndarray | None = None,
    tiff_solar_zenith_deg: float | None = None,
    tiff_solar_azimuth_deg: float | None = None,
    tiff_sensor_zenith_deg: float | None = None,
    tiff_sensor_azimuth_deg: float | None = None,
    acquisition_datetime: datetime | str | None = None,
    require_solar_geometry: bool = False,
) -> tuple[Path, bool]:
    source_path = Path(source_path)
    if source_type == "h5":
        return _prepare_drone_h5_working_copy(
            source_path,
            working_path=working_path,
            overwrite=overwrite,
        )
    if source_type != "tiff":
        raise ValueError(f"Unsupported drone source_type: {source_type}")

    package_dir = _drone_package_dir(source_path)
    prepared_path = convert_drone_tiff_to_h5(
        source_path,
        output_h5_path=working_path,
        wavelengths_nm=tiff_wavelengths_nm,
        fwhm_nm=tiff_fwhm_nm,
        slope_tiff=_find_drone_tiff_ancillary(package_dir, "slope"),
        aspect_tiff=_find_drone_tiff_ancillary(package_dir, "aspect"),
        sensor_zenith_tiff=_find_drone_tiff_ancillary(package_dir, "sensor_zenith"),
        sensor_azimuth_tiff=_find_drone_tiff_ancillary(package_dir, "sensor_azimuth"),
        solar_zenith_tiff=_find_drone_tiff_ancillary(package_dir, "solar_zenith"),
        solar_azimuth_tiff=_find_drone_tiff_ancillary(package_dir, "solar_azimuth"),
        solar_zenith_deg=tiff_solar_zenith_deg,
        solar_azimuth_deg=tiff_solar_azimuth_deg,
        sensor_zenith_deg=tiff_sensor_zenith_deg,
        sensor_azimuth_deg=tiff_sensor_azimuth_deg,
        acquisition_datetime=acquisition_datetime,
        require_solar_geometry=require_solar_geometry,
        overwrite=overwrite,
    )
    return prepared_path, False


def _find_drone_reflectance_dataset(h5_file: h5py.File) -> h5py.Dataset:
    """Locate the reflectance cube for drone staging without relaxing NEON readers.

    The drone pipeline prepares a run-owned working copy before instantiating
    ``NeonCube`` so that the standard NEON reader can remain strict elsewhere.
    """

    explicit_candidates = (
        "NIWO/Reflectance/Reflectance_Data",
        "Reflectance/Reflectance_Data",
    )
    for candidate in explicit_candidates:
        dataset = h5_file.get(candidate)
        if isinstance(dataset, h5py.Dataset):
            return dataset

    best_path: str | None = None
    best_score: tuple[int, int, int] | None = None

    def _visitor(name: str, obj: h5py.Dataset) -> None:
        nonlocal best_path, best_score
        if not isinstance(obj, h5py.Dataset):
            return

        name_lower = name.lower()
        keyword_score = 0
        for idx, needle in enumerate(("reflectance_data", "reflectance", "reflect")):
            if needle in name_lower:
                keyword_score = 3 - idx
                break
        if keyword_score == 0:
            return

        shape_score = min(int(obj.ndim), 3)
        size_score = int(obj.size > 0)
        score = (keyword_score, shape_score, size_score)
        if best_score is None or score > best_score:
            best_path = name
            best_score = score

    h5_file.visititems(_visitor)
    if best_path is None:
        raise KeyError("Could not locate a reflectance-like dataset in the drone HDF5.")

    dataset = h5_file.get(best_path)
    if not isinstance(dataset, h5py.Dataset):  # pragma: no cover - defensive
        raise KeyError(f"Resolved reflectance path is not a dataset: {best_path}")
    return dataset


def _dataset_has_recognised_nodata(dataset: h5py.Dataset) -> bool:
    return any(attr_name in dataset.attrs for attr_name in _RECOGNISED_NODATA_ATTRS)


def _prepare_drone_h5_working_copy(
    h5_path: str | Path,
    *,
    working_path: str | Path,
    overwrite: bool = False,
) -> tuple[Path, bool]:
    """Prepare a drone-owned HDF5 copy with fallback no-data metadata if needed.

    This compatibility shim is intentionally local to the drone pipeline. It
    never mutates the original source HDF5 and exists only to bridge drone
    orthomosaics into the existing strict NEON reader stack.
    """

    source_path = Path(h5_path)
    prepared_path = Path(working_path)
    prepared_path.parent.mkdir(parents=True, exist_ok=True)

    if overwrite or not prepared_path.exists():
        shutil.copy2(source_path, prepared_path)

    with h5py.File(prepared_path, "r+") as h5_file:
        reflectance_ds = _find_drone_reflectance_dataset(h5_file)
        if _dataset_has_recognised_nodata(reflectance_ds):
            return prepared_path, False

        for attr_name in _DRONE_NODATA_PATCH_ATTRS:
            reflectance_ds.attrs[attr_name] = _DRONE_FALLBACK_NODATA

    return prepared_path, True


def resolve_band_map(
    wavelengths: list[float] | np.ndarray, targets: dict[str, int]
) -> dict[str, dict[str, float | int]]:
    wavelengths_arr = np.asarray(wavelengths, dtype=float)
    if wavelengths_arr.ndim != 1 or wavelengths_arr.size == 0:
        raise ValueError("wavelengths must be a non-empty 1-D array")

    band_map: dict[str, dict[str, float | int]] = {}
    for name, target_wl in targets.items():
        idx = int(np.argmin(np.abs(wavelengths_arr - float(target_wl))))
        band_map[name] = {
            "index": idx,
            "wavelength": float(wavelengths_arr[idx]),
        }
    return band_map


def validate_drone_h5_metadata(h5_path: str | Path) -> dict[str, Any]:
    """Validate minimally required drone H5 metadata and return a structured summary."""

    cube = NeonCube(h5_path=h5_path)
    wavelengths = np.asarray(cube.wavelengths, dtype=np.float32).reshape(-1)
    if wavelengths.size == 0:
        raise ValueError(f"Drone H5 has no wavelength metadata: {h5_path}")

    fwhm = getattr(cube, "fwhm", None)
    fwhm_arr = (
        np.asarray(fwhm, dtype=np.float32).reshape(-1) if fwhm is not None else None
    )
    if fwhm_arr is not None and fwhm_arr.size != wavelengths.size:
        raise ValueError(
            f"Drone H5 FWHM length {fwhm_arr.size} does not match wavelengths length {wavelengths.size}: {h5_path}"
        )

    no_data = getattr(cube, "no_data", None)
    if no_data is None:
        raise ValueError(f"Drone H5 is missing a usable no-data value: {h5_path}")

    return {
        "wavelengths": wavelengths.tolist(),
        "fwhm": fwhm_arr.tolist() if fwhm_arr is not None else None,
        "nodata": float(no_data),
        "scale_factor": float(getattr(cube, "scale_factor", 1.0) or 1.0),
        "lines": int(cube.lines),
        "samples": int(cube.columns),
        "bands": int(cube.bands),
        "wavelength_units": getattr(cube, "wavelength_units", None),
        "has_transform": getattr(cube, "transform", None) is not None,
        "has_projection": bool(getattr(cube, "projection_wkt", "")),
    }


def export_h5_to_envi(
    h5_path: str | Path,
    *,
    output_stem: str | Path,
    brightness_offset: float = 0.0,
    overwrite: bool = False,
    cube: NeonCube | None = None,
) -> tuple[Path, Path]:
    """Export a local H5 cube to ENVI using a drone-native filename stem."""

    output_stem = Path(output_stem)
    output_img = output_stem.with_suffix(".img")
    output_hdr = output_stem.with_suffix(".hdr")
    output_img.parent.mkdir(parents=True, exist_ok=True)

    if not overwrite and is_valid_envi_pair(output_img, output_hdr):
        LOGGER.info(
            "[drone] Reusing ENVI export → %s / %s", output_img.name, output_hdr.name
        )
        return output_img, output_hdr

    cube = cube or NeonCube(h5_path=h5_path)
    header = cube.build_envi_header()
    header["description"] = "Drone hyperspectral reflectance exported to ENVI"
    header.setdefault("reflectance scale factor", float(getattr(cube, "scale_factor", 1.0)))
    if hasattr(cube, "no_data"):
        header.setdefault("data ignore value", float(getattr(cube, "no_data")))
    writer = EnviWriter(output_stem, header)

    offset_value = np.float32(brightness_offset)
    chunk_y = 100
    chunk_x = 100
    reporter = TileProgressReporter(
        stage_name="Drone ENVI export",
        total_tiles=cube.chunk_count(chunk_y=chunk_y, chunk_x=chunk_x),
        interactive_mode=False,
        log_every=25,
    )
    try:
        for ys, ye, xs, xe, raw_chunk in cube.iter_chunks(
            chunk_y=chunk_y, chunk_x=chunk_x
        ):
            chunk = np.asarray(raw_chunk, dtype=np.float32)
            if brightness_offset != 0.0:
                chunk = chunk + offset_value
            writer.write_chunk(chunk, ys, xs)
            reporter.update(1)
    finally:
        writer.close()
        reporter.close()

    if not is_valid_envi_pair(output_img, output_hdr):
        raise RuntimeError(
            f"Drone ENVI export failed for {h5_path}: {output_img} / {output_hdr}"
        )

    return output_img, output_hdr


def build_drone_config(
    *,
    h5_path: Path,
    envi_img: Path,
    envi_hdr: Path,
    corrected_img: Path,
    corrected_hdr: Path,
    wavelengths: list[float],
    fwhm: list[float] | None,
    band_map: dict[str, dict[str, float | int]],
    apply_topo: bool,
    apply_brdf: bool,
    use_ndvi_brdf_bins: bool,
) -> dict[str, Any]:
    return {
        "platform": "drone",
        "h5_path": str(Path(h5_path)),
        "raw_img_path": str(envi_img),
        "raw_hdr_path": str(envi_hdr),
        "out_img_path": str(corrected_img),
        "out_hdr_path": str(corrected_hdr),
        "wavelength_nm": list(wavelengths),
        "fwhm_nm": list(fwhm) if fwhm is not None else None,
        "band_map": band_map,
        "apply_topo": bool(apply_topo),
        "apply_brdf": bool(apply_brdf),
        "use_ndvi_brdf_bins": bool(use_ndvi_brdf_bins),
        "brightness_offset": 0.0,
        "apply_brightness_adjustment": False,
        "apply_cloud_mask": False,
        "apply_convolution": False,
    }


def _has_required_ancillary(cube: NeonCube, names: tuple[str, ...]) -> bool:
    for name in names:
        try:
            values = cube.get_ancillary(name, radians=True)
        except Exception:
            return False
        if values is None or np.asarray(values).size == 0:
            return False
    return True


def _chunk_has_any_valid_reflectance(
    chunk: np.ndarray,
    *,
    no_data_value: float | None,
) -> bool:
    valid = np.isfinite(chunk)
    if no_data_value is not None and np.isfinite(no_data_value):
        valid &= ~np.isclose(chunk, float(no_data_value), atol=1e-6)
    return bool(np.any(valid))


def _load_existing_drone_correction_flags(corrected_stem: Path) -> dict[str, bool]:
    """Best-effort recovery of prior correction flags for reused drone outputs."""

    corrected_stem = Path(corrected_stem)
    flight_dir = corrected_stem.parent
    qa_json_path = flight_dir / f"{flight_dir.name}__qa.json"
    if not qa_json_path.exists():
        return {}

    try:
        payload = json.loads(qa_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}

    audit = payload.get("audit")
    if not isinstance(audit, dict):
        return {}
    flags = audit.get("flags")
    if not isinstance(flags, dict):
        return {}

    flag_names = (
        "topo_applied",
        "brdf_applied",
        "topo_fallback_due_to_nodata",
        "brdf_fallback_due_to_nodata",
    )
    return {
        name: bool(flags.get(name, False))
        for name in flag_names
        if name in flags
    }


def _call_with_supported_kwargs(func, /, *args, **kwargs):
    """Call ``func`` after dropping kwargs it does not declare.

    The drone tests monkeypatch BRDF helpers with small lambdas that keep the
    historical signatures. Production helpers accept richer keyword options, so
    we filter here to preserve backward compatibility for test doubles and other
    lightweight call sites.
    """

    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return func(*args, **kwargs)

    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    ):
        return func(*args, **kwargs)

    supported_kwargs = {
        name: value for name, value in kwargs.items() if name in signature.parameters
    }
    return func(*args, **supported_kwargs)


def apply_drone_corrections(
    *,
    cube: NeonCube,
    envi_img: Path,
    envi_hdr: Path,
    corrected_stem: Path,
    apply_topo: bool,
    apply_brdf: bool,
    use_ndvi_brdf_bins: bool = False,
    overwrite: bool = False,
) -> tuple[Path, Path, dict[str, Any]]:
    """Apply optional topo/BRDF corrections to a drone ENVI export.

    ``run_drone_pipeline`` now requests both topo and BRDF correction by
    default. Each correction still remains conditional on the required
    ancillary geometry being available for the current cube.
    """

    corrected_img = corrected_stem.with_suffix(".img")
    corrected_hdr = corrected_stem.with_suffix(".hdr")
    audit = {
        "requested_topo": bool(apply_topo),
        "requested_brdf": bool(apply_brdf),
        "topo_applied": False,
        "brdf_applied": False,
        "topo_fallback_due_to_nodata": False,
        "brdf_fallback_due_to_nodata": False,
        "brightness_applied": False,
        "cloud_mask_applied": False,
        "convolution_skipped": True,
        "reused_existing_corrected": False,
        "correction_status_source": "live_run",
        "ndvi_brdf_bins_enabled": bool(use_ndvi_brdf_bins),
    }
    correction_requested = bool(apply_topo or apply_brdf)

    topo_ready = apply_topo and _has_required_ancillary(
        cube, ("slope", "aspect", "solar_zn", "solar_az")
    )
    brdf_ready = apply_brdf and _has_required_ancillary(
        cube, ("solar_zn", "solar_az", "sensor_zn", "sensor_az")
    )

    audit["topo_ready"] = topo_ready
    audit["brdf_ready"] = brdf_ready

    if not overwrite and is_valid_envi_pair(corrected_img, corrected_hdr):
        audit["reused_existing_corrected"] = True
        existing_flags = _load_existing_drone_correction_flags(corrected_stem)
        if existing_flags:
            audit.update(existing_flags)
            audit["correction_status_source"] = "existing_qa_json"
        else:
            audit["correction_status_source"] = "reuse_without_prior_audit"
        return corrected_img, corrected_hdr, audit

    if not topo_ready and not brdf_ready:
        if correction_requested:
            _cleanup_envi_pair(corrected_img, corrected_hdr)
            raise DroneCorrectionUnavailableError(
                "Requested drone correction could not run because the required ancillary geometry was unavailable.",
                audit,
            )
        shutil.copy2(envi_img, corrected_img)
        shutil.copy2(envi_hdr, corrected_hdr)
        return corrected_img, corrected_hdr, audit

    coeff_path: Path | None = None
    if brdf_ready:
        fit_kwargs: dict[str, Any] = {
            "brdf_kernel_config": HYTOOLS_BRDF_KERNEL_CONFIG,
        }
        if use_ndvi_brdf_bins:
            fit_kwargs["ndvi_config"] = NDVIBinningConfig(enabled=True)
        coeff_path = _call_with_supported_kwargs(
            fit_and_save_brdf_model,
            cube,
            corrected_stem.parent,
            **fit_kwargs,
        )

    header = cube.build_envi_header()
    header["description"] = (
        "Drone reflectance corrected with optional topo/BRDF adjustments"
    )
    header.setdefault("reflectance scale factor", float(getattr(cube, "scale_factor", 1.0)))
    if hasattr(cube, "no_data"):
        header.setdefault("data ignore value", float(getattr(cube, "no_data")))
    writer = EnviWriter(corrected_stem, header)
    # Drone scenes are already fully loaded into memory via ``NeonCube``.
    # Use a single full-scene chunk here so the correction is fit/applied
    # consistently across the footprint instead of tile-by-tile.
    chunk_y = cube.lines
    chunk_x = cube.columns
    reporter = TileProgressReporter(
        stage_name="Drone correction",
        total_tiles=cube.chunk_count(chunk_y=chunk_y, chunk_x=chunk_x),
        interactive_mode=False,
        log_every=25,
    )
    no_data_value = (
        float(getattr(cube, "no_data")) if hasattr(cube, "no_data") else None
    )
    try:
        for ys, ye, xs, xe, raw_chunk in cube.iter_chunks(
            chunk_y=chunk_y, chunk_x=chunk_x
        ):
            chunk = np.asarray(raw_chunk, dtype=np.float32)
            if topo_ready:
                topo_input = chunk
                topo_candidate = apply_topo_correct(cube, chunk, ys, ye, xs, xe)
                if _chunk_has_any_valid_reflectance(
                    topo_input,
                    no_data_value=no_data_value,
                ) and not _chunk_has_any_valid_reflectance(
                    topo_candidate,
                    no_data_value=no_data_value,
                ):
                    LOGGER.warning(
                        "[drone] Topographic correction collapsed valid reflectance to no-data for %s; "
                        "reverting to the pre-topo chunk.",
                        corrected_stem.name,
                    )
                    audit["topo_fallback_due_to_nodata"] = True
                    chunk = topo_input
                else:
                    chunk = topo_candidate
                    audit["topo_applied"] = True
            if brdf_ready:
                brdf_input = chunk
                brdf_kwargs: dict[str, Any] = {
                    "coeff_path": coeff_path,
                    "brdf_kernel_config": HYTOOLS_BRDF_KERNEL_CONFIG,
                }
                if use_ndvi_brdf_bins:
                    brdf_kwargs["ndvi_config"] = NDVIBinningConfig(enabled=True)
                brdf_candidate = _call_with_supported_kwargs(
                    apply_brdf_correct,
                    cube,
                    chunk,
                    ys,
                    ye,
                    xs,
                    xe,
                    **brdf_kwargs,
                )
                if _chunk_has_any_valid_reflectance(
                    brdf_input,
                    no_data_value=no_data_value,
                ) and not _chunk_has_any_valid_reflectance(
                    brdf_candidate,
                    no_data_value=no_data_value,
                ):
                    LOGGER.warning(
                        "[drone] BRDF correction collapsed valid reflectance to no-data for %s; "
                        "reverting to the pre-BRDF chunk.",
                        corrected_stem.name,
                    )
                    audit["brdf_fallback_due_to_nodata"] = True
                    chunk = brdf_input
                else:
                    chunk = brdf_candidate
                    audit["brdf_applied"] = True
            writer.write_chunk(chunk, ys, xs)
            reporter.update(1)
    finally:
        writer.close()
        reporter.close()

    if not is_valid_envi_pair(corrected_img, corrected_hdr):
        _cleanup_envi_pair(corrected_img, corrected_hdr)
        raise RuntimeError(
            f"Drone correction stage failed to produce a valid ENVI pair: {corrected_img} / {corrected_hdr}"
        )

    if correction_requested and not audit["topo_applied"] and not audit["brdf_applied"]:
        _cleanup_envi_pair(corrected_img, corrected_hdr)
        if audit["topo_fallback_due_to_nodata"] or audit["brdf_fallback_due_to_nodata"]:
            raise DroneCorrectionUnavailableError(
                "Requested drone correction was attempted but reverted because it collapsed valid reflectance to no-data.",
                audit,
            )
        raise DroneCorrectionUnavailableError(
            "Requested drone correction did not produce a corrected output.",
            audit,
        )

    return corrected_img, corrected_hdr, audit


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _remove_file_if_exists(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except FileNotFoundError:
        return


def _cleanup_envi_pair(img_path: Path, hdr_path: Path) -> None:
    _remove_file_if_exists(img_path)
    _remove_file_if_exists(hdr_path)


def _write_drone_audit_json(file_audit: dict[str, Any]) -> Path:
    qa_json_path = Path(str(file_audit["qa_json_path"]))
    payload = {
        "platform": "drone",
        "status": file_audit.get("status"),
        "error": file_audit.get("error"),
        "qa_rendered": False,
        "audit": file_audit,
    }
    return _write_json(qa_json_path, payload)


def _normalise_bounds(bounds: Any) -> list[float] | None:
    if bounds is None:
        return None
    values = [float(value) for value in bounds]
    return values if len(values) == 4 else None


def _normalise_transform(transform: Any) -> list[float] | None:
    if transform is None:
        return None
    try:
        return [float(value) for value in tuple(transform)[:6]]
    except Exception:
        return None


def _crs_to_string(crs: Any) -> str | None:
    if crs is None:
        return None
    if hasattr(crs, "to_string"):
        try:
            return crs.to_string()
        except Exception:
            pass
    return str(crs)


def collect_drone_spatial_diagnostics(
    *,
    raster_img: Path,
    polygons_path: Path,
) -> dict[str, Any]:
    """Collect drone-only raster/polygon overlay diagnostics before extraction."""

    geopandas = __import__("geopandas")
    rasterio = __import__("rasterio")
    from shapely.geometry import box

    polygons = geopandas.read_file(polygons_path)
    if polygons.empty:
        raise ValueError(f"No polygons were found in {polygons_path}")

    with rasterio.open(raster_img) as src:
        raster_crs = src.crs
        raster_bounds = src.bounds
        raster_transform = src.transform
        raster_width = src.width
        raster_height = src.height
        raster_nodata = src.nodata

    polygon_crs = polygons.crs
    polygon_total_bounds = _normalise_bounds(polygons.total_bounds)
    reprojected_polygons = polygons
    reprojected = False
    if polygon_crs is None and raster_crs is not None:
        reprojected_polygons = polygons.set_crs(raster_crs)
        reprojected = True
    elif raster_crs is not None and polygon_crs != raster_crs:
        reprojected_polygons = polygons.to_crs(raster_crs)
        reprojected = True

    raster_bounds_poly = box(*raster_bounds)
    reprojected_polygon_total_bounds = _normalise_bounds(reprojected_polygons.total_bounds)
    overlap_after_reproject = False
    if reprojected_polygon_total_bounds is not None:
        overlap_after_reproject = bool(
            box(*reprojected_polygon_total_bounds).intersects(raster_bounds_poly)
        )
    intersecting_polygon_count = int(
        reprojected_polygons.geometry.intersects(raster_bounds_poly).sum()
    )

    return {
        "raster_path": str(raster_img),
        "raster_crs": _crs_to_string(raster_crs),
        "raster_bounds": _normalise_bounds(raster_bounds),
        "raster_transform": _normalise_transform(raster_transform),
        "raster_width": int(raster_width),
        "raster_height": int(raster_height),
        "raster_nodata": None if raster_nodata is None else float(raster_nodata),
        "polygon_path": str(polygons_path),
        "polygon_crs": _crs_to_string(polygon_crs),
        "polygon_total_bounds": polygon_total_bounds,
        "polygon_count": int(len(polygons)),
        "reprojected_polygon_crs": _crs_to_string(reprojected_polygons.crs),
        "reprojected_polygon_total_bounds": reprojected_polygon_total_bounds,
        "polygon_reprojected": reprojected,
        "bounds_overlap_after_reproject": overlap_after_reproject,
        "intersecting_polygon_count": intersecting_polygon_count,
    }


def save_drone_overlay_debug_plot(
    *,
    polygons_path: Path,
    raster_bounds: list[float] | tuple[float, float, float, float],
    raster_crs: str | None,
    output_path: Path,
) -> Path:
    """Write a lightweight overlay PNG for drone polygon/raster diagnostics."""

    geopandas = __import__("geopandas")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    polygons = geopandas.read_file(polygons_path)
    if polygons.empty:
        raise ValueError(f"No polygons were found in {polygons_path}")

    if raster_crs is not None:
        if polygons.crs is None:
            polygons = polygons.set_crs(raster_crs)
        elif _crs_to_string(polygons.crs) != raster_crs:
            polygons = polygons.to_crs(raster_crs)

    minx, miny, maxx, maxy = [float(value) for value in raster_bounds]
    width = max(maxx - minx, 1.0)
    height = max(maxy - miny, 1.0)

    fig, ax = plt.subplots(figsize=(4, 4))
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
    pad_x = width * 0.05
    pad_y = height * 0.05
    ax.set_xlim(minx - pad_x, maxx + pad_x)
    ax.set_ylim(miny - pad_y, maxy + pad_y)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("Drone overlay debug")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend(loc="best")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def _build_polygon_pixel_index_for_raster(
    *,
    raster_img: Path,
    raster_hdr: Path,
    polygons_path: Path,
    output_path: Path,
    flight_id: str,
    overwrite: bool = False,
) -> Path:
    if output_path.exists() and not overwrite:
        return output_path

    geopandas = __import__("geopandas")
    rasterio = __import__("rasterio")
    from rasterio.features import rasterize
    from rasterio.transform import xy

    polygons = geopandas.read_file(polygons_path)
    if polygons.empty:
        raise ValueError(f"No polygons were found in {polygons_path}")

    is_valid, message = validate_coordinate_match(
        polygons, raster_img, raster_hdr, tolerance_m=50000.0
    )
    if not is_valid:
        LOGGER.warning("[drone-polygons] Coordinate validation warning: %s", message)

    with rasterio.open(raster_img) as src:
        transform = src.transform
        width = src.width
        height = src.height
        dataset_crs = src.crs
        crs_epsg = dataset_crs.to_epsg() if dataset_crs else None

    if polygons.crs is None and dataset_crs is not None:
        polygons = polygons.set_crs(dataset_crs)
    elif dataset_crs is not None and polygons.crs != dataset_crs:
        polygons = polygons.to_crs(dataset_crs)

    polygons = polygons.reset_index(drop=True).copy()
    if "polygon_id" in polygons and polygons["polygon_id"].is_unique:
        polygons["polygon_id"] = polygons["polygon_id"].astype("int64", copy=False)
    else:
        polygons["polygon_id"] = np.arange(1, len(polygons) + 1, dtype="int64")

    shapes = [
        (geom, int(pid))
        for geom, pid in zip(polygons.geometry, polygons["polygon_id"])
        if geom is not None and not geom.is_empty
    ]
    if not shapes:
        raise ValueError("All polygons were empty; nothing to index")

    polygon_grid = rasterize(
        shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype="int32",
        all_touched=False,
    )
    mask = polygon_grid > 0
    if not mask.any():
        raise ValueError("No pixels intersected the supplied polygons")

    rows, cols = np.nonzero(mask)
    xs, ys = xy(transform, rows, cols, offset="center")
    df = pd.DataFrame(
        {
            "pixel_id": rows.astype("int64") * width + cols.astype("int64"),
            "row": rows.astype("int32"),
            "col": cols.astype("int32"),
            "x": np.asarray(xs, dtype="float64"),
            "y": np.asarray(ys, dtype="float64"),
            "polygon_id": polygon_grid[rows, cols].astype("int64", copy=False),
            "flight_id": flight_id,
            "polygon_source": str(polygons_path),
            "reference_product": raster_img.stem,
        }
    )
    if dataset_crs is not None:
        df["raster_crs"] = dataset_crs.to_string()
    if crs_epsg is not None:
        df["epsg"] = pd.Series(crs_epsg, index=df.index, dtype="Int64")

    df = ensure_coord_columns(df, transform=transform, crs_epsg=crs_epsg or 0)

    attribute_columns = [
        col for col in polygons.columns if col != polygons.geometry.name
    ]
    polygon_attrs = polygons[attribute_columns].copy()
    polygon_attrs["polygon_geometry_wkb"] = polygons.geometry.to_wkb()
    df = df.merge(polygon_attrs, on="polygon_id", how="left")

    _write_dataframe_parquet(df, output_path)
    return output_path


def _merge_drone_polygon_outputs(
    outputs: list[str], output_path: Path, overwrite: bool = False
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return output_path
    if not outputs:
        raise ValueError("No polygon parquet outputs were provided for drone merge")

    con = duckdb.connect()
    try:
        files = ", ".join(
            ["'" + str(Path(path)).replace("'", "''") + "'" for path in outputs]
        )
        con.execute(
            "COPY (SELECT * FROM read_parquet(["
            + files
            + "], union_by_name=true)) TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [str(output_path)],
        )
    finally:
        con.close()
    return output_path


def _enrich_drone_polygon_parquet_with_index(
    polygon_parquet_path: Path,
    polygon_index_path: Path,
    *,
    overwrite: bool = True,
) -> Path:
    """Attach polygon index metadata to each extracted drone pixel row.

    The raw ENVI extraction step writes only the pixel-level spectral fields.
    For downstream CSV review and modeling we want each pixel row to also carry
    the polygon identifier and all non-geometry polygon attributes from the
    index parquet. This helper rewrites the polygon parquet in-place so the
    enriched schema propagates to both the per-flight CSV and the merged output.
    """

    polygon_parquet_path = Path(polygon_parquet_path)
    polygon_index_path = Path(polygon_index_path)
    if not polygon_parquet_path.exists():
        raise FileNotFoundError(polygon_parquet_path)
    if not polygon_index_path.exists():
        raise FileNotFoundError(polygon_index_path)

    temp_path = polygon_parquet_path.with_name(
        f"{polygon_parquet_path.stem}__enriched_tmp.parquet"
    )
    if temp_path.exists():
        temp_path.unlink()

    con = duckdb.connect()
    try:
        index_columns = _describe_parquet_columns(con, polygon_index_path)
        pixel_columns = _describe_parquet_columns(con, polygon_parquet_path)
        select_terms = [
            f"idx.{_quote_identifier(col)} AS {_quote_identifier(col)}"
            for col in index_columns
        ]
        seen_columns = set(index_columns)
        for col in pixel_columns:
            if col == "pixel_id" or col in seen_columns:
                continue
            select_terms.append(
                f"px.{_quote_identifier(col)} AS {_quote_identifier(col)}"
            )
            seen_columns.add(col)

        copy_sql = (
            "COPY (SELECT "
            + ", ".join(select_terms)
            + " FROM read_parquet('"
            + _quote_path(polygon_index_path)
            + "') idx INNER JOIN read_parquet('"
            + _quote_path(polygon_parquet_path)
            + "') px USING (pixel_id)) TO '"
            + _quote_path(temp_path)
            + "' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        con.execute(copy_sql)
    finally:
        con.close()

    if polygon_parquet_path.exists():
        polygon_parquet_path.unlink()
    temp_path.replace(polygon_parquet_path)
    return polygon_parquet_path


def _export_csv_copy_from_parquet(
    parquet_path: Path,
    csv_path: Path | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a CSV sidecar from an existing Parquet table for portability."""

    parquet_path = Path(parquet_path)
    csv_path = Path(csv_path) if csv_path is not None else parquet_path.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if csv_path.exists() and not overwrite:
        return csv_path
    if not parquet_path.exists():
        raise FileNotFoundError(f"Cannot export CSV sidecar; missing parquet: {parquet_path}")
    if csv_path.exists():
        csv_path.unlink()

    parquet_literal = str(parquet_path).replace("'", "''")
    csv_literal = str(csv_path).replace("'", "''")
    con = duckdb.connect()
    try:
        con.execute(
            "COPY (SELECT * FROM read_parquet('"
            + parquet_literal
            + "')) TO '"
            + csv_literal
            + "' (FORMAT CSV, HEADER)"
        )
    finally:
        con.close()
    return csv_path


def _try_export_csv_copy_from_parquet(
    parquet_path: Path,
    csv_path: Path | None = None,
    *,
    overwrite: bool = False,
    context_label: str,
) -> tuple[Path | None, str | None]:
    """Attempt CSV sidecar export without blocking the main drone outputs."""

    try:
        return (
            _export_csv_copy_from_parquet(
                parquet_path,
                csv_path=csv_path,
                overwrite=overwrite,
            ),
            None,
        )
    except Exception as exc:
        LOGGER.warning(
            "[drone] CSV sidecar export failed for %s (%s): %s",
            parquet_path,
            context_label,
            exc,
        )
        return None, str(exc)


def _drone_status_color(status: str) -> str | None:
    if status in {
        _DRONE_STATUS_SUCCESS_EXTRACTED,
        _DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP,
        _DRONE_STATUS_SUCCESS_QA_ONLY_NO_POLYGONS,
    }:
        return _ANSI_GREEN
    if status == _DRONE_STATUS_FAILED_OTHER:
        return _ANSI_RED
    return None


def _supports_ansi(stream: Any) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)())


def _colorize_drone_message(message: str, *, status: str | None = None) -> str:
    if status is None:
        return message
    color = _drone_status_color(status)
    if color is None or not _supports_ansi(sys.stderr):
        return message
    return f"{color}{message}{_ANSI_RESET}"


def _drone_emit(message: str, *, status: str | None = None) -> None:
    rendered = _colorize_drone_message(message, status=status)
    if tqdm is not None:
        try:  # pragma: no cover - tqdm.write is a thin wrapper
            tqdm.write(rendered, file=sys.stderr)
            return
        except Exception:
            pass
    print(rendered, file=sys.stderr)


def _format_elapsed(seconds: float) -> str:
    if seconds < 60.0:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(seconds, 60.0)
    if minutes < 60.0:
        return f"{int(minutes)}m {secs:.1f}s"
    hours, minutes = divmod(int(minutes), 60)
    return f"{hours}h {minutes}m {secs:.1f}s"


def _format_eta(elapsed_samples: list[float], remaining: int) -> str | None:
    if len(elapsed_samples) < 2 or remaining <= 0:
        return None
    avg_seconds = sum(elapsed_samples) / len(elapsed_samples)
    return _format_elapsed(avg_seconds * remaining)


def _classify_drone_exception(exc: Exception) -> tuple[str, str]:
    reason = str(exc).strip() or exc.__class__.__name__
    return _DRONE_STATUS_FAILED_OTHER, reason


def _has_drone_qa_inputs(file_audit: dict[str, Any]) -> bool:
    raw_img = Path(str(file_audit.get("working_raster_path", "")))
    corrected_img = Path(str(file_audit.get("corrected_raster_path", "")))
    return raw_img.exists() and corrected_img.exists()


def run_drone_pipeline(
    input_h5_dir: str | Path,
    polygon_path: str | Path | None = None,
    output_dir: str | Path = ".",
    apply_topo: bool = True,
    apply_brdf: bool = True,
    use_ndvi_brdf_bins: bool = False,
    apply_brightness_adjustment: bool = False,
    overwrite: bool = False,
    tiff_wavelengths_nm: Sequence[float] | np.ndarray | None = None,
    tiff_fwhm_nm: Sequence[float] | np.ndarray | None = None,
    tiff_solar_zenith_deg: float | None = None,
    tiff_solar_azimuth_deg: float | None = None,
    tiff_sensor_zenith_deg: float | None = None,
    tiff_sensor_azimuth_deg: float | None = None,
    drone_manifest_path: str | Path | None = None,
    require_solar_geometry: bool = True,
) -> dict[str, Any]:
    """Run the drone pipeline from local HDF5 or reflectance TIFF sources."""

    run_started = time.monotonic()
    input_h5_dir = Path(input_h5_dir)
    output_dir = Path(output_dir)
    polygon_path = Path(polygon_path) if polygon_path is not None else None
    output_dir.mkdir(parents=True, exist_ok=True)
    drone_manifest_path = _resolve_drone_manifest_path(
        drone_manifest_path,
        input_path=input_h5_dir,
    )
    drone_manifest = load_drone_manifest(drone_manifest_path)

    results: dict[str, Any] = {
        "platform": "drone",
        "processed": [],
        "failed": [],
        "outputs": [],
        "merged": None,
        "merged_csv": None,
        "qa_summary": {
            "platform": "drone",
            "convolution": "skipped",
            "brightness_offset": 0.0,
            "brightness_adjustment_requested": bool(apply_brightness_adjustment),
            "brightness_adjustment_applied": False,
            "cloud_mask_applied": False,
            "ndvi_brdf_bins_enabled": bool(use_ndvi_brdf_bins),
            "drone_manifest_path": (
                str(drone_manifest_path) if drone_manifest_path is not None else None
            ),
            "require_solar_geometry": bool(require_solar_geometry),
            "files": [],
        },
    }

    input_sources = _discover_drone_input_sources(input_h5_dir)
    input_path_exists = input_h5_dir.exists()
    input_path_type = (
        "file"
        if input_h5_dir.is_file()
        else "directory"
        if input_h5_dir.is_dir()
        else "missing"
    )
    results["qa_summary"]["discovered_total"] = len(input_sources)
    results["qa_summary"]["attempted_total"] = len(input_sources)
    results["qa_summary"]["run_root"] = str(output_dir)
    results["qa_summary"]["polygon_path"] = (
        str(polygon_path) if polygon_path is not None else None
    )
    results["qa_summary"]["input_source_path"] = str(input_h5_dir)
    results["qa_summary"]["input_source_path_resolved"] = str(
        input_h5_dir.expanduser().resolve(strict=False)
    )
    results["qa_summary"]["input_source_path_exists"] = bool(input_path_exists)
    results["qa_summary"]["input_source_path_type"] = input_path_type
    results["qa_summary"]["supported_input_extensions"] = list(
        _DRONE_SUPPORTED_INPUT_EXTENSIONS
    )
    if not input_sources:
        results["qa_summary"]["input_discovery_status"] = (
            "no_supported_drone_inputs_found"
        )
        results["qa_summary"]["skip_reason"] = (
            "No supported drone inputs were found under input_h5_dir. "
            "Expected local .h5, .tif, or .tiff files; ancillary-only TIFFs such "
            "as slope/aspect/sensor geometry are not treated as flight inputs."
        )
        _drone_emit(
            "[drone] No supported drone inputs discovered under "
            f"{input_h5_dir!s} (exists={input_path_exists}, "
            f"type={input_path_type}). Expected extensions: "
            f"{', '.join(_DRONE_SUPPORTED_INPUT_EXTENSIONS)}."
        )
        qa_path = _write_json(
            output_dir / "drone_qa_summary.json", results["qa_summary"]
        )
        results["qa_summary_path"] = str(qa_path)
        return results

    total_flights = len(input_sources)
    _drone_emit(
        "[drone] Starting batch: "
        f"{total_flights} discovered | {total_flights} to process | "
        f"polygon={polygon_path if polygon_path is not None else 'None'} | "
        f"run_root={output_dir}"
    )
    batch_bar = (
        tqdm(
            total=total_flights,
            desc="[drone] flights",
            unit="flight",
            dynamic_ncols=True,
            leave=True,
            file=sys.stderr,
        )
        if tqdm is not None
        else None
    )
    completed_flight_times: list[float] = []
    status_counts = {
        _DRONE_STATUS_SUCCESS_EXTRACTED: 0,
        _DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP: 0,
        _DRONE_STATUS_SUCCESS_QA_ONLY_NO_POLYGONS: 0,
        _DRONE_STATUS_FAILED_OTHER: 0,
    }

    for index, source in enumerate(input_sources, start=1):
        source_path = source.source_path
        flight_stem = source.flight_stem
        path_map = build_drone_output_paths(output_dir, flight_stem=flight_stem)
        prepared_h5_path = path_map["working_h5"]
        envi_stem = path_map["envi_stem"]
        corrected_stem = path_map["corrected_stem"]
        polygon_output_path = path_map["polygon_parquet"]
        polygon_index_path = path_map["polygon_index"]
        overlay_debug_path = path_map["overlay_debug_png"]
        package_dir = _drone_package_dir(source_path)
        acquisition_datetime = (
            lookup_flight_datetime(flight_stem, drone_manifest)
            if source.source_type == "tiff"
            else None
        )
        acquisition_datetime_used = (
            _datetime_to_utc_naive(acquisition_datetime).isoformat()
            if acquisition_datetime is not None
            else None
        )
        flight_started = time.monotonic()
        if batch_bar is not None:
            batch_bar.set_postfix_str(
                f"{index}/{total_flights} {flight_stem} | preparing {source.source_type}"
            )
        _drone_emit(
            f"[drone] [{index}/{total_flights}] {flight_stem} | source={package_dir} "
            f"| type={source.source_type} | stage=preparing working H5"
        )
        file_audit: dict[str, Any] = {
            "platform": "drone",
            "flight_stem": flight_stem,
            "flight_dir": str(path_map["flight_dir"]),
            "source_package": package_dir.name,
            "source_package_path": str(package_dir),
            "input_source_type": source.source_type,
            "input_source_filename": source_path.name,
            "input_source_path": str(source_path),
            "drone_manifest_path": (
                str(drone_manifest_path) if drone_manifest_path is not None else None
            ),
            "manifest_flight_datetime": acquisition_datetime_used,
            "input_h5_filename": source_path.name if source.source_type == "h5" else None,
            "input_h5_path": str(source_path) if source.source_type == "h5" else None,
            "base_name": flight_stem,
            "flags": {
                "topo_requested": bool(apply_topo),
                "brdf_requested": bool(apply_brdf),
                "ndvi_brdf_bins_enabled": bool(use_ndvi_brdf_bins),
                "topo_ready": False,
                "brdf_ready": False,
                "correction_failed": False,
                "brightness_requested": bool(apply_brightness_adjustment),
                "brightness_applied": False,
                "cloud_applied": False,
                "convolution_skipped": True,
            },
            "working_h5_filename": prepared_h5_path.name,
            "working_h5_path": str(prepared_h5_path),
            "working_raster": str(envi_stem.with_suffix(".img").name),
            "working_raster_path": str(envi_stem.with_suffix(".img")),
            "corrected_raster": str(corrected_stem.with_suffix(".img").name),
            "corrected_raster_path": str(corrected_stem.with_suffix(".img")),
            "polygon_filename": (
                polygon_output_path.name if polygon_path is not None else None
            ),
            "polygon_path": str(polygon_output_path) if polygon_path is not None else None,
            "polygon_csv_filename": None,
            "polygon_csv_path": None,
            "polygon_csv_error": None,
            "polygon_index_filename": polygon_index_path.name if polygon_path is not None else None,
            "polygon_index_path": str(polygon_index_path) if polygon_path is not None else None,
            "overlay_debug_filename": (
                overlay_debug_path.name if polygon_path is not None else None
            ),
            "overlay_debug_path": str(overlay_debug_path) if polygon_path is not None else None,
            "qa_plot_filename": path_map["qa_png"].name,
            "qa_json_filename": path_map["qa_json"].name,
            "qa_plot_path": str(path_map["qa_png"]),
            "qa_json_path": str(path_map["qa_json"]),
            "merged_filename": None,
            "merged_csv_filename": None,
            "merged_csv_path": None,
            "merged_csv_error": None,
            "correction_failure_reason": None,
            "correction_status_source": "live_run",
            "polygon_extraction_attempted": False,
            "polygon_extraction_ran": False,
            "polygon_extraction_skipped_reason": None,
            "status": None,
        }
        try:
            prepared_h5_path, nodata_patched = _prepare_drone_source_working_h5(
                source_path,
                source_type=source.source_type,
                working_path=prepared_h5_path,
                overwrite=overwrite,
                tiff_wavelengths_nm=tiff_wavelengths_nm,
                tiff_fwhm_nm=tiff_fwhm_nm,
                tiff_solar_zenith_deg=tiff_solar_zenith_deg,
                tiff_solar_azimuth_deg=tiff_solar_azimuth_deg,
                tiff_sensor_zenith_deg=tiff_sensor_zenith_deg,
                tiff_sensor_azimuth_deg=tiff_sensor_azimuth_deg,
                acquisition_datetime=acquisition_datetime,
                require_solar_geometry=bool(require_solar_geometry)
                and (bool(apply_topo) or bool(apply_brdf)),
            )
            file_audit["prepared_h5_filename"] = prepared_h5_path.name
            file_audit["prepared_h5_path"] = str(prepared_h5_path)
            file_audit["nodata_patch_applied"] = bool(nodata_patched)
            solar_geometry_summary = summarize_drone_h5_solar_geometry(prepared_h5_path)
            file_audit.update(solar_geometry_summary)
            if (
                bool(require_solar_geometry)
                and (bool(apply_topo) or bool(apply_brdf))
                and solar_geometry_summary.get("solar_geometry_source") == "missing"
            ):
                raise RuntimeError(
                    "Drone correction requested but no solar geometry is available. "
                    "Provide solar_zenith/solar_azimuth TIFFs, scalar solar angles, "
                    "or a drone_manifest_path with acquisition datetime values; "
                    "set require_solar_geometry=False to permit an uncorrected fallback."
                )

            cube = NeonCube(h5_path=prepared_h5_path)
            meta = validate_drone_h5_metadata(prepared_h5_path)
            band_map = resolve_band_map(meta["wavelengths"], DRONE_TARGET_BANDS)
            file_audit["resolved_band_map"] = band_map
            file_audit["metadata"] = {
                "lines": meta["lines"],
                "samples": meta["samples"],
                "bands": meta["bands"],
                "wavelength_units": meta["wavelength_units"],
                "nodata": meta["nodata"],
            }

            if batch_bar is not None:
                batch_bar.set_postfix_str(
                    f"{index}/{total_flights} {flight_stem} | converting to ENVI"
                )
            envi_img, envi_hdr = export_h5_to_envi(
                prepared_h5_path,
                output_stem=envi_stem,
                brightness_offset=0.0,
                overwrite=overwrite,
                cube=cube,
            )
            config = build_drone_config(
                h5_path=prepared_h5_path,
                envi_img=envi_img,
                envi_hdr=envi_hdr,
                corrected_img=corrected_stem.with_suffix(".img"),
                corrected_hdr=corrected_stem.with_suffix(".hdr"),
                wavelengths=meta["wavelengths"],
                fwhm=meta["fwhm"],
                band_map=band_map,
                apply_topo=apply_topo,
                apply_brdf=apply_brdf,
                use_ndvi_brdf_bins=use_ndvi_brdf_bins,
            )
            if batch_bar is not None:
                batch_bar.set_postfix_str(
                    f"{index}/{total_flights} {flight_stem} | correcting"
                )
            corrected_img, corrected_hdr, correction_audit = apply_drone_corrections(
                cube=cube,
                envi_img=envi_img,
                envi_hdr=envi_hdr,
                corrected_stem=corrected_stem,
                apply_topo=bool(config["apply_topo"]),
                apply_brdf=bool(config["apply_brdf"]),
                use_ndvi_brdf_bins=bool(config["use_ndvi_brdf_bins"]),
                overwrite=overwrite,
            )
            file_audit["flags"].update(
                {
                    "topo_ready": bool(correction_audit.get("topo_ready", False)),
                    "brdf_ready": bool(correction_audit.get("brdf_ready", False)),
                    "topo_applied": bool(correction_audit.get("topo_applied", False)),
                    "brdf_applied": bool(correction_audit.get("brdf_applied", False)),
                    "reused_existing_corrected": bool(
                        correction_audit.get("reused_existing_corrected", False)
                    ),
                    "topo_fallback_due_to_nodata": bool(
                        correction_audit.get("topo_fallback_due_to_nodata", False)
                    ),
                    "brdf_fallback_due_to_nodata": bool(
                        correction_audit.get("brdf_fallback_due_to_nodata", False)
                    ),
                    "brightness_applied": False,
                    "cloud_applied": False,
                    "convolution_skipped": True,
                }
            )
            file_audit["correction_status_source"] = str(
                correction_audit.get("correction_status_source", "live_run")
            )
            if correction_audit.get("reused_existing_corrected", False):
                _drone_emit(
                    f"[drone] [{index}/{total_flights}] {flight_stem} "
                    "reusing previously corrected output.",
                    status=None,
                )
            elif not correction_audit.get("topo_applied", False) and not correction_audit.get(
                "brdf_applied", False
            ):
                _drone_emit(
                    f"[drone] [{index}/{total_flights}] {flight_stem} "
                    "no correction was applied; reusing raw reflectance because the "
                    "required ancillary geometry was unavailable.",
                    status=None,
                )
            file_audit["corrected_raster"] = corrected_img.name
            file_audit["corrected_raster_path"] = str(corrected_img)

            if polygon_path is not None:
                if batch_bar is not None:
                    batch_bar.set_postfix_str(
                        f"{index}/{total_flights} {flight_stem} | polygon extraction"
                    )
                spatial_diagnostics = collect_drone_spatial_diagnostics(
                    raster_img=corrected_img,
                    polygons_path=polygon_path,
                )
                file_audit["spatial_diagnostics"] = spatial_diagnostics
                _drone_emit(
                    f"[drone] [{index}/{total_flights}] {flight_stem} "
                    f"raster_crs={spatial_diagnostics.get('raster_crs')} "
                    f"polygon_crs={spatial_diagnostics.get('polygon_crs')} "
                    f"reprojected={spatial_diagnostics.get('polygon_reprojected')} "
                    f"overlap_after_reproject={spatial_diagnostics.get('bounds_overlap_after_reproject')} "
                    f"intersecting_polygons={spatial_diagnostics.get('intersecting_polygon_count')}"
                )
                try:
                    save_drone_overlay_debug_plot(
                        polygons_path=polygon_path,
                        raster_bounds=spatial_diagnostics["raster_bounds"],
                        raster_crs=spatial_diagnostics["raster_crs"],
                        output_path=overlay_debug_path,
                    )
                except Exception as plot_exc:
                    LOGGER.warning(
                        "[drone] Overlay debug plot failed for %s: %s",
                        source_path,
                        plot_exc,
                    )
                    file_audit["overlay_debug_error"] = str(plot_exc)
                file_audit["polygon_extraction_attempted"] = True
                try:
                    index_path = _build_polygon_pixel_index_for_raster(
                        raster_img=corrected_img,
                        raster_hdr=corrected_hdr,
                        polygons_path=polygon_path,
                        output_path=polygon_index_path,
                        flight_id=flight_stem,
                        overwrite=overwrite,
                    )
                    polygon_parquet = extract_polygon_parquet_from_envi(
                        corrected_img,
                        corrected_hdr,
                        index_path,
                        polygon_output_path,
                        overwrite=overwrite,
                    )
                    polygon_parquet = _enrich_drone_polygon_parquet_with_index(
                        polygon_parquet,
                        index_path,
                        overwrite=True,
                    )
                    polygon_csv, polygon_csv_error = _try_export_csv_copy_from_parquet(
                        polygon_parquet,
                        overwrite=overwrite,
                        context_label=f"{flight_stem} polygon parquet",
                    )
                    results["outputs"].append(str(polygon_parquet))
                    file_audit["polygon_extraction_ran"] = True
                    file_audit["polygon_filename"] = polygon_parquet.name
                    file_audit["polygon_path"] = str(polygon_parquet)
                    file_audit["polygon_csv_filename"] = (
                        polygon_csv.name if polygon_csv is not None else None
                    )
                    file_audit["polygon_csv_path"] = (
                        str(polygon_csv) if polygon_csv is not None else None
                    )
                    file_audit["polygon_csv_error"] = polygon_csv_error
                    file_audit["polygon_index_filename"] = index_path.name
                    file_audit["polygon_index_path"] = str(index_path)
                    file_audit["status"] = _DRONE_STATUS_SUCCESS_EXTRACTED
                except Exception as polygon_exc:
                    _, polygon_reason = _classify_drone_exception(polygon_exc)
                    if any(marker in polygon_reason for marker in _DRONE_NO_OVERLAP_REASONS):
                        file_audit["status"] = _DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP
                        file_audit["polygon_extraction_skipped_reason"] = polygon_reason
                        file_audit["polygon_filename"] = None
                        file_audit["polygon_path"] = None
                        file_audit["polygon_csv_filename"] = None
                        file_audit["polygon_csv_path"] = None
                        file_audit["polygon_csv_error"] = None
                        LOGGER.warning(
                            "[drone] No polygon overlap for %s: raster_crs=%s polygon_crs=%s overlap_after_reproject=%s intersecting_polygons=%s reason=%s",
                            source_path,
                            spatial_diagnostics.get("raster_crs"),
                            spatial_diagnostics.get("polygon_crs"),
                            spatial_diagnostics.get("bounds_overlap_after_reproject"),
                            spatial_diagnostics.get("intersecting_polygon_count"),
                            polygon_reason,
                        )
                    else:
                        raise polygon_exc
            else:
                file_audit["polygon_filename"] = None
                file_audit["polygon_path"] = None
                file_audit["polygon_csv_filename"] = None
                file_audit["polygon_csv_path"] = None
                file_audit["polygon_csv_error"] = None
                file_audit["polygon_extraction_skipped_reason"] = "no polygons provided"
                file_audit["status"] = _DRONE_STATUS_SUCCESS_QA_ONLY_NO_POLYGONS

            results["processed"].append(str(source_path))
            if file_audit["status"] is None:
                file_audit["status"] = _DRONE_STATUS_SUCCESS_EXTRACTED
            elapsed = time.monotonic() - flight_started
            file_audit["elapsed_seconds"] = round(elapsed, 3)
            completed_flight_times.append(elapsed)
            status_counts[str(file_audit["status"])] += 1
            eta = _format_eta(completed_flight_times, total_flights - index)
            eta_suffix = f" | eta={eta}" if eta else ""
            _drone_emit(
                f"[drone] [{index}/{total_flights}] {flight_stem} -> "
                f"{file_audit['status']} ({_format_elapsed(elapsed)}){eta_suffix}",
                status=str(file_audit["status"]),
            )
        except Exception as exc:
            status, reason = _classify_drone_exception(exc)
            elapsed = time.monotonic() - flight_started
            if isinstance(exc, DroneCorrectionUnavailableError):
                correction_audit = exc.audit
                file_audit["flags"].update(
                    {
                        "topo_ready": bool(correction_audit.get("topo_ready", False)),
                        "brdf_ready": bool(correction_audit.get("brdf_ready", False)),
                        "topo_applied": bool(correction_audit.get("topo_applied", False)),
                        "brdf_applied": bool(correction_audit.get("brdf_applied", False)),
                        "reused_existing_corrected": bool(
                            correction_audit.get("reused_existing_corrected", False)
                        ),
                        "topo_fallback_due_to_nodata": bool(
                            correction_audit.get("topo_fallback_due_to_nodata", False)
                        ),
                        "brdf_fallback_due_to_nodata": bool(
                            correction_audit.get("brdf_fallback_due_to_nodata", False)
                        ),
                        "correction_failed": True,
                    }
                )
                file_audit["correction_status_source"] = str(
                    correction_audit.get("correction_status_source", "live_run")
                )
                file_audit["correction_failure_reason"] = reason
            file_audit["status"] = status
            file_audit["error"] = reason
            file_audit["elapsed_seconds"] = round(elapsed, 3)
            status_counts[status] += 1
            LOGGER.exception("[drone] FAILED for %s", source_path)
            results["failed"].append({"input": str(source_path), "error": reason})
            eta = _format_eta(completed_flight_times, total_flights - index)
            eta_suffix = f" | eta={eta}" if eta else ""
            suffix = f": {reason}" if reason else ""
            _drone_emit(
                f"[drone] [{index}/{total_flights}] {flight_stem} -> "
                f"{status}{suffix} ({_format_elapsed(elapsed)}){eta_suffix}",
                status=status,
            )
        finally:
            if batch_bar is not None:
                batch_bar.update(1)
                batch_bar.set_postfix_str(
                    f"{index}/{total_flights} {flight_stem} | finished"
                )
        _write_drone_audit_json(file_audit)
        results["qa_summary"]["files"].append(file_audit)

    if batch_bar is not None:
        batch_bar.close()

    if results["outputs"]:
        merged_path = _merge_drone_polygon_outputs(
            results["outputs"],
            output_dir / "drone_merged.parquet",
            overwrite=overwrite,
        )
        merged_csv_path, merged_csv_error = _try_export_csv_copy_from_parquet(
            merged_path,
            overwrite=overwrite,
            context_label="drone merged parquet",
        )
        results["merged"] = str(merged_path)
        results["merged_csv"] = str(merged_csv_path) if merged_csv_path is not None else None
        if merged_csv_error is not None:
            results["qa_summary"]["merged_csv_error"] = merged_csv_error
        for file_audit in results["qa_summary"]["files"]:
            file_audit["merged_filename"] = merged_path.name
            file_audit["merged_csv_filename"] = (
                merged_csv_path.name if merged_csv_path is not None else None
            )
            file_audit["merged_csv_path"] = (
                str(merged_csv_path) if merged_csv_path is not None else None
            )
            file_audit["merged_csv_error"] = merged_csv_error
    else:
        results["merged"] = None
        results["merged_csv"] = None

    try:
        from spectralbridge.qa_plots import render_drone_panel
        from spectralbridge.utils.qa_summary import build_drone_qa_summary

        for file_audit in results["qa_summary"]["files"]:
            if not _has_drone_qa_inputs(file_audit):
                continue
            raw_img = Path(str(file_audit["working_raster_path"]))
            corrected_img = Path(str(file_audit["corrected_raster_path"]))
            qa_png = Path(str(file_audit["qa_plot_path"]))
            _, qa_payload = render_drone_panel(
                raw_path=raw_img,
                corrected_path=corrected_img,
                output_png=qa_png,
                band_map=file_audit.get("resolved_band_map"),
                polygon_path=polygon_path,
                merged_path=Path(results["merged"]) if results["merged"] else None,
                qa_summary=file_audit,
                save_json=True,
            )
            file_audit["qa_plot_filename"] = qa_png.name
            file_audit["qa_json_filename"] = qa_png.with_suffix(".json").name
            file_audit["qa_plot_path"] = str(qa_png)
            file_audit["qa_json_path"] = str(qa_png.with_suffix(".json"))
            file_audit["qa_preview"] = {
                "nodata": qa_payload.get("nodata", {}),
                "polygon": qa_payload.get("polygon", {}),
                "merged_preview": qa_payload.get("merged_preview", {}),
            }
        qa_pngs = [
            Path(str(file_audit["qa_plot_path"]))
            for file_audit in results["qa_summary"]["files"]
            if Path(str(file_audit.get("qa_plot_path", ""))).exists()
        ]
        if qa_pngs:
            qa_summary_html = build_drone_qa_summary(output_dir)
            results["qa_summary"]["qa_summary_pdf"] = str(qa_summary_html)
            results["qa_summary"]["qa_summary_pdf_filename"] = qa_summary_html.name
            results["qa_summary_pdf"] = str(qa_summary_html)
    except Exception as exc:
        LOGGER.exception("[drone] QA rendering failed")
        results["qa_summary"]["qa_render_error"] = str(exc)

    total_wall_time = time.monotonic() - run_started
    avg_success_time = (
        round(sum(completed_flight_times) / len(completed_flight_times), 3)
        if completed_flight_times
        else None
    )
    results["qa_summary"]["status_counts"] = status_counts
    results["qa_summary"]["success_count"] = (
        status_counts[_DRONE_STATUS_SUCCESS_EXTRACTED]
        + status_counts[_DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP]
        + status_counts[_DRONE_STATUS_SUCCESS_QA_ONLY_NO_POLYGONS]
    )
    results["qa_summary"]["success_extracted_count"] = status_counts[
        _DRONE_STATUS_SUCCESS_EXTRACTED
    ]
    results["qa_summary"]["success_qa_only_no_polygon_overlap_count"] = status_counts[
        _DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP
    ]
    results["qa_summary"]["success_qa_only_no_polygons_count"] = status_counts[
        _DRONE_STATUS_SUCCESS_QA_ONLY_NO_POLYGONS
    ]
    results["qa_summary"]["skipped_no_polygon_overlap_count"] = status_counts[
        _DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP
    ]
    results["qa_summary"]["failed_other_count"] = status_counts[
        _DRONE_STATUS_FAILED_OTHER
    ]
    results["qa_summary"]["total_wall_time_seconds"] = round(total_wall_time, 3)
    results["qa_summary"]["average_successful_flight_seconds"] = avg_success_time
    results["qa_summary"]["merged_path"] = results["merged"]
    qa_path = _write_json(output_dir / "drone_qa_summary.json", results["qa_summary"])
    results["qa_summary_path"] = str(qa_path)
    _drone_emit(
        "[drone] Complete: "
        f"{total_flights} total | "
        f"{results['qa_summary']['success_count']} success_total | "
        f"{status_counts[_DRONE_STATUS_SUCCESS_EXTRACTED]} success_extracted | "
        f"{status_counts[_DRONE_STATUS_SUCCESS_QA_ONLY_NO_OVERLAP]} success_qa_only_no_polygon_overlap | "
        f"{status_counts[_DRONE_STATUS_SUCCESS_QA_ONLY_NO_POLYGONS]} success_qa_only_no_polygons | "
        f"{status_counts[_DRONE_STATUS_FAILED_OTHER]} failed_other | "
        f"{_format_elapsed(total_wall_time)} total | "
        f"run_root={output_dir} | qa_summary={qa_path} | "
        f"merged={results['merged'] if results['merged'] else 'None'}"
    )
    return results


__all__ = [
    "DRONE_TARGET_BANDS",
    "build_drone_output_paths",
    "build_drone_config",
    "clean_name",
    "collect_drone_spatial_diagnostics",
    "convert_drone_tiff_to_h5",
    "derive_drone_flight_stem",
    "export_h5_to_envi",
    "load_drone_manifest",
    "lookup_flight_datetime",
    "resolve_band_map",
    "run_drone_pipeline",
    "save_drone_overlay_debug_plot",
    "summarize_drone_h5_solar_geometry",
    "validate_drone_h5_metadata",
]
