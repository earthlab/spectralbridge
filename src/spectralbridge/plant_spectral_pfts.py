"""Auditable name-derived PFT tags and plant-balanced grouped spectral reports."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
import json
import logging
import os
import textwrap

import numpy as np
import pandas as pd

from .plant_spectral_atlas import _file_hash
from .plant_spectral_comparison import (
    _draw_product,
    _save,
    _micasense_labels_unverified,
)
from .plant_spectral_quantiles import (
    QuantileModelConfig,
    _model_inputs,
    _fit_checkpoint,
    _split_plants,
    _draw_quantile_panel,
    _evaluate_matching,
)
from .plant_spectral_years import _year_plant_spectra
from .plant_quantile_overlays import _overlay_figure

_LOG = logging.getLogger(__name__)
UNASSIGNED = "Unassigned"
COLUMNS = [
    ("Raw NEON", "raw"),
    ("Corrected NEON", "corr"),
    ("Derived Landsat OLI", "olioli"),
    ("Derived MicaSense", "micasense"),
]


def load_pft_crosswalk(path=None):
    """Load the explicit, versioned lookup; never infer a species from a genus."""
    if path is None:
        with (
            files("spectralbridge")
            .joinpath("data/plant_pft_crosswalk.csv")
            .open() as stream
        ):
            mapping = pd.read_csv(stream, keep_default_na=False)
    else:
        mapping = pd.read_csv(path, keep_default_na=False)
    required = {
        "species",
        "pft_code",
        "pft",
        "assignment_status",
        "source_url",
        "habit_variable",
        "scheme",
    }
    if not required.issubset(mapping):
        raise ValueError("PFT crosswalk lacks required fields")
    key = mapping.species.astype(str).map(_taxon_key)
    if key.eq("").any() or key.duplicated().any():
        raise ValueError("Duplicate or blank crosswalk taxa")
    assigned = mapping.pft.ne(UNASSIGNED)
    if (
        mapping.loc[assigned, "source_url"].eq("")
        | mapping.loc[assigned, "pft_code"].eq("")
    ).any():
        raise ValueError("Assigned PFTs require provenance and a code")
    if (
        mapping.groupby("pft").pft_code.nunique().gt(1).any()
        or mapping.groupby("pft_code").pft.nunique().gt(1).any()
    ):
        raise ValueError("PFT labels and codes must be one-to-one")
    return mapping


def _taxon_key(value):
    return " ".join(str(value).split()).casefold() if pd.notna(value) else ""


def tag_pfts(table, crosswalk):
    """Add tags while retaining verbatim species and all observation identities."""
    if "species" not in table or "pft" in table:
        raise ValueError("Expected untagged species observations")
    mapping = crosswalk.copy()
    mapping["_taxon_key"] = mapping.species.map(_taxon_key)
    if mapping._taxon_key.duplicated().any():
        raise ValueError("Duplicate crosswalk taxa")
    result = table.copy()
    original_species = result.species.copy()
    result["_taxon_key"] = result.species.map(_taxon_key)
    mapping = mapping.drop(columns="species")
    result = result.merge(
        mapping, on="_taxon_key", how="left", validate="many_to_one", sort=False
    ).drop(columns="_taxon_key")
    if len(result) != len(table) or not result.species.reset_index(drop=True).equals(
        original_species.reset_index(drop=True)
    ):
        raise ValueError("Tagging changed source rows or species labels")
    missing = result.pft.isna()
    result.loc[missing, "pft"] = UNASSIGNED
    result.loc[missing, "pft_code"] = "UNASSIGNED"
    result.loc[missing, "assignment_status"] = "missing_crosswalk"
    return result


def _requests_for_pfts(plants, data, years, year_columns, cohort, config):
    """Fit group distributions from individual plants, never from species medians."""
    requests = []
    counts = []
    for scope, group in [("ALL", plants), *list(plants.groupby("region", sort=True))]:
        for pft, sub in group.groupby("pft", sort=True):
            n = len(sub)
            counts.append(
                {
                    "scope": scope,
                    "pft": pft,
                    "plants": n,
                    "taxa": sub.species.nunique(),
                    "eligible": n >= config.min_plants_per_species,
                }
            )
            if n < config.min_plants_per_species:
                continue
            for partition in ["full", "train"]:
                training = (
                    sub
                    if partition == "full"
                    else sub[
                        sub.GlobalID.isin(
                            cohort.loc[cohort.partition == "train", "GlobalID"]
                        )
                    ]
                )
                for stage in config.stages:
                    w, values = data[stage]
                    meta = {
                        "level": "pft",
                        "region": scope,
                        "pft": pft,
                        "pft_code": sub.pft_code.iloc[0],
                        "year": None,
                        "GlobalID": "",
                        "stage": stage,
                        "partition": partition,
                        "independent_plants": len(training),
                        "contributing_taxa": training.species.nunique(),
                    }
                    requests.append(
                        (meta, w, values[training.source_position.to_numpy()])
                    )
    first = next(iter(years.values()))
    for (site, year, pft), sub in first.groupby(["site", "year", "pft"], sort=True):
        scope = f"{site}-{year}"
        n = len(sub)
        counts.append(
            {
                "scope": scope,
                "pft": pft,
                "plants": n,
                "taxa": sub.species.nunique(),
                "eligible": n >= config.min_plants_per_species,
            }
        )
        if n < config.min_plants_per_species:
            continue
        for stage in config.stages:
            cols = year_columns[stage]
            w = np.array([float(c.split("_wl")[1][:-2]) for c in cols])
            meta = {
                "level": "pft",
                "region": scope,
                "pft": pft,
                "pft_code": sub.pft_code.iloc[0],
                "year": int(year),
                "GlobalID": "",
                "stage": stage,
                "partition": "full",
                "independent_plants": n,
                "contributing_taxa": sub.species.nunique(),
            }
            requests.append(
                (meta, w, years[stage].loc[sub.index, cols].to_numpy(float))
            )
    return requests, pd.DataFrame(counts)


def _pft_panel(root, index, counts, columns, labels, title, limits, *, empirical=None):
    """One PFT per row; each column selects exactly one scope and sensor."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    height = max(4, len(labels) * 1.5)
    fig, axes = plt.subplots(
        len(labels),
        len(columns),
        figsize=(3.1 * len(columns) + 3, height),
        sharex="col",
        sharey=True,
        squeeze=False,
    )
    fig.subplots_adjust(
        left=0.20,
        right=0.99,
        top=1 - 0.95 / height,
        bottom=0.55 / height,
        hspace=0.23,
        wspace=0.13,
    )
    fig.text(0.20, 1 - 0.08 / height, title, fontsize=13, weight="bold", va="top")
    description = (
        "Independent plant traces; strong group median; empirical IQR"
        if empirical is not None
        else "99 boosted quantiles (1–99%); strong fitted median; dotted empirical median"
    )
    fig.text(
        0.20,
        1 - 0.37 / height,
        description + " | Equal plant weights; species composition varies",
        fontsize=9,
        va="top",
    )
    has_ms = any(stage == "micasense" for _, _, stage in columns)
    for i, pft in enumerate(labels):
        for j, (heading, scope, stage) in enumerate(columns):
            ax = axes[i, j]
            row = counts[(counts.scope == scope) & (counts.pft == pft)]
            n = int(row.plants.iloc[0]) if len(row) else 0
            taxa = int(row.taxa.iloc[0]) if len(row) else 0
            records = index[
                (index.region == scope)
                & (index.pft == pft)
                & (index.stage == stage)
                & (index.partition == "full")
            ]
            if len(row) and row.eligible.iloc[0] and not records.empty:
                if empirical is None:
                    _draw_quantile_panel(
                        ax,
                        records,
                        root,
                        ((1340, 1450), (1790, 2000)),
                        limits,
                        (stage,),
                    )
                else:
                    frame, values_by_stage = empirical[scope]
                    w, v = values_by_stage[stage]
                    take = frame.pft.eq(pft).to_numpy()
                    _draw_product(
                        ax,
                        stage,
                        w,
                        v[take],
                        excluded=((1340, 1450), (1790, 2000)),
                        band_diagnostics=[],
                    )
                    ax.set_xlim(w[0], w[-1])
                    ax.set_ylim(*limits)
                    ax.xaxis.set_major_locator(MaxNLocator(4))
                    ax.spines[["top", "right"]].set_visible(False)
                    for line in ax.lines[:-1]:
                        if line.get_alpha() is not None and line.get_alpha() < 0.2:
                            line.set_rasterized(True)
                ax.text(
                    0.97,
                    0.96,
                    f"n = {n}; {taxa} taxa",
                    ha="right",
                    va="top",
                    transform=ax.transAxes,
                    fontsize=7,
                )
            else:
                ax.set_ylim(*limits)
                msg = (
                    "No acquisition"
                    if scope not in set(counts.scope)
                    else f"n = {n}; below threshold"
                    if n
                    else "No assigned plants"
                )
                ax.text(
                    0.5,
                    0.5,
                    msg,
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                    fontsize=8,
                    color=".4",
                )
                ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=7, labelbottom=i == len(labels) - 1)
            if i == 0:
                ax.set_title(heading, fontsize=10)
            if j == 0:
                ax.text(
                    -0.19,
                    0.5,
                    textwrap.fill(pft, 22),
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontsize=9,
                )
    fig.supxlabel(
        "Wavelength / supplied export label (nm)" if has_ms else "Wavelength (nm)",
        fontsize=10,
        y=0.004 / height,
    )
    fig.text(
        0.99,
        0.018 / height,
        "Spectral values: native stored units",
        ha="right",
        fontsize=8,
    )
    if has_ms:
        fig.text(
            0.99,
            1 - 0.64 / height,
            "MicaSense export labels unverified when flagged by the source grid",
            ha="right",
            fontsize=8,
        )
    return fig


