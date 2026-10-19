"""Experimental integrated spectral-library analytics, with immutable inputs.

A source-specific scientific experiment, not a stable top-level package API.
Read the predeclared design before interpreting predictive or mixture outputs.
"""

from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import json
import logging
import time
import hashlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from .plant_spectral_atlas import _file_hash
from .mesma_readiness import load_compact_inputs, flight_target_tables
from .bulk.provenance import write_json_atomic, signature_sha256
from .spectral_learning import (
    LearningConfig,
    outer_folds,
    calibration_split,
    fit_training_model,
    probabilities,
    fit_temperature,
    temperature_probabilities,
    conformal_threshold,
    conformal_metrics,
    classification_metrics,
    cluster_bootstrap_accuracy,
)
from .mixtures import validate_holdout

LOG = logging.getLogger(__name__)
SCHEMES = {"inferred_pft": "pft_code", "researcher": "cover_category"}
MODELS = ["logistic", "PLSDA", "SVM", "forest", "centroid", "majority", "stratified"]
REPRESENTATIONS = [
    "NEON_full",
    "NEON_k100",
    "NEON_k50",
    "NEON_k20",
    "NEON_k10",
    "NEON_k7",
    "OLI",
]


def stable_seed(name, seed=20261014):
    """Derive a deterministic 32-bit-compatible random seed from a name and base seed."""

    return (seed + int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)) % (2**32 - 1)


def load_analytics_inputs(source, compact, output):
    """Verify upstream compact ownership, write only metadata/reference index."""
    source, compact, output = Path(source), Path(compact), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    analysis = compact.parent
    ledger = json.loads((analysis / "statistics_manifest.json").read_text())
    if _file_hash(source) != ledger["identity"]["source"]:
        raise ValueError("Source differs from paired canonical analysis")
    for name, expected in ledger["outputs"].items():
        if _file_hash(analysis / name) != expected:
            raise ValueError("Changed canonical input: " + name)
    table, values, waves = load_compact_inputs(source, compact)
    table = table.copy()
    table["observation_id"] = (
        table.site + ":" + table.year.astype(str) + ":" + table.GlobalID
    )
    if table.observation_id.duplicated().any():
        raise ValueError("Duplicate analytic key")
    table["paired_zero_norm"] = np.any(
        np.column_stack([np.linalg.norm(v, axis=1) <= 0 for v in values.values()]),
        axis=1,
    )
    table["NEON_negative_coordinates"] = (values["NEON"] < 0).sum(1)
    table["NEON_zero_coordinates"] = (values["NEON"] == 0).sum(1)
    grids = pd.read_csv(compact / "corr/flight_source_grids.csv")
    lookup = grids.set_index(["flight_id", "source_image"]).grid_id.to_dict()

    def native_grids(history):
        exposures = [tuple(json.loads(x)) for x in json.loads(history)]
        if any(x not in lookup for x in exposures):
            raise ValueError("Unresolved native grid exposure")
        return json.dumps(sorted(set(lookup[x] for x in exposures)))

    table["native_grid_ids"] = table.flight_history.map(native_grids)
    index = table.drop(columns="flights").copy()
    index["spectra_reference"] = table.observation_id
    index["NEON_source"] = "compact/corr_polygon_year.parquet"
    index["OLI_source"] = "compact/olioli_undarkened_polygon_year.parquet"
    index_path = output / "canonical_analysis_index.parquet"
    if not index_path.exists() or not pd.read_parquet(index_path).equals(index):
        index.to_parquet(index_path, index=False)
    summary = dict(
        pixel_rows=pq.ParquetFile(source).metadata.num_rows,
        identities=table.GlobalID.nunique(),
        polygon_years=len(table),
        sites=table.site.nunique(),
        years=table.year.nunique(),
        flights=table.flights.explode().nunique(),
        species_recorded=table.species.dropna().nunique(),
        species_missing_identities=table[table.species.isna()].GlobalID.nunique(),
        inferred_assigned_identities=table[
            table.pft_code.ne("UNASSIGNED")
        ].GlobalID.nunique(),
        inferred_unassigned_identities=table[
            table.pft_code.eq("UNASSIGNED")
        ].GlobalID.nunique(),
        cover_categories=table.cover_category.nunique(),
        native_grids=grids.grid_id.nunique(),
        common_NEON_coordinates=len(waves["NEON"]),
        OLI_channels=len(waves["OLI"]),
        paired_zero_norm_rows=int(table.paired_zero_norm.sum()),
    )
    summary_path = output / "library_summary.csv"
    summary_text = pd.DataFrame(
        [dict(quantity=k, value=v) for k, v in summary.items()]
    ).to_csv(index=False)
    if not summary_path.exists() or summary_path.read_text() != summary_text:
        summary_path.write_text(summary_text)
    metadata = dict(
        source=str(source.resolve()),
        source_sha256=_file_hash(source),
        canonical_manifest_sha256=_file_hash(analysis / "statistics_manifest.json"),
        summary=summary,
        compact=str(compact.resolve()),
        units="native stored units; physical scale unresolved",
        MicaSense_status="blocked_unverified_coordinates",
    )
    identity_path = output / "input_identity.json"
    if not identity_path.exists() or json.loads(identity_path.read_text()) != metadata:
        write_json_atomic(identity_path, metadata)
    actual = flight_target_tables(compact, waves)
    return table, values, waves, actual, metadata


