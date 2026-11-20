"""Scenario power for the unchanged NPC test under a declared matched design.

No observed effect sizes or interim p-values determine collection stopping.
Power is conditional on Gaussian patch residuals, common effects in three matched
regions and the stated per-band standardized shifts. It is not a biological
minimum-effect definition or proof of reference validity/geographic transfer.
"""

from pathlib import Path
from itertools import combinations, product
from math import comb
import json

import numpy as np
import pandas as pd
from scipy.stats import norm
from threadpoolctl import threadpool_limits

from spectralbridge.pft_method_audit import npc_probability
from spectralbridge.plant_pft_statistics import _center
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic
from landsat_spatial_expansion import OUTPUT as REFERENCES, sha

OUTPUT = REFERENCES / "power-directed-expansion" / "power-planning-v2"
DESIGN = dict(
    seed=20261119,
    seed_policy="independent per n/effect/pattern for restart determinism",
    small_label_space="enumerate exactly when assignments<=permutations+1",
    simulations=100,
    permutations=999,
    bands=7,
    patches_per_class=[6, 12, 18, 24, 36, 48, 60],
    region_blocks=3,
    standardized_shift_per_affected_band=[0.5, 1.0, 1.5],
    effect_patterns=["all_bands", "one_band"],
    residual_interband_correlation=0.6,
    family_pairs=10,
    planning_alpha=0.005,
    power_target=0.8,
    target_rule="Wilson95% lower bound >=.8; report all scenarios",
    interpretation="conditional scenario planning; no observed effect fitting; equal classes within all three regions",
)


def label_ensemble(per_region, regions, count, rng):
    labels = np.tile(np.r_[np.zeros(per_region), np.ones(per_region)], regions)
    options = (
        list(combinations(range(2 * per_region), per_region))
        if comb(2 * per_region, per_region) ** regions <= count
        else None
    )
    if options is not None:
        rows = []
        for choices in product(options, repeat=regions):
            row = np.zeros(len(labels))
            for region, indices in enumerate(choices):
                row[np.array(indices) + region * 2 * per_region] = 1
            rows.append(row)
        ensemble = np.asarray(rows)
        identity = np.flatnonzero((ensemble == labels).all(axis=1))[0]
        ensemble[[0, identity]] = ensemble[[identity, 0]]
        return labels, ensemble
    ensemble = np.empty((count, len(labels)))
    ensemble[0] = labels
    for region in range(regions):
        start = region * 2 * per_region
        random = rng.random((count - 1, 2 * per_region))
        assignment = np.zeros_like(random)
        indices = np.argpartition(random, per_region - 1, axis=1)[:, :per_region]
        np.put_along_axis(assignment, indices, 1, axis=1)
        ensemble[1:, start : start + 2 * per_region] = assignment
    return labels, ensemble


def npc_p(values, labels, ensemble, blocks):
    centered = _center(values, blocks)
    scale = np.sqrt(
        np.sum(centered**2, axis=0) / (len(values) - len(np.unique(blocks)))
    )
    x = _center(labels[:, None], blocks).ravel()
    t = ensemble @ (centered / scale) / np.sqrt(x @ x)
    statistics = np.column_stack([np.abs(t).max(axis=1), np.mean(t * t, axis=1)])
    return npc_probability(statistics)


def wilson(hits, trials):
    z = norm.ppf(0.975)
    p = hits / trials
    den = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / den
    half = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / den
    return float(center - half), float(center + half)


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    policy = OUTPUT / "power_design.json"
    if policy.exists() and json.loads(policy.read_text()) != DESIGN:
        raise ValueError("Power design changed: new version required")
    write_json_atomic(policy, DESIGN)
    rng = np.random.default_rng(DESIGN["seed"])
    covariance = np.full((7, 7), 0.6)
    np.fill_diagonal(covariance, 1)
    chol = np.linalg.cholesky(covariance)
    rows = []
    with threadpool_limits(limits=1):
        for n in DESIGN["patches_per_class"]:
            per = n // 3
            blocks = np.repeat(np.arange(3), 2 * per)
            for pattern in DESIGN["effect_patterns"]:
                for effect in DESIGN["standardized_shift_per_affected_band"]:
                    key = f"{n}-{pattern}-{effect}"
                    path = OUTPUT / f"power-checkpoint-{key}.json"
                    if path.exists():
                        rows.append(json.loads(path.read_text()))
                        continue
                    rng = np.random.default_rng(
                        np.random.SeedSequence(
                            [
                                DESIGN["seed"],
                                n,
                                int(effect * 100),
                                int(pattern == "one_band"),
                            ]
                        )
                    )
                    hits = 0
                    for _ in range(DESIGN["simulations"]):
                        labels, ensemble = label_ensemble(
                            per, 3, DESIGN["permutations"] + 1, rng
                        )
                        values = rng.normal(size=(2 * n, 7)) @ chol.T
                        shift = (
                            np.full(7, effect)
                            if pattern == "all_bands"
                            else np.r_[effect, np.zeros(6)]
                        )
                        values += labels[:, None] * shift
                        p = npc_p(values, labels, ensemble, blocks)
                        hits += p <= DESIGN["planning_alpha"]
                    low, high = wilson(hits, DESIGN["simulations"])
                    row = dict(
                        patches_per_class=n,
                        regions=3,
                        patches_per_class_per_region=per,
                        effect_pattern=pattern,
                        standardized_shift=effect,
                        simulations=DESIGN["simulations"],
                        detected=hits,
                        power=hits / DESIGN["simulations"],
                        power_low=low,
                        power_high=high,
                        meets_target=low >= 0.8,
                        code_sha256=sha(Path(__file__)),
                    )
                    write_json_atomic(path, row)
                    rows.append(row)
                    print(
                        "Power", n, pattern, effect, f"{row['power']:.0%}", flush=True
                    )
                    write_text_atomic(
                        OUTPUT / "npc_scenario_power.csv",
                        pd.DataFrame(rows).to_csv(index=False),
                    )
    results = pd.DataFrame(rows)
    targets = []
    for (pattern, effect), g in results.groupby(
        ["effect_pattern", "standardized_shift"]
    ):
        qualified = g.loc[g.meets_target].sort_values("patches_per_class")
        targets.append(
            dict(
                effect_pattern=pattern,
                standardized_shift=effect,
                target_patches_per_class=int(qualified.patches_per_class.iloc[0])
                if len(qualified)
                else None,
                supported_within_planning_range=bool(len(qualified)),
                interpretation="conditional matched-three-region scenario, not empirical achieved power",
            )
        )
    write_text_atomic(
        OUTPUT / "power_scenario_targets.csv", pd.DataFrame(targets).to_csv(index=False)
    )
    print(pd.DataFrame(targets).to_string(index=False), flush=True)


if __name__ == "__main__":
    run()
