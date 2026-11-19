"""Exploratory five-PFT tests with provisional Landsat references.

Run from repository root. No primary reference labels or Figure 4 are changed.
Exact NPC tests use patch medians and whole-patch labels. Identification holds
out entire patches and fits scaling/model only to training patch medians.
"""

from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from math import comb
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from landsat_photo_annotation import exact_statistics
from landsat_spatial_expansion import OUTPUT as REFERENCES, sha
from spectralbridge.plant_pft_statistics import holm
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

OUTPUT = REFERENCES / "exploratory-five-pft-tests"
BANDS = [f"B{i}" for i in range(1, 8)]
CATEGORIES = [
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "Non-vegetated & dead",
]


def load_cohort():
    photo = REFERENCES / "expanded_photo_screened_landsat_dataset.csv"
    evergreen = (
        REFERENCES
        / "evergreen-pointcloud/landsat_evergreen_structural_candidate_observations.csv"
    )
    a, b = pd.read_csv(photo), pd.read_csv(evergreen)
    a["reference_basis"] = "dated_photo_cover"
    b["reference_basis"] = "older_lidar_structure_and_provisional_evergreen_identity"
    b["patch_group_id"] = "evergreen-" + b.context_patch_id
    # The evergreen groups are pre-existing nonoverlapping 240 m patches.
    groups = b.groupby("patch_group_id")[["easting", "northing"]].mean().to_numpy()
    for i, j in combinations(range(len(groups)), 2):
        if np.max(np.abs(groups[i] - groups[j])) <= 240:
            raise ValueError("Evergreen patches overlap: merge groups before testing")
    a["shift_5m_screen"] = a.shift_5m_min_target_fraction.ge(0.95)
    b["shift_5m_screen"] = b.shift_5m_min_above_5m_fraction.ge(0.95)
    frame = pd.concat([a, b], ignore_index=True)
    if frame.candidate_id.duplicated().any() or frame.pft_purity_verified.any():
        raise ValueError(
            "Require distinct physical cells with explicit provisional labels"
        )
    if not np.isfinite(frame[BANDS]).all().all():
        raise ValueError("Incomplete bands")
    if not (
        frame.grid_match
        & frame.core_qa_clear
        & frame.context_150m_clear
        & frame.photo_date_match
        & frame.aerosol_level.lt(3)
    ).all():
        raise ValueError("Input QA failed")
    if frame.groupby("patch_group_id").researcher_category.nunique().max() != 1:
        raise ValueError("Mixed-label patch groups need explicit multi-class blocking")
    return frame, dict(photo=sha(photo), evergreen=sha(evergreen))


def prepare(frame, bands, normalize=True):
    """Normalize each cell before aggregation, as in the descriptive figure."""
    frame = frame.copy()
    if normalize:
        denominator = frame[BANDS[:5]].sum(axis=1)
        if (denominator <= 0).any():
            raise ValueError("Nonpositive normalization sum")
        frame[BANDS] = frame[BANDS].div(denominator, axis=0)
    patches = frame.groupby(
        ["patch_group_id", "researcher_category", "region"], as_index=False
    )[bands].median()
    return frame, patches


def separability(patches, bands):
    """Pooled inference is conditional on strong patch exchangeability.

    Region-restricted tests omit regions lacking both classes; lack of mixed
    support is an unavailable test, never a negative or positive result.
    """
    records = []
    for scope in ["pooled_patches_region_confounded", "within_region_mixed_support"]:
        for a, b in combinations(CATEGORIES, 2):
            pair = patches.loc[patches.researcher_category.isin([a, b])].copy()
            if scope.startswith("within"):
                mixed = pair.groupby("region").researcher_category.nunique()
                pair = pair.loc[pair.region.isin(mixed.index[mixed.eq(2)])]
                blocks = pair.region.to_numpy()
            else:
                blocks = np.zeros(len(pair), int)
            counts = pair.researcher_category.value_counts()
            rec = dict(
                scope=scope,
                a=a,
                b=b,
                n_patch_a=int(counts.get(a, 0)),
                n_patch_b=int(counts.get(b, 0)),
                regions=int(pair.region.nunique()),
                p_npc=np.nan,
                status="insufficient_matched_patch_support",
            )
            if min(rec["n_patch_a"], rec["n_patch_b"]) >= 2:
                rec.update(
                    exact_statistics(
                        pair[bands], pair.researcher_category.eq(a).astype(int), blocks
                    )
                )
                rec["status"] = "exploratory_provisional_references"
            if (
                scope.startswith("pooled")
                and min(rec["n_patch_a"], rec["n_patch_b"]) >= 2
            ):
                n_a, n_b = rec["n_patch_a"], rec["n_patch_b"]
                rec["best_case_two_sided_p_lower_bound"] = (
                    2 if n_a == n_b else 1
                ) / comb(n_a + n_b, n_a)
            records.append(rec)
    result = pd.DataFrame(records)
    result["p_npc_holm"] = np.nan
    for scope, group in result.groupby("scope"):
        # Preserve all ten planned comparisons in each correction family.
        adjusted = holm(group.p_npc.fillna(1).to_numpy())
        result.loc[group.index, "p_npc_holm"] = np.where(
            group.p_npc.notna(), adjusted, np.nan
        )
    return result