def scheme_data(table, values, field):
    """Subset paired arrays to assigned, nonmissing labels with nonzero spectral support."""

    eligible = (
        ~table[field].isna() & ~table[field].eq("UNASSIGNED") & ~table.paired_zero_norm
    )
    t = table.loc[eligible].copy().reset_index(drop=True)
    t["label"] = t[field]
    arrays = {k: v[eligible.to_numpy()] for k, v in values.items()}
    return t, arrays


def fold_support(table, train, test, config):
    """Report per-label training/test identity counts and explicit closed/open/insufficient-support statuses."""

    tr = table.loc[train].groupby("label").GlobalID.nunique()
    te = table.loc[test].groupby("label").GlobalID.nunique()
    records = []
    for label in sorted(table.label.unique()):
        ntr, nte = int(tr.get(label, 0)), int(te.get(label, 0))
        status = (
            "absent_training_open_set"
            if ntr == 0 and nte > 0
            else "insufficient_training_support"
            if ntr < config.minimum_train
            else "insufficient_test_support"
            if nte < config.minimum_test
            else "closed_evaluable"
        )
        records.append(
            dict(label=label, train_identities=ntr, test_identities=nte, status=status)
        )
    return pd.DataFrame(records)


def prepare_fold(table, arrays, actual, fold, kind, train, test, config):
    """Class support/calibration gates, using actual flight targets when required."""
    support = fold_support(table, train, test, config)
    known = support.loc[
        support.train_identities.ge(config.minimum_train), "label"
    ].tolist()
    evaluable = support.loc[support.status.eq("closed_evaluable"), "label"].tolist()
    train = train & table.label.isin(known).to_numpy()
    target = test & table.label.isin(evaluable).to_numpy()
    if len(known) < 2 or len(evaluable) < 2:
        return None, support, "insufficient_multiclass_support"
    train_ix, test_ix = np.flatnonzero(train), np.flatnonzero(target)
    seed = stable_seed(fold, config.seed)
    proper, cal = calibration_split(
        table.GlobalID.iloc[train_ix], fraction=config.calibration_fraction, seed=seed
    )
    classes = set(known)
    calibration_status = "independent_training_identity_calibration"
    if (
        set(table.label.iloc[train_ix[proper]]) != classes
        or table.iloc[train_ix[proper]].groupby("label").GlobalID.nunique().min() < 3
        or table.GlobalID.iloc[train_ix[cal]].nunique() < config.minimum_calibration
    ):
        proper = np.ones(len(train_ix), bool)
        cal = ~proper
        calibration_status = "unavailable_insufficient_class_or_identity_support"
    proper_ix, cal_ix = train_ix[proper], train_ix[cal]
    maskp, maskc = np.zeros(len(table), bool), np.zeros(len(table), bool)
    maskp[proper_ix], maskc[cal_ix] = True, True
    validate_holdout(table.GlobalID, maskp, maskc)
    validate_holdout(table.GlobalID, maskp, test)
    validate_holdout(table.GlobalID, maskc, test)
    test_arrays = {k: v[test_ix] for k, v in arrays.items()}
    if kind == "flight":
        flight = fold.removeprefix("flight_")
        keys = pd.MultiIndex.from_tuples(
            [(table.GlobalID.iloc[i], flight) for i in test_ix],
            names=["GlobalID", "flight_id"],
        )
        test_arrays = {k: actual[k].loc[keys].to_numpy(float) for k in arrays}
        if any(not np.isfinite(x).all() for x in test_arrays.values()):
            raise ValueError("Missing actual flight target")
    return (
        dict(
            proper=proper_ix,
            calibration=cal_ix,
            test=test_ix,
            test_arrays=test_arrays,
            seed=seed,
            calibration_status=calibration_status,
            known_classes=sorted(known),
            evaluable_classes=sorted(evaluable),
        ),
        support,
        "eligible",
    )


