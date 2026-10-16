"""Experimental staged MESMA audit on verified compact empirical spectral summaries.

Not operational abundance inference. Keep unknown units, material purity and
independent ground-truth gaps visible. Source rasters/library are never copied.
"""

from pathlib import Path
from dataclasses import dataclass, asdict
from itertools import combinations
import json
import logging
import time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial.distance import cdist

from .plant_spectral_atlas import _file_hash
from .plant_spectral_pfts import tag_pfts, load_pft_crosswalk
from .sensor_pft_transfer import validate_sensor_coordinates
from .pft_method_audit import wavelength_weights
from .bulk.provenance import write_json_atomic, signature_sha256
from .mixtures import (
    fit_models,
    fcls,
    shade_model_errors,
    selection_scores,
    select_endmembers,
    grouped_identity_split,
    validate_holdout,
    adequacy_status,
    detection_metrics,
    mixture_truth,
    _angles,
)

LOG = logging.getLogger(__name__)
METHODS = ["random", "medoid", "EAR", "MASA", "CoB", "IES", "diversity", "hybrid"]
META = [
    "GlobalID",
    "species",
    "cover_category",
    "cover_subcategory",
    "dead_subcategory",
    "other_subcategory",
    "shaded",
    "aop_site",
    "plot",
    "location",
    "field_year",
    "imagery_year",
]


@dataclass(frozen=True)
class ReadinessConfig:
    seed: int = 20261014
    candidate_per_class: int = 12
    mixture_endmembers_per_class: int = 2
    pairs_per_composition: int = 1
    mc_replicates: int = 12
    minimum_train: int = 4
    minimum_test: int = 2
    maximum_models: int = 20000
    plant_folds: int = 3
    all_flights: bool = True


def decode_flight_history(value):
    """Decode the established nested JSON exposure contract, never split on pipes."""
    pairs = [json.loads(v) for v in json.loads(value)]
    if not pairs or any(not isinstance(p, list) or len(p) != 2 for p in pairs):
        raise ValueError("Invalid compact flight exposure history")
    return tuple(sorted(set(p[0] for p in pairs)))


def load_compact_inputs(source, compact, *, include_historical_labels=True):
    """Validate paired memberships/support; retain stored units without guessing."""
    root = Path(compact)
    frames = {
        k: pd.read_parquet(root / (stage + "_polygon_year.parquet"))
        for k, stage in [("NEON", "corr"), ("OLI", "olioli_undarkened")]
    }
    key = ["site", "year", "GlobalID"]
    frames = {k: t.sort_values(key).reset_index(drop=True) for k, t in frames.items()}
    if not frames["NEON"][key].equals(frames["OLI"][key]):
        raise ValueError("Paired sensor membership drift")
    for k, t in frames.items():
        if t.duplicated(key).any():
            raise ValueError("Duplicate polygon/year identity")
    meta = pq.read_table(source, columns=META).to_pandas().drop_duplicates()
    for field in META[1:]:
        if meta.groupby("GlobalID")[field].nunique().gt(1).any():
            raise ValueError("Conflicting metadata: " + field)
    meta = meta.groupby("GlobalID", sort=True).first().reset_index()
    table = frames["NEON"][key + ["flight_history", "flight_observations"]].merge(
        meta, on="GlobalID", validate="many_to_one"
    )
    if include_historical_labels:
        table = tag_pfts(table, load_pft_crosswalk())
    table["flights"] = table.flight_history.map(decode_flight_history)
    table["material_label"] = table.cover_category
    background = table.cover_category.eq("Non-vegetated & dead")
    table.loc[background, "material_label"] = table.loc[
        background, "cover_subcategory"
    ].fillna("Unresolved background")
    dead = background & table.cover_subcategory.eq("Dead")
    table.loc[dead, "material_label"] = table.loc[dead, "dead_subcategory"].fillna(
        "Unresolved dead"
    )
    # Do not rename Bare to soil or combine mixed materials with pure-labelled records.
    spectra = {}
    waves = {}
    for k, t in frames.items():
        prefix = "corr_wl" if k == "NEON" else "olioli_undarkened_wl"
        cols = [c for c in t if c.startswith(prefix)]
        w = np.array([float(c.split("_wl")[1][:-2]) for c in cols])
        y = t[cols].to_numpy(float)
        if k == "OLI":
            validate_sensor_coordinates(w, "OLI")
        supported = np.isfinite(y).all(0)
        if k == "NEON":
            supported &= ~(((w >= 1340) & (w <= 1450)) | ((w >= 1790) & (w <= 2000)))
        spectra[k] = y[:, supported]
        waves[k] = w[supported]
        if spectra[k].shape[1] < 2:
            raise ValueError("No finite physical support")
    for k in spectra:
        if not np.isfinite(spectra[k]).all():
            raise ValueError("Incomplete paired support")
    return table, spectra, waves