def _individual_references(plants, observations, config, source_models, out):
    """Reuse unchanged existing individual fits in place; fit only newly admitted taxa."""
    manifest_path = source_models / "quantile_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    index_path = source_models / "model_index.parquet"
    if _file_hash(index_path) != manifest["outputs"]["model_index.parquet"]:
        raise ValueError("Individual source index checksum mismatch")
    original = pd.read_parquet(index_path)
    records = []
    pending = []
    dependencies = {str(manifest_path): _file_hash(manifest_path)}
    for stage in config.stages:
        obs, cols = observations[stage]
        by_id = obs.groupby("GlobalID").indices
        w = np.array([float(c.split("_wl")[1][:-2]) for c in cols])
        for plant in plants.itertuples():
            row = original[
                (original.level == "individual")
                & (original.stage == stage)
                & (original.GlobalID == plant.GlobalID)
            ]
            if not row.empty:
                record = row.iloc[0].to_dict()
                path = source_models / "checkpoints" / record["checkpoint"]
                expected = manifest["outputs"][str(path.relative_to(source_models))]
                # Hash once here; all later plot loads are covered by this dependency ledger.
                if _file_hash(path) != expected:
                    raise ValueError("Individual checkpoint checksum mismatch")
                dependencies[str(path)] = expected
                record["checkpoint"] = os.path.relpath(path, out / "checkpoints")
                records.append(
                    {
                        **record,
                        "pft": plant.pft,
                        "pft_code": plant.pft_code,
                        "source_reused": True,
                    }
                )
            else:
                meta = {
                    "level": "individual",
                    "region": plant.region,
                    "species": plant.species,
                    "GlobalID": plant.GlobalID,
                    "stage": stage,
                    "partition": "full",
                    "independent_plants": 1,
                }
                pending.append(
                    (
                        meta,
                        w,
                        obs.iloc[by_id[plant.GlobalID]][cols].to_numpy(float),
                        plant.pft,
                        plant.pft_code,
                    )
                )
        _LOG.info(
            "Individual references: checked %s; new fits queued %s",
            len(records),
            len(pending),
        )
    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        futures = {
            pool.submit(
                _fit_checkpoint, out / "checkpoints", meta, w, values, config, {}
            ): (pft, code)
            for meta, w, values, pft, code in pending
        }
        for future in as_completed(futures):
            pft, code = futures[future]
            records.append(
                {
                    **future.result(),
                    "pft": pft,
                    "pft_code": code,
                    "source_reused": False,
                }
            )
    return pd.DataFrame(records), dependencies


