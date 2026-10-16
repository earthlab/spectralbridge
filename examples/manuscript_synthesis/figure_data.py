"""Read canonical results only; save transparent, descriptive plotting reductions."""

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from .palette import CATEGORIES

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "provenance/manuscript-synthesis/2026-10-16/v1"
P129 = REPO / "provenance/researcher-pft-information/2026-10-15/v1"
P130 = REPO / "provenance/researcher-evidence/2026-10-16/v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def summarize_effects(frame):
    """Median of four observed cohort effects; stringent opacity, not pooled inference."""
    rows = []
    for (pair, w), g in frame.groupby(["pair", "wavelength_nm"], sort=False):
        if len(g) != 4:
            raise ValueError("Every displayed pair/coordinate requires four cohorts")
        sign = np.sign(g.matched_effect.to_numpy())
        consistent = np.all(sign > 0) or np.all(sign < 0)
        rows.append(
            dict(
                pair=pair,
                wavelength_nm=w,
                effect=g.matched_effect.median(),
                minimum_effect=g.matched_effect.min(),
                maximum_effect=g.matched_effect.max(),
                supported_cohorts=int((g.adjusted_p <= 0.05).sum()),
                same_direction=bool(consistent),
                consistent_evidence=bool((g.adjusted_p <= 0.05).all() and consistent),
            )
        )
    return pd.DataFrame(rows)


def summarize_calibration(frame):
    """Canonical mean-of-fold calibration, matching final report (equal held-site weight)."""
    f = frame[
        frame.kind.eq("site")
        & frame.representation.eq("NEON")
        & frame.method.isin(["Ridge", "MESMA"])
    ]
    keys = ["method", "researcher_category", "true_fraction"]
    return (
        f.groupby(keys, sort=False)
        .agg(
            prediction_mean=("prediction_mean", "mean"),
            fold_count=("fold", "nunique"),
            N_per_fold=("N", "mean"),
        )
        .reset_index()
    )