def identify(frame, patches, bands):
    """Training units are equally weighted patch medians; no pixel leakage."""
    records = []
    for scheme in ["leave_one_patch_out", "leave_one_region_out"]:
        key = "patch_group_id" if scheme == "leave_one_patch_out" else "region"
        for held in sorted(patches[key].unique()):
            train = patches.loc[patches[key].ne(held)]
            test = patches.loc[patches[key].eq(held)]
            if train.researcher_category.nunique() < 2:
                continue
            model = make_pipeline(
                StandardScaler(),
                LogisticRegression(C=1, class_weight="balanced", max_iter=2000),
            )
            model.fit(train[bands], train.researcher_category)
            for unit, table in [
                ("patch", test),
                ("pixel", frame.loc[frame[key].eq(held)]),
            ]:
                predictions = model.predict(table[bands])
                for (_, row), prediction in zip(
                    table.iterrows(), predictions, strict=True
                ):
                    records.append(
                        dict(
                            scheme=scheme,
                            held_out=str(held),
                            unit=unit,
                            candidate_id=row.get("candidate_id", ""),
                            patch_group_id=row.patch_group_id,
                            region=row.region,
                            truth=row.researcher_category,
                            prediction=prediction,
                            truth_in_training=row.researcher_category
                            in set(train.researcher_category),
                            train_patch_count=len(train),
                            training_classes=";".join(
                                sorted(train.researcher_category.unique())
                            ),
                        )
                    )
    return pd.DataFrame(records)


def geography_baseline(patches):
    """Leave-patch-out majority class from the same region, without spectra."""
    rows = []
    for _, test in patches.iterrows():
        train = patches.loc[patches.patch_group_id.ne(test.patch_group_id)]
        local = train.loc[train.region.eq(test.region)]
        counts = (local if len(local) else train).researcher_category.value_counts()
        prediction = sorted(counts.index[counts.eq(counts.max())])[0]
        rows.append(
            dict(
                patch_group_id=test.patch_group_id,
                truth=test.researcher_category,
                prediction=prediction,
                region=test.region,
            )
        )
    return pd.DataFrame(rows)


def summarize(predictions):
    rows = []
    for (scheme, unit, category), g in predictions.groupby(["scheme", "unit", "truth"]):
        supported = g.loc[g.truth_in_training]
        rows.append(
            dict(
                scheme=scheme,
                unit=unit,
                researcher_category=category,
                n=len(g),
                supported_n=len(supported),
                recall_all=float(g.truth.eq(g.prediction).mean()),
                recall_supported=float(supported.truth.eq(supported.prediction).mean())
                if len(supported)
                else np.nan,
                status="conditional_on_training_class_presence"
                if len(supported) != len(g)
                else "exploratory_provisional_references",
            )
        )
    return pd.DataFrame(rows)


