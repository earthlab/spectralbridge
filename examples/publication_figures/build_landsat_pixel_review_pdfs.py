"""Build the human review guide and complete61-patch/1241-cell atlas.

Consumes only prepared/hash-checked review artifacts. Run in an environment with
ReportLab, Pillow and pypdf after the two prepare_landsat_* scripts. No data labels
or cohort memberships are changed. Reviewer decisions remain blank.
"""

import csv
import hashlib
import json
import re
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "provenance/landsat-pure-pixels/2026-11-19/team-validation"
OUT = ROOT / "output/pdf"
NAVY = colors.HexColor("#263e56")
TEAL = colors.HexColor("#237d83")
GRAY = colors.HexColor("#66747e")
PALE = colors.HexColor("#edf3f4")
LINE = colors.HexColor("#dce5e8")
S = getSampleStyleSheet()
for name, size, leading, font, color in [
    ("T", 21, 25, "Helvetica-Bold", NAVY),
    ("H", 12, 16, "Helvetica-Bold", NAVY),
    ("B", 9.5, 13.2, "Helvetica", NAVY),
    ("Small", 8, 10.5, "Helvetica", GRAY),
    ("Cell", 8, 10, "Helvetica", NAVY),
    ("TH", 8, 10, "Helvetica-Bold", colors.white),
    ("Ledger", 7.5, 8.7, "Helvetica", NAVY),
    ("ReviewCode", 7.3, 10, "Courier", NAVY),
]:
    S.add(
        ParagraphStyle(
            name=name,
            fontName=font,
            fontSize=size,
            leading=leading,
            textColor=color,
            spaceAfter=7 if name in ["T", "B"] else 4,
        )
    )


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def P(text, style="B"):
    # Improve narrative spacing without altering stable IDs or file paths.
    text = re.sub(
        r"\b(All|all|in|of|at|to|from|by|the|for|pass|within|only|current|Prepared|November|over|across|nine|no-fill|above|below|Collection|most|after|tested|pages|The|and|proposed|meeting|page|What|not|proxy|conservative|surrounding|fill|Fmask|its|reach|Conservative|reaches|generated|despite|numbered|historical|extra|plus|USGS)(?=\d)",
        r"\1 ",
        text,
    )
    return Paragraph(text, S[style])


def H(text):
    return P(text, "H")


def image(path, width=520, maxheight=480):
    with PILImage.open(path) as img:
        w, h = img.size
    scale = min(width / w, maxheight / h)
    return Image(str(path), width=w * scale, height=h * scale, hAlign="CENTER")


def table(rows, widths, ledger=False):
    data = [
        [
            P(escape(str(v)), "TH" if i == 0 else "Ledger" if ledger else "Cell")
            for v in row
        ]
        for i, row in enumerate(rows)
    ]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    pad = 0.6 if ledger else 5
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 if ledger else 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 if ledger else 7),
                ("TOPPADDING", (0, 0), (-1, -1), pad),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, LINE),
            ]
        )
    )
    return t


