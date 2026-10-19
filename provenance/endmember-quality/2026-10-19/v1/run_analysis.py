"""Internal fixed-library diagnostics, not selection-blind validation.

Reads original arrays/Parquet in place. No source spectra cache or production change.
"""

from pathlib import Path
from itertools import combinations
import hashlib
import json
import time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial.distance import cdist
from scipy.optimize import linprog
from preflight import labels as read_labels, ROOT, INPUT
from spectralbridge.mixtures import fit_models, fcls
from spectralbridge.library_analysis import fraction_diagnostics

OUT = Path(__file__).resolve().parent
TABLES = OUT / "tables"
CLASSES = np.array(
    ["Deciduous", "Evergreen", "Herbaceous", "Non-vegetated & dead", "Woody shrub"]
)
CONFIG = {
    "seed": 20261019,
    "index_base": 0,
    "selection_scope": "whole library, confirmed by user",
    "random_replicates": 30,
    "screen_per_class": 3,
    "exploratory_screen_sensitivity": [1, 2, 5],
    "max_components": 3,
    "bundles_per_site_year": 2,
    "near_RMSE_tolerance": 0.01,
    "LP_feasibility_tolerance": 1e-9,
    "LP_verified_RMSE_tolerance": 1e-8,
    "class_mapping": {i + 1: c for i, c in enumerate(CLASSES)},
}


def save_json(path, data):
    path.write_text(
        json.dumps(
            data,
            indent=2,
            default=lambda x: x.item() if isinstance(x, np.generic) else str(x),
        )
        + "\n"
    )


def save_table(name, rows):
    pd.DataFrame(rows).to_csv(TABLES / (name + ".csv"), index=False)


def matched_random_indices(selected, identities, rng):
    """Match the exact number of selected pixels from EACH same polygon identity."""
    chosen = []
    for identity, count in zip(*np.unique(identities[selected], return_counts=True)):
        pool = np.flatnonzero(identities == identity)
        chosen.extend(rng.choice(pool, int(count), replace=False))
    return np.asarray(chosen, int)


def coverage(targets, truth, endmembers, labels, identities):
    """Single-reference label agreement and nearest same-label RMSE, weighted by ID."""
    distance = cdist(targets, endmembers) / np.sqrt(targets.shape[1])
    closest = distance.argmin(1)
    predicted = labels[closest]
    _, inverse, count = np.unique(identities, return_inverse=True, return_counts=True)
    weights = 1 / count[inverse]
    rows = []
    same = np.empty(len(targets))
    for c in CLASSES:
        use = truth == c
        which = np.flatnonzero(labels == c)
        if not len(which):
            raise ValueError("Every class needs a candidate")
        nearest = distance[:, which].min(1)
        same[use] = nearest[use]
        rows.append(
            dict(
                category=c,
                mean_same_class_RMSE=np.average(nearest[use], weights=weights[use]),
                recall=np.average(predicted[use] == c, weights=weights[use]),
                target_curves=int(use.sum()),
                target_IDs=len(np.unique(identities[use])),
            )
        )
    return pd.DataFrame(rows), dict(
        prediction=predicted,
        nearest=closest,
        nearest_RMSE=distance[np.arange(len(targets)), closest],
        same_class_RMSE=same,
        weights=weights,
    )


def cross_class_certificate(target, own_class, library, labels):
    """Find an alternative convex combination excluding every own-class reference."""
    ix = np.flatnonzero(labels != own_class)
    e = library[ix]
    result = linprog(
        np.zeros(len(e)),
        A_eq=np.vstack([e.T, np.ones(len(e))]),
        b_eq=np.r_[target, 1.0],
        bounds=(0, None),
        method="highs",
        options={
            "primal_feasibility_tolerance": 1e-9,
            "dual_feasibility_tolerance": 1e-9,
        },
    )
    if not result.success:
        return dict(feasible=False, status=int(result.status))
    f = result.x
    residual = float(np.sqrt(np.mean((f @ e - target) ** 2)))
    good = bool(residual <= 1e-8 and f.min() >= -1e-9 and abs(f.sum() - 1) <= 1e-8)
    class_f = np.array([f[labels[ix] == c].sum() for c in CLASSES])
    active = np.flatnonzero(f > 1e-9)
    return dict(
        feasible=good,
        status=int(result.status),
        RMSE=residual,
        class_fractions=class_f,
        local_indices=ix[active],
        weights=f[active],
    )


