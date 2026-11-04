"""Test spatial interpolation hypotheses independently for the red band."""

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

HERE = Path(__file__).resolve().parent
TEMP = Path("/private/tmp/p168-goldhill-sources")
rows = []
with rasterio.open(
    "/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif"
) as src:
    original = src.read(5).astype(np.float32)
    source_alpha = src.read(11) > 0
    for name, path, multiplier in [
        ("upstream_uint16_25cm", TEMP / "upstream_aligned/aligned_orthomosaic.tif", 1),
        ("normalized_10cm", TEMP / "ten_cm/aligned_orthomosaic.tif", 10000 / 65535),
    ]:
        with rasterio.open(path) as dst:
            y = dst.read(5)
            target = np.isfinite(y)
            if name == "upstream_uint16_25cm":
                target &= dst.read(11) > 0
            for method in ["nearest", "bilinear", "average"]:
                for mask_alpha in [False, True]:
                    values = original.copy()
                    if mask_alpha:
                        values[~source_alpha] = np.nan
                    warped = np.full(dst.shape, np.nan, np.float32)
                    reproject(
                        values,
                        warped,
                        src_transform=src.transform,
                        src_crs=src.crs,
                        src_nodata=np.nan,
                        dst_transform=dst.transform,
                        dst_crs=dst.crs,
                        dst_nodata=np.nan,
                        resampling=getattr(Resampling, method),
                    )
                    good = target & np.isfinite(warped)
                    predicted = warped[good].astype(float) * multiplier
                    observed = y[good].astype(float)
                    e = observed - predicted
                    rows.append(
                        dict(
                            target=name,
                            band=5,
                            wavelength_nm=650,
                            method=method,
                            exclude_original_transparent_pixels=mask_alpha,
                            pairs=int(good.sum()),
                            rmse=float(np.sqrt(np.mean(e**2))),
                            max_abs_error=float(abs(e).max()),
                            median_abs_error=float(np.median(abs(e))),
                            fraction_equal_after_rounding_to_integer=float(
                                np.mean(observed == np.rint(predicted))
                            )
                            if name == "upstream_uint16_25cm"
                            else None,
                        )
                    )
(HERE / "resampling_hypotheses.json").write_text(
    json.dumps(
        dict(
            cases=rows,
            interpretation="Independent GDAL interpolation tests; a closest numerical match does not recover the original exporter command or establish physical calibration.",
        ),
        indent=2,
    )
    + "\n"
)
print(
    [
        (
            r["target"],
            r["method"],
            r["exclude_original_transparent_pixels"],
            round(r["rmse"], 5),
        )
        for r in rows
    ]
)
