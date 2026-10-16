"""Verify report geometry, primary label boundary, hashes and exact rebuilding."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import pdfplumber
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]


def main():
    manifest = json.loads((BASE / "report_manifest.json").read_text())
    pdf = REPO / manifest["pdf"]
    for group in ["table_hashes", "figure_hashes"]:
        for name, expected in manifest[group].items():
            assert hashlib.sha256((BASE / name).read_bytes()).hexdigest() == expected, (
                name
            )
    source = json.loads((BASE / "report_source.json").read_text())
    assert len(source["figures"]) == 15
    reader = PdfReader(pdf)
    assert len(reader.pages) == 20
    outside = []
    with pdfplumber.open(pdf) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
        assert not re.search(r"\b(?:DBS|DBT|EBS|ECS|ECT)\b", text)
        for number, page in enumerate(doc.pages, 1):
            for word in page.extract_words():
                if (
                    word["x0"] < 0
                    or word["x1"] > page.width + 0.5
                    or word["top"] < 0
                    or word["bottom"] > page.height + 0.5
                ):
                    outside.append((number, word["text"]))
        for number, item in enumerate(source["figures"], start=2):
            page_text = doc.pages[number].extract_text()
            for header in ["HOW TO READ IT", "WHAT WE LEARN", "WHAT REMAINS UNCERTAIN"]:
                assert header in page_text, (number, header)
            assert reader.pages[number]["/Resources"].get("/XObject")
    assert not outside, outside
    before = hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert before == manifest["pdf_sha256"]
    subprocess.run(
        [sys.executable, str(BASE / "build_report.py")], cwd=REPO, check=True
    )
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == before
    result = {
        "status": "passed",
        "pages": 20,
        "figure_stories": 15,
        "out_of_bounds_words": outside,
        "retired_group_codes_in_primary_report": False,
        "table_hashes_checked": len(manifest["table_hashes"]),
        "figure_files_checked": len(manifest["figure_hashes"]),
        "report_rebuild_byte_identical": True,
    }
    (BASE / "pdf_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
