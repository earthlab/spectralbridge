"""Independent full-pixel checks of recovered Ruby geometry, masks and translation."""

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.windows import Window
from spectralbridge.drone_translation import load_drone_translation_plans


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    audit = result["qa_summary"]["files"][0]
    rows = []
    with h5py.File(audit["prepared_h5_path"]) as h:
        wavelengths = next(iter(h.values()))[
            "Reflectance/Metadata/Spectral_Data/Wavelength"
        ][()].tolist()
    with (
        rasterio.open(args.source) as src,
        rasterio.open(audit["corrected_raster_path"]) as corrected,
        rasterio.open(args.source.parent / "aligned_slope.tif") as slope,
        rasterio.open(args.source.parent / "aligned_aspect.tif") as aspect,
    ):
        new_nodata = 0
        lost_nodata = 0
        finite_change_count = 0
        geometry_excluded = 0
        geometry_mask_mismatches = 0
        for start in range(0, src.height, 128):
            stop = min(src.height, start + 128)
            w = Window(0, start, src.width, stop - start)
            original = src.read(list(range(1, 11)), window=w)
            values = corrected.read(window=w)
            a = np.isfinite(original)
            b = np.isfinite(values)
            new_nodata += int((a & ~b).sum())
            lost_nodata += int((~a & b).sum())
            finite_change_count += int((a & b & (original != values)).sum())
            geometry_valid = np.isfinite(slope.read(1, window=w)) & np.isfinite(
                aspect.read(1, window=w)
            )
            geometry_excluded += int((a.all(axis=0) & ~geometry_valid).sum())
            expected_valid = a.all(axis=0) & geometry_valid
            geometry_mask_mismatches += int((expected_valid != b.all(axis=0)).sum())
        plans = load_drone_translation_plans(
            Path(result["qa_summary"]["translation_coefficient_path"]),
            weighting="site_balanced",
            source_wavelengths_nm=wavelengths,
            strict=False,
        )
        by_target = {p.target_sensor: p for p in plans}
        for product in audit["translation_products"]:
            plan = by_target[product["target_sensor"]]
            with rasterio.open(product["output_img"]) as dst:
                count = 0
                mismatches = 0
                mask_mismatches = 0
                for start in range(0, src.height, 128):
                    stop = min(src.height, start + 128)
                    window = Window(0, start, src.width, stop - start)
                    original = corrected.read(window=window)
                    actual = dst.read(window=window)
                    for i, band in enumerate(plan.bands):
                        a = original[band.native_source_band_index - 1]
                        expected = np.float32(band.slope) * a + np.float32(
                            band.intercept
                        )
                        valid = np.isfinite(a)
                        count += a.size
                        mismatches += int((valid & (expected != actual[i])).sum())
                        mask_mismatches += int((valid != np.isfinite(actual[i])).sum())
                rows.append(
                    dict(
                        sensor=plan.target_sensor,
                        values_checked=count,
                        finite_value_mismatches=mismatches,
                        mask_mismatches=mask_mismatches,
                        crs_matches_source=dst.crs == src.crs,
                        affine_matches_source=dst.transform == src.transform,
                    )
                )
        report = dict(
            source=str(args.source),
            correction_new_nodata_values=new_nodata,
            finite_source_pixels_missing_terrain_geometry=geometry_excluded,
            correction_mask_mismatches_against_source_and_terrain_policy=geometry_mask_mismatches,
            correction_filled_source_nodata_values=lost_nodata,
            finite_values_changed_by_requested_correction=finite_change_count,
            corrected_crs_matches_source=corrected.crs == src.crs,
            corrected_affine_matches_source=corrected.transform == src.transform,
            translations=rows,
            qa_execution_status=result["qa_summary"].get("execution_status"),
            qa_scientific_status=audit.get("scientific_qa_status"),
            scope="Spatial and arithmetic conformance; existing correction enabled, not independently validated physical radiometry. Manifest date differs from package date.",
        )
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
