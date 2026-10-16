"""Reader-sized redraws from saved descriptive summaries; no new analysis."""

from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from spectralbridge.plant_spectral_comparison import _matched_products, _draw_product
from spectralbridge.plant_spectral_quantiles import _quantile_figure

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
OUT = BASE / "figures"
OUT.mkdir(exist_ok=True)
plt.rcParams.update(
    {
        "font.size": 13,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
        "svg.hashsalt": "lab-story-20261015",
    }
)

fig, ax = plt.subplots(1, 2, figsize=(13, 4.5), gridspec_kw={"width_ratios": [1.15, 1]})
plants, products, labels, _ = _matched_products(
    REPO / "artifacts/plant_spectral_atlas/comparisons/products", 10
)
main = plants.species.isin(labels).to_numpy()
delta = products["corr"][1][main] - products["raw"][1][main]
per_id = np.nanmedian(np.abs(delta), axis=1)
assert len(per_id) == 1886
ax[0].hist(per_id, bins=35, color="#356a7a")
ax[0].set_xlabel("Median absolute raw-to-corrected difference\n(stored spectral units)")
ax[0].set_ylabel("Polygon identities")
ax[0].set_title("A  Raw-to-corrected change", loc="left", weight="bold")
b = pd.read_csv(REPO / "provenance/sensor-pft-transfer/2026-10-14/brightness_audit.csv")
b = b[b.stage.eq("olioli")]
ax[1].bar(
    np.arange(7), b.median_ratio.to_numpy() - 1, bottom=1, color="#28758b", width=0.6
)
ax[1].axhline(1, color="#a45d3c", ls="--")
ax[1].set_ylim(0.94, 1.02)
ax[1].set_xticks(
    np.arange(7),
    ["Coastal", "Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"],
    rotation=35,
    ha="right",
)
ax[1].set_ylabel("Adjusted / undarkened OLI value")
ax[1].set_title("B  Fixed bandwise brightness gains", loc="left", weight="bold")
fig.tight_layout()
fig.savefig(
    OUT / "processing_effects.png",
    dpi=250,
    bbox_inches="tight",
    metadata={"Software": "SpectralBridge"},
)
plt.close(fig)

acc = pd.read_csv(REPO / "output/pdf/plant_spectral_review/accuracy_intervals.csv")
a = (
    acc[acc.scope.eq("ALL")]
    .set_index("stage")
    .loc[["raw", "corr", "olioli", "micasense"]]
)
fig, ax = plt.subplots(figsize=(10.5, 4.3))
y = a.accuracy.to_numpy() * 100
ax.bar(np.arange(4), y, color=["#578895", "#26708b", "#8a9b5d", "#999999"], width=0.6)
ax.errorbar(
    np.arange(4),
    y,
    yerr=np.array(
        [y - a.wilson_low.to_numpy() * 100, a.wilson_high.to_numpy() * 100 - y]
    ),
    fmt="none",
    color="#253b45",
    capsize=5,
)
ax.axhline(
    100 * 80 / 363, color="#a45d3c", ls="--", label="Majority-species baseline: 22.0%"
)
for i, v in enumerate(y):
    ax.text(i, v + 7, f"{v:.1f}%", ha="center", weight="bold")
