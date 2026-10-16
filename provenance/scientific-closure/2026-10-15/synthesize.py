"""Consolidate old and closure evidence; no new model search or mixture fitting."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from spectralbridge.spectral_closure import (
    closure_labels,
    spectral_shape,
    cluster_rate_intervals,
    one_vs_rest_metrics,
)
from spectralbridge.spectral_learning import (
    cluster_bootstrap_accuracy,
    LearningConfig,
    outer_folds,
)
from spectralbridge.spectral_library_analytics import (
    stable_seed,
    scheme_data,
    prepare_fold,
    fit_predict_case,
)
from spectralbridge.mesma_readiness import load_compact_inputs
from spectralbridge.pft_method_audit import wavelength_weights
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.bulk.provenance import write_json_atomic

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
PRIOR = REPO / "provenance/spectral-library-analytics/2026-10-14/tables"
ROOT = REPO / "artifacts/plant_spectral_atlas/closure_20261015"
LEVELS = [
    "species_level",
    "researcher_level",
    "narrow_pft",
    "broad_pft",
    "coarse_cover",
]
DISPLAY = {
    "species_level": "Recorded species",
    "researcher_level": "Researcher category",
    "narrow_pft": "Narrow woody PFT",
    "broad_pft": "Broad woody leaf habit",
    "coarse_cover": "Coarse cover proxy",
}


def save(frame, name):
    frame.to_csv(BASE / "tables" / name, index=False)


def class_effects(X, y, ids, w, replicates=499):
    """Identity-balanced descriptive multivariate eta squared, conditional bootstrap."""
    frame = pd.DataFrame(dict(label=y, id=ids))
    keep = frame.groupby("id").label.nunique().eq(1)
    valid = frame.id.isin(keep[keep].index).to_numpy()
    X, y, ids = X[valid], np.asarray(y)[valid], np.asarray(ids)[valid]
    counts = pd.Series(y).groupby(ids).first().value_counts()
    valid = np.isin(y, counts[counts >= 10].index)
    X, y, ids = X[valid], y[valid], ids[valid]
    unique, inverse = np.unique(ids, return_inverse=True)
    classes = np.unique(y)
    center = X.mean(0)
    Z = X - center
    first = np.zeros((len(unique), X.shape[1]))
    second = np.zeros(len(unique))
    n = np.bincount(inverse)
    np.add.at(first, inverse, Z)
    np.add.at(second, inverse, np.sum(Z * Z * w, axis=1))
    first /= n[:, None]
    second /= n
    labels = (
        frame[frame.id.isin(unique)].groupby("id").label.first().loc[unique].to_numpy()
    )

    def effect(multiplicity):
        N = multiplicity.sum()
        mean = multiplicity @ first / N
        total = multiplicity @ second - N * np.sum(mean * mean * w)
        between = 0.0
        for c in classes:
            ix = labels == c
            size = multiplicity[ix].sum()
            if size:
                mu = multiplicity[ix] @ first[ix] / size
                between += size * np.sum((mu - mean) ** 2 * w)
        return between / total if total > 0 else np.nan

    estimate = effect(np.ones(len(unique)))
    rng = np.random.default_rng(20261015)
    boot = []
    for _ in range(replicates):
        multiplicity = np.zeros(len(unique))
        for c in classes:
            members = np.flatnonzero(labels == c)
            multiplicity += np.bincount(
                rng.choice(members, len(members), replace=True), minlength=len(unique)
            )
        boot.append(effect(multiplicity))
    return dict(
        eta_squared=estimate,
        eta_low=float(np.quantile(boot, 0.025)),
        eta_high=float(np.quantile(boot, 0.975)),
        identities=len(unique),
        classes=len(classes),
        interpretation="identity_balanced_descriptive_class_association_not_causal_or_adjusted_for_class_count",
    )


def broad_sensitivity():
    table, arrays, waves = load_compact_inputs(
        REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
        REPO / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact",
    )
    table = closure_labels(table)
    table["observation_id"] = (
        table.site + ":" + table.year.astype(str) + ":" + table.GlobalID
    )
    table["paired_zero_norm"] = np.any(
        np.column_stack([np.linalg.norm(x, axis=1) <= 0 for x in arrays.values()]),
        axis=1,
    )
    t, a = scheme_data(table, arrays, "broad_pft")
    weights = wavelength_weights(waves["NEON"])
    shape, amplitude = spectral_shape(a["NEON"], weights)
    config = LearningConfig()
    directories = []
    identity = dict(
        experiment="predeclared broad brightness clarification",
        code=_file_hash(__file__),
        config_seed=config.seed,
        source_sha256=_file_hash(
            REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
        ),
    )
    for fold, kind, train, test in outer_folds(t, config):
        if kind not in {"plant", "site", "year"}:
            continue
        prepared, support, status = prepare_fold(
            t, a, {}, fold, kind, train, test, config
        )
        if prepared is None:
            continue
        for mode in ["shape", "amplitude"]:
            aa = dict(a)
            aa["NEON"] = shape if mode == "shape" else amplitude[:, None]
            pp = dict(prepared)
            pp["test_arrays"] = dict(
                prepared["test_arrays"], NEON=aa["NEON"][prepared["test"]]
            )
            ww = dict(waves)
            if mode == "amplitude":
                ww["NEON"] = np.array([np.nan])
            context = dict(
                scheme="broad_pft",
                fold=fold,
                kind=kind,
                experiment="sensitivity",
                mode=mode,
            )
            directory = fit_predict_case(
                t,
                aa,
                ww,
                pp,
                context,
                "NEON_full",
                "logistic",
                ROOT / "broad_sensitivity",
                identity,
                config,
            )
            directories.append(directory)
    save(
        pd.concat(
            [pd.read_csv(d / "summary.csv") for d in directories], ignore_index=True
        ),
        "broad_sensitivity_summary.csv",
    )
    predictions = pd.concat(
        [pd.read_parquet(d / "predictions.parquet") for d in directories],
        ignore_index=True,
    )
    predictions.to_parquet(ROOT / "broad_sensitivity/predictions.parquet", index=False)
    write_json_atomic(
        BASE / "manifests/broad_sensitivity.json",
        dict(
            identity=identity,
            fit_cases=len(directories),
            active_checkpoints=[str(d.relative_to(REPO)) for d in directories],
            outputs={
                str(p.relative_to(REPO)): _file_hash(p)
                for d in directories
                for p in d.iterdir()
                if p.is_file()
            },
        ),
    )
    return predictions


def run():
    broad_predictions = broad_sensitivity()
    old = pd.read_csv(PRIOR / "ml_generalization.csv")
    old = old[
        old.model.eq("logistic")
        & old.kind.isin(["plant", "year", "site"])
        & old.representation.isin(["NEON_full", "OLI"])
    ].copy()
    old["scheme"] = old.scheme.map(
        {"researcher": "researcher_level", "inferred_pft": "narrow_pft"}
    )
    old["mode"] = "stored"
    old["experiment"] = "hierarchy"
    old["origin"] = "P126 reused"
    new = pd.concat(
        [
            pd.read_csv(BASE / "tables/new_summary.csv"),
            pd.read_csv(BASE / "tables/broad_sensitivity_summary.csv"),
        ],
        ignore_index=True,
    )
    new["origin"] = "closure targeted"
    combined = pd.concat([old, new], ignore_index=True)
    save(combined, "biological_generalization.csv")
    preds = pd.concat(
        [pd.read_parquet(ROOT / "predictions.parquet"), broad_predictions],
        ignore_index=True,
    )
    current = preds[preds.experiment.eq("hierarchy")]

    legacy = pd.read_parquet(
        REPO / "artifacts/plant_spectral_atlas/analytics/predictions.parquet",
        filters=[
            ("model", "=", "logistic"),
            ("representation", "in", ["NEON_full", "OLI"]),
            ("kind", "in", ["plant", "year", "site"]),
        ],
    )
    legacy["scheme"] = legacy.scheme.map(
        {"researcher": "researcher_level", "inferred_pft": "narrow_pft"}
    )
    legacy["mode"] = "stored"
    legacy["experiment"] = "hierarchy"
    baseline_predictions = pd.concat([legacy, current], ignore_index=True)
    support = pd.read_csv(BASE / "tables/fold_support.csv")
    rows = []
    for (level, fold, kind), g in support[
        support.kind.isin(["plant", "site", "year"])
    ].groupby(["level", "fold", "kind"]):
        target = g.test_identities.sum()
        evaluable = g.loc[g.status.eq("closed_evaluable"), "test_identities"].sum()
        rows.append(
            dict(
                level=level,
                fold=fold,
                kind=kind,
                all_labelled_target_identities=target,
                closed_evaluable_identities=evaluable,
                closed_set_fraction=evaluable / target if target else np.nan,
                absent_training_target_identities=g.loc[
                    g.status.eq("absent_training_open_set"), "test_identities"
                ].sum(),
            )
        )
    save(pd.DataFrame(rows), "closed_set_coverage.csv")
    changes = []
    for (scheme, fold, mode), g in preds[preds.experiment.eq("sensitivity")].groupby(
        ["scheme", "fold", "mode"]
    ):
        base = baseline_predictions[
            baseline_predictions.scheme.eq(scheme)
            & baseline_predictions.fold.eq(fold)
            & baseline_predictions.representation.eq("NEON_full")
        ].sort_values("observation_id")
        g = g.sort_values("observation_id")
        if base.observation_id.tolist() != g.observation_id.tolist():
            raise ValueError("Sensitivity targets differ from baseline")
        classes = np.asarray(json.loads(g.classes.iloc[0]))
        draws = []
        point = []
        for a in [base, g]:
            draws.append(
                cluster_bootstrap_accuracy(
                    a.label,
                    a.suggested_label,
                    a.GlobalID,
                    classes,
                    seed=stable_seed(fold),
                )
            )
            point.append(
                a.assign(correct=a.label.eq(a.suggested_label))
                .groupby("label")
                .correct.mean()
                .mean()
            )
        delta = draws[1] - draws[0]
        changes.append(
            dict(
                scheme=scheme,
                fold=fold,
                kind=g.kind.iloc[0],
                mode=mode,
                baseline_BA=point[0],
                sensitivity_BA=point[1],
                BA_difference=point[1] - point[0],
                difference_low=float(np.quantile(delta, 0.025)),
                difference_high=float(np.quantile(delta, 0.975)),
            )
        )
    save(pd.DataFrame(changes), "brightness_sampling_sensitivity.csv")
    rates = [pd.read_csv(BASE / "tables/false_detection_rates.csv")]
    for (fold, mode), g in broad_predictions.groupby(["fold", "mode"]):
        classes = np.asarray(json.loads(g.classes.iloc[0]))
        r = one_vs_rest_metrics(g.label, g.suggested_label, classes).merge(
            cluster_rate_intervals(
                g.label, g.suggested_label, g.GlobalID, classes, seed=stable_seed(fold)
            ),
            on="label",
        )
        rates.append(
            r.assign(
                scheme="broad_pft",
                fold=fold,
                mode=mode,
                representation="NEON_full",
                experiment="sensitivity",
                kind=g.kind.iloc[0],
            )
        )

    for (scheme, fold, rep), g in legacy.groupby(["scheme", "fold", "representation"]):
        classes = np.asarray(json.loads(g.classes.iloc[0]))
        r = one_vs_rest_metrics(g.label, g.suggested_label, classes)
        r = r.merge(
            cluster_rate_intervals(
                g.label, g.suggested_label, g.GlobalID, classes, seed=stable_seed(fold)
            ),
            on="label",
            validate="one_to_one",
        )
        rates.append(
            r.assign(
                scheme=scheme,
                fold=fold,
                representation=rep,
                experiment="hierarchy",
                mode="stored",
                kind=g.kind.iloc[0],
            )
        )
    save(pd.concat(rates, ignore_index=True), "all_class_detection_rates.csv")
    # Unequal populations are explicit; species/narrow/broad are not all records.
    source = REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    compact = REPO / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact"
    table, arrays, waves = load_compact_inputs(source, compact)
    table = closure_labels(table)
    effects = []
    for level in LEVELS:
        eligible = table[level].notna()
        t = table[eligible]
        for sensor in ["NEON", "OLI"]:
            w = (
                wavelength_weights(waves[sensor])
                if sensor == "NEON"
                else np.ones(7) / 7
            )
            X = arrays[sensor][eligible]
            for mode in ["stored", "shape"]:
                values = spectral_shape(X, w)[0] if mode == "shape" else X
                effects.append(
                    dict(
                        level=level,
                        sensor=sensor,
                        mode=mode,
                        **class_effects(values, t[level], t.GlobalID, w),
                    )
                )
    save(pd.DataFrame(effects), "biological_effect_sizes.csv")
    sampling = (
        table.groupby("site")
        .agg(annual_rows=("GlobalID", "size"), identities=("GlobalID", "nunique"))
        .reset_index()
    )
    sampling["annual_row_share"] = sampling.annual_rows / sampling.annual_rows.sum()
    sampling["identity_share"] = sampling.identities / sampling.identities.sum()
    save(sampling, "sampling_weight_effect.csv")
    class_counts = (
        pd.concat([preds, legacy], ignore_index=True)
        .groupby(["scheme", "fold", "representation", "experiment", "mode"])
        .classes.first()
        .map(lambda value: len(json.loads(value)))
    )

    def promising(frame):
        if not len(frame):
            return False
        references = [
            1
            / class_counts.loc[
                (r.scheme, r.fold, r.representation, r.experiment, r.mode)
            ]
            for r in frame.itertuples(index=False)
        ]
        return bool(np.all(frame.BA_lo.to_numpy() > references))

    # Compact evidence ladder: no synthetic->real or classifier->abundance promotion.
    primary = combined[
        combined.probability.eq("raw")
        & combined.experiment.eq("hierarchy")
        & combined["mode"].eq("stored")
    ]
    ladder = []
    for level in LEVELS:
        for kind in ["plant", "year", "site"]:
            for rep in ["NEON_full", "OLI"]:
                g = primary[
                    primary.scheme.eq(level)
                    & primary.kind.eq(kind)
                    & primary.representation.eq(rep)
                ]
                if not len(g):
                    continue
                ladder.append(
                    dict(
                        level=level,
                        display=DISPLAY[level],
                        holdout=kind,
                        sensor=rep,
                        folds=len(g),
                        mean_BA=g.balanced_accuracy.mean(),
                        minimum_BA=g.balanced_accuracy.min(),
                        maximum_BA=g.balanced_accuracy.max(),
                        minimum_conditional_lower=g.BA_lo.min(),
                        maximum_conditional_upper=g.BA_hi.max(),
                        minimum_test_identities=g.test_identities.min(),
                        status="scientifically promising"
                        if promising(g)
                        else "exploratory",
                    )
                )
    save(pd.DataFrame(ladder), "biological_evidence_ladder.csv")
    matrix = []
    for level in LEVELS:
        g = primary[
            primary.scheme.eq(level)
            & primary.kind.eq("plant")
            & primary.representation.eq("NEON_full")
        ]
        q = primary[
            primary.scheme.eq(level)
            & primary.kind.eq("site")
            & primary.representation.eq("NEON_full")
        ]
        if not len(g):
            status = "not ready"
            quant = "Insufficient supported closed-set folds"
        else:
            status = "scientifically promising" if promising(g) else "exploratory"
            quant = f"Plant BA {g.balanced_accuracy.mean():.3f}; observed site range {q.balanced_accuracy.min():.3f}–{q.balanced_accuracy.max():.3f}"
        matrix.append(
            dict(
                use=DISPLAY[level] + " discrimination",
                evidence="biological_generalization.csv; biological_effect_sizes.csv; all_class_detection_rates.csv",
                validation="identity-held-out; site/year where class support permits",
                quantitative_performance=quant,
                uncertainty="whole-ID conditional bootstrap; varying supported class populations",
                readiness=status,
                recommended_use="closed-set research benchmark within supported source-label/domain populations",
                major_limitation="not novel-species or geographic-population validation; proxy/partial labels",
                plant_evidence=status,
                year_evidence="conditional observed directions",
                site_evidence="conditional observed sites",
                sensor_evidence="synthetic OLI only",
                mixture_evidence="does not follow from classification",
                independent_truth="source labels; no fraction truth",
            )
        )
    effects = pd.read_csv(PRIOR / "biological_contrasts.csv")
    effects = effects[effects.scheme.eq("inferred_pft")]
    pilot = pd.read_csv(PRIOR / "real_landsat_flight_metrics.csv")
    pilot = pilot[pilot.variant.eq("undarkened")].iloc[0]
    mixture = pd.read_csv(PRIOR / "mixture_recovery.csv")
    mixture = mixture[
        mixture.scheme.eq("inferred_pft")
        & mixture.sensor.eq("NEON")
        & mixture.kind.eq("plant")
        & mixture.method.eq("EAR_MESMA3")
    ]
    extras = [
        (
            "Cross-year transfer",
            "paired_temporal_recognition.csv; paired_temporal_partition.csv",
            "same unseen NIWO polygon targets in both years; other IDs train",
            "See direction/class-specific paired BA and change intervals",
            "conditional paired-ID bootstrap",
            "exploratory",
            "year-aware application only; preserve all valid annual records",
            "two years/one repeated site; observation conditions and ecology inseparable",
        ),
        (
            "Hyperspectral classification",
            "biological_generalization.csv; brightness_sampling_sensitivity.csv",
            "nested grouped logistic and saved P126 comparisons",
            "See label-specific scores and shape/amplitude sensitivities",
            "conditional identity intervals",
            "scientifically promising",
            "supported closed-set label recognition",
            "classification is not pure biological mechanism or abundance",
        ),
        (
            "Synthetic Landsat transfer",
            "P126 biological_contrasts.csv; spectral_resolution_performance.csv",
            "paired common reference and test memberships",
            f"{int((effects.NEON_supported & effects.OLI_supported).sum())}/{int(effects.NEON_supported.sum())} NEON-supported inferred-PFT contrasts retained",
            "paired bootstraps and original Holm families",
            "scientifically promising",
            "diagnostic response reduction at common support",
            "not independent Landsat validation",
        ),
        (
            "Real Landsat agreement",
            "P121 flight_metrics.csv; registration_sensitivity.csv",
            "one independent R10C flight/scene; spatial blocks",
            f"Pooled SR RMSE {pilot.pooled_seven_band_RMSE:.5f}; {int(pilot.N)} footprints",
            "56 spatial blocks; source timestamp caveat",
            "validated for constrained use",
            "radiometric/spatial comparison for this one scene pair",
            "no multisite ecological/fraction validation",
        ),
        (
            "Endmember selection",
            "P123 library_size.csv; mixture_identifiability.csv",
            "training-only candidates; held-out identities",
            "coverage improves; competing compositions remain",
            "conditional library/selector sensitivity",
            "exploratory",
            "controlled synthetic mixture tests with explicit competing solutions",
            "purity/scale incomplete; representation does not ensure uniqueness",
        ),
        (
            "Mixture detection",
            "P126 detection_limits.csv",
            "saved parents/fraction trajectories; cutoff 0.10",
            "class-specific conditional FPR/FNR; no population D50/80/95",
            "dependent trajectories; no field probability guarantee",
            "exploratory",
            "hypothesis generation and test-design planning",
            "few independent parents; thresholds not operationally validated",
        ),
        (
            "Mixture abundance estimation",
            "P123 fraction_errors.csv; P126 sensor_resolution_mixture_results.csv",
            "held-out empirical parents; constrained synthetic fractions",
            f"PFT primary NEON mean class/fold RMSE {mixture.fraction_RMSE.mean():.3f}",
            "endmember variability intervals are not calibrated field CI",
            "not ready",
            "experimental recoverability/ambiguity diagnostics only",
            "independent measured fractions/purity and verified library scale absent",
        ),
        (
            "Unknown-material detection",
            "P126 unknown_material_detection.csv",
            "whole ecological class omitted; known-only calibration",
            "weak recall at low known rejection; see saved class-specific values",
            "conditional proxy unknown challenge",
            "not ready",
            "flag potential outliers; never certify library membership",
            "fails declared 80% recall / 5% known-FPR review scenario; physical unknown coverage incomplete",
        ),
    ]
    for use, ev, design, quant, unc, status, recommend, gap in extras:
        matrix.append(
            dict(
                use=use,
                evidence=ev,
                validation=design,
                quantitative_performance=quant,
                uncertainty=unc,
                readiness=status,
                recommended_use=recommend,
                major_limitation=gap,
                plant_evidence="see named design",
                year_evidence="limited",
                site_evidence="limited",
                sensor_evidence="see named design",
                mixture_evidence="synthetic unless stated",
                independent_truth="no independent field abundance truth",
            )
        )
    save(pd.DataFrame(matrix), "FINAL_READINESS_MATRIX.csv")


if __name__ == "__main__":
    run()
