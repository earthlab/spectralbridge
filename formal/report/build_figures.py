"""Deterministic explanatory figures; no fitted scientific models or source spectra."""

from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BLUE = "#6495ED"
DARK = "#25303D"
WARM = "#B67F63"
GREEN = "#527D69"
GRAY = "#84909D"
LIGHT = "#EDF2FA"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 12,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "svg.hashsalt": "formal-explanation-v1",
        "savefig.facecolor": "white",
    }
)
manifest = {}


def save(fig, num, title, kind, source):
    name = f"figure_{num:02d}"
    fig.savefig(
        OUT / "figures" / f"{name}.pdf",
        metadata={"CreationDate": None, "ModDate": None},
    )
    fig.savefig(OUT / "figures" / f"{name}.svg", metadata={"Date": None})
    fig.savefig(OUT / "figures" / f"{name}.png", dpi=300)
    manifest[name] = {
        "title": title,
        "kind": kind,
        "source": source,
        "files": {
            ext: hashlib.sha256(
                (OUT / "figures" / f"{name}.{ext}").read_bytes()
            ).hexdigest()
            for ext in ["pdf", "svg", "png"]
        },
    }
    plt.close(fig)


def blank(w=7, h=4.8):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text, color=BLUE, fs=11):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=.008,rounding_size=.015",
            facecolor=color,
            alpha=0.13,
            edgecolor=color,
            lw=1.3,
        )
    )
    ax.text(
        x + w / 2, y + h / 2, text, ha="center", va="center", color=DARK, fontsize=fs
    )


def arrow(ax, a, b, color=GRAY):
    ax.annotate(
        "",
        xy=b,
        xytext=a,
        arrowprops={
            "arrowstyle": "->",
            "lw": 1.7,
            "color": color,
            "shrinkA": 4,
            "shrinkB": 4,
        },
    )


def note(ax, x, y, s, color=DARK, fs=11):
    ax.text(x, y, s, ha="center", va="center", color=color, fontsize=fs)


def triangle(ax):
    v = np.array([[0, 0], [1, 0], [0.5, np.sqrt(3) / 2]])
    ax.add_patch(Polygon(v, facecolor=LIGHT, edgecolor=BLUE, lw=2))
    for p, s in zip(v, ["Pure A", "Pure B", "Pure C"]):
        ax.text(
            *p,
            s,
            ha="center",
            va="top" if p[1] == 0 else "bottom",
            fontsize=12,
            color=DARK,
        )
    ax.set(xlim=(-0.25, 1.25), ylim=(-0.18, 1.1), aspect="equal")
    ax.axis("off")
    return v


