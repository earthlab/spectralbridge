"""Prespecified spatial/vegetation/terrain controls, never PFT-tuned corrections."""

import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment_support import ROOT, WORK, write, load_cube, isolated, c, Cube  # noqa:E402


def main():
    full, design, _, maps, _ = load_cube()
    stride = 10
    data = full.data[::stride, ::stride]
    X = design[::stride, ::stride]
    mask = full.mask_no_data[::stride, ::stride]
    geometry = {n: a[::stride, ::stride] for n, a in full.geometry.items()}
    train = np.load(WORK / "training_mask.npy", mmap_mode="r")[::stride, ::stride]
    yy, xx = np.indices(mask.shape)
    groups = (yy // 20) * 100 + (xx // 20)
    digest = hashlib.sha256(np.ascontiguousarray(X).tobytes()).hexdigest()
    legmap = pd.read_csv(
        ROOT / "provenance/goldhill-viewing-geometry/2026-11-04/acquisition_path.csv"
    ).leg.to_numpy()
    camera = maps[::stride, ::stride, 2]
    legs = np.full(mask.shape, -1, int)
    valid = mask & np.isfinite(camera) & (camera >= 0)
    legs[valid] = legmap[camera[valid].astype(int)]
    cfg = json.loads(
        (ROOT / "provenance/goldhill-end-to-end/2026-11-03/branches.json").read_text()
    )
    idx = pd.read_parquet(cfg["polygon_index"])
    classes = sorted(idx.cover_category.unique())
    labels = np.full(full.mask_no_data.shape, -1, np.int8)
    for k, label in enumerate(classes):
        group = idx[idx.cover_category == label]
        labels[group.row.to_numpy(), group.col.to_numpy()] = k
    labels = labels[::stride, ::stride]
    # Independent raw-appearance homogeneity rule, defined before corrected outputs:
    # a3x3sample neighbourhood (~3m), NDVI>.5, red/NIR CV<.15, enough valid cells.
    raw = np.asarray(data, float)
    good = np.isfinite(raw).all(-1) & mask
    count = uniform_filter(good.astype(float), size=3)
    hom = (
        good
        & (((raw[..., 9] - raw[..., 4]) / (raw[..., 9] + raw[..., 4] + 1e-20)) > 0.5)
        & (count > 0.99)
    )
    for b in [4, 9]:
        v = np.where(good, raw[..., b], 0)
        mean = uniform_filter(v, size=3)
        variance = np.maximum(uniform_filter(v * v, size=3) - mean**2, 0)
        hom &= np.sqrt(variance) / np.maximum(abs(mean), 1e-20) < 0.15
    slope = geometry["slope"]
    incidence = c.calc_cosine_i(
        np.deg2rad(geometry["solar_zn"]),
        np.deg2rad(geometry["solar_az"]),
        np.deg2rad(geometry["aspect"]),
        np.deg2rad(slope),
    )
    spatialfold = (yy // 50 + xx // 50) % 3
    cases = [
        ("global_sample", mask, train, None),
        ("homogeneous_raw_targets", mask, train & hom, None),
        ("global_spatial_covariance", mask, train, groups),
    ]
    for k in range(3):
        cases.append((f"spatial_holdout{k}", mask, train & (spatialfold != k), None))
        cases.append((f"flight_leg_holdout{k}", mask, train & ((legs % 3) != k), None))
    for k, label in enumerate(classes):
        cases.append(("PFT_" + label, mask & (labels == k), None, None))
    for lo, hi in [(5, 15), (15, 30), (30, 90)]:
        cases.append(
            (f"slope{lo}_{hi}", mask & (slope >= lo) & (slope < hi), train, None)
        )
    for lo, hi in [(0, 0.4), (0.4, 0.7), (0.7, 1.01)]:
        cases.append(
            (
                f"incidence{lo}_{hi}",
                mask & (incidence >= lo) & (incidence < hi),
                train,
                None,
            )
        )
    # Source positions selected in acquisition order, not correction appearance.
    path = pd.read_csv(
        ROOT / "provenance/goldhill-viewing-geometry/2026-11-04/acquisition_path.csv"
    )
    from spectralbridge.drone_view_geometry import (
        camera_rays,
        NadirFootprint,
        footprint_candidates,
    )
    import rasterio

    with rasterio.open(
        "/private/tmp/photogrammetry-metadata-20261102/goldhill_aligned_dem.tif"
    ) as src:
        z = src.read(1)[::stride, ::stride]
    with rasterio.open(full.h5_path) as src:
        t = src.transform
    gx = t.c + (xx * stride + 0.5) * t.a
    gy = t.f + (yy * stride + 0.5) * t.e
    ground = np.c_[gx.ravel(), gy.ravel(), z.ravel()]
    for k in np.linspace(0, 564, 8, dtype=int):
        camera = path.iloc[k]
        _, _, d = camera_rays(
            ground,
            camera[["X", "Y", "Z"]].to_numpy(float)[None],
            grid_to_true_deg=-0.3184058833629672,
        )
        eligible, _ = footprint_candidates(
            d,
            [np.deg2rad(camera.heading_grid_deg)],
            NadirFootprint(1280, 960, 5.5, 3.75),
        )
        cases.append(
            (f"footprint{k}", mask & eligible[:, 0].reshape(mask.shape), train, None)
        )
    results = []
    records = []
    for name, domain, sampling, unc in cases:
        print("SPATIAL CONTROL", name, int(domain.sum()), flush=True)
        cube = Cube(data, domain, geometry, scale=1, footprint=mask)
        try:
            p = isolated(c.fit_and_save_brdf_model, X, digest)(
                cube,
                WORK / "spatial_controls_v1" / name.replace(" ", "_"),
                brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
                fitting_mask=sampling,
                fitting_provenance={
                    "strategy": name,
                    "lattice": "every10thnativepixel; no spatial averaging",
                    "class_fits": "coefficient diagnostics only; no class-label-corrected PFT score",
                    "calibration": "HYPOTHETICAL_UNVERIFIED",
                },
                uncertainty_groups=unc,
            )
            m = json.loads(p.read_text())
            fits = m["validation"]["fits"]
            status = m["validation"]["status"]
        except Exception as exc:
            fits = []
            status = "UNSUPPORTED"
            m = {"error": str(exc)}
        results.append(
            dict(
                case=name,
                status=status,
                source_pixels=int(domain.sum()),
                fits=fits,
                error=m.get("error"),
            )
        )
        if status == "VALID":
            beta = np.array(
                [[m[key][0][b] for key in ["iso", "vol", "geo"]] for b in range(10)]
            )
            # Holdout metrics are prediction errors, not proof of directional correction.
            if name.startswith("spatial_holdout"):
                test = mask & (spatialfold == int(name[-1]))
            elif name.startswith("flight_leg_holdout"):
                test = mask & ((legs % 3) == int(name[-1]))
            else:
                test = domain
            for b in [4, 7, 9]:
                pred = X[test] @ beta[b]
                truth = data[..., b][test]
                records.append(
                    dict(
                        case=name,
                        band=b,
                        n=int(test.sum()),
                        prediction_rmse=float(np.sqrt(np.nanmean((truth - pred) ** 2))),
                        mean_baseline_rmse=float(
                            np.sqrt(
                                np.nanmean(
                                    (
                                        truth
                                        - np.nanmean(
                                            data[..., b][
                                                domain
                                                & (
                                                    sampling
                                                    if sampling is not None
                                                    else True
                                                )
                                            ]
                                        )
                                    )
                                    ** 2
                                )
                            )
                        ),
                        iso=beta[b, 0],
                        vol=beta[b, 1],
                        geo=beta[b, 2],
                    )
                )
    write("spatial_control_results.json", results)
    pd.DataFrame(records).to_csv(HERE / "spatial_holdout_metrics.csv", index=False)
    # Spatially structured permutation control: translate entire 50m-block labels,
    # preserving local signal structure. It is a confounding sensitivity, not a p-value.
    valid = mask & train & np.isfinite(data).all(-1)
    controls = []
    for shift in [0, 25, 50, 75, 100]:
        shuffled = np.roll(data[..., 4], shift, axis=1)
        choose = valid & np.isfinite(shuffled)
        A = X[choose]
        target = shuffled[choose]
        beta = np.linalg.lstsq(A, target, rcond=None)[0]
        r2 = 1 - np.sum((target - A @ beta) ** 2) / np.sum(
            (target - target.mean()) ** 2
        )
        controls.append(
            dict(column_shift_native_pixels=shift * 10, R2=float(r2), beta=beta)
        )
    write("spatial_shift_controls.json", controls)
    write(
        "sampling_contract.json",
        dict(
            sampled_native_shape=list(data.shape),
            stride=10,
            PFT_labels_unchanged=classes,
            homogeneity="rawNDVI>.5 and3x3sample red/NIR CV<.15, complete neighbourhood; independent of corrected appearance",
            class_models_used_for_PFT=False,
            uncertainty_groups="20m spatial blocks",
            holdouts="50m spatial blocks and nearest-camera flight-leg modulo3",
            permutation="prespecified whole-image horizontal translations; sensitivity diagnostic, not a physical BRDF significance test",
        ),
    )
    print("SPATIAL CONTROLS COMPLETE")


if __name__ == "__main__":
    main()
