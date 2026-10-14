"""Plant-balanced atlas for union-schema corrected polygon extraction tables.

Reads projected spectral batches; never copies the source pixel table. Global
plant identity is explicit: repeated flight observations receive equal weight.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import re
import warnings
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

_LOG = logging.getLogger(__name__)


def harmonize_spectrum(
    wavelengths, values, target, *, excluded=((1340, 1450), (1790, 2000)), max_gap_nm=8
):
    """Linearly harmonize one spectrum without bridging unsupported intervals.

    Args:
        wavelengths (array-like): Increasing native coordinates in nm, shape (B,).
        values (array-like): Same-shape stored reflectance values; nonfinite
            entries break support. Finite negatives and zeros are preserved.
        target (array-like): Output wavelength coordinates in nm.
        excluded (sequence): Inclusive wavelength intervals in nm to omit.
        max_gap_nm (float): Largest adjacent native interval to interpolate.

    Returns:
        numpy.ndarray: Target-shaped values in unchanged input units. Unsupported
        coordinates are NaN; no extrapolation, scaling or clipping occurs.

    Raises:
        ValueError: Native lengths differ or coordinates are not increasing.

    Exact isolated samples survive, but do not connect across gaps.
    """
    w, v, t = map(lambda a: np.asarray(a, dtype=float), (wavelengths, values, target))
    if len(w) != len(v) or len(w) < 2 or np.any(np.diff(w) <= 0):
        raise ValueError("Native wavelengths must be unique and increasing")
    result = np.full(t.shape, np.nan)
    valid = np.isfinite(v)
    allowed = np.ones(t.shape, dtype=bool)
    for lo, hi in excluded:
        valid &= ~((w >= lo) & (w <= hi))
        allowed &= ~((t >= lo) & (t <= hi))
    for i in range(len(w) - 1):
        if not (valid[i] and valid[i + 1]) or w[i + 1] - w[i] > max_gap_nm:
            continue
        use = allowed & (t >= w[i]) & (t <= w[i + 1])
        result[use] = np.interp(t[use], w[i : i + 2], v[i : i + 2])
    # Preserve isolated exact samples without bridging neighboring missing bands.
    for wi, vi, ok in zip(w, v, valid):
        if ok:
            result[(t == wi) & allowed] = vi
    return result


def _median(values, axis=0):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(values, axis=axis)


def _build_plant_spectral_atlas(
    source,
    output_dir,
    *,
    min_plants_per_species=10,
    plant_field="GlobalID",
    flight_field="flight_id",
    source_field="source_image",
    species_field="species",
    excluded=((1340, 1450), (1790, 2000)),
    grid_step_nm=5,
    max_gap_nm=8,
    band_batch_size=32,
    dpi=350,
    supplementary=True,
    spectral_stage="corr",
    make_figures=True,
):
    """Audit, aggregate pixels to observations to plants, and render an atlas.

    Identity fields are required, not inferred from local polygon numbering.
    Species-only main figure excludes genus-only labels and Other/Unidentified;
    supplementary atlas includes identified genus labels. Outputs are rerunnable
    derivatives; the original library is opened read-only.
    """
    if (
        min_plants_per_species < 1
        or (grid_step_nm is not None and grid_step_nm <= 0)
        or band_batch_size < 1
        or dpi < 300
    ):
        raise ValueError("Positive threshold/grid/batch and dpi >= 300 required")
    if spectral_stage not in ("raw", "corr") and (
        grid_step_nm is not None or make_figures
    ):
        raise ValueError(
            "Discrete sensor products require grid_step_nm=None and make_figures=False; use run_plant_comparison_atlas for plots"
        )
    source, out = Path(source), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pf = pq.ParquetFile(source)
    band_pattern = re.compile(
        rf"^{re.escape(spectral_stage)}_b(\d+)_wl(\d+(?:\.\d+)?)nm$"
    )
    bands = [
        (c, int(m[1]), float(m[2]))
        for c in pf.schema_arrow.names
        if (m := band_pattern.fullmatch(c))
    ]
    if not bands:
        raise ValueError(f"No {spectral_stage} wavelength columns")
    fields = list(
        dict.fromkeys(
            [plant_field, flight_field, source_field, species_field, "polygon_id"]
        )
    )
    provenance_fields = [
        c
        for c in ("source_parquet", "polygon_source", "reference_product", "aop_site")
        if c in pf.schema_arrow.names and c not in fields
    ]
    meta = pf.read(columns=fields + provenance_fields).to_pandas()
    identity = [flight_field, source_field]
    if meta[identity].isna().any().any():
        raise ValueError("Missing flight/source identity")
    labelled = meta[species_field].notna() & meta[species_field].astype(
        str
    ).str.strip().ne("")
    if meta.loc[labelled, plant_field].isna().any():
        raise ValueError("Labeled rows lack independent plant identity")
    if (meta.groupby(plant_field)[species_field].nunique() > 1).any():
        raise ValueError("Conflicting species labels for a plant")
    keys = [plant_field, flight_field, source_field, "polygon_id"]
    groups = meta.loc[labelled].groupby(keys, sort=True, dropna=False)
    observations = groups[species_field].first().reset_index()
    for field in provenance_fields:
        observations[field] = groups[field].first().to_numpy()
    observations["pixel_count"] = groups.size().to_numpy()
    obs_index = pd.MultiIndex.from_frame(observations[keys])
    native = np.full((len(observations), len(bands)), np.nan)
    source_groups = meta.groupby(identity, sort=True).indices
    active = {k: [] for k in source_groups}
    counts = np.zeros(len(meta), dtype=int)
    extremes = []
    band_statistics = []
    finite_total = 0
    for start in range(0, len(bands), band_batch_size):
        selection = bands[start : start + band_batch_size]
        _LOG.info(
            "%s band audit/plant medians: %s/%s", spectral_stage, start, len(bands)
        )
        frame = pf.read(columns=[b[0] for b in selection]).to_pandas()
        values = frame.to_numpy(dtype=float)
        if np.any(values == -9999):
            raise ValueError(
                "Unresolved -9999 nodata sentinel; supply a library with declared missing values"
            )
        finite = np.isfinite(values)
        counts += finite.sum(axis=1)
        finite_total += int(finite.sum())
        frame = frame.where(finite)
        for key, ix in source_groups.items():
            present = finite[ix].any(axis=0)
            active[key].extend(start + np.flatnonzero(present))
        combined = pd.concat([meta.loc[labelled, keys], frame.loc[labelled]], axis=1)
        med = (
            combined.groupby(keys, sort=True, dropna=False)[frame.columns]
            .median()
            .reindex(obs_index)
        )
        native[:, start : start + len(selection)] = med.to_numpy()
        for j, (column, _, wavelength) in enumerate(selection):
            finite_values = values[finite[:, j], j]
            band_statistics.append(
                {
                    "column": column,
                    "wavelength_nm": wavelength,
                    "finite_pixels": len(finite_values),
                    "zero_pixels": int((finite_values == 0).sum()),
                    "median": float(np.median(finite_values))
                    if len(finite_values)
                    else None,
                    "p99": float(np.quantile(finite_values, 0.99))
                    if len(finite_values)
                    else None,
                }
            )
            i = int(np.nanargmax(values[:, j])) if finite[:, j].any() else None
            if i is not None:
                extremes.append(
                    {
                        **meta.iloc[i].to_dict(),
                        "column": column,
                        "wavelength_nm": wavelength,
                        "value": values[i, j],
                    }
                )
    grids = []
    signatures = {}
    native_wavelengths = []
    for key, ix in source_groups.items():
        indices = sorted(active[key], key=lambda j: bands[j][2])
        w = np.array([bands[j][2] for j in indices])
        if (
            len(w) < 2
            or np.any(np.diff(w) <= 0)
            or len({bands[j][1] for j in indices}) != len(indices)
        ):
            raise ValueError(f"Ambiguous native wavelength/band mapping: {key}")
        signature = tuple(indices)
        grid_id = signatures.setdefault(signature, len(signatures) + 1)
        native_wavelengths.append(w)
        grids.append(
            {
                flight_field: key[0],
                source_field: key[1],
                "grid_id": grid_id,
                "pixel_rows": len(ix),
                "valid_bands": len(w),
                "min_nm": w.min(),
                "max_nm": w.max(),
                "median_spacing_nm": float(np.median(np.diff(w))),
                "min_spacing_nm": float(np.min(np.diff(w))),
                "max_spacing_nm": float(np.max(np.diff(w))),
                "native_finite_fraction": float(counts[ix].sum() / (len(ix) * len(w))),
                "wavelengths_nm": json.dumps(w.tolist()),
                "columns": json.dumps([bands[j][0] for j in indices]),
            }
        )
    pd.DataFrame(grids).to_csv(out / "flight_source_grids.csv", index=False)
    lower = max(w.min() for w in native_wavelengths)
    upper = min(w.max() for w in native_wavelengths)
    if grid_step_nm is None:
        target = np.array(
            sorted(set.intersection(*(set(w) for w in native_wavelengths)))
        )
    else:
        target = np.arange(
            np.ceil(lower / grid_step_nm) * grid_step_nm, upper + 0.001, grid_step_nm
        )
    if len(target) < 2:
        raise ValueError("No common wavelength support")
    native_records = []
    harmonized = np.full((len(observations), len(target)), np.nan)
    for i, row in observations.iterrows():
        key = (row[flight_field], row[source_field])
        ix = sorted(active[key], key=lambda j: bands[j][2])
        native_records.append(
            {
                **row.to_dict(),
                "wavelengths_nm": [bands[j][2] for j in ix],
                (
                    "corrected_values"
                    if spectral_stage == "corr"
                    else f"{spectral_stage}_values"
                ): native[i, ix].tolist(),
            }
        )
        harmonized[i] = harmonize_spectrum(
            [bands[j][2] for j in ix],
            native[i, ix],
            target,
            excluded=excluded,
            max_gap_nm=max_gap_nm,
        )
    pd.DataFrame(native_records).to_parquet(
        out / "plant_flight_native_spectra.parquet", index=False
    )
    pd.DataFrame(band_statistics).to_csv(
        out / "native_band_statistics.csv", index=False
    )
    obs_columns = [f"{spectral_stage}_wl{w:g}nm" for w in target]
    observation_table = pd.concat(
        [observations, pd.DataFrame(harmonized, columns=obs_columns)], axis=1
    )
    observation_table.to_parquet(out / "plant_flight_spectra.parquet", index=False)
    plant_rows, plant_values = [], []
    for plant, ix in observations.groupby(plant_field, sort=True).indices.items():
        plant_rows.append(
            {
                plant_field: plant,
                species_field: observations.iloc[ix[0]][species_field],
                "flight_observations": len(ix),
                "pixel_count": int(observations.iloc[ix].pixel_count.sum()),
                "flights": json.dumps(
                    sorted(observations.iloc[ix][flight_field].unique().tolist())
                ),
            }
        )
        plant_values.append(_median(harmonized[ix]))
    plants = pd.DataFrame(plant_rows)
    spectra = np.array(plant_values)
    keep = np.isfinite(spectra).any(axis=1)
    plants["retained"] = keep
    pd.concat([plants, pd.DataFrame(spectra, columns=obs_columns)], axis=1).to_parquet(
        out / "plant_harmonized_spectra.parquet", index=False
    )
    sample = (
        plants.groupby(species_field)
        .agg(
            plants=(plant_field, "size"),
            retained=("retained", "sum"),
            flight_observations=("flight_observations", "sum"),
            pixels=("pixel_count", "sum"),
        )
        .reset_index()
    )
    sample["biological_label"] = ~sample[species_field].str.casefold().isin(
        ["unidentified", "other"]
    )
    sample["species_resolution"] = sample[species_field].str.split().str.len() >= 2
    sample["main_panel"] = (
        sample.biological_label
        & sample.species_resolution
        & (sample.retained >= min_plants_per_species)
    )
    sample = sample.sort_values(["retained", species_field], ascending=[False, True])
    species_medians = []
    for label, ix in plants.groupby(species_field).indices.items():
        species_medians.append(
            {species_field: label, **dict(zip(obs_columns, _median(spectra[ix])))}
        )
    pd.DataFrame(species_medians).to_parquet(
        out / "species_median_spectra.parquet", index=False
    )
    observations.groupby([species_field, flight_field, source_field]).size().rename(
        "plant_observations"
    ).reset_index().to_csv(out / "species_flight_counts.csv", index=False)
    sample.to_csv(out / "species_sample_sizes.csv", index=False)
    pd.DataFrame(extremes).sort_values("value", ascending=False).to_csv(
        out / "band_extremes.csv", index=False
    )
    coverage = pd.DataFrame(
        {
            "wavelength_nm": target,
            "plant_count": np.isfinite(spectra).sum(0),
            "flight_observation_count": np.isfinite(harmonized).sum(0),
        }
    )
    coverage.to_csv(out / "common_coverage.csv", index=False)
    allowed = np.ones(len(target), dtype=bool)
    for lo, hi in excluded:
        allowed &= ~((target >= lo) & (target <= hi))
    audit = {
        "source": str(source.resolve()),
        "source_size_bytes": source.stat().st_size,
        "source_mtime_ns": source.stat().st_mtime_ns,
        "rows": len(meta),
        "labelled_rows": int(labelled.sum()),
        "union_bands": len(bands),
        "native_grids": len(signatures),
        "flight_sources": len(grids),
        "merged_finite_fraction": finite_total / (len(meta) * len(bands)),
        "finite_bands_per_pixel_min_max": [int(counts.min()), int(counts.max())],
        "plant_flight_observations": len(observations),
        "independent_labelled_plants": len(plants),
        "plants_retained": int(keep.sum()),
        "plants_lost": int((~keep).sum()),
        "harmonized_finite_fraction_including_excluded": float(
            np.isfinite(spectra).mean()
        ),
        "harmonized_finite_fraction_supported": float(
            np.isfinite(spectra[:, allowed]).mean()
        ),
        "excluded_nm": excluded,
        "grid_step_nm": grid_step_nm,
        "max_gap_nm": max_gap_nm,
        "target_range_nm": [float(target.min()), float(target.max())],
        "min_plants_per_species": min_plants_per_species,
        "main_species": int(sample.main_panel.sum()),
        "spectral_stage": spectral_stage,
        "units": "Spectral value (native stored units; no scaling)",
        "aggregation": "pixel median within plant/flight/source/polygon, then equal-observation median per GlobalID",
        "validation": {
            "conflicting_species": 0,
            "ambiguous_native_grids": 0,
            "blank_retained_plants": 0,
            "pixel_weighting": False,
            "gap_interpolation": False,
        },
    }
    if make_figures:
        _plot_atlas(
            plants,
            spectra,
            target,
            sample.loc[sample.main_panel, species_field].tolist(),
            out / "species_atlas",
            species_field,
            excluded,
            dpi,
            axis_label=f"{spectral_stage} spectral value (native stored units)",
        )
        if supplementary:
            _plot_atlas(
                plants,
                spectra,
                target,
                sample.loc[sample.biological_label, species_field].tolist(),
                out / "supplementary_atlas",
                species_field,
                excluded,
                dpi,
                axis_label=f"{spectral_stage} spectral value (native stored units)",
            )
        _plot_grids(grids, coverage, out, excluded)
    (out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_plant_spectral_atlas(source, output_dir, **kwargs):
    """Create/reuse empirical plant-atlas derivatives without copying source pixels.

    Args:
        source (str or pathlib.Path): Existing merged polygon Parquet, read in place.
        output_dir (str or pathlib.Path): Directory for compact products/manifest.
        **kwargs: Atlas options: plant_field='GlobalID', flight_field='flight_id',
            source_field='source_image', species_field='species',
            min_plants_per_species=10, spectral_stage='corr', grid_step_nm=5,
            max_gap_nm=8, excluded=((1340,1450),(1790,2000)), band_batch_size=32,
            dpi=350, supplementary=True, make_figures=True. Set grid_step_nm=None
            for exact shared discrete sensor coordinates; make_figures=False
            skips figures. Wavelengths are nm; stored reflectance units unchanged.

    Returns:
        dict: Audit counts, grids, support and output provenance. Derivative
        Parquets/CSVs and optional PDF/PNG/SVG persist in output_dir.

    Raises:
        ValueError: Missing/conflicting identities, ambiguous native grids,
            undeclared nodata sentinel, or no sufficiently supported taxa.
        OSError: Source/products cannot be read or written.

    Pixel medians form polygon/flight/source observations, then equal-observation
    plant medians. Structural NaNs are native-grid absence, not zero values.
    Completed output is reused only when source/options/code/output hashes match.
    Failed reruns preserve completed products. Years require the separate
    year-aware workflow; this default atlas aggregates across observations.
    """
    source, out = Path(source), Path(output_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    identity = {
        "source_sha256": _file_hash(source),
        "options": kwargs,
        "implementation_sha256": _file_hash(__file__),
    }
    identity = json.loads(json.dumps(identity))
    manifest_path = out / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["identity"] == identity and all(
            (out / name).is_file() and _file_hash(out / name) == digest
            for name, digest in manifest["outputs"].items()
        ):
            _LOG.info("Reusing checksum-verified completed plant atlas")
            return json.loads((out / "audit.json").read_text())
    with TemporaryDirectory(prefix="plant-atlas-", dir=out.parent) as directory:
        stage = Path(directory)
        audit = _build_plant_spectral_atlas(source, stage, **kwargs)
        if _file_hash(source) != identity["source_sha256"]:
            raise ValueError("Source changed during analysis")
        outputs = {p.name: _file_hash(p) for p in stage.iterdir()}
        out.mkdir(parents=True, exist_ok=True)
        # Publish manifest last: interrupted publication cannot be reused.
        for p in stage.iterdir():
            p.replace(out / p.name)
        temporary = out / "manifest.json.tmp"
        temporary.write_text(
            json.dumps({"identity": identity, "outputs": outputs}, indent=2) + "\n"
        )
        temporary.replace(manifest_path)
    return json.loads(json.dumps(audit))


def _plot_atlas(
    plants,
    spectra,
    w,
    labels,
    destination,
    species_field,
    excluded,
    dpi,
    axis_label="Corrected spectral value (native stored units)",
):
    import matplotlib.pyplot as plt

    if not labels:
        raise ValueError("No taxa meet the requested threshold")
    columns = min(4, len(labels))
    rows = int(np.ceil(len(labels) / columns))
    valid = plants[species_field].isin(labels).to_numpy() & plants.retained.to_numpy()
    selected = spectra[valid]
    lo, hi = np.nanmin(selected), np.nanmax(selected)
    margin = (hi - lo) * 0.04 or 1
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    ):
        fig, axes = plt.subplots(
            rows,
            columns,
            figsize=(columns * 3.6, rows * 2.3),
            sharex=True,
            sharey=True,
            squeeze=False,
            layout="constrained",
        )
        for ax, label in zip(axes.flat, labels):
            ix = (
                plants[species_field] == label
            ).to_numpy() & plants.retained.to_numpy()
            v = spectra[ix]
            ax.plot(w, v.T, color="#355c70", alpha=0.10, linewidth=0.45)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                q = np.nanquantile(v, [0.25, 0.5, 0.75], axis=0)
            ax.fill_between(w, q[0], q[2], color="#355c70", alpha=0.13)
            ax.plot(w, q[1], color="#142f40", linewidth=1.25)
            ax.set_title(label, fontstyle="italic", fontsize=10, pad=14)
            ax.text(
                0.5,
                1.015,
                f"n = {len(v):,} plants",
                transform=ax.transAxes,
                ha="center",
                fontsize=8,
            )
            for a, b in excluded:
                ax.axvspan(a, b, color="0.92", zorder=-1)
            ax.set_xlim(w.min(), w.max())
            ax.set_ylim(lo - margin, hi + margin)
            ax.set_xticks([500, 1000, 1500, 2000, 2500])
            ax.tick_params(labelsize=8)
        for ax in list(axes.flat)[len(labels) :]:
            ax.remove()
        fig.supxlabel("Wavelength (nm)")
        fig.supylabel(axis_label)
        for extension in ["pdf", "png", "svg"]:
            fig.savefig(destination.with_suffix("." + extension), dpi=dpi)
        plt.close(fig)


def _plot_grids(grids, coverage, out, excluded):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(12, 5), layout="constrained", sharex=True)
    seen = set()
    for row in grids:
        if row["grid_id"] in seen:
            continue
        seen.add(row["grid_id"])
        w = json.loads(row["wavelengths_nm"])
        axes[0].plot(w, np.full(len(w), row["grid_id"]), "|", markersize=5)
    axes[0].set_ylabel("Native grid")
    axes[0].set_yticks(sorted(seen))
    axes[1].plot(coverage.wavelength_nm, coverage.plant_count, color="#355c70")
    axes[1].set_ylabel("Supported plants")
    axes[1].set_xlabel("Wavelength (nm)")
    for ax in axes:
        for lo, hi in excluded:
            ax.axvspan(lo, hi, color="0.9", zorder=-1)
    fig.savefig(out / "wavelength_coverage.png", dpi=350)
    fig.savefig(out / "wavelength_coverage.pdf")
    plt.close(fig)
