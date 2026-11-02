"""Plot unchanged saved summaries and configured Gaussian weights, without new fits."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
data = pd.read_csv(
    ROOT / "provenance/manuscript-synthesis/2026-10-16/v1/data/A_category_spectra.csv"
)
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 20,
        "axes.labelsize": 22,
        "xtick.labelsize": 19,
        "ytick.labelsize": 19,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#B7C6CC",
        "axes.labelcolor": "#183440",
        "text.color": "#183440",
        "xtick.color": "#526873",
        "ytick.color": "#526873",
        "pdf.fonttype": 42,
    }
)
colors = {
    "Deciduous": "#4B8460",
    "Evergreen": "#144E49",
    "Herbaceous": "#BA921D",
    "Non-vegetated & dead": "#A56F50",
    "Woody shrub": "#9265A4",
}


def segments(a):
    return np.split(np.arange(len(a)), np.flatnonzero(np.diff(a) > 30) + 1)


def decorate(ax):
    ax.set_xlim(380, 2500)
    ax.set_xticks([500, 1000, 1500, 2000, 2500])
    ax.grid(axis="y", color="#E9EFEE", lw=1)
    ax.set_axisbelow(True)
    for lo, hi in [(1340, 1450), (1800, 1980)]:
        ax.axvspan(lo, hi, color="#EDF0F1", zorder=0)


fig, ax = plt.subplots(figsize=(15, 11))
fig.subplots_adjust(left=0.105, right=0.97, bottom=0.13, top=0.80)
for cat, color in colors.items():
    d = data[data.cover_category == cat].sort_values("wavelength_nm")
    w = d.wavelength_nm.to_numpy()
    m = d["median"].to_numpy() / 1000
    for i, seg in enumerate(segments(w)):
        ax.plot(w[seg], m[seg], color=color, lw=3.6, label=cat if i == 0 else None)
        ax.fill_between(
            w[seg],
            d.q25.to_numpy()[seg] / 1000,
            d.q75.to_numpy()[seg] / 1000,
            color=color,
            alpha=0.10,
            lw=0,
        )
decorate(ax)
ax.set_ylim(0, 5.7)
ax.set_ylabel("Stored spectral signal (thousands)")
ax.set_xlabel("Wavelength (nm)", labelpad=14)
ax.legend(
    loc="lower left",
    bbox_to_anchor=(0, 1.03),
    ncol=2,
    frameon=False,
    fontsize=18,
    handlelength=2.2,
    columnspacing=1.1,
)
ax.annotate(
    "Sharp rise beyond\nvisible red light",
    xy=(710, 2),
    xytext=(835, 5.0),
    fontsize=20,
    color="#176E65",
    arrowprops={"arrowstyle": "->", "color": "#176E65", "lw": 1.8},
)
ax.text(
    0.96,
    0.94,
    "Shading: middle 50%\nof observed curves",
    transform=ax.transAxes,
    ha="right",
    va="top",
    fontsize=17,
    color="#526873",
)
fig.savefig(BASE / "category_spectra.pdf", facecolor="white")
plt.close(fig)

# Sensor diagram: saved evergreen median above the package's configured OLI weights.
config = json.loads(
    (ROOT / "src/spectralbridge/data/landsat_band_parameters.json").read_text()
)["Landsat 8 OLI"]
fig, (ax1, ax2) = plt.subplots(
    2, 1, figsize=(15, 11), sharex=True, gridspec_kw={"height_ratios": [1, 1]}
)
fig.subplots_adjust(left=0.105, right=0.97, bottom=0.13, top=0.91, hspace=0.34)
d = data[data.cover_category == "Evergreen"].sort_values("wavelength_nm")
w = d.wavelength_nm.to_numpy()
for seg in segments(w):
    ax1.plot(
        w[seg], d["median"].to_numpy()[seg] / 1000, color=colors["Evergreen"], lw=3.6
    )
decorate(ax1)
ax1.set_ylim(0, 3.0)
ax1.set_ylabel("Stored signal\n(thousands)")
ax1.set_title(
    "Many wavelength samples: evergreen median", loc="left", fontsize=21, pad=16
)
wl = np.linspace(380, 2500, 3000)
bandcolors = [
    "#8262AD",
    "#3F83C6",
    "#65A868",
    "#D86658",
    "#A14E8F",
    "#C2923D",
    "#527F86",
]
for center, width, col in zip(config["wavelengths"], config["fwhms"], bandcolors):
    sigma = width / (2 * np.sqrt(2 * np.log(2)))
    weight = np.exp(-0.5 * ((wl - center) / sigma) ** 2)
    ax2.plot(wl, weight, color=col, lw=2.6)
    ax2.fill_between(wl, 0, weight, color=col, alpha=0.35)
ax2.set_xlim(380, 2500)
ax2.set_ylim(0, 1.2)
ax2.set_xticks([500, 1000, 1500, 2000, 2500])
ax2.set_yticks([0, 1])
ax2.set_ylabel("Relative weight")
ax2.set_xlabel("Wavelength (nm)", labelpad=14)
ax2.set_title("Seven configured Landsat-like bands", loc="left", fontsize=21, pad=16)
ax2.text(
    0.96,
    0.94,
    "Each peak selects a different\nrange of wavelengths",
    transform=ax2.transAxes,
    ha="right",
    va="top",
    fontsize=17,
    color="#526873",
)
ax2.grid(axis="y", color="#E9EFEE")
ax2.set_axisbelow(True)
fig.savefig(BASE / "sensor_weights.pdf", facecolor="white")
plt.close(fig)
print("Two vector graphs built from saved summaries and configuration")
