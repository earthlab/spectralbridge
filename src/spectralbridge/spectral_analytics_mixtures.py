"""Paired selected-coordinate counterparts of the saved synthetic mixture audit.

Exact saved parents, fractions, folds and EAR candidates are reused. No new
independent abundance truth is introduced. Coordinates use equal-channel RMSE;
legacy full NEON retains its disconnected-grid quadrature metric.
"""

from pathlib import Path
import json
import logging
import numpy as np
import pandas as pd
from .spectral_library_analytics import load_analytics_inputs
from .spectral_learning import StableFSelector
from .spectral_analytics_extensions import checkpoint
from .plant_spectral_atlas import _file_hash
from .pft_method_audit import wavelength_weights
from .mixtures import fit_models, detection_metrics

LOG = logging.getLogger(__name__)


def reconstruct_saved_mixtures(records, index, spectra, labels):
    """Reconstruct saved linear targets from explicit identity/year parents."""
    targets, truth = [], []
    classes = sorted(set(labels.values()))
    for row in records.itertuples(index=False):
        weights = json.loads(row.true_fractions)
        sources = row.source_ids.split("|")
        source_labels = [labels[k] for k in sources]
        if len(set(source_labels)) != len(sources):
            raise ValueError("Saved parents must have distinct class labels")
        if not np.isclose(sum(weights.values()), 1) or min(weights.values()) < 0:
            raise ValueError("Invalid saved fractions")
        targets.append(sum(weights[labels[k]] * spectra[index[k]] for k in sources))
        truth.append([weights.get(c, 0) for c in classes])
    return np.asarray(targets), np.asarray(truth), np.asarray(classes)


