"""Preserve compact per-mixture residual diagnostics, without source spectra."""

import numpy as np
import pandas as pd
from run_controls import BASE, PRIOR, REPO, CATS

T = BASE / "tables"


def read(name, old=False):
    return pd.read_csv((PRIOR / "tables" if old else T) / name)


def main():
    # Every scatter point traces to one saved canonical target mixture, no copied spectra.
    case = read("abundance_case_index.csv", True)
    scatter = []
    for r in case[
        case.method.eq("MESMA")
        & case.representation.eq("NEON")
        & case.kind.isin(["plant", "site"])
    ].itertuples():
        truth = pd.read_parquet(REPO / r.truth)
        a = np.load((REPO / r.predictions).with_name(r.target + "_MESMA.npz"))
        pred = pd.read_parquet(REPO / r.predictions)[
            ["pred_" + c for c in CATS]
        ].to_numpy()
        Y = truth[CATS].to_numpy()
        scatter.append(
            pd.DataFrame(
                {
                    "fold": r.fold,
                    "kind": r.kind,
                    "mixture_id": np.arange(len(Y)),
                    "bundle": truth.bundle,
                    "native_spectral_RMSE": a["native_RMSE"],
                    "MESMA_fraction_RMSE": np.sqrt(np.mean((pred - Y) ** 2, axis=1)),
                    "max_near_fraction_range": a["ambiguity_range"],
                }
            )
        )
    scatter = pd.concat(scatter, ignore_index=True)
    scatter.to_parquet(T / "reconstruction_fraction_points.parquet", index=False)
    print("Saved", len(scatter), "per-mixture reconstruction/fraction diagnostics.")


if __name__ == "__main__":
    main()