def run_pft_spectral_analysis(
    comparisons, output, *, crosswalk=None, config=None, individual_overlays=True
):
    """Write additive PFT products; the original species products stay immutable."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    config = config or QuantileModelConfig()
    config.validate()
    comparisons = Path(comparisons)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "checkpoints").mkdir(exist_ok=True)
    mapping = load_pft_crosswalk(crosswalk)
    source_plants, data, observations, _, hashes = _model_inputs(comparisons)
    source_plants["source_position"] = np.arange(len(source_plants))
    tagged = tag_pfts(source_plants, mapping)
    tagged.to_parquet(out / "tagged_plants.parquet", index=False)
    mapping.to_csv(out / "species_pft_crosswalk.csv", index=False)
    mapping_digest = _file_hash(out / "species_pft_crosswalk.csv")
    tagged.groupby(["pft", "species", "assignment_status"], dropna=False).size().rename(
        "plants"
    ).reset_index().to_csv(out / "pft_species_composition.csv", index=False)
    tagged[tagged.pft == UNASSIGNED].groupby(
        ["species", "assignment_status"]
    ).size().rename("plants").reset_index().to_csv(
        out / "unassigned_labels.csv", index=False
    )
    plants = tagged[tagged.pft != UNASSIGNED].copy()
    if plants.empty:
        raise ValueError("No plants have assigned PFTs")
    years = {}
    year_columns = {}
    for stage in config.stages:
        table, cols, _ = _year_plant_spectra(observations[stage][0], stage)
        table = tag_pfts(table, mapping)
        table = table[table.pft != UNASSIGNED].reset_index(drop=True)
        if years and not table[["GlobalID", "site", "year", "pft"]].equals(
            next(iter(years.values()))[["GlobalID", "site", "year", "pft"]]
        ):
            raise ValueError("Year/PFT cohorts disagree across stages")
        years[stage] = table
        year_columns[stage] = cols
    year_metadata = next(iter(years.values()))[
        [c for c in tagged if c in next(iter(years.values()))] + ["site", "year"]
    ]
    year_metadata.to_parquet(out / "tagged_plant_years.parquet", index=False)
    # Adapter only: the shared split/evaluation helpers call their target `species`.
    # Persist original species and explicit pft fields; do not overwrite source labels.
    split_input = plants.copy()
    split_input["species"] = plants.pft
    split = _split_plants(split_input.reset_index(drop=True), config)
    cohort = plants.merge(
        split[["GlobalID", "partition"]], on="GlobalID", validate="one_to_one"
    )
    cohort.to_parquet(out / "pft_holdout_plants.parquet", index=False)
    requests, counts = _requests_for_pfts(
        plants, data, years, year_columns, cohort, config
    )
    counts.to_csv(out / "pft_sample_sizes.csv", index=False)
    records = []
    with ThreadPoolExecutor(max_workers=config.workers) as pool:
        futures = [
            pool.submit(
                _fit_checkpoint, out / "checkpoints", meta, w, values, config, {}
            )
            for meta, w, values in requests
        ]
        for future in as_completed(futures):
            records.append(future.result())
            if len(records) % 10 == 0 or len(records) == len(requests):
                _LOG.info("PFT group fits %s/%s", len(records), len(requests))
    index = pd.DataFrame(records).sort_values(["region", "pft", "stage", "partition"])
    coord = {
        s: "unverified_export_labels"
        if s == "micasense" and _micasense_labels_unverified(data[s][0])
        else "supplied_grid"
        for s in config.stages
    }
    index["coordinate_status"] = index.stage.map(coord)
    index.to_parquet(out / "pft_model_index.parquet", index=False)
    eval_index = index[index.year.isna()].rename(columns={"pft": "species"}).copy()
    eval_index["level"] = "species"
    eval_cohort = cohort.copy()
    eval_cohort["species"] = cohort.pft
    scores, summary = _evaluate_matching(
        eval_cohort, data, eval_index, out / "checkpoints", config
    )
    scores = scores.rename(columns={c: c.replace("species", "pft") for c in scores})
    summary = summary.rename(columns={c: c.replace("species", "pft") for c in summary})
    for r in summary.to_dict("records"):
        candidates = set(
            eval_index[
                (eval_index.region == r["scope"]) & (eval_index.stage == r["stage"])
            ].species
        )
        train = cohort[(cohort.partition == "train") & cohort.pft.isin(candidates)]
        if r["scope"] != "ALL":
            train = train[train.region == r["scope"]]
        majority = train.pft.value_counts().sort_index().idxmax()
        ix = (summary.scope == r["scope"]) & (summary.stage == r["stage"])
        queries = scores[(scores.scope == r["scope"]) & (scores.stage == r["stage"])]
        summary.loc[ix, "majority_pft"] = majority
        summary.loc[ix, "majority_baseline_accuracy"] = queries.true_pft.eq(
            majority
        ).mean()
    for table in [scores, summary]:
        table["coordinate_status"] = table.stage.map(coord)
    scores.to_csv(out / "held_out_pft_matches.csv", index=False)
    summary.to_csv(out / "pft_matching_validation.csv", index=False)
    lo = min(
        float(index.plot_min.min()),
        min(
            float(np.nanmin(v[plants.source_position.to_numpy()]))
            for _, v in data.values()
        ),
    )
    hi = max(
        float(index.plot_max.max()),
        max(
            float(np.nanmax(v[plants.source_position.to_numpy()]))
            for _, v in data.values()
        ),
    )
    margin = (hi - lo) * 0.04 or 1
    limits = (lo - margin, hi + margin)
    empirical = {}
    for scope, frame in [("ALL", plants), *list(plants.groupby("region", sort=True))]:
        empirical[scope] = (
            frame,
            {s: (w, v[frame.source_position.to_numpy()]) for s, (w, v) in data.items()},
        )
    full = index[index.partition == "full"]
    all_labels = sorted(counts.loc[(counts.scope == "ALL") & counts.eligible, "pft"])
    for scope in ["ALL", *sorted(plants.region.unique())]:
        labels = sorted(counts.loc[(counts.scope == scope) & counts.eligible, "pft"])
        if not labels:
            continue
        columns = [
            (heading, scope, stage)
            for heading, stage in COLUMNS
            if stage in config.stages
        ]
        for kind, inputs in [("empirical", empirical), ("boosted", None)]:
            fig = _pft_panel(
                out,
                full,
                counts,
                columns,
                labels,
                f"{scope}: {kind} PFT spectra",
                limits,
                empirical=inputs,
            )
            _save(fig, out / f"{scope}_{kind}_pft_rows", 250)
    for stage in config.stages:
        columns = [(site, site, stage) for site in sorted(plants.region.unique())]
        labels = sorted(
            counts.loc[
                counts.scope.isin(plants.region.unique()) & counts.eligible, "pft"
            ].unique()
        )
        fig = _pft_panel(
            out,
            full,
            counts,
            columns,
            labels,
            f"{stage}: boosted PFT spectra by site (all years)",
            limits,
        )
        _save(fig, out / f"{stage}_pft_by_site", 250)
        first = next(iter(years.values()))
        columns = [
            (f"{year} · {site}", f"{site}-{year}", stage)
            for year in sorted(first.year.unique())
            for site in sorted(first.site.unique())
        ]
        labels = sorted(
            counts.loc[counts.scope.str.contains("-") & counts.eligible, "pft"].unique()
        )
        fig = _pft_panel(
            out,
            full,
            counts,
            columns,
            labels,
            f"{stage}: boosted PFT spectra by acquisition year and site",
            limits,
        )
        _save(fig, out / f"{stage}_pft_by_year_site", 250)
    dependencies = {}
    if individual_overlays:
        individual, dependencies = _individual_references(
            plants, observations, config, comparisons.parent / "quantile_models", out
        )
        individual.to_parquet(
            out / "tagged_individual_model_index.parquet", index=False
        )
        for stage in config.stages:
            sub = individual[individual.stage == stage].sort_values(
                ["pft", "species", "GlobalID"]
            )
            arrays = []
            w = None
            for row in sub.itertuples():
                with np.load(out / "checkpoints" / row.checkpoint) as saved:
                    if w is not None and not np.array_equal(w, saved["wavelengths_nm"]):
                        raise ValueError("Individual overlay grids disagree")
                    w = saved["wavelengths_nm"].copy()
                    arrays.append(saved["ordered_curves"].copy())
            curves = np.stack(arrays)
            del arrays
            fig = _overlay_figure(w, curves, sub.pft.tolist(), stage, group_name="PFTs")
            for extension in ["pdf", "png"]:
                fig.savefig(
                    out / f"{stage}_individual_quantiles_by_pft.{extension}",
                    dpi=200,
                    facecolor="white",
                )
            plt.close(fig)
            del curves
            _LOG.info("PFT individual overlay complete: %s; %s plants", stage, len(sub))
    _, _, _, _, final_hashes = _model_inputs(comparisons)
    if final_hashes != hashes:
        raise ValueError("Compact input products changed during PFT analysis")
    if crosswalk is not None and _file_hash(crosswalk) != mapping_digest:
        raise ValueError("Crosswalk changed during analysis")
    audit = {
        "inputs": hashes,
        "crosswalk_sha256": mapping_digest,
        "config": asdict(config),
        "scheme": mapping.scheme.unique().tolist(),
        "tagged_plants": len(tagged),
        "assigned_plants": len(plants),
        "unassigned_plants": int(tagged.pft.eq(UNASSIGNED).sum()),
        "pft_counts": plants.groupby("pft").size().to_dict(),
        "assignment_status_counts": tagged.groupby("assignment_status")
        .size()
        .to_dict(),
        "group_models": len(index),
        "years": sorted(next(iter(years.values())).year.unique().tolist()),
        "individual_model_count": len(individual) if individual_overlays else 0,
        "individual_reused": int(individual.source_reused.sum())
        if individual_overlays
        else 0,
        "coordinate_status": coord,
        "weighting": "One GlobalID plant per group; equal plant weights, not equal species weights; within-year plant medians recomputed",
        "interpretation": "Name-derived PFT scheme with typical growth-form assumptions; unresolved labels excluded explicitly; PFT group fits refitted from plants, not averaged species curves; unknown-spectrum PFT identification still requires validation",
        "validation": summary.to_dict("records"),
    }
    (out / "pft_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    outputs = {
        str(p.relative_to(out)): _file_hash(p)
        for p in out.rglob("*")
        if p.is_file() and p.name != "pft_manifest.json" and not p.name.endswith(".tmp")
    }
    temp = out / "pft_manifest.json.tmp"
    temp.write_text(
        json.dumps(
            {
                "identity": audit,
                "implementation_sha256": _file_hash(__file__),
                "dependencies": dependencies,
                "outputs": outputs,
            },
            indent=2,
        )
        + "\n"
    )
    temp.replace(out / "pft_manifest.json")
    return audit
