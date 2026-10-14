"""Matched independent-plant layouts for NEON and derived sensor products."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import warnings

import numpy as np
import pandas as pd

from .plant_spectral_atlas import _file_hash, run_plant_spectral_atlas

_LOG = logging.getLogger(__name__)
_STAGES = ("raw", "corr", "olioli", "micasense")
_TITLES = {
    "raw": "Raw NEON",
    "corr": "Corrected NEON",
    "olioli": "Landsat OLI-like (derived, darkened)",
    "micasense": "Drone MicaSense-like (derived, darkened)",
}
_COLORS = {
    "raw": "#355c70",
    "corr": "#355c70",
    "olioli": "#355c70",
    "micasense": "#8a6544",
}
_LINESTYLES = {"olioli": "-", "micasense": "--"}


def _matched_products(root, min_plants):
    """Intersect plant identities, never positional rows or pixel-count weights."""
    tables = {
        s: pd.read_parquet(root / s / "plant_harmonized_spectra.parquet").set_index(
            "GlobalID"
        )
        for s in _STAGES
    }
    ids = set.intersection(*(set(t.index[t.retained]) for t in tables.values()))
    ids = sorted(ids)
    if not ids:
        raise ValueError("No matched independent plants across all products")
    plants = (
        tables["corr"]
        .loc[ids, ["species", "flight_observations", "pixel_count"]]
        .reset_index()
    )
    products = {}
    for stage, table in tables.items():
        table = table.loc[ids]
        if not np.array_equal(table.species.to_numpy(), plants.species.to_numpy()):
            raise ValueError("Species conflict across products")
        columns = [c for c in table if c.startswith(f"{stage}_wl")]
        wavelengths = np.array(
            [float(c.split("_wl")[1].removesuffix("nm")) for c in columns]
        )
        if np.any(np.diff(wavelengths) <= 0):
            raise ValueError("Product wavelength order is invalid")
        products[stage] = (wavelengths, table[columns].to_numpy(float))
    sample = plants.groupby("species").agg(plants=("GlobalID", "size")).reset_index()
    sample["main_panel"] = (
        (sample.plants >= min_plants)
        & (sample.species.str.split().str.len() >= 2)
        & ~sample.species.str.casefold().isin(["other", "unidentified"])
    )
    sample = sample.sort_values("species", key=lambda values: values.str.casefold())
    labels = sample.loc[sample.main_panel, "species"].tolist()
    if not labels:
        raise ValueError("No species meet the matched-plant threshold")
    diagnostic = sample.copy()
    for stage in _STAGES:
        diagnostic[f"{stage}_available_plants"] = diagnostic.species.map(
            tables[stage].groupby("species").retained.sum()
        )
    return plants, products, labels, diagnostic


def _draw_product(ax, stage, wavelengths, values, *, excluded, band_diagnostics):
    """Plant traces at supported NEON wavelengths or discrete sensor band centers."""
    color = _COLORS[stage]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        q = np.nanquantile(values, [0.25, 0.5, 0.75], axis=0)
    if stage in ("raw", "corr"):
        ax.plot(wavelengths, values.T, color=color, alpha=0.09, linewidth=0.4)
        ax.fill_between(wavelengths, q[0], q[2], color=color, alpha=0.12)
        ax.plot(wavelengths, q[1], color="#142f40", linewidth=1.05)
        for lo, hi in excluded:
            ax.axvspan(lo, hi, color=".93", zorder=-1)
    else:
        # User-requested visual connections only: no new band samples are created.
        # Keeping NaNs in each trace lets Matplotlib break missing band segments.
        style = _LINESTYLES[stage]
        ax.plot(
            wavelengths,
            values.T,
            color=color,
            alpha=0.09,
            linewidth=0.4,
            linestyle=style,
        )
        ax.plot(wavelengths, q[1], color=color, linewidth=1.15, linestyle=style)
        ax.errorbar(
            wavelengths,
            q[1],
            yerr=np.array([q[1] - q[0], q[2] - q[1]]),
            fmt="none",
            color=color,
            alpha=0.45,
            elinewidth=0.75,
            capsize=1.5,
        )
    band_diagnostics.extend(
        {
            "stage": stage,
            "wavelength_nm": float(w),
            "plants": int(np.isfinite(values[:, i]).sum()),
            "median": float(q[1, i]) if np.isfinite(q[1, i]) else None,
        }
        for i, w in enumerate(wavelengths)
    )


def _limits(plants, products, labels):
    selected = plants.species.isin(labels).to_numpy()
    lo = min(float(np.nanmin(v[selected])) for _, v in products.values())
    hi = max(float(np.nanmax(v[selected])) for _, v in products.values())
    margin = (hi - lo) * 0.04 or 1
    return lo - margin, hi + margin


def _finish_axis(ax, limits, *, bottom):
    ax.set_xlim(385, 2510)
    ax.set_ylim(*limits)
    ax.set_xticks([500, 1000, 1500, 2000, 2500])
    ax.tick_params(labelsize=7, labelbottom=bottom)
    ax.spines[["top", "right"]].set_visible(False)


def _save(fig, destination, dpi):
    import matplotlib.pyplot as plt

    for extension in ("pdf", "svg", "png"):
        _LOG.info("Saving %s.%s", destination.name, extension)
        fig.savefig(destination.with_suffix("." + extension), dpi=dpi)
    plt.close(fig)


def _row_layout(
    plants,
    products,
    labels,
    columns,
    destination,
    *,
    dpi,
    excluded,
    limits,
    region_label=None,
):
    import matplotlib.pyplot as plt

    unverified = "micasense" in products and _micasense_labels_unverified(
        products["micasense"][0]
    )
    nrows = len(labels)
    fig, axes = plt.subplots(
        nrows,
        3,
        figsize=(12.8, max(3, nrows * 1.35)),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    height = fig.get_figheight()
    fig.subplots_adjust(
        left=0.20,
        right=0.99,
        bottom=0.48 / height,
        top=1 - 0.65 / height,
        hspace=0.20,
        wspace=0.10,
    )
    if region_label:
        fig.text(
            0.20,
            1 - 0.07 / height,
            region_label,
            fontsize=9,
            fontweight="bold",
            va="top",
        )
    diagnostics = []
    for row, label in enumerate(labels):
        selected = (plants.species == label).to_numpy()
        for col, (title, stages) in enumerate(columns):
            ax = axes[row, col]
            for stage in stages:
                w, values = products[stage]
                local = []
                _draw_product(
                    ax,
                    stage,
                    w,
                    values[selected],
                    excluded=excluded,
                    band_diagnostics=local,
                )
                diagnostics.extend(
                    {"species": label, "column": title, **r} for r in local
                )
            _finish_axis(ax, limits, bottom=row == nrows - 1)
            if row == 0:
                heading = title
                if unverified and "micasense" in stages:
                    heading = (
                        "MicaSense-like (export labels unverified)"
                        if len(stages) == 1
                        else "Darkened (MS labels unverified)"
                    )
                ax.set_title(heading, fontsize=10, pad=12)
            if col == 0:
                ax.text(
                    -0.22,
                    0.58,
                    label,
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontstyle="italic",
                    fontsize=9,
                )
                ax.text(
                    -0.22,
                    0.32,
                    f"n = {selected.sum():,} plants",
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontsize=8,
                )
    fig.supxlabel(
        "Wavelength / supplied export label (nm)" if unverified else "Wavelength (nm)",
        fontsize=11,
        y=0.005 / height,
    )
    fig.supylabel("Spectral value (native stored units)", fontsize=11, x=0.007)
    fig.text(
        0.99,
        1 - 0.07 / height,
        (
            "Band-center connections only; OLI solid, MS dashed; MS labels unverified"
            if unverified
            else "Band-center traces: OLI solid; MicaSense dashed. Connections are visual only."
        ),
        ha="right",
        va="top",
        fontsize=8,
    )
    _save(fig, destination, dpi)
    return diagnostics


def _atlas_block(
    fig, plants, products, labels, stages, title, *, excluded, limits, region_label=None
):
    unverified = "micasense" in stages and _micasense_labels_unverified(
        products["micasense"][0]
    )
    if unverified:
        title = "Darkened traces (MS export labels unverified)"
    cols = 1
    rows = int(np.ceil(len(labels) / cols))
    axes = fig.subplots(rows, cols, sharex=True, sharey=True, squeeze=False)
    height = fig.bbox.height / fig.dpi
    fig.subplots_adjust(
        left=0.10,
        right=0.985,
        bottom=0.48 / height,
        top=1 - (0.80 if region_label else 0.60) / height,
        hspace=0.52,
        wspace=0.16,
    )
    title = f"{region_label}\n{title}" if region_label else title
    fig.suptitle(
        title, fontsize=11 if region_label else 13, y=1 - 0.06 / height, va="top"
    )
    diagnostics = []
    for index, (ax, label) in enumerate(zip(axes.flat, labels)):
        selected = (plants.species == label).to_numpy()
        for stage in stages:
            w, values = products[stage]
            _draw_product(
                ax,
                stage,
                w,
                values[selected],
                excluded=excluded,
                band_diagnostics=diagnostics,
            )
        ax.set_title(
            f"{label}\nn = {selected.sum():,} plants",
            fontstyle="italic",
            fontsize=8,
            pad=3,
        )
        _finish_axis(ax, limits, bottom=index // cols == rows - 1)
    for ax in list(axes.flat)[len(labels) :]:
        ax.remove()
    fig.supxlabel(
        "Wavelength / supplied export label (nm)" if unverified else "Wavelength (nm)",
        fontsize=10,
        y=0.005 / height,
    )
    fig.supylabel("Spectral value (native stored units)", fontsize=10, x=0.01)


def _render_comparisons(
    plants, products, labels, out, *, dpi, excluded, limits=None, region_label=None
):
    import matplotlib.pyplot as plt

    labels = sorted(labels, key=str.casefold)
    if limits is None:
        limits = _limits(plants, products, labels)
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    ):
        stages_columns = [
            ("Raw NEON", ("raw",)),
            ("Corrected NEON", ("corr",)),
            ("Darkened derived sensor bands", ("olioli", "micasense")),
        ]
        diagnostic = _row_layout(
            plants,
            products,
            labels,
            stages_columns,
            out / "raw_corrected_darkened_rows",
            dpi=dpi,
            excluded=excluded,
            limits=limits,
            region_label=region_label,
        )
        sensors_columns = [
            (_TITLES["olioli"], ("olioli",)),
            (_TITLES["corr"], ("corr",)),
            (_TITLES["micasense"], ("micasense",)),
        ]
        _row_layout(
            plants,
            products,
            labels,
            sensors_columns,
            out / "landsat_neon_drone_rows",
            dpi=dpi,
            excluded=excluded,
            limits=limits,
            region_label=region_label,
        )
        blocks = [
            ("raw", ("raw",), "Raw NEON"),
            ("corrected", ("corr",), "Corrected NEON"),
            (
                "darkened",
                ("olioli", "micasense"),
                "Darkened band-center traces: OLI solid, MicaSense dashed",
            ),
        ]
        height = max(3, len(labels) * 1.35)
        for name, stages, title in blocks:
            fig = plt.figure(figsize=(7.2, height))
            _atlas_block(
                fig,
                plants,
                products,
                labels,
                stages,
                title,
                excluded=excluded,
                limits=limits,
                region_label=region_label,
            )
            _save(fig, out / f"{name}_atlas", dpi)
        # Preserve the established filename, now with one alphabetical species row
        # aligned across the three stage columns, rather than separate atlas grids.
        for extension in ("pdf", "svg", "png"):
            shutil.copyfile(
                out / f"raw_corrected_darkened_rows.{extension}",
                out / f"three_panel_atlas.{extension}",
            )
    pd.DataFrame(diagnostic).to_parquet(
        out / "plotted_species_medians.parquet", index=False
    )
    return limits


def run_plant_comparison_atlas(
    source,
    output_dir,
    *,
    min_plants_per_species=10,
    dpi=350,
    excluded=((1340, 1450), (1790, 2000)),
):
    """Render alphabetical species rows using matched independent plants.

    Uses raw/corr NEON spectra, darkened olioli and micasense derived bands.
    Broadband band centers are retained exactly, connected visually without adding
    interpolated samples; NaN bands break individual traces.
    All layouts use alphabetical species order, plant cohorts and full y limits.
    Each species occupies its own row in three-column comparisons and single-product atlases.
    Product tables/checkpoints are compact observation/plant spectra, not pixels.
    """
    if min_plants_per_species < 1 or dpi < 300:
        raise ValueError("Positive plant threshold and dpi >= 300 required")
    source, out = Path(source), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    identity = {
        "source_sha256": _file_hash(source),
        "implementation_sha256": _file_hash(__file__),
        "aggregation_sha256": _file_hash(
            Path(__file__).with_name("plant_spectral_atlas.py")
        ),
        "min_plants_per_species": min_plants_per_species,
        "dpi": dpi,
        "excluded": excluded,
    }
    identity = json.loads(json.dumps(identity))
    manifest_path = out / "comparison_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["identity"] == identity and all(
            (out / name).is_file() and _file_hash(out / name) == digest
            for name, digest in manifest["outputs"].items()
        ):
            _LOG.info("Reusing checksum-verified comparison figures")
            return json.loads((out / "comparison_audit.json").read_text())
    # Each stage reuses its independently verified aggregation checkpoint.
    stage_audits = {}
    for stage in _STAGES:
        _LOG.info("Preparing independent-plant product: %s", stage)
        stage_audits[stage] = run_plant_spectral_atlas(
            source,
            out / "products" / stage,
            spectral_stage=stage,
            make_figures=False,
            min_plants_per_species=min_plants_per_species,
            grid_step_nm=5 if stage in ("raw", "corr") else None,
            excluded=excluded if stage in ("raw", "corr") else (),
        )
    plants, products, labels, sample = _matched_products(
        out / "products", min_plants_per_species
    )
    with TemporaryDirectory(prefix="comparison-", dir=out.parent) as directory:
        pending = Path(directory)
        sample.to_csv(pending / "matched_species_sample_sizes.csv", index=False)
        plants.to_parquet(pending / "matched_plants.parquet", index=False)
        limits = _render_comparisons(
            plants, products, labels, pending, dpi=dpi, excluded=excluded
        )
        audit = {
            "species": labels,
            "main_species_count": len(labels),
            "matched_labelled_plants": len(plants),
            "main_plants": int(plants.species.isin(labels).sum()),
            "stage_retained_plants": {
                s: a["plants_retained"] for s, a in stage_audits.items()
            },
            "plants_unmatched_by_stage": {
                s: a["plants_retained"] - len(plants) for s, a in stage_audits.items()
            },
            "coordinate_status": {
                s: (
                    "unverified_export_labels"
                    if s == "micasense" and _micasense_labels_unverified(w)
                    else "supplied_grid"
                )
                for s, (w, _) in products.items()
            },
            "stages": list(_STAGES),
            "band_counts": {s: len(w) for s, (w, _) in products.items()},
            "excluded_neon_nm": excluded,
            "shared_y_limits": limits,
            "replication": "One GlobalID plant per trace/point set; equal flight-observation medians",
            "sensor_provenance": "OLI and MicaSense are derived NEON products, not independent acquisitions",
            "sensor_plotting": "Visual connections between supplied export coordinates; OLI solid/MicaSense dashed; band-level IQR; no new samples; check coordinate_status before physical interpretation",
            "species_order": "Alphabetical scientific species name",
            "layout": "One species per row; raw/corrected/darkened aligned in three columns",
            "layouts": [
                "raw_corrected_darkened_rows",
                "three_panel_atlas",
                "landsat_neon_drone_rows",
            ],
            "standalone_atlases": ["raw_atlas", "corrected_atlas", "darkened_atlas"],
        }
        (pending / "comparison_audit.json").write_text(
            json.dumps(audit, indent=2) + "\n"
        )
        if _file_hash(source) != identity["source_sha256"]:
            raise ValueError("Source changed during comparison analysis")
        outputs = {p.name: _file_hash(p) for p in pending.iterdir()}
        outputs.update(
            {
                str(p.relative_to(out)): _file_hash(p)
                for p in (out / "products").rglob("*")
                if p.is_file()
            }
        )
        for p in pending.iterdir():
            p.replace(out / p.name)
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps({"identity": identity, "outputs": outputs}, indent=2) + "\n"
        )
        temporary.replace(manifest_path)
    return json.loads(json.dumps(audit))


def _micasense_labels_unverified(wavelengths):
    """Detect extra band labels padded after the legacy five-band fallback.

    This flags a provenance problem; it does not infer replacement wavelengths.
    """
    from .exports.schema_utils import SENSOR_WAVELENGTHS_NM

    w = np.asarray(wavelengths, float)
    legacy = np.asarray(SENSOR_WAVELENGTHS_NM["micasense"], float)
    if len(w) <= len(legacy):
        return False
    expected = np.concatenate(
        [legacy, legacy[-1] + np.arange(1, len(w) - len(legacy) + 1)]
    )
    return bool(np.array_equal(w, expected))
