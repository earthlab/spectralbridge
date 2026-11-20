"""Paired identity-level BRDF benchmark; fixed design, no outcome-based tuning.

Use compact stage tables only. AOP histories stay together in classification;
separability first averages histories per identity. Whole-site evidence is reported
separately from conditional polygon resampling. Unsupported transfer is NOT zero.
"""

import hashlib
import json
from pathlib import Path
from itertools import combinations, product
import time
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from spectralbridge.library_analysis import evaluate_identifiability
from spectralbridge.pft_method_audit import npc_probability, _center, permute_within
from spectralbridge.plant_pft_statistics import holm
from compare_drone_mask_pft_information import effect_change, standard_effect

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provenance/brdf-benefit-audit/2026-11-19"
OUT = BASE / "statistics"
SEED = 20261119
N = 9999
BOOT = 1999


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def npc(values, labels, blocks, *, permutations=N, seed=SEED):
    """Exact existing max/integrated NPC without unused quadratic energy matrices.

    Same centering, permutations, identity draw, scaling, discrete band weights
    and NPC calibration as pft_method_audit.method_statistics. Regression tested.
    """
    y = np.asarray(values, float)
    z = np.asarray(labels, float)
    b = np.asarray(blocks)
    mixed = [v for v in np.unique(b) if len(np.unique(z[b == v])) == 2]
    keep = np.isin(b, mixed)
    y = y[keep]
    z = z[keep]
    b = b[keep]
    if not len(y):
        raise ValueError("No exchangeable mixed sites")
    centered = _center(y, b)
    variance = np.sum(centered**2, axis=0) / (len(y) - len(mixed))
    valid = np.isfinite(y).all(axis=0) & (variance > 0)
    if valid.sum() < 2:
        raise ValueError("Insufficient complete variable channels")
    standardized = centered[:, valid] / np.sqrt(variance[valid])
    x = _center(z[:, None], b).ravel()
    xx = x @ x
    rng = np.random.default_rng(seed)
    stats = np.empty((permutations + 1, 2))
    for start in range(0, len(stats), 128):
        size = min(128, len(stats) - start)
        zz = np.stack(
            [z if start + i == 0 else permute_within(z, b, rng) for i in range(size)]
        )
        t = zz @ standardized / np.sqrt(xx)
        stats[start : start + size, 0] = abs(t).max(axis=1)
        stats[start : start + size, 1] = np.mean(t * t, axis=1)
    return npc_probability(stats), int(keep.sum()), len(mixed)


def paired_scores(pred, *, permutations=N, bootstrap=BOOT, seed=SEED):
    """Identity-average correctness, equal classes; paired stratified bootstrap.

    Models stay fixed; intervals condition on fitted folds, not new-site sampling.
    Site flips preserve correlations in each recorded domain; few sites limit p.
    """
    frame = pred.assign(correct=(pred.truth == pred.prediction).astype(float))
    unit = frame.groupby(
        ["identity", "truth", "site", "arm"], as_index=False
    ).correct.mean()
    wide = unit.pivot(
        index=["identity", "truth", "site"], columns="arm", values="correct"
    ).reset_index()
    if wide[["no_brdf", "brdf"]].isna().any().any():
        raise ValueError("Unpaired identity predictions")
    truth = wide.truth.to_numpy()
    classes = np.unique(truth)
    a = wide.no_brdf.to_numpy()
    b = wide.brdf.to_numpy()
    delta = b - a
    weights = np.array([1 / (len(classes) * sum(truth == c)) for c in truth])
    observed = delta @ weights
    rng = np.random.default_rng(seed)
    draws = []
    for start in range(0, permutations, 128):
        signs = rng.choice([-1, 1], size=(min(128, permutations - start), len(wide)))
        draws.extend(signs @ (delta * weights))
    p = (1 + np.count_nonzero(abs(np.asarray(draws)) >= abs(observed) - 1e-12)) / (
        permutations + 1
    )
    site_contributions = [
        np.sum(delta[wide.site == s] * weights[wide.site == s])
        for s in sorted(wide.site.unique())
    ]
    exact = (
        np.asarray(list(product([-1, 1], repeat=len(site_contributions))))
        @ site_contributions
    )
    samples = np.zeros(bootstrap)
    for c in classes:
        d = delta[truth == c]
        samples += d[rng.integers(len(d), size=(bootstrap, len(d)))].mean(axis=1) / len(
            classes
        )
    return dict(
        ba_no_brdf=float(a @ weights),
        ba_brdf=float(b @ weights),
        delta_ba=float(observed),
        ci_low=float(np.quantile(samples, 0.025)),
        ci_high=float(np.quantile(samples, 0.975)),
        p_identity=float(p),
        p_site_exact=float(np.mean(abs(exact) >= abs(observed) - 1e-12)),
        identities=len(wide),
        sites=len(site_contributions),
        classes=len(classes),
    )


