"""Build the descriptive Landsat-mode PFT panel from the retained local inputs."""

from pathlib import Path
from dataclasses import dataclass

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch
from matplotlib.transforms import Bbox

from spectralbridge.landsat_agreement import mask_landsat_qa, scale_landsat_sr

ROOT = Path(__file__).resolve().parents[2]
NEON = ROOT / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact"
DRONE = ROOT / "archive/local/drone-brightness-baseline/2026-11-13"
SCENE = (
    ROOT
    / "deprecated/notebooks/megan_unmixing/data/Landsat/landsattest"
    / "LC09_L2SP_034032_20230820_20230822_02_T1"
)
EVIDENCE = ROOT / "provenance/researcher-evidence/2026-10-16/v1/tables"
RATES = (
    ROOT
    / "provenance/researcher-pft-information/2026-10-15/v1/tables"
    / "reused_researcher_class_rates_all_domains.csv"
)
OUTPUT = ROOT / "output/pdf/researcher_evidence"
PHOTO = ROOT / "provenance/landsat-pure-pixels/2026-11-18/photo-annotation"
CATEGORIES = [
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "Non-vegetated & dead",
]
LABEL = "cover_category"
BANDS = [f"B{index}" for index in range(1, 8)]
SHARED_BANDS = BANDS[:5]
EXTRA_ASSETS = ROOT / "archive/local/landsat-pft-scene"
PAIR_ROWS = ((0, 2), (1, 2), (0, 1))
PAIR_LABELS = ("Landsat–drone", "AOP–drone", "Landsat–AOP")
SENSORS = {
    "Landsat 9 OLI-2": ("#263e56", "-", "o"),
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


def band_columns(frame, columns):
    return frame.rename(columns=dict(zip(columns, BANDS[: len(columns)], strict=True)))


def sample_landsat(neon):
    labelled = neon.query("site == 'NIWO' and year == 2023")[["GlobalID", LABEL]]
    shapes = gpd.read_file(
        ROOT / "aop_polygons_4_22_2025_analysis_ready_half_diam.geojson",
        columns=["GlobalID"],
    ).merge(labelled, on="GlobalID", validate="many_to_one")
    with rasterio.open(f"{SCENE}_QA_PIXEL.TIF") as qa:
        points = shapes.to_crs(qa.crs).geometry.centroid
        coords = list(zip(points.x, points.y, strict=True))
        shapes["cell"] = [qa.index(*xy) for xy in coords]
        shapes["xy"] = coords
        qa_values = np.array([sample[0] for sample in qa.sample(coords)])
        with rasterio.open(EXTRA_ASSETS / f"{SCENE.name}_QA_RADSAT.TIF") as saturation:
            if (saturation.crs, saturation.transform, saturation.shape) != (
                qa.crs,
                qa.transform,
                qa.shape,
            ):
                raise ValueError(
                    "Landsat saturation QA grid differs from pixel QA grid"
                )
            saturation_values = np.array(
                [sample[0] for sample in saturation.sample(coords)]
            )
        shapes["clear"], _ = mask_landsat_qa(qa_values, saturation_values)
        grid = qa.crs, qa.transform, qa.shape
        inside = [
            0 <= row < qa.height and 0 <= col < qa.width for row, col in shapes.cell
        ]
    # Drop cells with conflicting mapped labels before selecting one row per cell.
    shapes = shapes.loc[inside].copy()
    unique_label = shapes.groupby("cell")[LABEL].transform("nunique").eq(1)
    cells = shapes.loc[unique_label & shapes.clear].drop_duplicates("cell").copy()
    for idx, band in enumerate(BANDS, start=1):
        path = Path(f"{SCENE}_SR_B{idx}.TIF")
        if band == "B7":
            path = EXTRA_ASSETS / path.name
        with rasterio.open(path) as raster:
            if (raster.crs, raster.transform, raster.shape) != grid:
                raise ValueError(f"Landsat {band} grid differs from QA grid")
            samples = np.array([sample[0] for sample in raster.sample(cells.xy)])
        cells[band] = scale_landsat_sr(samples)
    cells["footprint_id"] = cells.cell.map(
        lambda cell: f"{SCENE.name}:row{cell[0]}:col{cell[1]}"
    )
    cells["site"] = "NIWO"
    return cells[[LABEL, "footprint_id", "site", *BANDS]]


def load_spectra():
    neon_cols = [
        f"olioli_undarkened_wl{nm}nm" for nm in (443, 482, 561, 655, 865, 1609, 2201)
    ]
    neon = pd.read_parquet(NEON / "olioli_undarkened_polygon_year.parquet")
    landsat = sample_landsat(neon)
    neon = band_columns(neon, neon_cols)
    neon = neon.groupby([LABEL, "GlobalID", "site"], as_index=False)[BANDS].mean()

    # Documented conceptual OLI mapping for the MicaSense dual camera.
    drone_cols = [
        "raw_b001_wl0444nm",
        "raw_b002_wl0475nm",
        "raw_b004_wl0560nm",
        "raw_b006_wl0668nm",
        "raw_b010_wl0842nm",
    ]
    polygons = []
    for site in ("goldhill", "ruby"):
        (path,) = (DRONE / site).rglob("*__polygons.parquet")
        pixels = pd.read_parquet(path, columns=[LABEL, "GlobalID", *drone_cols])
        pixels = band_columns(pixels, drone_cols)
        polygons.append(
            pixels.groupby([LABEL, "GlobalID"], as_index=False)[SHARED_BANDS]
            .median()
            .assign(site=site)
        )
    drone = pd.concat(polygons, ignore_index=True)
    if drone.GlobalID.duplicated().any():
        raise ValueError("Duplicate drone polygon IDs")
    return dict(zip(SENSORS, (landsat, neon, drone), strict=True))


@dataclass
class SpectrumSummary:
    median: pd.DataFrame
    count: pd.Series
    q25: pd.DataFrame
    q75: pd.DataFrame


def summarize_spectra(spectra, categories):
    summary = {}
    for sensor, observations in spectra.items():
        available = [band for band in BANDS if band in observations]
        values = observations[available]
        totals = values[SHARED_BANDS].sum(axis=1)
        complete = np.isfinite(values).all(axis=1) & totals.gt(0)
        normalized = values.loc[complete].div(totals.loc[complete], axis=0)
        normalized[LABEL] = observations.loc[complete, LABEL]
        grouped = normalized.groupby(LABEL)
        counts = grouped.size().reindex(categories)
        if counts.isna().any():
            raise ValueError(f"Missing category data for {sensor}")
        summary[sensor] = SpectrumSummary(
            grouped[available].median().reindex(index=categories, columns=BANDS),
            counts,
            grouped[available].quantile(0.25).reindex(index=categories, columns=BANDS),
            grouped[available].quantile(0.75).reindex(index=categories, columns=BANDS),
        )
    return summary


def load_evidence(categories):
    contrasts = pd.read_csv(EVIDENCE / "whole_spectrum_separability.csv")
    rates = pd.read_csv(RATES).query(
        "representation == 'OLI' and experiment == 'hierarchy'"
    )
    evidence = {}
    for category in categories:
        pairs = contrasts.loc[contrasts.a.eq(category) | contrasts.b.eq(category)]
        recall = rates.loc[rates.label.eq(category)].groupby("kind").recall.mean()
        if len(pairs) != 16 or set(["plant", "site"]) - set(recall.index):
            raise ValueError(f"Incomplete NEON OLI evidence for {category}")
        evidence[category] = (
            f"{pairs.OLI_supported.sum()}/{len(pairs)} supported",
            f"{recall.plant:.0%} / {recall.site:.0%}",
        )
    return evidence


def band_gaps(summary):
    spectra = [item.median for item in summary.values()]
    return np.stack(
        [
            (spectra[left] - spectra[right]).abs().to_numpy() * 100
            for left, right in PAIR_ROWS
        ],
        axis=1,
    )


def load_landsat_evidence(categories, path=None):
    """Read the frozen primary photo-screened test; never infer missing tests."""
    tests = pd.read_csv(path or PHOTO / "separability.csv")
    primary = tests.loc[np.isclose(tests.threshold, 0.95) & tests.shift_m.eq(0)]
    results = {category: "No matched reference" for category in categories}
    for row in primary.itertuples():
        if row.status != "exploratory_photo_labels":
            continue
        for category, count in ((row.a, row.n_a), (row.b, row.n_b)):
            if results[category] != "No matched reference":
                raise ValueError(
                    "Multiple Landsat contrasts need an explicit table summary"
                )
            results[category] = f"n={int(count)}; p={row.p_npc_holm:.2f}†"
    return results


def draw_figure(categories, summary, evidence):
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
            [], [], color=c, linestyle=ls, marker=m, label=sensor, lw=1, markersize=6.5
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
            sensor,
            ha="center",
            va="center",
            weight="bold",
            color=SENSORS[sensor][0],
            fontsize=11,
        )
    landsat = load_landsat_evidence(categories)
    drone = pd.read_csv(OUTPUT / "drone_library_tests/class_summary.csv").set_index(
        "category"
    )
    rows = [
        [
            category,
            landsat[category],
            "Untested",
            *evidence[category],
            drone.loc[category, "separability"],
            drone.loc[category, "identification"],
        ]
        for category in categories
    ]
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
    OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    for sensor, item in summary.items():
        for category in categories:
            for band in BANDS:
                records.append(
                    dict(
                        sensor=sensor,
                        category=category,
                        band=band,
                        n=int(item.count[category]),
                        median=item.median.loc[category, band],
                        q25=item.q25.loc[category, band],
                        q75=item.q75.loc[category, band],
                    )
                )
    pd.DataFrame(records).to_csv(
        OUTPUT / "landsat_mode_pft_panel_summaries.csv", index=False
    )
    for suffix in ("pdf", "png"):
        fig.savefig(
            OUTPUT / f"landsat_mode_pft_panel.{suffix}",
            dpi=300,
            bbox_inches=Bbox.from_bounds(0, 1, 16, 9.5),
        )
    plt.close(fig)


if __name__ == "__main__":
    draw_figure(
        CATEGORIES,
        summarize_spectra(load_spectra(), CATEGORIES),
        load_evidence(CATEGORIES),
    )