def representation_values(arrays, representation):
    """Decode a representation name into its NEON/OLI sensor and feature budget; the arrays argument is retained but unused."""

    sensor = "OLI" if representation == "OLI" else "NEON"
    k = (
        "all"
        if representation in {"NEON_full", "OLI"}
        else int(representation.split("_k")[1])
    )
    return sensor, k


def fit_predict_case(
    table,
    arrays,
    waves,
    prepared,
    context,
    representation,
    model_name,
    root,
    identity,
    config,
):
    """One owned restartable fit; no final-test labels influence fitting choices."""
    import joblib

    key = signature_sha256(
        dict(
            context=context,
            representation=representation,
            model=model_name,
            identity=identity,
        )
    )[:24]
    directory = Path(root) / "checkpoints" / key
    directory.mkdir(parents=True, exist_ok=True)
    ledger = directory / "manifest.json"
    if ledger.exists():
        m = json.loads(ledger.read_text())
        if all(_file_hash(directory / p) == h for p, h in m["outputs"].items()):
            return directory
        raise ValueError("Changed analytic checkpoint: " + key)
    started = time.monotonic()
    sensor, k = representation_values(arrays, representation)
    proper, cal, test = [prepared[x] for x in ["proper", "calibration", "test"]]
    model, fit = fit_training_model(
        arrays[sensor][proper],
        table.label.iloc[proper],
        table.GlobalID.iloc[proper],
        model_name,
        k=k,
        seed=prepared["seed"],
        inner_folds=config.inner_folds,
    )
    classes = np.asarray(model.classes_)
    truth = table.label.iloc[test].to_numpy()
    ids = table.GlobalID.iloc[test].to_numpy()
    target = prepared["test_arrays"][sensor]
    p = probabilities(model, target)
    encoded = np.array([np.flatnonzero(classes == v)[0] for v in truth])
    temperature, threshold = 1.0, np.nan
    if len(cal):
        pc = probabilities(model, arrays[sensor][cal])
        yc = np.array([np.flatnonzero(classes == v)[0] for v in table.label.iloc[cal]])
        temperature = fit_temperature(pc, yc)
        # RAW score function was fitted independently of calibration labels.
        threshold = conformal_threshold(
            pc, yc, table.GlobalID.iloc[cal], config.conformal_alpha
        )
    calibrated = temperature_probabilities(p, temperature)
    common = dict(
        **context,
        representation=representation,
        model=model_name,
        calibration_status=prepared["calibration_status"],
        proper_training_rows=len(proper),
        proper_training_identities=table.GlobalID.iloc[proper].nunique(),
        calibration_identities=table.GlobalID.iloc[cal].nunique(),
        test_rows=len(test),
        test_identities=len(np.unique(ids)),
        temperature=temperature,
        conformal_threshold=threshold,
        feature_count=len(model["select"].selected_),
        tuning_status=fit["status"],
    )
    summaries, perclass, confusions, reliability = [], [], [], []
    for kind, prob in [("raw", p), ("temperature", calibrated)]:
        summary, by_class, matrix, bins = classification_metrics(truth, prob, classes)
        bootstrap = cluster_bootstrap_accuracy(
            truth,
            classes[prob.argmax(1)],
            ids,
            classes,
            replicates=config.bootstraps,
            seed=prepared["seed"],
        )
        summary.update(
            common,
            probability=kind,
            BA_lo=float(np.quantile(bootstrap, 0.025)),
            BA_hi=float(np.quantile(bootstrap, 0.975)),
        )
        if kind == "raw" and len(cal):
            summary.update(conformal_metrics(p, encoded, ids, threshold))
        summaries.append(summary)
        for row in by_class:
            perclass.append(dict(**common, probability=kind, **row))
        for i, a in enumerate(classes):
            for j, b in enumerate(classes):
                confusions.append(
                    dict(
                        **context,
                        representation=representation,
                        model=model_name,
                        probability=kind,
                        true_label=a,
                        predicted_label=b,
                        N=int(matrix[i, j]),
                    )
                )
        for row in bins:
            reliability.append(
                dict(
                    **context,
                    representation=representation,
                    model=model_name,
                    probability=kind,
                    **row,
                )
            )
    prediction = table.iloc[test][
        ["observation_id", "GlobalID", "site", "year", "label"]
    ].copy()
    prediction["suggested_label"] = classes[p.argmax(1)]
    prediction["raw_probabilities"] = [json.dumps(x.tolist()) for x in p]
    prediction["temperature_probabilities"] = [
        json.dumps(x.tolist()) for x in calibrated
    ]
    prediction["classes"] = json.dumps(classes.tolist())
    prediction["raw_nonconformity_true"] = 1 - p[np.arange(len(p)), encoded]
    prediction["prediction_set_size"] = (
        (1 - p <= threshold + 1e-12).sum(1) if len(cal) else -1
    )
    prediction["calibration_status"] = prepared["calibration_status"]
    prediction["conformal_available"] = bool(len(cal))
    prediction["prediction_set_covered"] = (
        (1 - p[np.arange(len(p)), encoded] <= threshold + 1e-12) if len(cal) else False
    )
    for column, value in dict(
        **context, representation=representation, model=model_name
    ).items():
        prediction[column] = value
    prediction.to_parquet(directory / "predictions.parquet", index=False)
    pd.DataFrame(summaries).to_csv(directory / "summary.csv", index=False)
    pd.DataFrame(perclass).to_csv(directory / "class_metrics.csv", index=False)
    pd.DataFrame(confusions).to_csv(directory / "confusion.csv", index=False)
    pd.DataFrame(reliability).to_csv(directory / "reliability.csv", index=False)
    positions = model["select"].selected_
    selection = pd.DataFrame(
        dict(
            wavelength_nm=waves[sensor],
            F_score=model["select"].scores_,
            selected=np.isin(np.arange(len(waves[sensor])), positions),
        )
    )
    for column, value in dict(
        **context, representation=representation, model=model_name
    ).items():
        selection[column] = value
    selection.to_csv(directory / "selection.csv", index=False)
    coefficient_rows = []
    estimator = model["model"]
    coefficient = getattr(estimator, "coef_", None)
    loading = None
    if model_name == "PLSDA":
        coefficient = estimator.regressor_.coef_
        loading = np.linalg.norm(estimator.regressor_.x_loadings_, axis=1)
        fit["effective_PLS_components"] = estimator.regressor_.n_components
    if coefficient is not None:
        coefficient = np.asarray(coefficient)
        if coefficient.shape[1] != len(positions) and coefficient.shape[0] == len(
            positions
        ):
            coefficient = coefficient.T
        if coefficient.shape[1] != len(positions):
            raise ValueError("Coefficient wavelength alignment failed")
        labels = (
            classes
            if len(coefficient) == len(classes)
            else [str(classes[1]) + "_minus_" + str(classes[0])]
        )
        for label, curve in zip(labels, coefficient):
            for j, position in enumerate(positions):
                coefficient_rows.append(
                    dict(
                        **context,
                        representation=representation,
                        model=model_name,
                        label=label,
                        wavelength_nm=waves[sensor][position],
                        coefficient=curve[j],
                        PLS_loading_norm=loading[j] if loading is not None else np.nan,
                    )
                )
    columns = [
        *context,
        "representation",
        "model",
        "label",
        "wavelength_nm",
        "coefficient",
        "PLS_loading_norm",
    ]
    pd.DataFrame(coefficient_rows, columns=columns).to_csv(
        directory / "coefficients.csv", index=False
    )
    model_path = directory / "model.joblib"
    joblib.dump(model, model_path, compress=3)
    membership = []
    for role, indices in [
        ("proper_training", proper),
        ("calibration", cal),
        ("test", test),
    ]:
        part = table.iloc[indices][
            ["observation_id", "GlobalID", "site", "year", "label"]
        ].copy()
        part["role"] = role
        membership.append(part)
    pd.concat(membership).to_parquet(directory / "memberships.parquet", index=False)
    write_json_atomic(
        directory / "fit_details.json",
        dict(
            **fit,
            elapsed_seconds=time.monotonic() - started,
            context=context,
            representation=representation,
            model=model_name,
            identity=identity,
        ),
    )
    outputs = {
        p.name: _file_hash(p)
        for p in directory.iterdir()
        if p.is_file() and p != ledger
    }
    write_json_atomic(ledger, dict(status="complete", outputs=outputs))
    return directory


