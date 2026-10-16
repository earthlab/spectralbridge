"""Six-panel manuscript science figure. No fitting and no source spectra accessed.

Run from the repository: python -m examples.manuscript_synthesis.build_figure
Use --layout balanced --draft to compare an equal-width arrangement.
"""

import argparse
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, FixedLocator, ScalarFormatter
from .palette import PALETTE as P, CATEGORIES as CATS
from .figure_data import BASE, REPO, prepare, load_bundle, sha

OUT = REPO / "output/figures/manuscript_synthesis"
WIDTH = 190 / 25.4
HEIGHT = 10.35


def segments(waves):
    return np.split(np.arange(len(waves)), np.flatnonzero(np.diff(waves) > 10) + 1)


def style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.labelsize": 8.2,
            "axes.titlesize": 9,
            "xtick.labelsize": 7.8,
            "ytick.labelsize": 7.8,
            "legend.fontsize": 7.6,
            "axes.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "text.color": P["text"],
            "axes.labelcolor": P["text"],
            "xtick.color": P["text"],
            "ytick.color": P["text"],
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "manuscript-synthesis-v1",
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "lines.solid_capstyle": "round",
        }
    )


def axes(fig, rect):
    ax = fig.add_axes(
        [rect[0] / WIDTH, rect[1] / HEIGHT, rect[2] / WIDTH, rect[3] / HEIGHT]
    )
    ax.tick_params(length=2.3, width=0.6, pad=2)
    return ax


def title(fig, x, y, letter, text):
    fig.text(x / WIDTH, y / HEIGHT, letter, fontsize=14, fontweight="bold", va="top")
    fig.text(
        (x + 0.25) / WIDTH,
        (y - 0.005) / HEIGHT,
        text,
        fontsize=9.5,
        fontweight="bold",
        va="top",
    )


def spectral_axis(ax, regions=False, bands=None):
    for lo, hi in [(1340, 1450), (1790, 2000)]:
        ax.axvspan(lo, hi, color=P["gap"], lw=0, zorder=-5)
    ax.set_xlim(380, 2510)
    ax.set_xticks([500, 1000, 1500, 2000, 2500])
    ax.set_xlabel("Wavelength (nm)", labelpad=3)
    if bands is not None:
        for b in bands.itertuples():
            ax.plot(
                [b.center_nm - b.FWHM_nm / 2, b.center_nm + b.FWHM_nm / 2],
                [1.025] * 2,
                transform=ax.get_xaxis_transform(),
                color=P["muted"],
                lw=1.4,
                clip_on=False,
            )
        if not regions:
            ax.text(
                0.995,
                1.045,
                "Synthetic OLI",
                transform=ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=7.4,
                color=P["muted"],
            )
    if regions:
        for label, lo, hi in [
            ("VIS", 385, 700),
            ("red edge", 700, 750),
            ("NIR", 750, 1340),
            ("SWIR1", 1450, 1790),
            ("SWIR2", 2000, 2495),
        ]:
            xx = (lo + hi) / 2
            yy = 1.035 if label != "red edge" else 1.105
            ax.text(
                xx,
                yy,
                label,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=7.4,
                color=P["muted"],
            )
            if label == "red edge":
                ax.plot(
                    [xx, xx],
                    [1.025, 1.09],
                    transform=ax.get_xaxis_transform(),
                    color=P["light"],
                    lw=0.5,
                    clip_on=False,
                )