def make_bundle_targets(frame, bands, seed=20261019, bundles_per_domain=2):
    """Disjoint parents across every bundle and domain; use one parent per category."""
    rng = np.random.default_rng(seed)
    used = set()
    records = []
    spectra = []
    truth = []
    parents = []
    bundle = 0
    fractions = [
        (list(comp), [f, 1 - f])
        for comp in combinations(range(5), 2)
        for f in [0.1, 0.5, 0.9]
    ]
    fractions += [(list(comp), [1 / 3] * 3) for comp in combinations(range(5), 3)]
    fractions += [([c], [1.0]) for c in range(5)]
    for (site, year), domain in frame.groupby(["site", "year"], sort=True):
        for _ in range(bundles_per_domain):
            chosen = []
            for c in CLASSES:
                pool = domain[(domain.category == c) & ~domain.GlobalID.isin(used)]
                if pool.empty:
                    raise ValueError("Insufficient independent parents in domain")
                chosen.append(pool.iloc[int(rng.integers(len(pool)))])
            p = pd.DataFrame(chosen)
            e = p[bands].to_numpy()
            ids = p.GlobalID.to_numpy()
            assert len(set(ids)) == 5 and not set(ids) & used
            used.update(ids)
            for category, weight in fractions:
                f = np.zeros(5)
                f[category] = weight
                target = f @ e
                spectra.append(target)
                truth.append(f)
                parents.append(e)
                records.append(
                    dict(
                        bundle=bundle,
                        site=site,
                        year=int(year),
                        components=len(category),
                        parent_ids="|".join(ids),
                        generating_classes="|".join(CLASSES[category]),
                        generating_fractions="|".join(map(str, weight)),
                    )
                )
            bundle += 1
    return (
        np.asarray(spectra),
        np.asarray(truth),
        pd.DataFrame(records),
        np.asarray(parents),
    )


