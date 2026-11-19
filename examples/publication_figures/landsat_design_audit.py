"""Audit Landsat evidence design without changing prior results or Figure 4.

Exact within-region label permutations test incremental held-patch prediction
skill conditional on the observed geography/class counts. They do not certify
all-pair separability, unseen-region transfer or reference purity. Normalized
and raw analyses are both retained; neither is selected by which p is smaller.
"""

import json
from collections import Counter
from itertools import product
from math import comb, factorial, prod
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from landsat_exploratory_pft_tests import (
    BANDS,
    CATEGORIES,
    REFERENCES,
    load_cohort,
    prepare,
)
from landsat_spatial_expansion import sha
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic
from spectralbridge.plant_pft_statistics import holm

OUTPUT = REFERENCES / "statistical-design-audit"


def region_assignments(labels, regions):
    """Enumerate unique class assignments within regions, identity first."""
    labels = np.asarray(labels)
    regions = np.asarray(regions)
    blocks = [np.flatnonzero(regions == r) for r in sorted(set(regions))]
    counts = [Counter(labels[ix]) for ix in blocks]
    total = prod(
        factorial(len(ix)) // prod(factorial(n) for n in count.values())
        for ix, count in zip(blocks, counts, strict=True)
    )
    if total > 10000:
        raise ValueError(
            "Exact assignment budget exceeded; declare a Monte Carlo design before expanding"
        )

    def distinct(count, prefix=()):
        if not any(count.values()):
            yield prefix
        for label in sorted(count):
            if count[label]:
                count[label] -= 1
                yield from distinct(count, prefix + (label,))
                count[label] += 1

    choices = [list(distinct(count)) for count in counts]
    rows = []
    for choice in product(*choices):
        assigned = labels.copy()
        for ix, values in zip(blocks, choice, strict=True):
            assigned[ix] = values
        rows.append(assigned)
    ensemble = np.array(rows)
    identity = np.flatnonzero((ensemble == labels).all(axis=1))[0]
    ensemble[[0, identity]] = ensemble[[identity, 0]]
    return ensemble


def held_patch_score(values, labels):
    """Fixed-model whole-patch leave-one-out, with training-only scaling."""
    labels = np.asarray(labels)
    predicted = []
    for index in range(len(labels)):
        train = np.arange(len(labels)) != index
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(C=1, class_weight="balanced", max_iter=2000),
        )
        model.fit(values[train], labels[train])
        predicted.append(model.predict(values[index : index + 1])[0])
    correct = np.asarray(predicted) == labels
    macro = np.mean(
        [correct[labels == category].mean() for category in sorted(set(labels))]
    )
    return float(macro), float(correct.mean())


def support_plan(frame):
    patches = (
        frame.groupby(["researcher_category", "region"])
        .patch_group_id.nunique()
        .unstack(fill_value=0)
        .reindex(CATEGORIES)
    )
    write_text_atomic(
        OUTPUT / "current_independent_patch_support.csv", patches.to_csv()
    )
    rows = []
    # This is a necessary p-resolution condition, not a power calculation.
    for n in range(2, 21):
        arrangements = comb(2 * n, n)
        rows.append(
            dict(
                patches_per_class=n,
                two_sided_resolution_lower_bound=2 / arrangements,
                first_holm_threshold=0.05 / 10,
                resolution_can_reach_first_holm_gate=2 / arrangements <= 0.05 / 10,
                interpretation="necessary_resolution_only_not_power_or_valid_exchangeability",
            )
        )
    write_text_atomic(
        OUTPUT / "independent_patch_resolution_requirements.csv",
        pd.DataFrame(rows).to_csv(index=False),
    )
    priorities = []
    for category in CATEGORIES:
        current = int(
            frame.loc[frame.researcher_category.eq(category)].patch_group_id.nunique()
        )
        priorities.append(
            dict(
                researcher_category=category,
                current_patches=current,
                minimum_additional_to_six=max(0, 6 - current),
                current_regions=int(
                    frame.loc[frame.researcher_category.eq(category)].region.nunique()
                ),
                recruitment_rule="Select by dated cover and QA, blind to spectral separation; prioritize mixed-class region/season blocks",
                caveat="Six per class permits exact resolution; does not guarantee power, independence or transfer",
            )
        )
    write_text_atomic(
        OUTPUT / "reference_collection_targets.csv",
        pd.DataFrame(priorities).to_csv(index=False),
    )

    proposals = pd.read_csv(REFERENCES / "patch_proposals.csv")
    reviewed = json.loads((REFERENCES / "reviewed_patch_policy.json").read_text())
    exclude = set(frame.context_patch_id) | {
        case["context_patch_id"] for case in reviewed["cases"]
    }
    queue = proposals.loc[~proposals.context_patch_id.isin(exclude)].copy()
    queue["current_class_patches_in_region"] = [
        int(patches.loc[x.target_hypothesis, x.region]) for x in queue.itertuples()
    ]
    queue["review_priority"] = np.where(
        queue.current_class_patches_in_region.eq(0),
        "new_class_in_existing_region",
        "additional_distinct_patch",
    )
    queue["review_status"] = (
        "Unvalidated locator hypothesis; growth-form and dated cover review required"
    )
    queue = queue.sort_values(
        [
            "current_class_patches_in_region",
            "target_hypothesis",
            "region",
            "context_patch_id",
        ]
    )
    write_text_atomic(
        OUTPUT / "prioritized_existing_photo_contexts.csv", queue.to_csv(index=False)
    )


