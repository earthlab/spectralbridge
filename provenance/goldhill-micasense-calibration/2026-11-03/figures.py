"""Plausibility plots only; none certifies physical calibration."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "results.json").read_text())
a = np.load(HERE / "display_arrays.npz")
waves = [b["wavelength_nm"] for b in r["band_statistics"]]
plt.rcParams.update(
    {
        "font.size": 10,
        "figure.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
manifest = []


def save(fig, name, caption):
    fig.savefig(HERE / (name + ".png"), dpi=180, bbox_inches="tight")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
    plt.close(fig)
    manifest.append(
        dict(
            name=name,
            png=name + ".png",
            svg=name + ".svg",
            caption=caption,
            status="HYPOTHETICAL_SCALE_ONLY_UNVERIFIED_CALIBRATION",
        )
    )


fig, axs = plt.subplots(2, 5, figsize=(15, 6), sharex=True, sharey=True)
centers = (a["edges"][:-1] + a["edges"][1:]) / 2
for i, ax in enumerate(axs.flat):
    ax.step(centers, a["histograms"][i], where="mid")
    ax.set(xlabel="Candidate DN / 32768", title=f"{waves[i]} nm", yscale="log")
    if i % 5 == 0:
        ax.set_ylabel("Valid original pixels / bin")
fig.suptitle(
    "HYPOTHESIS A: original positive-alpha observations only - not verified reflectance",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.93))
save(
    fig,
    "figure01_candidate_distributions",
    "All 9,377,010 valid original pixels per band. Transparent 65535 values are excluded. No candidate values exceed 1; this is a plausibility observation, not proof that calibration was applied.",
)

fig, axs = plt.subplots(1, 3, figsize=(14, 4))
for ax, p in zip(axs, r["representative_native_spectra"]):
    ax.plot(
        waves,
        p["hypothesis_A_DN_div_32768"],
        marker="o",
        label="Candidate calibrated DN/32768",
    )
    ax.plot(
        waves,
        p["numeric_fraction_DN_div_65535"],
        marker="x",
        label="Numerical DN/65535 fraction",
    )
    ax.set(
        xlabel="Wavelength (nm)",
        ylabel="Candidate fraction (units unverified)",
        title=f"E {p['easting']:.0f}, N {p['northing']:.0f}",
    )
axs[0].legend(fontsize=8)
fig.suptitle(
    "Both scales retain spectral shape; image appearance cannot select the divisor",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.92))
save(
    fig,
    "figure02_candidate_spectra",
    "Three fixed native source pixels, positive alpha. Candidate A is 1.99996948 times the DN/65535 numerical fraction. Shape, spectral angle, correlations and ratio indices cannot establish the absolute physical scale.",
)

fig, axs = plt.subplots(1, 3, figsize=(14, 4.5))
for ax, key, title, limit in [
    (axs[0], "red_A", "Candidate red / 32768", 0.45),
    (axs[1], "nir_A", "Candidate NIR / 32768", 0.65),
]:
    im = ax.imshow(a[key], vmin=0, vmax=limit, cmap="viridis")
    fig.colorbar(
        im, ax=ax, shrink=0.8, label="Candidate fractional reflectance - UNVERIFIED"
    )
    ax.set_title(title)
    ax.set_axis_off()
corr = np.asarray(r["shape_checks"]["pearson_correlations"])
im = axs[2].imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
axs[2].set(
    xticks=range(10),
    xticklabels=waves,
    yticks=range(10),
    yticklabels=waves,
    title="Cross-band Pearson correlation",
)
axs[2].tick_params(axis="x", rotation=90)
fig.colorbar(im, ax=axs[2], shrink=0.8)
fig.suptitle(
    "HYPOTHESIS A: spatial and cross-band plausibility, without an absolute reference",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.93))
save(
    fig,
    "figure03_candidate_maps",
    "Maps are decimated only for display; native statistics use all valid source pixels. Correlations use a deterministic approximately 50,000-pixel sample and are unchanged by a common positive divisor. No calibrated reference/panel observation is supplied.",
)
(HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
