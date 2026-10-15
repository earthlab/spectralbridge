"""Independent numerical/lineage checks for completed experimental learning runs."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score, confusion_matrix
from sklearn.feature_selection import f_classif
from .plant_spectral_atlas import _file_hash
from .mesma_readiness import load_compact_inputs, flight_target_tables
from .bulk.provenance import write_json_atomic


def validate_learning_run(root, destination=None):
    """Verify owned bytes before trusted model loading; compare math and support.

    Requires the original library and verified compact products, read in place.
    No new fit or selection is performed. This does not test external validity.
    """
    import joblib

    root = Path(root)
    manifest = json.loads((root / "learning_manifest.json").read_text())
    for name, expected in manifest["outputs"].items():
        if _file_hash(root / name) != expected:
            raise ValueError("Changed owned analytics output: " + name)
    inputs = manifest["identity"]["inputs"]
    if _file_hash(inputs["source"]) != inputs["source_sha256"]:
        raise ValueError("Source changed")
    table, arrays, waves = load_compact_inputs(inputs["source"], inputs["compact"])
    table["observation_id"] = (
        table.site + ":" + table.year.astype(str) + ":" + table.GlobalID
    )
    lookup = pd.Series(table.index.to_numpy(), index=table.observation_id)
    actual = flight_target_tables(inputs["compact"], waves)
    directories = [root / p for p in manifest.get("active_checkpoints", [])]
    if not directories:
        directories = sorted((root / "checkpoints").iterdir())
    if len(directories) != manifest["fit_cases"]:
        raise ValueError("Active case count drift")
    rows = []
    for directory in directories:
        details = json.loads((directory / "fit_details.json").read_text())
        membership = pd.read_parquet(directory / "memberships.parquet")
        roles = {role: set(t.GlobalID) for role, t in membership.groupby("role")}
        if (
            roles["proper_training"] & roles["test"]
            or roles.get("calibration", set()) & roles["test"]
            or roles["proper_training"] & roles.get("calibration", set())
        ):
            raise ValueError("Identity leakage")
        for inner in details["inner_memberships"]:
            if set(inner["train_ids"]) & set(inner["validation_ids"]):
                raise ValueError("Inner leakage")
            if not set(inner["train_ids"] + inner["validation_ids"]).issubset(
                roles["proper_training"]
            ):
                raise ValueError("Selection outside proper training")
        model = joblib.load(directory / "model.joblib")
        sensor = "OLI" if details["representation"] == "OLI" else "NEON"
        proper = membership[membership.role.eq("proper_training")]
        ix = lookup.loc[proper.observation_id].to_numpy()
        selected = model["select"].selected_
        np.testing.assert_allclose(
            model["scale"].mean_,
            arrays[sensor][ix][:, selected].mean(0),
            rtol=1e-12,
            atol=1e-8,
        )
        field = (
            "pft_code"
            if details["context"]["scheme"] == "inferred_pft"
            else "cover_category"
        )
        expected_f = f_classif(arrays[sensor][ix], table[field].iloc[ix])[0]
        np.testing.assert_allclose(
            model["select"].scores_,
            np.nan_to_num(expected_f, nan=-np.inf, posinf=np.finfo(float).max),
            rtol=1e-10,
            atol=1e-8,
        )
        prediction = pd.read_parquet(directory / "predictions.parquet")
        classes = np.array(json.loads(prediction.classes.iloc[0]))
        raw = np.array([json.loads(v) for v in prediction.raw_probabilities])
        calibrated = np.array(
            [json.loads(v) for v in prediction.temperature_probabilities]
        )
        from .spectral_learning import probabilities

        target_ix = lookup.loc[prediction.observation_id].to_numpy()
        if details["context"]["kind"] == "flight":
            flight = details["context"]["fold"].removeprefix("flight_")
            keys = pd.MultiIndex.from_tuples(
                [(gid, flight) for gid in prediction.GlobalID],
                names=["GlobalID", "flight_id"],
            )
            targets = actual[sensor].loc[keys].to_numpy(float)
        else:
            targets = arrays[sensor][target_ix]
        np.testing.assert_allclose(
            raw, probabilities(model, targets), atol=1e-10, rtol=1e-10
        )
        np.testing.assert_allclose(raw.sum(1), 1, atol=1e-12)
        np.testing.assert_array_equal(
            classes[raw.argmax(1)], prediction.suggested_label
        )
        summary = pd.read_csv(directory / "summary.csv")
        for kind, p in [("raw", raw), ("temperature", calibrated)]:
            s = summary[summary.probability.eq(kind)].iloc[0]
            predicted = classes[p.argmax(1)]
            truth = prediction.label.to_numpy()
            np.testing.assert_allclose(
                s.balanced_accuracy,
                balanced_accuracy_score(truth, predicted),
                atol=1e-12,
            )
            active = [c for c in classes if c in set(truth)]
            np.testing.assert_allclose(
                s.macro_F1,
                f1_score(
                    truth, predicted, labels=active, average="macro", zero_division=0
                ),
                atol=1e-12,
            )
            encoded = np.array([np.flatnonzero(classes == c)[0] for c in truth])
            np.testing.assert_allclose(
                s.Brier,
                np.mean(np.sum((p - np.eye(len(classes))[encoded]) ** 2, axis=1)),
                atol=1e-12,
            )
            matrix = confusion_matrix(truth, predicted, labels=classes)
            stored = pd.read_csv(directory / "confusion.csv")
            stored = (
                stored[stored.probability.eq(kind)]
                .pivot(index="true_label", columns="predicted_label", values="N")
                .reindex(index=classes, columns=classes)
                .to_numpy()
            )
            np.testing.assert_array_equal(matrix, stored)
        # Prediction tests are identical across every representation/model in a fold.
        rows.append(
            dict(
                **details["context"],
                representation=details["representation"],
                model=details["model"],
                test_keys=json.dumps(sorted(prediction.observation_id)),
                test_N=len(prediction),
                status="passed",
            )
        )
    checks = pd.DataFrame(rows)
    if checks.groupby(["scheme", "fold"]).test_keys.nunique().gt(1).any():
        raise ValueError("Sensor/model membership drift")
    result = dict(
        status="passed",
        fit_cases=len(rows),
        source_sha256=inputs["source_sha256"],
        numerical_metrics_independent=True,
        proper_training_scaling_and_selection=True,
        global_identity_and_inner_fold_separation=True,
        identical_paired_test_keys=True,
        saved_predictions_reproduced_from_annual_or_actual_flight_targets=True,
    )
    if destination is not None:
        write_json_atomic(Path(destination), result)
    return result