def main():
    started = time.time()
    TABLES.mkdir(exist_ok=True)
    files = [
        INPUT / "library_oli_undarkened_10_12_26.npy",
        INPUT / "class_list_oli_undarkened_10_12_26.npy",
        INPUT / "selected_constrained_members.csv",
    ]
    x = np.load(files[0], allow_pickle=False).T
    y = read_labels(files[1])
    selected = pd.read_csv(files[2]).iloc[:, 0].to_numpy()
    assert (
        x.shape == (len(y), 7) and np.isfinite(x).all() and selected.dtype.kind in "iu"
    )
    assert (
        len(selected) == len(np.unique(selected))
        and selected.min() >= 0
        and selected.max() < len(x)
    )
    source = ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    parquet = pq.ParquetFile(source)
    bands = [
        n for n in parquet.schema_arrow.names if n.startswith("olioli_undarkened_b")
    ]
    d = parquet.read(
        columns=bands
        + [
            "GlobalID",
            "cover_category",
            "flight_id",
            "source_parquet",
            "imagery_year",
            "aop_site",
        ]
    ).to_pandas()
    assert np.array_equal(y, d.cover_category.to_numpy()) and np.allclose(
        x, d[bands].to_numpy() / 10000, atol=1e-7, rtol=2e-7
    )
    assert set(y) == set(CLASSES) and not d.GlobalID.isna().any()
    d["site"] = d.flight_id.str.extract(r"_([A-Z]{4})_DP1")[0]
    d["year"] = d.flight_id.str.extract(r"_(\d{8})_")[0].str[:4].astype(int)
    assert d.site.notna().all() and np.array_equal(
        d.site.to_numpy(), d.aop_site.to_numpy()
    )
    d["category"] = y
    assert d.groupby("GlobalID").category.nunique().max() == 1
    for j, b in enumerate(bands):
        d[b] = x[:, j]
    ids = d.GlobalID.to_numpy()
    candidate_ids = set(ids[selected])
    e = x[selected]
    ey = y[selected]
    members = d.iloc[selected][
        ["GlobalID", "category", "site", "year", "flight_id", "source_parquet"] + bands
    ].copy()
    members.insert(0, "array_index", selected)
    members["class_code"] = (
        pd.Series(ey).map({c: i + 1 for i, c in enumerate(CLASSES)}).to_numpy()
    )
    members.to_csv(TABLES / "selected_members.csv", index=False)
    # Flight medians first, then one polygon/site/acquisition-year spectrum.
    flight = (
        d.groupby(["GlobalID", "category", "site", "year", "flight_id"], sort=True)[
            bands
        ]
        .median()
        .reset_index()
    )
    parent = (
        flight.groupby(["GlobalID", "category", "site", "year"], sort=True)[bands]
        .median()
        .reset_index()
    )
    targets = parent[~parent.GlobalID.isin(candidate_ids)].reset_index(drop=True)
    assert set(targets.GlobalID).isdisjoint(candidate_ids)
    tx = targets[bands].to_numpy()
    ty = targets.category.to_numpy()
    tid = targets.GlobalID.to_numpy()
    primary, detail = coverage(tx, ty, e, ey, tid)
    save_table("coverage_selected", primary)
    record = targets[["GlobalID", "category", "site", "year"]].copy()
    for key in ["prediction", "nearest_RMSE", "same_class_RMSE", "weights"]:
        record[key] = detail[key]
    record["nearest_array_index"] = selected[detail["nearest"]]
    record.to_csv(TABLES / "target_coverage.csv", index=False)
    random = []
    random_sample = None
    for rep in range(CONFIG["random_replicates"]):
        rix = matched_random_indices(
            selected, ids, np.random.default_rng(CONFIG["seed"] + rep)
        )
        assert set(ids[rix]) == candidate_ids
        rtable, _ = coverage(tx, ty, x[rix], y[rix], tid)
        rtable["replicate"] = rep
        random.extend(rtable.to_dict("records"))
        if rep == 0:
            random_sample = rix
        if rep % 5 == 0:
            print(
                f"Coverage random control {rep + 1}/{CONFIG['random_replicates']}",
                flush=True,
            )
    save_table("coverage_random", random)
    flight_groups = (d.GlobalID.astype(str) + "::" + d.flight_id.astype(str)).to_numpy()
    random_flight = []
    for rep in range(CONFIG["random_replicates"]):
        rix = matched_random_indices(
            selected, flight_groups, np.random.default_rng(CONFIG["seed"] + rep)
        )
        rtable, _ = coverage(tx, ty, x[rix], y[rix], tid)
        rtable["replicate"] = rep
        random_flight.extend(rtable.to_dict("records"))
    save_table("coverage_random_flight", random_flight)
    confusion = []
    for c in CLASSES:
        use = ty == c
        for predicted in CLASSES:
            confusion.append(
                dict(
                    truth=c,
                    prediction=predicted,
                    proportion=np.average(
                        detail["prediction"][use] == predicted,
                        weights=detail["weights"][use],
                    ),
                )
            )
    save_table("confusion", confusion)
    site_results = []
    for (site, year), group in record.groupby(["site", "year"]):
        for c in CLASSES:
            z = group[group.category == c]
            site_results.append(
                dict(
                    site=site,
                    year=int(year),
                    category=c,
                    curves=len(z),
                    IDs=z.GlobalID.nunique(),
                    recall=np.mean(z.prediction == c),
                    same_class_RMSE=np.mean(z.same_class_RMSE),
                )
            )
    save_table("coverage_domains", site_results)
    # Cross-category overlap of individual selected reference points.
    distance = cdist(e, e) / np.sqrt(7)
    same = ey[:, None] == ey[None, :]
    distance[same] = np.inf
    nearest = distance.argmin(1)
    save_table(
        "selected_cross_class_neighbours",
        [
            dict(
                array_index=int(selected[i]),
                category=ey[i],
                other_array_index=int(selected[j]),
                other_category=ey[j],
                RMSE=distance[i, j],
            )
            for i, j in enumerate(nearest)
        ],
    )
    certificates = []
    certificate_weights = []
    for i, target in enumerate(e):
        cert = cross_class_certificate(target, ey[i], e, ey)
        row = dict(
            array_index=int(selected[i]),
            category=ey[i],
            feasible=cert["feasible"],
            solver_status=cert["status"],
            RMSE=cert.get("RMSE", np.nan),
        )
        if cert["feasible"]:
            row.update(
                {f"fraction_{j + 1}": v for j, v in enumerate(cert["class_fractions"])}
            )
            for index, weight in zip(cert["local_indices"], cert["weights"]):
                certificate_weights.append(
                    dict(
                        target_array_index=int(selected[i]),
                        alternative_array_index=int(selected[index]),
                        alternative_category=ey[index],
                        weight=weight,
                    )
                )
        certificates.append(row)
        if i % 100 == 0:
            print(f"Convex-hull ambiguity {i + 1}/{len(e)}", flush=True)
    save_table("cross_class_hull", certificates)
    save_table("cross_class_hull_weights", certificate_weights)
    # Bounded screened MESMA, explicitly not the combinatorial full-library search.
    sx, truth, synthetic, oracle_parents = make_bundle_targets(
        targets, bands, CONFIG["seed"], CONFIG["bundles_per_site_year"]
    )
    predictions = {}
    diagnostics = []
    intervals = []
    bundle_errors = []
    model_details = []
    for method, library_ix, screen in [
        ("Selected screened MESMA", selected, 3),
        ("Matched random screened MESMA", random_sample, 3),
        ("Screen1 sensitivity", selected, 1),
        ("Screen2 sensitivity", selected, 2),
        ("Screen5 sensitivity", selected, 5),
    ]:
        library = x[library_ix]
        categories = y[library_ix]
        estimate = []
        for i, target in enumerate(sx):
            distances = np.mean((library - target) ** 2, axis=1)
            shortlist = np.concatenate(
                [
                    np.flatnonzero(categories == c)[
                        np.argsort(distances[categories == c], kind="stable")[:screen]
                    ]
                    for c in CLASSES
                ]
            )
            fit = fit_models(
                target[None, :],
                categories[shortlist],
                library[shortlist],
                max_components=3,
                tolerance=0.01,
                maximum_models=5000,
            )
            assert np.array_equal(fit["classes"], CLASSES)
            estimate.append(fit["fractions"][0])
            candidate_errors = np.sqrt(
                np.array([v[0] for v in fit["composition_errors"].values()])
            )
            model_details.append(
                dict(
                    method=method,
                    target=i,
                    bundle=int(synthetic.iloc[i].bundle),
                    reconstruction_RMSE=fit["RMSE"][0],
                    maximum_near_fraction_range=fit["near_fraction_range"][0].max(),
                    near_class_sets=int(fit["near_compositions"][0]),
                    near_class_sets_001=int(
                        np.sum(candidate_errors <= fit["RMSE"][0] + 0.001)
                    ),
                    near_class_sets_005=int(
                        np.sum(candidate_errors <= fit["RMSE"][0] + 0.005)
                    ),
                    screening_per_class=screen,
                    candidate_models=int(fit["model_count"]),
                    screened_array_indices="|".join(map(str, library_ix[shortlist])),
                    selected_array_indices="|".join(
                        map(
                            str,
                            library_ix[
                                shortlist[
                                    fit["model_indices"][0][
                                        fit["model_indices"][0] >= 0
                                    ]
                                ]
                            ],
                        )
                    ),
                    selected_component_fractions="|".join(
                        str(
                            fit["fractions"][
                                0,
                                np.flatnonzero(CLASSES == categories[shortlist[j]])[0],
                            ]
                        )
                        for j in fit["model_indices"][0]
                        if j >= 0
                    ),
                )
            )
            if i % 45 == 0:
                print(f"{method}: {i + 1}/{len(sx)} targets", flush=True)
        predictions[method] = np.asarray(estimate)
    predictions["Uniform design prior"] = np.full_like(truth, 0.2)
    # Follow-up fairness control: same <=3 nonzero-category constraint as MESMA.
    # Under the balanced design every fixed triple has identical expected error.
    sparse_prior = np.zeros_like(truth)
    sparse_prior[:, :3] = 1 / 3
    predictions["Sparse design prior"] = sparse_prior
    oracle_prediction = np.vstack(
        [fcls(sx[i : i + 1], oracle_parents[i])["fractions"][0] for i in range(len(sx))]
    )
    predictions["Known-parent FCLS oracle"] = oracle_prediction
    for method, pred in predictions.items():
        bundle = synthetic.bundle.to_numpy()
        result = fraction_diagnostics(
            truth,
            pred,
            class_order=CLASSES,
            groups=bundle,
            bootstraps=499,
            seed=CONFIG["seed"],
        )
        interval = result["intervals"].copy()
        interval["method"] = method
        intervals.extend(interval.to_dict("records"))
        for b in np.unique(bundle):
            use = bundle == b
            bundle_errors.append(
                dict(
                    method=method,
                    bundle=int(b),
                    RMSE=float(np.sqrt(np.mean((truth[use] - pred[use]) ** 2))),
                )
            )
        table = result["per_class"].copy()
        table["method"] = method
        diagnostics.extend(table.to_dict("records"))
        rows = synthetic.copy()
        rows["method"] = method
        rows["target"] = np.arange(len(rows))
        for j, c in enumerate(CLASSES):
            rows[f"truth_{j + 1}"] = truth[:, j]
            rows[f"prediction_{j + 1}"] = pred[:, j]
        rows["fraction_RMSE"] = np.sqrt(np.mean((truth - pred) ** 2, axis=1))
        rows.to_csv(
            TABLES / (method.split()[0].lower() + "_synthetic_predictions.csv"),
            index=False,
        )
    save_table("fraction_diagnostics", diagnostics)
    save_table("fraction_bootstrap_intervals", intervals)
    save_table("fraction_bundle_errors", bundle_errors)
    save_table("screened_mesma_details", model_details)
    synthetic.to_csv(TABLES / "synthetic_target_membership.csv", index=False)
    # Direct rank evidence and bounded full-search complexity, without enumeration.
    singular = np.linalg.svd(e - e.mean(0), compute_uv=False)
    counts = [int((ey == c).sum()) for c in CLASSES]
    model_count = sum(
        sum(int(np.prod(comb)) for comb in combinations(counts, k)) for k in [1, 2, 3]
    )
    r = pd.DataFrame(random)
    perrep = r.groupby("replicate")[["mean_same_class_RMSE", "recall"]].mean()
    summary = {
        "status": "completed internal diagnostics",
        "config": CONFIG,
        "array_shape": list(x.shape),
        "selected_members": len(selected),
        "selected_polygon_IDs": len(candidate_ids),
        "selected_class_counts": dict(zip(CLASSES, counts)),
        "target_polygon_IDs": len(np.unique(tid)),
        "target_curves": len(tx),
        "target_aggregation": "within-flight median then polygon/site/source-acquisition-year median; all candidate GlobalIDs excluded globally",
        "selection_blind": False,
        "selected_macro_same_class_RMSE": primary.mean_same_class_RMSE.mean(),
        "selected_single_reference_BA": primary.recall.mean(),
        "matched_random_macro_same_class_RMSE_mean": perrep.mean_same_class_RMSE.mean(),
        "matched_random_macro_same_class_RMSE_range": perrep.mean_same_class_RMSE.quantile(
            [0.025, 0.975]
        ).tolist(),
        "matched_random_single_reference_BA_mean": perrep.recall.mean(),
        "matched_random_single_reference_BA_range": perrep.recall.quantile(
            [0.025, 0.975]
        ).tolist(),
        "flight_matched_random_macro_same_class_RMSE_mean": pd.DataFrame(random_flight)
        .groupby("replicate")
        .mean_same_class_RMSE.mean()
        .mean(),
        "flight_matched_random_single_reference_BA_mean": pd.DataFrame(random_flight)
        .groupby("replicate")
        .recall.mean()
        .mean(),
        "cross_class_convex_hull_matches": sum(row["feasible"] for row in certificates),
        "affine_singular_values": singular.tolist(),
        "affine_rank": int(np.linalg.matrix_rank(e - e.mean(0))),
        "full_distinct_class_up_to_three_model_count": model_count,
        "synthetic_targets": len(truth),
        "synthetic_bundles": int(synthetic.bundle.nunique()),
        "synthetic_RMSE": {
            method: float(np.sqrt(np.mean((pred - truth) ** 2)))
            for method, pred in predictions.items()
        },
        "synthetic_mean_row_RMSE": {
            method: float(np.sqrt(np.mean((pred - truth) ** 2, axis=1)).mean())
            for method, pred in predictions.items()
        },
        "elapsed_seconds": time.time() - started,
        "input_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files
        },
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "imagery_year_mismatch_rows": int((d.year != d.imagery_year).sum()),
    }
    save_json(OUT / "summary.json", summary)
    print(
        json.dumps(
            summary,
            indent=2,
            default=lambda v: v.item() if isinstance(v, np.generic) else str(v),
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
