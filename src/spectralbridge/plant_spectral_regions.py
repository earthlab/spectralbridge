"""Site-resolved plant atlases backed by extraction-table provenance."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .plant_spectral_atlas import _file_hash
from .plant_spectral_comparison import (
    _STAGES,
    _draw_product,
    _finish_axis,
    _limits,
    _micasense_labels_unverified,
    _matched_products,
    _render_comparisons,
    _save,
)

_LOG = logging.getLogger(__name__)
_SITE = re.compile(r"^NEON_D\d{2}_([A-Z0-9]{4})_DP\d_")


def _site_from_table(value):
    """Read a site only from the NEON table basename, never an ancestor path."""
    if pd.isna(value) or not (
        match := _SITE.match(str(value).replace("\\", "/").split("/")[-1])
    ):
        raise ValueError(f"Cannot resolve NEON site from source table: {value}")
    return match[1]


def _regional_provenance(source):
    pf = pq.ParquetFile(source)
    required = ["GlobalID", "species", "source_parquet", "flight_id"]
    optional = [
        c for c in ("aop_site", "ecoregion", "polygon_id") if c in pf.schema_arrow.names
    ]
    meta = pf.read(columns=required + optional).to_pandas()
    # Map unique names first rather than applying a regex for every pixel.
    sites = {name: _site_from_table(name) for name in meta.source_parquet.unique()}
    meta["region"] = meta.source_parquet.map(sites)
    flight_sites = {name: _site_from_table(name) for name in meta.flight_id.unique()}
    if not (meta.region == meta.flight_id.map(flight_sites)).all():
        raise ValueError("Source table and flight site codes disagree")
    if "aop_site" in meta:
        populated = meta.aop_site.notna() & meta.aop_site.astype(str).str.strip().ne("")
        if not (meta.loc[populated, "aop_site"] == meta.loc[populated, "region"]).all():
            raise ValueError("Source table and aop_site metadata disagree")
    if (meta.groupby("GlobalID").region.nunique() > 1).any():
        raise ValueError("Independent plant identity spans multiple regions")
    labelled = meta.species.notna() & meta.species.astype(str).str.strip().ne("")
    if meta.loc[labelled, "GlobalID"].isna().any():
        raise ValueError("Labeled region observations lack plant identity")
    if (meta.loc[labelled].groupby("GlobalID").species.nunique() > 1).any():
        raise ValueError("Conflicting plant species labels in region provenance")
    source_rows = (
        meta.groupby(["region", "source_parquet", "flight_id"], sort=True)
        .size()
        .rename("pixel_rows")
        .reset_index()
    )
    labelled_counts = (
        meta.loc[labelled]
        .groupby(["region", "source_parquet", "flight_id"])
        .agg(
            labelled_pixels=("GlobalID", "size"),
            independent_labelled_plants=("GlobalID", "nunique"),
        )
        .reset_index()
    )
    source_rows = source_rows.merge(labelled_counts, how="left").fillna(
        {"labelled_pixels": 0, "independent_labelled_plants": 0}
    )
    plant_fields = ["GlobalID", "species", "region"]
    plant_rows = (
        meta.loc[labelled, plant_fields]
        .drop_duplicates("GlobalID")
        .sort_values("GlobalID")
        .reset_index(drop=True)
    )
    region_names = {}
    for region, group in meta.groupby("region"):
        if "ecoregion" in group:
            names = group.ecoregion.dropna().astype(str).str.strip()
            names = sorted(set(names[names.ne("")]))
            if len(names) > 1:
                raise ValueError(f"Site {region} has conflicting ecoregion names")
        else:
            names = []
        region_names[region] = names[0] if names else region
    return plant_rows, source_rows, region_names


def _verified_products(source_hash, products_dir):
    """Validate existing compact checkpoints; never reopen spectral pixel columns."""
    audits = {}
    hashes = {}
    for stage in _STAGES:
        directory = products_dir / stage
        manifest_path = directory / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        if manifest["identity"]["source_sha256"] != source_hash:
            raise ValueError(f"{stage} checkpoint belongs to a different source")
        if manifest["identity"]["options"].get("spectral_stage", "corr") != stage:
            raise ValueError(f"{stage} checkpoint stage disagrees with directory")
        for name, digest in manifest["outputs"].items():
            path = directory / name
            if not path.is_file() or _file_hash(path) != digest:
                raise ValueError(
                    f"Invalid {stage} compact checkpoint: {name}; rerun comparison analysis"
                )
            hashes[f"{stage}/{name}"] = digest
        hashes[f"{stage}/manifest.json"] = _file_hash(manifest_path)
        audits[stage] = json.loads((directory / "audit.json").read_text())
    if audits["raw"]["excluded_nm"] != audits["corr"]["excluded_nm"]:
        raise ValueError("Raw and corrected checkpoint gap policies differ")
    return audits, hashes


def _regional_counts(plants, min_plants):
    sample = (
        plants.groupby(["region", "species"], sort=True)
        .size()
        .rename("plants")
        .reset_index()
    )
    sample["eligible"] = (
        (sample.plants >= min_plants)
        & (sample.species.str.split().str.len() >= 2)
        & ~sample.species.str.casefold().isin(["other", "unidentified"])
    )
    return sample.sort_values(
        ["region", "species"], key=lambda values: values.str.casefold()
    )


def _cross_region_atlas(
    plants, products, labels, regions, names, out, *, dpi, excluded, limits, min_plants
):
    """Use explicit unavailable cells rather than hiding regional absence."""
    import matplotlib.pyplot as plt

    nrows = len(labels)
    fig, axes = plt.subplots(
        nrows,
        len(regions),
        figsize=(12.8, max(3, 1.35 * nrows)),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    height = fig.get_figheight()
    fig.subplots_adjust(
        left=0.20,
        right=0.99,
        bottom=0.48 / height,
        top=1 - 0.85 / height,
        hspace=0.20,
        wspace=0.10,
    )
    fig.text(
        0.20,
        1 - 0.07 / height,
        "Corrected NEON spectra by source-table site",
        fontsize=10,
        fontweight="bold",
        va="top",
    )
    diagnostic = []
    w, values = products["corr"]
    for row, species in enumerate(labels):
        for col, region in enumerate(regions):
            ax = axes[row, col]
            selected = (
                (plants.species == species) & (plants.region == region)
            ).to_numpy()
            n = int(selected.sum())
            if n >= min_plants:
                local = []
                _draw_product(
                    ax,
                    "corr",
                    w,
                    values[selected],
                    excluded=excluded,
                    band_diagnostics=local,
                )
                diagnostic.extend(
                    {"region": region, "species": species, **r} for r in local
                )
                ax.text(
                    0.99,
                    0.93,
                    f"n = {n} plants",
                    transform=ax.transAxes,
                    ha="right",
                    va="top",
                    fontsize=8,
                )
            else:
                message = (
                    "No sampled plants"
                    if n == 0
                    else f"n = {n}; below minimum {min_plants}"
                )
                ax.text(
                    0.5,
                    0.5,
                    message,
                    transform=ax.transAxes,
                    ha="center",
                    color=".4",
                    fontsize=9,
                )
                ax.set_facecolor(".97")
            _finish_axis(ax, limits, bottom=row == nrows - 1)
            if row == 0:
                ax.set_title(f"{region}\n{names[region]}", fontsize=10, pad=10)
            if col == 0:
                ax.text(
                    -0.22,
                    0.5,
                    species,
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontstyle="italic",
                    fontsize=9,
                )
    fig.supxlabel("Wavelength (nm)", fontsize=11, y=0.005 / height)
    fig.supylabel(
        "Corrected spectral value (native stored units)", fontsize=11, x=0.007
    )
    _save(fig, out / "corrected_by_region_rows", dpi)
    pd.DataFrame(diagnostic).to_parquet(
        out / "regional_corrected_medians.parquet", index=False
    )


def run_regional_plant_atlas(
    source, comparisons_dir, output_dir, *, min_plants_per_species=10, dpi=350
):
    """Reuse completed plant spectra for source-table site comparisons.

    Region codes must agree with flight IDs and populated aop_site metadata.
    GlobalID cannot span regions. Thresholds apply separately within each site;
    shared axes use full finite bounds across all eligible regional cohorts.
    The original source is read only for identity/provenance, not spectral values.
    """
    if min_plants_per_species < 1 or dpi < 300:
        raise ValueError("Positive threshold and dpi >= 300 required")
    source, comparisons_dir, out = Path(source), Path(comparisons_dir), Path(output_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    source_hash = _file_hash(source)
    audits, input_hashes = _verified_products(source_hash, comparisons_dir / "products")
    identity = {
        "source_sha256": source_hash,
        "products": input_hashes,
        "implementation_sha256": _file_hash(__file__),
        "plotting_sha256": _file_hash(
            Path(__file__).with_name("plant_spectral_comparison.py")
        ),
        "min_plants_per_species": min_plants_per_species,
        "dpi": dpi,
    }
    manifest_path = out / "regional_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["identity"] == identity and all(
            (out / name).is_file() and _file_hash(out / name) == digest
            for name, digest in manifest["outputs"].items()
        ):
            _LOG.info("Reusing checksum-verified regional figures")
            return json.loads((out / "regional_audit.json").read_text())
    plant_regions, source_rows, names = _regional_provenance(source)
    # A threshold of one here obtains all matched plants; per-site filtering follows.
    plants, products, _, _ = _matched_products(comparisons_dir / "products", 1)
    plants = plants.merge(
        plant_regions[["GlobalID", "region"]],
        on="GlobalID",
        how="left",
        validate="one_to_one",
    )
    if plants.region.isna().any():
        raise ValueError("Matched plants lack source-table region provenance")
    counts = _regional_counts(plants, min_plants_per_species)
    qualifying = counts[counts.eligible]
    if qualifying.empty:
        raise ValueError("No species meet the within-region threshold")
    labels = sorted(qualifying.species.unique(), key=str.casefold)
    regions = sorted(names)
    eligible_pairs = set(zip(qualifying.region, qualifying.species))
    eligible_plants = np.array(
        [(r, s) in eligible_pairs for r, s in zip(plants.region, plants.species)]
    )
    limits = _limits(
        plants.loc[eligible_plants].reset_index(drop=True),
        {s: (w, v[eligible_plants]) for s, (w, v) in products.items()},
        labels,
    )
    excluded = audits["corr"]["excluded_nm"]
    with TemporaryDirectory(prefix="regional-atlas-", dir=out.parent) as directory:
        pending = Path(directory)
        source_rows.to_csv(pending / "source_table_regions.csv", index=False)
        plants.to_parquet(pending / "matched_plant_regions.parquet", index=False)
        counts.to_csv(pending / "species_region_sample_sizes.csv", index=False)
        counts.pivot(index="species", columns="region", values="plants").fillna(
            0
        ).astype(int).to_csv(pending / "species_region_counts_wide.csv")
        summaries = []
        for region in regions:
            selected = (plants.region == region).to_numpy()
            region_plants = plants.loc[selected].reset_index(drop=True)
            region_products = {s: (w, v[selected]) for s, (w, v) in products.items()}
            region_labels = counts.loc[
                (counts.region == region) & counts.eligible, "species"
            ].tolist()
            region_out = pending / region
            region_out.mkdir()
            region_counts = counts[counts.region == region]
            region_counts.to_csv(region_out / "species_sample_sizes.csv", index=False)
            summary = {
                "region": region,
                "ecoregion": names[region],
                "matched_labelled_plants": len(region_plants),
                "eligible_species": len(region_labels),
                "main_plants": int(region_plants.species.isin(region_labels).sum()),
                "source_tables": int((source_rows.region == region).sum()),
            }
            summaries.append(summary)
            if not region_labels:
                _LOG.info(
                    "Site %s has no qualifying species; retaining counts only", region
                )
                continue
            _LOG.info(
                "Rendering %s: %s species, %s main plants",
                region,
                len(region_labels),
                summary["main_plants"],
            )
            _render_comparisons(
                region_plants,
                region_products,
                region_labels,
                region_out,
                dpi=dpi,
                excluded=excluded,
                limits=limits,
                region_label=f"{region} — {names[region]}",
            )
        import matplotlib.pyplot as plt

        with plt.rc_context(
            {"font.family": "DejaVu Sans", "pdf.fonttype": 42, "svg.fonttype": "none"}
        ):
            _cross_region_atlas(
                plants,
                products,
                labels,
                regions,
                names,
                pending,
                dpi=dpi,
                excluded=excluded,
                limits=limits,
                min_plants=min_plants_per_species,
            )
        pd.DataFrame(summaries).to_csv(pending / "region_summary.csv", index=False)
        audit = {
            "regions": summaries,
            "region_source": "Site code from NEON source_parquet basename; cross-checked flight_id and aop_site",
            "matched_labelled_plants": len(plants),
            "plants_without_region": 0,
            "cross_region_species": labels,
            "species_order": "Alphabetical scientific species name",
            "shared_y_limits": limits,
            "min_plants_per_species_per_region": min_plants_per_species,
            "cross_region_policy": "Plot only species/site cohorts meeting threshold; annotate absence and small samples",
            "replication": "One GlobalID per plant; no GlobalID spans sites; inherited equal-observation spectra",
            "spectral_pixel_reads": 0,
            "coordinate_status": {
                s: (
                    "unverified_export_labels"
                    if s == "micasense" and _micasense_labels_unverified(w)
                    else "supplied_grid"
                )
                for s, (w, _) in products.items()
            },
            "sensor_provenance": "Darkened OLI and MicaSense representations derived from NEON",
            "sensor_plotting": "Visual band-center connections only; OLI solid/MicaSense dashed; no interpolated samples",
        }
        (pending / "regional_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        if _file_hash(source) != source_hash:
            raise ValueError("Source changed during regional analysis")
        # Validate that compact products also remained unchanged while rendering.
        _, final_hashes = _verified_products(source_hash, comparisons_dir / "products")
        if final_hashes != input_hashes:
            raise ValueError("Compact plant products changed during regional rendering")
        outputs = {
            str(p.relative_to(pending)): _file_hash(p)
            for p in pending.rglob("*")
            if p.is_file()
        }
        out.mkdir(parents=True, exist_ok=True)
        for path in pending.rglob("*"):
            if path.is_file():
                target = out / path.relative_to(pending)
                target.parent.mkdir(parents=True, exist_ok=True)
                path.replace(target)
        temporary = manifest_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps({"identity": identity, "outputs": outputs}, indent=2) + "\n"
        )
        temporary.replace(manifest_path)
    return json.loads(json.dumps(audit))
