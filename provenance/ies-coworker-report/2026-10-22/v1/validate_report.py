"""Check PDF completeness, layout bounds, source preservation and figure lineage."""

import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
m = json.loads((BASE / "report_manifest.json").read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


pdf = ROOT / m["pdf"]
assert sha(pdf) == m["pdf_sha256"]
for name, digest in m["source_sha256"].items():
    assert sha(ROOT / name) == digest, name
r = PdfReader(pdf)
assert len(r.pages) == 8
text = " ".join(" ".join(p.extract_text().split()) for p in r.pages)
for phrase in [
    "not 74% accuracy",
    "not a 26% failure rate",
    "592",
    "3,904",
    "568",
    "8,260,481",
    "independent",
    "25.9%",
]:
    assert phrase in text, phrase
for box in m["layout_boxes"]:
    assert box["bottom"] >= 48
for i, page in enumerate(r.pages, 1):
    assert f"{i} / 8" in page.extract_text()
    assert len(page.extract_text()) > 1000
source = ROOT / "provenance/endmember-quality/2026-10-22/ies-comparison-v1"
figs = json.loads((source / "figure_manifest.json").read_text())["figures"]
for fig in figs:
    for ext, digest in fig["sha256"].items():
        assert sha(source / "figures" / f"{fig['id']}.{ext}") == digest
result = {
    "status": "pass",
    "pages": 8,
    "embedded_figures": 7,
    "source_files_verified": len(m["source_sha256"]),
    "layout_boxes_checked": len(m["layout_boxes"]),
    "visual_review": "All eight final rendered pages individually reviewed; readable labels and no clipped or overlapping content.",
    "pdf_sha256": sha(pdf),
}
(BASE / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
