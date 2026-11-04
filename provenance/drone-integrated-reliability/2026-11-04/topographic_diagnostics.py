"""Native uncapped denominator and output diagnostics, separate from plotting limits."""

import csv
import json
from pathlib import Path
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/drone-integrated-reliability-20261104/final_v2")
geom = []
for name in ["slope", "aspect", "solar_zn", "solar_az"]:
    with rasterio.open(
        "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_" + name + ".tif"
    ) as src:
        geom.append(np.deg2rad(src.read(1)))
slope, aspect, sz, sa = geom
ci = np.cos(sz) * np.cos(slope) + np.sin(sz) * np.sin(slope) * np.cos(sa - aspect)
ref = np.cos(sz) * np.cos(slope)
G = np.load(
    "/private/tmp/goldhill-viewing-geometry-20261104/geometry_native.npy", mmap_mode="r"
)
mask = np.isfinite(G[..., 0])
old = json.loads(
    (
        ROOT
        / "provenance/goldhill-viewing-geometry/2026-11-04/C_center_combined_model.json"
    ).read_text()
)["topographic_c"]
new = json.loads((HERE / "conditioned_scsc_model.json").read_text())
status = np.load(WORK / "topographic_status.npy", mmap_mode="r")
rows = []
for b, fit in enumerate(new["fits"]):
    row = dict(
        wavelength_nm=new["wavelengths_nm"][b],
        population=int(mask.sum()),
        backfacing_or_zero=int((mask & (ci <= 0)).sum()),
        old_C=old[b],
        new_C=fit["C"],
        new_C_low=fit["C_interval"][0],
        new_C_high=fit["C_interval"][1],
    )
    for name, C in [("old", old[b]), ("new", fit["C"])]:
        den = ci[mask] + C
        row.update(
            {
                name + "_denominator_nonpositive": int((den <= 0).sum()),
                name + "_denominator_abs_le_0_001": int((abs(den) <= 0.001).sum()),
                name + "_denominator_min": float(den.min()),
                name + "_denominator_q01": float(np.quantile(den, 0.01)),
            }
        )
    accepted = status[..., b] == 2
    factor = (ref[accepted] + fit["C"]) / (ci[accepted] + fit["C"])
    row["accepted_factor_max"] = float(factor.max())
    row["accepted_factor_q99"] = float(np.quantile(factor, 0.99))
    rows.append(row)
with (HERE / "native_topographic_diagnostics.csv").open("w") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
# Full unsaturated per-band output extrema and exceedances, with each support count.
out = []
for record in json.loads((HERE / "pipeline_results.json").read_text()):
    arr = np.load(record["array"], mmap_mode="r")
    for b, w in enumerate(new["wavelengths_nm"]):
        a = arr[..., b]
        a = a[np.isfinite(a) & (a > -100)]
        out.append(
            dict(
                branch=record["branch"],
                wavelength_nm=w,
                valid=len(a),
                minimum=float(a.min()),
                maximum=float(a.max()),
                above_one=int((a > 1).sum()),
                above_two=int((a > 2).sum()),
                negative=int((a < 0).sum()),
            )
        )
with (HERE / "native_output_extremes.csv").open("w") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(out[0]))
    writer.writeheader()
    writer.writerows(out)
print(
    "Native topographic diagnostics",
    len(rows),
    "bands; output diagnostics",
    len(out),
    "branch-band pairs",
)