def run():
    OUTPUT.mkdir(exist_ok=True)
    frame, inputs = load_cohort()
    write_text_atomic(
        OUTPUT / "combined_provisional_cohort.csv", frame.to_csv(index=False)
    )
    variants = {
        "primary_normalized_seven_bands": (frame, BANDS, True),
        "registration_5m_normalized_seven_bands": (
            frame.loc[frame.shift_5m_screen],
            BANDS,
            True,
        ),
        "preferred_aerosol_normalized_seven_bands": (
            frame.loc[frame.preferred_aerosol],
            BANDS,
            True,
        ),
        "shared_five_bands_normalized": (frame, BANDS[:5], True),
        "raw_seven_bands_sensitivity": (frame, BANDS, False),
    }
    overview = []
    for name, (subset, bands, normalize) in variants.items():
        print(name, len(subset), "cells", flush=True)
        dest = OUTPUT / name
        dest.mkdir(exist_ok=True)
        cells, patches = prepare(subset, bands, normalize)
        pairs = separability(patches, bands)
        predictions = identify(cells, patches, bands)
        summary = summarize(predictions)
        baseline = geography_baseline(patches)
        write_text_atomic(
            dest / "geography_only_baseline.csv", baseline.to_csv(index=False)
        )
        held_patch = predictions.loc[
            predictions.unit.eq("patch") & predictions.scheme.eq("leave_one_patch_out")
        ]
        write_text_atomic(
            dest / "patch_confusion_matrix.csv",
            pd.crosstab(held_patch.truth, held_patch.prediction)
            .reindex(index=CATEGORIES, columns=CATEGORIES, fill_value=0)
            .to_csv(),
        )
        for filename, table in [
            ("patch_median_spectra.csv", patches),
            ("separability.csv", pairs),
            ("identifiability_predictions.csv", predictions),
            ("identifiability_summary.csv", summary),
        ]:
            write_text_atomic(dest / filename, table.to_csv(index=False))
        for scheme, g in predictions.loc[predictions.unit.eq("patch")].groupby(
            "scheme"
        ):
            supported = g.loc[g.truth_in_training]
            overview.append(
                dict(
                    variant=name,
                    scheme=scheme,
                    cells=len(subset),
                    patches=len(patches),
                    patch_accuracy=float(g.truth.eq(g.prediction).mean()),
                    patch_macro_recall=float(
                        g.assign(correct=g.truth.eq(g.prediction))
                        .groupby("truth")
                        .correct.mean()
                        .mean()
                    ),
                    supported_patch_accuracy=float(
                        supported.truth.eq(supported.prediction).mean()
                    ),
                    unsupported_test_patches=int((~g.truth_in_training).sum()),
                )
            )
    write_text_atomic(
        OUTPUT / "analysis_overview.csv", pd.DataFrame(overview).to_csv(index=False)
    )
    write_json_atomic(
        OUTPUT / "manifest.json",
        dict(
            input_sha256=inputs,
            code_sha256=sha(Path(__file__)),
            exact_statistic_code_sha256=sha(
                Path(__file__).with_name("landsat_photo_annotation.py")
            ),
            provisional_references=True,
            independently_validated_accuracy=False,
            normalization="per-cell shared B1-B5 sum before patch medians",
            model="StandardScaler + balanced logistic regression C=1; fit training patch medians only",
            multiplicity="Holm over all ten planned pairs separately per scope/variant",
            output_sha256={
                str(p.relative_to(OUTPUT)): sha(p)
                for p in sorted(OUTPUT.rglob("*.csv"))
            },
        ),
    )
    print(pd.DataFrame(overview).to_string(index=False), flush=True)
    report()


