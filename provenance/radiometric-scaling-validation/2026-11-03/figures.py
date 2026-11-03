"""Actual-data figures; diagnostic normalized fractions are never physical calibration."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "results.json").read_text())
a = np.load(HERE / "display_arrays.npz")
rows = r["goldhill"]
waves = [x["wavelength_nm"] for x in rows]
plt.rcParams.update(
    {
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
    }
)
manifest = []


def save(fig, name, caption):
    fig.savefig(HERE / (name + ".png"), dpi=180, bbox_inches="tight")
    fig.savefig(HERE / (name + ".svg"), bbox_inches="tight")
    manifest.append(
        dict(
            name=name,
            caption=caption,
            source="results.json and display_arrays.npz; native actual Goldhill/NEON observations",
            png=name + ".png",
            svg=name + ".svg",
        )
    )
    plt.close(fig)


fig, axs = plt.subplots(2, 1, figsize=(12, 5))
for ax, title, text, color in [
    (
        axs[0],
        "Goldhill drone",
        "Metashape UInt16 output\nphysical calibration unverified\n↓ band-specific normalization\nS: range-normalized 0–10,000\n↓ verified numeric division by 10,000\nF: normalized fraction, DIAGNOSTIC ONLY\nPhysical calibration + angular information still required",
        "#fef0d9",
    ),
    (
        axs[1],
        "NEON AOP",
        "Calibrated H5 stored reflectance S\nScale_Factor = 10,000 (DIVISOR)\n↓ physical = 0.0001 × S + 0\nFit/apply in fractional physical reflectance\n↓ inverse encoding for native corrected output\nDecode once for physical tables/libraries",
        "#e0f3f8",
    ),
]:
    ax.axis("off")
    ax.text(0.02, 0.5, title, weight="bold", va="center", fontsize=14)
    ax.text(
        0.23,
        0.5,
        text,
        va="center",
        fontsize=11,
        bbox=dict(boxstyle="round,pad=.7", facecolor=color, edgecolor="0.7"),
    )
fig.suptitle(
    "The same stored range does not establish the same scientific units", weight="bold"
)
save(
    fig,
    "figure01_transformations",
    "Encoding chains; Goldhill physical calibration is unresolved.",
)

fig, axs = plt.subplots(2, 5, figsize=(15, 6), sharex=True, sharey=True)
centers = (a["edges"][:-1] + a["edges"][1:]) / 2
for i, ax in enumerate(axs.flat):
    ax.step(centers, a["histograms"][i], where="mid", color="#276a84")
    ax.set_yscale("log")
    ax.set_title(f"{waves[i]} nm")
    ax.set_xlabel("Stored normalized DN")
    if i % 5 == 0:
        ax.set_ylabel("Observed pixels / 100-unit bin")
    ax.axvspan(0, 2, color="#b2182b", alpha=0.7)
fig.suptitle(
    "Goldhill: native positive-alpha observations; red strip is historical 0–2 interval",
    weight="bold",
)
fig.tight_layout(rect=(0, 0, 1, 0.93))
save(
    fig,
    "figure02_band_distributions",
    "All ten actual band distributions; footprint counts are native, not stride estimates.",
)

fig, axs = plt.subplots(1, 3, figsize=(13, 4))
red = rows[4]
axs[0].step(centers, a["histograms"][4], where="mid")
axs[0].set(
    xlabel="Stored normalized DN",
    ylabel="Observed pixels / bin",
    yscale="log",
    title="A: incorrect stored 0–2 filter",
)
axs[0].axvspan(0, 2, color="red")
axs[0].text(
    0.35, 0.8, "14 accepted pixels", transform=axs[0].transAxes, color="#b2182b"
)
axs[1].hist(red["A_values"], bins=np.linspace(0, 2, 11), color="#b2182b")
axs[1].set(
    xlabel="Stored normalized DN (0–2 only)",
    ylabel="Accepted pixels",
    title="Actual 14 red-band values",
)
axs[2].step(centers / 10000, a["fraction_histograms"][4], where="mid", color="#1b7837")
axs[2].set(
    xlabel="Normalized fraction (NOT reflectance)",
    ylabel="Observed pixels / bin",
    yscale="log",
    title="B: diagnostic fraction 0–1",
)
axs[2].text(
    0.25,
    0.8,
    "6,692,436 accepted\nC: physical calibration unresolved",
    transform=axs[2].transAxes,
    fontsize=10,
)
fig.tight_layout()
save(
    fig,
    "figure03_eligibility_distributions",
    "The 650 nm unit mismatch; B is diagnostic and cannot replace physical case C.",
)

fig, ax = plt.subplots(figsize=(8, 7))
ax.imshow(
    np.where(a["alpha"], 0.85, np.where(a["valid"], 0.45, np.nan)),
    cmap="gray",
    vmin=0,
    vmax=1,
    extent=(0, 3165, 2238, 0),
    interpolation="nearest",
)
points = np.asarray(r["historical_accepted_positions"][4])
ax.scatter(
    points[:, 1] + 0.5,
    points[:, 0] + 0.5,
    s=65,
    facecolors="none",
    edgecolors="#b2182b",
    linewidths=1.2,
    label="14 native accepted pixels (symbols enlarged)",
)
ax.set(
    xlabel="Native column (10 cm grid)",
    ylabel="Native row",
    title="Historical 650 nm selection: nearly the entire scene rejected",
)
ax.set_title("Historical 650 nm selection: nearly the entire scene rejected", pad=32)
ax.legend(loc="lower left", fontsize=9)
ax.text(
    0.01,
    1.01,
    "Light gray: positive alpha; dark gray: finite H5 outside alpha; white: missing",
    transform=ax.transAxes,
    fontsize=9,
)
save(
    fig,
    "figure04_historical_map",
    "Native accepted coordinates, enlarged symbols; contextual image decimated 8× without altering counts.",
)

fig, ax = plt.subplots(figsize=(8, 7))
background = np.where(a["alpha"], a["stored"] / 10000, np.nan)
im = ax.imshow(
    background,
    vmin=0,
    vmax=1,
    cmap="viridis",
    extent=(0, 3165, 2238, 0),
    interpolation="nearest",
)
fig.colorbar(
    im, ax=ax, label="Normalized fraction F = S/10,000; not physical reflectance"
)
ax.set(
    xlabel="Native column",
    ylabel="Native row",
    title="Unit-aware DIAGNOSTIC population: 6,692,436 red pixels",
)
ax.text(
    0.02,
    0.03,
    "All positive-alpha observations pass diagnostic 0–1.\nProduction physical BRDF: UNSUPPORTED.\nNative design rank: 1 of 3; no supported fit.",
    transform=ax.transAxes,
    color="white",
    fontsize=10,
    bbox=dict(facecolor="black", alpha=0.75),
)
save(
    fig,
    "figure05_diagnostic_map",
    "Actual red normalized fraction; no physical calibration, corrected image or invented geometry.",
)

fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(10)
A = np.array([d["historical_A"] for d in rows])
B = np.array([d["diagnostic_B"] for d in rows])
ax.bar(
    x - 0.2,
    np.maximum(A, 0.5),
    width=0.4,
    color="#b2182b",
    label="A: historical counts (same positive-alpha count)",
)
ax.bar(
    x + 0.2,
    B,
    width=0.4,
    color="#1b7837",
    label="B: diagnostic fraction; not production",
)
for i, n in enumerate(A):
    ax.text(i - 0.2, max(n, 0.5) * 1.5, str(n), ha="center", fontsize=10)
ax.set(
    yscale="log",
    ylim=(0.3, 5e8),
    xticks=x,
    xticklabels=waves,
    xlabel="Wavelength (nm)",
    ylabel="Native pixel count (log scale)",
    title="Historical selection versus compatible normalized-fraction selection",
)
ax.text(
    0.02,
    0.94,
    "C: physical eligibility UNRESOLVED, not zero. B = 6,692,436 in every band.",
    transform=ax.transAxes,
    fontsize=10,
)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, fontsize=9)
save(
    fig,
    "figure06_counts",
    "Zero at 862 nm is explicitly labeled; a half-count-height placeholder only locates that label on a log axis.",
)

fig, axs = plt.subplots(1, 3, figsize=(13, 4))
for ax, title, lows, highs, label in [
    (
        axs[0],
        "Drone stored numerical ranges",
        [v["stored_range"][0] for v in rows],
        [v["stored_range"][1] for v in rows],
        "Range-normalized DN",
    ),
    (
        axs[1],
        "Drone diagnostic numerical ranges",
        [v["stored_range"][0] / 10000 for v in rows],
        [v["stored_range"][1] / 10000 for v in rows],
        "Normalized fraction; not reflectance",
    ),
    (
        axs[2],
        "NEON calibrated physical ranges",
        [v["physical_min"] for v in r["neon"]["selected_bands"]],
        [v["physical_max"] for v in r["neon"]["selected_bands"]],
        "Fractional physical reflectance",
    ),
]:
    ax.vlines(waves, lows, highs, color="#276a84", lw=3)
    ax.scatter(waves, lows, s=12)
    ax.scatter(waves, highs, s=12)
    ax.set(title=title, xlabel="Nearest wavelength (nm)", ylabel=label)
fig.tight_layout()
save(
    fig,
    "figure07_numeric_ranges",
    "Whole native selected-band ranges; NEON is 10 nearest source wavelengths, not an empirical sensor calibration comparison.",
)
(HERE / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
