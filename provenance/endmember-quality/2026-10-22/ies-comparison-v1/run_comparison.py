"""Matched internal readiness comparison; read supplied libraries in place.

Four cells: old/new selection x original/revised labels. No package changes.
Common targets exclude the union of selected polygon IDs. Search is restartable.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from itertools import combinations
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial.distance import cdist

from spectralbridge.library_analysis import fit_ridge_fractions
from spectralbridge.mixtures import fcls

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
OLD = ROOT / "provenance/endmember-quality/2026-10-19/v1"
EXH = OLD.parent / "exhaustive-v1"
INPUT = Path("/Users/tuff/Downloads")
ATOMS = ["Deciduous", "Evergreen", "Herbaceous", "Woody shrub", "Bare_Rock", "Dead"]
SCHEMES = {
    "original": [
        "Deciduous",
        "Evergreen",
        "Herbaceous",
        "Non-vegetated & dead",
        "Woody shrub",
    ],
    "revised": [
        "Deciduous",
        "Evergreen",
        "Herbaceous_woody_shrub",
        "Bare_Rock",
        "Dead",
    ],
}
MAPS = {
    "original": [0, 1, 2, 4, 3, 3],
    "revised": [0, 1, 2, 2, 3, 4],
    "common": [0, 1, 2, 2, 3, 3],
}
COMMON = [
    "Deciduous",
    "Evergreen",
    "Herbaceous + woody shrub",
    "Background (bare/rock + dead)",
]
CONFIG = dict(
    seed=20261022,
    bundles_per_site_year=2,
    train_groups=3,
    train_bundles_per_group=12,
    ridge_alphas=[0.01, 0.1, 1, 10, 100],
    max_components=3,
    chunk_models=1024,
    bootstrap_draws=1999,
    capacity_control_draws=5,
    unknown_background="Exclude mixed/unspecified backgrounds from the primary common label-eligible comparison; never guess dead/bare fractions",
    selection_scope="Internal fixed-library comparison; no selection-blind claim for either library",
    targets="71 recipes per six-parent bundle: six pure, all pairs at .1/.5/.9, all triples at equal thirds; exact same spectra for every cell",
    ridge_training="Same 71 recipes in 36 training bundles; three polygon-disjoint tuning groups; uniform parent-ID then uniform selected-pixel sampling within each atom/group",
    validation="Eight parent-disjoint target bundles; all selected parent IDs excluded; site/year breakdowns are diagnostics, not held-site validation",
    units="Supplied-array units; equality to source stored values /10000 is numerical lineage, not validated physical reflectance",
)


def load_module(name, path, search_path=None):
    if search_path:
        sys.path.insert(0, str(search_path))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if search_path:
            sys.path.pop(0)
    return module


legacy = load_module("ies_legacy_helpers", OLD / "run_analysis.py", OLD)
stream = load_module("ies_stream_kernel", EXH / "stream_mesma.py")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(2**20), b""):
            h.update(b)
    return h.hexdigest()


def save_json(path, value):
    Path(path).write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            default=lambda x: x.item() if isinstance(x, np.generic) else str(x),
        )
        + "\n"
    )


def atomic_labels(frame):
    """Conservative user-CSV mapping; mixed/missing background remains unknown."""
    out = frame.cover_category.astype("string").copy()
    use = out.eq("Non-vegetated & dead")
    out.loc[use] = frame.loc[use, "cover_subcategory"].map(
        {"Bare": "Bare_Rock", "Rock": "Bare_Rock", "Dead": "Dead"}
    )
    return out


def mapping_matrix(scheme):
    return np.eye(4 if scheme == "common" else 5)[MAPS[scheme]]


def label_codes(atoms, scheme):
    return np.array(MAPS[scheme])[np.array([ATOMS.index(v) for v in atoms])]


def coarsen(prediction, scheme):
    # Both output spaces are projected onto the SAME four ecological contrasts.
    mapping = [0, 1, 2, 3, 2] if scheme == "original" else [0, 1, 2, 3, 3]
    return np.asarray(prediction) @ np.eye(4)[mapping]


def recipes():
    result = []
    for i in range(6):
        w = np.zeros(6)
        w[i] = 1
        result.append(w)
    for a, b in combinations(range(6), 2):
        for f in [0.1, 0.5, 0.9]:
            w = np.zeros(6)
            w[[a, b]] = [f, 1 - f]
            result.append(w)
    for comp in combinations(range(6), 3):
        w = np.zeros(6)
        w[list(comp)] = 1 / 3
        result.append(w)
    return np.array(result)


def common_parent_targets(parent, selected_ids, seed=20261022):
    pool = parent[parent.atom.notna() & ~parent.GlobalID.isin(selected_ids)].copy()
    rng = np.random.default_rng(seed)
    used = set()
    xx = []
    truth = []
    meta = []
    refs = []
    design = recipes()
    for (site, year), group in pool.groupby(["site", "year"], sort=True):
        for _ in range(CONFIG["bundles_per_site_year"]):
            rows = []
            for atom in ATOMS:
                p = group[group.atom.eq(atom) & ~group.GlobalID.isin(used)]
                if p.empty:
                    raise ValueError(f"No independent parent for {site}/{year}/{atom}")
                row = p.iloc[int(rng.integers(len(p)))]
                rows.append(row)
                used.add(row.GlobalID)
            parents = pd.DataFrame(rows)
            spectra = parents.filter(regex="^band_").to_numpy(float)
            bid = len(refs)
            refs.append(spectra)
            for j, w in enumerate(design):
                xx.append(w @ spectra)
                truth.append(w)
                meta.append(
                    dict(
                        target=len(meta),
                        bundle=bid,
                        site=site,
                        year=int(year),
                        recipe=j,
                        components=int(np.count_nonzero(w)),
                        parent_ids="|".join(parents.GlobalID),
                        active_parent_ids="|".join(parents.GlobalID.to_numpy()[w > 0]),
                        active_atoms="|".join(np.array(ATOMS)[w > 0]),
                    )
                )
    assert used.isdisjoint(selected_ids)
    return pool, np.array(xx), np.array(truth), pd.DataFrame(meta), np.array(refs)


def training_mixtures(e, atoms, ids, seed=20261022):
    """Parent-disjoint tuning groups, retaining selected within-ID spectral spread."""
    rng = np.random.default_rng(seed)
    assign = {}
    for atom in ATOMS:
        parents = np.unique(ids[atoms == atom])
        parents = rng.permutation(parents)
        if len(parents) < CONFIG["train_groups"]:
            raise ValueError("Too few independent training IDs: " + atom)
        for j, pid in enumerate(parents):
            assign[pid] = j % CONFIG["train_groups"]
    groups = np.array([assign[p] for p in ids])
    x = []
    t = []
    g = []
    memberships = []
    design = recipes()
    for group in range(CONFIG["train_groups"]):
        memberships.append(
            dict(
                group=group,
                parent_ids=sorted({p for p, v in assign.items() if v == group}),
            )
        )
        for _ in range(CONFIG["train_bundles_per_group"]):
            picked = []
            for atom in ATOMS:
                parent = rng.choice(np.unique(ids[(atoms == atom) & (groups == group)]))
                ix = np.flatnonzero((ids == parent) & (atoms == atom))
                picked.append(int(rng.choice(ix)))
            x.extend(design @ e[picked])
            t.extend(design)
            g.extend([group] * len(design))
    assert len(assign) == len(np.unique(ids))
    return np.array(x), np.array(t), np.array(g), memberships


def coverage(x, atoms, ids, e, reference_atoms, scheme):
    distances = cdist(x, e) / np.sqrt(x.shape[1])
    nearest = distances.argmin(1)
    truth = label_codes(atoms, scheme)
    labels = label_codes(reference_atoms, scheme)
    predicted = labels[nearest]
    _, inverse, count = np.unique(ids, return_inverse=True, return_counts=True)
    weights = 1 / count[inverse]
    result = []
    details = []
    for k, cat in enumerate(SCHEMES[scheme]):
        use = truth == k
        rr = labels == k
        if not use.any() or not rr.any():
            raise ValueError("Missing category " + cat)
        same = distances[:, rr].min(1)
        result.append(
            dict(
                category=cat,
                recall=np.average(predicted[use] == k, weights=weights[use]),
                same_category_RMSE=np.average(same[use], weights=weights[use]),
                target_IDs=len(np.unique(ids[use])),
                target_curves=int(use.sum()),
            )
        )
        for ix in np.flatnonzero(use):
            details.append(
                dict(
                    row=int(ix),
                    truth=int(k),
                    prediction=int(predicted[ix]),
                    nearest_reference=int(nearest[ix]),
                    nearest_RMSE=float(distances[ix, nearest[ix]]),
                    same_category_RMSE=float(same[ix]),
                    identity_weight=float(weights[ix]),
                )
            )
    return pd.DataFrame(result), pd.DataFrame(details)


def prepare():
    OUT.mkdir(exist_ok=True)
    (OUT / "tables").mkdir(exist_ok=True)
    (OUT / "models").mkdir(exist_ok=True)
    paths = {
        "new_spectra": INPUT / "library_oli_undarkened_ies_selected.npy",
        "new_labels": INPUT / "class_list_oli_undarkened_ies_selected.npy",
        "new_csv": INPUT / "IES_selected_library.csv",
        "old_spectra": INPUT / "library_oli_undarkened_10_12_26.npy",
        "old_labels": INPUT / "class_list_oli_undarkened_10_12_26.npy",
        "old_selection": INPUT / "selected_constrained_members.csv",
        "source": ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet",
    }
    hashes = {
        key: dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)
        for key, p in paths.items()
    }
    previous = json.loads((OLD / "summary.json").read_text())
    for key in ["old_spectra", "old_labels", "old_selection"]:
        assert hashes[key]["sha256"] == previous["input_sha256"][str(paths[key])]
    assert (
        hashes["source"]["sha256"]
        == json.loads((EXH / "full_summary.json").read_text())["source_parquet_sha256"]
    )
    x = np.load(paths["old_spectra"], allow_pickle=False).T
    original_y = legacy.read_labels(paths["old_labels"])
    new_x = np.load(paths["new_spectra"], allow_pickle=False).T
    new_y = legacy.read_labels(paths["new_labels"])
    schema = pq.ParquetFile(paths["source"]).schema_arrow.names
    bands = [c for c in schema if c.startswith("olioli_undarkened_b")]
    metadata = [
        "GlobalID",
        "cover_category",
        "cover_subcategory",
        "flight_id",
        "pixel_id",
        "row",
        "col",
    ]
    source = pq.read_table(paths["source"], columns=metadata).to_pandas()
    new = pd.read_csv(
        paths["new_csv"],
        usecols=["Unnamed: 0", "new_class"] + metadata + bands,
        low_memory=False,
    )
    old_indices = pd.read_csv(paths["old_selection"]).iloc[:, 0].to_numpy()
    # Derive row lineage from immutable identity keys, never assume a CSV base.
    keys = ["GlobalID", "flight_id", "pixel_id", "row", "col"]
    linked = new[keys].merge(
        source.reset_index(names="source_index"),
        on=keys,
        how="left",
        sort=False,
        validate="one_to_one",
    )
    assert linked.source_index.notna().all()
    new_indices = linked.source_index.to_numpy(int)
    assert np.array_equal(new["Unnamed: 0"].to_numpy() - 1, new_indices)
    assert x.shape == (len(source), 7) and np.array_equal(
        original_y, source.cover_category
    )
    assert len(new) == len(new_x) == len(new_y) == len(new_indices)
    for ix in [old_indices, new_indices]:
        assert (
            ix.dtype.kind in "iu"
            and len(ix) == len(np.unique(ix))
            and ix.min() >= 0
            and ix.max() < len(x)
        )
    assert np.isfinite(x).all() and np.isfinite(new_x).all()
    assert np.array_equal(new_y, new.new_class) and np.array_equal(
        new_x, new[bands].to_numpy() / 10000
    )
    assert np.allclose(new_x, x[new_indices], rtol=2e-7, atol=1e-7)
    for col in metadata:
        assert np.array_equal(
            new[col].fillna("<NA>"), source.iloc[new_indices][col].fillna("<NA>")
        ), col
    source["atom"] = atomic_labels(source)
    assert source.groupby("GlobalID").atom.nunique(dropna=False).max() == 1
    expected_new = [
        SCHEMES["revised"][label_codes([v], "revised")[0]]
        for v in source.iloc[new_indices].atom
    ]
    assert np.array_equal(new_y, expected_new)
    source["site"] = source.flight_id.str.extract(r"_([A-Z]{4})_DP1")[0]
    source["year"] = source.flight_id.str.extract(r"_(\d{8})_")[0].str[:4].astype(int)
    assert source.site.notna().all()
    selected_union = set(source.iloc[np.r_[old_indices, new_indices]].GlobalID)
    libraries = {}
    for name, ix in [("old", old_indices), ("new", new_indices)]:
        eligible = source.iloc[ix].atom.notna().to_numpy()
        kept = ix[eligible]
        rows = source.iloc[kept].copy()
        libraries[name] = dict(
            x=x[kept],
            atoms=rows.atom.to_numpy(str),
            ids=rows.GlobalID.to_numpy(str),
            indices=kept,
            rows=rows,
        )
        rows[
            [
                "GlobalID",
                "cover_category",
                "cover_subcategory",
                "atom",
                "site",
                "year",
                "flight_id",
            ]
        ].assign(array_index=kept).to_csv(
            OUT / "tables" / f"{name}_selected_identity.csv", index=False
        )
    # Median per flight then per polygon/year, matching the earlier benchmark.
    bandnames = [f"band_{i}" for i in range(7)]
    source[bandnames] = x
    flight = source.groupby(
        ["GlobalID", "cover_category", "atom", "site", "year", "flight_id"],
        dropna=False,
        sort=True,
    )[bandnames].median()
    parent = (
        flight.groupby(
            level=["GlobalID", "cover_category", "atom", "site", "year"],
            dropna=False,
            sort=True,
        )
        .median()
        .reset_index()
    )
    pool, sx, truth, meta, refs = common_parent_targets(parent, selected_union)
    assert not set(pool.GlobalID) & selected_union
    audit = dict(
        inputs=hashes,
        source_rows=len(source),
        source_IDs=source.GlobalID.nunique(),
        new_shape=list(new_x.shape),
        new_label_counts=pd.Series(new_y).value_counts().to_dict(),
        alignment="CSV/NPY exact numerical match; new CSV exported row index is one-based, verified by one-to-one flight/GlobalID/pixel/row/column join and exact numerical spectra; previous selection indices remain zero-based",
        selected_union_IDs=len(selected_union),
        selected_overlap_IDs=len(
            set(libraries["old"]["ids"]) & set(libraries["new"]["ids"])
        ),
        unknown_background_rows=int(source.atom.isna().sum()),
        unknown_background_IDs=int(
            source.loc[source.atom.isna(), "GlobalID"].nunique()
        ),
        target_IDs=pool.GlobalID.nunique(),
        target_curves=len(pool),
        synthetic_targets=len(sx),
        target_bundles=meta.bundle.nunique(),
        parent_mixture_design=len(recipes()),
        source_units="Numerical lineage only; physical reflectance units unresolved",
    )
    audit["libraries"] = {
        name: dict(
            supplied_references=len(old_indices) if name == "old" else len(new_indices),
            primary_eligible_references=len(lib["x"]),
            primary_eligible_IDs=len(np.unique(lib["ids"])),
            atom_counts=pd.Series(lib["atoms"]).value_counts().to_dict(),
            site_counts=lib["rows"].site.value_counts().to_dict(),
            excluded_unresolved_references=(
                len(old_indices) if name == "old" else len(new_indices)
            )
            - len(lib["x"]),
        )
        for name, lib in libraries.items()
    }
    frozen = dict(
        config=CONFIG,
        input_hashes={k: v["sha256"] for k, v in hashes.items()},
        maps=MAPS,
        atoms=ATOMS,
        schemes=SCHEMES,
        analysis_code_sha256=sha(__file__),
        kernel_sha256=sha(EXH / "stream_mesma.py"),
        legacy_helpers_sha256=sha(OLD / "run_analysis.py"),
        package_helpers_sha256={
            n: sha(ROOT / "src/spectralbridge" / n)
            for n in ["mixtures.py", "library_analysis.py"]
        },
    )
    cp = OUT / "protocol.json"
    if cp.exists() and json.loads(cp.read_text()) != frozen:
        raise ValueError("Frozen protocol changed; use a new version directory")
    save_json(cp, frozen)
    save_json(OUT / "input_audit.json", audit)
    meta.to_csv(OUT / "tables/target_membership.csv", index=False)
    np.savez_compressed(
        OUT / "synthetic_targets.npz",
        spectra=sx,
        atomic_truth=truth,
        bundle_parents=refs,
    )
    pool[["GlobalID", "atom", "site", "year"]].to_csv(
        OUT / "tables/observed_target_identity.csv", index=False
    )
    support = (
        pool.groupby(["site", "year", "atom"])
        .agg(IDs=("GlobalID", "nunique"), curves=("GlobalID", "size"))
        .reset_index()
    )
    support.to_csv(OUT / "tables/target_support.csv", index=False)
    print(
        f"Prepared {len(sx)} identical synthetic targets in {meta.bundle.nunique()} bundles; {len(selected_union)} selected IDs excluded; {len(pool)} observed target curves.",
        flush=True,
    )
    return libraries, pool, sx, truth, meta, refs, bandnames


def small_analyses(libraries, pool, sx, truth, meta, refs, bands):
    coverage_rows = []
    ambiguity = []
    for name, lib in libraries.items():
        # One training spectrum/truth design shared by both label schemes.
        tx, tt, groups, membership = training_mixtures(
            lib["x"], lib["atoms"], lib["ids"]
        )
        save_json(OUT / "models" / f"{name}_training_memberships.json", membership)
        for scheme in SCHEMES:
            print(
                f"{name}/{scheme}: observed coverage, convex certificates, ridge",
                flush=True,
            )
            cov, detail = coverage(
                pool[bands].to_numpy(),
                pool.atom.to_numpy(str),
                pool.GlobalID.to_numpy(str),
                lib["x"],
                lib["atoms"],
                scheme,
            )
            cov["library"] = name
            cov["scheme"] = scheme
            coverage_rows.extend(cov.to_dict("records"))
            pool[["GlobalID", "site", "year", "atom"]].reset_index(drop=True).join(
                detail.set_index("row")
            ).to_csv(OUT / "tables" / f"coverage_{name}_{scheme}.csv", index=False)
            path = OUT / "models" / f"{name}_{scheme}_ridge.npz"
            if not path.exists():
                mapped = tt @ mapping_matrix(scheme)
                model = fit_ridge_fractions(
                    tx,
                    mapped,
                    groups=groups,
                    alphas=CONFIG["ridge_alphas"],
                    folds=3,
                    seed=CONFIG["seed"],
                    class_order=SCHEMES[scheme],
                )
                prediction = model.predict(sx)
                np.savez_compressed(
                    path,
                    prediction=prediction["projected_prediction"],
                    raw_prediction=prediction["raw_prediction"],
                )
                # Exact package model metadata and scaler/coefficient values are serializable.
                save_json(
                    OUT / "models" / f"{name}_{scheme}_ridge_metadata.json",
                    dict(
                        tuning=model.tuning,
                        chosen_alpha=model.preprocessing["alpha"],
                        classes=SCHEMES[scheme],
                    ),
                )
                estimator = model.pipeline
                np.savez_compressed(
                    OUT / "models" / f"{name}_{scheme}_ridge_parameters.npz",
                    scale_mean=estimator.named_steps["scale"].mean_,
                    scale=estimator.named_steps["scale"].scale_,
                    coefficient=estimator.named_steps["model"].coef_,
                    intercept=estimator.named_steps["model"].intercept_,
                )
            labels = label_codes(lib["atoms"], scheme)
            for i, e in enumerate(lib["x"]):
                cert = legacy.cross_class_certificate(
                    e, int(labels[i]), lib["x"], labels
                )
                if cert["feasible"]:
                    weights = cert["weights"]
                    ix = cert["local_indices"]
                    assert (
                        np.all(labels[ix] != labels[i])
                        and np.min(weights) >= 0
                        and np.isclose(weights.sum(), 1, atol=1e-8)
                    )
                    assert np.sqrt(np.mean((weights @ lib["x"][ix] - e) ** 2)) <= 1e-8
                ambiguity.append(
                    dict(
                        library=name,
                        scheme=scheme,
                        array_index=int(lib["indices"][i]),
                        class_code=int(labels[i]),
                        category=SCHEMES[scheme][labels[i]],
                        feasible=cert["feasible"],
                        RMSE=cert.get("RMSE", np.nan),
                    )
                )
            # Training-recipe prior: no target fractions used to choose it.
            prior = (tt @ mapping_matrix(scheme)).mean(0)
            np.savez_compressed(
                OUT / "models" / f"{name}_{scheme}_prior.npz",
                prediction=np.tile(prior, (len(sx), 1)),
            )
    pd.DataFrame(coverage_rows).to_csv(OUT / "tables/coverage_summary.csv", index=False)
    pd.DataFrame(ambiguity).to_csv(OUT / "tables/convex_ambiguity.csv", index=False)
    # Known actual generating parents are a numerical positive control only.
    oracle = []
    for i, reference in enumerate(refs):
        use = meta.bundle.eq(i).to_numpy()
        fit = fcls(sx[use], reference)
        oracle.extend(np.mean((fit["fractions"] - truth[use]) ** 2, axis=1))
    save_json(
        OUT / "oracle.json", dict(atomic_fraction_RMSE=float(np.sqrt(np.mean(oracle))))
    )


def exhaustive(libraries, sx):
    for scheme in SCHEMES:
        for name, lib in libraries.items():
            print(
                f"EXHAUSTIVE {name}/{scheme}: {len(lib['x'])} candidates; {len(sx)} targets",
                flush=True,
            )
            path = OUT / "models" / f"{name}_{scheme}_mesma.npz"
            if path.exists():
                print("Reused completed result " + path.name, flush=True)
                continue
            result = stream.search(
                sx,
                lib["x"],
                label_codes(lib["atoms"], scheme),
                directory=OUT / "checkpoints" / f"{name}_{scheme}",
                chunk_models=CONFIG["chunk_models"],
            )
            assert np.array_equal(result["classes"], np.arange(5))
            assert np.allclose(result["RMSE"], result["direct_RMSE"], atol=2e-7)
            np.savez_compressed(
                path,
                prediction=result["fractions"],
                spectral_RMSE=result["direct_RMSE"],
                reference_indices=result["model_indices"],
                reference_fractions=result["member_fractions"],
                complexity=result["complexity"],
            )
            save_json(
                OUT / "models" / f"{name}_{scheme}_mesma_metadata.json",
                dict(
                    model_count=result["model_count"],
                    seconds=result["seconds"],
                    max_components=3,
                    one_reference_per_category=True,
                ),
            )


def capacity_controls(libraries, sx):
    limits = {
        a: min(
            np.sum(libraries["old"]["atoms"] == a),
            np.sum(libraries["new"]["atoms"] == a),
        )
        for a in ATOMS
    }
    records = []
    for rep in range(CONFIG["capacity_control_draws"]):
        for name, lib in libraries.items():
            rng = np.random.default_rng(CONFIG["seed"] + 1000 + rep)
            ix = np.concatenate(
                [
                    rng.choice(
                        np.flatnonzero(lib["atoms"] == a), int(limits[a]), replace=False
                    )
                    for a in ATOMS
                ]
            )
            tx, tt, groups, _ = training_mixtures(
                lib["x"][ix], lib["atoms"][ix], lib["ids"][ix], CONFIG["seed"]
            )
            for scheme in SCHEMES:
                path = OUT / "models" / f"capacity_{rep}_{name}_{scheme}_ridge.npz"
                if not path.exists():
                    fit = fit_ridge_fractions(
                        tx,
                        tt @ mapping_matrix(scheme),
                        groups=groups,
                        alphas=CONFIG["ridge_alphas"],
                        folds=3,
                        class_order=SCHEMES[scheme],
                    )
                    np.savez_compressed(
                        path, prediction=fit.predict(sx)["projected_prediction"]
                    )
                records.append(
                    dict(
                        replicate=rep,
                        library=name,
                        scheme=scheme,
                        references=len(ix),
                        parent_IDs=len(np.unique(lib["ids"][ix])),
                        indices="|".join(map(str, lib["indices"][ix])),
                    )
                )
        print(
            f"Equal-atomic-count ridge control {rep + 1}/{CONFIG['capacity_control_draws']}",
            flush=True,
        )
    pd.DataFrame(records).to_csv(OUT / "tables/capacity_controls.csv", index=False)


def summarize(truth, meta):
    rows = []
    predictions = {}
    per_category = []
    domains = []
    commontruth = truth @ mapping_matrix("common")
    for scheme in SCHEMES:
        target = truth @ mapping_matrix(scheme)
        for name in ["old", "new"]:
            for method in ["ridge", "mesma", "prior"]:
                path = OUT / "models" / f"{name}_{scheme}_{method}.npz"
                if not path.exists():
                    continue
                with np.load(path, allow_pickle=False) as z:
                    p = z["prediction"]
                    res = (
                        float(np.mean(z["spectral_RMSE"]))
                        if "spectral_RMSE" in z
                        else None
                    )
                assert (
                    p.shape == target.shape
                    and np.isfinite(p).all()
                    and p.min() >= -1e-9
                    and np.allclose(p.sum(1), 1)
                )
                cp = coarsen(p, scheme)
                key = f"{name}/{scheme}/{method}"
                predictions[key] = cp
                native = np.mean((p - target) ** 2, axis=1)
                common = np.mean((cp - commontruth) ** 2, axis=1)
                rows.append(
                    dict(
                        library=name,
                        scheme=scheme,
                        method=method,
                        native_fraction_RMSE=np.sqrt(native.mean()),
                        common_fraction_RMSE=np.sqrt(common.mean()),
                        mean_spectral_RMSE=res,
                    )
                )
                for j, cat in enumerate(SCHEMES[scheme]):
                    per_category.append(
                        dict(
                            library=name,
                            scheme=scheme,
                            method=method,
                            category=cat,
                            RMSE=np.sqrt(np.mean((p[:, j] - target[:, j]) ** 2)),
                            bias=np.mean(p[:, j] - target[:, j]),
                        )
                    )
                d = meta.copy()
                d["native_MSE"] = native
                d["common_MSE"] = common
                for (site, year), g in d.groupby(["site", "year"]):
                    domains.append(
                        dict(
                            library=name,
                            scheme=scheme,
                            method=method,
                            site=site,
                            year=int(year),
                            native_RMSE=np.sqrt(g.native_MSE.mean()),
                            common_RMSE=np.sqrt(g.common_MSE.mean()),
                        )
                    )
                d["library"] = name
                d["scheme"] = scheme
                d["method"] = method
                for j in range(5):
                    d[f"prediction_{j}"] = p[:, j]
                    d[f"truth_{j}"] = target[:, j]
                d.to_csv(
                    OUT / "tables" / f"predictions_{name}_{scheme}_{method}.csv",
                    index=False,
                )
    pd.DataFrame(rows).to_csv(OUT / "tables/fraction_summary.csv", index=False)
    pd.DataFrame(per_category).to_csv(
        OUT / "tables/fraction_by_category.csv", index=False
    )
    pd.DataFrame(domains).to_csv(OUT / "tables/fraction_by_domain.csv", index=False)
    # Paired bootstrap resamples the eight whole parent bundles, not 568 rows.
    rng = np.random.default_rng(CONFIG["seed"])
    bundles = np.unique(meta.bundle)
    draws = rng.integers(
        0, len(bundles), size=(CONFIG["bootstrap_draws"], len(bundles))
    )
    comparisons = []
    pairs = []
    for scheme in SCHEMES:
        for method in ["ridge", "mesma"]:
            pairs.append(
                (f"old/{scheme}/{method}", f"new/{scheme}/{method}", "selection")
            )
    for lib in ["old", "new"]:
        for method in ["ridge", "mesma"]:
            pairs.append(
                (
                    f"{lib}/original/{method}",
                    f"{lib}/revised/{method}",
                    "category_scheme",
                )
            )
    for baseline, alternative, kind in pairs:
        if baseline not in predictions or alternative not in predictions:
            continue
        errors = []
        for key in [baseline, alternative]:
            v = np.mean((predictions[key] - commontruth) ** 2, axis=1)
            errors.append(
                np.array([v[meta.bundle.eq(b).to_numpy()].mean() for b in bundles])
            )
        diff = np.sqrt(errors[1][draws].mean(1)) - np.sqrt(errors[0][draws].mean(1))
        comparisons.append(
            dict(
                comparison=kind,
                baseline=baseline,
                alternative=alternative,
                common_RMSE_delta=float(
                    np.sqrt(errors[1].mean()) - np.sqrt(errors[0].mean())
                ),
                conditional_2_5=float(np.quantile(diff, 0.025)),
                conditional_97_5=float(np.quantile(diff, 0.975)),
            )
        )
    pd.DataFrame(comparisons).to_csv(OUT / "tables/paired_comparisons.csv", index=False)
    controls = []
    for path in sorted((OUT / "models").glob("capacity_*_ridge.npz")):
        _, rep, name, scheme, _ = path.stem.split("_")
        with np.load(path, allow_pickle=False) as z:
            p = z["prediction"]
        controls.append(
            dict(
                replicate=int(rep),
                library=name,
                scheme=scheme,
                common_RMSE=float(
                    np.sqrt(np.mean((coarsen(p, scheme) - commontruth) ** 2))
                ),
            )
        )
    pd.DataFrame(controls).to_csv(
        OUT / "tables/capacity_control_scores.csv", index=False
    )
    save_json(
        OUT / "summary.json",
        dict(
            status="complete"
            if len(rows) == 12
            else "partial - exhaustive fits pending",
            metrics=rows,
            paired_comparisons=comparisons,
            config=CONFIG,
            input_audit_sha256=sha(OUT / "input_audit.json"),
            protocol_sha256=sha(OUT / "protocol.json"),
        ),
    )
    print(pd.DataFrame(rows).to_string(index=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=["prepare", "small", "exhaustive", "controls", "summarize", "all"],
        default="all",
    )
    args = parser.parse_args()
    start = time.monotonic()
    data = prepare()
    libraries, pool, sx, truth, meta, refs, bands = data
    if args.stage in ["small", "all"]:
        small_analyses(*data)
    if args.stage in ["controls", "all"]:
        capacity_controls(libraries, sx)
    if args.stage in ["exhaustive", "all"]:
        exhaustive(libraries, sx)
    if args.stage != "prepare":
        summarize(truth, meta)
    print(
        f"Completed stage {args.stage} in {time.monotonic() - start:.1f}s", flush=True
    )


if __name__ == "__main__":
    main()
