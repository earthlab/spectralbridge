"""Independent numerical replay of compact endmember diagnostics and certificates."""

from pathlib import Path
from itertools import combinations
import hashlib
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from preflight import ROOT, INPUT, labels

OUT = Path(__file__).resolve().parent
TABLES = OUT / "tables"
CLASSES = np.array(
    ["Deciduous", "Evergreen", "Herbaceous", "Non-vegetated & dead", "Woody shrub"]
)


def read(name):
    return pd.read_csv(TABLES / (name + ".csv"), float_precision="round_trip")


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    s = json.loads((OUT / "summary.json").read_text())
    for path, digest in s["input_sha256"].items():
        assert sha(Path(path)) == digest, path
    assert sha(OUT / "run_analysis.py") == s["code_sha256"]
    x = np.load(INPUT / "library_oli_undarkened_10_12_26.npy", allow_pickle=False).T
    y = labels(INPUT / "class_list_oli_undarkened_10_12_26.npy")
    members = read("selected_members")
    ix = members.array_index.to_numpy()
    bands = [c for c in members if c.startswith("olioli_undarkened_b")]
    np.testing.assert_allclose(members[bands].to_numpy(), x[ix], rtol=0, atol=1e-15)
    np.testing.assert_array_equal(members.category, y[ix])
    np.testing.assert_array_equal(
        members.class_code, [list(CLASSES).index(c) + 1 for c in y[ix]]
    )
    p = ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    source = pq.read_table(
        p, columns=["GlobalID", "cover_category", "flight_id"]
    ).to_pandas()
    source["site"] = source.flight_id.str.extract(r"_([A-Z]{4})_DP1")[0]
    source["year"] = source.flight_id.str.extract(r"_(\d{8})_")[0].str[:4].astype(int)
    for j, b in enumerate(bands):
        source[b] = x[:, j]
    flight = source.groupby(
        ["GlobalID", "cover_category", "site", "year", "flight_id"]
    )[bands].median()
    parent = (
        flight.groupby(level=["GlobalID", "cover_category", "site", "year"])
        .median()
        .reset_index()
    )
    target = read("target_coverage")
    joined = target.merge(
        parent, on=["GlobalID", "site", "year"], validate="one_to_one"
    )
    assert len(joined) == len(target) and set(target.GlobalID).isdisjoint(
        set(members.GlobalID)
    )
    assert target.GlobalID.nunique() == 3272 and len(target) == 4261
    # Independent broadcast differences, rather than the analysis cdist calculation.
    ty = target.category.to_numpy()
    tx = joined[bands].to_numpy()
    end = x[ix]
    ey = y[ix]
    predicted = []
    same = []
    nearest = []
    for start in range(0, len(tx), 200):
        chunk = tx[start : start + 200]
        d = np.sqrt(np.mean((chunk[:, None, :] - end[None, :, :]) ** 2, axis=2))
        predicted.extend(ey[d.argmin(1)])
        nearest.extend(d.min(1))
        for row, c in enumerate(ty[start : start + len(chunk)]):
            same.append(d[row, ey == c].min())
    np.testing.assert_array_equal(predicted, target.prediction)
    np.testing.assert_allclose(same, target.same_class_RMSE, rtol=0, atol=1e-14)
    np.testing.assert_allclose(nearest, target.nearest_RMSE, rtol=0, atol=1e-14)
    class_rows = read("coverage_selected").set_index("category")
    for c in CLASSES:
        use = ty == c
        w = 1 / target.groupby("GlobalID").GlobalID.transform("size").to_numpy()[use]
        assert np.isclose(
            np.average(np.asarray(predicted)[use] == c, weights=w),
            class_rows.loc[c, "recall"],
        )
        assert np.isclose(
            np.average(np.asarray(same)[use], weights=w),
            class_rows.loc[c, "mean_same_class_RMSE"],
        )
    # Verify all 223 saved alternative mixtures against the ORIGINAL NPY values.
    certificates = read("cross_class_hull")
    weights = read("cross_class_hull_weights")
    verified = []
    for target_index, g in weights.groupby("target_array_index"):
        alternative_indices = g.alternative_array_index.to_numpy()
        f = g.weight.to_numpy()
        assert (
            np.all(y[alternative_indices] != y[target_index])
            and f.min() >= 0
            and abs(f.sum() - 1) < 1e-8
        )
        error = np.sqrt(np.mean((f @ x[alternative_indices] - x[target_index]) ** 2))
        assert error <= 1e-8
        verified.append(target_index)
    assert (
        set(verified) == set(certificates[certificates.feasible].array_index)
        and len(verified) == 223
    )
    # Reconstruct every target from stored source parents; verify whole-bundle disjointness.
    primary = read("selected_synthetic_predictions").sort_values("target")
    truth = primary[[f"truth_{j}" for j in range(1, 6)]].to_numpy()
    targets = []
    used = set()
    lookup = parent.set_index(["GlobalID", "site", "year"])
    for bundle, g in primary.groupby("bundle"):
        ids = g.parent_ids.iloc[0].split("|")
        assert g.parent_ids.nunique() == 1 and set(ids).isdisjoint(used)
        assert set(ids).isdisjoint(set(members.GlobalID))
        used.update(ids)
    for _, row in primary.iterrows():
        ids = row.parent_ids.split("|")
        e = np.array(
            [lookup.loc[(i, row.site, int(row.year)), bands].to_numpy() for i in ids]
        )
        targets.append(
            row[[f"truth_{j}" for j in range(1, 6)]].to_numpy(dtype=float) @ e
        )
    targets = np.asarray(targets)
    detail = read("screened_mesma_details")
    files = {
        "Selected screened MESMA": "selected",
        "Matched random screened MESMA": "matched",
        "Screen1 sensitivity": "screen1",
        "Screen2 sensitivity": "screen2",
        "Screen5 sensitivity": "screen5",
        "Uniform design prior": "uniform",
        "Sparse design prior": "sparse",
        "Known-parent FCLS oracle": "known-parent",
    }
    prediction = {}
    for method, prefix in files.items():
        frame = read(prefix + "_synthetic_predictions").sort_values("target")
        f = frame[[f"prediction_{j}" for j in range(1, 6)]].to_numpy()
        np.testing.assert_allclose(f.sum(1), 1, rtol=0, atol=1e-10)
        assert f.min() >= 0
        prediction[method] = f
        assert np.isclose(
            np.sqrt(np.mean((truth - f) ** 2)),
            s["synthetic_RMSE"][method],
            rtol=0,
            atol=1e-12,
        )
    dense = prediction["Uniform design prior"]
    sparse = prediction["Sparse design prior"]
    assert np.all(np.sum(sparse > 0, axis=1) == 3) and np.allclose(dense, 0.2)
    # Independent analytic consequence of balanced mean truth (.2 per category).
    np.testing.assert_allclose(truth.mean(0), 0.2)
    assert (
        abs(np.mean((truth - sparse) ** 2) - np.mean((truth - dense) ** 2) - 2 / 75)
        < 1e-12
    )
    replayed = 0
    for _, row in detail.iterrows():
        target_index = int(row.target)
        model = np.array(list(map(int, row.selected_array_indices.split("|"))))
        f = np.array(list(map(float, row.selected_component_fractions.split("|"))))
        shortlist = np.array(list(map(int, row.screened_array_indices.split("|"))))
        assert (
            len(model) <= 3
            and len(np.unique(y[model])) == len(model)
            and set(model) <= set(shortlist)
        )
        assert f.min() >= 0 and abs(f.sum() - 1) < 1e-10
        error = np.sqrt(np.mean((f @ x[model] - targets[target_index]) ** 2))
        assert abs(error - row.reconstruction_RMSE) < 1e-8
        class_f = np.array([f[y[model] == c].sum() for c in CLASSES])
        np.testing.assert_allclose(
            class_f, prediction[row.method][target_index], atol=1e-12
        )
        replayed += 1
    # Independently enumerate affine faces with lstsq on 12 prespecified targets.
    sampled = np.linspace(0, len(targets) - 1, 12, dtype=int)
    independent = []
    for i in sampled:
        row = detail[
            (detail.method == "Selected screened MESMA") & (detail.target == i)
        ].iloc[0]
        indices = np.array(list(map(int, row.screened_array_indices.split("|"))))
        e = x[indices]
        cats = y[indices]
        costs = []
        for size in [1, 2, 3]:
            for comb in combinations(range(len(e)), size):
                if len(np.unique(cats[list(comb)])) != size:
                    continue
                local = e[list(comb)]
                if size == 1:
                    f = np.ones(1)
                else:
                    tail = np.linalg.lstsq(
                        (local[1:] - local[0]).T, targets[i] - local[0], rcond=None
                    )[0]
                    f = np.r_[1 - tail.sum(), tail]
                if f.min() >= -1e-10:
                    costs.append(np.mean((f @ local - targets[i]) ** 2))
        assert abs(min(costs) - row.reconstruction_RMSE**2) < 1e-10
        independent.append(int(i))
    # Preserve previously sealed scientific/proof/report outputs; do not reseal them.
    preserved = {}
    for relative in [
        "provenance/researcher-pft-information/2026-10-15/v1/final_manifest.json",
        "provenance/researcher-evidence/2026-10-16/v1/final_manifest.json",
        "provenance/manuscript-synthesis/2026-10-16/v1/packet_manifest.json",
        "formal/packet_manifest.json",
        "formal/report/packet_manifest.json",
    ]:
        m = json.loads((ROOT / relative).read_text())
        for name, digest in m.get("sha256", m.get("files", {})).items():
            assert sha(ROOT / name) == digest, name
            preserved[name] = digest
    result = {
        "status": "passed",
        "verified_input_hashes": 3,
        "independent_target_coverage_rows": len(target),
        "all_cross_category_certificates_verified": len(verified),
        "synthetic_target_rows_verified": len(primary),
        "selected_model_reconstructions_replayed": replayed,
        "independent_lstsq_search_targets": independent,
        "previous_owned_files_preserved": len(preserved),
        "source_parquet_sha256": sha(p),
        "note": "No independent field truth or selection-blind validation is claimed.",
    }
    (OUT / "numerical_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
