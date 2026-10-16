"""Separate raw presence decisions, forced admission and final-fraction detection."""

import json
import numpy as np
import pandas as pd
from run_controls import BASE, REPO, PRIOR, CATS


def main():
    index = pd.read_csv(PRIOR / "tables/abundance_case_index.csv")
    index = index[
        index.method.eq("Two-stage") & index.representation.isin(["NEON", "OLI"])
    ]
    curves = []
    summary = []
    fallback = []
    old = pd.read_csv(PRIOR / "tables/two_stage_presence_metrics.csv")
    for r in index.itertuples():
        folder = (REPO / r.predictions).parent
        a = np.load(folder / (r.target + ".npz"))
        truth = pd.read_parquet(REPO / r.truth)[CATS].to_numpy()
        tuning = (
            pd.read_csv(folder / "tuning.csv")
            .set_index("researcher_category")
            .loc[CATS]
        )
        raw = a["presence_probability"] >= tuning.presence_threshold.to_numpy()
        forced = ~raw.any(axis=1)
        assert np.all(a["gate"].any(axis=1))
        fallback.append(
            dict(
                fold=r.fold,
                kind=r.kind,
                target=r.target,
                representation=r.representation,
                fallback_fraction=float(forced.mean()),
                mixtures=len(forced),
            )
        )
        for j, c in enumerate(CATS):
            actual = truth[:, j] > 0
            gate = a["gate"][:, j]
            reference = old[
                old.fold.eq(r.fold)
                & old.target.eq(r.target)
                & old.representation.eq(r.representation)
                & old.researcher_category.eq(c)
            ].iloc[0]
            assert abs(reference.stage_A_recall - gate[actual].mean()) < 1e-12
            assert abs(reference.stage_A_FPR - gate[~actual].mean()) < 1e-12
            admitted_positive = actual & gate
            summary.append(
                dict(
                    fold=r.fold,
                    kind=r.kind,
                    target=r.target,
                    representation=r.representation,
                    researcher_category=c,
                    raw_presence_recall=float(raw[actual, j].mean()),
                    raw_presence_FPR=float(raw[~actual, j].mean()),
                    admitted_presence_recall=float(gate[actual].mean()),
                    admitted_presence_FPR=float(gate[~actual].mean()),
                    admitted_positive_RMSE=float(
                        np.sqrt(
                            np.mean(
                                (
                                    a["pred"][admitted_positive, j]
                                    - truth[admitted_positive, j]
                                )
                                ** 2
                            )
                        )
                    ),
                    admitted_positive_N=int(admitted_positive.sum()),
                )
            )
            for fraction in np.unique(np.round(truth[:, j], 6)):
                use = np.round(truth[:, j], 6) == fraction
                curves.append(
                    dict(
                        fold=r.fold,
                        kind=r.kind,
                        target=r.target,
                        representation=r.representation,
                        researcher_category=c,
                        true_fraction=fraction,
                        N=int(use.sum()),
                        mean_model_presence_score=float(
                            a["presence_probability"][use, j].mean()
                        ),
                        raw_presence_detection_frequency=float(raw[use, j].mean()),
                        admitted_presence_detection_frequency=float(gate[use].mean()),
                        final_fraction_detection_frequency=float(
                            (a["pred"][use, j] >= 0.1).mean()
                        ),
                        tuned_presence_cutoff=float(tuning.presence_threshold.iloc[j]),
                    )
                )
    pd.DataFrame(curves).to_csv(
        BASE / "tables/stage_A_detection_by_fraction.csv", index=False
    )
    pd.DataFrame(summary).to_csv(
        BASE / "tables/conditional_admitted_quantification.csv", index=False
    )
    pd.DataFrame(fallback).to_csv(
        BASE / "tables/forced_presence_admission.csv", index=False
    )
    result = {
        "status": "passed",
        "target_cases": len(index),
        "fraction_rows": len(curves),
        "all_saved_Stage_A_metrics_reproduced": True,
        "raw_presence_separated_from_forced_admission": True,
        "final_fraction_cutoff": 0.1,
    }
    (BASE / "presence_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result)


if __name__ == "__main__":
    main()