def profile_learning(source, compact, output, config=None):
    """Profile declared models without computing or inspecting outer-test scores."""
    config = config or LearningConfig()
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    table, values, waves, actual, identity = load_analytics_inputs(
        source, compact, root
    )
    t, a = scheme_data(table, values, "pft_code")
    fold, kind, train, test = next(
        x for x in outer_folds(t, config) if x[0] == "plant_0"
    )
    prepared, support, status = prepare_fold(
        t, a, actual, fold, kind, train, test, config
    )
    if status != "eligible":
        raise ValueError("Initial profiling fold lacks support")
    rows = []
    for name in MODELS:
        LOG.info(
            "Profile proper-training-only %s N=%s B=%s",
            name,
            len(prepared["proper"]),
            a["NEON"].shape[1],
        )
        started = time.monotonic()
        ix = prepared["proper"]
        _, record = fit_training_model(
            a["NEON"][ix],
            t.label.iloc[ix],
            t.GlobalID.iloc[ix],
            name,
            seed=prepared["seed"],
            inner_folds=config.inner_folds,
        )
        rows.append(
            dict(
                model=name,
                seconds=time.monotonic() - started,
                training_rows=len(ix),
                features=a["NEON"].shape[1],
                tuning_status=record["status"],
                warning_count=len(record["warnings"]),
            )
        )
        pd.DataFrame(rows).to_csv(root / "computational_profile.csv", index=False)
    return pd.DataFrame(rows)


