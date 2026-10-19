"""Scientific figures from compact completed real-Landsat flight validation data."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Rectangle

from .landsat_agreement import OLI_CHANNELS


def build_flight_validation_figures(output, rgb_max=0.4):
    """Render common-support maps and band diagnostics from an existing flight-validation result packet."""

    root = Path(output)
    figures = root / "figures"
    figures.mkdir(exist_ok=True)
    with np.load(root / "matched_grid.npz") as f:
        a = {k: f[k] for k in f.files}
    pixels = pd.read_parquet(root / "pixel_metrics.parquet")
    metrics = pd.read_csv(root / "band_metrics.csv")
    status = json.loads((root / "status.json").read_text())
    grid = json.loads((root / "grid.json").read_text())
    plt.rcParams.update(
        {
            "font.size": 9,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    common = a["common"]
    real = a["actual"]
    raw = a["undarkened"]
    adjusted = a["adjusted"]

    def rgb(values):
        color = np.moveaxis(values[[3, 2, 1]], 0, -1) / rgb_max
        return np.dstack([np.nan_to_num(np.clip(color, 0, 1)), common.astype(float)])

    def save(fig, name, caption):
        fig.text(0.06, 0.012, caption, fontsize=8, va="bottom")
        fig.tight_layout(rect=(0, 0.065, 1, 0.98))
        for ext in ["pdf", "png", "svg"]:
            fig.savefig(figures / (name + "." + ext), dpi=250, bbox_inches="tight")
        plt.close(fig)

    title = f"{status['flight']['site']} | {status['flight']['flight_id']}\nActual {status['selected_scene']['product_id']} | time difference {status['selected_scene']['delta_time_hours']:.2f} h (legacy NEON UTC-basis caveat)"
    residual = np.where(common, raw[4] - real[4], np.nan)
    anglemap = np.full(common.shape, np.nan)
    anglemap[common] = pixels.undarkened_spectral_angle_deg
    rmsemap = np.full(common.shape, np.nan)
    rmsemap[common] = pixels.undarkened_multiband_RMSE
    fig, axes = plt.subplots(2, 3, figsize=(16, 7))
    for ax, values, label in zip(
        axes[0],
        [raw, real, adjusted],
        [
            "NEON-derived OLI, undarkened",
            "REAL Landsat C2 L2 SR",
            "NEON-derived OLI, adjusted",
        ],
    ):
        ax.imshow(rgb(values))
        ax.set_title(label)
        ax.set_facecolor("#d9dfe2")
    for ax, values, label, cmap, lo, hi in [
        (axes[1, 0], residual, "NIR residual: synthetic - real", "RdBu_r", -0.15, 0.15),
        (axes[1, 1], rmsemap, "Seven-band RMSE (unitless SR)", "magma", 0, 0.15),
        (axes[1, 2], anglemap, "Spectral angle (degrees)", "viridis", 0, 45),
    ]:
        im = ax.imshow(values, cmap=cmap, vmin=lo, vmax=hi)
        ax.set_title(label)
        fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    for ax in axes.flat:
        ax.set(
            xlabel="Actual Landsat column in crop", ylabel="Actual Landsat row in crop"
        )
    fig.suptitle(title, fontsize=11)
    clipped = int(np.count_nonzero(common & (np.abs(residual) > 0.15)))
    save(
        fig,
        "A_side_by_side",
        "Identical grid/extent/shared support; both RGB stretches fixed 0-0.4 unitless SR. Gray = excluded support. No fitted calibration or registration applied.\nResidual colors saturate beyond +/-0.15 ("
        + str(clipped)
        + " pixels); all values retained in tables/scatterplots. Maps keep the native pixel aspect.",
    )
    # QA and accepted coverage are distinct views.
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    cmap = ListedColormap(
        ["#6ca783", "#e1a2ba", "#594973", "#a5d4e8", "#444b51", "#e3a759"]
    )
    im = axes[0].imshow(
        a["qa_category"], cmap=cmap, norm=BoundaryNorm(np.arange(-0.5, 6), 6)
    )
    axes[0].set_title("Actual Landsat QA_PIXEL + QA_RADSAT")
    cb = fig.colorbar(im, ax=axes[0], ticks=range(6), fraction=0.04)
    cb.ax.set_yticklabels(
        [
            "Clear QA",
            "Cloud/cirrus",
            "Shadow",
            "Snow",
            "Fill/invalid",
            "Saturation/terrain",
        ]
    )
    for ax, key, label, cmap in [
        (axes[1], "coverage", "Valid NEON area / full Landsat cell", "viridis"),
        (
            axes[2],
            "cloud_distance",
            "Conservative distance to cloud/unknown edge (m)",
            "cividis",
        ),
    ]:
        im = ax.imshow(a[key], cmap=cmap)
        ax.set_title(label)
        fig.colorbar(im, ax=ax, fraction=0.04)
    for ax in axes:
        ax.set(xlabel="Landsat column", ylabel="Landsat row")
    save(
        fig,
        "B_QA_and_coverage",
        "Clear Landsat QA alone is not sufficient NEON coverage. Primary comparison requires >=90% valid area in each actual Landsat footprint.\nCloud-distance halo includes an unknown-boundary barrier; it is a conservative lower bound, not a claim that unseen areas are cloud-free.",
    )
    # Untrimmed point plots and agreement-oriented residuals.
    for variant in ["undarkened", "adjusted"]:
        fig, axes = plt.subplots(2, 4, figsize=(15, 8))
        for band, ax in zip(OLI_CHANNELS, axes.flat):
            x = pixels["real_" + band].to_numpy()
            y = pixels[variant + "_" + band].to_numpy()
            m = metrics[(metrics.variant == variant) & (metrics.band == band)].iloc[0]
            ax.scatter(x, y, s=3, alpha=0.12, rasterized=True, color="#1d657c")
            lo = min(x.min(), y.min())
            hi = max(x.max(), y.max())
            pad = max(0.005, (hi - lo) * 0.03)
            ax.plot(
                [lo - pad, hi + pad], [lo - pad, hi + pad], color="grey", ls="--", lw=1
            )
            ax.plot(
                [lo, hi],
                m.deming_intercept + m.deming_slope * np.array([lo, hi]),
                color="#b56738",
                lw=1,
            )
            ax.set(
                xlabel="Real Landsat SR",
                ylabel="NEON-derived OLI SR",
                title=band,
                xlim=(lo - pad, hi + pad),
                ylim=(lo - pad, hi + pad),
            )
            ax.text(
                0.03,
                0.97,
                f"N={len(x)}\nbias={m.mean_bias:.4f}\nRMSE={m.RMSE:.4f}\nr={m.Pearson_r:.3f}\nDeming slope={m.deming_slope:.3f}",
                transform=ax.transAxes,
                va="top",
                fontsize=8,
            )
        axes.flat[-1].axis("off")
        fig.suptitle("Band agreement: " + variant)
        save(
            fig,
            "C_scatter_" + variant,
            "All accepted pixels/outliers shown. Dashed: identity; brown: descriptive Deming lambda=1 (equal error variances assumed). No correction is applied.\nN is spatially correlated Landsat pixels, not independent ecological replicates. Spatial-block uncertainty and lambda sensitivity are in band_metrics.csv.",
        )
        fig, axes = plt.subplots(2, 4, figsize=(15, 8))
        for band, ax in zip(OLI_CHANNELS, axes.flat):
            x = pixels["real_" + band].to_numpy()
            y = pixels[variant + "_" + band].to_numpy()
            m = metrics[(metrics.variant == variant) & (metrics.band == band)].iloc[0]
            ax.scatter(
                (x + y) / 2, y - x, s=3, alpha=0.12, rasterized=True, color="#1d657c"
            )
            ax.axhline(0, color="grey", lw=0.8)
            ax.axhline(m.mean_bias, color="#b56738", lw=1)
            for value in [m.loa_lower, m.loa_upper]:
                ax.axhline(value, color="#b56738", ls="--", lw=0.8)
            ax.set(
                xlabel="Mean reflectance of pair", ylabel="Synthetic - real", title=band
            )
        axes.flat[-1].axis("off")
        fig.suptitle("Bland-Altman style agreement: " + variant)
        save(
            fig,
            "D_agreement_" + variant,
            "Solid brown: mean bias; dashed: mean +/-1.96 residual SD, descriptive normal-reference limits. Empirical 2.5/97.5 percentiles are also reported.\nBrightness dependence and spatial correlation can invalidate a constant normal limit interpretation; no iid-pixel significance tests are used.",
        )
    # Representative actual seven-channel observations, with no fake continuum.
    order = np.argsort(pixels.undarkened_multiband_RMSE.to_numpy())
    examples = [order[int(q * (len(order) - 1))] for q in [0.05, 0.5, 0.95, 1.0]]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    labels = [
        "Low error (5th percentile)",
        "Median error",
        "High error (95th percentile)",
        "Worst observed error",
    ]
    for ax, index, label in zip(axes.flat, examples, labels):
        row = pixels.iloc[index]
        xx = np.arange(7)
        for shift, variant, color in [
            (-0.14, "real", "#222222"),
            (0, "undarkened", "#1b7186"),
            (0.14, "adjusted", "#b16d35"),
        ]:
            ax.scatter(
                xx + shift,
                [row[variant + "_" + band] for band in OLI_CHANNELS],
                label=variant,
                color=color,
                s=25,
            )
        ax.set(
            xticks=xx,
            xticklabels=[
                "Coastal\n443",
                "Blue\n482",
                "Green\n561",
                "Red\n655",
                "NIR\n865",
                "SWIR1\n1609",
                "SWIR2\n2201",
            ],
            ylabel="Unitless SR",
            title=f"{label}\nr={row.row}, c={row.col}; raw RMSE={row.undarkened_multiband_RMSE:.4f}; angle={row.undarkened_spectral_angle_deg:.1f} deg",
        )
        ax.legend(fontsize=8)
    save(
        fig,
        "E_representative_spectra",
        "Actual implemented seven bands; points are independent channels, not a continuous hyperspectral curve. Examples selected by predeclared undarkened error ranks.\nSelection illustrates the error distribution and does not change inclusion or agreement statistics. Band centers are nominal rounded nanometers.",
    )
    # Worst cases: retain and display them rather than editing them away.
    worst = pixels.nlargest(8, "undarkened_multiband_RMSE")
    fig, axes = plt.subplots(2, 4, figsize=(15, 8))
    for ax, row in zip(axes.flat, worst.itertuples()):
        rr = int(row.row - grid["row_offset"])
        cc = int(row.col - grid["col_offset"])
        bounds = (
            slice(max(0, rr - 2), min(common.shape[0], rr + 3)),
            slice(max(0, cc - 2), min(common.shape[1], cc + 3)),
        )
        left = rgb(raw)[bounds]
        right = rgb(real)[bounds]
        ax.imshow(np.concatenate([left, right], axis=1), interpolation="nearest")
        ax.axis("off")
        ax.set_title(
            f"row {row.row}, col {row.col}\nRMSE={row.undarkened_multiband_RMSE:.3f}, angle={row.undarkened_spectral_angle_deg:.1f}\ncoverage={row.valid_coverage_fraction:.2f}, heterogeneity={row.heterogeneity:.3f}\nwater={row.water}, clear distance>={row.cloud_distance_lower_bound_m:.0f}m",
            fontsize=8,
        )
    save(
        fig,
        "F_failure_gallery",
        "Eight largest undarkened errors, retained in all primary metrics. Each patch: NEON-derived RGB left, actual Landsat RGB right; common 0-0.4 stretch.\nPatches provide context, not causal labels. Full worst-pixel coordinates and diagnostic quantities are in failure_pixels.csv.",
    )
    # Spatial alignment is a sensitivity, never an automatically selected shift.
    reg = pd.read_csv(root / "registration_sensitivity.csv")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, variant in zip(axes, ["undarkened", "adjusted"]):
        sub = (
            reg[reg.variant == variant]
            .groupby(["dy_m", "dx_m"])
            .RMSE.median()
            .unstack()
            .sort_index()
        )
        im = ax.imshow(sub.to_numpy(), origin="lower", cmap="magma")
        for i in range(3):
            for j in range(3):
                ax.text(
                    j,
                    i,
                    f"{sub.iloc[i, j]:.4f}",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=10,
                )
        ax.add_patch(Rectangle((0.5, 0.5), 1, 1, fill=False, edgecolor="cyan", lw=2))
        ax.set(
            xticks=range(3),
            xticklabels=["-30", "0", "+30"],
            yticks=range(3),
            yticklabels=["-30", "0", "+30"],
            xlabel="Source east shift (m)",
            ylabel="Source north shift (m)",
            title=variant + " | median band RMSE",
        )
        fig.colorbar(im, ax=ax, fraction=0.04)
    save(
        fig,
        "G_registration_sensitivity",
        "Nine predeclared shifts, evaluated on the same cells valid under all shifts. Cyan box: ORIGINAL alignment, used for primary results.\nNo shift is applied or optimized away. The complete per-band sensitivity table retains N and every tested alignment.",
    )
    # Paper-style summary: one flight is clearly labeled as one flight.
    fig, axes = plt.subplots(3, 2, figsize=(13, 11))
    axes[0, 0].imshow(rgb(raw))
    axes[0, 0].set_title("A | NEON-derived OLI (undarkened)")
    axes[0, 1].imshow(rgb(real))
    axes[0, 1].set_title("B | REAL Landsat C2 L2 SR")
    im = axes[1, 0].imshow(residual, cmap="RdBu_r", vmin=-0.15, vmax=0.15)
    fig.colorbar(im, ax=axes[1, 0], fraction=0.035)
    axes[1, 0].set_title("C | NIR residual: synthetic - real")
    x = pixels.real_nir08.to_numpy()
    y = pixels.undarkened_nir08.to_numpy()
    axes[1, 1].scatter(x, y, s=3, alpha=0.1, rasterized=True)
    lo = min(x.min(), y.min())
    hi = max(x.max(), y.max())
    axes[1, 1].plot([lo, hi], [lo, hi], ls="--", color="grey")
    axes[1, 1].set(
        xlabel="Real NIR SR",
        ylabel="Synthetic NIR SR",
        title="D | NIR agreement (all outliers retained)",
    )
    xx = np.arange(7)
    for shift, variant, color in [
        (-0.17, "undarkened", "#1d7186"),
        (0.17, "adjusted", "#b16d35"),
    ]:
        g = (
            metrics[metrics.variant == variant]
            .set_index("band")
            .loc[list(OLI_CHANNELS)]
        )
        axes[2, 0].bar(xx + shift, g.RMSE, width=0.3, label=variant, color=color)
        angles = pixels[variant + "_spectral_angle_deg"]
        axes[2, 1].hist(angles.dropna(), bins=35, alpha=0.5, label=variant, color=color)
    axes[2, 0].set(
        xticks=xx,
        xticklabels=OLI_CHANNELS,
        ylabel="RMSE (unitless SR)",
        title="E | Bandwise magnitude error",
    )
    axes[2, 0].tick_params(axis="x", rotation=40)
    axes[2, 0].legend(fontsize=8)
    axes[2, 1].set(
        xlabel="Spectral angle (degrees)",
        ylabel="Spatially correlated pixels",
        title="F | Within-flight spectral-shape agreement",
    )
    axes[2, 1].legend(fontsize=8)
    fig.suptitle("Independent real-sensor pilot | ONE flight / ONE scene", fontsize=13)
    save(
        fig,
        "H_paper_summary",
        "RGB shares extent/grid/mask and fixed 0-0.4 stretch. Primary uses original registration and no empirical calibration. Separate magnitude and shape diagnostics.\nThis single-flight pilot does not establish cross-flight/site replication, actual regional transfer, or an accuracy threshold for every scientific application.",
    )