def footer(label):
    def draw(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(
            36, 766, "SPECTRALBRIDGE | LANDSAT REFERENCE REVIEW | 19 NOVEMBER 2026"
        )
        canvas.setStrokeColor(LINE)
        canvas.line(36, 757, 576, 757)
        canvas.drawString(
            36, 22, label + " | Provisional labels; team validation pending"
        )
        canvas.drawRightString(576, 22, f"Page {doc.page}")

    return draw


def bool_value(x):
    return str(x).lower() in {"true", "1"}


def paragraphs(text):
    return [P(x) for x in text]


def context_page(c, role, ledger):
    photo = c["photo_date"][:10]
    hls = ", ".join(x[:10] for x in c["hls_dates"])
    story = [
        P(f"{c['id']} | {c['target']}", "T"),
        P(escape(role + " - " + c["context_patch_id"]), "Small"),
        P(
            f"{c['count']} retained cells; {c['strict_count']} also pass120 m screen. Aerial: {photo}; HLS: {hls}; maximum date gap {c['aerial_gap_max']} days.",
            "Small",
        ),
    ]
    story += [
        image(ROOT / c["plate"], width=535, maxheight=474),
        Spacer(1, 4),
        P("<b>Recorded interpretation:</b> " + escape(c["interpretation"]), "Small"),
    ]
    if c["structural"]:
        intervals = c["structural_metadata"].get("source_intervals", [])
        dates = sorted(
            set(
                x.get("end_datetime", "unknown")[:10]
                for x in intervals
                if x.get("end_datetime")
            )
        )
        story.append(
            P(
                "<b>Evergreen caveat:</b> right panel is older first-return height occupancy, not a current species map. Lidar end dates: "
                + ", ".join(dates)
                + ". Shadowed growth form and temporal stability require review.",
                "Small",
            )
        )
    else:
        rules = []
        spec = c["policy"]
        for key, meaning in [
            ("dark_unknown_max_ceiling", "all channels below"),
            ("dark_unknown_ceiling", "any channel below"),
            ("bright_unknown_floor", "all channels above"),
        ]:
            if key in spec:
                rules.append(f"{meaning} {spec[key]} -> unknown")
        story.append(
            P(
                "Image-specific RGB exclusions: "
                + escape("; ".join(rules) or "manual geometry/unknown polygons")
                + ". These flag ambiguity; they do not identify PFTs.",
                "Small",
            )
        )
    b = c["examples"][1]
    row = next(x for x in ledger if x["review_id"] == b["review_id"])
    story.append(
        P(
            f"Example B ({b['review_id']}): nominal {100 * b['nominal']:.3f}%; source area {100 * b['support']:.1f}%; lowest tested cover after3 m shifts {float(row['shift3_min_fraction']):.1%}, after5 m shifts {float(row['shift5_min_fraction']):.1%}. Dotted orange square is B's worst tested5 m-per-axis shift; not a measured registration error.",
            "Small",
        )
    )
    story.append(
        P(
            "Review: [ ] Confirm  [ ] Revise label  [ ] Exclude  [ ] Defer. Check identity, shadow, boundaries and dates; no decision is prefilled.",
            "Small",
        )
    )
    return story


def build_atlas(m, ledger):
    path = OUT / "landsat_pure_pixel_complete_atlas.pdf"
    story = []
    story += [
        P("Complete Landsat pixel atlas", "T"),
        P(
            "All1,241 retained HLS L30 reference cells, in61 provisional patches. Each patch has one evidence plate and one complete cell ledger."
        ),
        H("What is and is not established"),
        P(
            "The cells pass the recorded nominal95% mapped-cover or older structural-proxy screen and selected HLS data-quality/date checks. The proposed labels originated in a Codex aerial-interpretation pass using the researcher-defined PFT categories. No cell has an independent second-interpreter or field-purity verification recorded. This atlas makes those proposed labels inspectable; it does not certify them."
        ),
        H("How to use the atlas"),
        P(
            "Find a patch in the two-page index. On its plate, every retained30 m cell is numbered. The next page lists each unique review ID, projected centre, fraction estimates, HLS row/column and a blank decision field. Use the same review ID in team_pixel_review.csv to record a decision and notes."
        ),
        H("Visual key"),
        table(
            [
                ["Mark", "Meaning"],
                [
                    "White cell outlines",
                    "Retained30 m HLS footprints; numbers match the ledger.",
                ],
                [
                    "Dashed cyan square",
                    "120 m bounding source-area diagnostic for example B.",
                ],
                [
                    "Teal / tan / grey",
                    "Photo: target / known other / unknown. Lidar: >5 m / <=5 m / missing.",
                ],
                [
                    "A / B / R zooms",
                    "Interior retained / weakest nominal retained / closest rejected nominal-cover example.",
                ],
                [
                    "Dotted orange in B",
                    "Worst of nine tested5 m footprint shifts; sensitivity only.",
                ],
            ],
            [135, 405],
        ),
        H("Start with the readable guide"),
        P(
            "The companion team review guide defines each class, explains search and QA decisions, compares easy and difficult geometry and shows four contexts that did not contribute cells. Read that guide before treating any percentage as evidence of true ecological purity."
        ),
        P(
            "Source aerials are cached, dated NAIP RGB views; original image content is not recoloured. Classification/height panels are derived evidence layers. All cells use the HLS grid, not the old native Collection2 Landsat grid.",
            "Small",
        ),
        PageBreak(),
    ]
    story += [
        P("Rules and interpretation limits", "T"),
        table(
            [
                ["Term", "Operational meaning"],
                [
                    "Nominal cell",
                    "30 x30 m HLS footprint; >=95% mapped target area or qualifying older tall-height occupancy.",
                ],
                [
                    "Source support",
                    "Unweighted area within a120 x120 m bounding4x4 source-pixel neighbourhood. Not a PSF fraction, weighted purity estimate or probability.",
                ],
                [
                    "Strict support flag",
                    "Both nominal and120 m thresholds pass; only362 of1,241 current cells. This is a sensitivity subset, not independently validated truth.",
                ],
                [
                    "3 m /5 m minima",
                    "New review diagnostics: minimum nominal fraction over nine Cartesian shifts (-d,0,+d) in each axis; diagonals reach4.2/7.1 m. These do not change membership.",
                ],
                [
                    "Current PFT label",
                    "Single-interpreter proposed growth form. A target-coloured mask can be geometrically consistent even if the label is wrong.",
                ],
                [
                    "Pixel independence",
                    "Nearby cells in one patch are not independent field replicates. The current dataset has61 patches, not1,241 independent sites.",
                ],
            ],
            [135, 405],
        ),
        H("HLS observation gates"),
        P(
            "Selected observations require correct grid geometry, seven finite bands, centre Fmask lower-six flags clear, no fill and no high aerosol, plus a clear5x5 surrounding neighbourhood. Aerial and HLS dates are from the same year, differ by at most45 days, and satisfy the fixed seasonal window within21 days of the reference date."
        ),
        P(
            "Climatological aerosol estimates can be allowed; a good observation need not have Fmask=0. Fmask does not expose the original Collection2 saturation QA bit, so no direct HLS saturation-bit pass is claimed."
        ),
        H("Evergreen structural caveat"),
        P(
            "The no-fill1 m lidar grid is older than the aerial/HLS observation. A height bin above5 m supports historical tall structure, not current evergreen identity or current canopy purity. Missing bins are unknown and are not filled. Current photo shadows and growth-form ambiguity remain visible review issues."
        ),
        H("Coordinate and ID key"),
        P(
            "Each ledger states its UTM EPSG. Easting/northing are cell centres in metres. HLS row/column refer to the named granule. Review IDs Pxx-Cyy are unique within this snapshot; original candidate_id, source granule, dates, all source flags and hashes are retained in the accompanying CSV and manifest."
        ),
        PageBreak(),
    ]
    for start, end in [(0, 31), (31, 61)]:
        rows = [["Patch / proposed PFT", "Cells", "Plate", "Ledger"]]
        for c in m["contexts"][start:end]:
            rows.append(
                [
                    c["id"] + " " + c["target"] + " | " + c["region"].replace("_", " "),
                    c["count"],
                    5 + 2 * (c["number"] - 1),
                    6 + 2 * (c["number"] - 1),
                ]
            )
        story += [
            P("Patch index " + ("1 of2" if start == 0 else "2 of2"), "T"),
            P(
                "Pages are PDF page numbers. Use the searchable Pxx-Cyy ID to locate any individual cell.",
                "Small",
            ),
            table(rows, [375, 45, 60, 60], ledger=True),
            PageBreak(),
        ]
    for c in m["contexts"]:
        story += context_page(c, "Complete evidence plate", ledger) + [PageBreak()]
        q = [x for x in ledger if x["context_patch_id"] == c["context_patch_id"]]
        rows = [
            [
                "Review ID",
                "Easting",
                "Northing",
                "30 m %",
                "120 m %",
                "3 m min %",
                "5 m min %",
                "Strict",
                "HLS row/col",
                "Decision",
            ]
        ]
        for r in q:
            rows.append(
                [
                    r["review_id"],
                    f"{float(r['easting']):.0f}",
                    f"{float(r['northing']):.0f}",
                    f"{100 * float(r['nominal_target_fraction']):.3f}",
                    f"{100 * float(r['source_kernel_target_fraction']):.2f}",
                    f"{100 * float(r['shift3_min_fraction']):.2f}",
                    f"{100 * float(r['shift5_min_fraction']):.2f}",
                    "yes" if bool_value(r["strict_support_95pct"]) else "no",
                    f"{r['hls_row']}/{r['hls_col']}",
                    "",
                ]
            )
        story += [
            P(c["id"] + " | Individual-cell ledger", "T"),
            P(
                escape(c["context_patch_id"])
                + "<br/>Proposed PFT: "
                + escape(c["target"])
                + f". UTM EPSG:{q[0]['landsat_epsg']}. All decisions blank; {len(q)} retained cells.",
                "Small",
            ),
            table(rows, [55, 59, 59, 55, 55, 43, 43, 36, 68, 67], ledger=True),
            Spacer(1, 7),
            P(
                "Strict = nominal and120 m mapped/proxy area screens both pass. Shift minima are extra diagnostics, not measured registration errors or confidence bounds. The fixed original acceptance flags are not changed.",
                "Small",
            ),
            P(
                "Aerial ID: "
                + escape(q[0]["aerial_id"])
                + "<br/>Selected HLS: "
                + escape(", ".join(c["hls_items"])),
                "Small",
            ),
            P(
                "Record Confirm / Revise / Exclude / Defer and reviewer notes in team_pixel_review.csv, or annotate this page. Retained does not mean independently validated.",
                "Small",
            ),
            PageBreak(),
        ]
    story.pop()  # no blank final page
    SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=35,
        title="Complete HLS L30 provisional reference pixel atlas",
    ).build(
        story,
        onFirstPage=footer("Complete pixel atlas"),
        onLaterPages=footer("Complete pixel atlas"),
    )
    reader = PdfReader(path)
    assert len(reader.pages) == 126, f"Atlas page mapping changed: {len(reader.pages)}"
    text = "\n".join(p.extract_text() for p in reader.pages)
    for row in ledger:
        assert row["review_id"] in text, row["review_id"]
    return path


