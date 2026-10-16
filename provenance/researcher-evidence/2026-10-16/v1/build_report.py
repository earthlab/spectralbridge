"""Publication PDF from editable three-question source and saved numerical tables."""

from pathlib import Path
from html import escape
import hashlib
import json
from PIL import Image as PILImage
from pypdf import PdfReader
from reportlab import rl_config
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)
import pandas as pd

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
PRIOR = REPO / "provenance/researcher-pft-information/2026-10-15/v1"
OUT = (
    REPO
    / "output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf"
)
OUT.parent.mkdir(parents=True, exist_ok=True)
W, H = 1008, 756
WIDTH = 912
rl_config.invariant = 1
for name, file in [("Body", "Arial.ttf"), ("Bold", "Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, "/System/Library/Fonts/Supplemental/" + file))
pdfmetrics.registerFontFamily(
    "Body", normal="Body", bold="Bold", italic="Body", boldItalic="Bold"
)
S = {
    "body": ParagraphStyle(
        "body",
        fontName="Body",
        fontSize=11.3,
        leading=15,
        textColor="#193c4a",
        spaceAfter=9,
    ),
    "title": ParagraphStyle(
        "title",
        fontName="Bold",
        fontSize=22,
        leading=27,
        textColor="#123e51",
        spaceAfter=12,
    ),
    "head": ParagraphStyle(
        "head",
        fontName="Bold",
        fontSize=12,
        leading=15,
        textColor="#147d88",
        spaceBefore=4,
        spaceAfter=4,
        keepWithNext=True,
    ),
    "table": ParagraphStyle(
        "table", fontName="Body", fontSize=10.3, leading=13, textColor="#193c4a"
    ),
    "caption": ParagraphStyle(
        "caption", fontName="Body", fontSize=10.4, leading=13, textColor="#193c4a"
    ),
    "small": ParagraphStyle(
        "small",
        fontName="Body",
        fontSize=8.4,
        leading=10.5,
        textColor="#526975",
        spaceAfter=5,
    ),
}


def p(text, style="body"):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), S[style])


def table(headers, rows, widths):
    data = [[p(v, "table") for v in headers]] + [
        [p(v, "table") for v in row] for row in rows
    ]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dae9eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#147d88")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f3f7f8")],
                ),
            ]
        )
    )
    return t


