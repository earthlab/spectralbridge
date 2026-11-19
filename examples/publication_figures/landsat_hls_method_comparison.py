"""Compare fixed statistical and predictive definitions on expanded HLS data.

No model or purity threshold is selected by performance. Primary cohort restores
original nominal >=95% cover; 4x4 source-area purity remains sensitivity. Pairwise
balanced accuracy estimates discriminability and does not replace NPC p-values.
"""

from pathlib import Path
from itertools import combinations

import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from landsat_exploratory_pft_tests import (
    BANDS,
    CATEGORIES,
    prepare,
    separability,
    identify,
    summarize,
)
from landsat_hls_pft_tests import validate, table_summary
from landsat_spatial_expansion import OUTPUT as REFERENCES, sha
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

SOURCE = REFERENCES / "hls-l30-expanded-references"
OUTPUT = REFERENCES / "hls-l30-expanded-analysis"
DESIGN = dict(
    primary_cohort="nominal HLS footprint >=95% mapped cover; restored original reference definition",
    sensitivity="full 4x4 native source-area >=95%; extra conservative diagnostic",
    reflectance="B1–B7 direct NBAR; no plot normalization",
    statistical_separation="unchanged exact patch-level max/integrated NPC; Holm family10",
    predictive_discriminability="fixed pairwise logistic leave-one-patch-out; balanced accuracy, chance50%",
    identification="fixed five-class logistic leave-one-patch-out; class recall",
    preprocessing="training-only StandardScaler; balanced logistic C1; no tuning",
    selection="no rejection of references by spectral fit or test outcome; all reviewed passes retained",
    interpretation="pairwise BA is an estimate, not a significance claim or independent reference validation",
)


def pairwise_prediction(patches, bands=BANDS):
    scores = []
    predictions = []
    for a, b in combinations(CATEGORIES, 2):
        pair = patches.loc[patches.researcher_category.isin([a, b])].reset_index(
            drop=True
        )
        counts = pair.researcher_category.value_counts()
        if min(counts.get(a, 0), counts.get(b, 0)) < 2:
            scores.append(
                dict(
                    a=a,
                    b=b,
                    balanced_accuracy=np.nan,
                    n_a=int(counts.get(a, 0)),
                    n_b=int(counts.get(b, 0)),
                    status="insufficient_patch_support",
                )
            )
            continue
        records = []
        for index, test in pair.iterrows():
            train = pair.loc[pair.index != index]
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(C=1, class_weight="balanced", max_iter=2000),
            )
            model.fit(train[bands], train.researcher_category)
            prediction = model.predict(pair.loc[[index], bands])[0]
            record = dict(
                a=a,
                b=b,
                patch_group_id=test.patch_group_id,
                truth=test.researcher_category,
                prediction=prediction,
                train_patches=len(train),
                held_patch_in_training=False,
            )
            records.append(record)
            predictions.append(record)
        results = pd.DataFrame(records)
        recall_a = float(
            results.loc[results.truth.eq(a)]
            .truth.eq(results.loc[results.truth.eq(a)].prediction)
            .mean()
        )
        recall_b = float(
            results.loc[results.truth.eq(b)]
            .truth.eq(results.loc[results.truth.eq(b)].prediction)
            .mean()
        )
        scores.append(
            dict(
                a=a,
                b=b,
                balanced_accuracy=(recall_a + recall_b) / 2,
                recall_a=recall_a,
                recall_b=recall_b,
                n_a=int(counts[a]),
                n_b=int(counts[b]),
                status="held_patch_point_estimate",
            )
        )
    return pd.DataFrame(scores), pd.DataFrame(predictions)


def add_pairwise_estimates(table, pairs):
    table = table.copy()
    for index, row in table.iterrows():
        values = pairs.loc[
            pairs.a.eq(row.researcher_category) | pairs.b.eq(row.researcher_category)
        ].balanced_accuracy.dropna()
        table.loc[index, "pairwise_mean_ba"] = values.mean()
        table.loc[index, "pairwise_min_ba"] = values.min()
        table.loc[index, "pairwise_max_ba"] = values.max()
        table.loc[index, "pairwise_estimated_pairs"] = len(values)
    return table


def run():
    OUTPUT.mkdir(exist_ok=True)
    write_json_atomic(OUTPUT / "analysis_design.json", DESIGN)
    inputs = {}
    overviews = []
    for name, filename, strict in [
        ("nominal_primary", "hls_l30_nominal_95pct_observations.csv", False),
        (
            "source_support_sensitivity",
            "hls_l30_strict_source_support_95pct_observations.csv",
            True,
        ),
    ]:
        path = SOURCE / filename
        inputs[filename] = sha(path)
        frame = pd.read_csv(path)
        validate(frame, strict)
        cells, patches = prepare(frame, BANDS, normalize=False)
        npc = separability(patches, BANDS)
        predictions = identify(cells, patches, BANDS)
        pair_scores, pair_predictions = pairwise_prediction(patches)
        table = add_pairwise_estimates(table_summary(npc, predictions), pair_scores)
        dest = OUTPUT / name
        dest.mkdir(exist_ok=True)
        for filename, data in [
            ("patch_median_reflectance.csv", patches),
            ("separability.csv", npc),
            ("held_out_predictions.csv", predictions),
            ("identifiability_summary.csv", summarize(predictions)),
            ("pairwise_balanced_accuracy.csv", pair_scores),
            ("pairwise_held_patch_predictions.csv", pair_predictions),
            ("figure_table_summary.csv", table),
        ]:
            write_text_atomic(dest / filename, data.to_csv(index=False))
        held = predictions.loc[
            predictions.unit.eq("patch") & predictions.scheme.eq("leave_one_patch_out")
        ]
        supported = held.loc[held.truth_in_training]
        overviews.append(
            dict(
                cohort=name,
                cells=len(frame),
                patch_groups=len(patches),
                five_class_patch_accuracy=float(held.truth.eq(held.prediction).mean())
                if held.truth_in_training.all()
                else np.nan,
                correct_supported=int(supported.truth.eq(supported.prediction).sum()),
                supported_patches=len(supported),
                unsupported_patches=len(held) - len(supported),
                pairwise_mean_ba=float(pair_scores.balanced_accuracy.mean()),
                npc_testable_pairs=int(
                    npc.loc[npc.scope.str.startswith("pooled")].p_npc.notna().sum()
                ),
                npc_supported_pairs=int(
                    npc.loc[npc.scope.str.startswith("pooled")]
                    .p_npc_holm.le(0.05)
                    .sum()
                ),
            )
        )
        print(name, "cells", len(frame), "patches", len(patches), flush=True)
        print(table.to_string(index=False), flush=True)
    write_text_atomic(
        OUTPUT / "cohort_comparison.csv", pd.DataFrame(overviews).to_csv(index=False)
    )
    write_json_atomic(
        OUTPUT / "manifest.json",
        dict(
            design=DESIGN,
            input_sha256=inputs,
            code_sha256=sha(Path(__file__)),
            reference_expansion_sha256=sha(SOURCE / "expansion_provenance.json"),
            output_sha256={
                str(p.relative_to(OUTPUT)): sha(p)
                for p in sorted(OUTPUT.rglob("*.csv"))
            },
            independently_validated_references=False,
        ),
    )
    print(pd.DataFrame(overviews).to_string(index=False), flush=True)


if __name__ == "__main__":
    run()
