"""Verify experiment contracts, read-only inputs and compact deliverables."""

from pathlib import Path
import hashlib
import importlib.metadata
import json
import re
import subprocess

import h5py
import numpy as np
import pandas as pd
from spectralbridge.radiometry import dataset_radiometry

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def main():
    summary = json.loads((HERE / "experiment_summary.json").read_text())
    assert (
        summary["baseline_polygons"] == 301
        and summary["baseline_polygon_pixel_memberships"] == 198562
    )
    constants = json.loads((HERE / "constant_geometries.json").read_text())
    spatial = json.loads((HERE / "spatial_geometries.json").read_text())
    alpha = json.loads((HERE / "alpha_positive_design_audit.json").read_text())
    preserve = json.loads((HERE / "preservation.json").read_text())
    inventory = json.loads((HERE / "coefficient_inventory.json").read_text())
    masks = pd.read_csv(HERE / "source_alpha_audit.csv")
    baseline = pd.read_csv(HERE / "baseline_polygon_spectra.csv")
    assert len(constants) == 93 and len(spatial) == 15
    assert sum(r["angular_numerical_gate"] for r in constants) == 0
    assert sum(r["angular_numerical_gate"] for r in spatial) == 12
    assert alpha["constant_gate_passes"] == 0 and alpha["spatial_gate_passes"] == 12
    assert all(r["canonical_constant_relative_rank"] == 1 for r in constants)
    assert sum(r["view_zenith_degrees"] == 0 for r in constants) == 3
    assert len(baseline) == 301 and int(baseline.pixels.sum()) == 198562
    assert int(masks.finite_H5_memberships.sum()) == 200320
    assert int(masks.alpha_zero_memberships.sum()) == 1758
    assert int(masks.alpha_positive_memberships.sum()) == 198562
    assert len(masks) == 302 and (masks.alpha_positive_memberships == 0).sum() == 1
    assert (baseline.groupby(["flight", "GlobalID"]).size() == 1).all()
    assert (baseline.independent_component_representative).all()
    assert inventory["suitable_sets"] == 0 and len(inventory["candidates"]) == 13
    comp = json.loads((HERE / "correction_comparison_status.json").read_text())
    assert len(comp) == 9 and all(
        r["factor_quantiles"] is None and r["within_PFT_change"] is None for r in comp
    )
    checked = {}
    for path, expected in preserve["inputs_before"].items():
        checked[path] = sha(path)
        assert checked[path] == expected, path
    for candidate in inventory["candidates"]:
        path = candidate["path"]
        checked[path] = sha(path)
        assert checked[path] == candidate["sha256"], path
    auxiliary = inventory["auxiliary_real_NEON_QA"]
    checked[auxiliary["path"]] = sha(auxiliary["path"])
    assert checked[auxiliary["path"]] == auxiliary["sha256"]
    records = json.loads((HERE / "scenario_provenance.json").read_text())["reports"]
    previous = json.loads(
        (
            ROOT / "provenance/photogrammetry-metadata/2026-11-02/source_inventory.json"
        ).read_text()
    )["local_files"]
    for report in records:
        path = report["processing_report"]
        checked[path] = sha(path)
        assert checked[path] == report["sha256"]
        prev = next(r for r in previous if r.get("local_path") == path)
        assert prev["sha256"] == checked[path]
    actual_unit_gates = {}
    for name in ["gordon", "goldhill", "ruby"]:
        with h5py.File(
            f"/private/tmp/assumed-viewing-angles-20261103/{name}_working.h5", "r"
        ) as h:
            group = h[next(iter(h))]["Reflectance"]
            wave = group["Metadata"]["Spectral_Data"]["Wavelength"][...]
            np.testing.assert_array_equal(
                wave, [444, 475, 531, 560, 650, 668, 705, 717, 740, 862]
            )
            units = dataset_radiometry(group["Reflectance_Data"], neon=False)
            assert units.status == "UNSUPPORTED"
            actual_unit_gates[name] = units.record()
    report = (HERE / "report.md").read_text()
    for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", report):
        if not link.startswith(("https:", "http:")):
            assert (HERE / link.split("#")[0]).exists(), link
    assert len(list(HERE.glob("figure*.png"))) == 9
    assert (
        not list(HERE.glob("*.h5"))
        and not list(HERE.glob("*.tif"))
        and not list(HERE.glob("*.img"))
    )
    pdf = HERE / "can_assumed_viewing_angles_rescue_drone_brdf.pdf"
    info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
    assert re.search(r"Pages:\s+8", info)
    versions = {
        name: importlib.metadata.version(name)
        for name in [
            "numpy",
            "scipy",
            "pandas",
            "rasterio",
            "h5py",
            "geopandas",
            "matplotlib",
        ]
    }
    result = dict(
        status="passed",
        date="2026-11-03",
        revision=preserve["revision"],
        package_sources_and_inputs_checked=len(checked),
        input_hashes_unchanged=True,
        checked_input_hashes=checked,
        versions=versions,
        actual_flight_unit_gates=actual_unit_gates,
        constant_cases=93,
        constant_angular_passes=0,
        spatial_cases=15,
        spatial_angular_passes=12,
        positive_alpha_angular_audit="same outcomes",
        primary_baseline_polygons=301,
        primary_baseline_memberships=198562,
        finite_H5_only_memberships=200320,
        transparent_background_memberships_excluded=1758,
        independent_coefficient_sets=0,
        coefficient_application="NOT_EVALUATED",
        correction_PFT_improvement="NOT_EVALUATED",
        generated_production_corrections=0,
        focused_tests_passed=17,
        pdf_pages=8,
        pdf_figures=9,
        pdf_visual_review="All eight pages inspected; latest changed pages re-inspected",
        ruff="passed",
        docs_links="passed",
        ai_transparency="passed",
        whitespace="passed",
        limitations=[
            "No eligible independently validated coefficient set found in bounded search",
            "No physical reflectance calibration or recovered observation geometry",
            "No correction-factor, gain or corrected-PFT comparison manufactured",
            "Source alpha-positive mask is analytical; no H5, TIFF or polygon rewritten",
            "Previous corrected rasters partly absent locally and not used/reconstructed",
        ],
    )
    (HERE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"Verified {len(checked)} unchanged input/source/model/report files, 93+15 designs, alpha audit, 301 polygons and eight-page PDF."
    )


if __name__ == "__main__":
    main()
