"""Human-review summary visuals; diagnostic geometry, not new acceptance rules."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle

from prepare_landsat_pixel_review import (
    REPORT,
    COHORT,
    CACHE_DIRS,
    CATEGORIES,
    source_kernel,
    sha,
)

COLORS = ["#c78d33", "#2b806b", "#7c9c36", "#8b668c", "#85817a"]


def run():
    m = json.loads((REPORT / "review_manifest.json").read_text())
    d = pd.read_csv(REPORT / "team_pixel_review.csv")
    visuals = REPORT / "summary"
    visuals.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    # Workflow explicitly separates proposed labels from independent validation.
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 5)
    ax.axis("off")
    steps = [
        (
            "1  FIND",
            "Land-cover/GAP maps propose locations.\nThey do not establish PFT identity.",
        ),
        ("2  LOOK", "Dated aerial imagery:\nlook for crowns, texture and gaps."),
        (
            "3  INTERPRET",
            "Assign a provisional growth form.\nMap target / other / unknown.",
        ),
        (
            "4  MEASURE",
            "Overlay exact HLS 30 m cells.\nRetain mapped/proxy fraction >=95%.",
        ),
        (
            "5  CHECK DATA",
            "Same-year dates + seasonal window,\nFmask centre/context, seven bands.",
        ),
        (
            "6  CHALLENGE",
            "120 m support and 3/5 m shifts\nexpose edges; they are not truth.",
        ),
        (
            "7  INDEPENDENT REVIEW",
            "A team member confirms, revises,\nexcludes or defers each cell.",
        ),
        (
            "8  FREEZE A VERSION",
            "Only reviewed decisions create\na new validated dataset version.",
        ),
    ]
    for i, (title, text) in enumerate(steps):
        col = i % 2
        row = i // 2
        x = 0.15 + col * 4.5
        y = 3.8 - row * 1.2
        ax.add_patch(
            FancyBboxPatch(
                (x, y), 4.15, 1.03, boxstyle="round,pad=.05", fc="#edf3f4", ec="#b8cbd0"
            )
        )
        ax.text(
            x + 0.12, y + 0.74, title, fontweight="bold", color="#263e56", fontsize=10
        )
        ax.text(x + 0.12, y + 0.20, text, fontsize=9)
    fig.tight_layout()
    fig.savefig(visuals / "workflow.jpg", dpi=170)
    plt.close(fig)
    # Regional concentration is visible without implying a geographic basemap.
    fig, (a, b) = plt.subplots(
        1, 2, figsize=(10, 4.8), gridspec_kw={"width_ratios": [1, 1.25]}
    )
    for category, color in zip(CATEGORIES, COLORS, strict=True):
        x = [c["meta"]["longitude"] for c in m["contexts"] if c["target"] == category]
        y = [c["meta"]["latitude"] for c in m["contexts"] if c["target"] == category]
        a.scatter(x, y, c=color, s=35, label=category, alpha=0.75)
    a.set_xlabel("Longitude")
    a.set_ylabel("Latitude")
    a.set_title("61 context centres (no basemap)")
    a.grid(alpha=0.2)
    a.legend(loc="lower left", fontsize=7, frameon=False)
    matrix = (
        d.groupby(["researcher_category", "region"])
        .size()
        .unstack(fill_value=0)
        .reindex(CATEGORIES)
    )
    b.imshow(matrix.to_numpy(), cmap="Blues", aspect="auto")
    b.set_xticks(
        range(len(matrix.columns)),
        [x.replace("_", "\n") for x in matrix.columns],
        fontsize=8,
    )
    b.set_yticks(range(5), CATEGORIES, fontsize=8)
    for y in range(5):
        for x in range(len(matrix.columns)):
            b.text(
                x,
                y,
                str(matrix.iloc[y, x]),
                ha="center",
                va="center",
                color="white" if matrix.iloc[y, x] > 190 else "#263e56",
            )
    b.set_title("Retained cells by PFT and region")
    fig.tight_layout()
    fig.savefig(visuals / "geography.jpg", dpi=170)
    plt.close(fig)
    # Different footprint concepts on one actual cached aerial.
    c = next(c for c in m["contexts"] if c["id"] == m["guide_examples"][1]["context"])
    meta = c["meta"]
    key = c["context_patch_id"]
    cache = next(p for p in CACHE_DIRS if (p / (key + ".npy")).exists())
    image = np.moveaxis(np.load(cache / (key + ".npy")), 0, -1)
    row = c["examples"][1]
    x = row["easting"] - meta["easting"]
    y = row["northing"] - meta["northing"]
    kernel = source_kernel(row["easting"], row["northing"], meta)
    w, s, e, n = kernel.bounds
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(image, extent=[-120, 120, -120, 120])
    ax.add_patch(
        Rectangle(
            (x - 75, y - 75),
            150,
            150,
            fill=False,
            ec="#e561a1",
            lw=2,
            label="150 m: 5x5 HLS QA neighbourhood",
        )
    )
    ax.add_patch(
        Rectangle(
            (w - meta["easting"], s - meta["northing"]),
            e - w,
            n - s,
            fill=False,
            ec="#00ddff",
            ls="--",
            lw=2,
            label="120 m: source-support diagnostic",
        )
    )
    ax.add_patch(
        Rectangle(
            (x - 15, y - 15),
            30,
            30,
            fill=False,
            ec="white",
            lw=2,
            label="30 m: nominal HLS cell (900 square metres)",
        )
    )
    ax.set_xlim(-120, 120)
    ax.set_ylim(-120, 120)
    ax.set_xlabel("Metres east of context centre")
    ax.set_ylabel("Metres north")
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.12), fontsize=8, frameon=False
    )
    fig.tight_layout()
    fig.savefig(visuals / "footprints.jpg", dpi=170, bbox_inches="tight")
    plt.close(fig)
    # Registration perturbations are supplemental and never relabel cells.
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.5))
    counts = [
        len(d),
        int((d.shift3_min_fraction >= 0.95 - 1e-12).sum()),
        int((d.shift5_min_fraction >= 0.95 - 1e-12).sum()),
        int(d.strict_support_95pct.sum()),
    ]
    a.barh(range(4), counts, color=["#263e56", "#5f9697", "#7c9c9a", "#c18d4f"])
    a.set_yticks(
        range(4),
        [
            "Nominal 30 m screen",
            "+/-3 m per axis (9 positions)",
            "+/-5 m per axis (9 positions)",
            "120 m area >=95%",
        ],
    )
    a.invert_yaxis()
    a.set_xlim(0, 1450)
    for i, value in enumerate(counts):
        a.text(value + 15, i, str(value), va="center")
    a.set_xlabel("Cells meeting the diagnostic threshold")
    a.set_title("Screen robustness, not new acceptance")
    for category, color in zip(CATEGORIES, COLORS, strict=True):
        q = d[d.researcher_category == category]
        b.scatter(
            q.nominal_target_fraction * 100,
            q.source_kernel_target_fraction * 100,
            s=9,
            color=color,
            alpha=0.4,
        )
    b.axhline(95, color="#263e56", ls="--", lw=1)
    b.set_xlabel("Nominal target/proxy area (%)")
    b.set_ylabel("120 m target/proxy area (%)")
    b.set_title("A clean 30 m cell can have mixed/unknown support")
    fig.tight_layout()
    fig.savefig(visuals / "sensitivity.jpg", dpi=170)
    plt.close(fig)
    # Include contexts that never contributed any current retained cell.
    cover = pd.concat(
        [pd.read_csv(p) for p in COHORT.glob("*-all_cover_measurements.csv")],
        ignore_index=True,
    )
    qa_all = pd.concat(
        [pd.read_csv(p) for p in COHORT.glob("*-hls_qa_audit.csv")], ignore_index=True
    )
    missing = cover[
        ~cover.context_patch_id.isin([c["context_patch_id"] for c in m["contexts"]])
    ]
    options = []
    for key, g in missing.groupby("context_patch_id"):
        best = g.sort_values("nominal_target_fraction", ascending=False).iloc[0]
        options.append(
            dict(
                key=key,
                target=best.researcher_category,
                best=best,
                max_fraction=float(best.nominal_target_fraction),
                passes=int(g.nominal_95pct.sum()),
            )
        )
    chosen = []
    for nominal in [False, True]:
        seen = set()
        for o in sorted(
            [x for x in options if bool(x["passes"]) == nominal],
            key=lambda x: -x["max_fraction"],
        ):
            if o["target"] in seen:
                continue
            chosen.append(o)
            seen.add(o["target"])
            if len(seen) == 2:
                break
    if len(chosen) < 4:
        chosen.extend([o for o in options if o not in chosen][: 4 - len(chosen)])
    fig, axes = plt.subplots(2, 2, figsize=(8, 8))
    rejected = []
    for ax, o in zip(axes.ravel(), chosen[:4], strict=True):
        cache = next(p for p in CACHE_DIRS if (p / (o["key"] + ".npy")).exists())
        meta = json.loads((cache / (o["key"] + ".json")).read_text())
        image = np.load(cache / (o["key"] + ".npy"))
        r = o["best"]
        assert sha(cache / (o["key"] + ".npy")) == r.image_sha256
        ax.imshow(np.moveaxis(image, 0, -1), extent=[-120, 120, -120, 120])
        ax.add_patch(
            Rectangle(
                (r.easting - meta["easting"] - 15, r.northing - meta["northing"] - 15),
                30,
                30,
                fill=False,
                ec="#ee5577",
                lw=2,
            )
        )
        ax.set_xticks([])
        ax.set_yticks([])
        nominal_ids = cover[
            (cover.context_patch_id == o["key"]) & cover.nominal_95pct
        ].candidate_id
        audits = qa_all[qa_all.candidate_id.isin(nominal_ids)]
        qa_count = len(audits)
        eligible_count = int(audits.eligible_observation.sum())
        reason = (
            "No cell reached nominal 95%"
            if not o["passes"]
            else f"Nominal candidates: {eligible_count}/{qa_count} QA observations eligible"
        )
        ax.set_title(o["key"] + "\n" + o["target"], fontsize=7.4)
        ax.set_xlabel(
            f"Best recorded fraction {o['max_fraction']:.2%}\n{reason}", fontsize=7
        )
        rejected.append(
            dict(
                context_patch_id=o["key"],
                target=o["target"],
                best_fraction=o["max_fraction"],
                nominal_candidates=o["passes"],
                reason=reason,
                image_sha256=sha(cache / (o["key"] + ".npy")),
                metadata=meta,
                qa_observations=qa_count,
                qa_eligible=eligible_count,
                qa_fmask_counts={
                    str(k): int(v) for k, v in audits.fmask.value_counts().items()
                },
                source_image_path=str(cache / (o["key"] + ".npy")),
                source_metadata_path=str(cache / (o["key"] + ".json")),
                source_metadata_sha256=sha(cache / (o["key"] + ".json")),
            )
        )
    fig.tight_layout(h_pad=2)
    fig.savefig(visuals / "nonretained_contexts.jpg", dpi=170)
    plt.close(fig)
    summary = dict(
        shift_counts=dict(
            nominal=counts[0], shift3=counts[1], shift5=counts[2], support120=counts[3]
        ),
        nonretained_contexts=rejected,
        nonretained_context_count=missing.context_patch_id.nunique(),
        sources_digest=sha(REPORT / "review_manifest.json"),
        code_sha256=sha(Path(__file__)),
        visuals={p.name: sha(p) for p in visuals.glob("*.jpg")},
    )
    (REPORT / "visual_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n"
    )
    print(summary["shift_counts"], flush=True)


if __name__ == "__main__":
    run()
