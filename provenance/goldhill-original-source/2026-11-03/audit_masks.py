"""Separate transparent high-DN background from actual source measurements."""

import json
from pathlib import Path

import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
TEMP = Path("/private/tmp/p168-goldhill-sources")
rows = []
with (
    rasterio.open(
        "/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif"
    ) as original,
    rasterio.open(TEMP / "ten_cm/aligned_orthomosaic.tif") as old,
    rasterio.open(TEMP / "derived_10cm_10k/goldhill_10cm_fixed_10k.tif") as new,
):
    alpha = original.read(11) > 0
    newmask = new.dataset_mask() > 0
    for band in range(1, 11):
        source = original.read(band)
        observed = source[alpha]
        s = old.read(band)
        t = new.read(band)
        common = newmask & np.isfinite(s) & np.isfinite(t)
        lo = source.min()
        predicted = (
            s.astype(float) * (65535 - float(lo)) / 65535 + float(lo) * 10000 / 65535
        )
        err = t[common] - predicted[common]
        native_limit = float(observed.max()) * 10000 / 65535
        n = int(common.sum())
        rows.append(
            dict(
                band=band,
                source_observed_min=int(observed.min()),
                source_observed_max=int(observed.max()),
                source_transparent_pixels=int((~alpha).sum()),
                source_65535_in_observed=int(((source == 65535) & alpha).sum()),
                source_65535_in_transparent=int(((source == 65535) & ~alpha).sum()),
                common_old_new_pixels=n,
                old_above_original_observed_max_on_common_support=int(
                    (common & (s > native_limit + 0.002)).sum()
                ),
                old_max_on_common_support=float(s[common].max()),
                new_max_on_common_support=float(t[common].max()),
                expected_no_minimum_adjustment_from_old=dict(
                    multiplier=(65535 - float(lo)) / 65535,
                    offset=float(lo) * 10000 / 65535,
                ),
                old_new_expected_mapping_residual_quantiles=np.quantile(
                    err, [0, 0.01, 0.5, 0.99, 1]
                ).tolist(),
                old_new_expected_mapping_rmse=float(np.sqrt(np.mean(err**2))),
            )
        )
(HERE / "mask_and_encoding_audit.json").write_text(
    json.dumps(
        dict(
            bands=rows,
            derivative_valid_pixels=int(newmask.sum()),
            source_valid_pixels=int(alpha.sum()),
            meaning="Endpoint counts distinguish transparent background from observed signal. Existing-product discrepancies also include spatial interpolation and missing alpha semantics; linear change alone does not reproduce a mask-aware derivative.",
        ),
        indent=2,
    )
    + "\n"
)
print("Transparent-endpoint and same-support old/new encoding audit complete")