def run_learning(source, compact, output, *, config=None, first_pass=False, workers=2):
    """Run declared classical models/representations with per-fit restart checks.

    All-flight diagnostics use logistic/full/OLI. Plant/site/year comparisons use
    all model baselines at full/OLI plus logistic selected-coordinate curves.
    No ordinary pixel-level observations are materialized.
    """
    import sklearn
    from concurrent.futures import ThreadPoolExecutor, as_completed

    config = config or LearningConfig()
    if (
        config.minimum_train < 2
        or config.minimum_test < 1
        or config.bootstraps < 19
        or workers < 1
    ):
        raise ValueError("Invalid independent-support or compute settings")
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    table, values, waves, actual, input_identity = load_analytics_inputs(
        source, compact, root
    )
    identity = dict(
        inputs=input_identity,
        config=asdict(config),
        code=_file_hash(__file__),
        learning_code=_file_hash(Path(__file__).with_name("spectral_learning.py")),
        numpy=np.__version__,
        pandas=pd.__version__,
        sklearn=sklearn.__version__,
    )
    manifest_path = root / "learning_manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if (
            old["identity"] == identity
            and old["request"] == dict(first_pass=first_pass)
            and all(
                (root / name).is_file() and _file_hash(root / name) == expected
                for name, expected in old["outputs"].items()
            )
        ):
            LOG.info(
                "Reusing complete learning run (%s owned outputs)", len(old["outputs"])
            )
            return old
    supports, cases = [], []
    for scheme, field in SCHEMES.items():
        if first_pass and scheme != "inferred_pft":
            continue
        t, arrays = scheme_data(table, values, field)
        for fold, kind, train, test in outer_folds(t, config):
            if first_pass and fold != "plant_0":
                continue
            prepared, support, status = prepare_fold(
                t, arrays, actual, fold, kind, train, test, config
            )
            support = support.assign(
                scheme=scheme, fold=fold, kind=kind, fold_status=status
            )
            supports.append(support)
            if prepared is None:
                continue
            context = dict(scheme=scheme, fold=fold, kind=kind)
            models = ["logistic"] if kind in {"flight", "within_site_year"} else MODELS
            for representation in ["NEON_full", "OLI"]:
                for model in models:
                    cases.append((t, arrays, prepared, context, representation, model))
            if kind not in {"flight", "within_site_year"}:
                for representation in REPRESENTATIONS[1:-1]:
                    cases.append(
                        (t, arrays, prepared, context, representation, "logistic")
                    )
    pd.concat(supports, ignore_index=True).to_csv(
        root / "fold_support.csv", index=False
    )
    write_json_atomic(
        root / "run_plan.json",
        dict(
            fit_cases=len(cases),
            workers=workers,
            by_model=pd.Series([c[-1] for c in cases]).value_counts().to_dict(),
            by_kind=pd.Series([c[3]["kind"] for c in cases]).value_counts().to_dict(),
            first_pass=first_pass,
        ),
    )
    profile = root / "computational_profile.csv"
    if profile.exists():
        seconds = pd.read_csv(profile).set_index("model").seconds.to_dict()
        estimate = sum(seconds.get(c[-1], 0) for c in cases)
        LOG.info(
            "Conservative proper-training profile budget %.1f CPU-min / %s workers; %s fit cases",
            estimate / 60,
            workers,
            len(cases),
        )
    started = time.monotonic()
    completed = []

    def fit_case(case):
        t, arrays, prepared, context, representation, model = case
        LOG.info(
            "Fit %s %s %s %s", context["scheme"], context["fold"], representation, model
        )
        return fit_predict_case(
            t,
            arrays,
            waves,
            prepared,
            context,
            representation,
            model,
            root,
            identity,
            config,
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(fit_case, case): case for case in cases}
        for future in as_completed(pending):
            completed.append(future.result())
            LOG.info(
                "Learning completed %s/%s fits; %.1f min elapsed",
                len(completed),
                len(cases),
                (time.monotonic() - started) / 60,
            )
    completed = sorted(completed)
    for filename in [
        "summary.csv",
        "class_metrics.csv",
        "confusion.csv",
        "reliability.csv",
        "selection.csv",
        "coefficients.csv",
    ]:
        frames = [pd.read_csv(path / filename) for path in completed]
        pd.concat(frames, ignore_index=True).to_csv(root / filename, index=False)
    for filename in ["predictions.parquet", "memberships.parquet"]:
        pd.concat(
            [pd.read_parquet(path / filename) for path in completed], ignore_index=True
        ).to_parquet(root / filename, index=False)
    files = [p for p in root.rglob("*") if p.is_file() and p != manifest_path]
    manifest = dict(
        status="first_pass_complete" if first_pass else "complete",
        identity=identity,
        request=dict(first_pass=first_pass),
        fit_cases=len(cases),
        active_checkpoints=[str(p.relative_to(root)) for p in completed],
        outputs={str(p.relative_to(root)): _file_hash(p) for p in sorted(files)},
    )
    write_json_atomic(manifest_path, manifest)
    return manifest