def build_guide(m, summary, ledger):
    path = OUT / "landsat_pure_pixel_team_review_guide.pdf"
    pages = []
    visual = SOURCE / "summary"
    counts = {
        c: sum(x["count"] for x in m["contexts"] if x["target"] == c)
        for c in [
            "Deciduous",
            "Evergreen",
            "Herbaceous",
            "Woody shrub",
            "Non-vegetated & dead",
        ]
    }
    # 1. Purpose and current snapshot.
    pages.append(
        [
            P("Landsat reference pixels:<br/>team validation guide", "T"),
            P(
                "A visual, evidence-first review of the current HLS L30 NBAR search. Prepared19 November2026, before further dataset expansion."
            ),
            image(visual / "geography.jpg", maxheight=235),
            H("What the team is being asked to validate"),
            P(
                "For each proposed30 m pixel, does the dated aerial image support the proposed plant functional type (PFT), does the mapped or structural evidence justify the retained area fraction, and are the surrounding footprint and acquisition dates defensible? The initial labels and masks were proposed in a Codex aerial-interpretation pass using the researcher-defined categories; team validation is pending. Record disagreement and uncertainty rather than treating a high numerical score as truth."
            ),
            table(
                [
                    ["Current snapshot", "Count"],
                    ["Distinct HLS L30 cells / spatial patches", "1,241 /61"],
                    ["Cells also meeting120 m area screen", "362"],
                    [
                        "Independent second-interpreter or field-purity confirmations recorded",
                        "0",
                    ],
                ],
                [390, 134],
            ),
            H("How to review efficiently"),
            P(
                "Read pages2-8, inspect the ten representative cases on pages9-18, then review all61 patches in the companion atlas. The atlas includes every retained pixel and its own searchable record. Four non-retained contexts are shown on page19. Nothing in this pack changes a label or adds a cell."
            ),
        ]
    )
    # 2. Human definitions, not a classifier manual.
    rows = [
        ["PFT", "What would support it in an aerial", "What could fool us"],
        [
            "Deciduous",
            "Trees expected to lose foliage seasonally. In this cohort, broadleaf crown form and autumn colour support the proposal.",
            "Mixed conifers, senescent herbs, shadow; autumn colour is supporting evidence, not species proof.",
        ],
        [
            "Evergreen",
            "Trees expected to retain foliage across seasons. Current candidates use conifer-like crowns plus historical tall-height occupancy.",
            "Broadleaf trees, recent disturbance, dark gaps; >5 m does not identify evergreen trees.",
        ],
        [
            "Herbaceous",
            "Continuous low non-woody meadow/grass growth form; some managed grass is allowed by the existing definition.",
            "Low shrubs, wet ground, senescent vegetation, small woody clumps.",
        ],
        [
            "Woody shrub",
            "Low woody growth form, often multi-stemmed. Current candidates use dense chaparral-form crown texture.",
            "Short trees, grass/shrub mosaics and bare interspaces; no independent current height validation.",
        ],
        [
            "Non-vegetated & dead",
            "Exposed rock, talus or bare/dead cover under the study category. Current examples are largely rock/talus.",
            "Lichen, dry grass, snow, deep crevices. Rock examples do not validate every dead-cover type.",
        ],
    ]
    pages.append(
        [
            P("Definitions the team should share", "T"),
            table(rows, [92, 219, 213]),
            H("Target, other and unknown are different"),
            P(
                "<b>Target:</b> area interpreted as the proposed class, or qualifying height occupancy for the structural proxy. <b>Other:</b> explicitly mapped non-target cover. <b>Unknown:</b> unresolved shadow/brightness, unreviewed area or missing structural bins. Unknown is never counted as target."
            ),
            H("What95% means"),
            P(
                "For a900 square-metre cell, the nominal threshold allows up to45 square metres outside the mapped/proxy target. It is a study screening choice, not a NASA purity standard, not a95% probability that the label is correct, and not a95% confidence interval."
            ),
            P(
                "These are working visual cues, not a new botanical crosswalk. Evergreen broadleaf plants exist; height alone does not distinguish tree and shrub. A clean mask can carry a wrong PFT label. Confirm ecological identity and footprint calculation separately. Current proposals and this non-blinded review are not independent ground truth.",
                "Small",
            ),
        ]
    )
    # 3. Search pipeline.
    pages.append(
        [
            P("From a map proposal to a reviewable cell", "T"),
            image(visual / "workflow.jpg", maxheight=350),
            H("Where the class label came from"),
            P(
                "Land-cover and GAP layers locate candidate patches. Dated aerial images are then interpreted for growth form. Projected target/other/unknown polygons, image-specific ambiguity exclusions, or older height grids define the area evidence. Landsat spectra and classification accuracy were not used to choose the review examples or to certify PFT identity."
            ),
            P(
                "The frozen photo policy uses manually selected patch boundaries, explicit exclusions and image-specific dark/bright thresholds to mark ambiguity. Those RGB cutoffs are not calibrated PFT classifiers and should not be transferred to other images as universal rules."
            ),
            P(
                "The complete atlas repeats the original recorded interpretation for every patch. Treat that text as a proposed explanation to check against the image, not as an independent observation."
            ),
        ]
    )
    # 4. Geography and cohort composition.
    rows = [["PFT", "Retained cells", "Patches"]]
    for category, count in counts.items():
        rows.append(
            [category, count, sum(c["target"] == category for c in m["contexts"])]
        )
    pages.append(
        [
            P("Where the search currently has evidence", "T"),
            image(visual / "geography.jpg", maxheight=250),
            table(rows, [300, 112, 112]),
            H("Why geography belongs in a purity review"),
            P(
                "Deciduous, evergreen and woody-shrub references are each concentrated in one region in this cohort. Herbaceous and non-vegetated references span more regions. Regional colour/phenology differences can mimic PFT differences; high classification accuracy cannot independently validate these labels. Selected HLS years are 2023, 2024. Additional dates from the same place would not create new independent spatial patches."
            ),
            P(
                "Nearby cells in a patch share landscape context.61 patches are the current spatial grouping units, not1,241 independent ecological replicates. The team should question both individual cells and whole-patch assumptions."
            ),
        ]
    )
    # 5. Footprint concepts.
    pages.append(
        [
            P("Three different spatial footprints", "T"),
            image(visual / "footprints.jpg", maxheight=390),
            table(
                [
                    ["Footprint", "What it answers"],
                    [
                        "30 m nominal HLS cell",
                        "Does the proposed cell itself meet the mapped/proxy95% threshold?",
                    ],
                    [
                        "120 m source-area diagnostic",
                        "How much of a conservative4x4 source-pixel bounding area is mapped/proxy target?",
                    ],
                    [
                        "150 m QA neighbourhood",
                        "Are the surrounding5x5 HLS cells clear of lower-six Fmask flags and fill?",
                    ],
                ],
                [180, 344],
            ),
            P(
                "HLS resampling means a30 m output is not a hard-edged optical measurement of only900 square metres. The120 m diagnostic is an unweighted bounding-area check, not the true point-spread function, signed cubic-convolution contribution or a purity confidence bound. Low support can reflect unreviewed space, not known contamination.",
                "Small",
            ),
        ]
    )
    # 6. QA/time with real rejected records.
    qrows = [["Recorded example", "Observed values", "Why not retained on that date"]]
    for q in m["qa_examples"]:
        qrows.append(
            [
                q["candidate_id"],
                f"{q['acquisition_datetime'][:10]}; gap {q['aerial_gap_days']}d; Fmask {q['fmask']}",
                "Photo/date rule failed"
                if q["reason"] == "photo_date_match"
                else "Centre quality failed"
                if q["reason"] == "core_qa_clear"
                else "Surrounding quality failed",
            ]
        )
    pages.append(
        [
            P("Cover checks and data-quality checks", "T"),
            H("A convincing aerial is not sufficient"),
            table(
                [
                    ["Gate", "Current contract"],
                    [
                        "Product and grid",
                        "HLS L30 v2 NBAR; exact HLS grid and seven finite reflectance bands. Native Collection2 cells are not substituted.",
                    ],
                    [
                        "Centre Fmask",
                        "Reject fill255 and lower-six flags: cirrus, cloud, adjacency, shadow, snow and water. Reject high aerosol.",
                    ],
                    [
                        "Surroundings",
                        "All5x5 surrounding HLS cells must have lower-six flags clear and no fill.",
                    ],
                    [
                        "Date match",
                        "Same aerial/HLS year; absolute date gap <=45 days. HLS also lies within21 days of the fixed seasonal reference.",
                    ],
                    [
                        "Aerosol and saturation",
                        "Climatological aerosol estimates may be allowed. Original Collection2 saturation QA is not exposed in Fmask; no direct saturation-bit pass is claimed.",
                    ],
                ],
                [120, 404],
            ),
            H("Real rejected alternative observations"),
            table(qrows, [218, 150, 156]),
            P(
                "A candidate cell can be retained from one overpass and rejected from another. These rows are examples of recorded gate failures; more than one gate can fail in the same row. Fmask192 means high aerosol;66 includes a cloud flag. The complete alternative-date audit accompanies the reviewer CSV.",
                "Small",
            ),
            P(
                "The45-day limit does not make all phenological changes negligible. Review senescence, snow, disturbance and date mismatch directly. Older lidar dates are a separate issue and do not satisfy the same-year photo/HLS condition."
            ),
        ]
    )
    # 7. New perturbations, clearly supplemental.
    q = summary["shift_counts"]
    pages.append(
        [
            P("Edges and registration sensitivity", "T"),
            image(visual / "sensitivity.jpg", maxheight=265),
            H("What was calculated for this review"),
            P(
                "For each retained cell, we moved its30 m footprint by every combination of -3,0,+3 m in east/north, then repeated at -5,0,+5 m per axis. Diagonals reach4.2 and7.1 m respectively. The ledger records the lowest target/proxy fraction across each nine-position set. No label or membership flag was changed."
            ),
            table(
                [
                    ["Diagnostic", "Cells still at or above95%"],
                    ["Original nominal screen", q["nominal"]],
                    ["All nine tested3 m shifts", q["shift3"]],
                    ["All nine tested5 m shifts", q["shift5"]],
                    ["Conservative120 m area screen", q["support120"]],
                ],
                [360, 164],
            ),
            P(
                "These are finite stress tests, not measured geolocation errors, worst-case continuous bounds or confidence intervals. A shifted failure is a review priority, not automatic proof that a pixel is mixed. A pass does not prove its PFT identity."
            ),
            P(
                "B zooms show the worst tested5 m-per-axis shift as a dotted orange footprint. Grey beyond the aerial view is unreviewed space, not an inferred land-cover class."
            ),
        ]
    )
    # 8. Navigation and representative selection.
    rows = [["Guide page", "Atlas patch", "Example type", "Proposed PFT"]]
    for i, entry in enumerate(m["guide_examples"], 9):
        c = next(c for c in m["contexts"] if c["id"] == entry["context"])
        rows.append([i, c["id"], entry["role"], c["target"]])
    pages.append(
        [
            P("How to read the evidence plates", "T"),
            P(
                "Start with the aerial panel before accepting the interpretation layer. White outlines are retained HLS cells, numbered to the next atlas-page ledger. A/B/R are selected using geometry and source support only, never the HLS spectra or test performance."
            ),
            table(
                [
                    ["Example", "Selection rule and caution"],
                    [
                        "A: interior retained",
                        "Largest source-area support, then nominal fraction. Geometry-easy does not mean ecologically certain.",
                    ],
                    [
                        "B: edge retained",
                        "Smallest retained nominal fraction (then source support); may still pass by only a narrow margin.",
                    ],
                    [
                        "R: rejected",
                        "Closest below-threshold nominal-cover candidate in the same view. Not retained for this proposed PFT; no alternative PFT is assigned.",
                    ],
                ],
                [140, 384],
            ),
            H("Ten representative contexts"),
            table(rows, [65, 75, 210, 174]),
            P(
                "The companion atlas contains all61 contexts. Every retained cell is present, not just these representative picks. For a one-cell patch, A and B necessarily repeat the same cell. Percentages describe the stored evidence, not reviewer confidence.",
                "Small",
            ),
        ]
    )
    # 9-18. Ten visual case pages.
    for entry in m["guide_examples"]:
        c = next(c for c in m["contexts"] if c["id"] == entry["context"])
        pages.append(context_page(c, entry["role"], ledger))
    # 19. Non-retained examples.
    pages.append(
        [
            P("Examples that did not enter the cohort", "T"),
            image(visual / "nonretained_contexts.jpg", maxheight=460),
            P(
                f"The merged cover-measurement tables contain {summary['nonretained_context_count']} reviewed contexts with no cell in the current1,241-cell cohort. These four were selected from their recorded cover/selection status; they are not newly classified by this report."
            ),
            P(
                "No cell reaches95%: the recorded area screen fails. For power-front_range-non-vegetated-005, ten nominal-pass cells generated90 cell-date QA records and zero eligible observations. Date/grid checks passed, but every centre failed quality; flags include cloud/adjacency/shadow, high aerosol and fill. This is a concrete rejection despite99.68% best mapped cover. Do not infer an alternative PFT from that rejection.",
                "Small",
            ),
        ]
    )
    # 20. Protocol and reviewer decision sheet.
    pages.append(
        [
            P("A practical team review protocol", "T"),
            H("1. Judge identity before trusting the mask"),
            P(
                "Look for growth form, crown texture, bare holes, roads, water, mixed vegetation and shadow. If possible, ask a reviewer to describe an image-only view before seeing the proposed PFT. This pack shows the proposal and is not a blinded validation test."
            ),
            H("2. Check the exact footprint"),
            P(
                "Find the numbered30 m outline and its ledger row. Ask whether mapped target really is the proposed PFT, whether allowed non-target area is acceptable, and whether the120 m surroundings or shifted footprints expose unreviewed or mixed edges."
            ),
            H("3. Check time and evidence age"),
            P(
                "Compare aerial and HLS dates and the separate historical lidar interval. Disturbance, growth, seasonal change and shadow can break an apparently plausible cross-date interpretation."
            ),
            H("4. Record one explicit decision"),
            table(
                [
                    ["Decision", "Use when"],
                    [
                        "Confirm proposal",
                        "Evidence is sufficient for the proposed use; document remaining limitations. This is review agreement, not automatic field truth.",
                    ],
                    [
                        "Revise label",
                        "Another PFT is better supported; state the proposed replacement and the visual evidence.",
                    ],
                    [
                        "Exclude",
                        "Mixture, ambiguity, poor support, registration/date concerns or an unsuitable reference makes inclusion indefensible.",
                    ],
                    [
                        "Defer",
                        "Evidence is insufficient; request field review, newer structure, another date or independent interpretation.",
                    ],
                ],
                [142, 382],
            ),
            H("5. Preserve the audit trail"),
            P(
                "Use team_pixel_review.csv. Required fields are review_id, reviewer, team_decision, revised_pft where relevant, confidence, issue_tags and review_notes. Do not edit the original dataset or replace fractions with subjective scores. Resolve disagreements before a new cohort version is created."
            ),
            P(
                "Suggested issue tags: mixed_growth_form; shadow; canopy_gap; low_source_support; registration; old_structure; date_change; rock_lichen; insufficient_evidence.",
                "Small",
            ),
        ]
    )
    # 21. Known limitations and what would establish confidence.
    pages.append(
        [
            P("What should keep us cautious", "T"),
            table(
                [
                    ["Concern", "What is established", "What the team still needs"],
                    [
                        "Label identity",
                        "One frozen interpretation and its visual rationale are retained.",
                        "Independent assessment of actual PFT, especially shrub/short-tree and mixed-canopy cases.",
                    ],
                    [
                        "Area calculation",
                        "All1,241 stored nominal and source-area fractions were reproduced from saved geometries or structural grids.",
                        "Whether those geometries/proxies correctly represent current ecological cover.",
                    ],
                    [
                        "Evergreen structure",
                        "No-fill historical1 m height bins, source intervals and >5 m occupancy.",
                        "Current evergreen identity, disturbance/growth stability and shadowed canopy composition.",
                    ],
                    [
                        "Registration",
                        "Exact HLS cell geometry, small-shift sensitivity and source-support diagnostic.",
                        "Independent evidence that aerial, structure and HLS are aligned adequately on the ground.",
                    ],
                    [
                        "Population coverage",
                        "61 spatial contexts; dated aerial/HLS evidence and seven-band QA.",
                        "Broader region-matched reference replication and coverage of each PFT across ecological settings.",
                    ],
                    [
                        "Statistics",
                        "The report does not use separability or recognition scores to certify pixels.",
                        "Validation decisions that remain independent of a desired model result.",
                    ],
                ],
                [95, 202, 227],
            ),
            H("What would strengthen a confirmation"),
            P(
                "Agreement from a second interpreter using clear review criteria; current, appropriately resolved structural or field information where growth form is ambiguous; consistent evidence across dates; and a documented georegistration check against stable features. No single numerical purity threshold replaces those observations."
            ),
            P(
                "The extra3/5 m and120 m diagnostics identify where to look first. They are not reasons to silently remove cells, tune thresholds until a test passes, or relabel unclear pixels as target."
            ),
        ]
    )
    # 22. Provenance and use.
    pages.append(
        [
            P("Source records, files and next steps", "T"),
            H("Delivered materials"),
            table(
                [
                    ["File", "Purpose"],
                    [
                        "landsat_pure_pixel_team_review_guide.pdf",
                        "Readable definitions, search logic, ten contrasting cases and four non-retained contexts.",
                    ],
                    [
                        "landsat_pure_pixel_complete_atlas.pdf",
                        "61 evidence plates plus61 individual-cell ledgers; every one of1,241 cells.",
                    ],
                    [
                        "team_pixel_review.csv",
                        "Complete metadata/fractions, shift diagnostics, stable IDs and blank team review fields.",
                    ],
                    [
                        "review_manifest.json; geometry_verification.csv",
                        "Source/plate hashes, original rationale, deterministic example picks and fraction recalculation checks.",
                    ],
                    [
                        "candidate_date_qa_review.csv",
                        "Recorded alternative HLS observation QA for current candidate cells.",
                    ],
                ],
                [260, 264],
            ),
            H("Source imagery and product identity"),
            P(
                "Current cohort (unchanged):<br/>provenance/landsat-pure-pixels/2026-11-18/expanded-search/round-2/<br/>power-directed-expansion/review-batch-2/hls-combined/<br/>hls_l30_nominal_95pct_observations.csv",
                "ReviewCode",
            ),
            P(
                "Aerial panels use the retained dated NAIP RGB contexts. Native source ground resolution is recorded in metadata; the display is resampled to0.4 m and does not create finer source information. Source image IDs and hashes are retained. USDA NAIP imagery and USGS3DEP lidar are supporting observations, not labels generated by an independent ground survey."
            ),
            P(
                'The spectral dataset is Landsat-derived HLS L30 v2 NBAR, with seven bands. Product DOI: <link href="https://doi.org/10.5067/HLS/HLSL30.002" color="#237d83">10.5067/HLS/HLSL30.002</link>. The atlas lists HLS granule IDs, aerial dates and each projected centre.'
            ),
            H("Reproduce without changing the dataset"),
            P(
                ".venv/bin/python examples/publication_figures/prepare_landsat_pixel_review.py<br/>.venv/bin/python examples/publication_figures/prepare_landsat_review_summary.py<br/>python examples/publication_figures/build_landsat_pixel_review_pdfs.py",
                "ReviewCode",
            ),
            P(
                "The first two commands use the project geospatial environment; the PDF builder needs ReportLab, Pillow and pypdf. Inputs must be present in the existing archive. No network retrieval or new label assignment is required."
            ),
            P(
                "Review evidence folder:<br/>provenance/landsat-pure-pixels/2026-11-19/team-validation/",
                "ReviewCode",
            ),
            H("Decision before further expansion"),
            P(
                "Return the annotated CSV or PDF notes. Preserve ambiguous cases as deferred, resolve label disagreements and freeze a reviewed cohort version before treating these proposed references as validated pure pixels. Further search and statistical updates can then use those explicit team decisions."
            ),
        ]
    )
    assert len(pages) == 22
    story = []
    for i, page in enumerate(pages):
        story += page + ([PageBreak()] if i < len(pages) - 1 else [])
    SimpleDocTemplate(
        str(path),
        pagesize=letter,
        leftMargin=44,
        rightMargin=44,
        topMargin=48,
        bottomMargin=36,
        title="Landsat pure-pixel team validation guide",
    ).build(
        story,
        onFirstPage=footer("Team validation guide"),
        onLaterPages=footer("Team validation guide"),
    )
    count = len(PdfReader(path).pages)
    assert count == 22, f"Guide pagination changed: {count}"
    return path