def paired_table(frame):
    keys = ["identity", "site", "category"] + (["year"] if "year" in frame else [])
    a = frame[frame.arm == "no_brdf"].sort_values(keys).reset_index(drop=True)
    b = frame[frame.arm == "brdf"].sort_values(keys).reset_index(drop=True)
    if not a[keys].equals(b[keys]):
        raise ValueError("Source arms are not exactly paired")
    if a.groupby("identity").category.nunique().gt(1).any():
        raise ValueError("Identity label conflicts")
    if a.groupby("identity").site.nunique().gt(1).any():
        raise ValueError("Site-dependent identity needs explicit cluster design")
    return a, b


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    sources = {
        "hls": BASE / "hls/polygon_spectra.csv",
        "aop_archive": BASE / "aop/polygon_spectra.csv",
        "drone_10pct": BASE / "drone/conservative_polygon_spectra.csv",
        "drone_unmasked": BASE / "drone/baseline_polygon_spectra.csv",
    }
    identity = {
        "code": sha(Path(__file__)),
        "effect_helper": sha(ROOT / "examples/compare_drone_mask_pft_information.py"),
        "scientific_helpers": {
            name: sha(ROOT / "src/spectralbridge" / name)
            for name in [
                "library_analysis.py",
                "pft_method_audit.py",
                "plant_pft_statistics.py",
            ]
        },
        "software": {
            name: __import__("importlib.metadata", fromlist=["version"]).version(name)
            for name in ["numpy", "pandas", "scipy", "scikit-learn"]
        },
        "sources": {k: sha(p) for k, p in sources.items()},
    }
    checkpoint = OUT / "completed.json"
    if checkpoint.exists():
        old = json.loads(checkpoint.read_text())
        if old["identity"] == identity and all(
            sha(OUT / p) == h for p, h in old["outputs"].items()
        ):
            print("Verified statistics reuse", flush=True)
            return
    scores = []
    separation = []
    predictions = []
    members = []
    recalls = []
    effects = []
    with threadpool_limits(limits=1):
        for sensor, path in sources.items():
            frame = pd.read_csv(path)
            a, b = paired_table(frame)
            for count in [5, 7] if sensor in ["hls", "aop_archive"] else [5]:
                features = [f"B{i}" for i in range(1, count + 1)]
                for scheme in ["unseen_identity", "held_site"]:
                    meta = dict(sensor=sensor, bands=count, scheme=scheme)
                    try:
                        pair = []
                        for arm, data in [("no_brdf", a), ("brdf", b)]:
                            result = evaluate_identifiability(
                                data[features].to_numpy(),
                                data.category.to_numpy(),
                                data.identity.to_numpy(),
                                domains=data.site.to_numpy()
                                if scheme == "held_site"
                                else None,
                                folds=5,
                                inner_folds=2,
                                regularization=(1.0,),
                                seed=SEED,
                            )
                            pred = result["predictions"].copy()
                            pred["site"] = data.iloc[pred.row].site.to_numpy()
                            pred["arm"] = arm
                            pair.append(pred)
                            members.append(
                                result["memberships"].assign(**meta, arm=arm)
                            )
                            recalls.append(
                                result["class_metrics"].assign(**meta, arm=arm)
                            )
                        paired = pd.concat(pair, ignore_index=True)
                        metrics = paired_scores(paired)
                        scores.append(dict(**meta, status="SUPPORTED", **metrics))
                        predictions.append(paired.assign(**meta))
                        print(
                            sensor,
                            count,
                            scheme,
                            metrics["ba_no_brdf"],
                            metrics["ba_brdf"],
                            flush=True,
                        )
                    except ValueError as exc:
                        scores.append(
                            dict(**meta, status="UNSUPPORTED", reason=str(exc))
                        )
                        print(
                            sensor, count, scheme, "UNSUPPORTED", str(exc), flush=True
                        )
                # Equal-history mean, one record per independent identity for labels.
                keys = ["identity", "site", "category"]
                aa = a.groupby(keys, as_index=False)[features].mean()
                bb = b.groupby(keys, as_index=False)[features].mean()
                for index, (c0, c1) in enumerate(
                    combinations(sorted(aa.category.unique()), 2)
                ):
                    ix = aa.category.isin([c0, c1])
                    left = aa.loc[ix, features].to_numpy()
                    right = bb.loc[ix, features].to_numpy()
                    labels = (aa.loc[ix, "category"] == c1).to_numpy(float)
                    sites = aa.loc[ix, "site"].to_numpy()
                    meta = dict(
                        sensor=sensor, bands=count, category_a=c0, category_b=c1
                    )
                    try:
                        # Restrict ALL contrast statistics to sites containing both PFTs.
                        mixed = [
                            s
                            for s in np.unique(sites)
                            if len(np.unique(labels[sites == s])) == 2
                        ]
                        keep = np.isin(sites, mixed)
                        if not keep.any():
                            raise ValueError("No exchangeable mixed sites")
                        left = left[keep]
                        right = right[keep]
                        labels = labels[keep]
                        sites = sites[keep]
                        for arm, values in [("no_brdf", left), ("brdf", right)]:
                            p, n, ns = npc(values, labels, sites, seed=SEED + index)
                            separation.append(
                                dict(
                                    **meta,
                                    arm=arm,
                                    status="SUPPORTED",
                                    p_npc=p,
                                    n=n,
                                    sites=ns,
                                    effect=float(
                                        standard_effect(values, labels, sites)[0]
                                    ),
                                )
                            )
                        change = effect_change(left, right, labels, sites, SEED + index)
                        effects.append(
                            dict(
                                **meta,
                                status="SUPPORTED",
                                effect_no_brdf=change["effect_null"],
                                effect_brdf=change["effect_mask10"],
                                delta_effect=change["effect_delta"],
                                p_identity=change["p_two_sided"],
                                p_site_exact=change["p_two_sided_site_exact"],
                            )
                        )
                    except ValueError as exc:
                        for arm in ["no_brdf", "brdf"]:
                            separation.append(
                                dict(
                                    **meta,
                                    arm=arm,
                                    status="UNSUPPORTED",
                                    reason=str(exc),
                                )
                            )
                print(sensor, count, "separation complete", flush=True)
    score = pd.DataFrame(scores)
    sep = pd.DataFrame(separation)
    effect = pd.DataFrame(effects)
    for f, cols in [
        (score, ["p_identity", "p_site_exact"]),
        (sep, ["p_npc"]),
        (effect, ["p_identity", "p_site_exact"]),
    ]:
        for col in cols:
            ix = f[col].notna()
            f.loc[ix, col + "_holm_family"] = holm(f.loc[ix, col].to_numpy())
    for name, table in [
        ("identifiability", score),
        ("separability", sep),
        ("separation_changes", effect),
        ("predictions", pd.concat(predictions, ignore_index=True)),
        ("fold_memberships", pd.concat(members, ignore_index=True)),
        ("class_recalls", pd.concat(recalls, ignore_index=True)),
    ]:
        table.to_csv(OUT / f"{name}.csv", index=False)
    checkpoint.write_text(
        json.dumps(
            dict(
                identity=identity,
                elapsed_seconds=time.monotonic() - start,
                outputs={p.name: sha(p) for p in OUT.glob("*.csv")},
                inference="Conditional paired identity bootstrap/permutation, whole-site exact sensitivity; models fixed during inference; small domain counts; finite class/site confounding retained",
                multiplicity="Separate Holm families: all supported accuracy contrasts; all supported arm-specific NPC tests; all supported separation-change contrasts. Primary plus sensitivities included.",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    run()