def panel_a(fig, left, right, top, bottom, data):
    title(fig, left, top, "A", "Category spectra show clear structure")
    ax = axes(
        fig, (left + 0.40, bottom + 0.33, right - left - 0.47, top - bottom - 0.90)
    )
    s = data["A_category_spectra"]
    w = np.sort(s.wavelength_nm.unique())
    for cat in CATS:
        g = s[s.cover_category.eq(cat)].set_index("wavelength_nm").loc[w]
        for ix in segments(w):
            ax.fill_between(
                w[ix],
                g.q25.to_numpy()[ix],
                g.q75.to_numpy()[ix],
                color=P["categories"][cat],
                alpha=0.10,
                lw=0,
            )
            ax.plot(
                w[ix], g["median"].to_numpy()[ix], color=P["categories"][cat], lw=1.25
            )
    ax.set_ylim(0, float(s.q75.max()) * 1.10)
    ax.set_ylabel("Corrected spectral value\n(stored units)", labelpad=4)
    formatter = ScalarFormatter(useMathText=True)
    formatter.set_powerlimits((0, 0))
    ax.yaxis.set_major_formatter(formatter)
    ax.set_yticks([0, 2000, 4000])
    ax.yaxis.get_offset_text().set_fontsize(7.3)
    ax.yaxis.get_offset_text().set_x(-0.10)
    spectral_axis(ax, True, data["OLI_band_positions"])
    handles = [
        Line2D([], [], color=P["categories"][cat], lw=1.5, label=cat) for cat in CATS
    ]
    ax.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(1.02, 1.005),
        frameon=False,
        labelspacing=0.25,
        handlelength=1.3,
        handletextpad=0.5,
        fontsize=7.4,
        borderaxespad=0.2,
    )


def panel_b(fig, left, right, top, bottom, data):
    title(fig, left, top, "B", "All pairs separate across spectral regions")
    ax = axes(
        fig, (left + 1.40, bottom + 0.53, right - left - 1.46, top - bottom - 0.94)
    )
    b = data["B_wavelength_effects"]
    pairs = list(b.pair.unique())
    w = np.sort(b.wavelength_nm.unique())
    z = (
        b.pivot(index="pair", columns="wavelength_nm", values="effect")
        .loc[pairs, w]
        .to_numpy()
    )
    evidence = (
        b.pivot(index="pair", columns="wavelength_nm", values="consistent_evidence")
        .loc[pairs, w]
        .to_numpy(bool)
    )
    cmap = LinearSegmentedColormap.from_list(
        "effect", [P["effect_negative"], P["effect_zero"], P["effect_positive"]]
    )
    norm = TwoSlopeNorm(vmin=-2, vcenter=0, vmax=2)
    for ix in segments(w):
        edges = np.r_[w[ix] - 2.5, w[ix[-1]] + 2.5]
        ax.pcolormesh(
            edges,
            np.arange(11) - 0.5,
            z[:, ix],
            cmap=cmap,
            norm=norm,
            alpha=np.where(evidence[:, ix], 1, 0.24),
            shading="flat",
            rasterized=False,
            linewidth=0,
            edgecolors="none",
        )
    ax.set_facecolor(P["gap"])
    ax.set_ylim(9.5, -0.5)
    # Full category words on two lines keep the ten pair labels readable.
    names = [pair.replace("Non-vegetated & dead", "Non-veg./dead") for pair in pairs]
    ax.set_yticks(range(10), names, fontsize=7.4)
    ax.tick_params(axis="y", length=0, pad=3)
    ax.set_xlim(380, 2510)
    ax.set_xticks([500, 1000, 1500, 2000, 2500])
    ax.set_xlabel("Wavelength (nm)", labelpad=3)
    for bnd in data["OLI_band_positions"].itertuples():
        ax.plot(
            [bnd.center_nm - bnd.FWHM_nm / 2, bnd.center_nm + bnd.FWHM_nm / 2],
            [-0.80] * 2,
            color=P["muted"],
            lw=1.4,
            clip_on=False,
        )
    ax.text(
        0.995,
        1.09,
        "Synthetic OLI",
        transform=ax.transAxes,
        ha="right",
        fontsize=7.4,
        color=P["muted"],
    )
    ax.text(
        0, 1.09, "Faint: inconsistent support", transform=ax.transAxes, fontsize=7.4
    )
    cax = axes(fig, (left + 1.43, bottom + 0.09, right - left - 1.70, 0.07))
    cb = fig.colorbar(
        matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="horizontal",
        ticks=[-2, 0, 2],
        extend="both",
    )
    cb.solids.set_rasterized(False)
    cb.ax.tick_params(labelsize=7.4, length=2, pad=1)
    fig.text(
        (left + 0.03) / WIDTH,
        (bottom + 0.03) / HEIGHT,
        "Signed effect",
        fontsize=7.4,
        va="bottom",
    )


