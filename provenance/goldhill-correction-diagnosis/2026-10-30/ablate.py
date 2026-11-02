"""Goldhill stage-isolation experiment; existing sources/products stay read-only."""

from pathlib import Path
import json
import shutil
import sys
import time

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.neon_cube import NeonCube  # noqa: E402
from spectralbridge.corrections import (  # noqa: E402
    apply_topo_correct,
    apply_brdf_correct,
    HYTOOLS_BRDF_KERNEL_CONFIG,
)

EVIDENCE = Path(__file__).resolve().parent
WORK = Path("/private/tmp/goldhill-correction-diagnosis-20261030")
FLIGHT = Path(
    "/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1/flight_products/2023_AOP-GOLDHILL-08-14-23-ExportPackage/AOP_GOLDHILL_20230814"
)
WORK.mkdir(exist_ok=True)
model = WORK / FLIGHT.name
model.mkdir(exist_ok=True)
coeff = model / (FLIGHT.name + "_brdf_model.json")
shutil.copy2(FLIGHT / (FLIGHT.name + "__brdf_model.json"), coeff)
cube = NeonCube(FLIGHT / (FLIGHT.name + "__working.h5"))
shape = cube.data.shape
ys, xs = slice(None, None, 5), slice(None, None, 5)
np.save(WORK / "raw_preview.npy", cube.data[ys, xs])
records = {
    "shape": list(shape),
    "wavelengths_nm": cube.wavelengths.tolist(),
    "scale_factor": cube.scale_factor,
    "scope": "Full-scene existing correction functions, saved production BRDF coefficients; previews sampled every fifth pixel. No parameter refit/change.",
}


def summary(name, values):
    np.save(WORK / (name + "_preview.npy"), values[ys, xs])
    data = values[ys, xs]
    records[name] = {
        "sample_finite_fraction": np.isfinite(data).mean(axis=(0, 1)).tolist(),
        "sample_band_percentiles_1_50_99": np.nanpercentile(
            np.where(np.isfinite(data), data, np.nan), [1, 50, 99], axis=(0, 1)
        ).tolist(),
    }
    (EVIDENCE / "ablation.json").write_text(json.dumps(records, indent=2) + "\n")
    print(name, "complete", flush=True)


start = time.monotonic()
print("BRDF only starting", flush=True)
brdf = apply_brdf_correct(
    cube,
    cube.data,
    0,
    cube.lines,
    0,
    cube.columns,
    coeff_path=coeff,
    brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
)
summary("brdf_only", brdf)
del brdf
print("Topographic only starting", flush=True)
topo = apply_topo_correct(cube, cube.data, 0, cube.lines, 0, cube.columns)
summary("topo_only", topo)
np.save(WORK / "topo_full.npy", topo)
print("Combined starting", flush=True)
combined = apply_brdf_correct(
    cube,
    topo,
    0,
    cube.lines,
    0,
    cube.columns,
    coeff_path=coeff,
    brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
)
summary("combined", combined)
with rasterio.open(FLIGHT / (FLIGHT.name + "__corrected.img")) as src:
    mismatches = mask_mismatches = checked = 0
    for row in range(0, cube.lines, 128):
        block = src.read(
            window=rasterio.windows.Window(
                0, row, cube.columns, min(128, cube.lines - row)
            )
        )
        actual = np.moveaxis(combined[row : row + block.shape[1]], 2, 0)
        mask_mismatches += int(
            np.count_nonzero(np.isfinite(block) != np.isfinite(actual))
        )
        mismatches += int(np.count_nonzero(np.isfinite(block) & (block != actual)))
        checked += block.size
records["production_replay"] = {
    "values_checked": checked,
    "finite_value_mismatches": mismatches,
    "mask_mismatches": mask_mismatches,
}
records["seconds"] = time.monotonic() - start
(EVIDENCE / "ablation.json").write_text(json.dumps(records, indent=2) + "\n")
assert not mismatches and not mask_mismatches
print("Production replay exact:", records["production_replay"], flush=True)
