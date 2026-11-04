# ruff: noqa: E402
"""Conditional fit sensitivity on the prespecified every-tenth native pixel lattice."""

import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"))
from common import Cube, isolated, SOURCE, safe, dist  # noqa:E402
from spectralbridge.drone_view_geometry import (
    NadirFootprint,
    camera_rays,
    footprint_candidates,
    assign_camera,
    aggregate_kernels,
)  # noqa:E402
from spectralbridge import corrections as c  # noqa:E402
from fit_experiments import blend_adapter  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")


def main():
    cam = pd.read_csv(HERE / "acquisition_path.csv")
    xyz = cam[["X", "Y", "Z"]].to_numpy()
    heading = np.deg2rad(cam.heading_grid_deg.to_numpy())
    gamma = json.loads((HERE / "flight_and_crs.json").read_text())["north_rotation_deg"]
    with rasterio.open(SOURCE) as src:
        mask = src.dataset_mask()[::10, ::10] > 0
        t = src.transform
    with rasterio.open(
        "/private/tmp/photogrammetry-metadata-20261102/goldhill_aligned_dem.tif"
    ) as src:
        z = src.read(1)[::10, ::10]
    rr, cc = np.nonzero(mask & np.isfinite(z))
    rr *= 10
    cc *= 10
    ground = np.c_[
        t.c + (cc + 0.5) * t.a, t.f + (rr + 0.5) * t.e, z[rr // 10, cc // 10]
    ]
    raw = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
        mmap_mode="r",
    )[rr, cc][:, None, :]
    solar = {}
    for n in ["solar_az", "solar_zn"]:
        with rasterio.open(
            "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_" + n + ".tif"
        ) as src:
            solar[n] = src.read(1)[rr, cc][:, None]
    sz = np.mean(np.deg2rad(solar["solar_zn"].astype(np.float32)), dtype=np.float64)
    results = []
    for label, scale, height, rotation in [
        ("base", 1, 0, 0),
        ("footprint_80pct", 0.8, 0, 0),
        ("footprint_120pct", 1.2, 0, 0),
        ("height_minus30", 1, -30, 0),
        ("height_plus30", 1, 30, 0),
        ("yaw90", 1, 0, 90),
    ]:
        print("FIT SENSITIVITY", label, flush=True)
        cameras = xyz.copy()
        cameras[:, 2] += height
        rays = {
            k: np.full((len(rr), 1), np.nan, np.float32)
            for k in ["A_zen", "A_az", "B_zen", "B_az"]
        }
        designs = {
            k: np.full((len(rr), 1, 3), np.nan) for k in ["C_uniform", "C_center"]
        }
        for start in range(0, len(rr), 1024):
            end = min(len(rr), start + 1024)
            v, a, d = camera_rays(ground[start:end], cameras, grid_to_true_deg=gamma)
            good, central = footprint_candidates(
                d,
                heading + np.deg2rad(rotation),
                NadirFootprint(1280, 960, 5.5, 3.75, scale),
            )
            ii, jj = np.nonzero(good)
            sa = np.deg2rad(solar["solar_az"][start:end, 0].astype(np.float32))
            vz = np.deg2rad(np.rad2deg(v[ii, jj]).astype(np.float32))
            va = np.deg2rad(np.rad2deg(a[ii, jj]).astype(np.float32))
            kv = np.full(good.shape, np.nan)
            kg = kv.copy()
            kv[ii, jj] = c.calc_volume_kernel(
                sa[ii], np.float32(sz), va, vz, "RossThick"
            )
            kg[ii, jj] = c.calc_geom_kernel(
                sa[ii], np.float32(sz), va, vz, "LiDenseR", b_r=10, h_b=2
            )
            for key, rule in [("A", "nearest"), ("B", "central")]:
                assigned = assign_camera(d, good, central, rule=rule)
                valid = assigned >= 0
                k = np.flatnonzero(valid)
                rays[key + "_zen"][start + k, 0] = np.rad2deg(v[k, assigned[k]])
                rays[key + "_az"][start + k, 0] = np.rad2deg(a[k, assigned[k]])
            designs["C_uniform"][start:end, 0] = aggregate_kernels(kv, kg, good)
            designs["C_center"][start:end, 0] = aggregate_kernels(
                kv, kg, good, centrality=central
            )
        for scenario in ["A", "B", "C_uniform", "C_center"]:
            g = dict(solar)
            if scenario in ["A", "B"]:
                g.update(
                    sensor_zn=rays[scenario + "_zen"], sensor_az=rays[scenario + "_az"]
                )
            else:
                g.update(
                    sensor_zn=np.zeros((len(rr), 1), np.float32),
                    sensor_az=np.zeros((len(rr), 1), np.float32),
                )
            cube = Cube(raw, np.ones((len(rr), 1), bool), g, scale=1)
            if scenario in ["A", "B"]:
                f = isolated(c.fit_and_save_brdf_model)
            else:
                f = blend_adapter(
                    c.fit_and_save_brdf_model,
                    designs[scenario],
                    __import__("hashlib")
                    .sha256(designs[scenario].tobytes())
                    .hexdigest(),
                )
            modelpath = f(
                cube,
                WORK / "sampled_sensitivity_v1" / (label + "_" + scenario),
                brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
            )
            m = json.loads(modelpath.read_text())
            summary = dict(
                case=label,
                scenario=scenario,
                sampled_points=len(rr),
                status=m["validation"]["status"],
                fits=m["validation"]["fits"],
                full_native_image_created=False,
            )
            if m["validation"]["status"] == "VALID":
                if scenario in ["A", "B"]:
                    X, valid, _ = c._brdf_design(cube, c.HYTOOLS_BRDF_KERNEL_CONFIG)
                else:
                    X = designs[scenario]
                    valid = np.isfinite(X).all(-1)
                band = 4
                beta = np.array([m[k][0][band] for k in ["iso", "vol", "geo"]])
                ref = np.array(m["reference_design"]) @ beta
                factors = ref / (X @ beta)
                summary["red_BRDF_factor"] = dist(factors[valid])
                summary["red_reference_prediction"] = ref
            results.append(summary)
    (HERE / "fit_sensitivity.json").write_text(
        json.dumps(safe(results), indent=2) + "\n"
    )
    print("24 sensitivity fits complete")


if __name__ == "__main__":
    main()