def prepare():
    (BASE / "data").mkdir(parents=True, exist_ok=True)
    sources = {}
    panels = {}

    def source(relative):
        p = REPO / relative
        sources[relative] = sha(p)
        return p

    def read(relative):
        return pd.read_csv(source(relative))

    def save(frame, name):
        frame.to_csv(BASE / "data" / name, index=False)
        return frame

    pub = "provenance/publication-figures/2026-10-14/"
    p129 = str(P129.relative_to(REPO)) + "/"
    p130 = str(P130.relative_to(REPO)) + "/"
    old = json.loads((REPO / pub / "evidence_manifest.json").read_text())
    assert (
        sha(REPO / pub / "atlas_summary.csv")
        == old["owned_files"][pub + "atlas_summary.csv"]
    )
    a = read(pub + "atlas_summary.csv")
    assert set(a.cover_category) == set(CATEGORIES)
    assert (
        len(a) == 1800 and (a.q25 <= a["median"]).all() and (a["median"] <= a.q75).all()
    )
    save(a, "A_category_spectra.csv")
    panels["A"] = {
        "source": pub + "atlas_summary.csv",
        "filter": "All five cover_category labels; all 360 supported wavelengths",
        "fields": ["cover_category", "wavelength_nm", "N", "q25", "median", "q75"],
        "aggregation": "Previously validated annual-observation median and 25th/75th percentiles, unchanged; repeated years are descriptive observations, not independent replicate counts.",
        "units": "Corrected spectral value in stored units; absolute physical reflectance scale unresolved.",
    }
    bsource = read(p129 + "tables/cohort_wavelength_inference.csv")
    save(summarize_effects(bsource), "B_wavelength_effects.csv")
    panels["B"] = {
        "source": p129 + "tables/cohort_wavelength_inference.csv",
        "filter": "All ten researcher-category pairs; NIWO2020, NIWO2023, WREF2023, YELL2023; all 360 coordinates",
        "fields": [
            "pair",
            "site",
            "year",
            "wavelength_nm",
            "matched_effect",
            "adjusted_p",
        ],
        "aggregation": "Median signed standardized effect across four observed cohorts. Full saturation only if all four joint-adjusted p<=.05 AND effect signs agree; otherwise opacity .24. This is a descriptive display, not a new pooled test.",
        "sign": "First named category minus second named category. Wavelength family uses saved max-T / 40-contrast Bonferroni evidence.",
    }
    whole = read(p130 + "tables/whole_spectrum_separability.csv")
    assert len(whole) == 40 and whole.NEON_supported.all()
    source("src/spectralbridge/data/landsat_band_parameters.json")
    bands = json.loads(
        (REPO / "src/spectralbridge/data/landsat_band_parameters.json").read_text()
    )["Landsat 8 OLI"]
    save(
        pd.DataFrame(
            {
                "band": np.arange(1, 8),
                "center_nm": bands["wavelengths"],
                "FWHM_nm": bands["fwhms"],
            }
        ),
        "OLI_band_positions.csv",
    )
    s = read(p130 + "tables/recognition_control_summary.csv")
    s = s[s.method.isin(["Random", "Selected replay"])].rename(
        columns={"mean": "BA", "min": "observed_min", "max": "observed_max"}
    )
    original = read(p129 + "tables/complementary_feature_performance.csv")
    full = (
        original[original.budget.astype(str).eq("360")]
        .groupby("kind")
        .balanced_accuracy.agg(["mean", "min", "max"])
        .reset_index()
    )
    full["budget"] = 360
    full["method"] = "Full spectrum"
    full = full.rename(
        columns={"mean": "BA", "min": "observed_min", "max": "observed_max"}
    )
    c = save(
        pd.concat(
            [
                s[["kind", "method", "budget", "BA", "observed_min", "observed_max"]],
                full,
            ],
            ignore_index=True,
        ),
        "C_recognition.csv",
    )
    panels["C"] = {
        "sources": [
            p130 + "tables/recognition_control_summary.csv",
            p129 + "tables/complementary_feature_performance.csv",
        ],
        "filter": "plant/site; Selected replay / Random; budgets1,2,3,5,7,10,20,50,100; full360 baseline",
        "fields": [
            "kind",
            "method",
            "budget",
            "mean",
            "min",
            "max",
            "balanced_accuracy",
        ],
        "aggregation": "Mean across three outer folds; random averages five fixed paths per fold. Ranges are observed folds/seeds, not confidence intervals. Random series ends at100; only actual full-spectrum endpoints shown.",
    }
    rates = read(p129 + "tables/class_specific_transfer.csv")
    rates = rates[rates.budget.astype(str).eq("360")]
    d = save(
        rates.groupby(["kind", "researcher_category"]).recall.mean().reset_index(),
        "D_recall.csv",
    )
    confusion = read(p129 + "tables/confusion_plot_values.csv")
    confusion = confusion[
        confusion.kind.eq("site") & confusion.representation.eq("NEON")
    ]
    save(confusion, "D_confusion.csv")
    panels["D"] = {
        "sources": [
            p129 + "tables/class_specific_transfer.csv",
            p129 + "tables/confusion_plot_values.csv",
        ],
        "filter": "budget360; new-polygons/held-sites; NEON held-site confusion",
        "fields": [
            "researcher_category",
            "kind",
            "recall",
            "truth",
            "predicted",
            "mean_fold_row_fraction",
        ],
        "aggregation": "Mean per-class recall / row-normalized confusion fraction across the three observed outer folds; not pooled pixel counts.",
    }
    fractions = read(p130 + "tables/fraction_grid_calibration.csv")
    save(summarize_calibration(fractions), "E_calibration.csv")
    panels["E"] = {
        "source": p130 + "tables/fraction_grid_calibration.csv",
        "filter": "kind=site,representation=NEON,method in[Ridge,MESMA]",
        "fields": [
            "fold",
            "researcher_category",
            "method",
            "true_fraction",
            "prediction_mean",
            "N",
        ],
        "aggregation": "Equal-weight mean of three canonical held-site fold means at every supported nominal fraction, matching report. Existing counts/nominal-bin handling retained.",
        "scope": "Synthetic algebraic fractions only; Ridge denotes 120 proper parents, MESMA retains15 candidates.",
    }
    domain = read(p130 + "tables/abundance_domain_summary.csv")
    domain = domain[
        domain.kind.isin(["plant", "site"])
        & domain.representation.eq("NEON")
        & domain.method.isin(["Training prior", "MESMA", "Ridge"])
    ].copy()
    domain["method"] = domain.method.replace({"MESMA": "MESMA15", "Ridge": "Ridge120"})
    domain = domain.rename(columns={"mean": "RMSE"})
    matched = read(p130 + "tables/same_candidate_ridge.csv")
    matched = (
        matched[
            matched.kind.isin(["plant", "site"]) & matched.representation.eq("NEON")
        ]
        .groupby("kind")
        .RMSE.agg(["mean", "min", "max"])
        .reset_index()
        .rename(columns={"mean": "RMSE"})
    )
    matched["method"] = "Ridge15"
    f = save(
        pd.concat(
            [domain[["kind", "method", "RMSE", "min", "max"]], matched],
            ignore_index=True,
        ),
        "F_library_comparison.csv",
    )
    amb = read(p129 + "tables/abundance_by_ambiguity.csv")
    amb = amb[
        amb.kind.eq("site")
        & amb.representation.eq("NEON")
        & amb.method.isin(["MESMA", "Ridge"])
    ]
    amb = amb.groupby(["method", "ambiguity"]).fraction_RMSE.mean().reset_index()
    amb["method"] = amb.method.replace({"MESMA": "MESMA15", "Ridge": "Ridge120"})
    save(amb, "F_ambiguity.csv")
    panels["F"] = {
        "sources": [
            p130 + "tables/abundance_domain_summary.csv",
            p130 + "tables/same_candidate_ridge.csv",
            p129 + "tables/abundance_by_ambiguity.csv",
        ],
        "filter": "NEON; main comparison plant/site; prior/MESMA15/Ridge15/Ridge120. Ambiguity: held-site MESMA/Ridge120 only.",
        "fields": [
            "kind",
            "method",
            "RMSE",
            "mean",
            "min",
            "max",
            "ambiguity",
            "fraction_RMSE",
        ],
        "aggregation": "Mean-fold macro fraction RMSE. Retained-capacity ridge uses exact15 MESMA parents; original ridge120 uses120. Ambiguity curves average fold-stratum RMSE, not all mixture rows pooled.",
        "ambiguity_definition": "Maximum candidate-class fraction range under existing .01 near-fit tolerance: low<.10, moderate .10-.30, high>=.30. Same target strata for both models. Not exhaustive physical uncertainty.",
        "limit": "Same-candidate control changes retained biological diversity/training bundles and learning prior; no isolated causal library-size claim or intrinsic algorithm superiority.",
    }
    annotations = []

    def annotate(name, value, expected=None, tolerance=None):
        if expected is not None:
            assert abs(value - expected) <= tolerance, (name, value, expected)
        annotations.append(
            dict(
                annotation=name,
                value=float(value),
                requested_value=expected,
                tolerance=tolerance,
            )
        )

    for kind, sel, ran, endpoint in [
        ("plant", 0.816, 0.774, 0.852),
        ("site", 0.701, 0.650, 0.738),
    ]:
        for method, expected in [("Selected replay", sel), ("Random", ran)]:
            annotate(
                "C_" + kind + "_" + method + "_20",
                float(
                    c[c.kind.eq(kind) & c.method.eq(method) & c.budget.eq(20)].BA.iloc[
                        0
                    ]
                ),
                expected,
                0.0005,
            )
        annotate(
            "C_" + kind + "_full",
            float(c[c.kind.eq(kind) & c.method.eq("Full spectrum")].BA.iloc[0]),
            endpoint,
            0.0005,
        )
        m = f[f.kind.eq(kind)].set_index("method").RMSE
        annotate("F_" + kind + "_relative_improvement", 1 - m.Ridge120 / m.MESMA15)
    annotate(
        "D_Woody_shrub_site",
        float(
            d[d.kind.eq("site") & d.researcher_category.eq("Woody shrub")].recall.iloc[
                0
            ]
        ),
        0.463,
        0.0005,
    )
    save(pd.DataFrame(annotations), "annotations.csv")
    report = source(
        "output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf"
    )
    save(
        whole[
            ["contrast", "site", "year", "NEON_effect", "NEON_p_holm", "NEON_supported"]
        ],
        "B_whole_spectrum_support.csv",
    )
    manifest = {
        "status": "prepared from validated products; no fits or source-spectrum reads",
        "panel_sources": panels,
        "source_sha256": sources,
        "report": str(report.relative_to(REPO)),
        "data_sha256": {
            str(p.relative_to(BASE)): sha(p)
            for p in sorted((BASE / "data").glob("*.csv"))
        },
        "cohort_count": 4,
        "categories": list(CATEGORIES),
        "annotation_checks": "data/annotations.csv",
    }
    (BASE / "figure_data_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    return manifest


def load_bundle():
    manifest = json.loads((BASE / "figure_data_manifest.json").read_text())
    for name, expected in manifest["data_sha256"].items():
        assert sha(BASE / name) == expected, name
    return {p.stem: pd.read_csv(p) for p in (BASE / "data").glob("*.csv")}
