"""Prespecified size/ideal-shade sensitivities on the SAME held-out parent mixtures."""

from pathlib import Path
import json
import time
from itertools import combinations
import numpy as np
import pandas as pd
from spectralbridge.mesma_readiness import load_compact_inputs
from spectralbridge.pft_method_audit import wavelength_weights
from spectralbridge.mixtures import select_endmembers, fit_models, fcls

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "artifacts/plant_spectral_atlas/mesma_readiness"
T = OUT / "tables"
table, values, waves = load_compact_inputs(
    ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    ROOT / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact",
)
index = {(r.GlobalID, int(r.year)): i for i, r in table.iterrows()}
scores = pd.read_csv(RUN / "tables/endmember_scores.csv")
scores = scores[scores.EAR.notna()]
truth = pd.read_parquet(RUN / "tables/synthetic_mixture_truth.parquet")
truth = truth[truth.kind.eq("plant")]
members = pd.read_parquet(RUN / "tables/fold_membership.parquet")
size_results = []
shade_results = []
for (scheme, fold), g in scores[scores.kind.eq("plant")].groupby(["scheme", "fold"]):
    pool = np.array([index[(r.GlobalID, int(r.year))] for r in g.itertuples()])
    labels = g.label.to_numpy()
    classes = sorted(set(labels))
    scale = g.training_scale_stored_units.iloc[0]
    parent_labels = (
        members[(members.scheme == scheme) & members.fold.eq(fold)]
        .drop_duplicates("GlobalID")
        .set_index("GlobalID")
        .label.to_dict()
    )
    tests = truth[truth.scheme.eq(scheme) & truth.fold.eq(fold)].sort_values(
        "mixture_id"
    )
    ftrue = np.array(
        [[json.loads(v).get(c, 0) for c in classes] for v in tests.true_fractions]
    )
    for sensor, a in values.items():
        a = a / scale
        if sensor == "NEON":
            a = a * np.sqrt(wavelength_weights(waves["NEON"]) * a.shape[1])
        targets = []
        for r in tests.itertuples():
            f = json.loads(r.true_fractions)
            target = np.zeros(a.shape[1])
            for source in r.source_ids.split("|"):
                identity, year = source.split("@")
                target += (
                    f.get(parent_labels[identity], 0) * a[index[(identity, int(year))]]
                )
            targets.append(target)
        targets = np.array(targets)
        for size in [1, 2, 5, 10]:
            ids = select_endmembers(
                values["NEON"][pool]
                / scale
                * np.sqrt(wavelength_weights(waves["NEON"]) * len(waves["NEON"])),
                labels,
                "EAR",
                size,
                seed=20261014,
            )
            counts = [int(np.sum(labels[ids] == c)) for c in classes]
            count = sum(
                sum(
                    np.prod([counts[i] for i in ix], dtype=np.int64)
                    for ix in combinations(range(len(classes)), n)
                )
                for n in range(1, min(3, len(classes)) + 1)
            )
            if count > 20000:
                size_results.append(
                    dict(
                        scheme=scheme,
                        fold=fold,
                        sensor=sensor,
                        requested_per_class=size,
                        status="exact_model_budget_exceeded_not_pruned",
                        model_count=int(count),
                    )
                )
                continue
            start = time.perf_counter()
            fit = fit_models(
                targets, labels[ids], a[pool[ids]], max_components=3, tolerance=0.01
            )
            estimates = np.zeros_like(ftrue)
            for j, c in enumerate(fit["classes"]):
                estimates[:, classes.index(c)] = fit["fractions"][:, j]
            for j, c in enumerate(classes):
                size_results.append(
                    dict(
                        scheme=scheme,
                        fold=fold,
                        sensor=sensor,
                        label=c,
                        requested_per_class=size,
                        selected_per_class=counts[j],
                        status="evaluated",
                        model_count=int(count),
                        N=len(targets),
                        fraction_RMSE=float(
                            np.sqrt(np.mean((estimates[:, j] - ftrue[:, j]) ** 2))
                        ),
                        reconstruction_RMSE=float(fit["RMSE"].mean()),
                        seconds=time.perf_counter() - start,
                    )
                )
        mids = select_endmembers(
            values["NEON"][pool]
            / scale
            * np.sqrt(wavelength_weights(waves["NEON"]) * len(waves["NEON"])),
            labels,
            "medoid",
            1,
        )
        shaded = targets * 0.75
        no = fcls(shaded, a[pool[mids]])["fractions"]
        explicit = fcls(shaded, np.vstack([a[pool[mids]], np.zeros(a.shape[1])]))[
            "fractions"
        ]
        normalized = np.divide(
            explicit[:, :-1],
            explicit[:, :-1].sum(1, keepdims=True),
            out=np.full_like(no, np.nan),
            where=explicit[:, :-1].sum(1, keepdims=True) > 1e-12,
        )
        for formulation, estimand, f, target in [
            ("no_shade", "total_footprint", no, ftrue * 0.75),
            ("explicit_black_shade", "total_footprint", explicit[:, :-1], ftrue * 0.75),
            ("no_shade", "nonshade_composition", no, ftrue),
            ("shade_normalized", "nonshade_composition", normalized, ftrue),
        ]:
            for j, c in enumerate(classes):
                shade_results.append(
                    dict(
                        scheme=scheme,
                        fold=fold,
                        sensor=sensor,
                        label=c,
                        formulation=formulation,
                        estimand=estimand,
                        N=len(target),
                        fraction_RMSE=float(
                            np.sqrt(np.nanmean((f[:, j] - target[:, j]) ** 2))
                        ),
                        mean_bias=float(np.nanmean(f[:, j] - target[:, j])),
                        shade_truth=0.25,
                        shade_estimate_mean=float(explicit[:, -1].mean()),
                    )
                )
        print(scheme, fold, sensor, "size and shade sensitivity complete", flush=True)
pd.DataFrame(size_results).to_csv(T / "library_size_fraction_recovery.csv", index=False)
pd.DataFrame(shade_results).to_csv(T / "shade_formulation_comparison.csv", index=False)
print("No measured shade or real cover truth claimed.")
