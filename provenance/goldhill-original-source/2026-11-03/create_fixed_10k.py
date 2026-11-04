"""Create an explicit numerical derivative, never infer physical calibration.

Band-bounded bilinear resampling excludes original transparent pixels. An
independent nearest-neighbor alpha footprint is intersected with finite outputs.
Output contains ten float32 spectral bands plus a GDAL validity mask, no alpha
confused with a spectral band. The original TIFF is opened read-only.
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
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def create(source, template, destination):
    source, template, destination = map(Path, [source, template, destination])
    if destination.exists():
        raise FileExistsError(
            "Preserve existing derivative; choose a fresh output path"
        )
    original_hash = sha(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(source) as src, rasterio.open(template) as grid:
        assert (
            src.count == 11
            and src.dtypes[0] == "uint16"
            and src.colorinterp[-1].name == "alpha"
        )
        assert src.crs == grid.crs and np.allclose(
            grid.res, [0.1, 0.1], atol=1e-10, rtol=0
        )
        original_alpha = src.read(11) > 0
        target_alpha = np.zeros(grid.shape, np.uint8)
        reproject(
            original_alpha.astype(np.uint8),
            target_alpha,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=grid.transform,
            dst_crs=grid.crs,
            resampling=Resampling.nearest,
        )
        valid = target_alpha.astype(bool)
        profile = dict(
            driver="GTiff",
            width=grid.width,
            height=grid.height,
            count=10,
            dtype="float32",
            crs=grid.crs,
            transform=grid.transform,
            nodata=np.nan,
            tiled=True,
            blockxsize=256,
            blockysize=256,
            compress="deflate",
            predictor=3,
            BIGTIFF="IF_SAFER",
        )
        band_stats = []
        with (
            rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True),
            rasterio.open(destination, "w", **profile) as out,
        ):
            for band in range(1, 11):
                values = src.read(band, out_dtype="float32")
                values[~original_alpha] = np.nan
                warped = np.full(grid.shape, np.nan, np.float32)
                reproject(
                    values,
                    warped,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=np.nan,
                    dst_transform=grid.transform,
                    dst_crs=grid.crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                    num_threads=1,
                )
                warped *= np.float32(10000 / 65535)
                warped[~valid] = np.nan
                valid &= np.isfinite(warped)
                x = warped[np.isfinite(warped)]
                assert x.min() >= 0 and x.max() <= 10000.001
                out.write(warped, band)
                out.set_band_description(
                    band,
                    f"Source spectral band {band}; fixed 10000/65535 numerical encoding",
                )
                band_stats.append(
                    dict(
                        band=band,
                        minimum=float(x.min()),
                        maximum=float(x.max()),
                        finite_pixels=int(x.size),
                    )
                )
                print(f"Fixed numerical derivative: band {band}/10", flush=True)
            out.write_mask(valid.astype(np.uint8) * 255)
            out.update_tags(
                SPECTRALBRIDGE_ENCODING="fixed_uint16_range_dn",
                NUMERIC_MULTIPLIER=str(10000 / 65535),
                NUMERIC_OFFSET="0",
                PHYSICAL_CALIBRATION_STATUS="UNVERIFIED",
                SOURCE_SHA256=original_hash,
                SPATIAL_RESAMPLING="bilinear; exclude source alpha=0; nearest source alpha footprint",
                SPECTRALBRIDGE_NOTE="Numerical 0–10000 encoding, not a physical reflectance calibration",
            )
        record = dict(
            source=str(source),
            source_sha256=original_hash,
            target_grid_template=str(template),
            output=str(destination),
            numeric_equation="S = DN * 10000 / 65535",
            numeric_multiplier=10000 / 65535,
            numeric_offset=0,
            physical_calibration="UNVERIFIED; numerical encoding is not a physical calibration",
            radiometry=dict(
                scale=None,
                offset=None,
                status="UNSUPPORTED",
                provenance="Original UInt16 orthomosaic; fixed type-range conversion; physical calibration unavailable",
                convention="physical = scale * stored + offset",
                encoding=dict(
                    kind="range_normalized_dn",
                    stored_units="fixed UInt16-range DN encoded 0–10000; no minimum subtraction",
                    physical_calibration_status="UNVERIFIED",
                    nodata="NaN",
                    normalization=dict(
                        stored_min=0, stored_max=10000, source_min=0, source_max=65535
                    ),
                    quality_mask=dict(
                        status="DOCUMENTED",
                        provenance="Source declared alpha, nearest target footprint and finite bilinear interpolation",
                        convention="GDAL mask true/255 means valid",
                    ),
                ),
            ),
            shape=[grid.height, grid.width, 10],
            crs=str(grid.crs),
            transform=list(grid.transform),
            resolution=list(grid.res),
            valid_pixels=int(valid.sum()),
            bands=band_stats,
            clipping="NONE",
            rounding="Float32 arithmetic only; no integer quantization",
            storage="Float32 GeoTIFF, NaN NoData, internal GDAL validity mask",
            production_pipeline_changed=False,
        )
    assert sha(source) == original_hash
    record["output_sha256"] = sha(destination)
    destination.with_suffix(".radiometry.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("grid_template", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    create(args.source, args.grid_template, args.output)