def run_selected_mixtures(source, compact, root, previous):
    """Run the retained selected-endmember mixture sensitivity study using verified prior truth and fold membership."""

    root, previous = Path(root), Path(previous)
    table, arrays, waves, actual, metadata = load_analytics_inputs(
        source, compact, root
    )
    truth = pd.read_parquet(previous / "synthetic_mixture_truth.parquet")
    membership = pd.read_parquet(previous / "fold_membership.parquet")
    selected = pd.read_csv(previous / "selected_endmember_membership.csv")
    selected = selected[selected.selected_method.eq("EAR")]
    baseline = pd.read_parquet(previous / "abundance_estimates.parquet")
    baseline = baseline[baseline.sensor.eq("NEON") & baseline.method.eq("EAR_MESMA3")]
    keys = table.GlobalID.astype(str) + "@" + table.year.astype(str)
    index = dict(zip(keys, range(len(table))))
    identity = dict(
        source_sha256=metadata["source_sha256"],
        code_sha256=_file_hash(Path(__file__)),
        truth_sha256=_file_hash(previous / "synthetic_mixture_truth.parquet"),
        candidates_sha256=_file_hash(previous / "selected_endmember_membership.csv"),
        selected_counts=[100, 50, 20, 10, 7],
    )
    directories = []
    validated = set()
    for (scheme, fold, kind), records in truth.groupby(
        ["scheme", "fold", "kind"], sort=False
    ):
        # Material subclasses remain descriptive in the reused audit; new controlled
        # sensor experiment follows the two primary biological label schemes.
        if scheme not in {"inferred_pft", "researcher"}:
            continue
        members = membership[
            membership.scheme.eq(scheme) & membership.fold.eq(fold)
        ].drop_duplicates(["GlobalID", "year"])
        members = members.assign(
            key=members.GlobalID.astype(str) + "@" + members.year.astype(str)
        )
        labels = dict(zip(members.key, members.label))
        em = selected[selected.scheme.eq(scheme) & selected.fold.eq(fold)]
        emkeys = em.GlobalID.astype(str) + "@" + em.year.astype(str)
        emix = np.array([index[k] for k in emkeys])
        emlabels = em.label.to_numpy()
        train = members[members.role.eq("train")]
        trainix = np.array([index[k] for k in train.key])
        if set(train.GlobalID) & set(members[members.role.eq("test")].GlobalID):
            raise ValueError("Legacy mixture identity leak")
        scale = float(em.training_scale_stored_units.iloc[0])
        X = arrays["NEON"] / scale
        if kind == "flight":
            X = X.copy()
            flight = fold.removeprefix("flight_")
            for k in set("|".join(records.source_ids).split("|")):
                gid = k.rsplit("@", 1)[0]
                X[index[k]] = actual["NEON"].loc[(gid, flight)].to_numpy() / scale
        targets, true, classes = reconstruct_saved_mixtures(records, index, X, labels)

        def action(directory):
            summaries, detection, estimates, selections = [], [], [], []
            if kind == "plant" and scheme not in validated:
                weight = np.sqrt(wavelength_weights(waves["NEON"]) * X.shape[1])
                fit = fit_models(targets * weight, emlabels, X[emix] * weight)
                ref = baseline[
                    baseline.scheme.eq(scheme) & baseline.fold.eq(fold)
                ].sort_values("mixture_id")
                expected = np.array(
                    [
                        [json.loads(v).get(c, 0) for c in classes]
                        for v in ref.estimated_fractions
                    ]
                )
                order = [np.where(fit["classes"] == c)[0][0] for c in classes]
                np.testing.assert_allclose(
                    fit["fractions"][:, order], expected, atol=2e-7, rtol=1e-7
                )
                np.testing.assert_allclose(
                    fit["RMSE"], ref.reconstruction_RMSE, atol=1e-8
                )
                (directory / "legacy_reproduction.json").write_text(
                    json.dumps(
                        dict(
                            status="passed",
                            rows=len(ref),
                            maximum_fraction_difference=float(
                                np.max(np.abs(fit["fractions"][:, order] - expected))
                            ),
                        )
                    )
                )
            for count in [100, 50, 20, 10, 7]:
                selector = StableFSelector(count).fit(
                    X[trainix], train.label.to_numpy()
                )
                positions = selector.selected_
                fit = fit_models(targets[:, positions], emlabels, X[emix][:, positions])
                order = [np.where(fit["classes"] == c)[0][0] for c in classes]
                fractions = fit["fractions"][:, order]
                context = dict(
                    scheme=scheme,
                    fold=fold,
                    kind=kind,
                    sensor=f"NEON_k{count}",
                    method="EAR_MESMA3",
                )
                selections.extend(
                    dict(**context, wavelength_nm=waves["NEON"][p]) for p in positions
                )
                for j, c in enumerate(classes):
                    delta = fractions[:, j] - true[:, j]
                    summaries.append(
                        dict(
                            **context,
                            label=c,
                            N=len(true),
                            fraction_bias=float(delta.mean()),
                            fraction_MAE=float(np.abs(delta).mean()),
                            fraction_RMSE=float(np.sqrt(np.mean(delta**2))),
                            mean_reconstruction_RMSE=float(fit["RMSE"].mean()),
                            class_set_error=float(
                                np.any(
                                    (fractions >= 0.1) != (true >= 0.1), axis=1
                                ).mean()
                            ),
                            negative_fraction_count=int((fractions < -1e-9).sum()),
                            sum_violation_count=int(
                                (np.abs(fractions.sum(1) - 1) > 1e-8).sum()
                            ),
                            model_count=fit["model_count"],
                        )
                    )
                    for threshold in [0.05, 0.1, 0.2]:
                        for fraction in np.unique(np.round(true[:, j], 8)):
                            ix = np.isclose(true[:, j], fraction)
                            counts = detection_metrics(
                                true[ix, j], fractions[ix, j], threshold=threshold
                            )
                            detection.append(
                                dict(
                                    **context,
                                    label=c,
                                    true_fraction=fraction,
                                    detection_threshold=threshold,
                                    **counts,
                                    probability=(counts["TP"] + counts["FP"])
                                    / counts["N"],
                                    interpretation="conditional_saved_parent_trajectories_not_independent_draws",
                                )
                            )
                for i, row in enumerate(records.itertuples(index=False)):
                    estimates.append(
                        dict(
                            **context,
                            mixture_id=row.mixture_id,
                            source_ids=row.source_ids,
                            true_fractions=row.true_fractions,
                            estimated_fractions=json.dumps(
                                dict(zip(classes, fractions[i].tolist()))
                            ),
                            fraction_RMSE=float(
                                np.sqrt(np.mean((fractions[i] - true[i]) ** 2))
                            ),
                            reconstruction_RMSE=float(fit["RMSE"][i]),
                            near_compositions=int(fit["near_compositions"][i]),
                            max_near_fraction_range=float(
                                fit["near_fraction_range"][i].max()
                            ),
                        )
                    )
            pd.DataFrame(summaries).to_csv(directory / "recovery.csv", index=False)
            pd.DataFrame(detection).to_csv(directory / "detection.csv", index=False)
            pd.DataFrame(estimates).to_parquet(
                directory / "estimates.parquet", index=False
            )
            pd.DataFrame(selections).to_csv(directory / "selection.csv", index=False)
            train.to_csv(directory / "training_membership.csv", index=False)
            em.to_csv(directory / "endmember_membership.csv", index=False)

        LOG.info(
            "Paired selected mixtures %s %s (%s targets)", scheme, fold, len(records)
        )
        directory = checkpoint(
            root / "selected_mixtures" / f"{scheme}_{fold}", identity, action
        )
        directories.append(directory)
        if (directory / "legacy_reproduction.json").exists():
            validated.add(scheme)
    for name in ["recovery", "detection", "selection"]:
        pd.concat(
            [pd.read_csv(d / f"{name}.csv") for d in directories], ignore_index=True
        ).to_csv(root / f"selected_mixture_{name}.csv", index=False)
    return directories
