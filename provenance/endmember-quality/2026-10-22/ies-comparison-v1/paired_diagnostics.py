"""Supplementary exploratory paired-ID coverage and capacity summaries.

Intervals describe sensitivity to sampled IDs/control draws, not external validity.
"""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from spectralbridge.library_analysis import project_simplex

OUT = Path(__file__).resolve().parent
TABLES = OUT / "tables"


def main():
    summaries = []
    for scheme in ["original", "revised"]:
        parts = []
        for name in ["old", "new"]:
            d = pd.read_csv(TABLES / f"coverage_{name}_{scheme}.csv")
            d["correct"] = (d.truth == d.prediction).astype(float)
            g = d.groupby(["GlobalID", "truth"])[
                ["correct", "same_category_RMSE"]
            ].mean()
            g.columns = [name + "_" + c for c in g]
            parts.append(g)
        both = parts[0].join(parts[1], how="inner", validate="one_to_one")
        assert len(both) == len(parts[0]) == len(parts[1])
        rng = np.random.default_rng(20261022)
        estimates = []
        bootstrap = []
        for category, group in both.groupby(level="truth"):
            delta = (
                group[["new_correct", "new_same_category_RMSE"]].to_numpy()
                - group[["old_correct", "old_same_category_RMSE"]].to_numpy()
            )
            # One aggregate observation per polygon, preserving paired libraries.
            draws = rng.integers(0, len(delta), size=(1999, len(delta)))
            estimates.append(delta.mean(0))
            bootstrap.append(delta[draws].mean(1))
        estimate = np.mean(estimates, axis=0)
        replicates = np.mean(bootstrap, axis=0)
        for j, metric in enumerate(["macro_recall", "macro_same_category_RMSE"]):
            summaries.append(
                dict(
                    scheme=scheme,
                    metric=metric,
                    new_minus_old=estimate[j],
                    conditional_2_5=np.quantile(replicates[:, j], 0.025),
                    conditional_97_5=np.quantile(replicates[:, j], 0.975),
                    IDs=len(both),
                    scope="Stratified paired polygon-ID bootstrap after averaging annual curves; sampled-ID independence assumed; supplementary exploratory interval",
                )
            )
    pd.DataFrame(summaries).to_csv(
        TABLES / "paired_coverage_comparisons.csv", index=False
    )
    d = pd.read_csv(TABLES / "capacity_control_scores.csv")
    rows = []
    for scheme, g in d.groupby("scheme"):
        p = g.pivot(index="replicate", columns="library", values="common_RMSE")
        delta = p.new - p.old
        rows.append(
            dict(
                scheme=scheme,
                old_mean=p.old.mean(),
                new_mean=p.new.mean(),
                mean_new_minus_old=delta.mean(),
                new_better_draws=int((delta < 0).sum()),
                draws=len(delta),
                delta_min=delta.min(),
                delta_max=delta.max(),
                scope="Same per-atomic-category reference counts; five draw pairs, not a population interval; parent/site capacities remain unmatched",
            )
        )
    pd.DataFrame(rows).to_csv(TABLES / "capacity_control_summary.csv", index=False)
    (OUT / "supplementary_protocol.json").write_text(
        json.dumps(
            dict(
                seed=20261022,
                coverage_resamples=1999,
                unit="One polygon after averaging annual scores; stratified by declared scheme truth",
                status="Supplementary exploratory intervals; introduced after inspecting initial point estimates",
                capacity_control="Five paired draws with exact matching counts in six atomic source groups; not matched parent/site distribution",
            ),
            indent=2,
        )
        + "\n"
    )
    geometry = []
    with np.load(OUT / "synthetic_targets.npz", allow_pickle=False) as z:
        commontruth = z["atomic_truth"] @ np.eye(4)[[0, 1, 2, 2, 3, 3]]
    for lib in ["old", "new"]:
        pair = []
        alphas = []
        values = {}
        for scheme, mapping in [
            ("original", [0, 1, 2, 3, 2]),
            ("revised", [0, 1, 2, 3, 3]),
        ]:
            info = json.loads(
                (OUT / "models" / f"{lib}_{scheme}_ridge_metadata.json").read_text()
            )
            alphas.append(info["chosen_alpha"])
            with np.load(
                OUT / "models" / f"{lib}_{scheme}_ridge.npz", allow_pickle=False
            ) as z:
                raw = z["raw_prediction"] @ np.eye(4)[mapping]
                pair.append(raw)
                values[scheme + "_raw_common_RMSE"] = float(
                    np.sqrt(np.mean((raw - commontruth) ** 2))
                )
                values[scheme + "_project_common_first_RMSE"] = float(
                    np.sqrt(np.mean((project_simplex(raw) - commontruth) ** 2))
                )
                values[scheme + "_project_native_first_RMSE"] = float(
                    np.sqrt(
                        np.mean(
                            (z["prediction"] @ np.eye(4)[mapping] - commontruth) ** 2
                        )
                    )
                )
        geometry.append(
            dict(
                library=lib,
                original_alpha=alphas[0],
                revised_alpha=alphas[1],
                maximum_raw_common_difference=float(np.abs(pair[0] - pair[1]).max()),
                **values,
            )
        )
    pd.DataFrame(geometry).to_csv(
        TABLES / "ridge_relabelling_geometry.csv", index=False
    )
    print(pd.DataFrame(summaries).to_string(index=False))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