def flight_target_tables(compact, waves):
    """Actual paired plant/flight means, never polygon/year medians in flight tests."""
    result = {}
    key = ["GlobalID", "flight_id", "source_image", "polygon_id"]
    reference = None
    for sensor, stage in [("NEON", "corr"), ("OLI", "olioli_undarkened")]:
        frame = pd.read_parquet(Path(compact) / stage / "plant_flight_spectra.parquet")
        if frame.duplicated(key).any():
            raise ValueError("Duplicate plant-flight source key")
        frame = frame.sort_values(key).reset_index(drop=True)
        if reference is None:
            reference = frame[key]
        elif not reference.equals(frame[key]):
            raise ValueError("Plant-flight sensor membership drift")
        cols = [stage + "_wl" + f"{w:g}" + "nm" for w in waves[sensor]]
        if not np.isfinite(frame[cols].to_numpy(float)).all():
            raise ValueError("Missing actual-flight common support")
        result[sensor] = frame.groupby(["GlobalID", "flight_id"])[cols].median()
    return result


def replace_flight_targets(y, table, indices, flight, observations, scale):
    """Replace only held-out rows with their actual flight; expose missing sources."""
    key = pd.MultiIndex.from_tuples(
        [(table.iloc[i].GlobalID, flight) for i in indices],
        names=["GlobalID", "flight_id"],
    )
    for sensor in y:
        y[sensor][indices] = observations[sensor].loc[key].to_numpy(float) / scale


def _save(frame, root, name):
    frame = pd.DataFrame(frame)
    if name in {"abundance_estimates", "fold_membership", "synthetic_mixture_truth"}:
        frame.to_parquet(
            Path(root) / "tables" / (name + ".parquet"), index=False, compression="zstd"
        )
    else:
        frame.to_csv(Path(root) / "tables" / (name + ".csv"), index=False)
    return frame


def _source_metadata_audit(table, values, waves, root):
    results = []
    for scheme, field in [
        ("species", "species"),
        ("inferred_pft", "pft_code"),
        ("researcher", "cover_category"),
        ("material", "material_label"),
    ]:
        for (site, year, label), g in table.groupby(
            ["site", "year", field], dropna=False
        ):
            results.append(
                dict(
                    scheme=scheme,
                    site=site,
                    year=year,
                    label=label,
                    identities=g.GlobalID.nunique(),
                    polygon_years=len(g),
                    species=g.species.nunique(),
                    flights=g.flights.explode().nunique(),
                )
            )
    _save(results, root, "class_sample_sizes")
    table.to_csv(root / "tables" / "sample_membership.csv", index=False)
    qc = []
    variability = []
    accum = []
    nearest = []
    between = []
    for sensor, y in values.items():
        w = waves[sensor]
        for (site, year), ix in table.groupby(["site", "year"]).groups.items():
            a = y[list(ix)]
            q = np.quantile(a, [0, 0.01, 0.5, 0.99, 1])
            qc.append(
                dict(
                    sensor=sensor,
                    site=site,
                    year=year,
                    N=len(ix),
                    bands=len(w),
                    negative_values=int((a < 0).sum()),
                    zero_values=int((a == 0).sum()),
                    finite_values=int(np.isfinite(a).sum()),
                    minimum=q[0],
                    p01=q[1],
                    median=q[2],
                    p99=q[3],
                    maximum=q[4],
                    units="native_stored_no_verified_scale",
                    physical_gt1_or_saturation="not_identifiable_without_metadata",
                )
            )
        for scheme, field in [
            ("inferred_pft", "pft_code"),
            ("researcher", "cover_category"),
            ("material", "material_label"),
        ]:
            for label, ix in table.groupby(field).groups.items():
                ix = np.array(list(ix))
                a = y[ix]
                center = np.median(a, axis=0)
                distances = np.sqrt(np.mean((a - center) ** 2, 1))
                angles = _angles(a, center[None])[:, 0]
                trace = float(np.var(a, axis=0).mean())
                variability.append(
                    dict(
                        sensor=sensor,
                        scheme=scheme,
                        label=label,
                        identities=table.iloc[ix].GlobalID.nunique(),
                        polygon_years=len(ix),
                        median_RMSE_to_median=float(np.median(distances)),
                        p95_RMSE_to_median=float(np.quantile(distances, 0.95)),
                        median_angle_deg=float(np.median(angles)),
                        mean_band_variance=trace,
                    )
                )
            if scheme != "researcher":
                continue
            # Identity-disjoint accumulation: evaluation plants never become candidates.
            rng = np.random.default_rng(20261014)
            for label, group in table.groupby(field):
                ids = rng.permutation(group.GlobalID.unique())
                split = max(1, int(0.7 * len(ids)))
                train = group.index[group.GlobalID.isin(ids[:split])].to_numpy()
                test = group.index[group.GlobalID.isin(ids[split:])].to_numpy()
                if len(test) < 2:
                    continue
                for repeat in range(10):
                    order = rng.permutation(train)
                    for n in [1, 2, 5, 10, 20, 50, 100, 200, 500]:
                        if n > len(order):
                            continue
                        d = cdist(y[test], y[order[:n]], metric="euclidean") / np.sqrt(
                            y.shape[1]
                        )
                        angle = _angles(y[test], y[order[:n]])
                        accum.append(
                            dict(
                                sensor=sensor,
                                label=label,
                                repeat=repeat,
                                endmembers=n,
                                test_identities=table.iloc[test].GlobalID.nunique(),
                                median_nearest_RMSE=float(np.median(d.min(1))),
                                p95_nearest_RMSE=float(np.quantile(d.min(1), 0.95)),
                                median_nearest_angle_deg=float(np.median(angle.min(1))),
                                interpretation="library_holdout_not_full_image_coverage",
                            )
                        )
            for heldsite in table.site.unique():
                train = np.flatnonzero(table.site.ne(heldsite))
                test = np.flatnonzero(table.site.eq(heldsite))
                if not len(train) or not len(test):
                    continue
                d = cdist(y[test], y[train]) / np.sqrt(y.shape[1])
                a = _angles(y[test], y[train])
                for j, row in enumerate(test):
                    nearest.append(
                        dict(
                            sensor=sensor,
                            GlobalID=table.iloc[row].GlobalID,
                            site=heldsite,
                            year=table.iloc[row].year,
                            nearest_other_site_RMSE=float(d[j].min()),
                            nearest_other_site_angle=float(a[j].min()),
                        )
                    )
        for (la, ia), (lb, ib) in combinations(
            list(table.groupby("cover_category").groups.items()), 2
        ):
            ca = np.median(y[list(ia)], 0)
            cb = np.median(y[list(ib)], 0)
            between.append(
                dict(
                    sensor=sensor,
                    class_A=la,
                    class_B=lb,
                    median_curve_RMSE=float(np.sqrt(np.mean((ca - cb) ** 2))),
                    median_curve_angle_deg=float(_angles(ca[None], cb[None])[0, 0]),
                )
            )
    _save(qc, root, "spectral_qc")
    _save(variability, root, "within_class_variability")
    _save(accum, root, "endmember_accumulation")
    _save(nearest, root, "cross_site_library_coverage")
    _save(between, root, "between_class_distances")


