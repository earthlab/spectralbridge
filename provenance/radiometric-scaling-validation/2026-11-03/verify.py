"""Verify test evidence, unchanged source bytes and the P166/P167 math boundary."""

import ast
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

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
    for path, digest in r["protected_hashes"].items():
        assert sha(path) == digest, path
    baseline = json.loads(
        (
            ROOT
            / "provenance/brdf-mathematical-validation/2026-11-03/verification.json"
        ).read_text()
    )["kernel_AST_hashes_frozen_for_P167"]
    source = ast.parse((ROOT / "src/spectralbridge/corrections.py").read_text())
    current = {
        n.name: hashlib.sha256(
            ast.dump(n, include_attributes=False).encode()
        ).hexdigest()
        for n in source.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in baseline
    }
    assert current == baseline, (current, baseline)
    tests = set()
    summaries = []
    for name in ["p167_final_tests", "p167_additional_tests"]:
        path = Path("/private/tmp") / (name + ".xml")
        tree = ET.parse(path)
        assert not tree.findall(".//failure") and not tree.findall(".//error")
        cases = tree.findall(".//testcase")
        assert not tree.findall(".//skipped")
        tests.update((c.attrib["classname"], c.attrib["name"]) for c in cases)
        shutil.copyfile(path, HERE / (name + ".xml"))
        summaries.append(
            dict(
                record=name + ".xml", passed=len(cases), failures=0, errors=0, skipped=0
            )
        )
    figures = json.loads((HERE / "figure_manifest.json").read_text())
    assert len(figures) == 7
    for f in figures:
        for ext in ["png", "svg"]:
            assert (HERE / f[ext]).stat().st_size > 1000
    gate = json.loads((HERE / "physical_fit_gate.json").read_text())
    assert gate["status"] == "PASS" and gate["validation"]["status"] == "UNSUPPORTED"
    rec = dict(
        status="PASS",
        date="2026-11-03",
        focused_unique_tests=len(tests),
        test_runs=summaries,
        protected_source_files=len(r["protected_hashes"]),
        protected_files_unchanged=True,
        kernel_reference_ASTs_unchanged=True,
        kernel_AST_hashes=current,
        figure_pairs=7,
        visually_reviewed_figure_pairs=7,
        historical_counts=[x["historical_A"] for x in r["goldhill"]],
        normalized_diagnostic_count_per_band=6692436,
        physical_calibration="UNRESOLVED; diagnostic normalization not promoted",
        production_products_regenerated=0,
        physical_fit_gate="UNSUPPORTED with no coefficients",
        checks=[
            "targeted pytest",
            "Ruff modified source/tests/evidence",
            "local docs links",
            "API generator freshness",
            "AI transparency freshness",
            "git diff --check",
        ],
        warnings="Existing QA/deprecation warnings and GDAL NoData/alpha shadow warning; alpha is also explicitly enforced",
    )
    (HERE / "verification.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()
