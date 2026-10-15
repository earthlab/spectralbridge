"""Readable report atlas and conceptual validation diagram; no new inference."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
plt.rcParams.update(
    {
        "font.size": 10,
        "svg.fonttype": "none",
        "svg.hashsalt": "spectralbridge-analytics-20261014",
        "pdf.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
manifest = json.loads((BASE / "manifests/figures.json").read_text())


def save(name, fig, caption, source):
    fig.tight_layout()
    for ext in ["png", "pdf", "svg"]:
        fig.savefig(
            BASE / "figures" / f"{name}.{ext}",
            dpi=350,
            bbox_inches="tight",
            metadata=(
                {"Date": None}
                if ext == "svg"
                else {"CreationDate": None, "ModDate": None}
                if ext == "pdf"
                else {"Software": "SpectralBridge"}
            ),
        )
    plt.close(fig)
    item = dict(
        name=name,
        caption=caption,
        source=source,
        files=[f"figures/{name}.{ext}" for ext in ["png", "pdf", "svg"]],
    )
    manifest["figures"] = [x for x in manifest["figures"] if x["name"] != name] + [item]


atlas = pd.read_csv(
    REPO / "provenance/publication-figures/2026-10-14/atlas_summary.csv"
)
sizes = pd.read_csv(
    REPO / "provenance/mesma-readiness/2026-10-14/tables/class_sample_sizes.csv"
)
pd.DataFrame(atlas).to_csv(BASE / "tables/atlas_curves.csv", index=False)
fig, axes = plt.subplots(
    1, 2, figsize=(11.5, 4.1), gridspec_kw={"width_ratios": [1.35, 1]}
)
for (label, g), color in zip(
    atlas.groupby("cover_category"),
    ["#4477aa", "#228833", "#ccbb44", "#aa3377", "#66ccee"],
):
    g = g.sort_values("wavelength_nm")
    for j, ix in enumerate(
        np.split(np.arange(len(g)), np.where(np.diff(g.wavelength_nm) > 20)[0] + 1)
    ):
        seg = g.iloc[ix]
        if not len(seg):
            continue
        axes[0].plot(
            seg.wavelength_nm,
            seg["median"],
            label=label if j == 0 else None,
            color=color,
        )
axes[0].set(
    xlabel="Wavelength (nm)",
    ylabel="Median corrected value (stored units)",
    title="Researcher-category median curves",
)
axes[0].legend(fontsize=8)
subset = sizes[sizes.scheme.eq("inferred_pft")].copy()
subset["cohort"] = subset.site + " " + subset.year.astype(str)
heat = subset.pivot(index="label", columns="cohort", values="identities").fillna(0)
image = axes[1].imshow(heat, aspect="auto", cmap="Blues")
axes[1].set(
    xticks=range(len(heat.columns)),
    xticklabels=heat.columns,
    yticks=range(len(heat)),
    yticklabels=heat.index,
    title="Unique identities per observed cohort",
)
axes[1].tick_params(axis="x", rotation=25)
for i in range(len(heat)):
    for j in range(len(heat.columns)):
        axes[1].text(
            j,
            i,
            str(int(heat.iloc[i, j])),
            ha="center",
            va="center",
            color="white" if heat.iloc[i, j] > heat.max().max() * 0.5 else "black",
        )
save(
    "01_readable_atlas",
    fig,
    "Left: canonical corrected median spectra in unresolved stored units, with atmospheric gaps disconnected. Right: PFT identities within each cohort; repeated identities across years are not new independent plants.",
    "atlas_curves.csv; canonical class_sample_sizes.csv",
)
fig, ax = plt.subplots(figsize=(11.5, 3.4))
ax.set(xlim=(0, 12), ylim=(0, 4))
ax.axis("off")
boxes = [
    (
        0.2,
        2.1,
        3.3,
        1.25,
        "PROPER TRAINING\nScaling · features · models\nInner folds group whole plants",
    ),
    (
        4.3,
        2.1,
        3.3,
        1.25,
        "CALIBRATION\nKnown training plants only\nTemperature · raw-score sets",
    ),
    (
        8.4,
        2.1,
        3.3,
        1.25,
        "OUTER TEST\nNew identities / domain\nEvaluate once; do not tune",
    ),
]
for x, y, w, h, label in boxes:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=.15",
            facecolor="#e6eff1",
            edgecolor="#376576",
        )
    )
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=11)
for x1, x2 in [(3.65, 4.1), (7.75, 8.2)]:
    ax.annotate(
        "", xy=(x2, 2.7), xytext=(x1, 2.7), arrowprops={"arrowstyle": "->", "lw": 1.5}
    )
ax.text(
    6,
    1.2,
    "One GlobalID and all its years/flights stay in one role.\nNo test-guided feature selection, endmembers, tuning or thresholds.",
    ha="center",
    va="center",
    fontsize=12,
    color="#173e52",
)
save(
    "00_validation_diagram",
    fig,
    "Conceptual design, not an empirical result. Calibration never trains the base model; final targets never select parameters. Grouped holdouts do not remove all ecological confounding.",
    "DESIGN.md",
)
(BASE / "manifests/figures.json").write_text(json.dumps(manifest, indent=2) + "\n")
