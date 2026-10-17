"""Offline website evidence verification, examples and historical preservation.

Reads only compact tables and existing figures. Never fits historical studies.
"""

from pathlib import Path
import argparse
import hashlib
import json
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def verify():
    prior = ROOT / "provenance/researcher-pft-information/2026-10-15/v1"
    current = ROOT / "provenance/researcher-evidence/2026-10-16/v1"
    sources = {}

    def read(base, name):
        p = base / "tables" / name
        sources[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
        return pd.read_csv(p)

    feature = read(prior, "complementary_feature_performance.csv")
    recall = read(prior, "class_specific_transfer.csv")
    controls = read(current, "recognition_control_summary.csv")
    abundance = read(current, "abundance_domain_summary.csv")
    fair = read(current, "same_candidate_ridge.csv")
    pairs = read(current, "pair_support_and_evidence.csv")
    oracle = read(prior, "oracle_solver_controls.csv")
    values = {}
    for kind in ["plant", "site"]:
        for budget in ["360", "OLI"]:
            score = feature[
                (feature.kind == kind) & (feature.budget.astype(str) == budget)
            ].balanced_accuracy.mean()
            values[f"{kind}_{budget}_BA"] = float(score)
    values["shrub_site_recall"] = float(
        recall[
            (recall.kind == "site")
            & (recall.budget.astype(str) == "360")
            & (recall.researcher_category == "Woody shrub")
        ].recall.mean()
    )
    for method in ["Selected", "Random"]:
        subset = controls[
            (controls.kind == "site")
            & (controls.method == method)
            & (controls.budget == 20)
        ]
        # Selected may be encoded with its full descriptive name in current tables.
        if subset.empty and method == "Selected":
            subset = feature[
                (feature.kind == "site") & (feature.budget.astype(str) == "20")
            ]
            score = subset.balanced_accuracy.mean()
        else:
            score = subset["mean"].iloc[0]
        values[f"site20_{method}"] = float(score)
    for kind in ["plant", "site", "year"]:
        for method in ["Ridge", "MESMA", "No-spectrum prior"]:
            subset = abundance[
                (abundance.kind == kind)
                & (abundance.representation == "NEON")
                & (abundance.method == method)
            ]
            if subset.empty and method == "No-spectrum prior":
                subset = abundance[
                    (abundance.kind == kind)
                    & (abundance.representation == "NEON")
                    & (abundance.method == "Training prior")
                ]
            values[f"{kind}_{method}_RMSE"] = float(subset["mean"].iloc[0])
        values[f"{kind}_Ridge15_RMSE"] = float(
            fair[(fair.kind == kind) & (fair.representation == "NEON")].RMSE.mean()
        )
    values["pairs"] = len(pairs)
    values["contrasts"] = int(pairs.cohorts.sum())
    values["largest_adjusted_p"] = float(pairs.largest_adjusted_NEON_p.max())
    values["oracle_max_fraction_RMSE"] = float(oracle.fraction_RMSE.max())
    expected = {
        "plant_360_BA": 85.2,
        "site_360_BA": 73.8,
        "plant_OLI_BA": 66.8,
        "site_OLI_BA": 57.7,
        "shrub_site_recall": 46.3,
        "site20_Selected": 70.1,
        "site20_Random": 65.0,
    }
    for k, v in expected.items():
        assert round(100 * values[k], 1) == v, (k, values[k])
    assert (
        values["pairs"] == 10
        and values["contrasts"] == 40
        and values["largest_adjusted_p"] == 0.004
    )
    assert values["oracle_max_fraction_RMSE"] < 4e-13
    # These comparisons must remain adverse, rather than selecting a favorable view.
    assert values["plant_Ridge15_RMSE"] > values["plant_MESMA_RMSE"]
    assert values["site_Ridge15_RMSE"] > values["site_MESMA_RMSE"]
    assert values["year_Ridge_RMSE"] > values["year_No-spectrum prior_RMSE"]
    assets = json.loads(
        (ROOT / "docs/spectral-library/integration-figure-sources.json").read_text()
    )
    for entry in assets.values():
        for field in ["source", "website_path"]:
            assert (
                hashlib.sha256((ROOT / entry[field]).read_bytes()).hexdigest()
                == entry["sha256"]
            )
    preserved = {}
    manifests = [
        prior / "final_manifest.json",
        current / "final_manifest.json",
        ROOT / "provenance/manuscript-synthesis/2026-10-16/v1/packet_manifest.json",
        ROOT / "formal/packet_manifest.json",
        ROOT / "formal/report/packet_manifest.json",
    ]
    for p in manifests:
        m = json.loads(p.read_text())
        for key, digest in m.get("sha256", m.get("files", {})).items():
            assert hashlib.sha256((ROOT / key).read_bytes()).hexdigest() == digest, key
            preserved[key] = digest
    return {
        "status": "passed",
        "scientific_values": values,
        "source_sha256": sources,
        "figure_assets_verified": len(assets),
        "prior_owned_files_verified": len(preserved),
    }


def run_examples():
    pages = [
        "separability",
        "identifiability",
        "sensor-transfer",
        "mesma-readiness",
        "mathematical-guarantees",
    ]
    count = 0
    for page in pages:
        p = ROOT / f"docs/spectral-library/{page}.md"
        for code in re.findall(r"```python\n(.*?)```", p.read_text(), re.S):
            exec(compile(code, str(p), "exec"), {})
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify()
    if args.examples:
        result["website_python_examples_executed"] = run_examples()
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
