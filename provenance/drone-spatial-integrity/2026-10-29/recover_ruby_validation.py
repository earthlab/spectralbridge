"""Explicit, investigation-only first-ten-band Ruby recovery; never edits originals.

The source has an unclassified eleventh band. This script first proves every
retained value equals its historical H5 counterpart before creating a declared
10-band reference for the existing strict TIFF reader. It is not auto-trimming
in the package and not a general endorsement of the omitted channel's identity.
"""

import argparse
import json
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.windows import Window

from spectralbridge.pipelines.drone import run_drone_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--polygons", type=Path, required=True)
    args = parser.parse_args()
    package = args.sources / "AOP-Ruby-08-14-23-ExportPackage"
    original = package / "aligned_orthomosaic.tif"
    original_h5 = package / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    prepared = args.workspace / "reference" / "AOP-Ruby-08-14-23-ExportPackage"
    prepared.mkdir(parents=True, exist_ok=True)
    reference = prepared / "verified_first_ten_reflectance_bands.tif"
    with rasterio.open(original) as src, h5py.File(original_h5) as h:
        reflectance = next(iter(h.values()))["Reflectance"]
        ds = reflectance["Reflectance_Data"]
        if src.count != 11 or ds.shape != (src.height, src.width, 10):
            raise ValueError(
                "This versioned audit supports only the observed Ruby 11-to-10 contract"
            )
        for start in range(0, src.height, 128):
            stop = min(src.height, start + 128)
            a = src.read(
                list(range(1, 11)), window=Window(0, start, src.width, stop - start)
            )
            b = np.moveaxis(ds[start:stop, :, :], 2, 0)
            if not np.array_equal(a, b, equal_nan=True):
                raise ValueError("Cannot establish exact source band correspondence")
        # Preserve original scalar view geometry only after proving it is constant.
        view = {}
        for field in ["Zenith", "Azimuth"]:
            values = reflectance[f"Metadata/to-sensor_{field}_Angle"][()]
            if not np.isfinite(values).all() or not np.all(values == values.flat[0]):
                raise ValueError("View geometry is not a validated scalar")
            view[field.lower()] = float(values.flat[0])
        if not reference.exists():
            profile = src.profile.copy()
            profile.update(count=10)
            with rasterio.open(reference, "w", **profile) as dst:
                dst.update_tags(**src.tags())
                for start in range(0, src.height, 128):
                    stop = min(src.height, start + 128)
                    window = Window(0, start, src.width, stop - start)
                    dst.write(
                        src.read(list(range(1, 11)), window=window), window=window
                    )
                for i, name in enumerate(src.descriptions[:10], 1):
                    if name:
                        dst.set_band_description(i, name)
    for name in ["aligned_slope.tif", "aligned_aspect.tif"]:
        target = prepared / name
        if not target.exists():
            target.symlink_to((package / name).resolve())
    args.evidence.mkdir(parents=True, exist_ok=True)
    options = dict(
        polygon_path=args.polygons,
        output_dir=args.workspace / "outputs",
        apply_topo=True,
        apply_brdf=True,
        require_solar_geometry=True,
        tiff_sensor_zenith_deg=view["zenith"],
        tiff_sensor_azimuth_deg=view["azimuth"],
        apply_translation=True,
        merge_extractions=False,
        raise_on_incomplete=False,
    )
    result = run_drone_pipeline(reference, **options)
    (args.evidence / "ruby_recovery_result.json").write_text(
        json.dumps(result, indent=2, default=str) + "\n"
    )
    if result["failed"] or result["blocked"]:
        raise RuntimeError(
            "Recovery did not satisfy existing pipeline gates; inspect recorded result"
        )
    flight = Path(result["qa_summary"]["files"][0]["flight_dir"])
    tracked = [
        *flight.glob("*.img"),
        *flight.glob("*.h5"),
        *flight.glob("*__polygon_index.parquet"),
        *flight.glob("*__polygons.parquet"),
    ]
    before = {str(p): p.stat().st_mtime_ns for p in tracked}
    repeated = run_drone_pipeline(reference, **options)
    after = {str(p): p.stat().st_mtime_ns for p in tracked}
    (args.evidence / "ruby_restart.json").write_text(
        json.dumps(
            dict(
                before=before,
                after=after,
                all_tracked_products_reused=before == after,
                failed=repeated["failed"],
                blocked=repeated["blocked"],
                scope="Existing manifest computes solar geometry; acquisition-date discrepancy is unresolved, so this validates spatial wiring, not physical radiometric correctness.",
                explicit_source_bands=list(range(1, 11)),
                unclassified_source_band=11,
                originals_modified=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
