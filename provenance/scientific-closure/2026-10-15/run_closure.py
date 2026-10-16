"""Only the missing closure analyses; canonical completed fits stay immutable."""

from pathlib import Path
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import json
import numpy as np
import pandas as pd
from spectralbridge.spectral_closure import (
    cluster_rate_intervals,
    closure_labels,
    spectral_shape,
    paired_partition,
    paired_partition_bootstrap,
    one_vs_rest_metrics,
)
from spectralbridge.spectral_learning import (
    LearningConfig,
    outer_folds,
    classification_metrics,
    cluster_bootstrap_accuracy,
)
from spectralbridge.spectral_library_analytics import (
    load_analytics_inputs,
    scheme_data,
    prepare_fold,
    fit_predict_case,
    stable_seed,
)
from spectralbridge.pft_method_audit import wavelength_weights
from spectralbridge.plant_spectral_atlas import _file_hash
from spectralbridge.bulk.provenance import write_json_atomic

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
ROOT = REPO / "artifacts/plant_spectral_atlas/closure_20261015"
PRIOR = REPO / "provenance/spectral-library-analytics/2026-10-14"
LEVELS = [
    "species_level",
    "researcher_level",
    "narrow_pft",
    "broad_pft",
    "coarse_cover",
]
LOG = logging.getLogger(__name__)


def save(frame, name):
    frame.to_csv(BASE / "tables" / name, index=False)


