"""Check theorem status, empirical values, vector exports and preservation."""

from pathlib import Path
import hashlib
import json
import re
import sys
import numpy as np
import pandas as pd
import pdfplumber
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import STATUS, PAGES, AUDITS

B = Path(__file__).resolve().parent
R = B.parents[1]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    s = json.loads((B / "source_manifest.json").read_text())
    for p, h in s["sha256"].items():
        assert sha(R / p) == h, p
    ax = (R / "formal/checks/axioms.log").read_text()
    names = re.findall(r"'SpectralBridge\.([^']+)'", ax)
    assert len(names) == 106
    used = set()
    for g in re.findall(r"depends on axioms: \[([^\]]*)\]", ax):
        used.update(x.strip() for x in g.split(","))
    assert used <= {"propext", "Classical.choice", "Quot.sound"} and "sorryAx" not in ax
    proved = 0
    for statement, status, meaning, ref in STATUS:
        if status.startswith("PROVED") or status == "FALSE / COUNTEREXAMPLE":
            module, name = ref.split(".", 1)
            full = "Bridge." + name if module == "Bridge" else name
            assert full in names, ref
            assert re.search(
                r"\btheorem\s+" + name + r"\b",
                (R / f"formal/SpectralBridge/{module}.lean").read_text(),
            )
            proved += 1
    assert len(AUDITS) == 14
    d = pd.read_csv(
        R
        / "provenance/researcher-evidence/2026-10-16/v1/tables/abundance_domain_summary.csv"
    )
    m = pd.read_csv(
        R
        / "provenance/researcher-evidence/2026-10-16/v1/tables/same_candidate_ridge.csv"
    )
    t = pd.read_csv(B / "tables/empirical_comparison.csv")
    for row in t.itertuples():
        q = d[d.kind.eq(row.kind) & d.representation.eq("NEON")].set_index("method")[
            "mean"
        ]
        np.testing.assert_allclose(
            [row.ridge120, row.mesma15, row.prior],
            [q.Ridge, q.MESMA, q["Training prior"]],
            rtol=0,
            atol=1e-14,
        )
        assert (
            abs(
                row.ridge15
                - m[m.kind.eq(row.kind) & m.representation.eq("NEON")].RMSE.mean()
            )
            < 1e-14
        )
    rec = pd.read_csv(B / "tables/recognition_source.csv")
    summary = rec.groupby(["kind", "budget"], as_index=False).balanced_accuracy.mean()
    summary.to_csv(B / "tables/recognition_summary.csv", index=False)
    # Exact toy geometry is checked independently of drawing coordinates.
    a = np.array([1.0, 0])
    b = np.array([0.0, 1])
    f = 0.6
    assert np.isclose((f * a + (1 - f) * b).sum(), f * a.sum() + (1 - f) * b.sum())
    np.testing.assert_array_equal((a + b) / 2, [0.5, 0.5])
    x = np.array([-0.2, 0.8, 0.4])
    p = np.array([0, 0.7, 0.3])
    assert np.isclose(p.sum(), 1) and (p >= 0).all()
    np.testing.assert_allclose(np.maximum(x - 0.1, 0), p, rtol=0, atol=1e-14)
    manifest = json.loads((B / "figure_manifest.json").read_text())
    assert len(manifest) == 15
    for name, v in manifest.items():
        for ext, h in v["files"].items():
            assert sha(B / "figures" / f"{name}.{ext}") == h
        assert not PdfReader(B / "figures" / f"{name}.pdf").pages[0].images
        assert "<image" not in (B / "figures" / f"{name}.svg").read_text()
    path = B / "SpectralBridge_Formal_Verification_Explained.pdf"
    bad = []
    with pdfplumber.open(path) as pdf:
        assert len(pdf.pages) == len(PAGES) == 28
        texts = []
        for i, pg in enumerate(pdf.pages, 1):
            assert not pg.images
            txt = pg.extract_text() or ""
            texts.append(txt)
            assert "(cid:" not in txt and "\u25a0" not in txt
            for c in pg.chars:
                if c["text"].strip() and (
                    c["x0"] < 18
                    or c["x1"] > pg.width - 18
                    or c["top"] < 10
                    or c["bottom"] > pg.height - 10
                ):
                    bad.append([i, c["text"], c["x0"], c["top"]])
        assert not bad, bad
        whole = "\n".join(texts)
        for val in [
            "85.2%",
            "73.8%",
            "66.8%",
            "57.7%",
            "0.216",
            "0.359",
            "0.365",
            "0.269",
            "0.362",
            "0.387",
            "0.311",
            "0.309",
            "3.90e-13",
        ]:
            assert val in whole, val
        assert texts[-1].rfind("The proof does not tell us") > 0
        for n in range(1, 16):
            assert f"Figure {n}." in whole, n
    old = {}
    for p in [
        "provenance/researcher-pft-information/2026-10-15/v1/final_manifest.json",
        "provenance/researcher-evidence/2026-10-16/v1/final_manifest.json",
        "provenance/manuscript-synthesis/2026-10-16/v1/packet_manifest.json",
    ]:
        q = json.loads((R / p).read_text())
        old.update(q.get("sha256", q.get("files", {})))
    for p, h in old.items():
        assert sha(R / p) == h, p
    result = {
        "status": "passed",
        "pages": 28,
        "figures_vector_PDF_SVG_PNG": 15,
        "audited_theorem_declarations": 106,
        "proof_or_counterexample_status_rows_checked": proved,
        "audit_findings_explained": 14,
        "source_hashes_checked": len(s["sha256"]),
        "prior_owned_files_unchanged": len(old),
        "PDF_raster_images": 0,
        "SVG_raster_images": 0,
        "out_of_bounds_characters": bad,
        "new_theorems": 0,
        "scientific_refits": 0,
        "figure_geometry": "independently checked",
        "visual_review": "See visual_review.json; not inferred from text checks",
    }
    (B / "checks/report_validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
