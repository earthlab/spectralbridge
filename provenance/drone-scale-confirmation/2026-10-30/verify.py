"""Read-only three-flight scaling investigation; creates compact evidence only.

Usage: python verify.py --download-root /path/to/downloads --staged-root /path/to/staged_sources
All file names mirror the downloaded original/base/rescale inputs. No physical
reflectance conversion or change to production data is authorized by this script.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def regression(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xm = x.mean()
    ym = y.mean()
    slope = float(np.dot(x - xm, y - ym) / np.dot(x - xm, x - xm))
    offset = float(ym - slope * xm)
    error = y - (slope * x + offset)
    return {
        "slope": slope,
        "offset": offset,
        "max_abs_residual": float(abs(error).max()),
        "rmse": float(np.sqrt(np.mean(error**2))),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-root", type=Path, required=True)
    parser.add_argument("--staged-root", type=Path, required=True)
    args = parser.parse_args()
    output = {}
    for name, package in [
        ("gordon", "AOP-GORDON"),
        ("goldhill", "AOP-GOLDHILL"),
        ("ruby", "AOP-Ruby"),
    ]:
        root = args.download_root
        original = root / f"{name}-original.tif"
        base = (
            root
            / "base"
            / (
                "goldhill.tif"
                if name == "goldhill"
                else name + "/aligned_orthomosaic.tif"
            )
        )
        scaled = (
            root
            / "rescale"
            / (
                "goldhill.tif"
                if name == "goldhill"
                else name + "/aligned_orthomosaic.tif"
            )
        )
        target = next(
            args.staged_root.glob("2023_" + package + "*/aligned_orthomosaic.tif")
        )
        paths = {
            "original": original,
            "base_25cm": base,
            "rescaled_25cm": scaled,
            "target_10cm": target,
        }
        record = {
            "files": {k: {"path": str(p), "sha256": sha(p)} for k, p in paths.items()},
            "bands": [],
        }
        packages = {
            "gordon": (
                "AOP-GORDON-08-14-23-ExportPackage",
                "AOP-GORDON-8-14-23-M300_ORTHO.tif",
            ),
            "goldhill": (
                "AOP-GOLDHILL-08-14-23-ExportPackage",
                "AOP-GOLDHILL-08-14-23_ORTHO.tif",
            ),
            "ruby": (
                "AOP-Ruby-08-14-23-ExportPackage",
                "AOP-RUBY-08-14-23-ORTHO_CLIPPED.tif",
            ),
        }
        package_name, original_name = packages[name]
        remote_root = "i:/iplant/home/shared/earthlab/macrosystems/field-data/"
        for key, file_record in record["files"].items():
            if key == "original":
                relative = "uas-packages/" + package_name + "/" + original_name
            else:
                collection = {
                    "base_25cm": "summer-2023",
                    "rescaled_25cm": "summer-2023-rescale",
                    "target_10cm": "summer-2023-10cm-10k",
                }[key]
                relative = (
                    "output/"
                    + collection
                    + "/"
                    + package_name
                    + "/aligned_orthomosaic.tif"
                )
            file_record["remote_origin"] = remote_root + relative
        with (
            rasterio.open(original) as orig,
            rasterio.open(base) as prior,
            rasterio.open(scaled) as new,
            rasterio.open(target) as dst,
        ):
            assert (
                prior.transform == new.transform
                and prior.crs == new.crs
                and prior.shape == new.shape
            )
            record["resolutions"] = {
                k: list(d.res)
                for k, d in [
                    ("original", orig),
                    ("base", prior),
                    ("rescaled", new),
                    ("target", dst),
                ]
            }
            record["original_color_interpretation"] = [v.name for v in orig.colorinterp]
            for band in range(1, 11):
                source = orig.read(band)
                minimum = int(source.min())
                maximum = int(source.max())
                expected_slope = 10000 / (maximum - minimum)
                expected_offset = -minimum * expected_slope
                before = prior.read(band)
                after = new.read(band)
                mask = np.isfinite(before) & np.isfinite(after)
                paired = regression(before[mask], after[mask])
                expected = (
                    expected_slope * before[mask].astype(np.float64) + expected_offset
                )
                pair_error = after[mask] - expected
                tolerance = 2 * float(np.spacing(np.float32(10000)))
                assert np.max(np.abs(pair_error)) <= tolerance, (
                    name,
                    band,
                    "Range-mapping hypothesis failed",
                )
                # Reproduce spatial resampling from original pixels on the exact
                # current target grid, then compare the numerical normalization.
                warped = np.full(dst.shape, np.nan, np.float32)
                reproject(
                    source,
                    warped,
                    src_transform=orig.transform,
                    src_crs=orig.crs,
                    dst_transform=dst.transform,
                    dst_crs=dst.crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )
                observed = dst.read(band)
                matched = np.isfinite(warped) & np.isfinite(observed)
                target_fit = regression(warped[matched], observed[matched])
                predicted = (
                    expected_slope * warped[matched].astype(np.float64)
                    + expected_offset
                )
                target_error = observed[matched] - predicted
                row = {
                    "band": band,
                    "source_min": minimum,
                    "source_max": maximum,
                    "expected_range_mapping": {
                        "slope": expected_slope,
                        "offset": expected_offset,
                    },
                    "paired_25cm": {
                        **paired,
                        "valid_pairs": int(mask.sum()),
                        "max_error_vs_original_extrema_mapping": float(
                            abs(pair_error).max()
                        ),
                    },
                    "original_to_10cm_bilinear": {
                        **target_fit,
                        "valid_pairs": int(matched.sum()),
                        "rmse_vs_original_extrema_mapping": float(
                            np.sqrt(np.mean(target_error**2))
                        ),
                        "absolute_error_quantiles": np.quantile(
                            abs(target_error), [0, 0.5, 0.99, 1]
                        ).tolist(),
                    },
                    "note": "GDAL warp is an independent comparison, not an exact replay of the unavailable original 10cm export code",
                }
                record["bands"].append(row)
                print(
                    name,
                    band,
                    "min/max",
                    minimum,
                    maximum,
                    "25cm max error",
                    row["paired_25cm"]["max_error_vs_original_extrema_mapping"],
                    "10cm rmse",
                    row["original_to_10cm_bilinear"][
                        "rmse_vs_original_extrema_mapping"
                    ],
                    flush=True,
                )
        output[name] = record
    Path(__file__).with_name("evidence.json").write_text(
        json.dumps(output, indent=2, allow_nan=False)
    )


if __name__ == "__main__":
    main()
