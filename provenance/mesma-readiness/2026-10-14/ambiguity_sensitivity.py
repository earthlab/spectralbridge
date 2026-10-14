"""Test whether apparent ambiguity depends on EAR/shade-aware prototype selection."""

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from spectralbridge.mesma_readiness import load_compact_inputs
from spectralbridge.pft_method_audit import wavelength_weights
from spectralbridge.mixtures import fit_models, select_endmembers

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
T = OUT / "tables"
table, values, waves = load_compact_inputs(
    ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    ROOT / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact",
)
index = {(r.GlobalID, int(r.year)): i for i, r in table.iterrows()}
scores = pd.read_csv(T / "endmember_scores.csv")
scores = scores[scores.EAR.notna() & scores.kind.eq("plant")]
members = pd.read_parquet(T / "fold_membership.parquet")
records = []
for (scheme, fold), g in scores.groupby(["scheme", "fold"]):
    pool = np.array([index[(r.GlobalID, int(r.year))] for r in g.itertuples()])
    labels = g.label.to_numpy()
    scale = g.training_scale_stored_units.iloc[0]
    test = members[
        members.scheme.eq(scheme) & members.fold.eq(fold) & members.role.eq("test")
    ]
    tests = np.array([index[(r.GlobalID, int(r.year))] for r in test.itertuples()])
    testlabels = test.label.to_numpy()
    training = (
        values["NEON"][pool]
        / scale
        * np.sqrt(wavelength_weights(waves["NEON"]) * len(waves["NEON"]))
    )
    strategies = {
        m: select_endmembers(training, labels, m, 2) for m in ["EAR", "medoid", "MASA"]
    }
    strategies["all_proposed_candidates"] = np.arange(len(pool))
    for sensor, a in values.items():
        a = a / scale
        if sensor == "NEON":
            a = a * np.sqrt(wavelength_weights(waves["NEON"]) * a.shape[1])
        for method, ids in strategies.items():
            for c in sorted(set(labels)):
                ix = tests[testlabels == c]
                own = ids[labels[ids] == c]
                other = ids[labels[ids] != c]
                correct = cdist(a[ix], a[pool[own]]).min(1) / np.sqrt(a.shape[1])
                wrong = fit_models(
                    a[ix],
                    labels[other],
                    a[pool[other]],
                    max_components=2,
                    tolerance=0.01,
                )
                for tolerance in [0.005, 0.01, 0.02]:
                    records.append(
                        dict(
                            scheme=scheme,
                            fold=fold,
                            sensor=sensor,
                            selection=method,
                            label=c,
                            N=len(ix),
                            own_candidates=len(own),
                            total_candidates=len(ids),
                            other_material_limit=2,
                            tolerance=tolerance,
                            ambiguity_rate=float(
                                np.mean(wrong["RMSE"] <= correct + tolerance)
                            ),
                            median_own_RMSE=float(np.median(correct)),
                            median_other_RMSE=float(np.median(wrong["RMSE"])),
                            model_count=wrong["model_count"],
                        )
                    )
        print(
            scheme, fold, sensor, "ambiguity selection sensitivity complete", flush=True
        )
pd.DataFrame(records).to_csv(T / "ambiguity_selection_sensitivity.csv", index=False)
