"""Assemble a vector illustrated report, Markdown and source-linked tables."""

from pathlib import Path
import sys
import json
import hashlib
import re
import io
import html
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter, Transformation

sys.path.insert(0, str(Path(__file__).resolve().parent))
from content import PAGES, AUDITS, STATUS

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
TITLE = "SpectralBridge_Formal_Verification_Explained"
BLUE = colors.HexColor("#6495ED")
DARK = colors.HexColor("#25303D")
GRAY = colors.HexColor("#697787")
font = next(
    (ROOT / ".venv/lib").glob(
        "python*/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"
    )
)
pdfmetrics.registerFont(TTFont("DV", str(font)))
pdfmetrics.registerFont(TTFont("DV-Bold", str(font.with_name("DejaVuSans-Bold.ttf"))))
pdfmetrics.registerFontFamily(
    "DV", normal="DV", bold="DV-Bold", italic="DV", boldItalic="DV-Bold"
)
STYLES = {
    k: ParagraphStyle(
        k,
        fontName="DV-Bold" if k in ["title", "label"] else "DV",
        fontSize=size,
        leading=lead,
        textColor=DARK,
        spaceAfter=0,
    )
    for k, size, lead in [
        ("title", 21, 26),
        ("label", 10.4, 14),
        ("body", 10.6, 14.8),
        ("audit", 9.9, 13.4),
        ("caption", 9.5, 12.7),
        ("foot", 7.3, 10),
        ("cell", 9.4, 12.3),
        ("cellhead", 9.4, 12.3),
    ]
}
SRC = {
    "TRACEABILITY": "formal/TRACEABILITY.md",
    "CLAIMS": "formal/CLAIMS.md",
    "PROOF_STATUS": "formal/PROOF_STATUS.md",
    "ASSUMPTIONS": "formal/ASSUMPTIONS.md",
    "AUDIT": "formal/IMPLEMENTATION_AUDIT.md",
    "TRANSLATIONS": "formal/TRANSLATION_INVARIANCE.md",
    "AXIOMS": "formal/checks/axioms.log",
    "BRIDGE": "formal/SpectralBridge/Bridge.lean",
    "CONFORMANCE": "formal/tests/test_conformance.py",
    "PY_RESPONSE": "src/spectralbridge/resample.py",
    "PY_MIXTURE": "src/spectralbridge/mixtures.py",
    "PY_RIDGE": "provenance/researcher-pft-information/2026-10-15/v1/run_abundance.py",
    "SCIENTIFIC_REPORT": "output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf",
    "EMP_RECOGNITION": "provenance/researcher-pft-information/2026-10-15/v1/tables/complementary_feature_performance.csv",
    "EMP_ABUNDANCE": "provenance/researcher-evidence/2026-10-16/v1/tables/abundance_domain_summary.csv",
    "EMP_MATCHED": "provenance/researcher-evidence/2026-10-16/v1/tables/same_candidate_ridge.csv",
    "ORACLE": "provenance/researcher-pft-information/2026-10-15/v1/tables/oracle_solver_controls.csv",
}
refs = []


def source(r):
    if r in SRC:
        return SRC[r]
    module, name = r.split(".", 1)
    p = f"formal/SpectralBridge/{module}.lean"
    assert re.search(
        r"\b(?:theorem|def)\s+" + re.escape(name) + r"\b", (ROOT / p).read_text()
    ), r
    return p + ": " + name


def text(c, s, y, style="body", w=505, x=45):
    p = Paragraph(s, STYLES[style])
    _, h = p.wrap(w, 900)
    p.drawOn(c, x, y - h)
    return y - h


def table(c, rows, widths, y):
    data = [
        [Paragraph(str(s), STYLES["cellhead" if j == 0 else "cell"]) for s in row]
        for j, row in enumerate(rows)
    ]
    t = Table(data, colWidths=widths, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DFE9FC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, BLUE),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F5F7FA")],
                ),
            ]
        )
    )
    _, h = t.wrap(505, 900)
    t.drawOn(c, 45, y - h)
    return y - h


