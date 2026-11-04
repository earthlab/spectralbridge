"""Verify preserved inputs, honest branch status and actual supported controls."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import h5py
import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import ROOT, WORK, sha, write  # noqa: E402


def read(name):
    return json.loads((HERE / name).read_text())


def main():
    manifest = read("input_manifest.json")
    protected = manifest["protected_hashes"]
    print(
        "Checking",
        len(protected),
        "protected inputs and historical artifacts",
        flush=True,
    )
    for path, expected in protected.items():
        assert sha(path) == expected, path
    software = []
    for snapshot, relative in [
        ("corrections", "corrections.py"),
        ("brdf_topo", "brdf_topo.py"),
        ("pipelines_drone", "pipelines/drone.py"),
        ("radiometry", "radiometry.py"),
        ("envi_writer", "envi_writer.py"),
    ]:
        rel = "src/spectralbridge/" + relative
        before = HERE / f"pre_edit_{snapshot}.py"
        head = subprocess.check_output(["git", "show", "HEAD:" + rel], cwd=ROOT)
        assert before.read_bytes() == head, rel
        software.append(
            dict(path=rel, before_sha256=sha(before), current_sha256=sha(ROOT / rel))
        )
    for branch in ["A", "B"]:
        record = read(branch + "_replay.json")
        assert (
            record["maximum_error_vs_preserved_previous"] == 0
            and record["validity_exact"]
        )
    assert (
        read("factorial_contrasts.json")["A_B_extreme_boundary_pattern_agreement"] == 1
    )
    statuses = {row["branch"]: row for row in read("factorial_status.json")}
    for branch in ["C", "D", "E", "F"]:
        assert not statuses[branch]["image_created"]
    for branch in ["C", "D"]:
        m = read(branch + "_historical_refit_unsupported.json")
        assert m["stable_rank"] == 1 and not m["model_applied"]
    for mode in ["brdf", "combined"]:
        model = read("E_after_" + mode + "_model.json")
        assert model["radiometry"]["status"] == "HYPOTHETICAL_UNVERIFIED"
        assert model["validation"]["status"] == "UNSUPPORTED"
        assert all(f["stable_rank"] == 1 for f in model["validation"]["fits"])
        assert all(
            v is None
            for k in ["iso", "vol", "geo"]
            for row in model.get(k, [])
            for v in row
        )
    scaling = read("ingestion_and_scaling.json")
    assert all(
        r["max_decode_error"] == 0 and r["mask_exact"] for r in scaling["checks"]
    )
    h5 = Path(scaling["source_h5"])
    with h5py.File(h5) as f:
        names = []
        f.visit(names.append)
        assert not any(
            "sensor_zn" in n.lower() or "sensor_az" in n.lower() for n in names
        )
    with rasterio.open(scaling["raw_envi"][0]) as raw:
        assert raw.count == 10 and raw.transform.e < 0
        assert np.isclose(raw.transform.a, 0.1) and np.isclose(raw.transform.e, -0.1)
    assert all(
        r["balanced_accuracy"] is None for r in read("PFT_unsupported_branches.json")
    )
    folds = pd.read_csv(HERE / "classification_memberships.csv")
    for _, group in folds.groupby("fold"):
        train = set(group.loc[group.role == "train", "identity"])
        test = set(group.loc[group.role == "test", "identity"])
        assert train.isdisjoint(test)
    predictions = pd.read_csv(HERE / "classification_predictions.csv")
    keys = None
    for _, group in predictions.groupby("branch"):
        current = set(zip(group.identity, group.fold))
        assert len(current) == 157
        if keys is not None:
            assert keys == current
        keys = current
    summary = read("analysis_summary.json")
    assert (
        summary["identities"] == 157 and summary["common_polygon_memberships"] == 144406
    )
    neon = read("neon_after_control.json")
    comparisons = []
    for mode, control in zip(["brdf", "combined"], neon["controls"]):
        assert control["status"] == "VALID" and control["supported_bands"] == 10
        assert control["serialized_control"]["accepted_library_contract"]
        before = np.load(WORK / f"neon_before_{mode}.npy", mmap_mode="r")
        after = np.load(WORK / f"neon_after_{mode}.npy", mmap_mode="r")
        assert np.array_equal(before, after, equal_nan=True)
        comparisons.append(
            dict(mode=mode, exact_values_and_masks=True, max_abs_difference=0)
        )
    evidence = HERE / "verification_logs"
    evidence.mkdir(exist_ok=True)
    for pattern in [
        "p172_*tests.xml",
        "p172_*tests.log",
        "p172_regression_before.xml",
        "p172_regression_before.log",
        "p172_legacy_refits.log",
        "p172_neon_after_final.log",
        "p172_figures_final.log",
    ]:
        for path in Path("/private/tmp").glob(pattern):
            shutil.copyfile(path, evidence / path.name)
    suites = list(
        ET.parse("/private/tmp/p172_final_tests.xml").getroot().iter("testsuite")
    )
    counts = {
        k: sum(int(s.attrib.get(k, 0)) for s in suites)
        for k in ["tests", "failures", "errors", "skipped"]
    }
    assert counts == dict(tests=178, failures=0, errors=0, skipped=0)
    status = dict(
        status="PASS",
        protected_inputs_and_historical_artifacts=len(protected),
        all_protected_hashes_unchanged=True,
        software=software,
        targeted_test_results=counts,
        real_NEON_controls=comparisons,
        original_NEON_source_sha256=neon["source_sha256"],
        Goldhill_production_sensor_views_absent=True,
        calibration="HYPOTHETICAL_UNVERIFIED",
        Goldhill_supported_BRDF_output=False,
        actual_historical_replays_exact=True,
        geometry_rank=1,
        supported_library_serialization_verified=True,
        polygon_identities=157,
        matched_memberships=144406,
        current_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        scientific_summary_sha256=sha(HERE / "scientific_summary.json"),
        PDF_sha256=sha(HERE / "goldhill_clean_source_brdf_investigation.pdf"),
    )
    write("verification.json", status)
    write(
        "artifact_checksums.json",
        {
            str(p.relative_to(HERE)): sha(p)
            for p in sorted(HERE.rglob("*"))
            if p.is_file()
            and "__pycache__" not in p.parts
            and p.name != "artifact_checksums.json"
        },
    )
    print("PASS:", counts, "protected hashes", len(protected))


if __name__ == "__main__":
    main()
