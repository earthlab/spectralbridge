"""Independent lineage/fraction/detection checks for the dated analytics outputs."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.bulk.provenance import write_json_atomic

ROOT = Path("artifacts/plant_spectral_atlas/analytics")
OUT = Path("provenance/spectral-library-analytics/2026-10-14")
OLD = Path("provenance/mesma-readiness/2026-10-14/tables")


def validate():
    legacy = pd.read_parquet(OLD / "synthetic_mixture_truth.parquet")
    checked_targets = checked_models = 0
    for directory in sorted((ROOT / "selected_mixtures").iterdir()):
        ledger = json.loads((directory / "manifest.json").read_text())
        for name, h in ledger["outputs"].items():
            assert _file_hash(directory / name) == h
        training = pd.read_csv(directory / "training_membership.csv")
        em = pd.read_csv(directory / "endmember_membership.csv")
        assert set(em.GlobalID) <= set(training.GlobalID)
        estimates = pd.read_parquet(directory / "estimates.parquet")
        scheme, fold = estimates.scheme.iloc[0], estimates.fold.iloc[0]
        old = legacy[legacy.scheme.eq(scheme) & legacy.fold.eq(fold)].set_index(
            "mixture_id"
        )
        for sensor, g in estimates.groupby("sensor"):
            reference = old.loc[g.mixture_id]
            assert reference.source_ids.tolist() == g.source_ids.tolist()
            assert reference.true_fractions.tolist() == g.true_fractions.tolist()
            parents = set(
                k.rsplit("@", 1)[0] for ids in g.source_ids for k in ids.split("|")
            )
            assert not parents & set(training.GlobalID)
            y = np.array([list(json.loads(v).values()) for v in g.true_fractions])
            classes = list(json.loads(g.true_fractions.iloc[0]))
            p = np.array(
                [[json.loads(v)[c] for c in classes] for v in g.estimated_fractions]
            )
            assert np.isfinite(p).all() and p.min() >= -1e-9
            np.testing.assert_allclose(p.sum(1), 1, atol=1e-8)
            np.testing.assert_allclose(
                g.fraction_RMSE, np.sqrt(np.mean((p - y) ** 2, axis=1)), atol=1e-12
            )
            recovery = pd.read_csv(directory / "recovery.csv")
            for j, label in enumerate(classes):
                row = recovery[
                    recovery.sensor.eq(sensor) & recovery.label.eq(label)
                ].iloc[0]
                np.testing.assert_allclose(
                    row.fraction_RMSE,
                    np.sqrt(np.mean((p[:, j] - y[:, j]) ** 2)),
                    atol=1e-12,
                )
            detection = pd.read_csv(directory / "detection.csv")
            for row in detection[detection.sensor.eq(sensor)].itertuples(index=False):
                j = classes.index(row.label)
                ix = np.isclose(y[:, j], row.true_fraction)
                pred = p[ix, j] >= row.detection_threshold - 1e-10
                true = y[ix, j] > 0
                assert row.N == int(ix.sum())
                assert row.TP == int((pred & true).sum())
                assert row.FP == int((pred & ~true).sum())
                assert row.FN == int((~pred & true).sum())
                assert row.TN == int((~pred & ~true).sum())
            checked_targets += len(g)
            checked_models += 1
    contexts = []
    modelindex = []
    learning = json.loads((ROOT / "learning_manifest.json").read_text())
    for relative in learning["active_checkpoints"]:
        directory = ROOT / relative
        details = json.loads((directory / "fit_details.json").read_text())
        modelindex.append(
            dict(
                **details["context"],
                model=details["model"],
                representation=details["representation"],
                path=str(directory / "model.joblib"),
                sha256=_file_hash(directory / "model.joblib"),
                memberships=str(directory / "memberships.parquet"),
                memberships_sha256=_file_hash(directory / "memberships.parquet"),
                fit_details=str(directory / "fit_details.json"),
            )
        )
        if (
            details["model"] == "logistic"
            and details["representation"] == "NEON_full"
            and details["context"]["kind"] in {"plant", "site", "year"}
        ):
            frame = pd.read_parquet(directory / "memberships.parquet")
            for key, value in details["context"].items():
                frame[key] = value
            contexts.append(frame)
    memberships = pd.concat(contexts, ignore_index=True)
    pd.DataFrame(modelindex).to_csv(OUT / "models/model_index.csv", index=False)
    memberships.to_csv(OUT / "tables/primary_learning_memberships.csv", index=False)
    checked_unknown = checked_prototypes = 0
    for directory in sorted((ROOT / "extensions").iterdir()):
        ledger = json.loads((directory / "manifest.json").read_text())
        for name, h in ledger["outputs"].items():
            assert _file_hash(directory / name) == h
        unknown = pd.read_parquet(directory / "unknown_memberships.parquet")
        if len(unknown):
            for _, g in unknown.groupby(
                ["scheme", "fold", "representation", "omitted_class"]
            ):
                roles = {r: set(t.GlobalID) for r, t in g.groupby("role")}
                assert not roles["proper_training"] & roles["outer_test"]
                assert not roles["known_calibration"] & roles["outer_test"]
                assert not roles["proper_training"] & roles["known_calibration"]
                omitted = g.omitted_class.iloc[0]
                assert not g[g.role.ne("outer_test")].label.eq(omitted).any()
                checked_unknown += 1
        proto = pd.read_csv(directory / "prototype_memberships.csv")
        for (scheme, fold), g in proto.groupby(["scheme", "fold"]):
            actual = g[~g.synthesized_center]
            allowed = memberships[
                memberships.scheme.eq(scheme)
                & memberships.fold.eq(fold)
                & memberships.role.eq("proper_training")
            ]
            assert set(actual.source_GlobalID) <= set(allowed.GlobalID)
            checked_prototypes += len(actual)
    result = dict(
        status="passed",
        selected_mixture_targets=checked_targets,
        selected_mixture_representation_folds=checked_models,
        exact_saved_parent_fraction_ledgers=True,
        independent_fraction_constraint_and_RMSE_math=True,
        independent_detection_counts=True,
        withheld_class_representation_folds=checked_unknown,
        unknown_classes_absent_from_training_and_calibration=True,
        unknown_identity_roles_disjoint=True,
        observed_prototype_records=checked_prototypes,
        prototype_sources_confined_to_proper_training=True,
    )
    write_json_atomic(OUT / "manifests/secondary_validation.json", result)
    print(result)


if __name__ == "__main__":
    validate()