TRANS = [
    [
        "Transformation / actual path",
        "Class and preservation conditions",
        "Empirical assumption",
    ],
    [
        "NEON storage scaling<br/>io/neon.py",
        "Fixed multiplier: linear. Same scale and support preserve weights.",
        "Header scale represents the intended quantity.",
    ],
    [
        "NEON → synthetic OLI/MicaSense<br/>resample.py + pipeline SRFs",
        "Fixed sampled weights: linear, including epsilon. Exact normalized constants require true normalization.",
        "Response approximation adequately represents the target sensor.",
    ],
    [
        "Synthetic Landsat percentage adjustment<br/>pipeline brightness helper",
        "Fixed gains: linear on valid bands; axis and coefficients must match.",
        "Percent coefficients transfer to the intended comparison.",
    ],
    [
        "Native drone → Landsat-like<br/>drone_translation.py",
        "Wavelength-mapped affine. Shared transform preserves simplex weights. No convolution here.",
        "Synthetic NEON-derived coefficients are appropriate for native drone data.",
    ],
    [
        "Actual Landsat DN conversion<br/>landsat_agreement.py",
        "Affine: 0.0000275 × DN − 0.2 on valid DN [1,65455].",
        "Product metadata, QA and independent acquisition alignment.",
    ],
    [
        "Frozen topo/BRDF factors<br/>corrections.py",
        "Diagonal linear map at a location. Shared frozen positive factors preserve weights/signs.",
        "Geometry and fitted model are appropriate; masks remain fixed.",
    ],
    [
        "Fitted/clipped scene brightness<br/>brightness.py",
        "Data-dependent; frozen preclip map affine. Clipping is nonlinear. No universal preservation.",
        "Scene statistics and reference matching have scientific relevance.",
    ],
    [
        "Area-weighted footprint mean<br/>landsat_agreement.py",
        "Linear with fixed common support and normalized weights; commutes with shared affine maps.",
        "Registration, overlap and joint-valid support are correct.",
    ],
    [
        "Hierarchical polygon/year median<br/>plant_spectral_atlas.py",
        "Nonlinear under arbitrary mixing. Mean commutation does not apply.",
        "Labels, identities and reference variability represent intended cover.",
    ],
    [
        "Ridge + simplex projection<br/>researcher_information.py + benchmark",
        "Frozen raw prediction affine; projection nonlinear. No inverse uniqueness guarantee.",
        "Training fractions and distribution support the intended prediction.",
    ],
]


def empirical_table():
    d = pd.read_csv(ROOT / SRC["EMP_ABUNDANCE"])
    m = pd.read_csv(ROOT / SRC["EMP_MATCHED"])
    rows = [
        [
            "NEON synthetic target",
            "Ridge120",
            "MESMA15",
            "Matched Ridge15",
            "No-spectrum prior",
        ]
    ]
    records = []
    for kind, label in [
        ("plant", "New parents"),
        ("site", "Held sites"),
        ("year", "Global year"),
    ]:
        q = d[d.kind.eq(kind) & d.representation.eq("NEON")].set_index("method")["mean"]
        v = m[m.kind.eq(kind) & m.representation.eq("NEON")].RMSE.mean()
        rows.append(
            [
                label,
                f"{q.Ridge:.3f}",
                f"{q.MESMA:.3f}",
                f"{v:.3f}",
                f"{q['Training prior']:.3f}",
            ]
        )
        records.append(
            dict(
                kind=kind,
                ridge120=q.Ridge,
                mesma15=q.MESMA,
                ridge15=v,
                prior=q["Training prior"],
            )
        )
    pd.DataFrame(records).to_csv(OUT / "tables/empirical_comparison.csv", index=False)
    o = pd.read_csv(ROOT / SRC["ORACLE"])
    pd.DataFrame(
        [
            dict(
                statistic="Maximum saved oracle fraction RMSE",
                value=o.fraction_RMSE.max(),
                source=SRC["ORACLE"],
            )
        ]
    ).to_csv(OUT / "tables/oracle_summary.csv", index=False)
    return rows


