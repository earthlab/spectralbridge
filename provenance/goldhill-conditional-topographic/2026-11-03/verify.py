"""Verify immutable inputs, hypothesis boundary, matched support and completed tests."""

import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import ROOT, WORK, sha, write  # noqa: E402


def main():
    manifest = json.loads((HERE / "input_manifest.json").read_text())
    protected = dict(manifest["protected_hashes"])
    calibration = json.loads(
        (
            ROOT / "provenance/goldhill-micasense-calibration/2026-11-03/results.json"
        ).read_text()
    )
    protected.update(calibration["protected_hashes"])
    terrain = json.loads((HERE / "terrain_audit.json").read_text())
    protected.update({x["path"]: x["sha256"] for x in terrain["original_terrain"]})
    for p, digest in protected.items():
        assert sha(p) == digest, p
    config = json.loads((HERE / "experiment_configuration.json").read_text())
    assert config["status"] == "HYPOTHETICAL_UNVERIFIED"
    assert (
        config["production_changes"] == 0 and config["production_guard_still_rejects"]
    )
    assert not config["BRDF_applied"] and not config["factor_clipping"]
    additional = json.loads((HERE / "additional_verification.json").read_text())
    assert additional["raw_classifier_scaling_predictions_identical"]
    assert len(additional["all_ten_band_conversion"]) == 10
    assert all(
        x["max_abs_decode_difference"] == 0 and x["mask_exact"]
        for x in additional["all_ten_band_conversion"]
    )
    assert (
        max(
            x["max_abs_once_decode_difference"]
            for x in additional["apply_decode_once_checks"]
        )
        < 2e-6
    )
    invariant = json.loads((HERE / "scale_invariance.json").read_text())
    assert invariant["max_abs_C_difference"] == 0
    membership = pd.read_csv(HERE / "classification_memberships.csv")
    for _, g in membership.groupby("fold"):
        assert not (
            set(g[g.role == "train"].identity) & set(g[g.role == "test"].identity)
        )
    predictions = pd.read_csv(HERE / "classification_predictions.csv")
    assert predictions.groupby("branch").size().eq(157).all()
    cfg = json.loads((HERE / "branches.json").read_text())
    index = pd.read_parquet(cfg["polygon_index"])
    fit = np.load(WORK / "fit_eligible.npy")
    assert not fit[index.row, index.col].any()
    masks = np.load(HERE / "eligibility_masks.npz")
    assert not (masks["common"] & ~masks["source_valid"]).any()
    assert int(masks["common"].sum()) == 6614170
    # Recheck the authoritative package pixel-center contract (no reflection).
    import rasterio

    with rasterio.open(
        "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
    ) as src:
        x, y = rasterio.transform.xy(
            src.transform, index.row.to_numpy(), index.col.to_numpy(), offset="center"
        )
        error = max(np.max(abs(x - index.x)), np.max(abs(y - index.y)))
        assert error < 1e-6
    tests = ET.parse("/private/tmp/p171_tests.xml").getroot()[0].attrib
    assert int(tests["failures"]) == int(tests["errors"]) == 0
    assert int(tests["tests"]) >= 28
    for name in [
        "p171_tests.xml",
        "p171_tests.log",
        "p171_experiment.log",
        "p171_analysis.log",
        "p171_geometry.log",
        "p171_additional.log",
        "p171_median.log",
        "p171_figures.log",
    ]:
        shutil.copyfile(Path("/private/tmp") / name, HERE / name)
    # Source geometry provenance/timestamps are retained verbatim as compact records.
    for name in [
        "geometry_provenance.json",
        "photo_time_reconciliation.json",
        "software_and_configuration.json",
    ]:
        shutil.copyfile(
            ROOT / "provenance/goldhill-end-to-end/2026-11-03" / name,
            HERE / ("prior_" + name),
        )
    figures = json.loads((HERE / "figure_manifest.json").read_text())
    assert len(figures) == 14
    assert all((HERE / f[k]).exists() for f in figures for k in ["png", "svg"])
    layout = json.loads((HERE / "pdf_layout.json").read_text())
    assert len(layout) == 20 and min(x["lowest_content_y"] for x in layout) > 44
    write(
        "verification.json",
        dict(
            status="PASS_CONDITIONAL_EXPERIMENT_NOT_PHYSICAL_CERTIFICATION",
            protected_hashes=protected,
            protected_count=len(protected),
            tests=tests,
            common_pixels=6614170,
            evaluated_identities=157,
            pixel_center_max_error=float(error),
            all_band_masks_and_affine_exact=True,
            production_gate_rejects_hypothesis=True,
            identical_group_disjoint_folds=True,
            fit_excludes_evaluation_polygons=True,
            PDF_pages=20,
            figure_pairs=14,
            PDF_visual_review="Recorded separately in pdf_content_qa.json after final rendering",
            production_changes=0,
            BRDF_applied=False,
            factor_clipping=False,
        ),
    )
    paths = sorted(WORK.glob("*.npy"))
    output_hashes = {str(p): sha(p) for p in paths}
    output_manifest = HERE / "output_manifest.json"
    if output_manifest.exists():
        prior = json.loads(output_manifest.read_text())
        assert prior["scratch_output_hashes"] == output_hashes
    else:
        write(
            "output_manifest.json",
            dict(
                status="HYPOTHETICAL_UNVERIFIED",
                scratch_output_hashes=output_hashes,
                grid_source=cfg["profile"],
                units="candidate fractional reflectance for image arrays; explicit Boolean masks for support arrays",
            ),
        )
    print(
        "PASS:",
        len(protected),
        "protected files;",
        tests["tests"],
        "tests; matched157polygons;20PDF pages",
    )


if __name__ == "__main__":
    main()
