"""Prepare original sources and exercise existing pipeline; location tables deferred.

No research adapter, invented physical calibration or inferred camera table is used.
A prep-only run is never counted as a completed requested production run.
"""

import json
import logging
from pathlib import Path
import subprocess
import hashlib

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio

from spectralbridge import __version__, run_drone_pipeline
from spectralbridge.pipelines.drone import (
    prepare_drone_orthomosaic,
    build_drone_output_paths,
    _build_polygon_pixel_index_for_raster,
    _DRONE_TIFF_DEFAULT_WAVELENGTHS_NM,
)
from spectralbridge.remote import file_checksums

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = ROOT / "archive/local/drone-three-site-integration/2026-11-04"
POLYGONS = (
    ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
)
WAVES = list(_DRONE_TIFF_DEFAULT_WAVELENGTHS_NM)
GRID_RECORD = (
    ROOT
    / "provenance/drone-spatial-integrity/2026-10-29/production_source_comparison.json"
)


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, default=str) + "\n")


def profile(path):
    with rasterio.open(path) as src:
        return dict(
            path=str(path),
            size_bytes=Path(path).stat().st_size,
            sha256=file_checksums(path)["sha256"],
            crs=str(src.crs),
            shape=list(src.shape),
            resolution=list(src.res),
            transform=list(src.transform),
            bounds=list(src.bounds),
            band_count=src.count,
            dtypes=src.dtypes,
            alpha_bands=[
                i for i, c in enumerate(src.colorinterp, 1) if c.name == "alpha"
            ],
            nodata="NaN"
            if src.nodata is not None and np.isnan(src.nodata)
            else src.nodata,
            scales=list(src.scales),
            offsets=list(src.offsets),
            tags=src.tags(),
        )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    grid_rows = json.loads(GRID_RECORD.read_text())
    polygons = gpd.read_file(POLYGONS)
    git = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    for site in ["Gordon", "Goldhill", "Ruby"]:
        print("AVAILABLE STAGES:", site, flush=True)
        selection = json.loads(
            (HERE / f"{site.lower()}_remote_selection.json").read_text()
        )
        transfer = json.loads((HERE / f"{site.lower()}_transfers.json").read_text())
        source = Path(transfer["orthomosaic_local"])
        stem = selection["flight_stem"]
        output = WORK / "outputs" / stem
        output.mkdir(parents=True, exist_ok=True)
        native = profile(source)
        if not (
            native["band_count"] == 11
            and native["alpha_bands"] == [11]
            and native["dtypes"][0] == "uint16"
        ):
            raise ValueError("Unexpected original raster contract: " + site)
        reference = next(r for r in grid_rows if site.lower() in r["flight"].lower())
        grid = dict(
            width=reference["dimensions"][1],
            height=reference["dimensions"][0],
            transform=reference["source_affine"],
            crs=reference["source_crs"],
        )
        local_source = (
            WORK
            / "prepared"
            / Path(selection["source_directory"]).name
            / (source.stem + "__processing_10cm_10k.tif")
        )
        prepared = prepare_drone_orthomosaic(source, local_source, grid=grid)
        restart = prepare_drone_orthomosaic(source, local_source, grid=grid)
        assert restart["status"] == "reused"
        with rasterio.open(local_source) as src:
            in_crs = polygons.to_crs(src.crs)
            overlap = in_crs.intersects(__import__("shapely").geometry.box(*src.bounds))
        metadata = []
        for r in transfer["transfers"]:
            p = Path(r["local_path"])
            if p.suffix.lower() == ".csv":
                frame = pd.read_csv(p)
                metadata.append(
                    dict(
                        path=str(p),
                        remote_path=r["remote_path"],
                        rows=len(frame),
                        columns=list(frame.columns),
                        status="SOURCE_METADATA_ONLY; new flight-location table deferred by user",
                    )
                )
            elif p.suffix.lower() == ".tif" and p != source:
                try:
                    metadata.append(profile(p))
                except rasterio.errors.RasterioIOError as exc:
                    metadata.append(dict(path=str(p), status="INVALID_RASTER", error=str(exc),
                                         sha256=file_checksums(p)["sha256"]))
        manifest = dict(
            site=site,
            flight_stem=stem,
            source_directory=selection["source_directory"],
            orthomosaic=selection["orthomosaic"],
            original_local=native,
            transfers=transfer["transfers"],
            coordinate_table=None,
            coordinate_status="DEFERRED_BY_USER",
            available_metadata=metadata,
            selection_rationale=selection["selection_rationale"],
            clipped_export=selection["clipped_export"],
            wavelengths_nm=WAVES,
            wavelength_provenance="Established ten-band MicaSense Dual package convention; TIFF has no independent wavelength declarations",
            acquisition_metadata_source=str(
                ROOT / "src/spectralbridge/data/drone_field_manifest.csv"
            ),
            radiometric_encoding="Original UInt16 DN; physical calibration unverified",
            prepared=prepared,
            processing_grid_reference=str(GRID_RECORD),
            processing_grid_reference_sha256=file_checksums(GRID_RECORD)["sha256"],
            processing_grid_usage="Spatial comparison support only; original orthomosaic supplies all spectral values",
            polygon_source=str(POLYGONS),
            polygon_sha256=file_checksums(POLYGONS)["sha256"],
            polygon_definition="Established HALF-DIAMETER researcher polygons; no relabeling",
            intersecting_polygon_features=int(overlap.sum()),
            software_version=__version__,
            git_commit=git,
            working_tree_changes=True,
            source_code_sha256={
                str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [
                    ROOT / "src/spectralbridge/remote.py",
                    ROOT / "src/spectralbridge/drone_production.py",
                    ROOT / "src/spectralbridge/pipelines/drone.py",
                ]
            },
        )
        write(output / "source_manifest.json", manifest)
        write(HERE / f"{site.lower()}_source_manifest.json", manifest)
        write(
            output / "source_validation.json",
            dict(
                status="VALID_FOR_SOURCE_PREPARATION",
                calibration="UNVERIFIED",
                locations="DEFERRED_BY_USER",
                alpha="explicit band 11; excluded from ten-band reflectance data",
                numeric_scaling="DN*10000/65535; zero offset; no min/max adjustment",
                source_checksum_verified=all(
                    r["remote_checksum_verified"] for r in transfer["transfers"]
                ),
                preprocessing_restart_reused=True,
                original_immutable=file_checksums(source)["sha256"] == native["sha256"],
            ),
        )
        common = dict(
            input_h5_dir=local_source.parent,
            drone_manifest_timezone="UTC",
            tiff_wavelengths_nm=WAVES,
            radiometry=prepared["radiometry"],
            raise_on_incomplete=False,
            parquet_chunk_size=100000,
        )
        # Only source-preparation/QA is requested here; never label this the full objective.
        preproot = output / "preparation_pipeline"
        result = run_drone_pipeline(
            **common,
            output_dir=preproot,
            apply_topo=False,
            apply_brdf=False,
            apply_translation=False,
        )
        write(output / "preparation_pipeline_result.json", result)
        paths = build_drone_output_paths(preproot, flight_stem=stem)
        raw = paths["envi_stem"].with_suffix(".img")
        hdr = paths["envi_stem"].with_suffix(".hdr")
        if raw.exists():
            index = _build_polygon_pixel_index_for_raster(
                raster_img=raw,
                raster_hdr=hdr,
                polygons_path=POLYGONS,
                output_path=paths["polygon_index"],
                flight_id=stem,
            )
            manifest["polygon_index"] = str(index)
        # Exercise the requested production configuration and record its true block.
        targetroot = output / "requested_pipeline_attempt"
        target = run_drone_pipeline(
            **common,
            output_dir=targetroot,
            polygon_path=POLYGONS,
            extraction_mode="polygon",
            apply_topo=True,
            apply_brdf=True,
            apply_translation=True,
        )
        write(output / "requested_pipeline_result.json", target)
        manifest["preparation_pipeline_result"] = str(
            output / "preparation_pipeline_result.json"
        )
        manifest["requested_pipeline_result"] = str(
            output / "requested_pipeline_result.json"
        )
        manifest["overall_status"] = (
            "INCOMPLETE_LOCATION_TABLES_DEFERRED_AND_CALIBRATION_UNVERIFIED"
        )
        write(output / "source_manifest.json", manifest)
        write(HERE / f"{site.lower()}_source_manifest.json", manifest)
        print(
            site,
            "raw ENVI:",
            raw.exists(),
            "target status:",
            target.get("status"),
            "blocked:",
            target.get("blocked"),
            flush=True,
        )


if __name__ == "__main__":
    main()
