"""Editable human report source using current saved researcher-category results."""

import json
import re
from common import BASE


def main():
    figures = json.loads((BASE / "figure_manifest.json").read_text())
    s1 = json.loads((BASE / "supplementary_figure_manifest.json").read_text())
    numbers = json.loads((BASE / "report_numbers.json").read_text())
    acc = numbers["classification"]
    s = numbers["synthetic_scores"]

    def rmse(kind, method, rep="NEON"):
        return s["|".join([kind, method, rep])]

    titles = [
        "Whole-spectrum differences and recognition answer different questions",
        "Where do the matched spectral differences occur?",
        "Which individual wavelengths predict held-out categories?",
        "A large group difference can still be a weak predictor",
        "Which classes can one spectral coordinate recognize?",
        "Separate spectral magnitude from site and year stability",
        "Complementary information accumulates over many coordinates",
        "Synthetic OLI preserves tests better than predictive accuracy",
        "Supervised models improve known synthetic fraction recovery",
        "Fraction errors depend on both class and true abundance",
        "Fewer false detections can mean more missed low fractions",
        "Lower fraction error does not remove spectral ambiguity",
        "Abundance transfer depends on the target domain",
        "The final evidence is conditional, with a field-truth gate",
    ]
    findings = [
        "All forty eligible researcher-category whole-spectrum comparisons were supported in the prior matched NPC analysis. Magnitudes differ. In the new full-spectrum tests, mean held-site recall is 94.2% for Evergreen and 91.7% for Non-vegetated & dead, versus46.3% for Woody shrub.",
        "Strong differences occupy broad regions rather than isolated independent channels. Training-only corrected support is shown across eight overlapping outer-training designs; these are not independent replications. The signed mean can conceal reversals; consult individual site/year effects and sign consistency in the atlas.",
        "Evergreen/Herbaceous and several contrasts involving Non-vegetated & dead have stronger single-coordinate signals. Herbaceous/Woody shrub remains below chance at its best observed worst-site coordinate under this mean-based rule.",
        "These four selected pairs compare two distinct quantities: adjusted curve magnitude and held-site prediction. Effect height is not accuracy. Near-infrared and shortwave-infrared information helps some pairs, while the difficult Herbaceous/Woody shrub contrast lacks a robust single-coordinate rule.",
        "A coordinate that helps a two-class comparison need not distinguish all five classes at once. Mean-based class centers can crowd together. Full-spectrum logistic recognition is a separate, stronger model; these are not its wavelength importances.",
        "Some regions retain sign and predictive performance across sites; others are geographically specific or change between the paired image years. The score rewards the weakest observed site, so averaging cannot hide a failed domain.",
        f"New-polygon balanced accuracy rises from {acc['plant_1']:.1%} at one complementary coordinate to {acc['plant_20']:.1%} at twenty and {acc['plant_360']:.1%} for the full grid. Held-site values are {acc['site_20']:.1%} and {acc['site_360']:.1%}. The inner-only parsimony rule chooses50-100 coordinates across these folds.",
        f"All forty researcher contrasts retain statistical support in OLI. Yet full-spectrum new-polygon/held-site accuracy changes from {acc['plant_360']:.1%}/{acc['site_360']:.1%} for NEON to {acc['plant_OLI']:.1%}/{acc['site_OLI']:.1%} for synthetic OLI. Support retention is not preservation of all predictive information.",
        f"NEON ridge fraction RMSE is {rmse('plant', 'Ridge'):.3f} for new-polygon parents and {rmse('site', 'Ridge'):.3f} for held sites, versus MESMA {rmse('plant', 'MESMA'):.3f}/{rmse('site', 'MESMA'):.3f}. The no-spectrum training-prior control is0.309: ridge beats it for new-parent/held-site targets, but not on average in the global-year tests. Flexible trees do not outperform ridge in the principal mean.",
        "Models can shrink extremes, assign nonzero fractions to absent classes and differ substantially among researcher categories. Overall RMSE hides these patterns. The common projection enforces physical fraction constraints but cannot certify the biological interpretation.",
        "For Evergreen in new-parent tests, two-stage modeling reduces zero-fraction false detections relative to ridge, but increases low-fraction misses. Other classes show their own tradeoffs. A lower average fraction RMSE does not establish a reliable presence detector.",
        "Ridge improves average error in the high-ambiguity held-site stratum, but gains are not uniform: MESMA can perform better in a moderate stratum. A learned prior can improve expected error while another biological composition still fits almost as well.",
        "Held-site and year targets alter model performance. Ridge global-year mean RMSE is0.311, versus0.309 for the no-spectrum training prior. The complete-pair NIWO design tests the same unseen IDs/fractions in both years, using other identities for fitting. Global year holds additionally change site composition; those columns are not a clean causal temporal effect.",
        "Researcher-category recognition and controlled synthetic fraction recovery are useful, with clear domain limits. Supervised regression improves the latter. Unique physical inversion and operational fractional cover remain unestablished without independent purity and complete field fractions.",
    ]
    limits = [
        "These are observational cover labels, not randomized traits or pure-material guarantees. Full-cohort matched effects and nested prediction use different populations/weighting.",
        "Full-cohort evidence and training-only evidence are separate. Max-T and within-design Bonferroni control the declared training family. Neither inference map selects predictive features. Null support is not an effect confidence interval.",
        "LDA learns means, direction and midpoint threshold on training IDs only. It estimates one rule, not an upper bound on all nonlinear single-coordinate information. Outer peaks are descriptive, not selected deployment bands.",
        "Illustrations are selected for interpretation, not another testing family. All ten pairs are available in the full map. Spectral association does not uniquely identify a biochemical cause.",
        "Five-class nearest-mean recall differs from pairwise balanced accuracy. Class sizes differ; every identity, including its repeated years, stays together in train/test splitting.",
        "Only three sites and two incompletely crossed years are available. Labels dated2023/2024 are reused across image years. These are retrospective footprints, not independently verified annual individuals.",
        "Selectors and regularization refit inside each inner identity fold. The greedy residual path is not a globally optimal sensor. Correlation alone does not establish conditional predictive redundancy.",
        "OLI is derived from the same NEON spectra at native/polygon support. It is neither independent Landsat validation nor30m spatial aggregation. MicaSense is excluded because physical coordinates remain unresolved.",
        "Each experiment uses120 proper and40 tuning parents, with up to60 test parents. All methods share targets. Synthetic rows within a parent bundle are dependent; field abundance is not measured.",
        "Known fractions are algebraic source weights, not independent physical cover. Curves average folds on the stated synthetic prior. Every saved fraction is nonnegative and sums to one after projection.",
        "The .10 fraction cutoff is a stated comparison rule, not a universal detection limit. Parent-bundle dependence limits uncertainty; source class truth does not certify pure endmembers.",
        "Ambiguity is candidate-library- and tolerance-dependent. Strata use the same NEON diagnostic for all methods. Missing strata are unsupported, and near ranges are not calibrated confidence intervals.",
        "Paired abundance is a fixed identity split, not the three-fold single-wavelength temporal experiment. Interval estimates condition on observed parent bundles; they do not cover new geographic populations.",
        "The lowest observed outer score is a descriptive comparison, not test-set hyperparameter tuning or a multiplicity-corrected winner. No current result is promoted to field abundance validation.",
    ]
    for i, f in enumerate(figures):
        f.update(
            title=titles[i], finding=findings[i], limit=limits[i], read=f["caption"]
        )
    s1.update(
        title="Which researcher categories are confused?",
        read=s1["caption"],
        finding="Evergreen and the broad background category transfer better than Woody shrub. Off-diagonal cells identify the alternatives receiving mistakes. The year panels preserve the prior researcher-only model and clearly label that reuse.",
        limit="Rows are normalized within each fold, then averaged. The new polygon/site model uses identity weighting; historical year panels use the validated earlier annual-row model. Do not interpret these as identical fitted pipelines.",
    )
    for item in figures + [s1]:
        for key in ["read", "finding", "limit"]:
            item[key] = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z])", " ", item[key])
    ordered = figures[:8] + [s1] + figures[8:]
    source = {
        "title": "Researcher cover categories: spectral information and synthetic abundance",
        "date": "15 October 2026",
        "figures": ordered,
        "counts": numbers["counts"],
        "main_finding": f"Supervised regression improves known synthetic fraction recovery: NEON ridge {rmse('plant', 'Ridge'):.3f} versus MESMA {rmse('plant', 'MESMA'):.3f} on new-parent tests, and {rmse('site', 'Ridge'):.3f} versus {rmse('site', 'MESMA'):.3f} on held sites. These gains do not establish unique inversion or field-cover accuracy.",
    }
    (BASE / "report_source.json").write_text(json.dumps(source, indent=2) + "\n")
    print("Created editable researcher-only report source with15 figure stories.")


if __name__ == "__main__":
    main()
