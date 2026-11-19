"""Run HLS L30 PFT tests without treating pixels as independent patches.

Primary: >=95% nominal and conservative source-support cover. Nominal-only is
retained as a separate sensitivity. Unavailable held-class support remains NA.
Neither original C2 data nor prior tests are overwritten.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from landsat_exploratory_pft_tests import (
    BANDS,
    CATEGORIES,
    prepare,
    separability,
    identify,
    summarize,
)
from landsat_spatial_expansion import OUTPUT as REFERENCES, sha
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

SOURCE = REFERENCES / "hls-l30-rebuild"
OUTPUT = REFERENCES / "hls-l30-pft-tests"


def validate(frame, strict):
    if frame.candidate_id.duplicated().any():
        raise ValueError("Duplicate physical HLS cells")
    if not frame.brdf_normalized.all() or not frame.hls_collection.eq("hls2-l30").all():
        raise ValueError("Expected BRDF-normalized HLS L30 observations")
    if frame.pft_purity_verified.any():
        raise ValueError("Reference verification is still provisional")
    if not np.isfinite(frame[BANDS]).all().all():
        raise ValueError("Incomplete HLS spectral support")
    if not (
        frame.nominal_95pct
        & frame.core_qa_clear
        & frame.context_150m_clear
        & frame.photo_date_match
        & frame.aerosol_level.lt(3)
    ).all():
        raise ValueError("HLS reference/QA contract failed")
    if strict and not frame.strict_support_95pct.all():
        raise ValueError("Primary HLS cohort must pass source support")
    if frame.groupby("patch_group_id").researcher_category.nunique().gt(1).any():
        raise ValueError("Mixed-category patches need another permutation design")


def table_summary(pairs, predictions):
    """Keep unavailable tests/held-class predictions out of claimed estimates."""
    pooled = pairs.loc[pairs.scope.eq("pooled_patches_region_confounded")]
    held = predictions.loc[
        predictions.unit.eq("patch") & predictions.scheme.eq("leave_one_patch_out")
    ]
    rows = []
    for category in CATEGORIES:
        comparisons = pooled.loc[pooled.a.eq(category) | pooled.b.eq(category)]
        tests = comparisons.loc[comparisons.p_npc.notna()]
        target = held.loc[held.truth.eq(category)]
        supported = target.loc[target.truth_in_training]
        correct = int(supported.truth.eq(supported.prediction).sum())
        available = len(supported) > 0 and len(supported) == len(target)
        rows.append(
            dict(
                researcher_category=category,
                planned_pairs=len(comparisons),
                tested_pairs=len(tests),
                supported_pairs=int(tests.p_npc_holm.le(0.05).sum()),
                separability_status="available"
                if len(tests)
                else "insufficient_patches",
                held_patches=len(target),
                supported_test_patches=len(supported),
                correct_supported_patches=correct,
                held_patch_recall=correct / len(supported) if available else np.nan,
                identifiability_status="available"
                if available
                else "class_absent_from_training",
                reference_status="provisional",
            )
        )
    return pd.DataFrame(rows)


def run():
    OUTPUT.mkdir(exist_ok=True)
    overview = []
    inputs = {}
    for name, filename, strict in [
        (
            "strict_source_support",
            "hls_l30_strict_source_support_95pct_observations.csv",
            True,
        ),
        (
            "nominal_support_sensitivity",
            "hls_l30_nominal_95pct_observations.csv",
            False,
        ),
    ]:
        path = SOURCE / filename
        inputs[filename] = sha(path)
        frame = pd.read_csv(path)
        validate(frame, strict)
        cells, patches = prepare(frame, BANDS, normalize=False)
        print(
            name, len(cells), "HLS cells;", len(patches), "spatial groups", flush=True
        )
        pairs = separability(patches, BANDS)
        predictions = identify(cells, patches, BANDS)
        class_summary = summarize(predictions)
        table = table_summary(pairs, predictions)
        dest = OUTPUT / name
        dest.mkdir(exist_ok=True)
        for filename, data in [
            ("patch_median_reflectance.csv", patches),
            ("separability.csv", pairs),
            ("held_out_predictions.csv", predictions),
            ("identifiability_summary.csv", class_summary),
            ("figure_table_summary.csv", table),
        ]:
            write_text_atomic(dest / filename, data.to_csv(index=False))
        held = predictions.loc[
            predictions.unit.eq("patch") & predictions.scheme.eq("leave_one_patch_out")
        ]
        eligible = held.loc[held.truth_in_training]
        # A five-class overall score would disguise classes absent from training.
        all_supported = bool(held.truth_in_training.all())
        overview.append(
            dict(
                cohort=name,
                cells=len(frame),
                patch_groups=len(patches),
                tested_pooled_pairs=int(
                    pairs.loc[pairs.scope.str.startswith("pooled")].p_npc.notna().sum()
                ),
                supported_pooled_pairs=int(
                    pairs.loc[pairs.scope.str.startswith("pooled")]
                    .p_npc_holm.le(0.05)
                    .sum()
                ),
                supported_test_patches=len(eligible),
                unsupported_test_patches=len(held) - len(eligible),
                correct_supported_patches=int(
                    eligible.truth.eq(eligible.prediction).sum()
                ),
                conditional_supported_patch_accuracy=float(
                    eligible.truth.eq(eligible.prediction).mean()
                ),
                five_class_patch_accuracy=float(held.truth.eq(held.prediction).mean())
                if all_supported
                else np.nan,
            )
        )
        print(table.to_string(index=False), flush=True)
    write_text_atomic(
        OUTPUT / "cohort_comparison.csv", pd.DataFrame(overview).to_csv(index=False)
    )
    write_json_atomic(
        OUTPUT / "manifest.json",
        dict(
            input_sha256=inputs,
            code_sha256=sha(Path(__file__)),
            reused_statistics_code_sha256=sha(
                Path(__file__).with_name("landsat_exploratory_pft_tests.py")
            ),
            npc_code_sha256=sha(
                Path(__file__).with_name("landsat_photo_annotation.py")
            ),
            primary="strict_source_support",
            normalization="none; stored direct HLS NBAR reflectance",
            multiplicity="Holm across all ten planned pairs separately per cohort/scope; unavailable pairs enter as p=1",
            classifier="training-only StandardScaler + balanced logistic regression C=1; equally weighted patch medians",
            labels_independently_validated=False,
            output_sha256={
                str(p.relative_to(OUTPUT)): sha(p)
                for p in sorted(OUTPUT.rglob("*.csv"))
            },
        ),
    )
    print(pd.DataFrame(overview).to_string(index=False), flush=True)


if __name__ == "__main__":
    run()
