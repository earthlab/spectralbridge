"""Resolve arithmetic, fallback, support-selection and scale-dependence diagnostics."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import WORK, SOURCE, SCALE, WAVES, Cube, isolated, write, distribution  # noqa: E402
from spectralbridge import corrections  # noqa: E402
from spectralbridge.library_analysis import evaluate_identifiability  # noqa: E402


def main():
    raw = np.load(WORK / "raw.npy", mmap_mode="r")
    mask = np.isfinite(raw).all(-1)
    geometry = {}
    for name in ["slope", "aspect", "solar_zn", "solar_az"]:
        with rasterio.open(
            f"/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_{name}.tif"
        ) as src:
            geometry[name] = np.deg2rad(src.read(1))
    ci = corrections.calc_cosine_i(
        geometry["solar_zn"],
        geometry["solar_az"],
        geometry["aspect"],
        geometry["slope"],
    )
    ref = np.cos(geometry["solar_zn"]) * np.cos(geometry["slope"])
    fits = json.loads((HERE / "coefficients.json").read_text())
    valid = mask & np.isfinite(ci)
    guards = []
    for method in ["historical", "current", "eligible", "robust"]:
        for b, c in enumerate(fits[method]):
            den = ci + c
            num = ref + c
            guards.append(
                dict(
                    method=method,
                    wavelength_nm=int(WAVES[b]),
                    nonpositive_denominator=int((valid & (den <= 0)).sum()),
                    tiny_positive_denominator=int(
                        (valid & (den > 0) & (den <= 0.001)).sum()
                    ),
                    nonpositive_numerator=int((valid & (num <= 0)).sum()),
                    C=c,
                    pole_incidence=-c,
                    illumination=distribution(ci[valid]),
                )
            )
    write("fallback_audit.json", guards)
    C = np.asarray(fits["current"], np.float32)
    checks = []
    with rasterio.open(SOURCE) as src:
        for y in [0, 700, 1178, 2100]:
            chunk = src.read(
                window=rasterio.windows.Window(0, y, src.width, min(50, src.height - y))
            ).transpose(1, 2, 0)
            g = {k: v[y : y + len(chunk)] for k, v in geometry.items()}
            m = mask[y : y + len(chunk)]
            stored_cube = Cube(chunk, m, g, SCALE)
            decoded_cube = Cube(raw[y : y + len(chunk)].copy(), m, g, 1)
            a = isolated(corrections.apply_topo_correct)(
                stored_cube, chunk, 0, len(chunk), 0, src.width, scs_c=C
            )
            b = isolated(corrections.apply_topo_correct)(
                decoded_cube, decoded_cube.data, 0, len(chunk), 0, src.width, scs_c=C
            )
            x = stored_cube.radiometry.to_physical(a)
            checks.append(
                dict(
                    start_row=y,
                    max_abs_once_decode_difference=float(np.nanmax(abs(x - b))),
                )
            )
    # All-ten-band conversion is source affine, with missingness unchanged, no transpose/reflection.
    precision = []
    with rasterio.open(SOURCE) as src:
        for b in range(10):
            stored = src.read(b + 1)
            difference = raw[..., b] - stored * np.float32(SCALE)
            assert np.array_equal(np.isfinite(raw[..., b]), src.dataset_mask() > 0)
            precision.append(
                dict(
                    band=b + 1,
                    wavelength_nm=int(WAVES[b]),
                    max_abs_decode_difference=float(np.nanmax(abs(difference))),
                    mask_exact=True,
                )
            )
    table = pd.read_csv(HERE / "polygon_summaries.csv")
    g = table[(table.branch == "raw") & (table.support == "common")].sort_values(
        "GlobalID"
    )
    X = g[[f"b{b + 1}" for b in range(10)]].to_numpy()
    y = g.cover_category.to_numpy()
    ids = g.GlobalID.to_numpy()
    a = evaluate_identifiability(
        X, y, groups=ids, folds=3, regularization=(1,), seed=20261103
    )
    k = 65535 / 32768
    b = evaluate_identifiability(
        X / k, y, groups=ids, folds=3, regularization=(1,), seed=20261103
    )
    pd.testing.assert_frame_equal(a["memberships"], b["memberships"])
    predictions_equal = np.array_equal(
        a["predictions"].prediction, b["predictions"].prediction
    )
    assert predictions_equal
    stable = np.load(WORK / "stable_support.npy")
    fit = np.load(WORK / "fit_eligible.npy")
    common = np.load(WORK / "common.npy")
    np.savez_compressed(
        HERE / "eligibility_masks.npz",
        source_valid=mask,
        fit_eligible=fit,
        stabilized=stable,
        common=common,
        self_shadow=valid & (ci <= 0),
    )
    write(
        "additional_verification.json",
        dict(
            all_ten_band_conversion=precision,
            apply_decode_once_checks=checks,
            raw_classifier_scaling_predictions_identical=predictions_equal,
            balanced_accuracy_candidate=a["overall"]["balanced_accuracy"],
            balanced_accuracy_fixed_fraction=b["overall"]["balanced_accuracy"],
            scale_invariant=[
                "C=b/a with nonzero slope",
                "SCS+C factors with same masks",
                "Pearson correlations",
                "NDVI and spectral angle",
                "CV",
                "standardized classifier with fixed C",
            ],
            scale_dependent=[
                "Absolute reflectance and values>1",
                "absolute residuals, variance and distances",
                "near-zero slope absolute-tolerance fallback may change at extreme scales",
                "thresholds expressed in absolute units",
            ],
            no_factor_clipping=True,
        ),
    )


if __name__ == "__main__":
    main()
