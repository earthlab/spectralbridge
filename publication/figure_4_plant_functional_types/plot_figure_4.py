#!/usr/bin/env python3
"""Reproduce Figure 4 from the CSV files beside this script.

No SpectralBridge installation, GIS software, network access or source rasters
are required. See README.md for setup and how to replace the numbers.
Rendering consumes summary tables; --recalculate-spectra recomputes panel A
from the supplied footprint observations. Statistical tests are supplied results,
not refitted by this renderer. Code license: GPL-3.0-or-later (LICENSE.txt).
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Headless rendering also works on servers and publisher systems.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.transforms import Bbox

HERE = Path(__file__).resolve().parent


@dataclass
class SpectrumSummary:
    median: pd.DataFrame
    count: pd.Series
    q25: pd.DataFrame
    q75: pd.DataFrame


CATEGORIES = [
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "Non-vegetated & dead",
]

BANDS = [f"B{index}" for index in range(1, 8)]

SHARED_BANDS = BANDS[:5]

PAIR_ROWS = ((0, 2), (1, 2), (0, 1))

PAIR_LABELS = ("HLS–drone", "AOP–drone", "HLS–AOP")

SENSORS = {
    "HLS L30 NBAR": ("#263e56", "-", "o"),
    "NEON AOP → OLI/OLI-2-like": ("#237d83", "-", "o"),
    "Drone → OLI/OLI-2-like": ("#b56a4c", "-", "o"),
}

PALETTE = {
    "ink": "#233444",
    "muted": "#66747e",
    "navy": "#263e56",
    "section": "#e7edef",
    "neutral": "#f1f4f5",
    "grid": "#dfe6e9",
    "axis": "#95a3ac",
}


def tint(color, strength):
    """Mix a sensor color with white for consistent supporting fills."""
    return to_hex((1 - strength) + strength * np.asarray(to_rgb(color)))


def band_gaps(summary):
    spectra = [item.median for item in summary.values()]
    return np.stack(
        [
            (spectra[left] - spectra[right]).abs().to_numpy() * 100
            for left, right in PAIR_ROWS
        ],
        axis=1,
    )


def draw_figure(categories, summary, table_values, output):
    plt.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "font.size": 10,
            "pdf.fonttype": 42,
            "mathtext.fontset": "dejavuserif",
            "text.color": PALETTE["ink"],
            "axes.labelcolor": PALETTE["ink"],
            "xtick.color": PALETTE["ink"],
            "ytick.color": PALETTE["ink"],
        }
    )
    fig = plt.figure(figsize=(16, 10.5), facecolor="white")
    navy = PALETTE["navy"]

    def box(x, y, w, h, color):
        fig.add_artist(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.002,rounding_size=0.005",
                transform=fig.transFigure,
                linewidth=0,
                facecolor=color,
                zorder=0,
            )
        )

    def section(y, letter, title):
        box(0.035, y, 0.93, 0.036, PALETTE["section"])
        box(0.035, y, 0.032, 0.036, navy)
        fig.text(
            0.051,
            y + 0.018,
            letter,
            ha="center",
            va="center",
            color="white",
            weight="bold",
            fontsize=17,
        )
        fig.text(0.080, y + 0.018, title, va="center", weight="bold", fontsize=16)

    fig.text(
        0.04,
        0.965,
        "Figure 4. Plant functional types across three Landsat-mode products",
        weight="bold",
        fontsize=21,
        color=PALETTE["ink"],
    )
    fig.add_artist(
        Line2D(
            [0.035, 0.965],
            [0.944, 0.944],
            transform=fig.transFigure,
            color=navy,
            lw=1.6,
        )
    )
    section(0.895, "A", "Spectral shape and pairwise differences across Landsat bands")
    handles = [
        Line2D(
            [],
            [],
            color=c,
            linestyle=ls,
            marker=m,
            label="Landsat HLS L30 NBAR" if sensor == "HLS L30 NBAR" else sensor,
            lw=1,
            markersize=6.5,
        )
        for sensor, (c, ls, m) in SENSORS.items()
    ]
    handles.append(
        Patch(
            facecolor=navy,
            edgecolor="none",
            alpha=0.18,
            label="Shading: interquartile range (25th–75th percentile)",
        )
    )
    fig.legend(
        handles=handles,
        loc="center",
        bbox_to_anchor=(0.5, 0.866),
        ncol=4,
        frameon=True,
        edgecolor=navy,
        fontsize=10,
        handlelength=2.7,
        columnspacing=1.6,
    )
    # Panel A: common scale and aligned native band positions for every PFT.
    grid = fig.add_gridspec(
        2,
        5,
        left=0.108,
        right=0.962,
        top=0.759,
        bottom=0.471,
        height_ratios=[4, 1.15],
        hspace=0.30,
        wspace=0.14,
    )
    upper = max(float(item.q75.max().max()) for item in summary.values())
    lower = min(0, min(float(item.q25.min().min()) for item in summary.values()))
    # Pairwise gaps are descriptive median differences, not significance tests.
    gaps = band_gaps(summary)
    cmap = LinearSegmentedColormap.from_list(
        "slate_gap", ["#f3f6f7", "#d0dde3", "#89a6b5", "#4c7089", PALETTE["navy"]]
    ).with_extremes(bad="#000000")
    scale = Normalize(0, max(5, 5 * np.ceil(np.nanmax(gaps) / 5)))
    for index, category in enumerate(categories):
        ax = fig.add_subplot(grid[0, index])
        position = ax.get_position()
        box(position.x0, 0.801, position.width, 0.031, navy)
        fig.text(
            position.x0 + position.width / 2,
            0.8165,
            category,
            ha="center",
            va="center",
            color="white",
            weight="bold",
            fontsize=11,
        )
        box(position.x0, 0.774, position.width, 0.023, PALETTE["neutral"])
        counts = " / ".join(f"{item.count[category]:,}" for item in summary.values())
        fig.text(
            position.x0 + position.width / 2,
            0.7855,
            "n = " + counts,
            ha="center",
            va="center",
            fontsize=9,
            style="italic",
        )
        for sensor, (color, style, marker) in SENSORS.items():
            item = summary[sensor]
            x = np.arange(len(BANDS))
            ax.fill_between(
                x,
                item.q25.loc[category].to_numpy(dtype=float),
                item.q75.loc[category].to_numpy(dtype=float),
                color=color,
                alpha=0.18,
                linewidth=0,
            )
            ax.plot(
                x,
                item.median.loc[category],
                color=color,
                linestyle=style,
                marker=marker,
                markersize=6.5,
                markeredgewidth=0,
                linewidth=1.0,
            )
        ax.set(ylim=(lower, upper * 1.06), xlim=(-0.5, 6.5))
        ax.set_xticks(range(7), BANDS, fontsize=9)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(PALETTE["axis"])
        ax.grid(axis="y", color=PALETTE["grid"], linewidth=0.7)
        ax.set_axisbelow(True)
        ax.tick_params(length=3, pad=4, labelleft=index == 0)
        if index == 0:
            ax.set_ylabel("Normalized spectral reflectance", fontsize=11)
        strip = fig.add_subplot(grid[1, index])
        heatmap = strip.imshow(
            gaps[index], cmap=cmap, norm=scale, aspect="auto", interpolation="none"
        )
        strip.set_xticks([])
        strip.set_yticks(range(3), PAIR_LABELS if index == 0 else [""] * 3, fontsize=8)
        strip.set_xticks(np.arange(8) - 0.5, minor=True)
        strip.set_yticks(np.arange(4) - 0.5, minor=True)
        strip.grid(which="minor", color="white", linewidth=0.8)
        strip.tick_params(which="both", length=0, pad=5)
        strip.spines[:].set_visible(False)
    bar = fig.colorbar(
        heatmap, cax=fig.add_axes([0.73, 0.435, 0.232, 0.013]), orientation="horizontal"
    )
    bar.set_ticks([0, scale.vmax / 2, scale.vmax])
    bar.ax.tick_params(labelsize=9, length=3)
    bar.outline.set_visible(False)
    fig.text(
        0.108,
        0.436,
        "Pairwise gap: |difference in category medians| × 100   •   Black = no shared band",
        fontsize=9,
    )
    # Panel B uses separate evidence cohorts; see figure_4_caption.md.
    section(0.363, "B", "Separability and held-out identifiability")
    table_ax = fig.add_axes([0.035, 0.128, 0.93, 0.223])
    table_ax.axis("off")
    widths = [0.205, 0.165, 0.10, 0.145, 0.12, 0.135, 0.13]
    edges = np.r_[0, np.cumsum(widths)]
    for group, (sensor, header_fill) in enumerate(
        ((sensor, tint(style[0], 0.18)) for sensor, style in SENSORS.items())
    ):
        first = 1 + 2 * group
        table_ax.add_patch(
            FancyBboxPatch(
                (edges[first], 0.86),
                edges[first + 2] - edges[first],
                0.14,
                boxstyle="round,pad=0,rounding_size=0.014",
                facecolor=header_fill,
                linewidth=0,
            )
        )
        table_ax.text(
            (edges[first] + edges[first + 2]) / 2,
            0.93,
            "Landsat HLS L30 NBAR†"
            if sensor.startswith(("Landsat", "HLS"))
            else sensor,
            ha="center",
            va="center",
            weight="bold",
            color=SENSORS[sensor][0],
            fontsize=11,
        )
    # Panel B cells are formatted from numeric evidence, never inferred from spectra.
    rows = []
    for category in categories:
        row = [category]
        for sensor in SENSORS:
            row.extend(table_values[(sensor, category)])
        rows.append(row)
    table = table_ax.table(
        cellText=rows,
        cellLoc="center",
        colWidths=widths,
        colLabels=["Researcher category", *["Separability", "Identifiability"] * 3],
        bbox=[0, 0, 1, 0.85],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("white")
        if col == 0:
            cell.set_facecolor(
                PALETTE["section"]
                if row == 0
                else tint(navy, 0.025 if row % 2 else 0.055)
            )
        else:
            sensor_color = list(SENSORS.values())[(col - 1) // 2][0]
            cell.set_facecolor(
                tint(sensor_color, 0.12 if row == 0 else 0.035 if row % 2 else 0.075)
            )
        cell.set_text_props(color=PALETTE["ink"])
        if col == 0 or row == 0:
            cell.set_text_props(weight="bold")
        if col == 0:
            cell.set_text_props(ha="left")
        elif row and col == 2:
            cell.set_text_props(style="italic", color=PALETTE["muted"])
        elif row and col == 1:
            cell.set_text_props(fontsize=9)
    output.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "png"):
        fig.savefig(
            output / f"figure_4_plant_functional_types.{suffix}",
            dpi=300,
            bbox_inches=Bbox.from_bounds(0, 1, 16, 9.5),
        )
    plt.close(fig)


def recalculate_spectra(path):
    """Recalculate medians/IQRs from one observation per footprint (not pixels).

    Input observations are already aggregated across repeat NEON years and within
    drone polygons. Normalize each footprint by its own B1-B5 sum *before* taking
    category quantiles, with linear interpolation (pandas default).
    """
    frame = pd.read_csv(path)
    required = {
        "sensor",
        "category",
        "footprint_id",
        "site",
        "calculation_dtype",
        *BANDS,
    }
    if not required.issubset(frame):
        raise ValueError(f"Observation columns missing: {required - set(frame)}")
    if frame[["sensor", "category", "footprint_id", "site"]].isna().any().any():
        raise ValueError("Every footprint requires a sensor, category, ID and site")
    if frame.duplicated(["sensor", "footprint_id"]).any():
        raise ValueError("Repeated footprint identities would inflate sample counts")
    records = []
    for sensor in SENSORS:
        subset = frame.loc[frame.sensor.eq(sensor)].copy()
        available = BANDS[:5] if sensor.startswith("Drone") else BANDS
        # Preserve the arithmetic precision of the source summary (drone float32).
        dtypes = subset.calculation_dtype.unique()
        if len(dtypes) != 1 or dtypes[0] not in {"float32", "float64"}:
            raise ValueError(
                "Use one calculation_dtype (float32 or float64) per sensor"
            )
        values = subset[available].astype(dtypes[0])
        totals = values[BANDS[:5]].sum(axis=1)
        valid = np.isfinite(values).all(axis=1) & totals.gt(0)
        if not valid.all():
            print(
                f"{sensor}: excluded {int((~valid).sum())} incomplete/nonpositive-sum footprints"
            )
        normalized = values.loc[valid].div(totals.loc[valid], axis=0)
        normalized["category"] = subset.loc[valid, "category"]
        grouped = normalized.groupby("category")
        for category in CATEGORIES:
            if category not in grouped.groups:
                raise ValueError(f"No complete footprints for {sensor}: {category}")
            group = grouped.get_group(category)
            for band in BANDS:
                stats = (
                    group[band].quantile([0.25, 0.5, 0.75]).to_numpy()
                    if band in available
                    else [np.nan] * 3
                )
                records.append(
                    dict(
                        sensor=sensor,
                        category=category,
                        band=band,
                        n=len(group),
                        q25=stats[0],
                        median=group[band].median() if band in available else np.nan,
                        q75=stats[2],
                    )
                )
    return pd.DataFrame(records)[
        ["sensor", "category", "band", "n", "median", "q25", "q75"]
    ]


def load_summary(path):
    """Reject ambiguous/missing rows and preserve absent drone SWIR as blank."""
    frame = pd.read_csv(path)
    expected = {
        (sensor, category, band)
        for sensor in SENSORS
        for category in CATEGORIES
        for band in BANDS
    }
    actual = set(zip(frame.sensor, frame.category, frame.band))
    if actual != expected or frame.duplicated(["sensor", "category", "band"]).any():
        raise ValueError(
            "Summary must contain exactly one row per sensor/PFT/B1-B7 combination"
        )
    if not (np.isfinite(frame.n) & frame.n.gt(0) & frame.n.eq(np.floor(frame.n))).all():
        raise ValueError("Counts must be positive whole footprint counts")
    unavailable = frame.sensor.str.startswith("Drone") & frame.band.isin(["B6", "B7"])
    values = frame[["q25", "median", "q75"]]
    if (
        not values.loc[unavailable].isna().all().all()
        or not np.isfinite(values.loc[~unavailable]).all().all()
    ):
        raise ValueError(
            "Only drone B6/B7 must be blank; all shared band values must be finite"
        )
    if not (
        values.loc[~unavailable, "q25"].le(values.loc[~unavailable, "median"])
        & values.loc[~unavailable, "median"].le(values.loc[~unavailable, "q75"])
    ).all():
        raise ValueError("Require q25 <= median <= q75")
    if frame.groupby(["sensor", "category"]).n.nunique().gt(1).any():
        raise ValueError("Each sensor/PFT count must agree across bands")
    summary = {}
    for sensor in SENSORS:
        selected = frame.loc[frame.sensor.eq(sensor)]

        def wide(column):
            return selected.pivot(
                index="category", columns="band", values=column
            ).reindex(index=CATEGORIES, columns=BANDS)

        counts = selected.groupby("category").n.first().reindex(CATEGORIES).astype(int)
        summary[sensor] = SpectrumSummary(
            wide("median"), counts, wide("q25"), wide("q75")
        )
    return summary


def load_table(path):
    """Format numeric evidence without changing p-values or inventing tests.

    Recall inputs are fractions in [0,1]. The table displays percentages rounded
    to whole numbers. The two recall columns mean unseen polygons / held-out sites.
    Dagger marks point to the full companion caption, not additional table tests.
    """
    frame = pd.read_csv(path)
    expected = {(sensor, category) for sensor in SENSORS for category in CATEGORIES}
    if (
        set(zip(frame.sensor, frame.category)) != expected
        or frame.duplicated(["sensor", "category"]).any()
    ):
        raise ValueError("Evidence must contain one row per sensor/PFT")
    output = {}
    for row in frame.itertuples():
        if row.separability_status == "no_matched_reference":
            separability = "No matched reference"
        elif row.separability_status == "insufficient_patch_support":
            if row.total_tests != 0 or row.supported_tests != 0:
                raise ValueError(
                    "Insufficient patch support requires zero testable pairs"
                )
            separability = "Insufficient patches†"
        elif row.separability_status == "provisional_matched_test":
            if not (
                np.isfinite(row.matched_n)
                and row.matched_n >= 1
                and row.matched_n == int(row.matched_n)
                and 0 <= row.adjusted_p <= 1
            ):
                raise ValueError(
                    "Matched tests require positive integer n and p in [0,1]"
                )
            separability = f"n={int(row.matched_n)}; p={row.adjusted_p:.2f}†"
        elif row.separability_status == "supported_test_counts":
            if not (
                0 <= row.supported_tests <= row.total_tests
                and row.total_tests > 0
                and row.total_tests == int(row.total_tests)
                and row.supported_tests == int(row.supported_tests)
            ):
                raise ValueError(
                    "Require integer supported/total counts with positive denominator"
                )
            separability = (
                f"{int(row.supported_tests)}/{int(row.total_tests)} supported"
            )
            if row.sensor.startswith("Drone"):
                separability += "‡"
            elif row.sensor.startswith(("Landsat", "HLS")):
                separability += "†"
        else:
            raise ValueError(f"Unknown separability status: {row.separability_status}")
        if row.identifiability_status == "untested":
            identifiability = "Untested"
        elif row.identifiability_status == "insufficient_training_patches":
            if row.supported_test_patches != 0 or np.isfinite(
                row.held_out_patch_recall
            ):
                raise ValueError(
                    "Unavailable held-class recall must have zero support and blank recall"
                )
            identifiability = f"NA ({int(row.held_out_patch_total)} patch)†"
        elif row.identifiability_status == "provisional_patch_recall":
            if not 0 <= row.held_out_patch_recall <= 1:
                raise ValueError("Patch recall must be a fraction in [0,1]")
            correct, total = row.held_out_patch_correct, row.held_out_patch_total
            if not (
                0 <= correct <= total
                and total > 0
                and total == int(total)
                and correct == int(correct)
                and np.isclose(correct / total, row.held_out_patch_recall)
            ):
                raise ValueError("Patch recall must agree with integer correct/total")
            identifiability = (
                f"{row.held_out_patch_recall:.0%} ({int(correct)}/{int(total)})†"
            )
        elif row.identifiability_status == "available":
            recalls = [row.unseen_polygon_recall, row.held_out_site_recall]
            if any(np.isfinite(value) and not 0 <= value <= 1 for value in recalls):
                raise ValueError(
                    "Recall must be a fraction in [0,1], or blank for unavailable"
                )
            identifiability = " / ".join(
                f"{value:.0%}" if np.isfinite(value) else "NA" for value in recalls
            )
            if row.sensor.startswith("Drone"):
                identifiability += "‡"
        else:
            raise ValueError(
                f"Unknown identifiability status: {row.identifiability_status}"
            )
        output[(row.sensor, row.category)] = (separability, identifiability)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=HERE / "data",
        help="Folder with the three CSV inputs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=HERE,
        help="Where to write the Figure 4 PDF and 300-dpi PNG",
    )
    parser.add_argument(
        "--recalculate-spectra",
        action="store_true",
        help="Replace summary CSV with medians/IQRs recalculated from footprint observations",
    )
    parser.add_argument(
        "--check", action="store_true", help="Validate inputs only; do not render"
    )
    args = parser.parse_args()
    summary_path = args.data_dir / "spectral_medians_and_interquartile_ranges.csv"
    if args.recalculate_spectra:
        recalculate_spectra(
            args.data_dir / "spectral_observations_by_footprint.csv"
        ).to_csv(summary_path, index=False)
        print(f"Updated {summary_path}")
    summary = load_summary(summary_path)
    table = load_table(args.data_dir / "pft_separability_and_identifiability.csv")
    if args.check:
        print("Inputs valid: 105 spectral rows and 15 sensor/PFT evidence rows")
        return
    draw_figure(CATEGORIES, summary, table, args.output_dir)
    print(f"Wrote Figure 4 PDF and PNG to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