ax.set_xticks(
    np.arange(4), ["Raw NEON", "Corrected NEON", "Synthetic OLI", "Archive MicaSense*"]
)
ax.set_ylabel("Top-1 species accuracy (%)")
ax.set_ylim(0, 38)
ax.legend(loc="upper right", frameon=False)
ax.set_title(
    "Early pooled quantile matcher | 363 held-out polygon identities",
    loc="left",
    weight="bold",
)
fig.tight_layout()
fig.savefig(
    OUT / "early_matching.png",
    dpi=250,
    bbox_inches="tight",
    metadata={"Software": "SpectralBridge"},
)
plt.close(fig)
# Select two alphabetical examples and enlarge labels instead of shrinking an atlas.
selected = ["Abies lasiocarpa", "Pinus contorta"]
fig, axes = plt.subplots(2, 4, figsize=(13.4, 5.8), sharey=True)
for i, species in enumerate(selected):
    for j, (stage, (wavelengths, values)) in enumerate(products.items()):
        ax = axes[i, j]
        mask = plants.species.eq(species).to_numpy()
        _draw_product(
            ax,
            stage,
            wavelengths,
            values[mask],
            excluded=((1340, 1450), (1790, 2000)),
            band_diagnostics=[],
        )
        ax.tick_params(labelsize=9)
        if i == 0:
            ax.set_title(
                {
                    "raw": "Raw NEON",
                    "corr": "Corrected NEON",
                    "olioli": "Synthetic OLI",
                    "micasense": "MicaSense: labels unverified",
                }[stage],
                fontsize=11,
            )
        if j == 0:
            ax.set_ylabel(
                species + "\n" + str(mask.sum()) + " polygon IDs", fontsize=10
            )
        if i == 1:
            ax.set_xlabel("Wavelength / export label (nm)", fontsize=9)
fig.supylabel("Spectral value (stored units)", fontsize=11)
fig.tight_layout()
fig.savefig(
    OUT / "empirical_traces.png",
    dpi=250,
    bbox_inches="tight",
    metadata={"Software": "SpectralBridge"},
)
plt.close(fig)

qroot = REPO / "artifacts/plant_spectral_atlas/quantile_models"
index = pd.read_parquet(qroot / "model_index.parquet")
full = index[index.level.eq("species") & index.partition.eq("full")]
subset = full[full.region.eq("ALL") & full.species.isin(selected)]
limits = (float(full.plot_min.min()) - 300, float(full.plot_max.max()) + 300)
fig = _quantile_figure(
    qroot,
    subset,
    selected,
    [
        ("Raw NEON", ("raw",)),
        ("Corrected NEON", ("corr",)),
        ("Synthetic OLI", ("olioli",)),
        ("MicaSense", ("micasense",)),
    ],
    "Exploratory boosted species signatures",
    limits,
    ((1340, 1450), (1790, 2000)),
)
fig.set_size_inches(13.4, 5.8)
fig.subplots_adjust(
    left=0.19, right=0.99, bottom=0.13, top=0.80, hspace=0.3, wspace=0.14
)
for ax in fig.axes:
    ax.tick_params(labelsize=9)
    if ax.get_title():
        ax.set_title(
            ax.get_title().replace(
                "MicaSense (export labels unverified)", "MicaSense: labels unverified"
            ),
            fontsize=11,
        )
    for text in ax.texts:
        text.set_fontsize(10)
        text.set_text(text.get_text().replace(" plants", " polygon IDs"))
for text in fig.texts:
    text.set_fontsize(11)
fig.savefig(
    OUT / "quantile_fans.png",
    dpi=250,
    bbox_inches="tight",
    metadata={"Software": "SpectralBridge"},
)
plt.close(fig)
quantile_sources = [
    "artifacts/plant_spectral_atlas/quantile_models/model_index.parquet",
    "src/spectralbridge/plant_spectral_quantiles.py",
] + [
    str((qroot / "checkpoints" / name).relative_to(REPO)) for name in subset.checkpoint
]
(OUT / "redraw_sources.json").write_text(
    json.dumps(
        {
            "processing_effects": [
                "artifacts/plant_spectral_atlas/comparisons/products/raw/plant_harmonized_spectra.parquet",
                "artifacts/plant_spectral_atlas/comparisons/products/corr/plant_harmonized_spectra.parquet",
                "artifacts/plant_spectral_atlas/comparisons/products/olioli/plant_harmonized_spectra.parquet",
                "artifacts/plant_spectral_atlas/comparisons/products/micasense/plant_harmonized_spectra.parquet",
                "src/spectralbridge/plant_spectral_comparison.py",
                "provenance/sensor-pft-transfer/2026-10-14/brightness_audit.csv",
            ],
            "quantile_fans": quantile_sources,
            "early_matching": [
                "output/pdf/plant_spectral_review/accuracy_intervals.csv"
            ],
            "majority_baseline": {"correct": 80, "N": 363},
        },
        indent=2,
    )
    + "\n"
)
print("Created four reader-sized descriptive redraws.")
