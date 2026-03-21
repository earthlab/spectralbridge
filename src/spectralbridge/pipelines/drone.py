from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import duckdb
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

DRONE_TARGET_BANDS: dict[str, int] = {
    "blue": 444,
    "green": 560,
    "red": 650,
    "nir": 862,
}


def clean_name(name: str) -> str:
    """Normalise a source name minimally for filesystem-safe output filenames."""

    safe = "".join(
        ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(name)
    )
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe.strip("._") or "drone"


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
    chunk_y = 100
    chunk_x = 100
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
            [f"'{str(Path(path)).replace("'", "''")}'" for path in outputs]
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
    if not h5_files:
        qa_path = _write_json(
            output_dir / "drone_qa_summary.json", results["qa_summary"]
        )
        results["qa_summary_path"] = str(qa_path)
        return results

    for h5_path in h5_files:
        base_name = clean_name(h5_path.stem)
        envi_stem = output_dir / f"{base_name}__envi"
        corrected_stem = output_dir / f"{base_name}__corrected"
        polygon_output_path = output_dir / f"{base_name}__polygons.parquet"
        polygon_index_path = output_dir / f"{base_name}__polygon_index.parquet"
        file_audit: dict[str, Any] = {
            "platform": "drone",
            "input_h5_filename": h5_path.name,
            "base_name": base_name,
            "flags": {
                "topo_requested": bool(apply_topo),
                "brdf_requested": bool(apply_brdf),
                "brightness_requested": bool(apply_brightness_adjustment),
                "brightness_applied": False,
                "cloud_applied": False,
                "convolution_skipped": True,
            },
            "working_raster": str(envi_stem.with_suffix(".img").name),
            "corrected_raster": str(corrected_stem.with_suffix(".img").name),
            "polygon_filename": (
                polygon_output_path.name if polygon_path is not None else None
            ),
            "merged_filename": None,
        }
        try:
            cube = NeonCube(h5_path=h5_path)
            meta = validate_drone_h5_metadata(h5_path)
            band_map = resolve_band_map(meta["wavelengths"], DRONE_TARGET_BANDS)
            file_audit["resolved_band_map"] = band_map
            file_audit["metadata"] = {
                "lines": meta["lines"],
                "samples": meta["samples"],
                "bands": meta["bands"],
                "wavelength_units": meta["wavelength_units"],
            }

            envi_img, envi_hdr = export_h5_to_envi(
                h5_path,
                output_stem=envi_stem,
                brightness_offset=0.0,
                overwrite=overwrite,
                cube=cube,
            )
            config = build_drone_config(
                h5_path=h5_path,
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

            if polygon_path is not None:
                index_path = _build_polygon_pixel_index_for_raster(
                    raster_img=corrected_img,
                    raster_hdr=corrected_hdr,
                    polygons_path=polygon_path,
                    output_path=polygon_index_path,
                    flight_id=base_name,
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
            else:
                file_audit["polygon_filename"] = None

            results["processed"].append(str(h5_path))
            file_audit["status"] = "processed"
        except Exception as exc:
            LOGGER.exception("[drone] FAILED for %s", h5_path)
            file_audit["status"] = "failed"
            file_audit["error"] = str(exc)
            results["failed"].append({"input": str(h5_path), "error": str(exc)})
        results["qa_summary"]["files"].append(file_audit)

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

    qa_path = _write_json(output_dir / "drone_qa_summary.json", results["qa_summary"])
    results["qa_summary_path"] = str(qa_path)
    return results


__all__ = [
    "DRONE_TARGET_BANDS",
    "build_drone_config",
    "clean_name",
    "export_h5_to_envi",
    "resolve_band_map",
    "run_drone_pipeline",
    "validate_drone_h5_metadata",
]
