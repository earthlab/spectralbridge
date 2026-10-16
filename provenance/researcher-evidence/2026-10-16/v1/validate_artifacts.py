"""Check source traceability, all page geometry, figure and PDF exact rebuilding."""

from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import pdfplumber
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    m = json.loads((BASE / "report_manifest.json").read_text())
    pdf = REPO / m["pdf"]
    for name, h in m["numerical_source_hashes"].items():
        assert sha(REPO / name) == h, name
    for group in ["table_hashes", "figure_hashes"]:
        for name, h in m[group].items():
            assert sha(BASE / name) == h, name
    assert m["pages"] == len(PdfReader(pdf).pages)
    outside = []
    counts = []
    captions = 0
    alltext = []
    with pdfplumber.open(pdf) as doc:
        for i, page in enumerate(doc.pages, 1):
            text = page.extract_text() or ""
            alltext.append(text)
            counts.append(len(text.split()))
            assert len(text.split()) >= 60, (
                i,
                "orphan or near-empty page",
                len(text.split()),
            )
            captions += text.count("HOW TO READ IT")
            for word in page.extract_words():
                if (
                    word["x0"] < 0
                    or word["x1"] > page.width + 0.5
                    or word["top"] < 0
                    or word["bottom"] > page.height + 0.5
                ):
                    outside.append((i, word["text"]))
    text = "\n".join(alltext)
    assert not re.search(r"\b(?:DBS|DBT|EBS|ECS|ECT)\b", text)
    assert captions == 10, captions
    for name in ["WHAT WE LEARN", "WHAT REMAINS UNCERTAIN"]:
        assert text.count(name) == 10, name
    for name in [
        "1. SEPARABILITY",
        "2. IDENTIFIABILITY",
        "3. ABUNDANCE",
        "FINAL EVIDENCE LADDER",
        "LIMITATIONS",
        "WHAT DATA SHOULD BE COLLECTED NEXT",
        "REPRODUCIBILITY",
        "HOW ACCURATELY",
        "WHERE IT TRANSFERS",
        "WHERE IT FAILS",
    ]:
        assert name in text, name
    assert not outside, outside
    before = sha(pdf)
    assert before == m["pdf_sha256"]
    subprocess.run(
        [sys.executable, str(BASE / "build_report.py")], check=True, cwd=REPO
    )
    assert sha(pdf) == before
    result = {
        "status": "passed",
        "pages": m["pages"],
        "figure_explanations": captions,
        "out_of_bounds_words": outside,
        "retired_codes_in_primary_report": False,
        "minimum_words_per_page": min(counts),
        "PDF_byte_identical": True,
        "numerical_source_files_checked": len(m["numerical_source_hashes"]),
        "table_files_checked": len(m["table_hashes"]),
        "figure_files_checked": len(m["figure_hashes"]),
    }
    (BASE / "artifact_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