def _folds(table, scheme, config):
    """Exhaustive available sites/years/flights, and stratified identity folds."""
    rng = np.random.default_rng(config.seed)
    assignments = {}
    for _, g in table.groupby(["label", "site"]):
        ids = rng.permutation(g.GlobalID.unique())
        assignments.update({v: i % config.plant_folds for i, v in enumerate(ids)})
    for fold in range(config.plant_folds):
        yield (
            f"plant_{fold}",
            "plant",
            table.GlobalID.map(assignments).eq(fold).to_numpy(),
        )
    for site in sorted(table.site.unique()):
        yield "site_" + site, "site", table.site.eq(site).to_numpy()
    for year in sorted(table.year.unique()):
        yield "year_" + str(year), "year", table.year.eq(year).to_numpy()
    # Explicit within-NIWO directional transfer, distinct from geographic transfer.
    for year in sorted(table.loc[table.site.eq("NIWO"), "year"].unique()):
        mask = table.site.eq("NIWO") & table.year.eq(year)
        yield "NIWO_year_" + str(year), "within_site_year", mask.to_numpy()
    if config.all_flights:
        flights = sorted(set(table.flights.explode()))
        for flight in flights:
            yield (
                "flight_" + str(flight),
                "flight",
                table.flights.map(lambda v: flight in v).to_numpy(),
            )


def _pool(table, train, config, rng):
    """Explicit candidate budget, one record/identity, class/site/year stratified."""
    pool = []
    for label, g in table.loc[train].groupby("label"):
        g = g.iloc[rng.permutation(len(g))].drop_duplicates("GlobalID")
        strata = [list(ix) for ix in g.groupby(["site", "year"]).groups.values()]
        selected = []
        while len(selected) < config.candidate_per_class and any(strata):
            for s in strata:
                if s and len(selected) < config.candidate_per_class:
                    selected.append(s.pop())
        pool.extend(selected)
    return np.array(pool, int)


def _aligned_fractions(fit, classes):
    f = np.zeros((len(fit["fractions"]), len(classes)))
    for j, c in enumerate(fit["classes"]):
        f[:, list(classes).index(c)] = fit["fractions"][:, j]
    return f


def _record_fit(
    fit, true, classes, context, method, rows, summaries, detection, source_ids
):
    f = _aligned_fractions(fit, classes)
    difference = f - true
    for j, c in enumerate(classes):
        delta = difference[:, j]
        summaries.append(
            dict(
                **context,
                method=method,
                label=c,
                N=len(f),
                fraction_bias=float(delta.mean()),
                fraction_MAE=float(np.abs(delta).mean()),
                fraction_RMSE=float(np.sqrt(np.mean(delta**2))),
                mean_reconstruction_RMSE=float(np.mean(fit["RMSE"])),
                class_set_error=float(
                    np.mean(np.any((f >= 0.1) != (true >= 0.1), axis=1))
                ),
                negative_fraction_count=int((f < -1e-9).sum()),
                sum_violation_count=int((np.abs(f.sum(1) - 1) > 1e-8).sum()),
                model_count=fit["model_count"],
            )
        )
        for threshold in [0.05, 0.1, 0.2]:
            for fraction in np.unique(np.round(true[:, j], 8)):
                ix = np.isclose(true[:, j], fraction)
                counts = detection_metrics(true[ix, j], f[ix, j], threshold=threshold)
                detection.append(
                    dict(
                        **context,
                        method=method,
                        label=c,
                        true_fraction=fraction,
                        detection_threshold=threshold,
                        N=int(ix.sum()),
                        detections=counts["TP"] + counts["FP"],
                        probability=(counts["TP"] + counts["FP"]) / counts["N"],
                        interpretation="conditional_synthetic_draws_not_independent_plants",
                    )
                )
    for i in range(len(f)):
        rows.append(
            dict(
                **context,
                method=method,
                mixture_id=i,
                source_ids=source_ids[i],
                true_fractions=json.dumps(
                    dict(zip(map(str, classes), true[i].tolist()))
                ),
                estimated_fractions=json.dumps(
                    dict(zip(map(str, classes), f[i].tolist()))
                ),
                fraction_RMSE=float(np.sqrt(np.mean(difference[i] ** 2))),
                reconstruction_RMSE=fit["RMSE"][i],
                spectral_angle_deg=fit["spectral_angle_deg"][i],
                complexity=int(fit["complexity"][i]),
                near_compositions=int(fit["near_compositions"][i]),
                max_near_fraction_range=float(np.max(fit["near_fraction_range"][i])),
                runner_up_gap=fit["runner_up_gap"][i],
            )
        )
    return f


