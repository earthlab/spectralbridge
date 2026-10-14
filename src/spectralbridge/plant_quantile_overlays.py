"""Descending quantile overlays from verified individual-plant checkpoints."""

from pathlib import Path
import json
import logging

import numpy as np
import pandas as pd

from .plant_spectral_atlas import _file_hash
from .plant_spectral_comparison import _micasense_labels_unverified

_LOG = logging.getLogger(__name__)


def _overlay_figure(wavelengths, curves, species, stage, *, group_name="species"):
    """One collection per percentile, with one unchanged trace per GlobalID."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.lines import Line2D

    if curves.shape != (len(species), 99, len(wavelengths)):
        raise ValueError("Expected every plant's 1–99% curves on one grid")
    unverified = stage == "micasense" and _micasense_labels_unverified(wavelengths)
    labels = sorted(set(species))
    palette = list(plt.get_cmap("tab20").colors) + list(plt.get_cmap("Set2").colors)
    colors = {name: palette[i % len(palette)] for i, name in enumerate(labels)}
    fig, axes = plt.subplots(10, 10, figsize=(25, 24), sharex=True, sharey=True)
    fig.subplots_adjust(
        left=0.04, right=0.995, bottom=0.095, top=0.95, hspace=0.32, wspace=0.14
    )
    low, high = float(np.nanmin(curves)), float(np.nanmax(curves))
    pad = max((high - low) * 0.03, 1)
    for percentile, ax in zip(range(100, 0, -1), axes.flat):
        ax.set_title(f"{percentile}% quantile", fontsize=9)
        ax.set_xlim(float(wavelengths[0]), float(wavelengths[-1]))
        ax.set_ylim(low - pad, high + pad)
        if stage in ("raw", "corr"):
            ax.set_xticks([500, 1500, 2500])
        else:
            from matplotlib.ticker import MaxNLocator

            ax.xaxis.set_major_locator(MaxNLocator(3))
        ax.tick_params(labelsize=6)
        ax.spines[["top", "right"]].set_visible(False)
        if percentile == 100:
            ax.text(
                0.5,
                0.5,
                "Not fitted\nModels cover 1–99%",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=10,
            )
            continue
        values = curves[:, percentile - 1, :]
        segments = np.stack(
            [np.broadcast_to(wavelengths, values.shape), values], axis=-1
        )
        ax.add_collection(
            LineCollection(
                segments,
                colors=[colors[s] for s in species],
                linewidths=0.32,
                alpha=0.14,
                rasterized=True,
                linestyles="--" if stage == "micasense" else "-",
            )
        )
        for start, stop in (
            [(1340, 1450), (1790, 2000)] if stage in ("raw", "corr") else []
        ):
            ax.axvspan(start, stop, color=".94", zorder=-1)
    title = {
        "corr": "Corrected NEON",
        "raw": "Raw NEON",
        "olioli": "Landsat OLI (derived)",
        "micasense": "MicaSense (derived; export labels unverified)"
        if unverified
        else "MicaSense (derived)",
    }[stage]
    fig.suptitle(
        f"{title}: one fitted quantile per plant in each subplot", fontsize=18, y=0.985
    )
    fig.text(
        0.5,
        0.963,
        f"{len(species):,} individual plants • {len(labels)} {group_name} • descending 100 → 1 • shared full-range axes",
        ha="center",
        fontsize=12,
    )
    fig.supxlabel(
        "Supplied export label (nm; physical wavelengths unverified)"
        if unverified
        else "Wavelength (nm)",
        y=0.073,
        fontsize=12,
    )
    fig.supylabel("Spectral value (native stored units)", x=0.008, fontsize=12)
    fig.legend(
        handles=[Line2D([], [], color=colors[s], label=s, linewidth=2) for s in labels],
        loc="lower center",
        ncol=8,
        fontsize=8,
        frameon=False,
        bbox_to_anchor=(0.5, 0.022),
    )
    fig.text(
        0.5,
        0.009,
        "Exploratory fits; outer quantiles can underfit. Faint overlays are not normalized densities; curves are not new plants.",
        ha="center",
        fontsize=10,
    )
    return fig


def run_quantile_overlays(models, output, *, stages=("corr", "raw")):
    """Render 100 slots (100 unfitted, then 99–1) without changing any fit."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root, out = Path(models), Path(output)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "quantile_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    source_manifest_hash = _file_hash(manifest_path)
    index_path = root / "model_index.parquet"
    if _file_hash(index_path) != manifest["outputs"]["model_index.parquet"]:
        raise ValueError("Model index checksum mismatch")
    index = pd.read_parquet(index_path)
    report = {
        "source_manifest_sha256": source_manifest_hash,
        "implementation_sha256": _file_hash(__file__),
        "percentiles_descending": list(range(100, 0, -1)),
        "unfitted_percentiles": [100],
        "stages": {},
    }
    for stage in stages:
        if stage not in ("raw", "corr", "olioli", "micasense"):
            raise ValueError("Unsupported spectral stage")
        selected = index[
            (index.level == "individual")
            & (index.partition == "full")
            & (index.stage == stage)
        ].sort_values(["species", "GlobalID"])
        if selected.empty or selected.GlobalID.duplicated().any():
            raise ValueError("Expected unique nonempty individual-plant references")
        arrays, wavelengths = [], None
        for n, row in enumerate(selected.itertuples(), 1):
            path = root / "checkpoints" / row.checkpoint
            if _file_hash(path) != manifest["outputs"][str(path.relative_to(root))]:
                raise ValueError(f"Checkpoint checksum mismatch: {row.checkpoint}")
            with np.load(path) as saved:
                w, q = saved["wavelengths_nm"], saved["quantiles"]
                if not np.array_equal(q, np.arange(1, 100) / 100):
                    raise ValueError("Expected fitted quantiles 1–99%")
                if wavelengths is not None and not np.array_equal(wavelengths, w):
                    raise ValueError("Individual grids disagree")
                wavelengths = w.copy()
                arrays.append(saved["ordered_curves"].copy())
            if n % 250 == 0:
                _LOG.info("Loaded %s %s/%s plants", stage, n, len(selected))
        curves = np.stack(arrays)
        del arrays
        fig = _overlay_figure(wavelengths, curves, selected.species.tolist(), stage)
        for extension in ("pdf", "png"):
            path = out / f"{stage}_individual_quantiles_descending.{extension}"
            temporary = path.with_suffix(path.suffix + ".tmp")
            _LOG.info("Saving %s", path.name)
            fig.savefig(temporary, format=extension, dpi=200, facecolor="white")
            temporary.replace(path)
        plt.close(fig)
        report["stages"][stage] = {
            "plants": len(selected),
            "species": selected.species.nunique(),
            "curves_per_populated_subplot": len(selected),
            "curve_source": "ordered_curves",
            "coordinate_status": "unverified_export_labels"
            if stage == "micasense" and _micasense_labels_unverified(wavelengths)
            else "supplied_grid",
            "GlobalIDs": selected.GlobalID.tolist(),
        }
        del curves
    if _file_hash(manifest_path) != source_manifest_hash:
        raise ValueError("Source manifest changed during rendering")
    report["outputs"] = {
        p.name: _file_hash(p) for p in out.iterdir() if p.suffix in ("pdf", "png")
    }
    (out / "overlay_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
