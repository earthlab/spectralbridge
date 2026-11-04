# ruff: noqa: E402
"""Prespecified spatial sampling for footprint/height/convention sensitivity."""

import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"))
from common import SOURCE, dist, safe  # noqa:E402
from spectralbridge.drone_view_geometry import (
    camera_rays,
    NadirFootprint,
    footprint_candidates,
    assign_camera,
)  # noqa:E402

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
    ground = np.c_[t.c + (cc * 10 + 0.5) * t.a, t.f + (rr * 10 + 0.5) * t.e, z[rr, cc]]
    baseline = np.load(WORK / "geometry_native.npy", mmap_mode="r")[rr * 10, cc * 10]
    rows = []
    for label, scale, height, rotation in [
        ("base", 1, 0, 0),
        ("footprint_80pct", 0.8, 0, 0),
        ("footprint_120pct", 1.2, 0, 0),
        ("camera_height_minus30m", 1, -30, 0),
        ("camera_height_plus30m", 1, 30, 0),
        ("footprint_yaw90", 1, 0, 90),
    ]:
        count = []
        zen = []
        changed = []
        cameras = xyz.copy()
        cameras[:, 2] += height
        for start in range(0, len(ground), 1024):
            g = ground[start : start + 1024]
            v, a, d = camera_rays(g, cameras, grid_to_true_deg=gamma)
            good, center = footprint_candidates(
                d,
                heading + np.deg2rad(rotation),
                NadirFootprint(1280, 960, 5.5, 3.75, scale),
            )
            assign = assign_camera(d, good, center, rule="central")
            supported = assign >= 0
            k = np.flatnonzero(supported)
            count.extend(good.sum(1))
            zen.extend(np.rad2deg(v[k, assign[k]]))
            changed.extend(assign != baseline[start : start + len(g), 5])
        rows.append(
            dict(
                scenario=label,
                sampled_points=len(ground),
                coverage=float(np.mean(np.asarray(count) > 0)),
                C_candidate_count=dist(count),
                B_selected_zenith=dist(zen),
                B_assignment_change_fraction=float(np.mean(changed)),
            )
        )
    (HERE / "footprint_sensitivity.json").write_text(
        json.dumps(safe(rows), indent=2) + "\n"
    )
    # At the fixed four pixels preserve every candidate ray with individual kernels.
    selection = json.loads(
        (
            ROOT / "provenance/brdf-artifact-anatomy/2026-11-03/selection.json"
        ).read_text()
    )
    from spectralbridge import corrections as c

    records = []
    with rasterio.open(
        "/private/tmp/photogrammetry-metadata-20261102/goldhill_aligned_dem.tif"
    ) as dem:
        for point in selection["pixels"]:
            x, y = rasterio.transform.xy(t, point["row"], point["column"])
            z = float(next(dem.sample([(x, y)]))[0])
            v, a, d = camera_rays([[x, y, z]], xyz, grid_to_true_deg=gamma)
            good, center = footprint_candidates(
                d, heading, NadirFootprint(1280, 960, 5.5, 3.75)
            )
            j = np.flatnonzero(good[0])
            va = a[0, j]
            vz = v[0, j]
            with rasterio.open(
                "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_solar_az.tif"
            ) as src:
                sa = float(src.read(1)[point["row"], point["column"]])
            sz = np.deg2rad(27.76494)
            kv = c.calc_volume_kernel(np.deg2rad(sa), sz, va, vz, "RossThick")
            kg = c.calc_geom_kernel(
                np.deg2rad(sa), sz, va, vz, "LiDenseR", b_r=10, h_b=2
            )
            for k, i in enumerate(j):
                records.append(
                    dict(
                        point=point["label"],
                        order=int(i),
                        PhotoID=cam.PhotoID.iloc[i],
                        zenith_deg=np.rad2deg(vz[k]),
                        azimuth_deg=np.rad2deg(va[k]),
                        relative_deg=(sa - np.rad2deg(va[k])) % 360,
                        RossThick=kv[k],
                        LiDenseR=kg[k],
                        centrality=center[0, i],
                    )
                )
    pd.DataFrame(records).to_csv(HERE / "fixed_point_candidate_rays.csv", index=False)
    print("six sensitivity cases and fixed rays complete")


if __name__ == "__main__":
    main()