def panel_c(fig, left, right, top, bottom, data):
    title(fig, left, top, "C", "More wavelengths improve recognition")
    ax = axes(
        fig, (left + 0.53, bottom + 0.38, right - left - 0.61, top - bottom - 0.72)
    )
    c = data["C_recognition"]
    for method, color in [("Random", P["random"]), ("Selected replay", P["selected"])]:
        for kind in ["plant", "site"]:
            g = c[c.method.eq(method) & c.kind.eq(kind)].sort_values("budget")
            if method == "Selected replay":
                g = pd.concat([g, c[c.method.eq("Full spectrum") & c.kind.eq(kind)]])
            ax.fill_between(
                g.budget, g.observed_min, g.observed_max, color=color, alpha=0.05, lw=0
            )
            ax.plot(
                g.budget,
                g.BA,
                color=color,
                lw=1.45 if method == "Selected replay" else 1.0,
                ls=P["domain_lines"][kind],
                marker=P["domain_markers"][kind],
                ms=3.3,
                markerfacecolor="white" if kind == "plant" else color,
                markeredgewidth=0.8,
            )
    ax.set(
        xscale="log",
        xlim=(0.92, 450),
        ylim=(0.28, 1.01),
        ylabel="Five-class balanced accuracy",
    )
    budgets = [1, 2, 3, 5, 7, 10, 20, 50, 100, 360]
    ax.set_xticks(budgets, [str(x) if x != 360 else "Full" for x in budgets])
    ax.xaxis.set_minor_locator(FixedLocator([]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y * 100:.0f}%"))
    ax.set_xlabel("Number of wavelengths", labelpad=4)
    a = data["annotations"].set_index("annotation").value
    ax.text(
        0.025,
        0.97,
        "At 20: selected / random",
        transform=ax.transAxes,
        fontsize=7.4,
        va="top",
    )
    ax.text(
        0.025,
        0.90,
        f"New: {a['C_plant_Selected replay_20']:.1%} / {a['C_plant_Random_20']:.1%}",
        transform=ax.transAxes,
        fontsize=7.3,
        va="top",
    )
    ax.text(
        0.025,
        0.83,
        f"Site:  {a['C_site_Selected replay_20']:.1%} / {a['C_site_Random_20']:.1%}",
        transform=ax.transAxes,
        fontsize=7.3,
        va="top",
    )
    for kind, offset in [("plant", (-7, 13)), ("site", (-6, -15))]:
        value = a["C_" + kind + "_full"]
        ax.annotate(
            f"Full {value:.1%}",
            xy=(360, value),
            xytext=offset,
            textcoords="offset points",
            ha="right",
            fontsize=7.3,
        )
    # Four entries use a common style key, not four arbitrary hues.
    handles = [
        Line2D([], [], color=P["selected"], lw=1.5, label="Selected"),
        Line2D([], [], color=P["random"], lw=1, label="Random"),
        Line2D(
            [], [], color=P["text"], marker="o", mfc="white", lw=1, label="New polygon"
        ),
        Line2D([], [], color=P["text"], marker="s", lw=1, ls="--", label="Held site"),
    ]
    ax.legend(
        handles=handles,
        loc="lower right",
        fontsize=7.4,
        frameon=False,
        ncol=2,
        columnspacing=0.7,
        handlelength=1.5,
        handletextpad=0.4,
        borderaxespad=0.2,
    )


def panel_d(fig, left, right, top, bottom, data):
    title(fig, left, top, "D", "Category transfer is uneven")
    # Matrix + recall dumbbells share precisely the same category row positions.
    matrix_width = 1.38
    matrix_left = left + 1.00
    y0 = bottom + 0.84
    h = 1.44
    ax = axes(fig, (matrix_left, y0, matrix_width, h))
    g = (
        data["D_confusion"]
        .pivot(index="truth", columns="predicted", values="mean_fold_row_fraction")
        .loc[list(CATS), list(CATS)]
    )
    cmap = LinearSegmentedColormap.from_list(
        "recognition", [P["confusion_low"], P["confusion_high"]]
    )
    ax.pcolormesh(
        np.arange(6) - 0.5,
        np.arange(6) - 0.5,
        g.to_numpy(),
        vmin=0,
        vmax=1,
        cmap=cmap,
        shading="flat",
        edgecolors="none",
        rasterized=False,
    )
    ax.set_xlim(-0.5, 4.5)
    ax.set_ylim(4.5, -0.5)
    rows = [c.replace("Non-vegetated & dead", "Non-vegetated\n& dead") for c in CATS]
    cols = ["Deciduous", "Evergreen", "Herbaceous", "Non-veg. & dead", "Woody shrub"]
    ax.set_yticks(range(5), rows, fontsize=7.4)
    ax.set_xticks(range(5), cols, rotation=65, ha="right", fontsize=7.4)
    ax.tick_params(length=0, pad=3)
    ax.set_title("Held-site prediction (%)", fontsize=7.8, pad=7)
    for i in range(5):
        for j in range(5):
            ax.text(
                j,
                i,
                f"{100 * g.iloc[i, j]:.0f}",
                ha="center",
                va="center",
                fontsize=7.4,
                color="white" if g.iloc[i, j] > 0.6 else P["text"],
            )
    r = axes(
        fig,
        (
            matrix_left + matrix_width + 0.12,
            y0,
            right - (matrix_left + matrix_width) - 0.17,
            h,
        ),
    )
    recall = (
        data["D_recall"]
        .pivot(index="researcher_category", columns="kind", values="recall")
        .loc[list(CATS)]
    )
    for i, c in enumerate(CATS):
        color = P["categories"][c]
        r.plot(
            [recall.loc[c, "plant"], recall.loc[c, "site"]], [i, i], color=color, lw=1.2
        )
        r.scatter(
            recall.loc[c, "plant"],
            i,
            marker="o",
            s=20,
            facecolor="white",
            edgecolor=color,
            lw=1,
        )
        r.scatter(recall.loc[c, "site"], i, marker="s", s=19, color=color)
    r.set(xlim=(0.3, 1.04), ylim=(4.5, -0.5))
    r.set_xticks([0.5, 1], ["50", "100"])
    r.set_yticks([])
    r.set_title("Recall (%)", fontsize=7.8, pad=7)
    r.spines["left"].set_visible(False)
    value = float(recall.loc["Woody shrub", "site"])
    r.annotate(
        f"{value:.1%}",
        xy=(value, 4),
        xytext=(0, 7),
        textcoords="offset points",
        ha="center",
        fontsize=8.0,
        fontweight="bold",
        color=P["categories"]["Woody shrub"],
    )
    fig.text(
        (matrix_left + matrix_width + 0.08) / WIDTH,
        (bottom + 0.20) / HEIGHT,
        "○ New  ■ Site",
        fontsize=7.4,
        ha="left",
    )


def panel_e(fig, left, right, top, bottom, data):
    title(fig, left, top, "E", "Fraction recovery differs by category")
    f = data["E_calibration"]
    pad = 0.39
    gap = 0.18
    w = (right - left - pad - 0.02 - 2 * gap) / 3
    h = 1.00
    yvalues = [bottom + 2.04, bottom + 0.48]
    for i, cat in enumerate(CATS):
        row, col = divmod(i, 3)
        ax = axes(fig, (left + pad + col * (w + gap), yvalues[row], w, h))
        for source, model in [("MESMA", "MESMA15"), ("Ridge", "Ridge120")]:
            g = f[f.method.eq(source) & f.researcher_category.eq(cat)].sort_values(
                "true_fraction"
            )
            ax.plot(
                g.true_fraction,
                g.prediction_mean,
                color=P["models"][model],
                ls=P["model_styles"][model],
                lw=1.25 if model == "Ridge120" else 0.95,
            )
        ax.plot([0, 1], [0, 1], color=P["light"], lw=0.8, ls=":", zorder=-1)
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.set_xticks([0, 0.5, 1], ["0", ".5", "1"])
        ax.set_yticks([0, 0.5, 1], ["0", ".5", "1"] if col == 0 else [""] * 3)
        ax.tick_params(labelsize=7.2, length=2, pad=1.5)
        name = cat.replace("Non-vegetated & dead", "Non-vegetated\n& dead")
        ax.set_title(
            name, color=P["categories"][cat], fontsize=8.1, pad=5, fontweight="bold"
        )
    legend = axes(fig, (left + pad + 2 * (w + gap), yvalues[1], w, h))
    legend.axis("off")
    handles = [
        Line2D([], [], color=P["models"][m], ls=P["model_styles"][m], lw=1.3, label=m)
        for m in ["Ridge120", "MESMA15"]
    ]
    handles += [Line2D([], [], color=P["muted"], ls=":", lw=0.8, label="1:1")]
    legend.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(-0.14, 1.04),
        frameon=False,
        fontsize=7.4,
        handlelength=1.6,
        handletextpad=0.4,
        labelspacing=0.7,
    )
    legend.text(
        -0.05,
        0.19,
        "Held sites\nSynthetic fractions",
        fontsize=7.4,
        va="top",
        transform=legend.transAxes,
    )
    fig.text(
        (left + 0.035) / WIDTH,
        (bottom + 1.95) / HEIGHT,
        "Mean predicted fraction",
        rotation=90,
        fontsize=8.1,
        ha="left",
        va="center",
    )
    fig.text(
        (left + (right - left) / 2) / WIDTH,
        (bottom + 0.07) / HEIGHT,
        "Known synthetic fraction",
        fontsize=8.2,
        ha="center",
    )


