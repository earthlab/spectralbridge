"""Trace saved BRDF coefficients, predicted denominator and neutral-factor boundary."""

from pathlib import Path
import json
import sys

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.corrections import (  # noqa: E402
    calc_volume_kernel,
    calc_geom_kernel,
    _resolve_scene_solar_zenith,
)

F = Path(
    "/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1/flight_products/2023_AOP-GOLDHILL-08-14-23-ExportPackage/AOP_GOLDHILL_20230814"
)
WORK = Path("/private/tmp/goldhill-correction-diagnosis-20261030")
EVIDENCE = Path(__file__).resolve().parent
model = json.loads((F / (F.name + "__brdf_model.json")).read_text())
with h5py.File(F / (F.name + "__working.h5")) as h:
    m = next(iter(h.values()))["Reflectance/Metadata"]
    solar_zn = np.deg2rad(m["Solar_Zenith_Angle"][()].astype("float32"))
    scene_zn = _resolve_scene_solar_zenith(solar_zn)[::5, ::5]
    sa = np.deg2rad(m["Solar_Azimuth_Angle"][::5, ::5].astype("float32"))
    va = np.full_like(scene_zn, np.deg2rad(float(m["to-sensor_Azimuth_Angle"][()])))
    vz = np.full_like(scene_zn, np.deg2rad(float(m["to-sensor_Zenith_Angle"][()])))
kv = calc_volume_kernel(sa, scene_zn, va, vz, kernel_type=model["volume_kernel"])
kg = calc_geom_kernel(
    sa,
    scene_zn,
    va,
    vz,
    kernel_type=model["geom_kernel"],
    b_r=model["b_r"],
    h_b=model["h_b"],
)
ref_sz = np.full_like(scene_zn, np.deg2rad(45.0))
zero = np.zeros_like(sa)
ref_kv = calc_volume_kernel(
    zero, ref_sz, zero, zero, kernel_type=model["volume_kernel"]
)
ref_kg = calc_geom_kernel(
    zero,
    ref_sz,
    zero,
    zero,
    kernel_type=model["geom_kernel"],
    b_r=model["b_r"],
    h_b=model["h_b"],
)
raw = np.load(WORK / "raw_preview.npy")
brdf = np.load(WORK / "brdf_only_preview.npy")
X = np.column_stack([np.ones(kv.size), kv.ravel(), kg.ravel()])
report = {
    "sample_stride": 5,
    "design_singular_values": np.linalg.svd(X, compute_uv=False).tolist(),
    "design_condition_number": float(np.linalg.cond(X)),
    "sample_band_diagnostics": [],
}
for band in [1, 3, 4]:
    iso, vol, geo = [np.float32(model[key][0][band]) for key in ["iso", "vol", "geo"]]
    denominator = iso + vol * kv + geo * kg
    numerator = iso + vol * ref_kv + geo * ref_kg
    positive = (denominator > 0) & (numerator > 0)
    factor = np.ones_like(denominator)
    np.divide(numerator, denominator, out=factor, where=positive)
    factor = np.where(np.isfinite(factor) & (factor > 0), factor, 1.0)
    expected = raw[:, :, band] * factor
    valid = np.isfinite(raw[:, :, band]) & np.isfinite(brdf[:, :, band])
    nonzero = valid & (raw[:, :, band] != 0)
    observed = np.ones_like(factor)
    np.divide(brdf[:, :, band], raw[:, :, band], out=observed, where=nonzero)
    diagnostics = {
        "band_one_based": band + 1,
        "iso": float(iso),
        "vol": float(vol),
        "geo": float(geo),
        "R_pixel_range": [float(np.nanmin(denominator)), float(np.nanmax(denominator))],
        "R_reference_range": [float(np.nanmin(numerator)), float(np.nanmax(numerator))],
        "neutral_fraction": float(np.mean(~positive[valid])),
        "positive_factor_percentiles_0_50_100": np.percentile(
            factor[valid & positive], [0, 50, 100]
        ).tolist()
        if np.any(valid & positive)
        else [],
        "reconstructed_output_mismatches": int(
            np.count_nonzero(valid & (expected != brdf[:, :, band]))
        ),
        "neutral_guard_output_mismatches": int(
            np.count_nonzero(nonzero & ~positive & (observed != 1.0))
        ),
    }
    report["sample_band_diagnostics"].append(diagnostics)
    np.save(WORK / f"band{band + 1}_brdf_denominator.npy", denominator)
    np.save(WORK / f"band{band + 1}_brdf_factor.npy", factor)
(EVIDENCE / "brdf_mechanism.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