def section_table(key):
    if key in ["FOUNDATION", "SEPARABILITY", "IDENTIFIABILITY", "ABUNDANCE"]:
        f = pd.read_csv(BASE / "tables/design_validation.csv")
        f = f[f.section.eq(key)]
        return table(
            ["Requirement", "Status", "Test/result"],
            [[r.requirement, r.status, r.result] for r in f.itertuples()],
            [230, 90, 592],
        )
    if key == "PAIR_SUPPORT":
        f = pd.read_csv(BASE / "tables/pair_support_and_evidence.csv")
        return table(
            [
                "Pair",
                "Cohorts",
                "Minimum class support A/B",
                "Effect range",
                "Largest adjusted p",
            ],
            [
                [
                    r.contrast,
                    r.cohorts,
                    f"{r.minimum_class_a_IDs}/{r.minimum_class_b_IDs}",
                    f"{r.min_NEON_effect:.2f}-{r.max_NEON_effect:.2f}",
                    f"{r.largest_adjusted_NEON_p:.3f}",
                ]
                for r in f.itertuples()
            ],
            [355, 65, 180, 130, 182],
        )
    if key == "PAIRED":
        f = pd.read_csv(BASE / "tables/abundance_paired_vs_baselines.csv")
        f = f[f.method.eq("Ridge") & f.representation.eq("NEON")]
        rows = []
        for (fold, target), g in f.groupby(["fold", "target"]):
            a = g[g.reference.eq("MESMA")].iloc[0]
            b = g[g.reference.eq("Training prior")].iloc[0]

            def interval(r):
                return f"{r.difference:+.3f} [{r.difference_low:+.3f}, {r.difference_high:+.3f}]"

            rows.append(
                [fold + " / " + target, f"{a.RMSE:.3f}", interval(a), interval(b)]
            )
        return table(
            [
                "Training / target",
                "Ridge RMSE",
                "Ridge - MESMA [95% interval]",
                "Ridge - prior [95% interval]",
            ],
            rows,
            [300, 100, 256, 256],
        )
    if key == "DETECTION":
        f = pd.read_csv(PRIOR / "tables/abundance_model_comparison.csv")
        f = (
            f[
                f.kind.eq("site")
                & f.representation.eq("NEON")
                & f.method.isin(["Ridge", "Two-stage"])
            ]
            .groupby(["researcher_category", "method"])[
                ["positive_RMSE", "bias", "FPR", "low_FNR"]
            ]
            .mean()
            .reset_index()
        )
        stage = pd.read_csv(PRIOR / "tables/two_stage_presence_metrics.csv")
        stage = (
            stage[stage.kind.eq("site") & stage.representation.eq("NEON")]
            .groupby("researcher_category")[["stage_A_recall", "stage_A_FPR"]]
            .mean()
        )
        rows = []
        for r in f.itertuples():
            a = stage.loc[r.researcher_category]
            rows.append(
                [
                    r.researcher_category,
                    r.method,
                    f"{r.positive_RMSE:.3f}",
                    f"{r.bias:+.3f}",
                    f"{r.FPR:.3f}",
                    f"{r.low_FNR:.3f}",
                    f"{a.stage_A_recall:.3f} / {a.stage_A_FPR:.3f}"
                    if r.method == "Two-stage"
                    else "n/a",
                ]
            )
        return table(
            [
                "Category",
                "Method",
                "Positive RMSE",
                "Bias",
                "Final FPR",
                "Low FNR",
                "Stage A recall / FPR",
            ],
            rows,
            [200, 110, 110, 90, 90, 90, 222],
        )
    if key == "LIMITING":
        rows = [
            [
                "Solver failure",
                "Ideal known-parent oracle is near exact. Solver failure is not the explanation for the controlled candidate-library errors.",
            ],
            [
                "Spectral resolution",
                "OLI loses recognition and some synthetic fraction information. Shared-source convolution does not test actual satellite scaling or PSF.",
            ],
            [
                "Candidate-library variability",
                "Ridge120 gains disappear in the same-candidate NEON ridge15 control. Retained parent diversity/capacity matters, but the control does not isolate one causal mechanism.",
            ],
            [
                "Class overlap",
                "Candidate near-solutions and recognition errors persist. Better expected fractions do not make every composition unique.",
            ],
            [
                "Geographic shift",
                "Held-site recognition and fraction errors worsen. Three observational sites cannot establish broad geographic universality.",
            ],
            [
                "Temporal shift",
                "Paired recognition/abundance differences and global-year failures remain. Static annotations and confounding block ecological causal attribution.",
            ],
            [
                "Training priors",
                "The no-spectrum prior defeats ridge on global-year mean. Projection and learned fraction/shape priors contribute to performance.",
            ],
            [
                "Independent field truth",
                "Missing. No synthetic result can establish real fractional cover, physical purity or real mixing-linearity validity.",
            ],
        ]
        return table(
            ["Potential limit", "What the evidence actually supports"], rows, [220, 692]
        )
    if key == "LADDER":
        f = pd.read_csv(BASE / "tables/evidence_ladder.csv")
        return table(
            ["Level / question", "Status", "Exact supporting evidence", "Scope"],
            [
                [str(r.level) + " / " + r.question, r.status, r.evidence, r.scope]
                for r in f.itertuples()
            ],
            [150, 125, 337, 300],
        )
    if key.startswith("ADVERSARIAL:"):
        start = int(key.split(":")[1])
        f = pd.read_csv(BASE / "tables/adversarial_validation.csv").iloc[
            start : start + 7
        ]
        return table(
            [
                "Claim / failure mode",
                "Test performed",
                "Result / status",
                "Remaining limitation",
            ],
            [
                [
                    r.claim + " / " + r.potential_failure_mode,
                    r.test_performed,
                    r.result + "\n" + r.status,
                    r.remaining_limitation,
                ]
                for r in f.itertuples()
            ],
            [225, 225, 242, 220],
        )
    raise ValueError(key)


