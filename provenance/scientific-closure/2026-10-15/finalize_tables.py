"""Use-specific quantitative review table; no new scientific fits."""

from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
LEVELS = {
    "Recorded species discrimination": "species_level",
    "Researcher category discrimination": "researcher_level",
    "Narrow woody PFT discrimination": "narrow_pft",
    "Broad woody leaf habit discrimination": "broad_pft",
    "Coarse cover proxy discrimination": "coarse_cover",
}


def run():
    matrix = pd.read_csv(BASE / "tables/FINAL_READINESS_MATRIX.csv")
    scores = pd.read_csv(BASE / "tables/biological_generalization.csv")
    rates = pd.read_csv(BASE / "tables/all_class_detection_rates.csv")
    keys = ["scheme", "fold", "representation", "experiment", "mode"]
    info = scores.drop_duplicates(keys).set_index(keys)
    for i, row in rates.iterrows():
        context = tuple(row[k] for k in keys)
        rates.loc[i, "kind"] = info.loc[context, "kind"]
        rates.loc[i, "target_identities"] = info.loc[context, "test_identities"]
    rates.to_csv(BASE / "tables/all_class_detection_rates.csv", index=False)
    scores = scores[
        scores.probability.eq("raw")
        & scores.experiment.eq("hierarchy")
        & scores["mode"].eq("stored")
        & scores.representation.eq("NEON_full")
    ]
    coverage = pd.read_csv(BASE / "tables/closed_set_coverage.csv")
    for i, row in matrix.iterrows():
        if row["use"] not in LEVELS:
            continue
        level = LEVELS[row["use"]]
        plant = scores[scores.scheme.eq(level) & scores.kind.eq("plant")]
        site = scores[scores.scheme.eq(level) & scores.kind.eq("site")]
        cov = coverage[coverage.level.eq(level) & coverage.kind.eq("site")]
        matrix.loc[i, "mean_new_polygon_BA"] = plant.balanced_accuracy.mean()
        matrix.loc[i, "mean_held_site_BA"] = site.balanced_accuracy.mean()
        matrix.loc[i, "minimum_held_site_BA"] = site.balanced_accuracy.min()
        matrix.loc[i, "maximum_held_site_BA"] = site.balanced_accuracy.max()
        matrix.loc[i, "minimum_site_closed_set_coverage"] = (
            cov.closed_set_fraction.min()
        )
        matrix.loc[i, "uncertainty"] = (
            f"New-polygon per-fold conditional 95% BA interval endpoints span {plant.BA_lo.min():.3f}-{plant.BA_hi.max():.3f}; held-site endpoints span {site.BA_lo.min():.3f}-{site.BA_hi.max():.3f}; not an interval over new geographic populations"
        )
        matrix.loc[i, "major_limitation"] = (
            "Retrospective 2023/2024 source annotations on image-year footprints; different class populations/closed-set support; native 1 m polygon support; no novel-species or operational field-abundance guarantee"
        )
    paired = pd.read_csv(BASE / "tables/paired_temporal_recognition.csv")

    def score(level, year):
        g = paired[
            paired.scheme.eq(level)
            & paired.training_year.eq(2020)
            & paired.test_year.eq(year)
            & paired.representation.eq("NEON_full")
        ]
        return g.balanced_accuracy.mean()

    ix = matrix["use"].eq("Cross-year transfer")
    matrix.loc[ix, "quantitative_performance"] = (
        f"2020-trained same unseen NIWO targets: broad woody BA {score('broad_pft', 2020):.3f} to {score('broad_pft', 2023):.3f}; species {score('species_level', 2020):.3f} to {score('species_level', 2023):.3f}"
    )
    matrix.loc[ix, "major_limitation"] = (
        "Two NIWO image years; reused 2023/2024 annotations, not independently verified annual biological status; temporal ecology and acquisition conditions inseparable"
    )
    matrix.loc[ix, "recommended_use"] = (
        "retrospective recognition of labelled footprints in the supported repeated-panel domain"
    )
    unknown = pd.read_csv(
        REPO
        / "provenance/spectral-library-analytics/2026-10-14/tables/unknown_material_detection.csv"
    )
    chosen = unknown[
        unknown.status.eq("evaluated")
        & unknown.representation.eq("NEON_full")
        & unknown.scheme.eq("inferred_pft")
        & unknown.detector.eq("nearest_angle_deg")
    ]
    matrix.loc[
        matrix["use"].eq("Unknown-material detection"), "quantitative_performance"
    ] = f"Nearest-angle omitted-PFT challenge mean recall {chosen.unknown_recall.mean():.3f}, known false rejection {chosen.known_false_rejection.mean():.3f}; class-specific tables retained"
    species = matrix["use"].eq("Recorded species discrimination")
    matrix.loc[species, "readiness"] = "exploratory"
    matrix.loc[species, "recommended_use"] = (
        "supported known-species benchmark within familiar source populations; not unrestricted regional species recognition"
    )
    matrix.loc[species, "major_limitation"] += (
        "; downgraded for low closed-set coverage at WREF and severe paired cross-year loss"
    )
    matrix.to_csv(BASE / "tables/FINAL_READINESS_MATRIX.csv", index=False)


if __name__ == "__main__":
    run()
