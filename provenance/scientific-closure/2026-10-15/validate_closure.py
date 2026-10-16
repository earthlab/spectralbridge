"""Independent numerical and identity checks of final targeted closure fits."""

from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
from scipy.special import softmax
from sklearn.feature_selection import f_classif
from sklearn.metrics import balanced_accuracy_score, f1_score
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.mesma_readiness import load_compact_inputs
from spectralbridge.spectral_closure import closure_labels, spectral_shape
from spectralbridge.spectral_learning import probabilities
from spectralbridge.pft_method_audit import wavelength_weights
from spectralbridge.bulk.provenance import write_json_atomic

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]


def run():
    import joblib

    main = json.loads((BASE / "manifests/closure_run.json").read_text())
    broad = json.loads((BASE / "manifests/broad_sensitivity.json").read_text())
    for name, h in main["outputs"].items():
        assert _file_hash(REPO / name) == h, name
    for name, h in broad["outputs"].items():
        assert _file_hash(REPO / name) == h, name
    table, arrays, waves = load_compact_inputs(
        REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
        REPO / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact",
    )
    table = closure_labels(table)
    table["observation_id"] = (
        table.site + ":" + table.year.astype(str) + ":" + table.GlobalID
    )
    lookup = pd.Series(table.index, index=table.observation_id)
    checked = paired = 0
    for name in main["active_checkpoints"] + broad["active_checkpoints"]:
        d = REPO / name
        ledger = json.loads((d / "manifest.json").read_text())
        for f, h in ledger["outputs"].items():
            assert _file_hash(d / f) == h
        details = json.loads((d / "fit_details.json").read_text())
        context = details["context"]
        members = pd.read_parquet(d / "memberships.parquet")
        roles = {r: set(g.GlobalID) for r, g in members.groupby("role")}
        assert not roles["proper_training"] & roles["test"]
        assert not roles.get("calibration", set()) & roles["test"]
        assert not roles.get("calibration", set()) & roles["proper_training"]
        for inner in details["inner_memberships"]:
            assert (
                set(inner["train_ids"] + inner["validation_ids"])
                <= roles["proper_training"]
            )
            assert not set(inner["train_ids"]) & set(inner["validation_ids"])
        if context["experiment"] == "paired_transfer":
            assert (
                members[members.role.ne("test")].year.eq(context["training_year"]).all()
            )
            targets = members[members.role.eq("test")]
            assert targets.groupby("GlobalID").year.nunique().eq(2).all()
            paired += 1
        if context["mode"] == "one_identity":
            assert members[members.role.eq("proper_training")].GlobalID.is_unique
        sensor = "OLI" if details["representation"] == "OLI" else "NEON"
        X = arrays[sensor]
        if context["mode"] in {"shape", "amplitude"}:
            shape, amplitude = spectral_shape(X, wavelength_weights(waves[sensor]))
            X = shape if context["mode"] == "shape" else amplitude[:, None]
        proper = members[members.role.eq("proper_training")]
        ix = lookup.loc[proper.observation_id].to_numpy()
        model = joblib.load(d / "model.joblib")
        np.testing.assert_allclose(
            model["scale"].mean_, X[ix].mean(0), rtol=1e-12, atol=1e-8
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            expected = f_classif(X[ix], proper.label)[0]
        np.testing.assert_allclose(
            model["select"].scores_,
            np.nan_to_num(expected, nan=-np.inf, posinf=np.finfo(float).max),
            rtol=1e-10,
            atol=1e-8,
        )
        pred = pd.read_parquet(d / "predictions.parquet")
        truth = pred.label.to_numpy()
        classes = np.asarray(json.loads(pred.classes.iloc[0]))
        assert np.array_equal(
            table[context["scheme"]].iloc[lookup.loc[pred.observation_id]].to_numpy(),
            truth,
        )
        p = np.array([json.loads(v) for v in pred.raw_probabilities])
        actual = probabilities(model, X[lookup.loc[pred.observation_id]])
        np.testing.assert_allclose(actual, p, rtol=1e-10, atol=1e-10)
        summary = pd.read_csv(d / "summary.csv")
        if context["experiment"] == "paired_transfer":
            yearly = pd.read_csv(BASE / "tables/paired_temporal_recognition.csv")
            selected = yearly[
                yearly.scheme.eq(context["scheme"])
                & yearly.fold.eq(context["fold"])
                & yearly.representation.eq(details["representation"])
            ]
            for year, g in pred.groupby("year"):
                value = selected[selected.test_year.eq(year)].iloc[0]
                np.testing.assert_allclose(
                    value.balanced_accuracy,
                    balanced_accuracy_score(g.label, g.suggested_label),
                    atol=1e-12,
                )

        for mode, column in [
            ("raw", "raw_probabilities"),
            ("temperature", "temperature_probabilities"),
        ]:
            probs = np.array([json.loads(v) for v in pred[column]])
            row = summary[summary.probability.eq(mode)].iloc[0]
            predicted = classes[probs.argmax(1)]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                np.testing.assert_allclose(
                    row.balanced_accuracy,
                    balanced_accuracy_score(truth, predicted),
                    atol=1e-12,
                )
            np.testing.assert_allclose(
                row.macro_F1,
                f1_score(
                    truth,
                    predicted,
                    labels=[c for c in classes if c in set(truth)],
                    average="macro",
                    zero_division=0,
                ),
                atol=1e-12,
            )
            encoded = np.array([np.where(classes == v)[0][0] for v in truth])
            np.testing.assert_allclose(
                row.Brier,
                np.mean(np.sum((probs - np.eye(len(classes))[encoded]) ** 2, axis=1)),
                atol=1e-12,
            )
        raw = summary[summary.probability.eq("raw")].iloc[0]
        np.testing.assert_allclose(
            np.array([json.loads(v) for v in pred.temperature_probabilities]),
            softmax(np.log(np.clip(p, 1e-12, 1)) / raw.temperature, axis=1),
            atol=1e-10,
        )
        cal = members[members.role.eq("calibration")]
        if len(cal):
            pc = probabilities(model, X[lookup.loc[cal.observation_id]])
            encoded = np.array([np.where(classes == v)[0][0] for v in cal.label])
            scores = 1 - pc[np.arange(len(pc)), encoded]
            grouped = (
                pd.DataFrame(dict(id=cal.GlobalID.to_numpy(), score=scores))
                .groupby("id")
                .score.max()
            )
            rank = int(np.ceil((len(grouped) + 1) * 0.9))
            q = np.sort(grouped)[rank - 1] if rank <= len(grouped) else np.inf
            np.testing.assert_allclose(raw.conformal_threshold, q, atol=1e-12)
            y = np.array([np.where(classes == v)[0][0] for v in truth])
            covered = 1 - p[np.arange(len(p)), y] <= q + 1e-12
            np.testing.assert_array_equal(covered, pred.prediction_set_covered)
            empirical = (
                pd.DataFrame(dict(id=pred.GlobalID.to_numpy(), covered=covered))
                .groupby("id")
                .covered.all()
                .mean()
            )
            np.testing.assert_allclose(
                raw.identity_joint_coverage, empirical, atol=1e-12
            )
        checked += 1
    partition = pd.read_csv(BASE / "tables/paired_temporal_partition.csv")
    components = [
        "class_SS",
        "polygon_within_class_SS",
        "year_SS",
        "class_by_year_SS",
        "residual_change_SS",
    ]
    np.testing.assert_allclose(
        partition[components].sum(axis=1), partition.total_SS, rtol=1e-12
    )
    effects = pd.read_csv(BASE / "tables/biological_effect_sizes.csv")
    for row in effects.itertuples(index=False):
        mask = table[row.level].notna()
        t = table.loc[mask].copy()
        X = arrays[row.sensor][mask.to_numpy()]
        consistent = t.groupby("GlobalID")[row.level].nunique().eq(1)
        keep = t.GlobalID.isin(consistent[consistent].index).to_numpy()
        t = t.loc[keep]
        X = X[keep]
        counts = t.drop_duplicates("GlobalID")[row.level].value_counts()
        keep = t[row.level].isin(counts[counts >= 10].index).to_numpy()
        t = t.loc[keep]
        X = X[keep]
        w = (
            wavelength_weights(waves[row.sensor])
            if row.sensor == "NEON"
            else np.ones(7) / 7
        )
        if row.mode == "shape":
            X = spectral_shape(X, w)[0]
        multiplicity = t.groupby("GlobalID").GlobalID.transform("size").to_numpy()
        weight = 1 / multiplicity
        center = np.average(X, axis=0, weights=weight)
        total = np.sum(weight[:, None] * (X - center) ** 2 * w)
        residual = 0.0
        for label in t[row.level].unique():
            ix = t[row.level].eq(label).to_numpy()
            mu = np.average(X[ix], axis=0, weights=weight[ix])
            residual += np.sum(weight[ix, None] * (X[ix] - mu) ** 2 * w)
        np.testing.assert_allclose(row.eta_squared, 1 - residual / total, atol=1e-12)
        assert (
            row.identities == t.GlobalID.nunique()
            and row.classes == t[row.level].nunique()
        )
        assert 0 <= row.eta_low <= row.eta_high <= 1
    previous = REPO / "provenance/spectral-library-analytics/2026-10-14"
    e = json.loads((previous / "evidence_manifest.json").read_text())
    for n, h in e["outputs"].items():
        assert _file_hash(previous / n) == h, n
    result = dict(
        status="passed",
        fits=checked,
        paired_transfer_fits=paired,
        proper_train_calibration_test_IDs_disjoint=True,
        paired_targets_two_years_same_unseen_IDs=True,
        paired_year_specific_BA_independently_reproduced=True,
        scaling_and_feature_scores_training_only=True,
        predictions_reproduced=True,
        independent_BA_F1_Brier_and_conformal_math=True,
        paired_SS_partition_exact=True,
        identity_balanced_class_effects_independently_reproduced=True,
        prior_116_artifacts_unchanged=True,
    )
    write_json_atomic(BASE / "manifests/numerical_validation.json", result)
    print(result)


if __name__ == "__main__":
    run()
