"""Acquisition-year/site boosted species panels from compact plant-flight spectra."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
import json
import logging
import re

import numpy as np
import pandas as pd

from .plant_spectral_atlas import _file_hash
from .plant_spectral_comparison import _save, _micasense_labels_unverified
from .plant_spectral_regions import _site_from_table, _regional_counts
from .plant_spectral_quantiles import (
    QuantileModelConfig,
    _model_inputs,
    _fit_checkpoint,
    _draw_quantile_panel,
)

_LOG = logging.getLogger(__name__)
_DATE = re.compile(r"_(\d{8})_(?:directional_reflectance|\d{6}_reflectance)(?:_|$)")


def _acquisition_group(name):
    site = _site_from_table(name)
    basename = str(name).replace("\\", "/").split("/")[-1]
    match = _DATE.search(basename)
    if not match:
        raise ValueError(f"Cannot resolve acquisition date: {name}")
    date = pd.to_datetime(match[1], format="%Y%m%d", errors="raise")
    return site, date.year


def _year_plant_spectra(observations, stage):
    """Equal observation medians within GlobalID/year; never reuse all-year medians."""
    table = observations.copy()
    groups = {name: _acquisition_group(name) for name in table.source_parquet.unique()}
    flights = {name: _acquisition_group(name) for name in table.flight_id.unique()}
    if any(
        groups[row.source_parquet] != flights[row.flight_id]
        for row in table.itertuples()
    ):
        raise ValueError("Source table and flight acquisition year/site disagree")
    table["site"] = table.source_parquet.map(lambda name: groups[name][0])
    table["year"] = table.source_parquet.map(lambda name: groups[name][1])
    if "aop_site" in table:
        populated = table.aop_site.notna() & table.aop_site.astype(str).str.strip().ne(
            ""
        )
        if not table.loc[populated, "aop_site"].eq(table.loc[populated, "site"]).all():
            raise ValueError("Source site and aop_site disagree")
    if (
        table.GlobalID.isna().any()
        or table.groupby("GlobalID").species.nunique().gt(1).any()
    ):
        raise ValueError("Missing plant identities or conflicting species")
    if table.groupby("GlobalID").site.nunique().gt(1).any():
        raise ValueError("Plant identity spans sites")
    observation_key = ["GlobalID", "flight_id", "source_image", "polygon_id"]
    if table.duplicated(observation_key).any():
        raise ValueError("Duplicate compact flight/polygon observations")
    columns = [c for c in table if c.startswith(stage + "_wl")]
    records = []
    for (site, year, species, plant), group in table.groupby(
        ["site", "year", "species", "GlobalID"], sort=True
    ):
        values = group[columns].to_numpy(float)
        median = np.ma.median(np.ma.masked_invalid(values), axis=0).filled(np.nan)
        if np.isfinite(median).sum() < 2:
            continue
        records.append(
            {
                "site": site,
                "year": int(year),
                "species": species,
                "GlobalID": plant,
                "flight_observations": len(group),
                **dict(zip(columns, median)),
            }
        )
    return pd.DataFrame(records), columns, table


def _year_site_figure(root, index, counts, stage, years, sites, labels, limits):
    import matplotlib.pyplot as plt

    columns = [(year, site) for year in years for site in sites]
    height = max(4, len(labels) * 1.25)
    fig, axes = plt.subplots(
        len(labels),
        len(columns),
        figsize=(3.1 * len(columns) + 2, height),
        sharex=True,
        sharey=True,
        squeeze=False,
    )
    fig.subplots_adjust(
        left=0.14,
        right=0.99,
        top=1 - 0.85 / height,
        bottom=0.45 / height,
        hspace=0.22,
        wspace=0.12,
    )
    title = {
        "raw": "Raw NEON",
        "corr": "Corrected NEON",
        "olioli": "Derived Landsat OLI",
        "micasense": "Derived MicaSense",
    }[stage]
    unverified = False
    records = index[index.stage == stage]
    with np.load(root / "checkpoints" / records.iloc[0].checkpoint) as first:
        w = first["wavelengths_nm"]
        if stage == "micasense":
            unverified = _micasense_labels_unverified(w)
    fig.text(
        0.14,
        1 - 0.07 / height,
        f"{title}: boosted species quantiles by acquisition year and site",
        fontsize=14,
        weight="bold",
        va="top",
    )
    fig.text(
        0.14,
        1 - 0.36 / height,
        "99 fitted quantiles (1–99%); strong 50%; dotted empirical median. One GlobalID per plant within each year; ≥10 plants per fitted cell.",
        fontsize=9,
        va="top",
    )
    observed = set(zip(counts.year, counts.site))
    for i, species in enumerate(labels):
        for j, (year, site) in enumerate(columns):
            ax = axes[i, j]
            rows = records[
                (records.year == year)
                & (records.site == site)
                & (records.species == species)
            ]
            n = counts.loc[
                (counts.year == year)
                & (counts.site == site)
                & (counts.species == species),
                "plants",
            ].sum()
            if not rows.empty:
                _draw_quantile_panel(
                    ax, rows, root, ((1340, 1450), (1790, 2000)), limits, (stage,)
                )
            else:
                ax.set_ylim(*limits)
                ax.set_xlim(w[0], w[-1])
                message = (
                    "No acquisition"
                    if (year, site) not in observed
                    else f"n = {int(n)}; below threshold"
                    if n
                    else "No plants of this species"
                )
                ax.text(
                    0.5,
                    0.5,
                    message,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=".4",
                )
                ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=7, labelbottom=i == len(labels) - 1)
            if not rows.empty:
                ax.text(
                    0.97,
                    0.94,
                    f"n = {int(n)}",
                    ha="right",
                    va="top",
                    transform=ax.transAxes,
                    fontsize=8,
                )
            if i == 0:
                ax.set_title(f"{year} · {site}", fontsize=11)
            if j == 0:
                ax.text(
                    -0.16,
                    0.5,
                    species,
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontsize=9,
                    fontstyle="italic",
                )
    fig.supxlabel(
        "Supplied export label (nm; MicaSense physical wavelengths unverified)"
        if unverified
        else "Wavelength (nm)",
        y=0.006 / height,
        fontsize=11,
    )
    fig.supylabel("Spectral value (native stored units)", x=0.007, fontsize=11)
    if unverified:
        fig.text(
            0.99,
            1 - 0.58 / height,
            "MicaSense export labels unverified",
            ha="right",
            fontsize=9,
        )
    return fig


def run_year_site_quantiles(comparisons, output, *, config=None):
    """Fit or reuse boosted spectral quantiles within eligible species-by-site-by-year cohorts."""

    import matplotlib

    matplotlib.use("Agg")
    config = config or QuantileModelConfig()
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    checkpoint = root / "checkpoints"
    checkpoint.mkdir(exist_ok=True)
    _, _, observations, _, hashes = _model_inputs(Path(comparisons))
    tables = {}
    column_map = {}
    sources = None
    counts = None
    keys = ["site", "year", "species", "GlobalID"]
    for stage in config.stages:
        table, columns, source = _year_plant_spectra(observations[stage][0], stage)
        if tables and not table[keys].equals(next(iter(tables.values()))[keys]):
            raise ValueError("Year/plant cohorts disagree across stages")
        tables[stage] = table
        column_map[stage] = columns
        if sources is None:
            sources = source
    plants = next(iter(tables.values()))[keys + ["flight_observations"]].copy()
    plants["region"] = plants.site + "-" + plants.year.astype(str)
    counts = _regional_counts(plants, config.min_plants_per_species).rename(
        columns={"eligible": "eligible"}
    )
    counts = counts.merge(
        plants[["region", "site", "year"]].drop_duplicates(),
        on="region",
        validate="many_to_one",
    )
    labels = sorted(counts.loc[counts.eligible, "species"].unique(), key=str.casefold)
    if not labels:
        raise ValueError("No year/site species cohort meets minimum plants")
    requests = []
    for (site, year, species), group in plants.groupby(
        ["site", "year", "species"], sort=True
    ):
        eligible = counts.loc[
            (counts.site == site) & (counts.year == year) & (counts.species == species),
            "eligible",
        ].item()
        if not eligible:
            continue
        for stage, table in tables.items():
            w = np.array([float(c.split("_wl")[1][:-2]) for c in column_map[stage]])
            meta = {
                "level": "species",
                "region": f"{site}-{year}",
                "site": site,
                "year": int(year),
                "species": species,
                "GlobalID": "",
                "stage": stage,
                "partition": "full",
                "independent_plants": len(group),
            }
            requests.append(
                (meta, w, table.loc[group.index, column_map[stage]].to_numpy(float))
            )
    records = []
    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        futures = [
            pool.submit(_fit_checkpoint, checkpoint, meta, w, values, config, {})
            for meta, w, values in requests
        ]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records) % 10 == 0 or len(records) == len(requests):
                _LOG.info("Year/site fits %s/%s", len(records), len(requests))
    index = pd.DataFrame(records).sort_values(["year", "site", "species", "stage"])
    index.to_parquet(root / "model_index.parquet", index=False)
    counts.to_csv(root / "species_year_site_counts.csv", index=False)
    plants.to_parquet(root / "plant_year_site_cohorts.parquet", index=False)
    source_counts = (
        sources.groupby(["year", "site"])
        .agg(
            observations=("GlobalID", "size"),
            plants=("GlobalID", "nunique"),
            flights=("flight_id", "nunique"),
        )
        .reset_index()
    )
    source_counts.to_csv(root / "year_site_counts.csv", index=False)
    sources[["year", "site", "flight_id", "source_parquet"]].drop_duplicates().to_csv(
        root / "source_year_site_provenance.csv", index=False
    )
    years = sorted(plants.year.unique().tolist())
    sites = sorted(plants.site.unique().tolist())
    lo = float(index.plot_min.min())
    hi = float(index.plot_max.max())
    margin = (hi - lo) * 0.04 or 1
    for stage in config.stages:
        _LOG.info("Rendering year/site panel: %s", stage)
        fig = _year_site_figure(
            root, index, counts, stage, years, sites, labels, (lo - margin, hi + margin)
        )
        _save(fig, root / f"{stage}_species_year_site_quantiles", 250)
    _, _, _, _, final_hashes = _model_inputs(Path(comparisons))
    if hashes != final_hashes:
        raise ValueError("Compact inputs changed during run")
    audit = {
        "inputs": hashes,
        "implementation_sha256": _file_hash(__file__),
        "config": asdict(config),
        "models": len(index),
        "species": len(labels),
        "years": years,
        "sites": sites,
        "acquisition_groups": source_counts.to_dict("records"),
        "plants_observed_multiple_years": int(
            plants.groupby("GlobalID").year.nunique().gt(1).sum()
        ),
        "replication": "One within-year median per GlobalID, equal flight/polygon observations; years are not independent plants",
        "interpretation": "Exploratory within-year species fits, not a longitudinal causal effect or validated identifier; existing tail fitting limitations apply",
        "coordinate_status": {
            stage: "unverified_export_labels"
            if stage == "micasense"
            and _micasense_labels_unverified(
                np.array([float(c.split("_wl")[1][:-2]) for c in column_map[stage]])
            )
            else "supplied_grid"
            for stage in config.stages
        },
    }
    (root / "year_site_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    outputs = {
        str(p.relative_to(root)): _file_hash(p)
        for p in root.rglob("*")
        if p.is_file() and p.name != "year_site_manifest.json"
    }
    temp = root / "year_site_manifest.json.tmp"
    temp.write_text(
        json.dumps({"identity": audit, "outputs": outputs}, indent=2) + "\n"
    )
    temp.replace(root / "year_site_manifest.json")
    return audit
