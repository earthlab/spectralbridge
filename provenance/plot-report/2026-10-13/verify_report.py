"""Contract checks for evidence consistency, PDF attachments and page geometry."""

from pathlib import Path
import json
import hashlib
import math
from pypdf import PdfReader
import pdfplumber

root = Path.cwd()
out = root / "output/pdf/plant_spectral_review"
evidence = json.loads((out / "report_evidence.json").read_text())
pdf = out / "spectral_plots_methods_robustness_report.pdf"
reader = PdfReader(pdf)
assert len(reader.pages) == 33
for name in ["report_evidence.json", "accuracy_intervals.csv", "figure_inventory.json"]:
    assert reader.attachments[name][0] == (out / name).read_bytes()
for name, digest in evidence["source_hashes"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
assert len(evidence["inventory"]) == 46
assert sum(row["pages"] for row in evidence["inventory"]) == 421
assert evidence["audit"]["finite_bands_per_pixel_min_max"] == [426, 426]
assert evidence["comparison"]["main_plants"] == 1886
assert evidence["year"]["plants_observed_multiple_years"] == 886
for row in evidence["accuracy_intervals"]:
    n, k = row["n"], row["correct"]
    z = 1.959963984540054
    phat = k / n
    center = (phat + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    assert math.isclose(row["wilson_low"], center - half, abs_tol=1e-12)
    assert math.isclose(row["wilson_high"], center + half, abs_tol=1e-12)
    matching = next(
        r
        for r in evidence["matching"]
        if (r["scope"], r["stage"]) == (row["scope"], row["stage"])
    )
    assert matching["held_out_plants"] == n
    assert math.isclose(matching["top1_accuracy"], phat, abs_tol=1e-12)
all_text = " ".join(" ".join(p.extract_text() for p in reader.pages).split())
for term in [
    "57/363",
    "37.3684%",
    "421 pages",
    "unverified",
    "886",
    "No new model fit",
]:
    assert term in all_text, term
assert "\ufffd" not in all_text and "\u25a0" not in all_text
assert all(len(p.extract_text()) > 600 for p in reader.pages)
with pdfplumber.open(pdf) as doc:
    for n, page in enumerate(doc.pages, 1):
        for word in page.extract_words():
            assert word["x0"] >= -1 and word["x1"] <= page.width + 1, (n, word)
            assert word["top"] >= -1 and word["bottom"] <= page.height + 1, (n, word)
receipt = {
    "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
    "pages": len(reader.pages),
    "original_pdf_artifacts": len(evidence["inventory"]),
    "original_pages_including_aliases": 421,
    "embedded_attachments": list(reader.attachments),
    "checked_source_inputs": len(evidence["source_hashes"]),
    "checked_accuracy_intervals": len(evidence["accuracy_intervals"]),
    "authoring_sources_sha256": {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (root / "provenance/plot-report/2026-10-13").glob("*.py")
    },
}
(out / "report_validation.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(
    json.dumps(
        {k: v for k, v in receipt.items() if k != "authoring_sources_sha256"}, indent=2
    )
)