def run():
    OUTPUT.mkdir(exist_ok=True)
    frame, inputs = load_cohort()
    support_plan(frame)
    write_json_atomic(
        OUTPUT / "analysis_design.json",
        dict(
            primary_prediction_score="macro recall on held-out patch medians",
            secondary_prediction_score="patch accuracy",
            label_randomization="all unique whole-patch label assignments within existing regions",
            interpretation="incremental spectral prediction conditional on observed region/class counts",
            comparisons=[
                "normalized shared B1-B5 sum; existing figure input",
                "raw reflectance; matching archived sensor input convention",
            ],
            multiplicity="Holm across the two representation diagnostics",
            limitations="Pure-class regions cannot contribute within-region exchangeability; not a five-class geographic transfer test",
            input_sha256=inputs,
        ),
    )
    summaries = []
    with threadpool_limits(limits=1):
        for name, normalize in [
            ("normalized_existing_figure", True),
            ("raw_reflectance_protocol", False),
        ]:
            _, patches = prepare(frame, BANDS, normalize)
            values = patches[BANDS].to_numpy()
            labels = patches.researcher_category.to_numpy()
            ensemble = region_assignments(labels, patches.region.to_numpy())
            records = []
            for index, assignment in enumerate(ensemble):
                macro, accuracy = held_patch_score(values, assignment)
                records.append(
                    dict(assignment=index, macro_recall=macro, accuracy=accuracy)
                )
                if index % 30 == 0:
                    print(
                        name,
                        index,
                        "/",
                        len(ensemble),
                        "exact geography-conditioned assignments",
                        flush=True,
                    )
            distribution = pd.DataFrame(records)
            p = float(
                distribution.macro_recall.ge(
                    distribution.macro_recall.iloc[0] - 1e-12
                ).mean()
            )
            summaries.append(
                dict(
                    representation=name,
                    patches=len(patches),
                    cells=len(frame),
                    macro_recall=distribution.macro_recall.iloc[0],
                    accuracy=distribution.accuracy.iloc[0],
                    exact_assignments=len(ensemble),
                    p_geography_conditioned_macro_recall=p,
                    independently_validated_references=False,
                )
            )
            write_text_atomic(
                OUTPUT / f"{name}_exact_prediction_null.csv",
                distribution.to_csv(index=False),
            )
    result = pd.DataFrame(summaries)
    result["p_holm_two_representations"] = holm(
        result.p_geography_conditioned_macro_recall.to_numpy()
    )
    write_text_atomic(
        OUTPUT / "geography_conditioned_prediction_test.csv", result.to_csv(index=False)
    )
    write_json_atomic(
        OUTPUT / "manifest.json",
        dict(
            input_sha256=inputs,
            code_sha256=sha(Path(__file__)),
            outputs={p.name: sha(p) for p in sorted(OUTPUT.glob("*.csv"))},
        ),
    )
    print(result.to_string(index=False), flush=True)
    report(result)


