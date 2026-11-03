"""Confirm angular conclusions also hold on positive-source-alpha support."""

from pathlib import Path
import json
import h5py
import numpy as np
import rasterio
import analyze as a

HERE = Path(__file__).resolve().parent


def main():
    constants = []
    spatial = []
    for name in ["gordon", "goldhill", "ruby"]:
        print("Positive-alpha angular audit", name, flush=True)
        raw = np.load(
            f"/private/tmp/drone-brdf-strategy-20261102/{name}_raw.npy", mmap_mode="r"
        )
        with rasterio.open(
            f"/private/tmp/goldhill-radiometric-recovery-20261102/{name}_recovered_source_dn.tif"
        ) as src:
            alpha = src.read(11)
            pixel = src.transform.a
        valid = a.spectral_valid_mask(np.isfinite(raw).all(-1), alpha)
        with h5py.File(a.WORK / f"{name}_working.h5", "r") as h:
            meta = h[next(iter(h))]["Reflectance"]["Metadata"]
            sa = meta["Solar_Azimuth_Angle"][...]
            sz = meta["Solar_Zenith_Angle"][...]
        # Keep the original encoded full-scene solar policy fixed to isolate support.
        baseline = json.loads((HERE / "flight_baselines.json").read_text())[name]
        scene = float(
            np.mean(
                np.deg2rad(sz.astype(np.float32))[np.isfinite(raw).all(-1)],
                dtype=np.float64,
            )
        )
        values, weights = np.unique(sa[valid], return_counts=True)
        for theta in [0, 5, 10, 15, 20, 25, 30]:
            for rel in [0] if theta == 0 else [0, 45, 90, 135, 180]:
                r = a.constant_case(values, weights, scene, theta, rel)
                r.update(
                    flight=name,
                    population="finite H5 intersect positive retained TIFF alpha",
                )
                constants.append(r)
        for name_scenario in a.SCENARIOS:
            R = np.zeros((0, 3))
            n = 0
            for y in range(0, len(raw), 128):
                end = min(y + 128, len(raw))
                vz, va = a.scenario_map(
                    name_scenario, y, end, *valid.shape, pixel, a.HEIGHT[name]
                )
                X, ok = a.design(sa[y:end], sz[y:end], va, vz, valid[y:end], scene)
                A = X[ok].astype(float)
                n += len(A)
                R = np.linalg.qr(np.vstack([R, A]), mode="r")
            r = a.diagnostics(np.linalg.svd(R, compute_uv=False), n)
            r.update(
                flight=name,
                scenario=name_scenario,
                population="finite H5 intersect positive retained TIFF alpha",
            )
            spatial.append(r)
        assert int(valid.sum()) == baseline["alpha_positive_raw_pixels"]
    out = dict(
        constant_cases=constants,
        spatial_cases=spatial,
        constant_gate_passes=sum(r["angular_numerical_gate"] for r in constants),
        spatial_gate_passes=sum(r["angular_numerical_gate"] for r in spatial),
        meaning="Analytical support sensitivity only. Source arrays and H5 masks unchanged; no reflectance fitting or corrections.",
    )
    assert out["constant_gate_passes"] == 0 and out["spatial_gate_passes"] == 12
    (HERE / "alpha_positive_design_audit.json").write_text(
        json.dumps(out, indent=2) + "\n"
    )
    print("Same 0/93 constant and 12/15 spatial angular-only gate results.")


if __name__ == "__main__":
    main()