def header(canvas, doc):
    canvas.setFillColor(colors.HexColor("#147d88"))
    canvas.rect(0, H - 13, W, 13, fill=1, stroke=0)
    canvas.setFont("Body", 9)
    canvas.setFillColor(colors.HexColor("#526975"))
    canvas.drawString(
        48,
        H - 33,
        "SPECTRALBRIDGE  |  FIVE RESEARCHER CATEGORIES  |  SCIENTIFIC VALIDATION",
    )
    canvas.setStrokeColor(colors.HexColor("#c9dadf"))
    canvas.line(48, 28, W - 48, 28)
    canvas.setFont("Body", 8.3)
    canvas.drawString(
        48,
        15,
        "2026-10-16  •  Synthetic fractions are not independently validated field cover",
    )
    canvas.drawRightString(W - 48, 15, str(doc.page))


def main():
    source = json.loads((BASE / "report_source.json").read_text())
    story = []
    for i, page in enumerate(source["pages"]):
        if i:
            story.append(PageBreak())
        story.append(p(page["title"], "title"))
        for title, text in page["paragraphs"]:
            story.extend([p(title, "head"), p(text)])
        if page["table"]:
            story.extend([section_table(page["table"]), Spacer(1, 10)])
        if page["figure"]:
            f = source["figures"][page["figure"] - 1]
            path = BASE / "figures" / (f["name"] + ".png")
            iw, ih = PILImage.open(path).size
            # Figure geometry preserves readable labels; captions stay with the visual.
            maximum = 440 if not page["paragraphs"] else 365
            scale = min(WIDTH / iw, maximum / ih)
            image = Image(str(path), width=iw * scale, height=ih * scale)
            caps = []
            for title, key in [
                ("HOW TO READ IT", "how"),
                ("WHAT WE LEARN", "learn"),
                ("WHAT REMAINS UNCERTAIN", "uncertain"),
            ]:
                caps.append(
                    Paragraph(
                        "<b>" + title + "</b><br/>" + escape(f[key]), S["caption"]
                    )
                )
            caption = Table([caps], colWidths=[WIDTH / 3] * 3, hAlign="LEFT")
            caption.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#edf4f5")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            evidence = p("Numerical sources: " + "; ".join(f["sources"]), "small")
            story.append(
                KeepTogether([image, Spacer(1, 8), caption, Spacer(1, 6), evidence])
            )
        for title, text in page["ending"]:
            story.extend([p(title, "head"), p(text)])
        if page["sources"]:
            story.append(p("Evidence: " + "; ".join(page["sources"]), "small"))
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=(W, H),
        leftMargin=48,
        rightMargin=48,
        topMargin=48,
        bottomMargin=40,
        title=source["title"],
        author="SpectralBridge research analysis",
        subject="Researcher-category separability, recognition and synthetic abundance validation",
    )
    doc.build(story, onFirstPage=header, onLaterPages=header)

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    sources = {}
    for f in source["figures"]:
        for name in f["sources"]:
            path = (
                PRIOR / name.removeprefix("prior:")
                if name.startswith("prior:")
                else BASE / name
            )
            sources[str(path.relative_to(REPO))] = sha(path)
    manifest = {
        "pdf": str(OUT.relative_to(REPO)),
        "pdf_sha256": sha(OUT),
        "pages": len(PdfReader(OUT).pages),
        "editable_source_sha256": sha(BASE / "report_source.json"),
        "numerical_source_hashes": sources,
        "table_hashes": {
            str(p.relative_to(BASE)): sha(p)
            for p in sorted((BASE / "tables").iterdir())
            if p.is_file()
        },
        "figure_hashes": {
            str(p.relative_to(BASE)): sha(p)
            for p in sorted((BASE / "figures").iterdir())
            if p.suffix in [".png", ".pdf", ".svg"]
        },
    }
    (BASE / "report_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(OUT, "pages:", manifest["pages"])


if __name__ == "__main__":
    main()