def panel_f(fig, left, right, top, bottom, data):
    title(fig, left, top, "F", "Richer libraries help; ambiguity remains")
    x0 = left + 0.73
    ww = right - x0 - 0.10
    ax = axes(fig, (x0, bottom + 2.10, ww, 0.88))
    f = data["F_library_comparison"]
    names = ["Training prior", "MESMA15", "Ridge15", "Ridge120"]
    for i, m in enumerate(names):
        g = f[f.method.eq(m)].set_index("kind")
        color = P["models"][m]
        ax.plot(
            [g.loc["plant", "RMSE"], g.loc["site", "RMSE"]], [i, i], color=color, lw=1
        )
        for kind in ["plant", "site"]:
            ax.plot(
                [g.loc[kind, "min"], g.loc[kind, "max"]],
                [i, i],
                color=color,
                lw=3,
                alpha=0.11,
                solid_capstyle="butt",
            )
            ax.scatter(
                g.loc[kind, "RMSE"],
                i,
                s=21,
                marker=P["domain_markers"][kind],
                facecolor="white" if kind == "plant" else color,
                edgecolor=color,
                lw=0.9,
                zorder=3,
            )
    ax.set_yticks(range(4), ["Prior", "MESMA15", "Ridge15", "Ridge120"], fontsize=7.5)
    ax.set(ylim=(3.5, -0.5), xlim=(0.18, 0.42))
    ax.set_xticks([0.2, 0.3, 0.4])
    ax.set_xlabel("Fraction RMSE", fontsize=7.7, labelpad=2)
    ax.tick_params(axis="y", length=0)
    ax.text(
        0.98,
        1.11,
        "○ New parents  ■ Held sites",
        transform=ax.transAxes,
        ha="right",
        fontsize=7.4,
    )
    a = data["annotations"].set_index("annotation").value
    fig.text(
        (left + 0.07) / WIDTH,
        (bottom + 1.65) / HEIGHT,
        f"Ridge120 vs MESMA15: −{a['F_plant_relative_improvement']:.0%} / −{a['F_site_relative_improvement']:.0%}",
        fontsize=7.6,
        fontweight="bold",
    )
    fig.text(
        (left + 0.07) / WIDTH,
        (bottom + 1.48) / HEIGHT,
        "Same 15 parents: mean advantage lost",
        fontsize=7.5,
    )
    b = axes(fig, (x0, bottom + 0.57, ww, 0.80))
    amb = data["F_ambiguity"]
    for m in ["MESMA15", "Ridge120"]:
        g = (
            amb[amb.method.eq(m)]
            .set_index("ambiguity")
            .loc[["Low", "Moderate", "High"]]
        )
        b.plot(
            range(3),
            g.fraction_RMSE,
            color=P["models"][m],
            ls=P["model_styles"][m],
            lw=1.25,
            marker="o",
            ms=3,
        )
        b.text(
            2.08,
            g.fraction_RMSE.iloc[-1],
            m,
            color=P["models"][m],
            fontsize=7.4,
            va="center",
        )
    b.set(xlim=(-0.1, 3.0), ylim=(0.14, 0.395))
    b.set_xticks(range(3), ["Low", "Moderate", "High"])
    b.tick_params(axis="x", labelsize=7.5)
    b.set_yticks([0.2, 0.3])
    b.set_ylabel("Fraction RMSE", fontsize=7.7, labelpad=3)
    b.set_xlabel("Candidate-library ambiguity", fontsize=7.8, labelpad=3)
    fig.text(
        (left + (right - left) / 2) / WIDTH,
        (bottom + 0.02) / HEIGHT,
        "Lower error ≠ unique mixture",
        ha="center",
        fontsize=8.0,
        fontweight="bold",
    )


