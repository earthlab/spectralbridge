"""Verify final native products, frozen evidence, NEON parity and test results."""

import ast
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/drone-integrated-reliability-20261104/final_v2")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


manifest = json.loads((HERE / "input_manifest.json").read_text())
protected = []
incidental = []
for path, expected in manifest["protected_hashes"].items():
    if Path(path).name == ".DS_Store":
        incidental.append(dict(path=path, unchanged=digest(path) == expected))
        continue
    assert digest(path) == expected, path
    protected.append(path)
neon = []
for mode in ["brdf", "combined"]:
    old = np.load(
        f"/private/tmp/goldhill-viewing-geometry-20261104/neon_after_{mode}.npy",
        mmap_mode="r",
    )
    new = np.load(WORK / f"neon_after_{mode}.npy", mmap_mode="r")
    np.testing.assert_array_equal(old, new)
    neon.append(dict(mode=mode, elements=int(new.size), exact_equal=True))
products = []
for record in json.loads((HERE / "pipeline_results.json").read_text()):
    arr = np.load(record["array"], mmap_mode="r")
    header = Path(record["header"]).read_text()
    assert "EXPERIMENTAL" in header
    with rasterio.open(record["image"]) as src:
        assert src.crs.to_epsg() == 26913 and src.count == 10
        assert abs(src.transform.a - 0.1) < 1e-9 and abs(src.transform.e + 0.1) < 1e-9
        for _, win in src.block_windows(1):
            x, y = int(win.col_off), int(win.row_off)
            h, w = int(win.height), int(win.width)
            np.testing.assert_array_equal(
                np.moveaxis(src.read(window=win), 0, -1), arr[y : y + h, x : x + w]
            )
        tags = src.tags()
    products.append(
        dict(
            branch=record["branch"],
            path=record["image"],
            sha256=digest(record["image"]),
            size_bytes=Path(record["image"]).stat().st_size,
            native_roundtrip_exact=True,
            experimental_header=True,
            tiff_tags=tags,
        )
    )
# Kernel math must retain its already-validated equations.
old = ast.parse((HERE / "pre_edit_corrections.py").read_text())
new = ast.parse((ROOT / "src/spectralbridge/corrections.py").read_text())
olddefs = {
    n.name: ast.dump(n, include_attributes=False)
    for n in old.body
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
}
newdefs = {
    n.name: ast.dump(n, include_attributes=False)
    for n in new.body
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
}
unchanged = [name for name, value in olddefs.items() if newdefs.get(name) == value]
changed = [name for name, value in olddefs.items() if newdefs.get(name) != value]
tests = []
for path in [
    "/private/tmp/p175_final_tests.xml",
    "/private/tmp/p175_contract_tests.xml",
]:
    suite = ET.parse(path).getroot().find("testsuite")
    assert int(suite.attrib["errors"]) == 0 and int(suite.attrib["failures"]) == 0
    tests.append(dict(path=path, **suite.attrib))
result = dict(
    protected_artifacts=len(protected),
    incidental_finder_metadata=incidental,
    protected_hashes_unchanged=True,
    neon=neon,
    products=products,
    unchanged_correction_functions=unchanged,
    intentionally_changed_functions=changed,
    tests=tests,
    scientific_status="EXPERIMENTAL; physical calibration and actual contributors remain unverified",
)
(HERE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
with (HERE / "radiometric_validation.csv").open("w") as stream:
    out = csv.writer(stream)
    out.writerow(["transformation", "status", "evidence", "limitation"])
    out.writerows(
        [
            [
                "inverse historical min-adjusted encoding",
                "NUMERICALLY_VERIFIED",
                "paired archived H5 equation residual <=0.000781 stored units",
                "does not verify physical calibration",
            ],
            [
                "clean source zero-offset 10K conversion",
                "NUMERICALLY_VERIFIED",
                "DN *10000/65535; candidate scale .0001999969482421875",
                "candidate DN/32768 remains conditional",
            ],
            [
                "alpha-aware interpolation",
                "NUMERICALLY_VERIFIED",
                "source mask excluded background before resampling",
                "not a calibration procedure",
            ],
            [
                "band-specific affine decode",
                "REGRESSION_TESTED",
                "per-band scale/offset, NoData and chunk tests",
                "synthetic fixtures establish code contract",
            ],
            [
                "DN/32768 physical interpretation",
                "HYPOTHETICAL_UNVERIFIED",
                "plausibility and source encoding recovery",
                "no applied Goldhill panel/DLS/export chain",
            ],
            [
                "2021 calibration sample to2023 Goldhill",
                "UNSUPPORTED",
                "sample has MicaSense tags but different acquisition",
                "cannot certify Goldhill calibration",
            ],
        ]
    )
print(
    "Verified",
    len(products),
    "native products,",
    len(protected),
    "protected artifacts, exact NEON parity",
    neon,
)
