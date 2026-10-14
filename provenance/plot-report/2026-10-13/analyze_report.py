"""Read saved analysis in place and produce compact evidence/figures for the report."""

from pathlib import Path
from PIL import Image
import json
import hashlib
import math
import subprocess
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from spectralbridge.plant_spectral_comparison import _matched_products, _draw_product
from spectralbridge.plant_spectral_quantiles import _quantile_figure
from spectralbridge.plant_spectral_years import _year_site_figure
from spectralbridge.plant_quantile_overlays import _overlay_figure

ROOT = Path.cwd()
A = ROOT / "artifacts/plant_spectral_atlas"
REPORT_DIR = ROOT / "output/pdf/plant_spectral_review"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
F = REPORT_DIR / "figures"
F.mkdir(exist_ok=True)


def load(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wilson(k, n):
    z = 1.959963984540054
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [c - h, c + h]


def save(fig, name):
    fig.savefig(F / (name + ".png"), dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)


sources = [
    A / "audit.json",
    A / "manifest.json",
    A / "comparisons/comparison_audit.json",
    A / "comparisons/regional/regional_audit.json",
    A / "quantile_models/quantile_audit.json",
    A / "quantile_models/quantile_manifest.json",
    A / "quantile_models/model_index.parquet",
    A / "quantile_models/matching_validation.csv",
    A / "quantile_models/held_out_species_matches.csv",
    A / "quantile_models/held_out_individual_reference_matches.csv",
    A / "quantile_validation/matching_baselines.csv",
    A / "year_site_quantiles/year_site_audit.json",
    A / "year_site_quantiles/year_site_manifest.json",
    A / "year_site_quantiles/species_year_site_counts.csv",
]
# Validate authoritative manifests for every supplied figure/table they cover.
verified = 0
for manifest in [
    A / "manifest.json",
    A / "comparisons/comparison_manifest.json",
    A / "comparisons/regional/regional_manifest.json",
    A / "quantile_models/quantile_manifest.json",
    A / "year_site_quantiles/year_site_manifest.json",
]:
    if not manifest.exists():
        continue
    for name, h in load(manifest)["outputs"].items():
        p = manifest.parent / name
        if not p.is_file() or digest(p) != h:
            raise ValueError(f"Invalid recorded output {p}")
        verified += 1
sources += [p for p in A.rglob("*audit.json") if p not in sources]
plants, products, labels, _ = _matched_products(A / "comparisons/products", 10)
main = plants.species.isin(labels).to_numpy()
x = products["raw"][1]
y = products["corr"][1]
delta = y[main] - x[main]
finite = np.isfinite(delta)
correction = {
    "plants": int(main.sum()),
    "finite_pairs": int(finite.sum()),
    "median_absolute_change": float(np.nanmedian(abs(delta))),
    "mean_absolute_change": float(np.nanmean(abs(delta))),
    "max_absolute_change": float(np.nanmax(abs(delta))),
    "changed_fraction": float(np.mean(delta[finite] != 0)),
    "negative_raw_values": int(np.sum(x[main] < 0)),
    "negative_corrected_values": int(np.sum(y[main] < 0)),
}
# Reader-sized excerpts reproduce existing rendering semantics; no new fitting.
selected = ["Abies lasiocarpa", "Pinus contorta", "Pseudotsuga menziesii"]
fig, axes = plt.subplots(3, 4, figsize=(13, 7), sharey=True)
for i, species in enumerate(selected):
    for j, stage in enumerate(products):
        ax = axes[i, j]
        w, v = products[stage]
        mask = plants.species.eq(species).to_numpy()
        _draw_product(
            ax,
            stage,
            w,
            v[mask],
            excluded=((1340, 1450), (1790, 2000)),
            band_diagnostics=[],
        )
        ax.set_title(
            {
                "raw": "Raw NEON",
                "corr": "Corrected NEON",
                "olioli": "Derived OLI",
                "micasense": "MicaSense labels unverified",
            }[stage]
            if i == 0
            else "",
            fontsize=9,
        )
        ax.tick_params(labelsize=7)
        ax.spines[["top", "right"]].set_visible(False)
        if j == 0:
            ax.set_ylabel(species + "\nn=" + str(mask.sum()), fontsize=8)
        if i == 2:
            ax.set_xlabel("Supplied wavelength / export label (nm)", fontsize=7)
fig.suptitle(
    "Empirical plant traces: selected species (all-year summaries)", fontsize=13
)
fig.tight_layout()
save(fig, "empirical_examples")
# Correction diagnostic: one statistic per independent plant, not pixel pooling.
perplant = np.nanmedian(abs(delta), axis=1)
fig, ax = plt.subplots(figsize=(8, 3))
ax.hist(perplant, bins=35, color="#356a7a")
ax.set(
    xlabel="Within-plant median absolute raw-to-corrected difference (stored units)",
    ylabel="Independent plants",
    title="Correction magnitude, 1,886 selected plants",
)
save(fig, "correction_histogram")
idx = pd.read_parquet(A / "quantile_models/model_index.parquet")
full = idx[(idx.level == "species") & (idx.partition == "full")]
subset = full[(full.region == "ALL") & full.species.isin(selected)]
limits = (float(full.plot_min.min()) - 300, float(full.plot_max.max()) + 300)
columns = [
    ("Raw NEON", ("raw",)),
    ("Corrected NEON", ("corr",)),
    ("Derived Landsat OLI", ("olioli",)),
    ("Derived MicaSense", ("micasense",)),
]
fig = _quantile_figure(
    A / "quantile_models",
    subset,
    selected,
    columns,
    "Pooled species fits: selected examples",
    limits,
    ((1340, 1450), (1790, 2000)),
)
save(fig, "species_quantile_examples")
# One actual polygon example per selected species from NIWO.
ind = idx[
    (idx.level == "individual") & (idx.region == "NIWO") & idx.species.isin(selected)
]
ids = (
    ind[["species", "GlobalID"]]
    .drop_duplicates()
    .sort_values(["species", "GlobalID"])
    .groupby("species")
    .first()
    .GlobalID.tolist()
)
fig = _quantile_figure(
    A / "quantile_models",
    ind,
    ids,
    columns,
    "Selected NIWO individual-plant fits",
    limits,
    ((1340, 1450), (1790, 2000)),
    individual=True,
)
save(fig, "individual_examples")
# Audit the known tail issue directly against independent plant spectra.
m = idx[
    (idx.level == "species")
    & (idx.partition == "full")
    & (idx.region == "NIWO")
    & (idx.stage == "corr")
    & (idx.species == "Abies lasiocarpa")
].iloc[0]
with np.load(A / "quantile_models/checkpoints" / m.checkpoint) as d:
    w = d["wavelengths_nm"]
    q = d["quantiles"]
    fit = d["ordered_curves"]
regions = pd.read_parquet(
    A / "comparisons/regional/matched_plant_regions.parquet"
).set_index("GlobalID")
mask = (
    plants.species.eq("Abies lasiocarpa")
    & plants.GlobalID.map(regions.region).eq("NIWO")
).to_numpy()
vals = products["corr"][1][mask]
emp = np.nanquantile(vals[:, np.isfinite(vals).any(0)], q, axis=0)
empfull = np.full_like(fit, np.nan)
empfull[:, np.isfinite(vals).any(0)] = emp
j = int(np.flatnonzero(w == 425)[0])
tail = [
    {
        "quantile": float(q[k]),
        "fitted": float(fit[k, j]),
        "empirical": float(empfull[k, j]),
    }
    for k in [0, 4, 49, 94, 98]
]
fig, axes = plt.subplots(1, 2, figsize=(11, 3.5))
for percentile, color in [(50, "#32677a"), (95, "#cb8a34"), (99, "#9b3f32")]:
    k = percentile - 1
    axes[0].plot(w, fit[k], color=color, label=f"Fitted q{percentile}")
    axes[0].plot(w, empfull[k], color=color, ls=":", lw=2)
axes[0].set(
    xlabel="Wavelength (nm)",
    ylabel="Stored spectral value",
    title="NIWO Abies lasiocarpa: fitted vs empirical",
)
axes[0].legend(fontsize=7, ncol=3)
axes[1].plot(q * 100, fit[:, j], label="Boosted fit", color="#9b3f32")
axes[1].plot(q * 100, empfull[:, j], label="Empirical plants", color="#32677a")
axes[1].set(
    xlabel="Quantile (%)",
    ylabel="Stored spectral value",
    title="At 425 nm (32 independent plants)",
)
axes[1].legend(fontsize=8)
fig.tight_layout()
save(fig, "tail_fit_diagnostic")
# Saved holdout accuracy, with conditional binomial intervals (no new model selection).
scores = pd.read_csv(A / "quantile_models/held_out_species_matches.csv")
summary = pd.read_csv(A / "quantile_models/matching_validation.csv")
base = pd.read_csv(A / "quantile_validation/matching_baselines.csv")
intervals = []
for (scope, stage), g in scores.groupby(["scope", "stage"]):
    k = int(g.top1_correct.sum())
    n = len(g)
    lo, hi = wilson(k, n)
    intervals.append(
        {
            "scope": scope,
            "stage": stage,
            "correct": k,
            "n": n,
            "accuracy": k / n,
            "wilson_low": lo,
            "wilson_high": hi,
        }
    )
ci = pd.DataFrame(intervals)
ci.to_csv(REPORT_DIR / "accuracy_intervals.csv", index=False)
pool = (
    ci[ci.scope == "ALL"].set_index("stage").loc[["raw", "corr", "olioli", "micasense"]]
)
fig, ax = plt.subplots(figsize=(8, 3.2))
v = pool.accuracy.to_numpy() * 100
lo = pool.wilson_low.to_numpy() * 100
hi = pool.wilson_high.to_numpy() * 100
ax.bar(range(4), v, color=["#32677a", "#32677a", "#779465", "#b58d55"])
ax.errorbar(range(4), v, yerr=[v - lo, hi - v], fmt="none", color="#202020", capsize=4)
major = (
    base[
        (base.level == "species") & (base.scope == "ALL")
    ].majority_class_accuracy.iloc[0]
    * 100
)
ax.axhline(major, ls="--", color="#9b3f32", label=f"Majority baseline {major:.1f}%")
ax.set_xticks(range(4), ["Raw NEON", "Corrected NEON", "Derived OLI", "MicaSense*"])
ax.set(
    ylabel="Top-1 species accuracy (%)",
    ylim=(0, 35),
    title="Pooled holdout: 363 independent plant identities",
)
ax.legend(fontsize=8)
save(fig, "pooled_accuracy")
# Year/site excerpt: refitted models only, not all-year models.
yr = A / "year_site_quantiles"
yi = pd.read_parquet(yr / "model_index.parquet")
yc = pd.read_csv(yr / "species_year_site_counts.csv")
fig = _year_site_figure(yr, yi, yc, "corr", [2020, 2023], ["NIWO"], selected, limits)
fig._supylabel.set_visible(False)
fig.text(0.5, -0.025, "Spectral values in native stored units", ha="center", fontsize=9)
save(fig, "niwo_year_examples")
fig = _year_site_figure(
    yr,
    yi,
    yc,
    "corr",
    [2023],
    ["NIWO", "WREF", "YELL"],
    ["Juniperus communis", "Pinus contorta", "Pseudotsuga menziesii"],
    limits,
)
fig._supylabel.set_visible(False)
fig.text(0.5, -0.025, "Spectral values in native stored units", ha="center", fontsize=9)
save(fig, "site_2023_examples")
# Crops from original plot PNGs: geometry alone; do not resample analytical spectra.

for stage in ["corr", "olioli", "micasense"]:
    path = A / "quantile_overlays" / f"{stage}_individual_quantiles_descending.png"
    im = Image.open(path)
    W, H = im.size
    # Derive exact axes bounds from the same plotting helper; exclude neighboring cells/titles.
    grid = _overlay_figure(
        np.array([400.0, 500.0]), np.zeros((1, 99, 2)), ["Geometry only"], stage
    )
    for label, index in [("q99", 1), ("q50", 50)]:
        bounds = grid.axes[index].get_position()
        box = (
            round(bounds.x0 * W),
            round((1 - bounds.y1) * H),
            round(bounds.x1 * W),
            round((1 - bounds.y0) * H),
        )
        im.crop(box).save(F / f"{stage}_{label}_crop.png")
    plt.close(grid)
# Complete PDF inventory, including historical aliases, with file hashes.
inventory = []
for p in sorted(A.rglob("*.pdf")):
    if p.name.endswith(".tmp"):
        continue
    rel = str(p.relative_to(A))
    info = subprocess.check_output(["pdfinfo", str(p)], text=True)
    pages = int(
        next(
            line.split(":", 1)[1]
            for line in info.splitlines()
            if line.startswith("Pages:")
        )
    )
    inventory.append(
        {"path": rel, "pages": pages, "bytes": p.stat().st_size, "sha256": digest(p)}
    )
(REPORT_DIR / "figure_inventory.json").write_text(
    json.dumps(inventory, indent=2) + "\n"
)
# Compact data for report builder; every number traceable to a saved input.
rmse = (
    full.groupby("stage").empirical_quantile_rmse.agg(["median", "max"]).reset_index()
)
obs = idx[idx.level == "individual"].drop_duplicates("GlobalID")
year_counts = pd.read_csv(yr / "year_site_counts.csv")
eligible = (
    yc[yc.eligible]
    .groupby(["year", "site"])
    .agg(species=("species", "size"), plants=("plants", "sum"))
    .reset_index()
)
summary_data = {
    "date": "2026-10-13",
    "audit": load(A / "audit.json"),
    "comparison": load(A / "comparisons/comparison_audit.json"),
    "regional": load(A / "comparisons/regional/regional_audit.json"),
    "quantile": {
        k: v
        for k, v in load(A / "quantile_models/quantile_audit.json").items()
        if k not in ("config", "quantiles", "validation")
    },
    "year": {
        k: v
        for k, v in load(yr / "year_site_audit.json").items()
        if k not in ("inputs", "config")
    },
    "correction": correction,
    "tail_425nm": tail,
    "matching": summary.to_dict("records"),
    "baselines": base.to_dict("records"),
    "accuracy_intervals": intervals,
    "fit_rmse": rmse.to_dict("records"),
    "single_observation_plants": int((obs.spectra == 1).sum()),
    "individual_observation_quantiles": obs.spectra.quantile(
        [0, 0.25, 0.5, 0.75, 1]
    ).to_dict(),
    "year_eligible": eligible.to_dict("records"),
    "inventory": inventory,
    "verified_manifest_outputs": verified,
    "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in sources},
    "species_counts": pd.read_csv(A / "comparisons/matched_species_counts.csv").to_dict(
        "records"
    )
    if (A / "comparisons/matched_species_counts.csv").exists()
    else [],
}
(REPORT_DIR / "report_evidence.json").write_text(
    json.dumps(summary_data, indent=2) + "\n"
)
print(
    "Evidence complete:",
    len(inventory),
    "PDF artifacts;",
    verified,
    "manifest-covered outputs verified;",
    len(intervals),
    "accuracy intervals",
)
print("Correction", correction)