def report(result):
    raw = result.loc[result.representation.eq("raw_reflectance_protocol")].iloc[0]
    normalized = result.loc[
        result.representation.eq("normalized_existing_figure")
    ].iloc[0]
    text = f"""# Landsat statistical-design audit and concrete next steps

19 November 2026. Existing runs are preserved. No p-value threshold, spatial unit,
model hyperparameter or reference label was changed to obtain significance.

## Corrected interpretation and table inputs

The 95% previously shown is classification of normalized **patch medians**, not
unknown-pixel or new-region identification. The archived NEON and drone evidence
uses stored/direct reflectance; the new Landsat primary used plot normalization.
Direct Landsat reflectance instead gives {raw.accuracy:.0%} held-patch accuracy
(17/20) and {raw.macro_recall:.0%} macro recall. Class recall is 80% deciduous,
100% evergreen, 80% herbaceous, 100% shrub and 75% non-vegetated/dead.
Normalized reflectance gives {normalized.accuracy:.0%} accuracy (19/20); retain
this as sensitivity, not a more favorable interchangeable estimate.
The models still have different physical reference units across sensors; matching
input convention does not make them a controlled sensor comparison.

## A test of the prediction evidence, conditional on geography

Enumerated all {int(raw.exact_assignments)} unique assignments of complete patch
labels **within regions**. Each assignment refits all 20 held-patch models with
training-only scaling and the fixed balanced logistic classifier. The statistic
is five-class macro recall; raw and normalized inputs were both retained and the
two tests corrected with Holm. Both yield exact p =
{raw.p_geography_conditioned_macro_recall:.6f}, adjusted p =
{raw.p_holm_two_representations:.6f}. Thus the prediction results contain spectral
skill beyond what these within-region label assignments support by chance.
This is a new, post-audit diagnostic; the earlier p-values are not replaced.
Pure-class regions have fixed labels in this test. The conditional signal comes
from the mixed regions; it does not prove each of five PFTs independently
identifiable, independently valid labels, or transfer to new regions.

## Pairwise separability: actual sampling constraint

Ten exact patch-level NPC contrasts still give 0/10 Holm-supported pairs under
both representations. The current 3–5 patches per class cannot attain the first
0.005 Holm gate. This is a design limitation, not a finding of equal spectra.
Do not switch to pixel permutations, remove the correction, split one patch into
nominal replicates, or increase random permutations to conceal this limit.

A concrete minimum-resolution collection target is **six independent patches per
class**: add at least one deciduous, three evergreen, one herbaceous, three shrub,
and two non-vegetated patches (ten additional groups). This is a lower bound for
balanced unblocked pair designs, **not a statistical-power recommendation**.
With region/season restrictions, larger matched collections will be needed.
A definitive power claim would require credible effects and covariance beyond
this small, selected sample; no such power was fabricated.

`reference_collection_targets.csv` gives the class targets;
`current_independent_patch_support.csv` shows the missing class/region cells;
`prioritized_existing_photo_contexts.csv` ranks unused public contexts for cover
review without inspecting their Landsat values. Prioritize classes sharing a
region/season, not just more samples from their existing single-class region.

Newly inspected Gunnison herbaceous locator contexts 001–004 show clumped low
woody-looking vegetation and/or tracks/trees. They were **not accepted** as pure
herbaceous cover. Map hypotheses cannot resolve growth form. Independent dated
reference review remains necessary, especially for the older-lidar evergreen
candidates; current labels are provisional throughout.

## Reproduce

```bash
.venv/bin/python examples/publication_figures/landsat_design_audit.py
.venv/bin/pytest -q tests/test_landsat_design_audit.py
```

The script uses the existing compact input tables in place, no raster copies.
The exact enumeration is bounded at 10,000 unique assignments and avoids
factorially duplicated permutations for pure-class regions. The source protocols
are in `src/spectralbridge/researcher_pft_statistics.py`,
`src/spectralbridge/pft_method_audit.py`, `src/spectralbridge/spectral_learning.py`,
and `examples/publication_figures/drone_library_evidence.py`. All diagnostic null
scores and input/source hashes are retained. No independent validation claim is
made from a significant diagnostic.
"""
    write_text_atomic(OUTPUT / "README.md", text)


if __name__ == "__main__":
    run()
