"""Optional Landsat acquisition and common-support drone validation.

The core drone pipeline does not depend on this module succeeding.  Network
search, remote COG access, cloud screening, and optional NEON comparison are QA
activities performed only after valid Landsat-like drone products exist.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

import numpy as np

from spectralbridge.drone_translation import DroneTranslationPlan


PLANETARY_COMPUTER_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
LANDSAT_COLLECTION = "landsat-c2-l2"
LANDSAT_SURFACE_REFLECTANCE_SCALE = 0.0000275
LANDSAT_SURFACE_REFLECTANCE_OFFSET = -0.2
LANDSAT_CACHE_SCHEMA_VERSION = 2

_COMMON_NAMES = {
    "Landsat_5_TM": ("blue", "green", "red", "nir08"),
    "Landsat_7_ETM+": ("blue", "green", "red", "nir08"),
    "Landsat_8_OLI": ("coastal", "blue", "green", "red", "nir08"),
    "Landsat_9_OLI-2": ("coastal", "blue", "green", "red", "nir08"),
}
_TARGET_WAVELENGTHS = {
    "Landsat_5_TM": (485.0, 575.0, 660.0, 837.5),
    "Landsat_7_ETM+": (482.5, 565.0, 660.0, 837.5),
    "Landsat_8_OLI": (443.0, 482.0, 561.4, 654.6, 864.7),
    "Landsat_9_OLI-2": (442.8, 481.9, 561.0, 654.3, 864.6),
}


@dataclass(frozen=True)
class LandsatObservation:
    """A cropped, QA-masked actual Landsat surface-reflectance product."""

    product_id: str
    target_sensor: str
    acquisition_datetime: str | None
    cloud_cover: float | None
    raster_path: str
    metadata_path: str | None
    source: str
    temporal_offset_days: float | None
    band_common_names: tuple[str, ...]
    target_band_indices: tuple[int, ...]
    wavelengths_nm: tuple[float, ...]
    scene_selection: str


def _sensor_from_text(value: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "", value.lower())
    if any(token in normalized for token in ("landsat9", "lc09", "oli2")):
        return "Landsat_9_OLI-2"
    if any(token in normalized for token in ("landsat8", "lc08", "l8oli")):
        return "Landsat_8_OLI"
    if any(token in normalized for token in ("landsat7", "le07", "etm")):
        return "Landsat_7_ETM+"
    if any(token in normalized for token in ("landsat5", "lt05", "l5tm")):
        return "Landsat_5_TM"
    return None


def _item_sensor(item: Any) -> str | None:
    properties = getattr(item, "properties", {}) or {}
    candidates = [
        str(getattr(item, "id", "")),
        str(properties.get("platform", "")),
        str(properties.get("constellation", "")),
        " ".join(str(value) for value in properties.get("instruments", []) or []),
    ]
    for candidate in candidates:
        sensor = _sensor_from_text(candidate)
        if sensor is not None:
            return sensor
    return None


def _asset_common_name(key: str, asset: Any) -> str | None:
    extra = getattr(asset, "extra_fields", {}) or {}
    bands = extra.get("eo:bands") or []
    if bands and isinstance(bands[0], dict) and bands[0].get("common_name"):
        return str(bands[0]["common_name"])
    lowered = key.lower()
    aliases = {
        "qa_pixel": "qa_pixel",
        "qa": "qa_pixel",
        "blue": "blue",
        "green": "green",
        "red": "red",
        "nir08": "nir08",
        "nir": "nir08",
        "coastal": "coastal",
    }
    return aliases.get(lowered)


def _asset_scale_offset(asset: Any) -> tuple[float, float, float | None]:
    extra = getattr(asset, "extra_fields", {}) or {}
    bands = extra.get("raster:bands") or []
    band = bands[0] if bands and isinstance(bands[0], dict) else {}
    scale = float(band.get("scale", LANDSAT_SURFACE_REFLECTANCE_SCALE))
    offset = float(band.get("offset", LANDSAT_SURFACE_REFLECTANCE_OFFSET))
    nodata = band.get("nodata")
    return scale, offset, float(nodata) if nodata is not None else None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        try:
            result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _absolute_offset_days(first: Any, second: Any) -> float | None:
    first_parsed = _parse_datetime(first)
    second_parsed = _parse_datetime(second)
    if first_parsed is None or second_parsed is None:
        return None
    return abs((first_parsed - second_parsed).total_seconds()) / 86400.0


def _clear_landsat_mask(qa: np.ndarray) -> np.ndarray:
    """Return valid Collection 2 QA_PIXEL support.

    Bits 0--5 represent fill, dilated cloud, cirrus, cloud, cloud shadow, and
    snow.  Keeping only pixels where all six are clear is conservative across
    Landsat 5--9; non-applicable bits remain zero.
    """

    qa_int = np.asarray(qa, dtype=np.uint16)
    return (qa_int & np.uint16(0b11_1111)) == 0


def _write_observation_metadata(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _landsat_cache_signature(
    *,
    product_id: str,
    target_sensor: str,
    bounds_wgs84: Sequence[float],
    temporal_offset_days: float | None,
    cloud_cover: float | None,
) -> tuple[str, dict[str, Any]]:
    """Return the deterministic request contract for one cached STAC crop."""

    payload = {
        "schema_version": LANDSAT_CACHE_SCHEMA_VERSION,
        "product_id": str(product_id),
        "target_sensor": target_sensor,
        "bounds_wgs84": [float(value) for value in bounds_wgs84],
        "temporal_offset_days": temporal_offset_days,
        "cloud_cover": cloud_cover,
        "band_common_names": list(_COMMON_NAMES[target_sensor]),
        "wavelengths_nm": list(_TARGET_WAVELENGTHS[target_sensor]),
        "qa_pixel_clear_rule": "bits 0 through 5 must all be zero",
        "surface_reflectance_fallback_scale": LANDSAT_SURFACE_REFLECTANCE_SCALE,
        "surface_reflectance_fallback_offset": LANDSAT_SURFACE_REFLECTANCE_OFFSET,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest(), payload


def _load_cached_stac_observation(
    *,
    raster_path: Path,
    metadata_path: Path,
    expected_signature: str,
    product_id: str,
    target_sensor: str,
) -> LandsatObservation | None:
    """Load a cache entry only when its request and raster contract validate."""

    if not raster_path.is_file() or not metadata_path.is_file():
        return None
    try:
        import rasterio

        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != LANDSAT_CACHE_SCHEMA_VERSION:
            return None
        if payload.get("cache_signature_sha256") != expected_signature:
            return None
        observation_payload = payload["observation"]
        if (
            observation_payload.get("product_id") != str(product_id)
            or observation_payload.get("target_sensor") != target_sensor
            or Path(observation_payload.get("raster_path", "")) != raster_path
            or Path(observation_payload.get("metadata_path", "")) != metadata_path
        ):
            return None
        required = _COMMON_NAMES[target_sensor]
        with rasterio.open(raster_path) as source:
            if source.count != len(required) or source.width < 1 or source.height < 1:
                return None
            if source.tags().get("product_id") != str(product_id):
                return None
            if source.tags().get("target_sensor") != target_sensor:
                return None
            if tuple(source.descriptions) != tuple(required):
                return None
        for field in (
            "band_common_names",
            "target_band_indices",
            "wavelengths_nm",
        ):
            observation_payload[field] = tuple(observation_payload[field])
        return LandsatObservation(**observation_payload)
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _crop_stac_item(
    item: Any,
    *,
    target_sensor: str,
    bounds_wgs84: tuple[float, float, float, float],
    output_dir: Path,
    temporal_offset_days: float | None,
    cloud_cover: float | None,
) -> LandsatObservation:
    import planetary_computer
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds

    signed = planetary_computer.sign(item)
    assets_by_common: dict[str, Any] = {}
    qa_asset = None
    for key, asset in signed.assets.items():
        common_name = _asset_common_name(key, asset)
        if common_name == "qa_pixel":
            qa_asset = asset
        elif common_name:
            assets_by_common[common_name] = asset
    required = _COMMON_NAMES[target_sensor]
    missing = [name for name in required if name not in assets_by_common]
    if missing:
        raise ValueError(
            f"Landsat item {item.id} lacks required surface-reflectance assets: {missing}"
        )
    if qa_asset is None:
        raise ValueError(f"Landsat item {item.id} lacks a QA_PIXEL asset")

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(item.id))
    raster_path = output_dir / f"{safe_id}__surface_reflectance_crop.tif"
    metadata_path = output_dir / f"{safe_id}__observation.json"
    cache_signature, cache_contract = _landsat_cache_signature(
        product_id=str(item.id),
        target_sensor=target_sensor,
        bounds_wgs84=bounds_wgs84,
        temporal_offset_days=temporal_offset_days,
        cloud_cover=cloud_cover,
    )
    cached = _load_cached_stac_observation(
        raster_path=raster_path,
        metadata_path=metadata_path,
        expected_signature=cache_signature,
        product_id=str(item.id),
        target_sensor=target_sensor,
    )
    if cached is not None:
        return cached

    reference_asset = assets_by_common[required[0]]
    with rasterio.open(reference_asset.href) as reference:
        projected_bounds = transform_bounds(
            "EPSG:4326", reference.crs, *bounds_wgs84, densify_pts=21
        )
        window = from_bounds(*projected_bounds, transform=reference.transform)
        window = window.round_offsets().round_lengths()
        full_window = rasterio.windows.Window(0, 0, reference.width, reference.height)
        try:
            window = window.intersection(full_window)
        except rasterio.errors.WindowError as exc:
            raise ValueError(f"Landsat item {item.id} has no raster overlap") from exc
        if window.width < 1 or window.height < 1:
            raise ValueError(f"Landsat item {item.id} has no raster overlap")
        transform = reference.window_transform(window)
        profile = reference.profile.copy()
        profile.update(
            driver="GTiff",
            dtype="float32",
            count=len(required),
            width=int(window.width),
            height=int(window.height),
            transform=transform,
            nodata=-9999.0,
            compress="deflate",
            tiled=True,
        )

    with rasterio.open(qa_asset.href) as qa_source:
        qa = qa_source.read(1, window=window)
    clear = _clear_landsat_mask(qa)
    if not np.any(clear):
        raise ValueError(
            f"Landsat item {item.id} has no clear QA_PIXEL support over the drone footprint"
        )
    with rasterio.open(raster_path, "w", **profile) as destination:
        destination.update_tags(
            product_id=str(item.id),
            target_sensor=target_sensor,
            product_semantics="actual_landsat_collection_2_level_2_surface_reflectance",
        )
        for output_index, common_name in enumerate(required, start=1):
            asset = assets_by_common[common_name]
            scale, offset, asset_nodata = _asset_scale_offset(asset)
            with rasterio.open(asset.href) as source:
                raw = source.read(1, window=window)
                valid = clear & np.isfinite(raw)
                nodata = source.nodata if source.nodata is not None else asset_nodata
                if nodata is not None:
                    valid &= raw != nodata
                values = raw.astype(np.float32) * np.float32(scale) + np.float32(offset)
                values = np.where(valid, values, np.float32(-9999.0))
            destination.write(values.astype(np.float32), output_index)
            destination.set_band_description(output_index, common_name)

    properties = getattr(item, "properties", {}) or {}
    acquired = _parse_datetime(
        properties.get("datetime") or getattr(item, "datetime", None)
    )
    observation = LandsatObservation(
        product_id=str(item.id),
        target_sensor=target_sensor,
        acquisition_datetime=acquired.isoformat() if acquired else None,
        cloud_cover=cloud_cover,
        raster_path=str(raster_path),
        metadata_path=str(metadata_path),
        source="planetary_computer_stac",
        temporal_offset_days=temporal_offset_days,
        band_common_names=tuple(required),
        target_band_indices=tuple(range(1, len(required) + 1)),
        wavelengths_nm=_TARGET_WAVELENGTHS[target_sensor],
        scene_selection=(
            "minimum absolute acquisition-time offset among spatially overlapping "
            "Collection 2 Level 2 scenes passing cloud-cover and required-asset checks"
        ),
    )
    _write_observation_metadata(
        metadata_path,
        {
            "schema_version": LANDSAT_CACHE_SCHEMA_VERSION,
            "cache_signature_sha256": cache_signature,
            "cache_contract": cache_contract,
            "observation": asdict(observation),
            "stac_url": PLANETARY_COMPUTER_STAC,
            "collection": LANDSAT_COLLECTION,
            "bounds_wgs84": bounds_wgs84,
            "qa_pixel_clear_rule": "bits 0 through 5 must all be zero",
            "surface_reflectance_fallback_scale": LANDSAT_SURFACE_REFLECTANCE_SCALE,
            "surface_reflectance_fallback_offset": LANDSAT_SURFACE_REFLECTANCE_OFFSET,
        },
    )
    return observation


def acquire_landsat_observation(
    *,
    bounds_wgs84: Sequence[float],
    acquisition_datetime: datetime | str,
    search_days: int,
    target_sensors: Iterable[str],
    output_dir: str | Path,
    cloud_cover_max: float = 50.0,
) -> LandsatObservation | None:
    """Discover and cache the best overlapping Landsat Collection 2 L2 crop."""

    try:
        from pystac_client import Client
        import planetary_computer
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Landsat search requires the optional 'landsat' dependencies. Install "
            "with `pip install earthlab-spectralbridge[landsat]`."
        ) from exc

    acquired = _parse_datetime(acquisition_datetime)
    if acquired is None:
        raise ValueError("A valid drone acquisition_datetime is required for Landsat search")
    if len(bounds_wgs84) != 4:
        raise ValueError("bounds_wgs84 must contain minx, miny, maxx, maxy")
    start = acquired - timedelta(days=int(search_days))
    end = acquired + timedelta(days=int(search_days))
    client = Client.open(
        PLANETARY_COMPUTER_STAC,
        modifier=planetary_computer.sign_inplace,
    )
    search = client.search(
        collections=[LANDSAT_COLLECTION],
        bbox=tuple(float(value) for value in bounds_wgs84),
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        query={"eo:cloud_cover": {"lte": float(cloud_cover_max)}},
    )
    allowed = set(target_sensors)
    candidates: list[tuple[float, float, Any, str]] = []
    for item in search.items():
        sensor = _item_sensor(item)
        if sensor is None or sensor not in allowed:
            continue
        properties = getattr(item, "properties", {}) or {}
        item_datetime = _parse_datetime(
            properties.get("datetime") or getattr(item, "datetime", None)
        )
        if item_datetime is None:
            continue
        offset = abs((item_datetime - acquired).total_seconds()) / 86400.0
        cloud = properties.get("eo:cloud_cover")
        cloud_value = float(cloud) if cloud is not None else math.inf
        if cloud_value > cloud_cover_max:
            continue
        candidates.append((offset, cloud_value, item, sensor))
    for offset, cloud, item, sensor in sorted(
        candidates, key=lambda value: (value[0], value[1], str(value[2].id))
    ):
        try:
            return _crop_stac_item(
                item,
                target_sensor=sensor,
                bounds_wgs84=tuple(float(value) for value in bounds_wgs84),
                output_dir=Path(output_dir),
                temporal_offset_days=offset,
                cloud_cover=None if not math.isfinite(cloud) else cloud,
            )
        except (OSError, ValueError):
            continue
    return None


def load_supplied_landsat_observation(
    path: str | Path,
    *,
    target_sensors: Iterable[str],
) -> LandsatObservation:
    """Load an acquisition manifest or a user-supplied multiband raster."""

    import rasterio

    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Supplied Landsat product not found: {path}")
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        observation_payload = payload.get("observation", payload)
        observation = LandsatObservation(**observation_payload)
        if not Path(observation.raster_path).is_file():
            raise FileNotFoundError(
                f"Supplied Landsat manifest raster is missing: {observation.raster_path}"
            )
        return observation

    with rasterio.open(path) as source:
        tags = source.tags()
        descriptions = tuple(
            description or f"band_{index}"
            for index, description in enumerate(source.descriptions, start=1)
        )
        sensor = None
        for value in (
            tags.get("target_sensor"),
            tags.get("SPACECRAFT_ID"),
            tags.get("platform"),
            path.name,
        ):
            if value:
                sensor = _sensor_from_text(str(value))
                if sensor:
                    break
        if sensor is None:
            allowed = tuple(target_sensors)
            if len(allowed) == 1:
                sensor = allowed[0]
            else:
                raise ValueError(
                    "Could not determine the supplied Landsat sensor; add a "
                    "target_sensor raster tag or use a sensor-identifying filename"
                )
        required_count = len(_COMMON_NAMES[sensor])
        if source.count < required_count:
            raise ValueError(
                f"Supplied {sensor} product has {source.count} bands; expected at least {required_count}"
            )
        if not all(np.issubdtype(dtype, np.floating) for dtype in source.dtypes):
            raise ValueError(
                "Supplied Landsat raster must contain analysis-ready floating-point "
                "unitless surface reflectance; raw Collection 2 integer DNs are not accepted"
            )
        sample = source.read(1, masked=True, out_shape=(1, min(64, source.height), min(64, source.width)))
        finite_sample = np.asarray(sample.compressed(), dtype=np.float64)
        if finite_sample.size and (
            float(np.nanmin(finite_sample)) < -1.0
            or float(np.nanmax(finite_sample)) > 2.0
        ):
            raise ValueError(
                "Supplied Landsat raster values are outside the plausible unitless "
                "reflectance range; apply Collection 2 scale/offset first"
            )
    if sensor not in set(target_sensors):
        raise ValueError(
            f"Supplied Landsat sensor {sensor} has no corresponding drone translation"
        )
    return LandsatObservation(
        product_id=tags.get("product_id", path.stem),
        target_sensor=sensor,
        acquisition_datetime=tags.get("acquisition_datetime"),
        cloud_cover=(
            float(tags["cloud_cover"])
            if tags.get("cloud_cover") is not None
            else None
        ),
        raster_path=str(path),
        metadata_path=None,
        source="user_supplied",
        temporal_offset_days=None,
        band_common_names=descriptions[:required_count],
        target_band_indices=tuple(range(1, required_count + 1)),
        wavelengths_nm=_TARGET_WAVELENGTHS[sensor],
        scene_selection="user supplied product; no scene search performed",
    )


def raster_bounds_wgs84(path: str | Path) -> tuple[float, float, float, float]:
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.open(path) as source:
        if source.crs is None:
            raise ValueError(f"Raster has no CRS: {path}")
        return tuple(
            float(value)
            for value in transform_bounds(
                source.crs, "EPSG:4326", *source.bounds, densify_pts=21
            )
        )


def raster_acquisition_datetime(path: str | Path) -> str | None:
    """Read an acquisition timestamp tag or conservative YYYYMMDD filename token."""

    import rasterio

    path = Path(path)
    with rasterio.open(path) as source:
        tags = source.tags()
    for key in ("acquisition_datetime", "datetime", "ACQUISITION_DATE"):
        parsed = _parse_datetime(tags.get(key))
        if parsed is not None:
            return parsed.isoformat()
    match = re.search(r"(?<!\d)(20\d{6})(?!\d)", path.name)
    if match:
        try:
            parsed = datetime.strptime(match.group(1), "%Y%m%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return None
        return parsed.isoformat()
    return None


def _pair_metrics(reference: np.ndarray, candidate: np.ndarray) -> dict[str, Any]:
    valid = np.isfinite(reference) & np.isfinite(candidate)
    x = candidate[valid].astype(np.float64)
    y = reference[valid].astype(np.float64)
    if x.size == 0:
        return {"sample_count": 0, "status": "insufficient_overlap"}
    residual = x - y
    metrics: dict[str, Any] = {
        "sample_count": int(x.size),
        "status": "ok" if x.size >= 2 else "insufficient_overlap",
        "mean_bias": float(np.mean(residual)),
        "median_bias": float(np.median(residual)),
        "mae": float(np.mean(np.abs(residual))),
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "residual_std": float(np.std(residual)),
        "residual_q05": float(np.quantile(residual, 0.05)),
        "residual_q25": float(np.quantile(residual, 0.25)),
        "residual_q75": float(np.quantile(residual, 0.75)),
        "residual_q95": float(np.quantile(residual, 0.95)),
        "median_percent_difference": float(
            np.median(100.0 * residual[np.abs(y) > 1e-8] / y[np.abs(y) > 1e-8])
        )
        if np.any(np.abs(y) > 1e-8)
        else None,
    }
    if x.size >= 2 and not np.isclose(np.var(x), 0.0):
        slope, intercept = np.polyfit(x, y, 1)
        metrics["fitted_slope"] = float(slope)
        metrics["fitted_intercept"] = float(intercept)
        metrics["correlation"] = float(np.corrcoef(x, y)[0, 1])
    else:
        metrics.update(
            fitted_slope=None, fitted_intercept=None, correlation=None
        )
    return metrics


def _aggregate_to_reference_grid(
    source_path: Path,
    *,
    source_band_indices: Sequence[int],
    reference: Any,
    valid_fraction_threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    import rasterio
    from rasterio.warp import Resampling, reproject

    arrays: list[np.ndarray] = []
    support_arrays: list[np.ndarray] = []
    with rasterio.open(source_path) as source:
        source_nodata = source.nodata
        for band_index in source_band_indices:
            values = source.read(int(band_index)).astype(np.float32)
            valid = np.isfinite(values)
            if source_nodata is not None:
                valid &= values != source_nodata
            destination = np.full(
                (reference.height, reference.width), np.nan, dtype=np.float32
            )
            support = np.zeros_like(destination)
            reproject(
                source=np.where(valid, values, np.nan),
                destination=destination,
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=np.nan,
                dst_transform=reference.transform,
                dst_crs=reference.crs,
                dst_nodata=np.nan,
                resampling=Resampling.average,
            )
            reproject(
                source=valid.astype(np.float32),
                destination=support,
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=None,
                dst_transform=reference.transform,
                dst_crs=reference.crs,
                dst_nodata=0.0,
                resampling=Resampling.average,
            )
            destination[support < valid_fraction_threshold] = np.nan
            arrays.append(destination)
            support_arrays.append(support)
    return np.stack(arrays), np.stack(support_arrays)


def compare_landsat_common_support(
    *,
    translated_img: str | Path,
    plan: DroneTranslationPlan,
    observation: LandsatObservation,
    output_dir: str | Path,
    neon_product: str | Path | None = None,
    drone_acquisition_datetime: str | None = None,
    neon_acquisition_datetime: str | None = None,
    valid_fraction_threshold: float = 0.5,
) -> dict[str, Any]:
    """Aggregate drone/optional NEON products to the actual Landsat grid."""

    import rasterio

    translated_img = Path(translated_img)
    actual_path = Path(observation.raster_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(translated_img) as drone_source:
        drone_resolution = tuple(float(value) for value in drone_source.res)
    neon_resolution = None
    if neon_product is not None:
        with rasterio.open(neon_product) as neon_source:
            neon_resolution = tuple(float(value) for value in neon_source.res)
    with rasterio.open(actual_path) as actual_source:
        actual_resolution = tuple(float(value) for value in actual_source.res)
        selected_actual_bands = list(observation.target_band_indices)
        raw_actual = actual_source.read(selected_actual_bands)
        actual_valid = np.isfinite(raw_actual)
        if actual_source.nodata is not None:
            actual_valid &= raw_actual != actual_source.nodata
        scales = [
            float(actual_source.scales[index - 1])
            for index in selected_actual_bands
        ]
        offsets = [
            float(actual_source.offsets[index - 1])
            for index in selected_actual_bands
        ]
        scaling_source = "raster_metadata"
        if np.issubdtype(raw_actual.dtype, np.integer) and all(
            np.isclose(scale, 1.0) for scale in scales
        ) and all(np.isclose(offset, 0.0) for offset in offsets):
            scales = [LANDSAT_SURFACE_REFLECTANCE_SCALE] * len(
                selected_actual_bands
            )
            offsets = [LANDSAT_SURFACE_REFLECTANCE_OFFSET] * len(
                selected_actual_bands
            )
            scaling_source = "landsat_collection_2_level_2_fallback"
        actual = np.empty(raw_actual.shape, dtype=np.float32)
        for index, (scale, offset) in enumerate(
            zip(scales, offsets, strict=True)
        ):
            actual[index] = (
                raw_actual[index].astype(np.float32) * np.float32(scale)
                + np.float32(offset)
            )
        actual[~actual_valid] = np.nan
        drone, drone_support = _aggregate_to_reference_grid(
            translated_img,
            source_band_indices=tuple(range(1, len(plan.bands) + 1)),
            reference=actual_source,
            valid_fraction_threshold=valid_fraction_threshold,
        )
        neon = None
        neon_support = None
        if neon_product is not None:
            neon, neon_support = _aggregate_to_reference_grid(
                Path(neon_product),
                source_band_indices=tuple(
                    band.target_band_index for band in plan.bands
                ),
                reference=actual_source,
                valid_fraction_threshold=valid_fraction_threshold,
            )

        profile = actual_source.profile.copy()
        profile.update(
            driver="GTiff",
            dtype="float32",
            count=drone.shape[0],
            nodata=-9999.0,
            compress="deflate",
        )
        common_path = output_dir / (
            translated_img.stem + "__on_actual_landsat_grid.tif"
        )
        with rasterio.open(common_path, "w", **profile) as destination:
            destination.write(np.where(np.isfinite(drone), drone, -9999.0))
            destination.update_tags(
                aggregation="valid-data-aware average",
                valid_fraction_threshold=valid_fraction_threshold,
                reference_landsat_product=observation.product_id,
            )
        neon_common_path = None
        if neon is not None:
            neon_common_path = output_dir / (
                Path(neon_product).stem + "__on_actual_landsat_grid.tif"
            )
            with rasterio.open(neon_common_path, "w", **profile) as destination:
                destination.write(np.where(np.isfinite(neon), neon, -9999.0))
                destination.update_tags(
                    aggregation="valid-data-aware average",
                    valid_fraction_threshold=valid_fraction_threshold,
                    reference_landsat_product=observation.product_id,
                )

    bands: list[dict[str, Any]] = []
    for index, band in enumerate(plan.bands):
        actual_band = actual[index]
        drone_band = drone[index]
        record: dict[str, Any] = {
            "target_band_index": band.target_band_index,
            "target_wavelength_nm": band.target_wavelength_nm,
            "drone_vs_actual": _pair_metrics(actual_band, drone_band),
            "drone_valid_overlap_fraction": float(
                np.mean(np.isfinite(actual_band) & np.isfinite(drone_band))
            ),
            "drone_mean_source_support": float(np.mean(drone_support[index])),
        }
        if neon is not None and neon_support is not None:
            neon_band = neon[index]
            record["neon_vs_actual"] = _pair_metrics(actual_band, neon_band)
            record["drone_vs_neon"] = _pair_metrics(neon_band, drone_band)
            record["neon_valid_overlap_fraction"] = float(
                np.mean(np.isfinite(actual_band) & np.isfinite(neon_band))
            )
            record["neon_mean_source_support"] = float(
                np.mean(neon_support[index])
            )
        bands.append(record)
    return {
        "schema_version": 1,
        "status": "ok",
        "actual_landsat": asdict(observation),
        "actual_landsat_scaling": {
            "source": scaling_source,
            "scales": scales,
            "offsets": offsets,
        },
        "target_sensor": plan.target_sensor,
        "translated_drone_product": str(translated_img),
        "comparison_neon_product": str(neon_product) if neon_product else None,
        "temporal_context": {
            "drone_acquisition_datetime": drone_acquisition_datetime,
            "actual_landsat_acquisition_datetime": observation.acquisition_datetime,
            "drone_to_landsat_offset_days": (
                observation.temporal_offset_days
                if observation.temporal_offset_days is not None
                else _absolute_offset_days(
                    drone_acquisition_datetime,
                    observation.acquisition_datetime,
                )
            ),
            "neon_acquisition_datetime": neon_acquisition_datetime,
            "neon_to_landsat_offset_days": _absolute_offset_days(
                neon_acquisition_datetime,
                observation.acquisition_datetime,
            ),
        },
        "common_grid": {
            "reference": "actual Landsat grid",
            "aggregation": "valid-data-aware average",
            "valid_fraction_threshold": valid_fraction_threshold,
            "nodata_treatment": "non-finite and declared nodata excluded",
            "common_support_product": str(common_path),
            "neon_common_support_product": (
                str(neon_common_path) if neon_common_path is not None else None
            ),
            "drone_source_resolution": drone_resolution,
            "actual_landsat_resolution": actual_resolution,
            "neon_source_resolution": neon_resolution,
        },
        "bands": bands,
    }


__all__ = [
    "LANDSAT_COLLECTION",
    "LANDSAT_SURFACE_REFLECTANCE_OFFSET",
    "LANDSAT_SURFACE_REFLECTANCE_SCALE",
    "LandsatObservation",
    "PLANETARY_COMPUTER_STAC",
    "acquire_landsat_observation",
    "compare_landsat_common_support",
    "load_supplied_landsat_observation",
    "raster_acquisition_datetime",
    "raster_bounds_wgs84",
]
