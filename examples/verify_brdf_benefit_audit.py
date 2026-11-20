"""Independent completed-evidence contracts; no refits or endpoint selection."""

import hashlib
import json
from pathlib import Path
import h5py
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provenance/brdf-benefit-audit/2026-11-19"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def adjust(p):
    p = np.asarray(p)
    order = np.argsort(p)
    v = np.maximum.accumulate(p[order] * (len(p) - np.arange(len(p))))
    result = np.empty_like(v)
    result[order] = np.minimum(1, v)
    return result


def run():
    checks = {}
    for folder in ["hls", "aop", "drone", "aop-control", "statistics"]:
        record = json.loads((BASE / folder / "completed.json").read_text())
        for name, h in record["outputs"].items():
            assert sha(BASE / folder / name) == h, (folder, name)
        checks[folder + "_output_hashes"] = True
    d = json.loads((BASE / "drone/completed.json").read_text())
    for path, h in d["sources"].items():
        assert sha(ROOT / path) == h, path
    checks["drone_source_hashes"] = len(d["sources"])
    # Archived combined rasters and recomputed topo-only must share model ancestry.
    prior = ROOT / "provenance/drone-calibration-translation/2026-11-19"
    archive = ROOT / "archive/local/drone-calibration-translation/2026-11-19"
    fits = prior / "shade-excluded-refit-v2"
    for site in ["gordon", "goldhill", "ruby"]:
        record = json.loads(
            (
                prior
                / "conservative-refitted-products"
                / site
                / "application_complete.json"
            ).read_text()
        )
        assert record["identity"]["topo_sha256"] == sha(
            fits / site / "conservative/conditioned_scsc_model.json"
        )
        assert record["identity"]["brdf_sha256"] == sha(
            next((fits / site / "conservative/combined").glob("*brdf_model.json"))
        )
        img = next(
            (archive / "conservative-refitted-products" / site).glob(
                "*EXPERIMENTAL.img"
            )
        )
        for suffix, h in record["outputs"].items():
            assert sha(img.with_suffix(suffix)) == h
        null = json.loads(
            (
                prior / "unmasked-null-products" / site / "native_complete.json"
            ).read_text()
        )
        for path, h in {**null["identity"]["inputs"], **null["outputs"]}.items():
            assert sha(Path(path)) == h
    checks["drone_native_model_ancestry"] = True
    for sensor, file, expected in [
        ("hls", "hls/polygon_spectra.csv", 61),
        ("aop_archive", "aop/polygon_spectra.csv", 3639),
        ("drone_10pct", "drone/conservative_polygon_spectra.csv", 300),
        ("drone_unmasked", "drone/baseline_polygon_spectra.csv", 300),
    ]:
        f = pd.read_csv(BASE / file)
        keys = ["identity", "site", "category"] + (["year"] if "year" in f else [])
        a = f[f.arm == "no_brdf"].sort_values(keys).reset_index(drop=True)
        b = f[f.arm == "brdf"].sort_values(keys).reset_index(drop=True)
        assert a[keys].equals(b[keys])
        assert not a.duplicated(keys).any()
        assert a.identity.nunique() == expected
        checks[sensor + "_identities"] = expected
    memberships = pd.read_csv(BASE / "statistics/fold_memberships.csv")
    groups = ["sensor", "bands", "scheme", "arm", "fold"]
    for key, f in memberships.groupby(groups):
        assert not set(f[f.role == "train"].identity) & set(
            f[f.role == "test"].identity
        ), key
    left = (
        memberships[memberships.arm == "no_brdf"]
        .drop(columns="arm")
        .sort_values(groups[:3] + ["fold", "row", "role"])
        .reset_index(drop=True)
    )
    right = (
        memberships[memberships.arm == "brdf"]
        .drop(columns="arm")
        .sort_values(groups[:3] + ["fold", "row", "role"])
        .reset_index(drop=True)
    )
    assert left.equals(right)
    checks["no_identity_leak_and_identical_arm_folds"] = True
    preds = pd.read_csv(BASE / "statistics/predictions.csv")
    rates = pd.read_csv(BASE / "statistics/identifiability.csv")
    for (sensor, bands, scheme), g in preds.groupby(["sensor", "bands", "scheme"]):
        g = g.assign(correct=(g.truth == g.prediction).astype(float))
        unit = g.groupby(["identity", "truth", "arm"], as_index=False).correct.mean()
        rate = rates[
            (rates.sensor == sensor) & (rates.bands == bands) & (rates.scheme == scheme)
        ].iloc[0]
        scores = {}
        for arm, h in unit.groupby("arm"):
            scores[arm] = float(h.groupby("truth").correct.mean().mean())
            np.testing.assert_allclose(
                scores[arm], rate["ba_" + arm], rtol=0, atol=1e-14
            )
        np.testing.assert_allclose(
            scores["brdf"] - scores["no_brdf"], rate.delta_ba, rtol=0, atol=1e-14
        )
    checks["recognition_recalculated_from_predictions"] = True
    for name, cols, expected in [
        ("identifiability", ["p_identity", "p_site_exact"], 10),
        ("separability", ["p_npc"], 96),
        ("separation_changes", ["p_identity", "p_site_exact"], 48),
    ]:
        f = pd.read_csv(BASE / "statistics" / f"{name}.csv")
        for col in cols:
            ix = f[col].notna()
            assert int(ix.sum()) == expected
            np.testing.assert_allclose(
                adjust(f.loc[ix, col].to_numpy()),
                f.loc[ix, col + "_holm_family"],
                rtol=0,
                atol=1e-14,
            )
        checks[name + "_family_size"] = expected
    control = json.loads((BASE / "aop-control/completed.json").read_text())
    model = json.loads((ROOT / control["model_path"]).read_text())
    assert sha(ROOT / control["model_path"]) == control["model_sha256"]
    assert control["status"] == "VALID" and control["supported_bands"] == 10
    assert all(
        r["uncertainty_groups"] == 720
        and r["excluded_by_fitting_subset"] == 72000
        and r["eligible"] == 288000
        for r in model["validation"]["fits"]
    )
    with h5py.File(
        ROOT
        / "archive/local/validation-input/NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5"
    ) as src:
        info = (
            src["R10C/Reflectance/Metadata/Coordinate_System/Map_Info"][()]
            .decode()
            .split(",")
        )
        assert float(info[5]) == float(info[6]) == 1.0
    checks["aop_control_held72000_and_20m_groups"] = True
    aop = pd.read_csv(BASE / "aop/flight_support_audit.csv")
    assert aop.paired_rows.sum() == aop.input_rows.sum() == 85706
    checks["aop_source_rows_paired_without_attrition"] = 85706
    # Reconstruction arithmetic on all1241cells, not a selected example.
    hls = pd.read_csv(BASE / "hls/paired_cells.csv")
    assert len(hls) == 1241
    for i in range(1, 8):
        np.testing.assert_allclose(
            hls[f"pre_nbar_B{i}"] * hls[f"cf_B{i}"], hls[f"B{i}"], rtol=0, atol=1e-15
        )
    checks["all_hls_inverse_relations"] = True
    result = dict(
        date="2026-11-20",
        checks=checks,
        status="PASS",
        code_sha256=sha(Path(__file__)),
        source_manifests={
            folder: sha(BASE / folder / "completed.json")
            for folder in ["hls", "aop", "drone", "aop-control", "statistics"]
        },
    )
    (BASE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    run()