def run():
    OUT.mkdir(exist_ok=True, parents=True)
    m = json.loads((SOURCE / "review_manifest.json").read_text())
    summary = json.loads((SOURCE / "visual_summary.json").read_text())
    for path, digest in m["sources"].items():
        if sha(Path(path)) != digest:
            raise ValueError("Changed source: " + path)
    for c in m["contexts"]:
        assert sha(ROOT / c["plate"]) == c["plate_sha256"]
    assert sha(SOURCE / "review_manifest.json") == summary["sources_digest"]
    for case in summary["nonretained_contexts"]:
        if "source_image_path" in case:
            assert sha(Path(case["source_image_path"])) == case["image_sha256"]
            assert (
                sha(Path(case["source_metadata_path"]))
                == case["source_metadata_sha256"]
            )
    for name, digest in summary["visuals"].items():
        assert sha(SOURCE / "summary" / name) == digest
    with (SOURCE / "team_pixel_review.csv").open() as stream:
        ledger = list(csv.DictReader(stream))
    assert len(ledger) == 1241 and len({r["review_id"] for r in ledger}) == 1241
    outputs = [build_guide(m, summary, ledger), build_atlas(m, ledger)]
    provenance = dict(
        date="2026-11-19",
        source_manifest_sha256=sha(SOURCE / "review_manifest.json"),
        visual_summary_sha256=sha(SOURCE / "visual_summary.json"),
        review_csv_sha256=sha(SOURCE / "team_pixel_review.csv"),
        builder_sha256=sha(Path(__file__)),
        labels_changed=False,
        outputs={
            str(p.relative_to(ROOT)): dict(sha256=sha(p), pages=len(PdfReader(p).pages))
            for p in outputs
        },
    )
    (SOURCE / "pdf_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    for p in outputs:
        print(p, flush=True)


if __name__ == "__main__":
    run()