def run_readiness(source, compact, output, *, config=None, first_pass=False) -> dict:
    """Run experimental grouped readiness diagnostics on verified compact inputs.

    Args:
        source (str or pathlib.Path): Original polygon Parquet, read in place.
        compact (str or pathlib.Path): Completed paired NEON/undarkened OLI
            empirical summaries from the same source; caller verifies upstream
            manifests. Values stay in stored units; no physical scale inferred.
        output (str or pathlib.Path): Compact checkpoints, memberships and tables.
        config (ReadinessConfig, optional): Explicit candidate/fold/model budgets.
        first_pass (bool): Restrict to plant_0 for a controlled diagnostic run.

    Returns:
        dict: Conditional synthetic status, source/config/code identity and owned
            output hashes. This is not an operational MESMA readiness certificate.

    Raises:
        ValueError: Invalid budgets, pairing, coordinates, conflicts or corrupt
            checkpoints. Missing optional flight inputs fail explicitly.
        OSError: Required source/checkpoint files cannot be read/written.

    Parent identities are purged globally before training-only candidate
    selection. Synthetic fractions are algebraic mixing weights, not field
    abundance. Missing purity, verified units and real fraction truth remain
    blockers. Completed valid fold checkpoints are reused, not regenerated.
    """
    config = config or ReadinessConfig()
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    for name in ["tables", "manifests", "checkpoints"]:
        (root / name).mkdir(exist_ok=True)
    if (
        config.candidate_per_class < 2
        or config.plant_folds < 2
        or config.mc_replicates < 2
    ):
        raise ValueError("Invalid audit budgets")
    table, values, waves = load_compact_inputs(source, compact)
    flight_observations = (
        flight_target_tables(compact, waves) if config.all_flights else None
    )
    identity = dict(
        flight_compact={
            str(p): _file_hash(p)
            for stage in ["corr", "olioli_undarkened"]
            for p in [Path(compact) / stage / "plant_flight_spectra.parquet"]
        }
        if config.all_flights
        else {},
        source_sha256=_file_hash(source),
        crosswalk_sha256=_file_hash(
            Path(__file__).parent / "data" / "plant_pft_crosswalk.csv"
        ),
        compact={
            str(p): _file_hash(p) for p in Path(compact).glob("*_polygon_year.parquet")
        },
        config=asdict(config),
        first_pass=first_pass,
        code=_file_hash(__file__),
        mixtures_code=_file_hash(Path(__file__).with_name("mixtures.py")),
    )
    manifest = root / "manifests" / "statistics_manifest.json"
    if manifest.exists():
        old = json.loads(manifest.read_text())
        if old["identity"] == identity and all(
            (root / n).exists() and _file_hash(root / n) == h
            for n, h in old["outputs"].items()
        ):
            return old
    write_json_atomic(
        root / "manifests" / "design.json",
        dict(
            identity=identity,
            spectral_support={k: v.tolist() for k, v in waves.items()},
            units="native stored; common training-only RMS scalar; absolute units unverified",
            detection_thresholds=[0.05, 0.1, 0.2],
            ambiguity_tolerances=[0.005, 0.01, 0.02],
        ),
    )
    # Earlier experimental iterations used CSV for these large compact tables.
    for name in ["abundance_estimates", "fold_membership"]:
        (root / "tables" / (name + ".csv")).unlink(missing_ok=True)
    _source_metadata_audit(table, values, waves, root)
    outcomes = []
    membership = []
    selections = []
    runtimes = []
    library = []
    ambiguities = []
    confusion = []
    allrows = []
    summaries = []
    detection = []
    uncertainty = []
    novelty = []
    state_groups = dict(
        fold_membership=membership,
        endmember_scores=selections,
        runtime=runtimes,
        library_size=library,
        mixture_ambiguity=ambiguities,
        directed_confusion=confusion,
        abundance_estimates=allrows,
        fraction_errors=summaries,
        detection_curves=detection,
        uncertainty=uncertainty,
        unknown_detection=novelty,
    )
    schemes = {
        "inferred_pft": "pft_code",
        "researcher": "cover_category",
        "material": "material_label",
    }
    for scheme, field in schemes.items():
        eligible = ~table[field].isna() & ~table[field].isin(
            [
                "UNASSIGNED",
                "Mixed Dead / Bare / Rock",
                "Unresolved background",
                "Unresolved dead",
                "Dead - Debris",
            ]
        )
        t = table.loc[eligible].copy()
        original = t.index.to_numpy()
        t = t.reset_index(drop=True)
        t["label"] = t[field]
        v = {k: a[original] for k, a in values.items()}
        for fold, kind, test_mask in _folds(t, scheme, config):
            if first_pass and fold != "plant_0":
                continue
            train, test = grouped_identity_split(t.GlobalID, test_mask)
            if kind == "within_site_year":
                train &= t.site.eq("NIWO").to_numpy()
            classes = sorted(t.label.unique())
            tr = t.loc[train].groupby("label").GlobalID.nunique()
            te = t.loc[test].groupby("label").GlobalID.nunique()
            supported = [
                c
                for c in classes
                if tr.get(c, 0) >= config.minimum_train
                and te.get(c, 0) >= config.minimum_test
            ]
            outcomes.extend(
                [
                    dict(
                        scheme=scheme,
                        fold=fold,
                        kind=kind,
                        label=c,
                        train_identities=int(tr.get(c, 0)),
                        test_identities=int(te.get(c, 0)),
                        status="eligible"
                        if c in supported
                        else "insufficient_class_support",
                    )
                    for c in classes
                ]
            )
            if len(supported) < 2:
                continue
            train &= t.label.isin(supported).to_numpy()
            test &= t.label.isin(supported).to_numpy()
            checkpoint = (
                root
                / "checkpoints"
                / signature_sha256(dict(scheme=scheme, fold=fold))[:20]
            )
            ledger = checkpoint / "manifest.json"
            if ledger.exists():
                old = json.loads(ledger.read_text())
                if old["identity"] == identity and all(
                    (checkpoint / n).exists() and _file_hash(checkpoint / n) == h
                    for n, h in old["outputs"].items()
                ):
                    for name in old["tables"]:
                        state_groups[name].extend(
                            pd.read_parquet(checkpoint / (name + ".parquet")).to_dict(
                                "records"
                            )
                        )
                    LOG.info("Reused completed fold: %s %s", scheme, fold)
                    continue
            starts = {name: len(records) for name, records in state_groups.items()}
            rng = np.random.default_rng(config.seed + len(outcomes))
            pool = _pool(t, train, config, rng)
            validate_holdout(t.GlobalID, train, test, pool)
            testix = np.flatnonzero(test)
            # One held-out polygon/year per identity for simulation source sampling.
            test_unique = t.loc[test].drop_duplicates("GlobalID").index.to_numpy()
            assert set(t.iloc[pool].GlobalID).isdisjoint(t.iloc[testix].GlobalID)
            for ix in np.flatnonzero(train | test):
                membership.append(
                    dict(
                        scheme=scheme,
                        fold=fold,
                        kind=kind,
                        GlobalID=t.iloc[ix].GlobalID,
                        year=t.iloc[ix].year,
                        site=t.iloc[ix].site,
                        label=t.iloc[ix].label,
                        role="test" if test[ix] else "train",
                        candidate=bool(ix in pool),
                    )
                )
            LOG.info(
                "%s %s: %s classes, %s candidates, %s held-out identities",
                scheme,
                fold,
                len(supported),
                len(pool),
                len(test_unique),
            )
            labels = t.iloc[pool].label.to_numpy()
            scale = float(np.median(np.sqrt(np.mean(v["NEON"][pool] ** 2, 1))))
            if scale <= 0:
                raise ValueError("Nonpositive training spectral scale")
            y = {k: a / scale for k, a in v.items()}
            if kind == "flight":
                replace_flight_targets(
                    y, t, testix, fold[len("flight_") :], flight_observations, scale
                )
            # Quadrature on disconnected NEON segments; equal OLI channels.
            weights = np.sqrt(wavelength_weights(waves["NEON"]) * y["NEON"].shape[1])
            y["NEON"] = y["NEON"] * weights
            score = selection_scores(y["NEON"][pool], labels)
            for i, ix in enumerate(pool):
                selections.append(
                    dict(
                        scheme=scheme,
                        fold=fold,
                        kind=kind,
                        GlobalID=t.iloc[ix].GlobalID,
                        year=t.iloc[ix].year,
                        label=t.iloc[ix].label,
                        EAR=score["EAR"][i],
                        MASA=score["MASA"][i],
                        medoid=score["medoid"][i],
                        training_scale_stored_units=scale,
                    )
                )
            chosen = {}
            methods = METHODS if kind == "plant" else ["EAR"]
            start = time.perf_counter()
            for method in methods:
                k = config.mixture_endmembers_per_class
                chosen[method] = select_endmembers(
                    y["NEON"][pool], labels, method, k, seed=config.seed, threshold=0.02
                )
            for method, ids in chosen.items():
                for index in pool[ids]:
                    selections.append(
                        dict(
                            scheme=scheme,
                            fold=fold,
                            kind=kind,
                            GlobalID=t.iloc[index].GlobalID,
                            year=t.iloc[index].year,
                            label=t.iloc[index].label,
                            selected_method=method,
                            training_scale_stored_units=scale,
                        )
                    )
            runtimes.append(
                dict(
                    scheme=scheme,
                    fold=fold,
                    kind=kind,
                    stage="selection",
                    seconds=time.perf_counter() - start,
                    candidate_count=len(pool),
                )
            )
            # Size curves are held-out reconstruction of each true class; not training fit.
            if kind == "plant":
                for method in methods:
                    for size in [1, 2, 5, 10, 20, 50, 100]:
                        if size > config.candidate_per_class:
                            library.append(
                                dict(
                                    scheme=scheme,
                                    fold=fold,
                                    method=method,
                                    requested_per_class=size,
                                    status="outside_declared_candidate_budget",
                                )
                            )
                            continue
                        ids = select_endmembers(
                            y["NEON"][pool],
                            labels,
                            method,
                            size,
                            seed=config.seed,
                            threshold=0.02,
                        )
                        for sensor, a in y.items():
                            for c in supported:
                                candidates = ids[labels[ids] == c]
                                targets = testix[t.iloc[testix].label.eq(c)]
                                if not len(candidates):
                                    continue
                                errors = shade_model_errors(
                                    a[targets], a[pool[candidates]]
                                ).min(1)
                                library.append(
                                    dict(
                                        scheme=scheme,
                                        fold=fold,
                                        sensor=sensor,
                                        method=method,
                                        label=c,
                                        requested_per_class=size,
                                        selected_per_class=len(candidates),
                                        status="evaluated",
                                        N=len(targets),
                                        median_RMSE=float(np.median(errors)),
                                        p95_RMSE=float(np.quantile(errors, 0.95)),
                                    )
                                )
            synthetic = mixture_truth(
                y["NEON"][test_unique],
                t.iloc[test_unique].label.to_numpy(),
                pairs_per_composition=config.pairs_per_composition,
                seed=config.seed,
            )
            source_rows = np.where(
                synthetic["sources"] >= 0,
                test_unique[np.maximum(synthetic["sources"], 0)],
                -1,
            )
            source_ids = [
                "|".join(
                    str(t.iloc[ix].GlobalID) + "@" + str(t.iloc[ix].year)
                    for ix in row
                    if ix >= 0
                )
                for row in source_rows
            ]
            truth = synthetic["truth"]
            simclasses = synthetic["classes"]
            repeat_pairs = []
            for _, repeat_group in t.loc[train].groupby("GlobalID"):
                if len(repeat_group) > 1:
                    repeat_pairs.append([repeat_group.index[0], repeat_group.index[-1]])
            if repeat_pairs:
                repeated = np.array(repeat_pairs)[
                    rng.integers(0, len(repeat_pairs), len(truth))
                ]
                signs = rng.choice([-1.0, 1.0], len(truth))
            for sensor, a in y.items():
                targets = np.array(
                    [
                        sum(
                            weight * a[ix]
                            for ix, weight in zip(row, weights_)
                            if ix >= 0
                        )
                        for row, weights_ in zip(
                            source_rows, synthetic["source_fractions"]
                        )
                    ]
                )
                context = dict(scheme=scheme, fold=fold, kind=kind, sensor=sensor)
                start = time.perf_counter()
                for method, ids in chosen.items():
                    for complexity in [2, 3] if method == "EAR" else [3]:
                        fit = fit_models(
                            targets,
                            labels[ids],
                            a[pool[ids]],
                            max_components=complexity,
                            tolerance=0.01,
                            maximum_models=config.maximum_models,
                        )
                        name = method + "_MESMA" + str(complexity)
                        _record_fit(
                            fit,
                            truth,
                            simclasses,
                            context,
                            name,
                            allrows,
                            summaries,
                            detection,
                            source_ids,
                        )
                        if method == "EAR" and complexity == 3:
                            # Pure held-out directed confusion and wrong-class convex reconstructions.
                            pure = fit_models(
                                a[testix],
                                labels[ids],
                                a[pool[ids]],
                                max_components=3,
                                tolerance=0.01,
                                maximum_models=config.maximum_models,
                            )
                            for c in supported:
                                ix = testix[t.iloc[testix].label.eq(c)]
                                own = ids[labels[ids] == c]
                                other = ids[labels[ids] != c]
                                correct = cdist(a[ix], a[pool[own]]).min(1) / np.sqrt(
                                    a.shape[1]
                                )
                                incorrect = fit_models(
                                    a[ix],
                                    labels[other],
                                    a[pool[other]],
                                    max_components=3,
                                    tolerance=0.01,
                                    maximum_models=config.maximum_models,
                                )
                                incorrect_f = _aligned_fractions(incorrect, simclasses)
                                for j, row in enumerate(ix):
                                    for tolerance in [0.005, 0.01, 0.02]:
                                        ambiguities.append(
                                            dict(
                                                **context,
                                                GlobalID=t.iloc[row].GlobalID,
                                                year=t.iloc[row].year,
                                                label=c,
                                                correct_class_RMSE=correct[j],
                                                incorrect_mixture_RMSE=incorrect[
                                                    "RMSE"
                                                ][j],
                                                incorrect_minus_correct=incorrect[
                                                    "RMSE"
                                                ][j]
                                                - correct[j],
                                                tolerance=tolerance,
                                                ambiguous=bool(
                                                    incorrect["RMSE"][j]
                                                    <= correct[j] + tolerance
                                                ),
                                                near_incorrect_compositions=int(
                                                    sum(
                                                        np.sqrt(err[j])
                                                        <= incorrect["RMSE"][j]
                                                        + tolerance
                                                        for err in incorrect[
                                                            "composition_errors"
                                                        ].values()
                                                    )
                                                ),
                                                wrong_composition=json.dumps(
                                                    dict(
                                                        zip(
                                                            map(str, simclasses),
                                                            incorrect_f[j].tolist(),
                                                        )
                                                    )
                                                ),
                                            )
                                        )
                                # Training-only own-class leave-self-out adequacy threshold.
                                training = cdist(a[pool[own]], a[pool[own]]) / np.sqrt(
                                    a.shape[1]
                                )
                                np.fill_diagonal(training, np.inf)
                                threshold = (
                                    float(np.quantile(training.min(1), 0.95))
                                    if len(own) > 1
                                    else np.nan
                                )
                                for j, row in enumerate(ix):
                                    novelty.append(
                                        dict(
                                            **context,
                                            GlobalID=t.iloc[row].GlobalID,
                                            label=c,
                                            threshold=threshold,
                                            known_error=correct[j],
                                            absent_class_error=incorrect["RMSE"][j],
                                            known_flagged=bool(correct[j] > threshold),
                                            unknown_adequacy_status=str(adequacy_status(incorrect["RMSE"][j], threshold)),
                                            unknown_flagged=bool(
                                                incorrect["RMSE"][j] > threshold
                                            ),
                                        )
                                    )
                                for otherc in supported:
                                    eids = ids[labels[ids] == otherc]
                                    if len(eids):
                                        confusion.append(
                                            dict(
                                                **context,
                                                target_class=c,
                                                model_class=otherc,
                                                N=len(ix),
                                                median_shade_model_RMSE=float(
                                                    np.median(
                                                        shade_model_errors(
                                                            a[ix], a[pool[eids]]
                                                        ).min(1)
                                                    )
                                                ),
                                            )
                                        )
                            # Keep pure geometry outcomes separate from synthetic recovery.
                            _ = pure
                if kind == "plant" and repeat_pairs:
                    ids = chosen["EAR"]
                    for amplitude in [0.25, 0.5]:
                        stressed = targets + amplitude * signs[:, None] * (
                            a[repeated[:, 1]] - a[repeated[:, 0]]
                        )
                        stressfit = fit_models(
                            stressed,
                            labels[ids],
                            a[pool[ids]],
                            max_components=3,
                            tolerance=0.01,
                            maximum_models=config.maximum_models,
                        )
                        _record_fit(
                            stressfit,
                            truth,
                            simclasses,
                            context,
                            f"EAR_acquisition_stress_{amplitude}",
                            allrows,
                            summaries,
                            detection,
                            source_ids,
                        )
                # Simple FCLS uses one training medoid per class, not all library entries.
                mids = select_endmembers(
                    y["NEON"][pool], labels, "medoid", 1, seed=config.seed
                )
                fit = fcls(targets, a[pool[mids]])
                fit["classes"] = labels[mids]
                _record_fit(
                    fit,
                    truth,
                    simclasses,
                    context,
                    "FCLS_medoid",
                    allrows,
                    summaries,
                    detection,
                    source_ids,
                )
                if kind == "plant":
                    bundle = []
                    predictions = []
                    for rep in range(config.mc_replicates):
                        ids = select_endmembers(
                            y["NEON"][pool], labels, "random", 1, seed=config.seed + rep
                        )
                        result = fcls(targets, a[pool[ids]])
                        result["classes"] = labels[ids]
                        bundle.append(_aligned_fractions(result, simclasses))
                        predictions.append(result["reconstruction"])
                    bundle = np.array(bundle)
                    average = bundle.mean(0)
                    prediction = np.mean(predictions, axis=0)
                    norms = np.linalg.norm(targets, axis=1) * np.linalg.norm(
                        prediction, axis=1
                    )
                    cosine = np.divide(
                        np.sum(targets * prediction, axis=1),
                        norms,
                        out=np.full(len(targets), np.nan),
                        where=norms > 1e-12,
                    )
                    ensemble = dict(
                        fractions=average,
                        classes=simclasses,
                        RMSE=np.sqrt(np.mean((targets - prediction) ** 2, axis=1)),
                        spectral_angle_deg=np.degrees(
                            np.arccos(np.clip(cosine, -1, 1))
                        ),
                        model_count=config.mc_replicates,
                        complexity=np.sum(average > 1e-9, axis=1),
                        near_compositions=np.full(len(targets), np.nan),
                        near_fraction_range=np.ptp(bundle, axis=0),
                        runner_up_gap=np.full(len(targets), np.nan),
                    )
                    # Ensemble model count records draws; near_compositions is not defined for it.
                    ensemble["near_compositions"] = np.zeros(len(targets), int)
                    _record_fit(
                        ensemble,
                        truth,
                        simclasses,
                        context,
                        "MC_mean_FCLS",
                        allrows,
                        summaries,
                        detection,
                        source_ids,
                    )
                    errors = np.sqrt(np.mean((average - truth) ** 2, 0))
                    lo, hi = np.quantile(bundle, [0.025, 0.975], axis=0)
                    for j, c in enumerate(simclasses):
                        uncertainty.append(
                            dict(
                                **context,
                                label=c,
                                N=len(targets),
                                fraction_RMSE=float(errors[j]),
                                mean_interval_width=float(np.mean(hi[:, j] - lo[:, j])),
                                conditional_interval_coverage=float(
                                    np.mean(
                                        (truth[:, j] >= lo[:, j])
                                        & (truth[:, j] <= hi[:, j])
                                    )
                                ),
                                nominal=0.95,
                                replicates=config.mc_replicates,
                                interpretation="endmember_choice_stability_not_calibrated_confidence",
                            )
                        )
                    # Explicit idealized black shade; physical zero is invariant to the common scalar.
                    shaded = targets * 0.75
                    e = np.vstack([a[pool[mids]], np.zeros(a.shape[1])])
                    shadefit = fcls(shaded, e)
                    for j, c in enumerate(
                        list(labels[mids]) + ["idealized_black_shade"]
                    ):
                        expected = np.column_stack(
                            [truth * 0.75, np.full(len(truth), 0.25)]
                        )[:, j]
                        uncertainty.append(
                            dict(
                                **context,
                                label=c,
                                N=len(targets),
                                fraction_RMSE=float(
                                    np.sqrt(
                                        np.mean(
                                            (shadefit["fractions"][:, j] - expected)
                                            ** 2
                                        )
                                    )
                                ),
                                interpretation="idealized_shade_sensitivity_not_measured_material",
                            )
                        )
                runtimes.append(
                    dict(
                        **context,
                        stage="unmixing",
                        seconds=time.perf_counter() - start,
                        synthetic_mixtures=len(targets),
                    )
                )
            checkpoint.mkdir(exist_ok=True)
            completed = []
            for name, records in state_groups.items():
                frame = pd.DataFrame(records[starts[name] :])
                if frame.empty:
                    continue
                path = checkpoint / (name + ".parquet")
                temporary = path.with_suffix(".tmp")
                frame.to_parquet(temporary, index=False, compression="zstd")
                temporary.replace(path)
                completed.append(name)
            write_json_atomic(
                ledger,
                dict(
                    identity=identity,
                    tables=completed,
                    outputs={
                        name + ".parquet": _file_hash(checkpoint / (name + ".parquet"))
                        for name in completed
                    },
                ),
            )
            # A valid fold ledger resumes without redoing its selections or unmixing.
            write_json_atomic(
                root / "checkpoints" / "progress.json",
                dict(
                    scheme=scheme,
                    fold=fold,
                    completed_mixture_rows=len(allrows),
                    status="running",
                ),
            )
    frames = {
        "fold_support": outcomes,
        "fold_membership": membership,
        "endmember_scores": selections,
        "runtime": runtimes,
        "library_size": library,
        "mixture_ambiguity": ambiguities,
        "directed_confusion": confusion,
        "abundance_estimates": allrows,
        "fraction_errors": summaries,
        "detection_curves": detection,
        "uncertainty": uncertainty,
        "unknown_detection": novelty,
    }
    for name, frame in frames.items():
        _save(frame, root, name)
    estimates = pd.DataFrame(allrows)
    if len(estimates):
        _save(
            estimates[
                ["scheme", "fold", "kind", "mixture_id", "source_ids", "true_fractions"]
            ].drop_duplicates(),
            root,
            "synthetic_mixture_truth",
        )
    probabilities = pd.DataFrame(detection)
    if len(probabilities):
        probabilities["false_positive_rate"] = np.where(
            probabilities.true_fraction.eq(0), probabilities.probability, np.nan
        )
        probabilities["false_negative_rate"] = np.where(
            probabilities.true_fraction.gt(0), 1 - probabilities.probability, np.nan
        )
        _save(probabilities, root, "detection_errors")
    losses = pd.DataFrame(summaries)
    if len(losses):
        index = ["scheme", "fold", "kind", "method", "label"]
        paired = losses.pivot(
            index=index, columns="sensor", values="fraction_RMSE"
        ).reset_index()
        paired["OLI_minus_NEON_fraction_RMSE"] = paired.OLI - paired.NEON
        _save(paired, root, "sensor_comparison")
    write_json_atomic(
        root / "checkpoints" / "progress.json",
        dict(
            status="complete_conditional_synthetic_audit",
            real_abundance_validation="NOT YET AVAILABLE",
        ),
    )
    result = dict(
        identity=identity,
        status="conditional_synthetic_audit_complete_real_abundance_blocked",
        outputs={
            str(p.relative_to(root)): _file_hash(p)
            for p in root.rglob("*")
            if p.is_file() and p != manifest
        },
    )
    write_json_atomic(manifest, result)
    return result
