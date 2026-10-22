"""Independent identity, prediction, reconstruction and score checks; no refits."""

from itertools import combinations
from pathlib import Path
import hashlib
import json
import math
import platform

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial.distance import cdist

from spectralbridge.library_analysis import project_simplex

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ATOMS = ["Deciduous", "Evergreen", "Herbaceous", "Woody shrub", "Bare_Rock", "Dead"]
ATOM_MAP = {"original": [0, 1, 2, 4, 3, 3], "revised": [0, 1, 2, 2, 3, 4]}
COMMON_MAP = {"original": [0, 1, 2, 3, 2], "revised": [0, 1, 2, 3, 3]}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def read(name):
    return pd.read_csv(OUT / "tables" / (name + ".csv"))


def js(path):
    return json.loads(Path(path).read_text())


def main():
    audit = js(OUT / "input_audit.json")
    protocol = js(OUT / "protocol.json")
    summary = js(OUT / "summary.json")
    assert summary["status"] == "complete"
    assert sha(OUT / "run_comparison.py") == protocol["analysis_code_sha256"]
    assert (
        sha(
            ROOT
            / "provenance/endmember-quality/2026-10-19/exhaustive-v1/stream_mesma.py"
        )
        == protocol["kernel_sha256"]
    )
    for key, record in audit["inputs"].items():
        assert (
            sha(record["path"]) == record["sha256"] == protocol["input_hashes"][key]
        ), key
    for path, digest in protocol["package_helpers_sha256"].items():
        assert sha(ROOT / "src/spectralbridge" / path) == digest
    # Old data and index base were verified previously; derive new row lineage
    # independently from identity keys, not the inherited indexing convention.
    columns = [
        "GlobalID",
        "flight_id",
        "pixel_id",
        "row",
        "col",
        "cover_category",
        "cover_subcategory",
    ]
    source = pq.read_table(
        audit["inputs"]["source"]["path"], columns=columns
    ).to_pandas()
    new = pd.read_csv(
        audit["inputs"]["new_csv"]["path"],
        usecols=["Unnamed: 0", "new_class"] + columns,
        low_memory=False,
    )
    keys = ["GlobalID", "flight_id", "pixel_id", "row", "col"]
    joined = new[keys].merge(
        source.reset_index(names="source_index"),
        on=keys,
        validate="one_to_one",
        how="left",
        sort=False,
    )
    assert joined.source_index.notna().all()
    indices = joined.source_index.to_numpy(int)
    np.testing.assert_array_equal(indices, new["Unnamed: 0"].to_numpy() - 1)
    raw = np.load(audit["inputs"]["old_spectra"]["path"], allow_pickle=False).T
    new_values = np.load(audit["inputs"]["new_spectra"]["path"], allow_pickle=False).T
    np.testing.assert_array_equal(new_values, raw[indices])
    previous_indices = (
        pd.read_csv(audit["inputs"]["old_selection"]["path"]).iloc[:, 0].to_numpy()
    )
    union = set(source.iloc[np.r_[indices, previous_indices]].GlobalID)
    assert len(union) == audit["selected_union_IDs"]
    observed = read("observed_target_identity")
    assert observed.GlobalID.nunique() == audit["target_IDs"]
    assert len(observed) == audit["target_curves"]
    assert set(observed.GlobalID).isdisjoint(union)
    assert not observed.duplicated(["GlobalID", "site", "year"]).any()
    # Rebuild observed parent medians from the original small seven-band array
    # and source metadata; never cache the pixel-scale table on disk.
    source["atom"] = source.cover_category.astype("string")
    bg = source.cover_category.eq("Non-vegetated & dead")
    source.loc[bg, "atom"] = source.loc[bg, "cover_subcategory"].map(
        {"Bare": "Bare_Rock", "Rock": "Bare_Rock", "Dead": "Dead"}
    )
    source["site"] = source.flight_id.str.extract(r"_([A-Z]{4})_DP1")[0]
    source["year"] = source.flight_id.str.extract(r"_(\d{8})_")[0].str[:4].astype(int)
    bandnames = [f"band_{i}" for i in range(7)]
    source[bandnames] = raw
    flight = source.groupby(
        ["GlobalID", "cover_category", "atom", "site", "year", "flight_id"],
        dropna=False,
    )[bandnames].median()
    parent = (
        flight.groupby(
            level=["GlobalID", "cover_category", "atom", "site", "year"], dropna=False
        )
        .median()
        .reset_index()
    )
    pool = parent[parent.atom.notna() & ~parent.GlobalID.isin(union)].reset_index(
        drop=True
    )
    assert (
        pool[["GlobalID", "atom", "site", "year"]]
        .astype(str)
        .equals(observed[["GlobalID", "atom", "site", "year"]].astype(str))
    )
    coverage_summary = read("coverage_summary")
    _, inv, counts = np.unique(
        pool.GlobalID.to_numpy(), return_inverse=True, return_counts=True
    )
    weights = 1 / counts[inv]
    for lib in ["old", "new"]:
        refs = read(lib + "_selected_identity")
        distances = cdist(
            pool[bandnames].to_numpy(), raw[refs.array_index.to_numpy()]
        ) / np.sqrt(7)
        nearest = distances.argmin(1)
        for scheme in ATOM_MAP:
            codes = np.array(ATOM_MAP[scheme])[[ATOMS.index(a) for a in refs.atom]]
            target_codes = np.array(ATOM_MAP[scheme])[
                [ATOMS.index(a) for a in pool.atom]
            ]
            detail = read(f"coverage_{lib}_{scheme}")
            np.testing.assert_array_equal(codes[nearest], detail.prediction)
            np.testing.assert_array_equal(target_codes, detail.truth)
            for k in range(5):
                use = target_codes == k
                same = distances[:, codes == k].min(1)
                values = coverage_summary[
                    (coverage_summary.library.eq(lib))
                    & (coverage_summary.scheme.eq(scheme))
                ].iloc[k]
                expected_recall = np.average(
                    codes[nearest][use] == k, weights=weights[use]
                )
                expected_distance = np.average(same[use], weights=weights[use])
                assert math.isclose(expected_recall, values.recall, abs_tol=1e-12)
                assert math.isclose(
                    expected_distance, values.same_category_RMSE, abs_tol=1e-12
                )
                np.testing.assert_allclose(
                    same[use], detail.same_category_RMSE.to_numpy()[use], atol=1e-12
                )

    meta = read("target_membership")
    with np.load(OUT / "synthetic_targets.npz", allow_pickle=False) as z:
        x = z["spectra"]
        truth = z["atomic_truth"]
        parents = z["bundle_parents"]
    assert (
        x.shape == (568, 7) and truth.shape == (568, 6) and parents.shape == (8, 6, 7)
    )
    assert meta.target.tolist() == list(range(len(x)))
    assert np.isfinite(x).all() and truth.min() >= 0
    np.testing.assert_allclose(truth.sum(1), 1)
    np.testing.assert_allclose(truth.mean(0), np.repeat(1 / 6, 6))
    seen = set()
    for bid, g in meta.groupby("bundle"):
        ids = set(g.parent_ids.iloc[0].split("|"))
        assert len(ids) == 6 and ids.isdisjoint(seen) and ids.isdisjoint(union)
        seen.update(ids)
        use = meta.bundle.eq(bid).to_numpy()
        np.testing.assert_allclose(truth[use] @ parents[bid], x[use], atol=1e-14)
        assert len(g) == 71 and g.components.value_counts().to_dict() == {
            2: 45,
            3: 20,
            1: 6,
        }
    commontruth = truth @ np.eye(4)[[0, 1, 2, 2, 3, 3]]
    scores = read("fraction_summary").set_index(["library", "scheme", "method"])
    domains = read("fraction_by_domain")
    common_predictions = {}
    models = {}
    largest_reconstruction_difference = 0
    for name in ["old", "new"]:
        refs = read(name + "_selected_identity")
        reference = raw[refs.array_index.to_numpy()]
        if name == "new":
            np.testing.assert_array_equal(reference, new_values)
        assert len(refs) == audit["libraries"][name]["primary_eligible_references"]
        memberships = js(OUT / "models" / f"{name}_training_memberships.json")
        groups = [set(r["parent_ids"]) for r in memberships]
        assert set.union(*groups) == set(refs.GlobalID)
        assert set.union(*groups).isdisjoint(seen)
        assert all(not groups[a] & groups[b] for a in range(3) for b in range(a))
        for scheme in ATOM_MAP:
            target = truth @ np.eye(5)[ATOM_MAP[scheme]]
            for method in ["ridge", "mesma", "prior"]:
                path = OUT / "models" / f"{name}_{scheme}_{method}.npz"
                with np.load(path, allow_pickle=False) as z:
                    pred = z["prediction"]
                    assert (
                        pred.shape == target.shape
                        and pred.min() >= -1e-9
                        and np.isfinite(pred).all()
                    )
                    np.testing.assert_allclose(pred.sum(1), 1)
                    common = pred @ np.eye(4)[COMMON_MAP[scheme]]
                    native_rmse = np.sqrt(np.mean((pred - target) ** 2))
                    common_rmse = np.sqrt(np.mean((common - commontruth) ** 2))
                    recorded = scores.loc[(name, scheme, method)]
                    assert math.isclose(
                        native_rmse, recorded.native_fraction_RMSE, abs_tol=1e-12
                    )
                    assert math.isclose(
                        common_rmse, recorded.common_fraction_RMSE, abs_tol=1e-12
                    )
                    class_rows = read("fraction_by_category")
                    class_rows = class_rows[
                        (class_rows.library.eq(name))
                        & (class_rows.scheme.eq(scheme))
                        & (class_rows.method.eq(method))
                    ]
                    np.testing.assert_allclose(
                        np.sqrt(np.mean((pred - target) ** 2, axis=0)),
                        class_rows.RMSE.to_numpy(),
                        atol=1e-12,
                    )
                    np.testing.assert_allclose(
                        np.mean(pred - target, axis=0),
                        class_rows.bias.to_numpy(),
                        atol=1e-12,
                    )
                    common_predictions[f"{name}/{scheme}/{method}"] = common
                    if method == "mesma":
                        labels = np.array(ATOM_MAP[scheme])[
                            [ATOMS.index(a) for a in refs.atom]
                        ]
                        counts = np.bincount(labels, minlength=5)
                        nmodels = sum(
                            math.prod(int(counts[i]) for i in c)
                            for k in [1, 2, 3]
                            for c in combinations(range(5), k)
                        )
                        info = js(
                            OUT / "models" / f"{name}_{scheme}_mesma_metadata.json"
                        )
                        assert nmodels == info["model_count"]
                        models[f"{name}/{scheme}"] = nmodels
                        ix = z["reference_indices"]
                        weights = z["reference_fractions"]
                        recon = np.zeros_like(x)
                        classf = np.zeros_like(pred)
                        assert ix.shape == weights.shape == (len(x), 3)
                        assert weights.min() >= -1e-12
                        np.testing.assert_allclose(weights.sum(1), 1)
                        for j in range(3):
                            use = np.flatnonzero(ix[:, j] >= 0)
                            recon[use] += weights[use, j, None] * reference[ix[use, j]]
                            classf[use, labels[ix[use, j]]] += weights[use, j]
                        for row in range(len(ix)):
                            active = ix[row][ix[row] >= 0]
                            assert len(active) == len(np.unique(labels[active])) <= 3
                        np.testing.assert_allclose(classf, pred, atol=1e-12)
                        residual = np.sqrt(np.mean((recon - x) ** 2, axis=1))
                        largest_reconstruction_difference = max(
                            largest_reconstruction_difference,
                            float(np.max(np.abs(residual - z["spectral_RMSE"]))),
                        )
                        np.testing.assert_allclose(
                            residual, z["spectral_RMSE"], atol=1e-12
                        )
                        assert math.isclose(
                            residual.mean(), recorded.mean_spectral_RMSE, abs_tol=1e-12
                        )
                        cp = OUT / "checkpoints" / f"{name}_{scheme}"
                        cfg = js(cp / "config.json")
                        assert cfg["count"] == nmodels
                        assert len(list(cp.glob("composition_*.npz"))) == 25
                        with np.load(
                            cp / "composition_24.npz", allow_pickle=False
                        ) as final:
                            np.testing.assert_array_equal(final["bestix"], ix)
                            np.testing.assert_allclose(final["bestf"], weights, atol=0)
                    elif method == "ridge":
                        with np.load(
                            OUT / "models" / f"{name}_{scheme}_ridge_parameters.npz",
                            allow_pickle=False,
                        ) as parameters:
                            raw_pred = (
                                (x - parameters["scale_mean"]) / parameters["scale"]
                            ) @ parameters["coefficient"].T + parameters["intercept"]
                        np.testing.assert_allclose(
                            raw_pred, z["raw_prediction"], atol=1e-12
                        )
                        np.testing.assert_allclose(
                            project_simplex(raw_pred), pred, atol=1e-12
                        )
                        info = js(
                            OUT / "models" / f"{name}_{scheme}_ridge_metadata.json"
                        )
                        chosen = info["tuning"]["alphas"][
                            int(np.argmin(info["tuning"]["MSE"]))
                        ]
                        assert chosen == info["chosen_alpha"]
                    else:
                        # Training design is symmetric over six atomic parents;
                        # this prior is defined without using held-out fractions.
                        expected = np.repeat(1 / 6, 6) @ np.eye(5)[ATOM_MAP[scheme]]
                        np.testing.assert_allclose(pred, np.tile(expected, (len(x), 1)))
                    for (site, year), g in meta.groupby(["site", "year"]):
                        use = g.index.to_numpy()
                        r = domains[
                            (domains.library.eq(name))
                            & (domains.scheme.eq(scheme))
                            & (domains.method.eq(method))
                            & (domains.site.eq(site))
                            & (domains.year.eq(year))
                        ].iloc[0]
                        assert math.isclose(
                            np.sqrt(np.mean((common[use] - commontruth[use]) ** 2)),
                            r.common_RMSE,
                            abs_tol=1e-12,
                        )
    rng = np.random.default_rng(20261022)
    draws = rng.integers(0, 8, size=(1999, 8))
    comparisons = read("paired_comparisons")
    for r in comparisons.itertuples():
        errors = []
        for key in [r.baseline, r.alternative]:
            v = np.mean((common_predictions[key] - commontruth) ** 2, axis=1)
            errors.append(
                np.array([v[meta.bundle.eq(b).to_numpy()].mean() for b in range(8)])
            )
        delta = np.sqrt(errors[1][draws].mean(1)) - np.sqrt(errors[0][draws].mean(1))
        assert math.isclose(
            r.common_RMSE_delta,
            np.sqrt(errors[1].mean()) - np.sqrt(errors[0].mean()),
            abs_tol=1e-12,
        )
        np.testing.assert_allclose(
            [r.conditional_2_5, r.conditional_97_5],
            np.quantile(delta, [0.025, 0.975]),
            atol=1e-12,
        )
    # Verify the stored numerical witnesses, not just feasibility flags.
    certificates = read("convex_certificate_weights")
    flags = read("convex_ambiguity").set_index(["library", "scheme", "array_index"])
    verified = set()
    for (lib, scheme, target), group in certificates.groupby(
        ["library", "scheme", "target_array_index"]
    ):
        refs = read(lib + "_selected_identity").set_index("array_index")
        alternatives = group.alternative_array_index.to_numpy(int)
        weights = group.weight.to_numpy(float)
        own = ATOM_MAP[scheme][ATOMS.index(refs.loc[target, "atom"])]
        other = [
            ATOM_MAP[scheme][ATOMS.index(a)] for a in refs.loc[alternatives, "atom"]
        ]
        assert all(v != own for v in other) and weights.min() >= 0
        assert abs(weights.sum() - 1) <= 1e-8
        residual = np.sqrt(
            np.mean((weights @ raw[alternatives] - raw[int(target)]) ** 2)
        )
        assert residual <= 1e-8
        assert flags.loc[(lib, scheme, target), "feasible"]
        verified.add((lib, scheme, int(target)))
    assert verified == set(flags.index[flags.feasible])
    with np.load(OUT / "models/known_parent_oracle.npz", allow_pickle=False) as oracle:
        expected = float(np.sqrt(np.mean((oracle["prediction"] - truth) ** 2)))
        assert math.isclose(
            expected, js(OUT / "oracle.json")["atomic_fraction_RMSE"], abs_tol=1e-15
        )
        np.testing.assert_allclose(oracle["reconstruction"], x, atol=1e-11)
    # Label exports preserve exact 501-column order and never invent new codes.
    options = read("new_label_options")
    assert options.selected_column.tolist() == list(range(len(new)))
    for name, column in [
        ("original_researcher", "cover_category"),
        ("revised", "new_class"),
    ]:
        values = np.load(OUT / f"new_IES_{name}_labels.npy", allow_pickle=False)
        np.testing.assert_array_equal(values, options[column].to_numpy(str))
    np.testing.assert_array_equal(options.new_class, new.new_class)
    geometry = read("ridge_relabelling_geometry")
    for row in geometry.itertuples():
        pair = []
        for scheme in ["original", "revised"]:
            with np.load(
                OUT / "models" / f"{row.library}_{scheme}_ridge.npz", allow_pickle=False
            ) as z:
                pair.append(z["raw_prediction"] @ np.eye(4)[COMMON_MAP[scheme]])
        assert np.max(np.abs(pair[0] - pair[1])) < 1e-11
        np.testing.assert_allclose(
            project_simplex(pair[0]), project_simplex(pair[1]), atol=1e-11
        )
    figure_manifest = js(OUT / "figure_manifest.json")
    assert len(figure_manifest["figures"]) == 8
    assert sha(OUT / "build_report.py") == figure_manifest["report_builder_sha256"]
    assert sha(OUT / "summary.json") == figure_manifest["summary_sha256"]
    for figure in figure_manifest["figures"]:
        assert all((OUT / source).is_file() for source in figure["sources"])
        for ext, digest in figure["sha256"].items():
            assert sha(OUT / "figures" / (figure["id"] + "." + ext)) == digest

    # Preserve every previously delivered briefing file and the older source
    # scripts used here; no historic packet is silently overwritten.
    preserved = {}
    prior = ROOT / "provenance/pft-scientific-update/2026-10-22/v1/packet_manifest.json"
    for path, digest in js(prior)["files"].items():
        assert sha(ROOT / path) == digest, path
        preserved[path] = digest
    result = dict(
        status="PASS",
        source_inputs_verified=len(audit["inputs"]),
        primary_cells=4,
        prediction_sets=12,
        observed_target_IDs=audit["target_IDs"],
        synthetic_targets=len(x),
        disjoint_target_parents=len(seen),
        target_bundles=8,
        exhaustive_models_per_target=models,
        maximum_direct_reconstruction_check_difference=largest_reconstruction_difference,
        paired_comparisons_verified=len(comparisons),
        convex_witnesses_verified=len(verified),
        label_options_verified=2,
        figure_pairs_verified=8,
        ridge_shared_raw_invariance_verified=True,
        prior_briefing_files_preserved=len(preserved),
        physical_abundance_validated=False,
        selection_blind=False,
        raw_spectral_library_copied=False,
        source_parquet_copied=False,
        environment=dict(
            python=platform.python_version(),
            numpy=np.__version__,
            pandas=pd.__version__,
        ),
    )
    (OUT / "validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