def main():
    # 1 Actual architecture: separate observation paths, model/data boundaries.
    fig, ax = blank(7, 5.0)
    for x, t in [
        (0.02, "NEON/AOP\npackaged reflectance"),
        (0.35, "Native drone\nMicaSense bands"),
        (0.68, "Actual Landsat\nindependent comparison"),
    ]:
        box(ax, x, 0.85, 0.28, 0.12, t, WARM)
    box(
        ax,
        0.02,
        0.66,
        0.61,
        0.12,
        "Topography → BRDF → optional offset\nScene fits, geometry, masks; optional NDVI bins",
        WARM,
    )
    arrow(ax, (0.16, 0.85), (0.16, 0.79))
    arrow(ax, (0.49, 0.85), (0.49, 0.79))
    box(ax, 0.02, 0.47, 0.28, 0.12, "Synthetic OLI /\nMicaSense response", BLUE)
    box(ax, 0.35, 0.47, 0.28, 0.12, "Drone → Landsat-like\nFixed affine map", GREEN)
    arrow(ax, (0.16, 0.66), (0.16, 0.60))
    arrow(ax, (0.49, 0.66), (0.49, 0.60))
    box(
        ax,
        0.68,
        0.47,
        0.28,
        0.25,
        "QA + DN scaling\nFootprint means\nEmpirical calibration",
        WARM,
    )
    arrow(ax, (0.82, 0.85), (0.82, 0.73))
    box(
        ax,
        0.02,
        0.29,
        0.61,
        0.11,
        "Pixel extraction → hierarchical medians\nGap-aware common representation / library",
        WARM,
    )
    arrow(ax, (0.16, 0.47), (0.16, 0.41))
    arrow(ax, (0.49, 0.47), (0.49, 0.41))
    box(ax, 0.02, 0.09, 0.28, 0.11, "FCLS / MESMA\nReconstruct spectra", GREEN)
    box(ax, 0.35, 0.09, 0.28, 0.11, "Ridge + projection\nPredict fractions", GREEN)
    arrow(ax, (0.19, 0.29), (0.16, 0.21))
    arrow(ax, (0.45, 0.29), (0.49, 0.21))
    note(
        ax,
        0.81,
        0.24,
        "Representative\nPython paths checked\n(not every execution)",
        GRAY,
    )
    for x, yy, t, c in [
        (0.1, 0.015, "Proved algebra", BLUE),
        (0.55, 0.015, "Conditional model", GREEN),
        (0.1, 0.055, "Numerical checks", GRAY),
        (0.55, 0.055, "Empirical / fitted", WARM),
    ]:
        ax.text(x, yy, t, fontsize=9, color=c, ha="left")
    save(
        fig,
        1,
        "The actual pipeline has several kinds of guarantees",
        "implementation diagram",
        "formal/TRACEABILITY.md; named production functions",
    )
    # 2 Spectrum, mixture, simplex.
    w = np.linspace(400, 1000, 121)
    a = 0.15 + 0.4 / (1 + np.exp(-(w - 710) / 18))
    b = 0.2 + 0.2 / (1 + np.exp(-(w - 690) / 25)) + 0.035 * np.sin(w / 40)
    y = 0.6 * a + 0.4 * b
    pd.DataFrame({"wavelength_nm": w, "A": a, "B": b, "mixture_60_40": y}).to_csv(
        OUT / "tables/toy_spectra.csv", index=False
    )
    fig, axs = plt.subplots(
        1, 2, figsize=(7, 3.7), gridspec_kw={"width_ratios": [1.6, 1]}
    )
    ax = axs[0]
    for vals, t, c in [(a, "A", BLUE), (b, "B", WARM), (y, "60% A + 40% B", DARK)]:
        ax.plot(w, vals, color=c, lw=2, label=t)
    ax.set(xlabel="Wavelength (nm)", ylabel="Hypothetical spectral value")
    ax.legend(fontsize=10, frameon=False)
    triangle(axs[1])
    pt = 0.6 * np.array([0, 0]) + 0.4 * np.array([1, 0])
    axs[1].scatter(*pt, c=DARK, s=50)
    axs[1].text(0.48, 0.17, "60/40", ha="center", fontsize=11)
    fig.tight_layout()
    save(
        fig,
        2,
        "A curve, a vector and valid fractions",
        "hypothetical illustration",
        "Core.mixture; pair_simplex; mixture_convexHull; explicit toy formula",
    )
    # 3 Same endpoint, actual computed linear toy.
    fig, ax = blank(7, 3.3)
    box(ax, 0.02, 0.72, 0.27, 0.16, "A = [1, 0]\nB = [0, 1]", BLUE)
    box(ax, 0.02, 0.12, 0.27, 0.16, "Mix first\n[0.6, 0.4]", BLUE)
    arrow(ax, (0.15, 0.72), (0.15, 0.29))
    note(ax, 0.29, 0.5, "60/40")
    box(ax, 0.64, 0.72, 0.31, 0.16, "Transform first\nT(A) = 1; T(B) = 1", GREEN)
    arrow(ax, (0.30, 0.8), (0.63, 0.8))
    note(ax, 0.48, 0.9, "T(x) = x₁ + x₂")
    box(ax, 0.64, 0.12, 0.31, 0.16, "SAME RESULT\nT(y) = 1", DARK)
    arrow(ax, (0.30, 0.20), (0.63, 0.20))
    arrow(ax, (0.8, 0.72), (0.8, 0.29))
    note(ax, 0.8, 0.49, "Mix with the\nsame 60/40")
    note(
        ax,
        0.49,
        0.04,
        "Exact formal sensor example; not an OLI response curve",
        GRAY,
        10,
    )
    save(
        fig,
        3,
        "Mix then transform = transform then mix",
        "proved toy example",
        "Core.linear_mixture; Counterexamples.sumSensor",
    )
    # 4 Exact collapse example.
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.6))
    axs[0].plot([1, 2], [1, 0], "o-", color=BLUE, lw=2, label="A = [1,0]")
    axs[0].plot([1, 2], [0, 1], "s--", color=WARM, lw=2, label="B = [0,1]")
    axs[0].set(
        xticks=[1, 2],
        xlabel="Toy spectral coordinate",
        ylabel="Spectral value",
        ylim=(-0.12, 1.2),
    )
    axs[0].legend(frameon=False, fontsize=10)
    axs[1].scatter([1], [1], s=170, facecolors="none", edgecolors=BLUE, lw=3)
    axs[1].scatter([1], [1], s=45, color=WARM, marker="s")
    axs[1].set(
        xlim=(0.5, 1.5),
        ylim=(-0.12, 1.2),
        xticks=[1],
        xticklabels=["One summed band"],
        ylabel="T(x)",
    )
    axs[1].text(
        1,
        0.5,
        "T(A) = T(B) = 1\nEvery A/B fraction\nhas this same value",
        ha="center",
        fontsize=12,
    )
    fig.tight_layout()
    save(
        fig,
        4,
        "A valid reduction erases the distinction",
        "exact proved counterexample",
        "Counterexamples.hyperspectral_identifiable; convolution_destroys_identifiability",
    )
    # 5 Ambiguous endmembers equal same observed spectrum.
    fig, ax = blank(7, 3.3)
    box(ax, 0.02, 0.61, 0.36, 0.22, "Composition 1\n100% C\nC = [0.5, 0.5]", BLUE)
    box(
        ax,
        0.02,
        0.13,
        0.36,
        0.22,
        "Composition 2\n50% A + 50% B\nA = [1,0]; B = [0,1]",
        WARM,
    )
    box(
        ax,
        0.64,
        0.34,
        0.31,
        0.27,
        "SAME SPECTRUM\n[0.5, 0.5]\nDifferent composition",
        DARK,
    )
    arrow(ax, (0.39, 0.71), (0.63, 0.50))
    arrow(ax, (0.39, 0.24), (0.63, 0.44))
    save(
        fig,
        5,
        "Exact reconstruction with two different compositions",
        "exact proved counterexample",
        "Counterexamples.ambiguousE; ambiguous_reconstruction; mesma_ambiguity",
    )
    # 6 FCLS feasible region closest point.
    fig, ax = plt.subplots(figsize=(7, 4))
    v = np.array([[0, 0], [1, 0], [0.2, 0.8]])
    ax.add_patch(Polygon(v, facecolor=LIGHT, edgecolor=BLUE, lw=2))
    obs = np.array([0.9, 0.8])
    p = np.array([0.55, 0.45])  # projection onto x+y=1 edge between (1,0) and(.2,.8)
    ax.scatter(*obs, s=65, color=WARM)
    ax.annotate("Observed y", obs, xytext=(0.93, 0.88), fontsize=12)
    ax.scatter(*p, s=60, color=DARK)
    ax.annotate(
        "Closest allowed mixture",
        p,
        xytext=(0.53, 0.18),
        arrowprops={"arrowstyle": "->", "color": GRAY},
        fontsize=11,
    )
    ax.plot([p[0], obs[0]], [p[1], obs[1]], "--", color=WARM)
    for pt, t in zip(v, ["A", "B", "C"]):
        ax.annotate(
            t, pt, xytext=(5, 5), textcoords="offset points", color=BLUE, fontsize=13
        )
    ax.set(
        xlim=(-0.1, 1.4),
        ylim=(-0.1, 1.1),
        xlabel="Toy spectral coordinate 1",
        ylabel="Toy spectral coordinate 2",
        aspect="equal",
    )
    fig.tight_layout()
    save(
        fig,
        6,
        "FCLS finds the nearest feasible reconstruction",
        "hypothetical geometry",
        "Inference.IsFCLS; fcls_exists; fcls_unique; oracle_unique; explicit triangle projection",
    )
    # 7 tolerance-aware candidate search.
    fig, ax = blank(7, 3.4)
    box(ax, 0.34, 0.39, 0.32, 0.22, "Observed spectrum\n[0.5, 0.5]", DARK)
    for x, y, t, c in [
        (0.02, 0.77, "Singleton C\nResidual = 0", BLUE),
        (0.69, 0.77, "A/B mixture\nResidual = 0", WARM),
        (0.34, 0.05, "Other admitted candidates\nWithin declared tolerance?", GRAY),
    ]:
        box(ax, x, y, 0.29, 0.16, t, c)
        arrow(
            ax,
            (x + 0.145, y if y > 0.5 else y + 0.16),
            (0.5, 0.61 if y > 0.5 else 0.39),
            c,
        )
    save(
        fig,
        7,
        "MESMA selects among admitted candidate mixtures",
        "proved toy plus conceptual tolerance",
        "Inference.tolerant_search_bound; ambiguity_mono; Counterexamples.mesma_ambiguity",
    )
    # 8 distinct learning vs search objectives.
    fig, ax = blank(7, 3.4)
    for x, title, c in [
        (0.02, "MESMA: reconstruction", WARM),
        (0.53, "Ridge: prediction", BLUE),
    ]:
        note(ax, x + 0.22, 0.95, title, c, 13)
    for x, ys, texts, c in [
        (
            0.02,
            [0.71, 0.43, 0.15],
            [
                "New spectrum",
                "Search admitted mixtures",
                "Best spectral reconstruction",
            ],
            WARM,
        ),
        (
            0.53,
            [0.71, 0.43, 0.15],
            [
                "Training spectra + synthetic truth",
                "Learn regularized mapping",
                "New spectrum → expected fractions",
            ],
            BLUE,
        ),
    ]:
        for yy, t in zip(ys, texts):
            box(ax, x, yy, 0.43, 0.15, t, c, 10.5)
        arrow(ax, (x + 0.21, 0.71), (x + 0.21, 0.59))
        arrow(ax, (x + 0.21, 0.43), (x + 0.21, 0.31))
    note(
        ax,
        0.5,
        0.055,
        "One unique fitted prediction can coexist with multiple inverse solutions.",
        DARK,
        11,
    )
    save(
        fig,
        8,
        "Different estimators optimize different targets",
        "conceptual estimator diagram",
        "Ridge.ridge_minimizer_unique; mixtures.fit_models; P129 supervised; Counterexamples.perfect_prediction_not_unique_inversion",
    )
    # 9 Isometric simplex plane with outside sum-one raw point.
    fig, ax = plt.subplots(figsize=(7, 3.3))
    v = triangle(ax)
    raw = np.array([-0.2, 0.8, 0.4])
    proj = np.array([0, 0.7, 0.3])
    truth = np.array([0.2, 0.3, 0.5])
    r = raw @ v
    p = proj @ v
    t = truth @ v
    for point, txt, c in [
        (r, "Raw prediction", WARM),
        (p, "Projected", DARK),
        (t, "Feasible truth", GREEN),
    ]:
        ax.scatter(*point, s=60, color=c)
        ax.annotate(
            txt,
            point,
            xytext=(0, 22 if c == WARM else -25),
            textcoords="offset points",
            fontsize=12,
            ha="center",
            color=c,
        )
    arrow(ax, r, p, WARM)
    ax.plot([r[0], t[0]], [r[1], t[1]], ":", color=WARM)
    ax.plot([p[0], t[0]], [p[1], t[1]], ":", color=GREEN)
    ax.set_xlim(-0.3, 1.55)
    fig.tight_layout()
    save(
        fig,
        9,
        "Projection imposes valid fraction geometry",
        "hypothetical sum-one plane; exact geometry",
        "Projection.simplex_projection_error; projection_idempotent; threshold_projection; Python project_simplex",
    )
    # 10 overall composition vs information synthesis.
    fig, ax = blank(7, 4.3)
    rows = [
        ("Landscape: ideal 60% A / 40% B", "ASSUMED", WARM),
        ("Hyperspectral observation: many coordinates", "OBSERVED", GRAY),
        ("Same fixed linear / affine transformation", "PRESERVED weights", BLUE),
        ("Fewer sensor bands: distinctions may collapse", "LOST dimensions", WARM),
        ("Representative library + inference model", "ASSUMED references", WARM),
        ("MESMA reconstruction / ridge prediction", "ESTIMATED fractions", GREEN),
        ("Independent contemporaneous fractional cover", "FIELD TRUTH needed", WARM),
    ]
    for j, (t, label, c) in enumerate(rows):
        yy = 0.86 - j * 0.125
        box(ax, 0.02, yy, 0.66, 0.085, t, c, 10.5)
        note(ax, 0.84, yy + 0.043, label, c, 10.5)
        if j < len(rows) - 1:
            arrow(ax, (0.35, yy), (0.35, yy - 0.04))
    save(
        fig,
        10,
        "Where proportions survive and interpretation needs evidence",
        "conditional synthesis diagram",
        "Pipeline.full_pipeline_conditional; formal/ASSUMPTIONS.md",
    )
    # 11 assumption ladder.
    fig, ax = blank(7, 4.8)
    levels = [
        ("MATHEMATICS", "Equations proved under stated hypotheses", BLUE),
        (
            "IMPLEMENTATION",
            "Representative examples agree; IEEE not fully certified",
            GRAY,
        ),
        (
            "SENSOR PHYSICS",
            "Calibration, response and spatial support need evidence",
            WARM,
        ),
        (
            "SPECTRAL LIBRARY",
            "References must represent the generating materials",
            WARM,
        ),
        (
            "BIOLOGICAL REPRESENTATION",
            "Recorded categories need the intended ecological meaning",
            WARM,
        ),
        (
            "FIELD ABUNDANCE",
            "Independent contemporaneous fraction truth is required",
            WARM,
        ),
    ]
    for j, (t, desc, c) in enumerate(levels):
        yy = 0.83 - j * 0.15
        box(ax, 0.02, yy, 0.93, 0.11, t + "\n" + desc, c, 11)
        if j < 5:
            arrow(ax, (0.49, yy), (0.49, yy - 0.04))
    save(
        fig,
        11,
        "Each interpretive step needs its own support",
        "assumption diagram",
        "formal/ASSUMPTIONS.md",
    )
    # 12 actual canonical empirical panels.
    prior = ROOT / "provenance/researcher-pft-information/2026-10-15/v1"
    cur = ROOT / "provenance/researcher-evidence/2026-10-16/v1"
    d = pd.read_csv(prior / "tables/complementary_feature_performance.csv")
    full = d[(d.budget.astype(str) == "360") | (d.budget.astype(str) == "OLI")].copy()
    full.to_csv(OUT / "tables/recognition_source.csv", index=False)
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.7))
    for i, kind in enumerate(["plant", "site"]):
        sub = full[full.kind.eq(kind)]
        vals = []
        for budget in ["360", "OLI"]:
            vals.append(sub[sub.budget.astype(str).eq(budget)].balanced_accuracy.mean())
        axs[0].plot(
            [0, 1],
            vals,
            "o-",
            color=[BLUE, WARM][i],
            label=["New polygon", "Held site"][i],
        )
        for j, value in enumerate(vals):
            axs[0].annotate(
                f"{value:.1%}",
                (j, value),
                xytext=(8 if j == 0 else -8, 10 if i == 0 else -18),
                textcoords="offset points",
                ha="left" if j == 0 else "right",
                fontsize=11,
            )
    axs[0].set(
        xticks=[0, 1],
        xticklabels=["Full NEON", "Synthetic OLI"],
        ylim=(0.45, 0.95),
        ylabel="Five-category balanced accuracy",
    )
    axs[0].legend(frameon=False, fontsize=10, loc="lower left")
    ab = pd.read_csv(cur / "tables/abundance_domain_summary.csv")
    ab = ab[
        ab.representation.eq("NEON")
        & ab.kind.isin(["plant", "site", "year"])
        & ab.method.isin(["Ridge", "MESMA", "Training prior"])
    ]
    ab.to_csv(OUT / "tables/abundance_source.csv", index=False)
    for method, c in [("Ridge", BLUE), ("MESMA", WARM), ("Training prior", GRAY)]:
        q = (
            ab[ab.method.eq(method)]
            .set_index("kind")
            .reindex(["plant", "site", "year"])
        )
        axs[1].plot(
            range(3),
            q["mean"],
            "o-",
            color=c,
            label=method + "120"
            if method == "Ridge"
            else method + "15"
            if method == "MESMA"
            else "No-spectrum prior",
        )
    axs[1].set(
        xticks=range(3),
        xticklabels=["New\nparents", "Held\nsite", "Global\nyear"],
        ylabel="Synthetic fraction RMSE",
        ylim=(0.18, 0.41),
    )
    axs[1].legend(frameon=False, fontsize=9, loc="lower left", bbox_to_anchor=(0, 1.01))
    fig.tight_layout()
    save(
        fig,
        12,
        "Canonical recognition and synthetic fraction evidence",
        "empirical data; mean saved outer scores",
        "P129 tables/complementary_feature_performance.csv; P130 tables/abundance_domain_summary.csv",
    )
    # 13 actual deterministic overlapping chunks and inferred axis.
    fig, axs = plt.subplots(1, 2, figsize=(7, 3.8))
    ax = axs[0]
    ax.axis("off")
    ax.text(0.02, 0.9, "Band-first cube: (7, 2, 3)", fontsize=13, color=DARK)
    ax.text(
        0.02,
        0.65,
        "7 bands\n2 image rows\n3 image columns",
        fontsize=12,
        linespacing=1.7,
    )
    ax.text(
        0.02,
        0.22,
        "Smallest axis is rows.\nShape inference chooses it\nas the band axis.",
        fontsize=12,
        color=WARM,
    )
    ax = axs[1]
    arr = np.array([[1, 1, 1], [2, 2, 2], [2, 2, 2]])
    ax.pcolormesh(
        np.arange(4),
        np.arange(4),
        arr,
        cmap=matplotlib.colors.ListedColormap([LIGHT, BLUE]),
        edgecolors="white",
        linewidth=3,
    )
    ax.invert_yaxis()
    ax.set(aspect="equal", xticks=[], yticks=[])
    for r in range(3):
        for col in range(3):
            ax.text(
                col + 0.5,
                r + 0.5,
                str(arr[r, col]),
                ha="center",
                va="center",
                fontsize=19,
                color=DARK,
            )
    ax.text(
        1.5,
        3.4,
        "Numbers = emission count\n15 rows; 9 unique pixels",
        ha="center",
        fontsize=12,
    )
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    save(
        fig,
        13,
        "Two reproduced implementation discrepancies",
        "actual deterministic audit fixtures",
        "formal/tests/test_conformance.py: test_audit_axis_counterexample; test_audit_polygon_chunk_overlap",
    )
    # 14 tests vs theorem domain.
    fig, ax = blank(7, 2.9)
    box(ax, 0.34, 0.12, 0.62, 0.75, "Inputs satisfying the\ntheorem hypotheses", BLUE)
    ax.scatter([0.43, 0.62, 0.81], [0.42, 0.64, 0.36], s=70, c=WARM)
    note(ax, 0.16, 0.64, "Lean proof", BLUE, 13)
    arrow(ax, (0.02, 0.56), (0.32, 0.56), BLUE)
    note(ax, 0.16, 0.25, "Python tests", WARM, 13)
    arrow(ax, (0.15, 0.34), (0.42, 0.42), WARM)
    note(ax, 0.65, 0.18, "Dots = finite checked examples", GRAY, 11)
    save(
        fig,
        14,
        "Examples and universal conditional statements",
        "conceptual domain diagram",
        "formal/PROOF_STATUS.md; checks/axioms.log; conformance tests",
    )
    # 15 epsilon normalization exact-real attenuation ratio.
    s = np.logspace(-16, -6, 300)
    ratio = s / (s + 1e-12)
    pd.DataFrame({"response_sum": s, "constant_output_ratio": ratio}).to_csv(
        OUT / "tables/epsilon_curve.csv", index=False
    )
    fig, ax = plt.subplots(figsize=(7, 3.1))
    ax.semilogx(s, ratio, color=BLUE, lw=2.5)
    ax.axhline(1, color=GRAY, ls=":")
    ax.scatter([1e-14], [1e-14 / (1e-14 + 1e-12)], color=WARM, s=50)
    ax.annotate(
        "Near-zero support\n≈ 0.0099 of a constant",
        (1e-14, 0.01),
        xytext=(1e-13, 0.32),
        arrowprops={"arrowstyle": "->", "color": WARM},
        fontsize=11,
    )
    ax.set(
        xlabel="Sum of sampled response weights",
        ylabel="Output / constant input",
        ylim=(-0.05, 1.12),
    )
    fig.tight_layout()
    save(
        fig,
        15,
        "The epsilon guard changes constant preservation",
        "exact-real formula and Python toy check",
        "Core.epsilon_constant; resample.py; test_audit_epsilon_degenerate_srf",
    )
    (OUT / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