def run():
    config = LearningConfig()
    source = REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    compact = REPO / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact"
    table, arrays, waves, actual, metadata = load_analytics_inputs(
        source, compact, ROOT
    )
    table = closure_labels(table)
    weights = {
        "NEON": wavelength_weights(waves["NEON"]),
        "OLI": np.ones(len(waves["OLI"])) / len(waves["OLI"]),
    }
    identity = dict(
        source=metadata,
        config=asdict(config),
        code=_file_hash(__file__),
        helpers=_file_hash(REPO / "src/spectralbridge/spectral_closure.py"),
        learner=_file_hash(REPO / "src/spectralbridge/spectral_learning.py"),
        fitter=_file_hash(REPO / "src/spectralbridge/spectral_library_analytics.py"),
    )
    ledger = ROOT / "closure_manifest.json"
    if ledger.exists():
        old = json.loads(ledger.read_text())
        if old["identity"] != identity:
            raise ValueError(
                "Closure configuration changed: use a new output directory"
            )
        for name, h in old["outputs"].items():
            if _file_hash(REPO / name) != h:
                raise ValueError("Changed closure output " + name)
        LOG.info("Reused complete closure: %s fits", old["fit_cases"])
        return old
    support = []
    for level in LEVELS:
        s = (
            table[table[level].notna()]
            .groupby(["site", "year", level])
            .agg(
                identities=("GlobalID", "nunique"),
                polygon_years=("GlobalID", "size"),
                flight_observations=("flight_observations", "sum"),
            )
            .reset_index()
            .rename(columns={level: "label"})
        )
        s["level"] = level
        support.append(s)
    save(pd.concat(support, ignore_index=True), "observational_support.csv")
    # Acquisition IDs are source flight/flightline products, not independent sites.
    flight = table[["GlobalID", "site", "year", "flights"]].explode("flights")
    save(
        flight.groupby(["site", "year", "flights"])
        .GlobalID.nunique()
        .rename("unique_polygon_ids")
        .reset_index(),
        "flight_support.csv",
    )
    products = []
    for sensor, X in arrays.items():
        products.append(
            dict(
                product=sensor,
                polygon_years=len(X),
                identities=table.GlobalID.nunique(),
                coordinates=X.shape[1],
                status="paired canonical product; OLI synthetic"
                if sensor == "OLI"
                else "corrected common support",
            )
        )
    products.append(
        dict(
            product="MicaSense",
            status="physical coordinates unverified; no new inference",
        )
    )
    save(pd.DataFrame(products), "product_support.csv")
    save(
        table.groupby("GlobalID")
        .agg(
            site=("site", "first"),
            years=("year", "nunique"),
            annual_rows=("year", "size"),
            flight_observations=("flight_observations", "sum"),
        )
        .reset_index(),
        "identity_sampling.csv",
    )
    temporal = []
    pairs = []
    label_audit = []
    for site, g in table.groupby("site"):
        years = sorted(g.year.unique())
        if len(years) != 2:
            continue
        first = g[g.year.eq(years[0])].set_index("GlobalID")
        second = g[g.year.eq(years[1])].set_index("GlobalID")
        shared = first.index.intersection(second.index).sort_values()
        a = first.loc[shared]
        b = second.loc[shared]
        for level in LEVELS:
            valid = a[level].notna() & b[level].notna() & a[level].eq(b[level])
            counts = a.loc[valid, level].value_counts()
            valid &= a[level].isin(counts[counts >= 3].index)
            label_audit.append(
                dict(
                    site=site,
                    level=level,
                    total_pairs=len(shared),
                    stable_supported_pairs=int(valid.sum()),
                    missing_or_changed_or_under3=int((~valid).sum()),
                    changed_labels=int(
                        (
                            a[level].notna() & b[level].notna() & a[level].ne(b[level])
                        ).sum()
                    ),
                )
            )
            if valid.sum() < 3 or a.loc[valid, level].nunique() < 2:
                continue
            ai = a.loc[valid].index
            ia = table.index[
                table.GlobalID.isin(ai) & table.year.eq(years[0]) & table.site.eq(site)
            ]
            ib = table.set_index(["GlobalID", "year"]).index.get_indexer(
                [(table.GlobalID.iloc[i], years[1]) for i in ia]
            )
            labels = table[level].iloc[ia].to_numpy()
            for sensor in ["NEON", "OLI"]:
                X, Y = arrays[sensor][ia], arrays[sensor][ib]
                for mode in ["stored", "shape"]:
                    A, B = X, Y
                    if mode == "shape":
                        A, _ = spectral_shape(X, weights[sensor])
                        B, _ = spectral_shape(Y, weights[sensor])
                    result = paired_partition(A, B, labels, weights[sensor])
                    result.update(
                        paired_partition_bootstrap(A, B, labels, weights[sensor])
                    )
                    temporal.append(
                        dict(
                            site=site,
                            first_year=int(years[0]),
                            second_year=int(years[1]),
                            level=level,
                            sensor=sensor,
                            mode=mode,
                            **result,
                        )
                    )
                    for k, i in enumerate(ia):
                        pairs.append(
                            dict(
                                site=site,
                                GlobalID=table.GlobalID.iloc[i],
                                level=level,
                                label=labels[k],
                                sensor=sensor,
                                mode=mode,
                                first_year=int(years[0]),
                                second_year=int(years[1]),
                                change_RMS=float(
                                    np.sqrt(
                                        np.sum((A[k] - B[k]) ** 2 * weights[sensor])
                                    )
                                ),
                            )
                        )
                    LOG.info(
                        "Paired partition %s %s %s %s N=%s",
                        site,
                        level,
                        sensor,
                        mode,
                        len(A),
                    )
    save(pd.DataFrame(temporal), "paired_temporal_partition.csv")
    save(pd.DataFrame(pairs), "paired_polygon_changes.csv")
    save(pd.DataFrame(label_audit), "paired_label_audit.csv")
    cases = []
    supports = []
    for level in LEVELS:
        t, a = scheme_data(table, arrays, level)
        # Recorded taxon labels can vary within an ID: exclude rather than guess.
        inconsistent = t.groupby("GlobalID").label.nunique()
        bad = set(inconsistent[inconsistent > 1].index)
        mask = ~t.GlobalID.isin(bad)
        a = {s: X[mask.to_numpy()] for s, X in a.items()}
        t = t.loc[mask].reset_index(drop=True)
        for fold, kind, train, test in outer_folds(t, config):
            if kind not in {"plant", "site", "year"}:
                continue
            prepared, counts, status = prepare_fold(
                t, a, actual, fold, kind, train, test, config
            )
            supports.append(
                counts.assign(
                    level=level,
                    fold=fold,
                    kind=kind,
                    status_fold=status,
                    excluded_conflicting_ids=len(bad),
                    experiment="hierarchy"
                    if level not in {"researcher_level", "narrow_pft"}
                    else "sensitivity",
                )
            )
            if prepared is None:
                continue
            if level in {"researcher_level", "narrow_pft"}:
                # Same old memberships and seed: no new stored baseline fits.
                for mode in ["shape", "amplitude", "one_identity"]:
                    aa = dict(a)
                    ww = dict(waves)
                    pp = dict(prepared)
                    if mode in {"shape", "amplitude"}:
                        shape, norm = spectral_shape(a["NEON"], weights["NEON"])
                        aa["NEON"] = shape if mode == "shape" else norm[:, None]
                        pp["test_arrays"] = dict(
                            prepared["test_arrays"], NEON=aa["NEON"][prepared["test"]]
                        )
                        if mode == "amplitude":
                            ww["NEON"] = np.array([np.nan])
                    else:
                        pp["proper"] = (
                            t.iloc[prepared["proper"]]
                            .sort_values(["GlobalID", "year"])
                            .drop_duplicates("GlobalID")
                            .index.to_numpy()
                        )
                    context = dict(
                        scheme=level,
                        fold=fold,
                        kind=kind,
                        experiment="sensitivity",
                        mode=mode,
                    )
                    cases.append((t, aa, ww, pp, context, "NEON_full"))
            else:
                for rep in ["NEON_full", "OLI"]:
                    cases.append(
                        (
                            t,
                            a,
                            waves,
                            prepared,
                            dict(
                                scheme=level,
                                fold=fold,
                                kind=kind,
                                experiment="hierarchy",
                                mode="stored",
                            ),
                            rep,
                        )
                    )
        # Same unseen identities assessed in both years; paired training panel only.
        niwo = t[t.site.eq("NIWO")]
        if niwo.year.nunique() != 2:
            continue
        ids = niwo.groupby("GlobalID").year.nunique()
        shared = ids[ids == 2].index
        paired = niwo[niwo.GlobalID.isin(shared)]
        ix = paired.index.to_numpy()
        pt = t.iloc[ix].reset_index(drop=True)
        pa = {s: X[ix] for s, X in a.items()}
        for fold, kind, tr, te in outer_folds(pt, config):
            if kind != "plant":
                continue
            for year in sorted(pt.year.unique()):
                train = tr & pt.year.eq(year).to_numpy()
                prepared, counts, status = prepare_fold(
                    pt, pa, actual, fold, "paired", train, te, config
                )
                name = f"paired_train{year}_{fold}"
                supports.append(
                    counts.assign(
                        level=level,
                        fold=name,
                        kind="paired",
                        status_fold=status,
                        experiment="paired_transfer",
                    )
                )
                if prepared is None:
                    continue
                for rep in ["NEON_full", "OLI"]:
                    cases.append(
                        (
                            pt,
                            pa,
                            waves,
                            prepared,
                            dict(
                                scheme=level,
                                fold=name,
                                kind="paired",
                                experiment="paired_transfer",
                                mode="stored",
                                training_year=int(year),
                            ),
                            rep,
                        )
                    )
    save(pd.concat(supports, ignore_index=True), "fold_support.csv")
    LOG.info("Closure fixed plan: %s fits; no prior fits rerun", len(cases))
    write_json_atomic(
        BASE / "manifests/run_plan.json",
        dict(
            fit_cases=len(cases),
            by_experiment=pd.Series([c[4]["experiment"] for c in cases])
            .value_counts()
            .to_dict(),
        ),
    )

    def execute(case):
        t, a, w, p, context, rep = case
        LOG.info(
            "Fit %s %s %s %s", context["scheme"], context["fold"], context["mode"], rep
        )
        return fit_predict_case(
            t, a, w, p, context, rep, "logistic", ROOT, identity, config
        )

    directories = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(execute, c) for c in cases]
        for future in as_completed(jobs):
            directories.append(future.result())
            LOG.info("Closure completed %s/%s", len(directories), len(cases))
    directories = sorted(directories)
    for name in ["summary", "class_metrics", "confusion", "reliability"]:
        save(
            pd.concat(
                [pd.read_csv(d / (name + ".csv")) for d in directories],
                ignore_index=True,
            ),
            "new_" + name + ".csv",
        )
    predictions = pd.concat(
        [pd.read_parquet(d / "predictions.parquet") for d in directories],
        ignore_index=True,
    )
    predictions.to_parquet(ROOT / "predictions.parquet", index=False)
    peryear = []
    paired_delta = []
    rates = []
    groupcols = ["scheme", "fold", "representation", "experiment", "mode"]
    for keys, g in predictions.groupby(groupcols):
        context = dict(zip(groupcols, keys))
        classes = np.asarray(json.loads(g.classes.iloc[0]))
        byyear = (
            list(g.groupby("year"))
            if context["experiment"] == "paired_transfer"
            else [(None, g)]
        )
        draws = []
        values = []
        for year, part in byyear:
            part = part.sort_values(["GlobalID", "observation_id"])
            p = np.array([json.loads(v) for v in part.raw_probabilities])
            truth = part.label.to_numpy()
            pred = part.suggested_label.to_numpy()
            metrics, _, _, _ = classification_metrics(truth, p, classes)
            boot = cluster_bootstrap_accuracy(
                truth, pred, part.GlobalID, classes, seed=stable_seed(context["fold"])
            )
            if year is not None:
                peryear.append(
                    dict(
                        **context,
                        test_year=int(year),
                        training_year=int(g.training_year.iloc[0]),
                        **metrics,
                        BA_low=float(np.quantile(boot, 0.025)),
                        BA_high=float(np.quantile(boot, 0.975)),
                        identities=part.GlobalID.nunique(),
                    )
                )
                draws.append(boot)
                values.append(metrics["balanced_accuracy"])
            rate = one_vs_rest_metrics(truth, pred, classes)
            rate = rate.merge(
                cluster_rate_intervals(
                    truth,
                    pred,
                    part.GlobalID,
                    classes,
                    seed=stable_seed(context["fold"]),
                ),
                on="label",
                validate="one_to_one",
            )
            for k, v in context.items():
                rate[k] = v
            rate["test_year"] = year
            rates.append(rate)
        if len(draws) == 2:
            delta = draws[1] - draws[0]
            paired_delta.append(
                dict(
                    **context,
                    training_year=int(g.training_year.iloc[0]),
                    first_test_year=int(byyear[0][0]),
                    second_test_year=int(byyear[1][0]),
                    BA_delta_2023_minus_2020=values[1] - values[0],
                    delta_low=float(np.quantile(delta, 0.025)),
                    delta_high=float(np.quantile(delta, 0.975)),
                )
            )
    save(pd.DataFrame(peryear), "paired_temporal_recognition.csv")
    save(pd.DataFrame(paired_delta), "paired_temporal_accuracy_change.csv")
    save(pd.concat(rates, ignore_index=True), "false_detection_rates.csv")
    index = []
    for d in directories:
        detail = json.loads((d / "fit_details.json").read_text())
        index.append(
            dict(
                **detail["context"],
                representation=detail["representation"],
                directory=str(d.relative_to(REPO)),
                model_sha256=_file_hash(d / "model.joblib"),
                memberships_sha256=_file_hash(d / "memberships.parquet"),
            )
        )
    save(pd.DataFrame(index), "new_model_index.csv")
    files = [p for p in ROOT.rglob("*") if p.is_file() and p != ledger] + list(
        (BASE / "tables").glob("*.csv")
    )
    manifest = dict(
        identity=identity,
        fit_cases=len(cases),
        active_checkpoints=[str(p.relative_to(REPO)) for p in directories],
        outputs={str(p.relative_to(REPO)): _file_hash(p) for p in sorted(files)},
    )
    write_json_atomic(ledger, manifest)
    write_json_atomic(BASE / "manifests/closure_run.json", manifest)
    return manifest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    run()
