"""Readable report and diagnostic figure from compact completed mask-PFT outputs."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from compare_drone_mask_pft_information import CATEGORIES, REPORT
from drone_shade_mask_preview import file_sha256


def run():
    manifest = json.loads((REPORT / "manifest.json").read_text())
    for name, digest in manifest["outputs"].items():
        assert file_sha256(REPORT / name) == digest
    accuracy = pd.read_csv(REPORT / "identifiability_change.csv")
    separability = pd.read_csv(REPORT / "separability.csv")
    changes = pd.read_csv(REPORT / "separability_change.csv")
    classes = pd.read_csv(REPORT / "class_summary.csv")
    coverage = pd.read_csv(REPORT / "polygon_coverage.csv")
    predictions = pd.read_csv(REPORT / "held_out_predictions.csv")
    a = accuracy[accuracy.target == "Landsat_9_OLI-2"].copy()
    d = changes[
        (changes.target == "Landsat_9_OLI-2") & (changes.population == "shared_pixels")
    ]
    c = classes[
        (classes.target == "Landsat_9_OLI-2") & (classes.population == "shared_pixels")
    ]
    v = coverage[coverage.target == "Landsat_9_OLI-2"]
    site_rows = []
    for keys, group in predictions.groupby(
        ["target", "population", "scheme", "arm", "site"]
    ):
        recall = (
            group.assign(correct=group.truth == group.prediction)
            .groupby("truth")
            .correct.mean()
        )
        site_rows.append(
            dict(
                zip(
                    ["target", "population", "scheme", "arm", "site"], keys, strict=True
                ),
                n_polygons=len(group),
                represented_classes=len(recall),
                balanced_accuracy=float(recall.mean()),
            )
        )
    pd.DataFrame(site_rows).to_csv(REPORT / "site_specific_accuracy.csv", index=False)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, (left, right) = plt.subplots(
        1, 2, figsize=(13, 5.7), gridspec_kw={"width_ratios": [1, 1.25]}
    )
    colors = ["#263e56", "#237d83"]
    yy = np.arange(len(a))
    offset = 0.16
    for values, shift, label, color in [
        (a.ba_null, -offset, "Unmasked null", colors[0]),
        (a.ba_mask10, offset, "10% mask", colors[1]),
    ]:
        left.barh(yy + shift, values * 100, height=0.3, color=color, label=label)
        for y, value in zip(yy + shift, values, strict=True):
            left.text(value * 100 + 1, y, f"{value:.1%}", va="center", fontsize=9)
    left.set_yticks(
        yy,
        [
            f"{'Held-site' if r.scheme == 'held_out_site' else 'Held-polygon'}\n{'Shared pixels' if r.population == 'shared_pixels' else 'Each arm retained pixels'}"
            for r in a.itertuples()
        ],
    )
    left.invert_yaxis()
    left.set_xlim(0, 80)
    left.set_xlabel("Balanced accuracy (%)")
    left.set_title("Identifiability: matched polygon cohorts")
    handles, labels = left.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.93),
        ncol=2,
        frameon=False,
    )
    yy = np.arange(len(d))
    for i, row in enumerate(d.itertuples()):
        right.plot([row.effect_null, row.effect_mask10], [i, i], color="#b8c2c8", lw=1)
    right.scatter(
        d.effect_null, yy, color=colors[0], s=35, label="Unmasked null", zorder=3
    )
    right.scatter(
        d.effect_mask10, yy, color=colors[1], s=35, label="10% mask", zorder=3
    )
    short = {
        "Deciduous": "Deciduous",
        "Evergreen": "Evergreen",
        "Herbaceous": "Herbaceous",
        "Woody shrub": "Shrub",
        "Non-vegetated & dead": "Non-veg/dead",
    }
    right.set_yticks(
        yy, [short[r.first] + " / " + short[r.second] for r in d.itertuples()]
    )
    right.invert_yaxis()
    right.set_xlabel("Site-adjusted standardized RMS PFT contrast")
    right.set_title("Separability effect sizes: shared pixels")
    fig.suptitle(
        "Translated OLI-2-like spectra: unmasked versus 10% shade mask",
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.015,
        "300 polygons • 3 sites • five physical-reflectance bands • point estimates; not independent field validation",
        ha="center",
        fontsize=9,
        color="#66747e",
    )
    fig.tight_layout(rect=[0, 0.04, 1, 0.94])
    fig.savefig(REPORT / "mask_pft_comparison.png", dpi=180)
    fig.savefig(REPORT / "mask_pft_comparison.pdf")
    plt.close(fig)
    lines = [
        "# Translated PFT information: unmasked null versus 10% mask",
        "",
        "The results do not show a consistent loss of PFT information after masking. Effects are mixed; three calibration sites provide limited independent replication.",
        "",
        "## Identifiability",
        "",
        "| Pixel population | Evaluation | Unmasked BA | 10% BA | Change (percentage points) |",
        "|---|---|---:|---:|---:|",
    ]
    for row in a.itertuples():
        lines.append(
            f"| {row.population} | {row.scheme} | {row.ba_null:.1%} | {row.ba_mask10:.1%} | {row.delta_ba * 100:+.2f} |"
        )
    lines += [
        "",
        "Balanced accuracy is the mean of five class recalls from pooled out-of-fold predictions, not overall accuracy or an equal-site average. All 300 polygons are evaluated once per scheme and arm; every test class is present in training. OLI-like results match OLI-2-like results to the displayed precision.",
        "",
        "No paired identifiability loss survives Holm adjustment across the eight prespecified comparisons. Site-level arm-swap tests have only eight possible assignments with three sites, so a one-sided p-value cannot be smaller than0.125. A nonsignificant result does not establish equivalence. Polygon-level swaps additionally assume exchangeability of polygon contributions and remain exploratory because nearby polygons and overlapping training folds can induce dependence.",
        "",
        "## Separability",
        "",
    ]
    for population in ["shared_pixels", "retained_pixels"]:
        q = separability[
            (separability.target == "Landsat_9_OLI-2")
            & (separability.population == population)
        ]
        counts = {
            arm: (
                (q[q.arm == arm].p_holm_within10 <= 0.05).sum(),
                (q[q.arm == arm].p_holm_all80 <= 0.05).sum(),
            )
            for arm in ["unmasked", "mask10"]
        }
        lines.append(
            f"- {population}: per-arm ten-pair Holm supports {counts['unmasked'][0]}/10 unmasked versus {counts['mask10'][0]}/10 masked; joint80-contrast Holm supports {counts['unmasked'][1]}/10 versus {counts['mask10'][1]}/10."
        )
    lines += [
        "",
        f"On shared pixels, standardized contrasts decrease for {int((d.effect_delta < 0).sum())}/10 pairs and increase for {int((d.effect_delta > 0).sum())}/10. Decreases occur for Deciduous/Evergreen, Evergreen/Herbaceous and Evergreen/Woody shrub. No directional effect-loss test survives Holm across the40 prespecified pair comparisons (smallest polygon-swap adjusted p approximately0.052). Counts of significant category differences are not themselves a test of whether masking changes separation.",
        "",
        "## Class recalls: shared pixels, OLI-2-like",
        "",
        "| PFT | n | Held-polygon unmasked | Held-polygon10% | Held-site unmasked | Held-site10% |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for category in CATEGORIES:
        x = c[(c.category == category) & (c.arm == "unmasked")].iloc[0]
        y = c[(c.category == category) & (c.arm == "mask10")].iloc[0]
        lines.append(
            f"| {category} | {x.n_polygons} | {x.unseen_polygon_recall:.1%} | {y.unseen_polygon_recall:.1%} | {x.held_out_site_recall:.1%} | {y.held_out_site_recall:.1%} |"
        )
    lines += [
        "",
        "Woody-shrub held-site recall is0% in both arms. Thus overall recognition remains limited even where masking improves the mean score.",
        "",
        "## Cohort, coverage and design",
        "",
        f"Original302 polygon footprints contain {int(v.source_pixels.sum()):,} indexed pixels. Two polygons have zero complete five-band valid pixels in both arms; neither is a mask-only dropout. The matched cohort is300 polygons: Deciduous12, Evergreen176, Herbaceous46, Woody shrub40, Non-vegetated/dead26. There are no overlapping indexed polygon pixels.",
        "",
        f"Complete five-band labelled pixels: unmasked {int(v.null_pixels.sum()):,}; mask10 {int(v.mask10_pixels.sum()):,}; shared {int(v.common_pixels.sum()):,}. These counts concern labelled footprints, not the whole scene. Both analyses keep the same polygon IDs. Shared-pixel medians use identical exact row/column sets. Retained-pixel medians use each arm's available pixels.",
        "",
        "PFT annotations are the original calibration polygon labels. Spectra are polygon medians in fractional physical-reflectance units, without sum normalization. Separability uses the existing site-blocked whole-polygon label NPC kernel with9,999 synchronized draws, equal discrete band weights, ten-pair local Holm and joint80-contrast Holm. Effect change uses site-adjusted RMS standardized coefficients with paired whole-polygon arm swaps, plus exact whole-site swaps.",
        "",
        "Classification uses training-only StandardScaler and balanced logistic regression, C=1, with fixed five stratified polygon folds and three leave-site-out folds. Fold memberships are identical between arms. There is no feature selection or hyperparameter tuning on test data. Correction models are fit separately for each site; held-site evaluation refers to classifier transfer after site-specific correction, not an entirely frozen correction pipeline applied to an unseen site.",
        "",
        "The contrast includes changes in fitted SCS+C and BRDF parameters, and in the retained-pixel analysis also changes in pixel composition. It is not a mask-only causal experiment. Ruby's unmasked reference remains failed BRDF QA; all products retain conditional, unverified radiometry. Same-site spatial dependence, three-site scope and lack of independent external reflectance validation limit generalization. Figure4 and uploaded datasets were not changed.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python examples/compare_drone_mask_pft_information.py",
        "MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/summarize_drone_mask_pft_information.py",
        "```",
        "",
        "`analysis_policy.json` was frozen before test results. `manifest.json` records input/label/code and output hashes and software versions. Completed analytical outputs are reused only after hash checks. The internal null arm is serialized as `unmasked` so CSV readers do not treat it as missing. Full polygon spectra/coverage, folds, predictions, per-class results, effect/p-value tables and site-specific scores accompany this report.",
    ]
    (REPORT / "README.md").write_text("\n".join(lines) + "\n")
    (REPORT / "summary_manifest.json").write_text(
        json.dumps(
            dict(
                code_sha256=file_sha256(Path(__file__)),
                outputs={
                    name: file_sha256(REPORT / name)
                    for name in [
                        "README.md",
                        "mask_pft_comparison.png",
                        "mask_pft_comparison.pdf",
                        "site_specific_accuracy.csv",
                    ]
                },
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    run()
