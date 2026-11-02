"""Display-only stage comparisons; per-image stretches and ratio maps are labeled."""

from pathlib import Path
import json
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

EVIDENCE = Path(__file__).resolve().parent
WORK = Path("/private/tmp/goldhill-correction-diagnosis-20261030")
metadata = json.loads((EVIDENCE / "ablation.json").read_text())
wave = np.asarray(metadata["wavelengths_nm"])
rgb_bands = [int(np.argmin(abs(wave - w))) for w in [650, 560, 475]]
raw = np.load(WORK / "raw_preview.npy")
fig, axes = plt.subplots(2, 3, figsize=(15, 9), layout="constrained")
for ax, name, title in zip(
    axes.flat,
    ["raw", "topo_only", "brdf_only", "combined"],
    [
        "Original",
        "Topographic correction only",
        "BRDF correction only",
        "Combined (matches production)",
    ],
):
    image = np.load(WORK / (name + "_preview.npy"))
    rgb = image[:, :, rgb_bands].astype(float)
    valid = np.isfinite(rgb).all(2)
    for channel in range(3):
        lo, hi = np.percentile(rgb[:, :, channel][valid], [2, 90])
        rgb[:, :, channel] = np.clip(
            (rgb[:, :, channel] - lo) / max(hi - lo, 1e-12), 0, 1
        )
    rgb[~valid] = 1
    ax.imshow(rgb)
    ax.set_title(title)
    ax.axis("off")
for ax, name in zip(axes.flat[4:], ["topo_only", "brdf_only"]):
    image = np.load(WORK / (name + "_preview.npy"))
    red = rgb_bands[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        factor = image[:, :, red] / raw[:, :, red]
        logarithm = np.where(
            (factor > 0) & np.isfinite(factor), np.log10(factor), np.nan
        )
    rendered = ax.imshow(logarithm, cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_title(name + " red-band factor (log10)")
    ax.axis("off")
    fig.colorbar(
        rendered, ax=ax, label="−1: ×0.1; 0: unchanged; +1: ×10 (bounds display only)"
    )
fig.suptitle(
    "Goldhill stage isolation — original geometry and correction settings preserved\nRGB panels have independent 2–90% display stretches; numerical replay tested separately.",
    fontsize=14,
)
fig.savefig(EVIDENCE / "stage_isolation.png", dpi=170)
fig.savefig(EVIDENCE / "stage_isolation.pdf")
plt.close(fig)
