"""Canonical method-specific predictions reconstructed from immutable fit archives.

The raw fitting stage's baseline aliases are intermediate only. This finalizer
prevents FCLS/MESMA sharing a prediction filename; no models are refitted.
"""

import numpy as np
import pandas as pd


def prediction_frame(metadata, fractions, categories, native_residual, common_residual):
    out = metadata[["mixture_id", "bundle", "ambiguity"]].copy()
    if len(out) != len(fractions):
        raise ValueError("Misaligned fraction export")
    out["common_reconstruction_RMSE"] = common_residual
    out["native_reconstruction_RMSE"] = native_residual
    for j, c in enumerate(categories):
        out["pred_" + c] = fractions[:, j]
    return out


def baseline_filename(target, method):
    if method not in {"FCLS", "MESMA"}:
        raise ValueError("Explicit baseline method required")
    return f"{target}_{method}_predictions.parquet"


def main():
    from common import BASE, REPO, load
    from run_abundance import experiments, context, CLASSES

    t, arrays, waves, _ = load()
    index = pd.read_csv(BASE / "tables/abundance_case_index.csv")
    for name, kind, proper, cal, targets in experiments(t):
        ctx = context(t, arrays, waves, name, kind, proper, cal, targets)
        rows = index[index.fold.eq(name) & index.method.isin(["FCLS", "MESMA"])]
        for r in rows.itertuples():
            directory = (REPO / r.predictions).parent
            alias = directory / (r.target + "_predictions.parquet")
            meta = pd.read_parquet(alias)
            with np.load(directory / f"{r.target}_{r.method}.npz") as archive:
                p = archive["pred"]
                native = archive["native_RMSE"]
            common = np.sqrt(
                np.sum(
                    (
                        (p @ ctx["classmeans"] - ctx["tests"][r.target]["NEON"])
                        * ctx["weights"]
                    )
                    ** 2,
                    axis=1,
                )
            )
            output = directory / baseline_filename(r.target, r.method)
            prediction_frame(meta, p, CLASSES, native, common).to_parquet(
                output, index=False
            )
            index.loc[r.Index, "predictions"] = str(output.relative_to(REPO))
    assert not index.predictions.duplicated().any(), (
        "Two scientific cases share one export"
    )
    index.to_csv(BASE / "tables/abundance_case_index.csv", index=False)
    print(
        "Canonicalized distinct baseline exports from owned numerical fit archives; no refits."
    )


if __name__ == "__main__":
    main()
