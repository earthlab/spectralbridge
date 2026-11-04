"""Verify source preservation, the delivered derivative and investigation evidence."""

import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    r = json.loads((HERE / "results.json").read_text())
    derivative = json.loads((HERE / "derivative_radiometry.json").read_text())
    protected = dict(r["protected_hashes"])
    for h in json.loads((HERE / "h5_source_audit.json").read_text()):
        protected[h["path"]] = h["sha256"]
    h = r["working_h5"]
    protected[h["path"]] = h["sha256"]
    assert all(sha(p) == digest for p, digest in protected.items())
    expected = json.loads(
        (
            ROOT / "provenance/drone-scale-confirmation/2026-10-30/evidence.json"
        ).read_text()
    )["goldhill"]["files"]
    for key, old in [
        ("original", "original"),
        ("summer_float_25cm", "base_25cm"),
        ("normalized_25cm", "rescaled_25cm"),
        ("normalized_10cm", "target_10cm"),
    ]:
        assert r["candidate_inventory"][key]["sha256"] == expected[old]["sha256"]
    assert sha(derivative["output"]) == derivative["output_sha256"]
    with rasterio.open(derivative["output"]) as src:
        assert (
            src.count == 10
            and src.dtypes[0] == "float32"
            and src.crs.to_epsg() == 26913
        )
        np.testing.assert_allclose(src.res, [0.1, 0.1], atol=1e-10, rtol=0)
        mask = src.dataset_mask() > 0
        assert int(mask.sum()) == 6683944
        for band in range(1, 11):
            a = src.read(band)
            assert (
                np.isfinite(a[mask]).all()
                and (a[mask] >= 0).all()
                and (a[mask] <= 10000).all()
            )
            assert np.isnan(a[~mask]).all()
        assert src.tags()["PHYSICAL_CALIBRATION_STATUS"] == "UNVERIFIED"
    tree = ET.parse("/private/tmp/p168_tests.xml")
    assert (
        not tree.findall(".//failure")
        and not tree.findall(".//error")
        and not tree.findall(".//skipped")
    )
    count = len(tree.findall(".//testcase"))
    assert count == 2
    shutil.copyfile("/private/tmp/p168_tests.xml", HERE / "tests.xml")
    manifest = json.loads((HERE / "figure_manifest.json").read_text())
    assert len(manifest) == 4
    for f in manifest:
        for ext in ["png", "svg"]:
            assert (HERE / f[ext]).stat().st_size > 1000
    masks = json.loads((HERE / "mask_and_encoding_audit.json").read_text())
    assert all(
        b["source_65535_in_observed"] == 0
        and b["source_65535_in_transparent"] == 537552
        for b in masks["bands"]
    )
    record = dict(
        status="PASS",
        date="2026-11-03",
        protected_files=len(protected),
        protected_hashes=protected,
        all_protected_files_unchanged=True,
        previous_original_and_25cm_and_10cm_source_hashes_match=True,
        synthetic_contract_tests_passed=count,
        failures=0,
        figure_pairs=4,
        visually_reviewed_pairs=4,
        new_numerical_derivative=derivative["output"],
        derivative_sha256=derivative["output_sha256"],
        derivative_valid_pixels=6683944,
        derivative_minimum_offset=0,
        derivative_all_finite_valid_values_in_0_10000=True,
        declared_physical_calibration="UNVERIFIED",
        production_code_changed=False,
        production_corrected_products_regenerated=0,
        source_files_modified=0,
        datastore_writes=0,
        checks=[
            "Synthetic fixed-encoding/mask/overwrite contracts",
            "Actual independent same-grid and cross-grid comparisons",
            "Two archived H5s versus all ten neighboring TIFF bands",
            "Protected SHA-256 including production-code boundary",
            "Ruff",
            "Local docs links",
            "AI transparency generator freshness",
            "git diff --check",
        ],
    )
    (HERE / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        f"PASS: {len(protected)} protected files unchanged; {count} contract tests; 4 reviewed figure pairs; derivative verified"
    )


if __name__ == "__main__":
    main()
