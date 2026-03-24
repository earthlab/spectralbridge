from __future__ import annotations

import json
import logging
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import duckdb
import h5py
import numpy as np
import pandas as pd

from spectralbridge.corrections import (
    apply_brdf_correct,
    apply_topo_correct,
    fit_and_save_brdf_model,
)
from spectralbridge.envi_writer import EnviWriter
from spectralbridge.neon_cube import NeonCube
from spectralbridge.polygons import (
    _write_dataframe_parquet,
    extract_polygon_parquet_from_envi,
    validate_coordinate_match,
)
from spectralbridge.progress_utils import TileProgressReporter
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
_DRONE_STATUS_SUCCESS = "success"
_DRONE_STATUS_NO_OVERLAP = "skipped_no_polygon_overlap"
_DRONE_STATUS_FAILED_OTHER = "failed_other"
_DRONE_NO_OVERLAP_REASONS = (
    "No pixels intersected the supplied polygons",
    "zero intersected pixels",
)
_ANSI_RESET = "\033[0m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_RED = "\033[31m"


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


def apply_drone_corrections(
    *,
    cube: NeonCube,
    envi_img: Path,
    envi_hdr: Path,
    corrected_stem: Path,
    apply_topo: bool,
    apply_brdf: bool,
    overwrite: bool = False,
) -> tuple[Path, Path, dict[str, Any]]:
    """Apply optional topo/BRDF corrections with conservative drone defaults."""

    corrected_img = corrected_stem.with_suffix(".img")
    corrected_hdr = corrected_stem.with_suffix(".hdr")
    audit = {
        "requested_topo": bool(apply_topo),
        "requested_brdf": bool(apply_brdf),
        "topo_applied": False,
        "brdf_applied": False,
        "brightness_applied": False,
        "cloud_mask_applied": False,
        "convolution_skipped": True,
    }

    if not overwrite and is_valid_envi_pair(corrected_img, corrected_hdr):
        return corrected_img, corrected_hdr, audit

    topo_ready = apply_topo and _has_required_ancillary(
        cube, ("slope", "aspect", "solar_zn", "solar_az")
    )
    brdf_ready = apply_brdf and _has_required_ancillary(
        cube, ("solar_zn", "solar_az", "sensor_zn", "sensor_az")
    )

    audit["topo_ready"] = topo_ready
    audit["brdf_ready"] = brdf_ready

    if not topo_ready and not brdf_ready:
        shutil.copy2(envi_img, corrected_img)
        shutil.copy2(envi_hdr, corrected_hdr)
        return corrected_img, corrected_hdr, audit

    coeff_path: Path | None = None
    if brdf_ready:
        coeff_path = fit_and_save_brdf_model(cube, corrected_stem.parent)

    header = cube.build_envi_header()
    header["description"] = (
        "Drone reflectance corrected with optional topo/BRDF adjustments"
    )
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
    try:
        for ys, ye, xs, xe, raw_chunk in cube.iter_chunks(
            chunk_y=chunk_y, chunk_x=chunk_x
        ):
            chunk = np.asarray(raw_chunk, dtype=np.float32)
            if topo_ready:
                chunk = apply_topo_correct(cube, chunk, ys, ye, xs, xe)
                audit["topo_applied"] = True
            if brdf_ready:
                chunk = apply_brdf_correct(
                    cube, chunk, ys, ye, xs, xe, coeff_path=coeff_path
                )
                audit["brdf_applied"] = True
            writer.write_chunk(chunk, ys, xs)
            reporter.update(1)
    finally:
        writer.close()
        reporter.close()

    if not is_valid_envi_pair(corrected_img, corrected_hdr):
        raise RuntimeError(
            f"Drone correction stage failed to produce a valid ENVI pair: {corrected_img} / {corrected_hdr}"
        )

    return corrected_img, corrected_hdr, audit


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


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


def _drone_status_color(status: str) -> str | None:
    if status == _DRONE_STATUS_SUCCESS:
        return _ANSI_GREEN
    if status == _DRONE_STATUS_NO_OVERLAP:
        return _ANSI_YELLOW
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
    if any(marker in reason for marker in _DRONE_NO_OVERLAP_REASONS):
        return _DRONE_STATUS_NO_OVERLAP, reason
    return _DRONE_STATUS_FAILED_OTHER, reason


def run_drone_pipeline(
    input_h5_dir: str | Path,
    polygon_path: str | Path | None = None,
    output_dir: str | Path = ".",
    apply_topo: bool = True,
    apply_brdf: bool = False,
    apply_brightness_adjustment: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Run the local-H5 drone pipeline with wavelength-driven band resolution and QA audit output."""

    run_started = time.monotonic()
    input_h5_dir = Path(input_h5_dir)
    output_dir = Path(output_dir)
    polygon_path = Path(polygon_path) if polygon_path is not None else None
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {
        "platform": "drone",
        "processed": [],
        "failed": [],
        "outputs": [],
        "merged": None,
        "qa_summary": {
            "platform": "drone",
            "convolution": "skipped",
            "brightness_offset": 0.0,
            "brightness_adjustment_requested": bool(apply_brightness_adjustment),
            "brightness_adjustment_applied": False,
            "cloud_mask_applied": False,
            "files": [],
        },
    }

    h5_files = sorted(input_h5_dir.rglob("*.h5"))
    results["qa_summary"]["discovered_total"] = len(h5_files)
    results["qa_summary"]["attempted_total"] = len(h5_files)
    results["qa_summary"]["run_root"] = str(output_dir)
    results["qa_summary"]["polygon_path"] = (
        str(polygon_path) if polygon_path is not None else None
    )
    if not h5_files:
        qa_path = _write_json(
            output_dir / "drone_qa_summary.json", results["qa_summary"]
        )
        results["qa_summary_path"] = str(qa_path)
        return results

    flight_stems: dict[Path, str] = {}
    stem_sources: dict[str, Path] = {}
    for h5_path in h5_files:
        flight_stem = derive_drone_flight_stem(h5_path)
        existing_source = stem_sources.get(flight_stem)
        if existing_source is not None and existing_source != h5_path:
            raise ValueError(
                "Duplicate drone flight stem derived within one run: "
                f"{flight_stem} from {existing_source} and {h5_path}. "
                "Package-folder naming must remain unique per flight."
            )
        flight_stems[h5_path] = flight_stem
        stem_sources[flight_stem] = h5_path

    total_flights = len(h5_files)
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
        _DRONE_STATUS_SUCCESS: 0,
        _DRONE_STATUS_NO_OVERLAP: 0,
        _DRONE_STATUS_FAILED_OTHER: 0,
    }

    for index, h5_path in enumerate(h5_files, start=1):
        flight_stem = flight_stems[h5_path]
        path_map = build_drone_output_paths(output_dir, flight_stem=flight_stem)
        prepared_h5_path = path_map["working_h5"]
        envi_stem = path_map["envi_stem"]
        corrected_stem = path_map["corrected_stem"]
        polygon_output_path = path_map["polygon_parquet"]
        polygon_index_path = path_map["polygon_index"]
        overlay_debug_path = path_map["overlay_debug_png"]
        package_dir = _drone_package_dir(h5_path)
        flight_started = time.monotonic()
        if batch_bar is not None:
            batch_bar.set_postfix_str(f"{index}/{total_flights} {flight_stem} | preparing H5")
        _drone_emit(
            f"[drone] [{index}/{total_flights}] {flight_stem} | source={package_dir} | stage=preparing H5"
        )
        file_audit: dict[str, Any] = {
            "platform": "drone",
            "flight_stem": flight_stem,
            "flight_dir": str(path_map["flight_dir"]),
            "source_package": package_dir.name,
            "source_package_path": str(package_dir),
            "input_h5_filename": h5_path.name,
            "input_h5_path": str(h5_path),
            "base_name": flight_stem,
            "flags": {
                "topo_requested": bool(apply_topo),
                "brdf_requested": bool(apply_brdf),
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
            "status": None,
        }
        try:
            prepared_h5_path, nodata_patched = _prepare_drone_h5_working_copy(
                h5_path,
                working_path=prepared_h5_path,
                overwrite=overwrite,
            )
            file_audit["prepared_h5_filename"] = prepared_h5_path.name
            file_audit["prepared_h5_path"] = str(prepared_h5_path)
            file_audit["nodata_patch_applied"] = bool(nodata_patched)

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
                overwrite=overwrite,
            )
            file_audit["flags"].update(
                {
                    "topo_applied": bool(correction_audit.get("topo_applied", False)),
                    "brdf_applied": bool(correction_audit.get("brdf_applied", False)),
                    "brightness_applied": False,
                    "cloud_applied": False,
                    "convolution_skipped": True,
                }
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
                        h5_path,
                        plot_exc,
                    )
                    file_audit["overlay_debug_error"] = str(plot_exc)
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
                results["outputs"].append(str(polygon_parquet))
                file_audit["polygon_filename"] = polygon_parquet.name
                file_audit["polygon_path"] = str(polygon_parquet)
                file_audit["polygon_index_filename"] = index_path.name
                file_audit["polygon_index_path"] = str(index_path)
            else:
                file_audit["polygon_filename"] = None
                file_audit["polygon_path"] = None

            results["processed"].append(str(h5_path))
            file_audit["status"] = _DRONE_STATUS_SUCCESS
            elapsed = time.monotonic() - flight_started
            file_audit["elapsed_seconds"] = round(elapsed, 3)
            completed_flight_times.append(elapsed)
            status_counts[_DRONE_STATUS_SUCCESS] += 1
            eta = _format_eta(completed_flight_times, total_flights - index)
            eta_suffix = f" | eta={eta}" if eta else ""
            _drone_emit(
                f"[drone] [{index}/{total_flights}] {flight_stem} -> "
                f"{_DRONE_STATUS_SUCCESS} ({_format_elapsed(elapsed)}){eta_suffix}",
                status=_DRONE_STATUS_SUCCESS,
            )
        except Exception as exc:
            status, reason = _classify_drone_exception(exc)
            elapsed = time.monotonic() - flight_started
            file_audit["status"] = status
            file_audit["error"] = reason
            file_audit["elapsed_seconds"] = round(elapsed, 3)
            status_counts[status] += 1
            if status == _DRONE_STATUS_NO_OVERLAP:
                results["processed"].append(str(h5_path))
                diagnostics = file_audit.get("spatial_diagnostics")
                if diagnostics is not None:
                    LOGGER.warning(
                        "[drone] No polygon overlap for %s: raster_crs=%s polygon_crs=%s overlap_after_reproject=%s intersecting_polygons=%s reason=%s",
                        h5_path,
                        diagnostics.get("raster_crs"),
                        diagnostics.get("polygon_crs"),
                        diagnostics.get("bounds_overlap_after_reproject"),
                        diagnostics.get("intersecting_polygon_count"),
                        reason,
                    )
                else:
                    LOGGER.warning(
                        "[drone] No polygon overlap for %s: %s", h5_path, reason
                    )
            else:
                LOGGER.exception("[drone] FAILED for %s", h5_path)
                results["failed"].append({"input": str(h5_path), "error": reason})
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
        results["qa_summary"]["files"].append(file_audit)

    if batch_bar is not None:
        batch_bar.close()

    if results["outputs"]:
        merged_path = _merge_drone_polygon_outputs(
            results["outputs"],
            output_dir / "drone_merged.parquet",
            overwrite=overwrite,
        )
        results["merged"] = str(merged_path)
        for file_audit in results["qa_summary"]["files"]:
            file_audit["merged_filename"] = merged_path.name
    else:
        results["merged"] = None

    try:
        from spectralbridge.qa_plots import render_drone_panel

        for file_audit in results["qa_summary"]["files"]:
            if file_audit.get("status") != _DRONE_STATUS_SUCCESS:
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
    results["qa_summary"]["success_count"] = status_counts[_DRONE_STATUS_SUCCESS]
    results["qa_summary"]["skipped_no_polygon_overlap_count"] = status_counts[
        _DRONE_STATUS_NO_OVERLAP
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
        f"{status_counts[_DRONE_STATUS_SUCCESS]} success | "
        f"{status_counts[_DRONE_STATUS_NO_OVERLAP]} skipped_no_polygon_overlap | "
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
    "derive_drone_flight_stem",
    "export_h5_to_envi",
    "resolve_band_map",
    "run_drone_pipeline",
    "save_drone_overlay_debug_plot",
    "validate_drone_h5_metadata",
]
