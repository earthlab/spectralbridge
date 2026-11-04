"""Preserve requested native deliverables outside temporary scratch, without Git binaries."""

import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "archive/local/drone-integrated-reliability/2026-11-04"
OUT.mkdir(parents=True, exist_ok=True)
records = json.loads((HERE / "verification.json").read_text())["products"]
for r in records:
    source = Path(r["path"])
    target = OUT / source.name
    shutil.copy2(source, target)
    h = hashlib.sha256()
    with target.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    assert h.hexdigest() == r["sha256"]
    r["persistent_path"] = str(target)
    branch = r["branch"]
    model = HERE / (branch + "_model.json")
    if model.exists():
        shutil.copy2(model, OUT / model.name)
shutil.copy2(
    "/private/tmp/drone-integrated-reliability-20261104/final_v2/conditioned_topographic_status.tif",
    OUT / "conditioned_topographic_status.tif",
)
for name in [
    "conditioned_scsc_model.json",
    "pipeline_results.json",
    "evaluation_contract.json",
    "verification.json",
    "radiometric_validation.csv",
    "native_vs_common_extremes.json",
]:
    shutil.copy2(HERE / name, OUT / name)
(HERE / "product_catalog.json").write_text(json.dumps(records, indent=2) + "\n")
(OUT / "product_catalog.json").write_text(json.dumps(records, indent=2) + "\n")
(OUT / "README.txt").write_text(
    "EXPERIMENTAL ONLY. Candidate DN/32768 calibration and inferred camera contributors are unverified. Both correction stages are active in combined images. Never import these into an approved spectral library. See the scientific report and product_catalog.json for methods, hashes, models, status masks and limitations.\n"
)
print("Preserved", len(records), "native GeoTIFFs and topographic status at", OUT)
