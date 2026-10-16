"""PDF/SVG vector, print size, high-resolution PNG and actual drawn-text QA.

Run with a Python containing pypdf, pdfplumber and Pillow.
"""

from pathlib import Path
import json
import re
from PIL import Image
from pypdf import PdfReader
import pdfplumber

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "provenance/manuscript-synthesis/2026-10-16/v1"
OUT = REPO / "output/figures/manuscript_synthesis"


def main():
    reader = PdfReader(OUT / "figure_main_synthesis.pdf")
    assert len(reader.pages) == 1
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    assert abs(width / 72 * 25.4 - 190) < 0.01
    images = []

    def resources(res):
        for name, ref in res.get("/XObject", {}).items():
            obj = ref.get_object()
            if obj.get("/Subtype") == "/Image":
                images.append(name)
            if obj.get("/Resources"):
                resources(obj["/Resources"])

    resources(page["/Resources"])
    assert not images, images
    svg = (OUT / "figure_main_synthesis.svg").read_text()
    assert "<image" not in svg
    png = Image.open(OUT / "figure_main_synthesis.png")
    dpi = png.info["dpi"]
    assert min(dpi) > 599.9 and png.width >= 4488 and png.height >= 6209
    outside = []
    with pdfplumber.open(OUT / "figure_main_synthesis.pdf") as f:
        p = f.pages[0]
        text = p.extract_text()
        for word in p.extract_words():
            if (
                word["x0"] < -0.2
                or word["x1"] > width + 0.2
                or word["top"] < -0.2
                or word["bottom"] > height + 0.2
            ):
                outside.append(word["text"])
    assert not outside, outside
    assert not re.search(r"\b(?:DBS|DBT|EBS|ECS|ECT)\b", text)
    for token in [
        "81.6%",
        "77.4%",
        "70.1%",
        "65.0%",
        "85.2%",
        "73.8%",
        "46.3%",
        "40%",
        "26%",
        "Ridge120",
        "Ridge15",
        "MESMA15",
        "Synthetic fractions",
    ]:
        assert token in text, token
    # Compare every decimal annotation with the final report text, not a copied label.
    with pdfplumber.open(
        REPO
        / "output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf"
    ) as f:
        report = "\n".join(p.extract_text() or "" for p in f.pages)
    for token in [
        "81.6%",
        "77.4%",
        "70.1%",
        "65.0%",
        "85.2%",
        "73.8%",
        "46.3%",
        "39.8%",
        "25.6%",
    ]:
        assert token in report, token
    result = {
        "status": "passed",
        "PDF_pages": 1,
        "PDF_width_mm": width / 72 * 25.4,
        "PDF_height_mm": height / 72 * 25.4,
        "PDF_raster_images": len(images),
        "SVG_raster_images": 0,
        "PNG_pixels": list(png.size),
        "PNG_dpi": list(dpi),
        "out_of_bounds_drawn_words": outside,
        "annotations_match_final_validation_report": True,
    }
    (BASE / "export_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
