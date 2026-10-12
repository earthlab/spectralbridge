"""Record a successful canonical JOSS build; never infer visual-review completion."""

from pathlib import Path
import argparse
import hashlib
import json
import re


def record(paper, image, review_note=None, pages=None):
    paper = Path(paper)
    pdf = paper / "generated/paper.pdf"
    inputs = ["paper.md", "paper.bib"] + re.findall(
        r"\]\((figures/[^)]+)\)", (paper / "paper.md").read_text()
    )
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    report = {
        "renderer": "openjournals/inara",
        "image": image,
        "journal": "joss",
        "network": "disabled during render",
        "canonical_source": "paper/",
        "inputs": {name: sha(paper / name) for name in sorted(set(inputs))},
        "pdf_sha256": sha(pdf),
        "compile_success": True,
        "visual_review": review_note or "Pending visual review of this exact PDF",
        "submission_status": "Author declarations and reviewed public submission pending",
    }
    if pages is not None:
        report["preview_pages"] = pages
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--review-note")
    parser.add_argument("--pages", type=int)
    args = parser.parse_args()
    paper = Path(__file__).resolve().parents[1] / "paper"
    report = record(paper, args.image, args.review_note, args.pages)
    (paper / "generated/build-verification.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
