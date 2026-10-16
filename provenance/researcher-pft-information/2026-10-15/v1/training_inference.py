"""Training-only blocked wavelength evidence, separate from descriptive full cohorts."""

from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
import json
import logging
import numpy as np
import pandas as pd
from spectralbridge.plant_pft_statistics import _center, permute_within


def max_t_null(X, z, blocks, *, permutations=1999, seed=0):
    X, z, blocks = np.asarray(X, float), np.asarray(z, float), np.asarray(blocks)
    y = _center(X, blocks)
    scale = np.sqrt(np.sum(y * y, axis=0) / max(1, len(y) - len(np.unique(blocks))))
    scale = np.maximum(scale, 1e-12)
    x = _center(z[:, None], blocks).ravel()
    xx = x @ x
    if xx <= 0:
        raise ValueError("No within-block binary contrast")
    standardized = y / scale
    observed = z @ standardized / np.sqrt(xx)
    beta = z @ y / xx
    rng = np.random.default_rng(seed)
    maxima = []
    for start in range(0, permutations, 128):
        zs = np.stack(
            [
                permute_within(z, blocks, rng)
                for _ in range(min(128, permutations - start))
            ]
        )
        maxima.extend(abs(zs @ standardized / np.sqrt(xx)).max(axis=1))
    maxima = np.asarray(maxima)
    p = (
        1 + np.count_nonzero(maxima[:, None] >= abs(observed)[None, :] - 1e-12, axis=0)
    ) / (permutations + 1)
    return dict(beta=beta, effect=beta / scale, observed=observed, maxima=maxima, p=p)


def main():
    from common import BASE, REPO, LOG, load, folds, save, checkpoint, seed
    from spectralbridge.plant_spectral_atlas import _file_hash
    from spectralbridge.researcher_information import RESEARCHER_CATEGORIES

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t, arrays, waves, identity = load()
    identity.update(
        code=_file_hash(__file__),
        common=_file_hash(BASE / "common.py"),
        permutations=1999,
        centering=_file_hash(REPO / "src/spectralbridge/plant_pft_statistics.py"),
    )
    all_rows = []
    support = []
    for fold, kind, tr, _ in folds(t, paired=False):
        cases = []
        for (site, year), cohort in t.loc[tr].groupby(["site", "year"]):
            for a, b in combinations(RESEARCHER_CATEGORIES, 2):
                pair = cohort[cohort.label.isin([a, b])]
                blocks = pd.factorize(pair.flight_history)[0]
                z = pair.label.eq(a).to_numpy(int)
                mixed = [
                    k for k in np.unique(blocks) if len(np.unique(z[blocks == k])) == 2
                ]
                keep = np.isin(blocks, mixed)
                pair = pair.loc[keep]
                blocks = blocks[keep]
                z = z[keep]
                n_a = int(z.sum())
                n_b = int(len(z) - z.sum())
                support.append(
                    dict(
                        fold=fold,
                        kind=kind,
                        site=site,
                        year=year,
                        class_a=a,
                        class_b=b,
                        N_a=n_a,
                        N_b=n_b,
                        status="eligible"
                        if min(n_a, n_b) >= 10
                        else "insufficient_matched_training_support",
                    )
                )
                if min(n_a, n_b) >= 10:
                    cases.append(
                        (site, int(year), a, b, pair.index.to_numpy(), z, blocks)
                    )
        family = len(cases)
        LOG.info("Training-only max-T %s: %s eligible pair/cohort cases", fold, family)

        def action(case):
            site, year, a, b, ix, z, blocks = case
            name = f"{fold}/{site}_{year}_{list(RESEARCHER_CATEGORIES).index(a)}_{list(RESEARCHER_CATEGORIES).index(b)}"

            def fit(directory):
                result = max_t_null(arrays["NEON"][ix], z, blocks, seed=seed(name))
                np.savez_compressed(directory / "null.npz", **result)
                pd.DataFrame(
                    {
                        "GlobalID": t.GlobalID.iloc[ix],
                        "label": t.label.iloc[ix],
                        "year": year,
                        "site": site,
                        "block": blocks,
                    }
                ).to_csv(directory / "training_membership.csv", index=False)

            d = checkpoint("training_inference/" + name, identity, fit)
            with np.load(d / "null.npz") as r:
                return pd.DataFrame(
                    dict(
                        fold=fold,
                        kind=kind,
                        site=site,
                        year=year,
                        pair=a + " / " + b,
                        class_a=a,
                        class_b=b,
                        wavelength_nm=waves["NEON"],
                        training_matched_effect=r["effect"],
                        training_within_contrast_maxT_p=r["p"],
                        training_adjusted_p=np.minimum(1, r["p"] * family),
                        family_contrasts=family,
                        training_IDs=len(ix),
                    )
                )

        with ThreadPoolExecutor(max_workers=3) as executor:
            all_rows.extend(executor.map(action, cases))
    result = pd.concat(all_rows, ignore_index=True)
    save(result, "training_wavelength_inference.parquet")
    save(result, "training_wavelength_inference.csv")
    save(pd.DataFrame(support), "training_inference_support.csv")
    (BASE / "training_inference_scope.json").write_text(
        json.dumps(
            {
                "permutations_per_training_contrast": 1999,
                "cases": len(result) // 360,
                "family": "max-T wavelengths; Bonferroni eligible pair/cohort cases separately within each outer-training design",
                "not_selected_on_outer_data": True,
                "full_cohort_inference_is_separate": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "Completed training-only blocked wavelength inference:",
        len(result),
        "coordinate rows",
    )


if __name__ == "__main__":
    main()
