"""Experimental numeric recovery only; never declares physical calibration."""

import json
from pathlib import Path
import numpy as np
import rasterio

STATUS = "RECOVERED_SOURCE_DN — PHYSICAL_UNITS_UNVERIFIED"


def inverse_values(values, minimum, maximum):
    """Undo the verified bandwise mapping without clipping or rounding to integers."""
    if not np.isfinite([minimum, maximum]).all() or maximum <= minimum:
        raise ValueError("Invalid normalization extrema")
    return (
        minimum + np.asarray(values, np.float64) * ((maximum - minimum) / 10000)
    ).astype(np.float32)


def recover_raster(source, output, mapping):
    """Preserve the source grid, masks, alpha and band order; recover spectral bands.

    An explicit shared mask is copied verbatim. Per-band nodata-derived masks
    retain the source sentinel. An alpha band is copied without normalization.
    Output must be new; inputs are never opened for writing.
    """
    source, output = Path(source), Path(output)
    if output.exists() or source.resolve() == output.resolve():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with rasterio.open(source) as src:
        profile = src.profile.copy()
        profile.update(
            dtype="float32", compress="deflate", predictor=3, BIGTIFF="IF_SAFER"
        )
        by_band = {b["band"]: b for b in mapping["bands"]}
        with rasterio.open(output, "w", **profile) as dst:
            dst.colorinterp = src.colorinterp
            dst.descriptions = src.descriptions
            dst.update_tags(**src.tags())
            dst.update_tags(
                experimental_status=STATUS,
                inverse_equation="DN = band_min + S * (band_max-band_min)/10000",
                normalization_mapping=json.dumps(mapping),
                source=str(source),
            )
            for band in range(1, src.count + 1):
                dst.update_tags(band, **src.tags(band))
                nvalid = lost = 0
                max_roundtrip = 0.0
                for _, window in src.block_windows(band):
                    data = src.read(band, window=window)
                    mask = src.read_masks(band, window=window) > 0
                    valid = mask & np.isfinite(data)
                    recovered = data.astype("float32")
                    if band in by_band:
                        b = by_band[band]
                        recovered[valid] = inverse_values(
                            data[valid], b["original_min"], b["original_max"]
                        )
                        roundtrip = (
                            (recovered[valid].astype("float64") - b["original_min"])
                            * 10000
                            / (b["original_max"] - b["original_min"])
                        )
                        if valid.any():
                            max_roundtrip = max(
                                max_roundtrip,
                                float(np.max(abs(roundtrip - data[valid]))),
                            )
                    lost += int(np.count_nonzero(valid & ~np.isfinite(recovered)))
                    nvalid += int(valid.sum())
                    dst.write(recovered, band, window=window)
                rows.append(
                    dict(
                        band=band,
                        valid_pixels=nvalid,
                        newly_nonfinite=lost,
                        max_normalized_roundtrip_error=max_roundtrip,
                        operation="inverse"
                        if band in by_band
                        else "unchanged auxiliary/alpha",
                    )
                )
            if any(
                rasterio.enums.MaskFlags.per_dataset in flags
                for flags in src.mask_flag_enums
            ):
                for _, window in src.block_windows(1):
                    dst.write_mask(src.dataset_mask(window=window), window=window)
    with rasterio.open(source) as a, rasterio.open(output) as b:
        assert (
            a.transform == b.transform
            and a.crs == b.crs
            and a.shape == b.shape
            and a.count == b.count
        )
        for band in range(1, a.count + 1):
            assert np.array_equal(a.read_masks(band), b.read_masks(band)), (
                source,
                band,
                "mask changed",
            )
        assert a.colorinterp == b.colorinterp
    return dict(
        source=str(source),
        recovered=str(output),
        status=STATUS,
        grid_unchanged=True,
        masks_unchanged=True,
        bands=rows,
    )
