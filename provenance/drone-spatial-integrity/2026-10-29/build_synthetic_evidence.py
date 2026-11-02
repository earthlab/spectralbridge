"""Generate an asymmetric control fixture; never represent it as production."""

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from affine import Affine
from shapely.geometry import box

from spectralbridge.drone_translation import (
    DroneTranslationBand,
    DroneTranslationPlan,
    apply_drone_translation,
)
from spectralbridge.neon_cube import NeonCube
from spectralbridge.pipelines.drone import (
    convert_drone_tiff_to_h5,
    export_h5_to_envi,
    apply_drone_corrections,
    _build_polygon_pixel_index_for_raster,
)
from spectralbridge.polygons import extract_polygon_parquet_from_envi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = args.output
    data = np.arange(3 * 5 * 7, dtype="float32").reshape(3, 5, 7) + 100
    data[:, 0, 0] = -9999
    transform = Affine(0.123456789, 0, 457624.1234567, 0, -0.234567891, 4432830.9876543)
    source = root / "authoritative_synthetic.tif"
    with rasterio.open(
        source,
        "w",
        driver="GTiff",
        width=7,
        height=5,
        count=3,
        dtype="float32",
        crs=32613,
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(data)
    h5 = convert_drone_tiff_to_h5(
        source,
        output_h5_path=root / "fixture__working.h5",
        wavelengths_nm=[500, 650, 860],
        fwhm_nm=[10] * 3,
        overwrite=True,
    )
    img, hdr = export_h5_to_envi(
        h5, output_stem=root / "fixture__native", overwrite=True
    )
    corrected, corrected_hdr, _ = apply_drone_corrections(
        cube=NeonCube(h5),
        envi_img=img,
        envi_hdr=hdr,
        corrected_stem=root / "fixture__corrected",
        apply_topo=False,
        apply_brdf=False,
        overwrite=True,
    )
    bands = tuple(
        DroneTranslationBand(
            translation_pair="fixture",
            source_sensor="MicaSense_to-match_OLI_and_OLI-2",
            target_sensor="Landsat_8_OLI",
            coefficient_band_index=i,
            coefficient_source_band_index=i,
            native_source_band_index=i,
            target_band_index=i,
            source_spectral_identity=f"band{i}",
            target_spectral_identity=f"band{i}",
            source_wavelength_nm=wl,
            native_source_wavelength_nm=wl,
            target_wavelength_nm=wl,
            target_fwhm_nm=10,
            slope=1,
            intercept=1,
            x_min=0,
            x_max=1000,
            x_mean=200,
            r2=1,
        )
        for i, wl in enumerate([500, 650, 860], 1)
    )
    plan = DroneTranslationPlan(
        analysis_run_id="synthetic-fixture",
        analysis_level="site_balanced",
        weighting_description="synthetic",
        source_sensor="MicaSense_to-match_OLI_and_OLI-2",
        target_sensor="Landsat_8_OLI",
        translation_pair="fixture",
        coefficient_path="synthetic",
        coefficient_sha256="synthetic",
        evidence_boundary="synthetic translation wiring control",
        candidate_status="fixture",
        bands=bands,
    )
    apply_drone_translation(
        corrected,
        corrected_hdr,
        output_stem=root / "fixture__translated",
        plan=plan,
        overwrite=True,
    )
    x0, y0 = transform * (0.51, 0.51)
    x1, y1 = transform * (2.49, 2.49)
    polygons = root / "polygons.geojson"
    gpd.GeoDataFrame(
        {"polygon_id": [19], "cover_category": ["Evergreen"]},
        geometry=[box(x0, y1, x1, y0)],
        crs=32613,
    ).to_file(polygons)
    index = _build_polygon_pixel_index_for_raster(
        raster_img=corrected,
        raster_hdr=corrected_hdr,
        polygons_path=polygons,
        output_path=root / "index.parquet",
        flight_id="synthetic",
        overwrite=True,
    )
    extract_polygon_parquet_from_envi(
        corrected, corrected_hdr, index, root / "spectra.parquet", overwrite=True
    )


if __name__ == "__main__":
    main()