def build(layout="flow", draft=False):
    style()
    data = load_bundle()
    fig = plt.figure(figsize=(WIDTH, HEIGHT))
    # All panel letters have identical offsets from their panel bounds.
    rows = [(10.20, 7.30), (6.94, 4.03), (3.67, 0.13)]
    splits = [3.30, 3.71, 3.71] if layout == "flow" else [3.71] * 3
    funcs = [(panel_a, panel_b), (panel_c, panel_d), (panel_e, panel_f)]
    geometry = []
    for k, ((top, bottom), split, (a, b)) in enumerate(zip(rows, splits, funcs)):
        a(fig, 0.10, split - 0.10, top, bottom, data)
        b(fig, split + 0.10, WIDTH - 0.10, top, bottom, data)
        geometry.append(
            dict(
                row=k + 1,
                left_panel_width_in=split - 0.20,
                right_panel_width_in=WIDTH - split - 0.20,
            )
        )
    for y in [7.11, 3.86]:
        fig.add_artist(
            Line2D(
                [0.1 / WIDTH, (WIDTH - 0.1) / WIDTH],
                [y / HEIGHT] * 2,
                transform=fig.transFigure,
                color=P["light"],
                lw=0.5,
            )
        )
    # Final print typography: no base text smaller than 8 pt. Mathematical
    # superscripts retain Matplotlib's normal proportional typesetting.
    for text in fig.findobj(match=matplotlib.text.Text):
        if text.get_fontsize() < 8:
            text.set_fontsize(8)
    dest = BASE / "drafts" / layout if draft else OUT
    dest.mkdir(parents=True, exist_ok=True)
    stem = dest / "figure_main_synthesis"
    for ext in ["pdf", "svg", "png"]:
        metadata = (
            {"CreationDate": None, "ModDate": None}
            if ext == "pdf"
            else {"Date": None}
            if ext == "svg"
            else {"Software": "SpectralBridge"}
        )
        fig.savefig(stem.with_suffix("." + ext), dpi=600, metadata=metadata)
    # Store all text bounds at intended print size, separate from scientific data.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = []
    for text in fig.findobj(match=matplotlib.text.Text):
        if not text.get_visible() or not text.get_text():
            continue
        box = text.get_window_extent(renderer).transformed(
            fig.dpi_scale_trans.inverted()
        )
        bounds.append(
            dict(
                text=text.get_text(),
                fontsize_pt=text.get_fontsize(),
                x0=box.x0,
                y0=box.y0,
                x1=box.x1,
                y1=box.y1,
            )
        )
    plt.close(fig)
    record = {
        "layout": layout,
        "width_mm": 190,
        "height_in": HEIGHT,
        "PNG_dpi": 600,
        "geometry": geometry,
        "text_bounds": bounds,
        "output_sha256": {
            ext: sha(stem.with_suffix("." + ext)) for ext in ["pdf", "svg", "png"]
        },
    }
    (dest / "render_manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    print(stem)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", choices=["flow", "balanced"], default="flow")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--reuse-data", action="store_true")
    args = parser.parse_args()
    if not args.reuse_data:
        prepare()
    build(args.layout, args.draft)


if __name__ == "__main__":
    main()
