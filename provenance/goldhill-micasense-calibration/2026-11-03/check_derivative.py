"""Independent scale-before versus scale-after resampling, hypothesis only."""

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

HERE = Path(__file__).resolve().parent
original = Path("/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif")
derivative = Path(
    "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
)
rows = []
with rasterio.open(original) as src, rasterio.open(derivative) as dst:
    alpha = src.read(11) > 0
    targetmask = dst.dataset_mask() > 0
    for band in range(1, 11):
        values = src.read(band, out_dtype="float32") / np.float32(32768)
        values[~alpha] = np.nan
        reference = np.full(dst.shape, np.nan, np.float32)
        reproject(
            values,
            reference,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=np.nan,
            dst_transform=dst.transform,
            dst_crs=dst.crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
            num_threads=1,
        )
        candidate = dst.read(band) * np.float32(65535 / (32768 * 10000))
        common = targetmask & np.isfinite(reference) & np.isfinite(candidate)
        error = candidate[common] - reference[common]
        assert np.max(abs(error)) < 2e-7
        rows.append(
            dict(
                band=band,
                valid_pixels=int(common.sum()),
                max_abs_scale_before_after_resampling_error=float(abs(error).max()),
                rmse=float(np.sqrt(np.mean(error.astype(float) ** 2))),
                candidate_R_min=float(candidate[common].min()),
                candidate_R_max=float(candidate[common].max()),
                candidate_R_mean=float(candidate[common].mean(dtype=float)),
            )
        )
(HERE / "derivative_candidate_precision.json").write_text(
    json.dumps(
        dict(
            status="PASS_NUMERICAL_HYPOTHESIS_ONLY",
            method="Original DN/32768 before masked bilinear warp versus existing fixed-10K after warp times 65535/(32768*10000); no physical raster written",
            bands=rows,
        ),
        indent=2,
    )
    + "\n"
)
print(
    "Ten-band candidate algebra/resampling consistency verified; no physical calibration assigned"
)