def main():
    md = [
        "# SpectralBridge formal verification explained",
        "\nPreserving composition while losing identifiability.\n",
    ]
    temp = io.BytesIO()
    c = canvas.Canvas(temp, pagesize=(595.276, 841.89), invariant=1)
    placements = []
    geometry = []
    for i, page in enumerate(PAGES, 1):
        c.setFillColor(BLUE)
        c.rect(45, 800, 505, 3, fill=1, stroke=0)
        c.setFont("DV", 8.2)
        c.setFillColor(GRAY)
        c.drawString(45, 812, "SPECTRALBRIDGE / FORMAL VERIFICATION EXPLAINED")
        c.drawRightString(550, 812, "16 OCTOBER 2026")
        y = text(c, page["title"], 780, "title") - 13
        md += ["\n## " + page["title"]]
        for label, s in page["blocks"]:
            if label:
                y = text(c, html.escape(label), y, "label") - 3
            y = (
                text(
                    c,
                    s,
                    y,
                    "audit" if page["title"].startswith("Audit details") else "body",
                )
                - 10
            )
            md.append(
                ("\n### " + label + "\n" if label else "\n")
                + s.replace("<br/>", "\n").replace("<b>", "**").replace("</b>", "**")
            )
        if page["table"]:
            tid = page["table"]
            if tid.startswith("translations"):
                rows = TRANS[:6] if tid.endswith("1") else [TRANS[0]] + TRANS[6:]
                widths = [168, 205, 132]
            elif tid.startswith("status"):
                q = STATUS[:10] if tid.endswith("1") else STATUS[10:]
                rows = [["Scientific statement", "Status", "Meaning"]] + [
                    [x[0], x[1], x[2]] for x in q
                ]
                widths = [166, 120, 219]
            elif tid == "bridge":
                rows = [
                    ["Case", "Exact / simple example", "Absolute tolerance"],
                    ["Response weighting", "[2,6], weights [1,3]: ≈ 5", "10⁻⁶"],
                    ["Percentage multiplication", "100 → 95.555048", "10⁻⁵"],
                    ["Affine drone writer", "2 × 3 + 1 → 7", "10⁻⁶"],
                    ["Footprint mean", "Equal-area [2,6] → 4", "10⁻¹⁰"],
                    ["Synthetic mixture", "20% / 80% unit references", "10⁻¹⁵"],
                    ["FCLS oracle", "[0.25,0.75] recovered", "10⁻¹⁰"],
                    ["MESMA ambiguity", "C selected; A/B also exact", "10⁻¹⁰"],
                    ["Centered ridge", "[1/3,2/3] at input 0.5", "10⁻¹²"],
                    ["Simplex projection", "[-2,1,0.8] → [0,0.6,0.4]", "10⁻¹²"],
                ]
                widths = [145, 240, 120]
            else:
                rows = empirical_table()
                widths = [130, 92, 92, 99, 92]
            y = table(c, rows, widths, y) - 12
            if tid == "abundance":
                oracle = pd.read_csv(ROOT / SRC["ORACLE"]).fraction_RMSE.max()
                y = (
                    text(
                        c,
                        f"Lower fraction RMSE is better. Squared errors are averaged across fractions and mixtures, square-rooted per target, then averaged across folds. The known-parent oracle maximum fraction RMSE is {oracle:.2e}.",
                        y,
                        "caption",
                    )
                    - 8
                )
            md += [
                "\n|" + "|".join(rows[0]) + "|",
                "|" + "|".join(["---"] * len(rows[0])) + "|",
            ] + ["|" + "|".join(row) + "|" for row in rows[1:]]
        if page["figure"]:
            n = page["figure"]
            p = PdfReader(OUT / "figures" / f"figure_{n:02d}.pdf").pages[0]
            aspect = float(p.mediabox.height) / float(p.mediabox.width)
            h = min(
                505 * aspect,
                310
                if n == 10
                else 360
                if n == 1
                else 350
                if n == 11
                else 230
                if n in [7, 9]
                else 245,
            )
            w = h / aspect
            x = 45 + (505 - w) / 2
            placements.append((i - 1, n, x, y - h, w / float(p.mediabox.width)))
            y -= h + 13
            md.append(f"\n![Figure {n}](figures/figure_{n:02d}.png)")
            y = (
                text(
                    c,
                    html.escape(
                        "Figure "
                        + str(n)
                        + ". "
                        + json.loads((OUT / "figure_manifest.json").read_text())[
                            f"figure_{n:02d}"
                        ]["title"]
                    ),
                    y,
                    "label",
                )
                - 5
            )
            for label, s in page["caption"]:
                y = text(c, "<b>" + label + "</b> " + s, y, "caption") - 5
                md.append("\n**" + label + "** " + s)
        sr = [source(r) for r in page["refs"]]
        refs.extend(sr)
        foot = "Evidence: " + "; ".join(page["refs"])
        text(c, html.escape(foot), 48, "foot")
        c.setFont("DV", 7.4)
        c.setFillColor(GRAY)
        c.drawString(
            45,
            22,
            "Mathematical guarantees are conditional; synthetic fractions are not field cover.",
        )
        c.drawRightString(550, 22, str(i))
        if y < 65:
            raise ValueError(f"Page {i} overflow: final body y={y:.1f}")
        geometry.append(
            {
                "page": i,
                "title": page["title"],
                "body_bottom_pt": round(y, 2),
                "figure": page["figure"],
            }
        )
        md.append("\nEvidence: " + "; ".join("`" + r + "`" for r in sr))
        c.showPage()
    c.save()
    temp.seek(0)
    reader = PdfReader(temp)
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
    for i, n, x, y, scale in placements:
        overlay = PdfReader(OUT / "figures" / f"figure_{n:02d}.pdf").pages[0]
        writer.pages[i].merge_transformed_page(
            overlay, Transformation().scale(scale).translate(x, y), over=False
        )
    writer.add_metadata(
        {
            "/Title": "SpectralBridge formal verification explained",
            "/Author": "SpectralBridge science team / OpenAI Codex synthesis",
            "/Subject": "Composition preservation, information loss and scientific interpretation",
            "/CreationDate": "D:20261016000000Z",
        }
    )
    with (OUT / (TITLE + ".pdf")).open("wb") as f:
        writer.write(f)
    (OUT / (TITLE + ".md")).write_text("\n".join(md) + "\n")
    pd.DataFrame(
        STATUS, columns=["statement", "status", "meaning", "source_reference"]
    ).to_csv(OUT / "tables/proof_status.csv", index=False)
    pd.DataFrame(
        AUDITS,
        columns=[
            "finding",
            "code",
            "expected",
            "difference",
            "outputs",
            "existing_results",
            "severity",
            "action",
        ],
    ).to_csv(OUT / "tables/implementation_audit.csv", index=False)
    pd.DataFrame(TRANS[1:], columns=TRANS[0]).to_csv(
        OUT / "tables/transformations.csv", index=False
    )
    (OUT / "checks/layout.json").write_text(json.dumps(geometry, indent=2) + "\n")
    allsources = (
        set(SRC.values())
        | {
            f"formal/SpectralBridge/{p.name}"
            for p in (ROOT / "formal/SpectralBridge").glob("*.lean")
        }
        | {
            "formal/README.md",
            "formal/CLAIMS.md",
            "formal/PROOF_STATUS.md",
            "formal/ASSUMPTIONS.md",
            "formal/IMPLEMENTATION_AUDIT.md",
            "formal/TRANSLATION_INVARIANCE.md",
            "formal/TRACEABILITY.md",
        }
    )
    allsources |= {
        str(p.relative_to(ROOT)) for p in (ROOT / "src/spectralbridge").rglob("*.py")
    }
    allsources |= {
        "src/spectralbridge/data/landsat_band_parameters.json",
        "src/spectralbridge/data/drone_translation_coefficients_v1.json",
        "src/spectralbridge/data/brightness/landsat_to_micasense.json",
        "src/spectralbridge/data/brightness/landsat_tm_etm_to_micasense.json",
        "provenance/researcher-evidence/2026-10-16/v1/run_candidate_control.py",
    }
    (OUT / "source_manifest.json").write_text(
        json.dumps(
            {
                "scope": "Read-only formal, implementation and canonical evidence sources; generated report adds no theorems or scientific fits",
                "sha256": {
                    s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                    for s in sorted(allsources)
                },
                "page_evidence": {
                    str(i): [source(r) for r in p["refs"]]
                    for i, p in enumerate(PAGES, 1)
                },
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "Built",
        len(PAGES),
        "pages; minimum body bottom",
        min(x["body_bottom_pt"] for x in geometry),
    )


if __name__ == "__main__":
    main()
