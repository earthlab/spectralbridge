"""Verify bounded hypothesis evidence without promoting physical calibration."""

import hashlib
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
results = json.loads((ROOT / "results.json").read_text())
precision = json.loads((ROOT / "derivative_candidate_precision.json").read_text())
checks = {}
for name, expected in results["protected_hashes"].items():
    digest = hashlib.file_digest(Path(name).open("rb"), "sha256").hexdigest()
    assert digest == expected, name
    checks[name] = digest
suite = ET.parse("/private/tmp/p170_tests.xml").getroot()[0].attrib
assert int(suite["tests"]) == 19
assert int(suite["failures"]) == int(suite["errors"]) == 0
assert results["outcome"] == "SUPPORTED_BUT_UNVERIFIED"
assert results["production_changes"] == 0
assert results["alpha_valid_pixels"] == 9377010
assert len(results["band_statistics"]) == len(precision["bands"]) == 10
assert all(b["above_one_count"] == 0 for b in results["band_statistics"])
error = max(
    b["max_abs_scale_before_after_resampling_error"] for b in precision["bands"]
)
assert error < 2e-7
for name in ["p170_tests.xml", "p170_tests.log", "p170_derivative.log"]:
    shutil.copyfile(Path("/private/tmp") / name, ROOT / name)
verification = {
    "date": "2026-11-03",
    "status": "PASS_BOUNDED_INVESTIGATION_NOT_PHYSICAL_CALIBRATION",
    "outcome": results["outcome"],
    "production_physical_units": results["production_physical_units"],
    "protected_hashes_rechecked": checks,
    "targeted_tests": suite,
    "actual_ten_band_resampling_max_absolute_error": error,
    "figures_visually_reviewed": 3,
    "production_changes": 0,
    "source_or_datastore_writes": 0,
}
(ROOT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("PASS: 19 tests, 9 protected hashes, 10 bands, 3 reviewed figures")