def report():
    primary = OUTPUT / "primary_normalized_seven_bands"
    predictions = pd.read_csv(primary / "identifiability_predictions.csv")
    pairs = pd.read_csv(primary / "separability.csv")
    cohort = pd.read_csv(OUTPUT / "combined_provisional_cohort.csv")
    patches = predictions.loc[
        predictions.unit.eq("patch") & predictions.scheme.eq("leave_one_patch_out")
    ]
    baseline = pd.read_csv(primary / "geography_only_baseline.csv")
    pooled = pairs.loc[pairs.scope.str.startswith("pooled")]
    matched = pairs.loc[pairs.scope.str.startswith("within")]
    lines = [
        "# Exploratory Landsat separability and identifiability",
        "",
        "Provisional five-class analysis, 19 November 2026. Neither independently validated accuracy nor a change to Figure 4.",
        "",
        f"Combined cohort: {len(cohort)} unique 30 m cells, {cohort.patch_group_id.nunique()} spatial patch groups, {cohort.researcher_category.nunique()} PFT labels. Evergreen consists of {int(cohort.researcher_category.eq('Evergreen').sum())} structurally screened candidates with older lidar; the other {int(cohort.researcher_category.ne('Evergreen').sum())} are single-interpreter photo references.",
        "",
        "## Primary results",
        "",
        f"Leave-one-patch-out identification correctly predicts {int(patches.truth.eq(patches.prediction).sum())}/{len(patches)} patch medians ({patches.truth.eq(patches.prediction).mean():.0%}). Each patch is predicted once; all pixels from that patch are excluded from training. Models are trained on equally weighted patch medians, with balanced class weights. Pixel predictions are secondary descriptive outputs, not extra independent test replicates.",
        "",
        "| PFT | Correct held-out patches | Recall |",
        "| --- | ---: | ---: |",
    ]
    for category in CATEGORIES:
        g = patches.loc[patches.truth.eq(category)]
        lines.append(
            f"| {category} | {int(g.truth.eq(g.prediction).sum())}/{len(g)} | {g.truth.eq(g.prediction).mean():.0%} |"
        )
    lines += [
        "",
        f"The geography-only leave-patch-out majority baseline correctly predicts {int(baseline.truth.eq(baseline.prediction).sum())}/{len(baseline)} patches, without using spectra. Classes and geography are strongly associated.",
        "",
        f"Exact pooled NPC separability: {int(pooled.p_npc_holm.le(0.05).sum())}/10 contrasts supported after Holm correction. Adjusted p-values range from {pooled.p_npc_holm.min():.4f} to {pooled.p_npc_holm.max():.4f}. This is insufficient evidence for all-pair separability, not proof of spectral equivalence. With only 3–5 patches per class, the smallest attainable exact two-sided p-value across these pair designs exceeds the first Holm threshold of 0.005; adding adjacent pixels does not improve permutation resolution.",
        "",
        f"Within-region tests have mixed-class support for only {int(matched.p_npc.notna().sum())}/10 contrasts, and none passes correction. Those tests restrict permutations by region; they do not fully control acquisition date or scene. The pooled tests assume whole-patch exchangeability across regions/seasons, a strong and potentially invalid assumption.",
        "",
        "## Geographic transfer",
        "",
        "Deciduous, evergreen and shrub each occur in one region. Holding that region out removes the class from training entirely, so regional-transfer recall for those classes is unavailable. Zero predictions for an unseen training class are retained in the audit, but must not be described as an ordinary measured class-transfer accuracy. The raw overall leave-region-out score conflates unsupported classes and supported predictions; consult support flags rather than reporting its overall percentage as five-class transfer performance.",
        "",
        "## Sensitivity analyses",
        "",
        "Separate folders repeat the entire analysis for the 5 m registration screen, preferred aerosol retrieval only, shared B1–B5, and raw B1–B7 reflectance. These are diagnostics, not independent confirmations or a basis for selecting whichever result looks best. `analysis_overview.csv` reports the resulting patch counts and performance. Some restrictions remove whole patches; track the denominator.",
        "",
        "## Reproduce and interpret",
        "",
        "Run from repository root with the existing environment:",
        "",
        "```bash",
        ".venv/bin/python examples/publication_figures/landsat_exploratory_pft_tests.py",
        ".venv/bin/pytest -q tests/test_landsat_exploratory_pft_tests.py",
        "```",
        "",
        "Inputs are read in place from round-2 primary references and the evergreen candidate table. `manifest.json` records their hashes, code and output CSV checksums. `combined_provisional_cohort.csv` preserves both reference bases rather than relabeling structural occupancy as photo-cover purity. For normalized analyses, divide each pixel by its B1–B5 sum before taking patch medians. Exact synchronized max/integrated NPC statistics reuse the existing annotation helper, with equal band weights. Holm correction includes all ten planned pairs separately for each scope/variant. Identification uses StandardScaler and balanced logistic regression (C=1), fitted only to training patch medians; no tuning on held-out data was performed.",
        "",
        "This is the same NPC statistic family used previously, but spatial patch units and the current cohort differ from archived NEON/drone protocols. Percentages should not be presented as directly comparable cross-sensor validation. Label source, season and geography are confounded; independent reference validation and more distinct matched-region patches remain necessary.",
        "",
    ]
    write_text_atomic(OUTPUT / "README.md", "\n".join(lines))


if __name__ == "__main__":
    run()
