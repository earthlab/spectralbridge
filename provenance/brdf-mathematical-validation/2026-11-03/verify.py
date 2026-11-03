"""Verify mathematical evidence and freeze the P166 boundary for P167 radiometry."""

import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from evaluate_geometry import sha  # noqa: E402


def main():
    geometry = json.loads((HERE / "real_geometry_validation.json").read_text())
    before = geometry["preservation"]["before"]
    after = {p: sha(p) for p in before}
    assert before == after
    assert geometry["flights"]["neon"]["designs"]["current"]["rank"] == 3
    assert geometry["flights"]["goldhill"]["designs"]["current"]["rank"] == 1
    assert geometry["goldhill_arbitrary_nadir_azimuth_range"] == 0
    assert (
        geometry["real_geometry_synthetic_signal_gate_control"]["supported_band_fits"]
        == 0
    )
    report = (ROOT / "docs/reports/BRDF_MATHEMATICAL_VALIDATION.md").read_text()
    for link in re.findall(r"\]\(([^)]+)\)", report):
        if not link.startswith("http"):
            assert (ROOT / "docs/reports" / link).exists(), link
    manifest = json.loads((HERE / "figure_manifest.json").read_text())
    for figure in manifest:
        assert figure["name"] in report
        for ext in [".png", ".svg"]:
            assert (HERE / (figure["name"] + ext)).is_file()
    testcases = {}
    for filename in [
        "/private/tmp/p166_final_tests.xml",
        "/private/tmp/p166_resume_tests.xml",
    ]:
        tree = ET.parse(filename)
        for case in tree.findall(".//testcase"):
            assert case.find("failure") is None and case.find("error") is None
            testcases[(case.get("classname"), case.get("name"))] = True
    source = (ROOT / "src/spectralbridge/corrections.py").read_text()
    tree = ast.parse(source)
    names = [
        "_brdf_angles",
        "calc_volume_kernel",
        "calc_geom_kernel",
        "_reference_design",
        "_normalize_geom_kernel_name",
    ]
    hashes = {
        node.name: hashlib.sha256(
            ast.dump(node, include_attributes=False).encode()
        ).hexdigest()
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    }
    record = dict(
        status="PASS",
        date="2026-11-03",
        repository_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        kernel_math_version=geometry["kernel_math_version"],
        focused_unique_tests=len(testcases),
        reference_geometries_per_kernel=len(
            json.loads(
                (
                    ROOT / "tests/data/brdf/published_equation_references.json"
                ).read_text()
            )["rows"]
        ),
        preserved_source_hashes=after,
        production_rasters_regenerated=0,
        figure_pairs=len(manifest),
        kernel_AST_hashes_frozen_for_P167=hashes,
        reference_geometry_degrees=dict(solar=45, view=0, relative_azimuth=0),
        versions={
            name: importlib.metadata.version(name)
            for name in ["numpy", "scipy", "h5py", "matplotlib"]
        },
        warnings="Existing QA/deprecation warnings in focused pipeline tests; no mathematical test failures",
        scope="Mathematics/compatibility only. No radiometry, fitting thresholds or physical calibration changed.",
    )
    (HERE / "verification.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        record["focused_unique_tests"],
        "unique focused tests passed;",
        len(after),
        "protected input hashes unchanged",
    )


if __name__ == "__main__":
    main()
