"""Checkpointed boosted conditional quantile signatures and held-plant matching.

Fitted curves are representations, never synthetic independent plant observations.
Species fits use independent polygon medians; individual fits use repeated-flight
polygon medians. Unsupported NEON segments are trained separately.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import logging
from pathlib import Path
import time

import numpy as np
import pandas as pd

from .plant_spectral_atlas import _file_hash, harmonize_spectrum
from .plant_spectral_comparison import _STAGES, _micasense_labels_unverified
from .plant_spectral_regions import _verified_products

_LOG = logging.getLogger(__name__)
QUANTILES = tuple(i / 100 for i in range(1, 100))


@dataclass(frozen=True)
class QuantileModelConfig:
    quantiles: tuple[float, ...] = QUANTILES
    boosting_rounds: int = 80
    learning_rate: float = 0.1
    max_depth: int = 5
    max_bin: int = 256
    seed: int = 0
    min_plants_per_species: int = 10
    holdout_fraction: float = 0.2
    workers: int = 4
    stages: tuple[str, ...] = _STAGES

    def validate(self):
        q = np.asarray(self.quantiles)
        if (
            len(q) < 2
            or np.any(np.diff(q) <= 0)
            or np.any((q <= 0) | (q >= 1))
            or not np.isfinite(q).all()
        ):
            raise ValueError(
                "Quantiles must be unique, increasing and strictly between zero and one"
            )
        if 0.5 not in self.quantiles:
            raise ValueError("Quantiles must include the median (.5)")
        if (
            self.boosting_rounds < 1
            or self.max_depth < 1
            or self.max_bin < 2
            or self.learning_rate <= 0
        ):
            raise ValueError("Invalid boosting parameters")
        if (
            self.min_plants_per_species < 2
            or not 0 < self.holdout_fraction < 0.5
            or self.workers < 1
        ):
            raise ValueError(
                "Invalid independent-plant threshold, holdout fraction or workers"
            )
        if not self.stages or not set(self.stages).issubset(_STAGES):
            raise ValueError("Select supplied raw/corr/olioli/micasense stages")


def _xgboost():
    try:
        import xgboost as xgb
    except ImportError as exc:
        raise ImportError(
            "Install earthlab-spectralbridge[quantile-models] for boosted quantile signatures"
        ) from exc
    return xgb


def _segments(w, supported, *, hyperspectral):
    indices = np.flatnonzero(supported)
    if not len(indices):
        raise ValueError("No supported spectral values")
    breaks = np.diff(indices) != 1
    if hyperspectral:
        breaks |= np.diff(w[indices]) > 8
    return np.split(indices, np.flatnonzero(breaks) + 1)


def fit_quantile_signature(wavelengths, spectra, *, config=None, hyperspectral=True):
    """Fit exact supplied wavelengths with equal total weight per input spectrum.

    NaN columns and >8 nm hyperspectral gaps split independent boosting models.
    Returns raw fitted quantiles and explicitly pointwise-rearranged ordered
    quantiles. No clipping, normalization, extrapolation or added samples.
    """
    config = config or QuantileModelConfig()
    config.validate()
    xgb = _xgboost()
    w, y = np.asarray(wavelengths, float), np.asarray(spectra, float)
    if (
        y.ndim != 2
        or y.shape[1] != len(w)
        or np.any(np.diff(w) <= 0)
        or not np.isfinite(w).all()
    ):
        raise ValueError(
            "Spectra must be rows paired to strictly increasing finite wavelengths"
        )
    valid_rows = np.isfinite(y).any(axis=1)
    if not valid_rows.all():
        raise ValueError("Each training spectrum must contain finite observations")
    q = np.asarray(config.quantiles)
    raw = np.full((len(q), len(w)), np.nan, dtype=np.float32)
    segments = _segments(w, np.isfinite(y).any(axis=0), hyperspectral=hyperspectral)
    start = time.monotonic()
    for segment in segments:
        if len(segment) < 2:
            raise ValueError("Insufficient supported wavelengths in a spectral segment")
        values = y[:, segment]
        finite = np.isfinite(values)
        counts = finite.sum(axis=1)
        # Each plant/observation has equal total weight len(segment); complete rows
        # have weight one per band. Pixel count is never used.
        weights = np.broadcast_to(
            np.divide(
                float(len(segment)),
                counts,
                out=np.zeros_like(counts, dtype=float),
                where=counts > 0,
            )[:, None],
            values.shape,
        )
        features = np.broadcast_to(w[segment], values.shape)[finite].reshape(-1, 1)
        matrix = xgb.QuantileDMatrix(
            features,
            label=values[finite],
            weight=weights[finite],
            max_bin=config.max_bin,
            nthread=1,
        )
        model = xgb.train(
            {
                "objective": "reg:quantileerror",
                "tree_method": "hist",
                "quantile_alpha": q,
                "learning_rate": config.learning_rate,
                "max_depth": config.max_depth,
                "max_bin": config.max_bin,
                "nthread": 1,
                "seed": config.seed,
                "verbosity": 0,
                "multi_strategy": "one_output_per_tree",
            },
            matrix,
            num_boost_round=config.boosting_rounds,
        )
        raw[:, segment] = model.inplace_predict(w[segment].reshape(-1, 1)).T
    supported = np.isfinite(raw).all(axis=0)
    crossings = np.diff(raw[:, supported], axis=0) < -1e-5
    ordered = np.sort(raw, axis=0)
    empirical = np.nanquantile(y[:, supported], q, axis=0)
    median_index = config.quantiles.index(0.5)
    residual = y[:, supported] - ordered[median_index, supported]
    metrics = {
        "spectra": len(y),
        "segments": len(segments),
        "supported_bands": int(supported.sum()),
        "crossing_adjacent_fraction": float(crossings.mean()),
        "crossing_wavelength_fraction": float(crossings.any(axis=0).mean()),
        "max_rearrangement": float(np.nanmax(np.abs(ordered - raw))),
        "training_median_rmse": float(np.sqrt(np.nanmean(residual**2))),
        "empirical_quantile_rmse": float(
            np.sqrt(np.mean((ordered[:, supported] - empirical) ** 2))
        ),
        "plot_min": float(min(np.nanmin(raw), np.nanmin(y[:, supported]))),
        "plot_max": float(max(np.nanmax(raw), np.nanmax(y[:, supported]))),
        "elapsed_seconds": time.monotonic() - start,
    }
    return raw, ordered, metrics


def quantile_distance(observed, curves, quantiles, *, minimum_bands=2):
    """Mean pinball loss times two: a discrete 1–99% integrated-score approximation.

    Lower is a closer match in supplied units. It is not a class probability and
    treats wavelengths marginally, without estimating spectral covariance.
    """
    observed, curves, q = (
        np.asarray(observed, float),
        np.asarray(curves, float),
        np.asarray(quantiles, float),
    )
    if curves.shape != (len(q), len(observed)):
        raise ValueError("Query, quantiles and fitted bands do not align")
    finite = np.isfinite(observed) & np.isfinite(curves).all(axis=0)
    if finite.sum() < minimum_bands:
        raise ValueError("Insufficient shared supported bands for matching")
    residual = observed[None, finite] - curves[:, finite]
    return float(
        2 * np.maximum(q[:, None] * residual, (q[:, None] - 1) * residual).mean()
    ), int(finite.sum())


def _split_plants(plants, config):
    """Deterministic disjoint GlobalID split; all repeated flights stay together."""
    result = plants.copy()
    result["partition"] = "train"
    for _, indices in result.groupby(["region", "species"]).indices.items():
        if len(indices) < 2:
            continue
        count = max(1, int(np.floor(len(indices) * config.holdout_fraction)))
        ordered = sorted(
            indices,
            key=lambda i: hashlib.sha256(
                f"{config.seed}:{result.iloc[i].GlobalID}".encode()
            ).hexdigest(),
        )
        result.loc[ordered[:count], "partition"] = "held_out"
    return result


def _model_inputs(comparisons):
    products = comparisons / "products"
    source_hash = json.loads((products / "corr" / "manifest.json").read_text())[
        "identity"
    ]["source_sha256"]
    audits, hashes = _verified_products(source_hash, products)
    region_dir = comparisons / "regional"
    region_manifest = json.loads((region_dir / "regional_manifest.json").read_text())
    mapping_path = region_dir / "matched_plant_regions.parquet"
    if (
        region_manifest["identity"]["source_sha256"] != source_hash
        or _file_hash(mapping_path)
        != region_manifest["outputs"]["matched_plant_regions.parquet"]
    ):
        raise ValueError(
            "Regional plant mapping is not a verified source-matched output"
        )
    plants = (
        pd.read_parquet(mapping_path).sort_values("GlobalID").reset_index(drop=True)
    )
    if not plants.GlobalID.is_unique:
        raise ValueError("Plant identity is not unique")
    hashes["region_mapping"] = _file_hash(mapping_path)
    data, observations = {}, {}
    for stage in _STAGES:
        table = (
            pd.read_parquet(products / stage / "plant_harmonized_spectra.parquet")
            .set_index("GlobalID")
            .loc[plants.GlobalID]
        )
        if not np.array_equal(table.species.to_numpy(), plants.species.to_numpy()):
            raise ValueError("Plant species disagree between compact tables")
        columns = [c for c in table if c.startswith(f"{stage}_wl")]
        w = np.array([float(c.split("_wl")[1][:-2]) for c in columns])
        data[stage] = (w, table[columns].to_numpy(float))
        obs = pd.read_parquet(products / stage / "plant_flight_spectra.parquet")
        observations[stage] = (obs, columns)
    return plants, data, observations, audits, hashes


def _identity_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _fit_checkpoint(directory, meta, w, values, config, identity):
    training_digest = hashlib.sha256()
    training_digest.update(np.asarray(w).tobytes())
    training_digest.update(np.asarray(values).tobytes())
    # Fit identity is separate from plotting/evaluation so presentation repairs do
    # not invalidate expensive scientifically unchanged fits.
    identity = json.loads(
        json.dumps(
            {
                "config": _fitting_parameters(asdict(config)),
                "xgboost": _xgboost().__version__,
                "training_arrays_sha256": training_digest.hexdigest(),
                "meta": meta,
                "fitting_source_sha256": hashlib.sha256(
                    (
                        inspect.getsource(fit_quantile_signature)
                        + inspect.getsource(_segments)
                    ).encode()
                ).hexdigest(),
            }
        )
    )
    model_id = _identity_digest(meta)[:20]
    npz = directory / f"{model_id}.npz"
    metadata = directory / f"{model_id}.json"
    if metadata.exists() and npz.exists():
        saved = json.loads(metadata.read_text())
        saved_identity = dict(saved["identity"])
        if "config" in saved_identity:
            saved_identity["config"] = _fitting_parameters(saved_identity["config"])
        if saved_identity == identity and saved["npz_sha256"] == _file_hash(npz):
            return saved["record"]
    raw, ordered, metrics = fit_quantile_signature(
        w, values, config=config, hyperspectral=meta["stage"] in ("raw", "corr")
    )
    temporary = npz.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        np.savez_compressed(
            stream,
            wavelengths_nm=w,
            quantiles=config.quantiles,
            raw_curves=raw,
            ordered_curves=ordered,
            empirical_median=np.ma.median(np.ma.masked_invalid(values), axis=0).filled(
                np.nan
            ),
        )
    temporary.replace(npz)
    record = {
        **meta,
        **metrics,
        "checkpoint": npz.name,
        "low_replication": len(values) < 2
        if meta["level"] == "individual"
        else len(values) < 20,
        "effective_tail_observations": len(values)
        * min(config.quantiles[0], 1 - config.quantiles[-1]),
    }
    temporary = metadata.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {"identity": identity, "record": record, "npz_sha256": _file_hash(npz)},
            indent=2,
        )
        + "\n"
    )
    temporary.replace(metadata)
    return record


def _tasks(plants, data, observations, config):
    selected = plants.species.str.split().str.len().ge(
        2
    ) & ~plants.species.str.casefold().isin(["other", "unidentified"])
    counts = plants.groupby("species").GlobalID.transform("size")
    selected &= counts >= config.min_plants_per_species
    cohort = _split_plants(plants.loc[selected].reset_index(drop=True), config)
    original_index = plants.set_index("GlobalID").assign(index=np.arange(len(plants)))[
        "index"
    ]
    requests = []
    for scope, sub in [("ALL", cohort), *list(cohort.groupby("region"))]:
        for species, group in sub.groupby("species", sort=True):
            if len(group) < config.min_plants_per_species:
                continue
            for partition in ["full", "train"]:
                training = (
                    group if partition == "full" else group[group.partition == "train"]
                )
                positions = original_index.loc[training.GlobalID].to_numpy()
                for stage in config.stages:
                    w, values = data[stage]
                    meta = {
                        "level": "species",
                        "region": scope,
                        "species": species,
                        "GlobalID": "",
                        "stage": stage,
                        "partition": partition,
                        "independent_plants": len(training),
                    }
                    requests.append((meta, w, values[positions]))
    for stage in config.stages:
        obs, columns = observations[stage]
        positions = obs.groupby("GlobalID").indices
        w = data[stage][0]
        for row in cohort.itertuples():
            ix = positions[row.GlobalID]
            meta = {
                "level": "individual",
                "region": row.region,
                "species": row.species,
                "GlobalID": row.GlobalID,
                "stage": stage,
                "partition": "full",
                "independent_plants": 1,
            }
            requests.append((meta, w, obs.iloc[ix][columns].to_numpy(float)))
    return cohort, requests


def _evaluate_matching(cohort, data, index, directory, config):
    results = []
    diagnostics = []
    for stage in config.stages:
        w, all_values = data[stage]
        # Source rows in data are linked by the full plants table via a stored position.
        for scope in ["ALL", *sorted(cohort.region.unique())]:
            candidates = index[
                (index.level == "species")
                & (index.stage == stage)
                & (index.region == scope)
                & (index.partition == "train")
            ]
            if candidates.empty:
                continue
            models = []
            for row in candidates.itertuples():
                with np.load(directory / row.checkpoint) as stored:
                    models.append(
                        (
                            row.species,
                            stored["ordered_curves"],
                            stored["empirical_median"],
                        )
                    )
            queries = cohort[cohort.partition == "held_out"]
            if scope != "ALL":
                queries = queries[queries.region == scope]
            queries = queries[queries.species.isin(candidates.species)]
            for query in queries.itertuples():
                observed = all_values[query.source_position]
                ranking, baseline = [], []
                true_curves = None
                for species, curves, empirical in models:
                    score, bands = quantile_distance(observed, curves, config.quantiles)
                    ranking.append((score, species))
                    finite = np.isfinite(observed) & np.isfinite(empirical)
                    baseline.append(
                        (
                            float(
                                np.sqrt(
                                    np.mean((observed[finite] - empirical[finite]) ** 2)
                                )
                            ),
                            species,
                        )
                    )
                    if species == query.species:
                        true_curves = curves
                ranking.sort()
                baseline.sort()
                record = {
                    "GlobalID": query.GlobalID,
                    "region": query.region,
                    "scope": scope,
                    "stage": stage,
                    "true_species": query.species,
                    "predicted_species": ranking[0][1],
                    "baseline_species": baseline[0][1],
                    "top1_correct": ranking[0][1] == query.species,
                    "top3_correct": query.species in [s for _, s in ranking[:3]],
                    "baseline_correct": baseline[0][1] == query.species,
                    "score": ranking[0][0],
                    "shared_bands": bands,
                }
                if 0.05 in config.quantiles and 0.95 in config.quantiles:
                    lo, hi = (
                        true_curves[config.quantiles.index(0.05)],
                        true_curves[config.quantiles.index(0.95)],
                    )
                    finite = np.isfinite(observed) & np.isfinite(lo) & np.isfinite(hi)
                    record["true_species_05_95_band_coverage"] = float(
                        np.mean(
                            (observed[finite] >= lo[finite])
                            & (observed[finite] <= hi[finite])
                        )
                    )
                results.append(record)
            # Conditional coverage on held-out plants is evidence, not training fit.
    scores = pd.DataFrame(results)
    if not scores.empty:
        summary = (
            scores.groupby(["scope", "stage"])
            .agg(
                held_out_plants=("GlobalID", "size"),
                top1_accuracy=("top1_correct", "mean"),
                top3_accuracy=("top3_correct", "mean"),
                empirical_median_baseline_accuracy=("baseline_correct", "mean"),
            )
            .reset_index()
        )
        for row in summary.to_dict("records"):
            group = scores[
                (scores.scope == row["scope"]) & (scores.stage == row["stage"])
            ]
            row["macro_species_accuracy"] = float(
                group.groupby("true_species").top1_correct.mean().mean()
            )
            if "true_species_05_95_band_coverage" in group:
                row["true_species_05_95_band_coverage"] = float(
                    group.true_species_05_95_band_coverage.mean()
                )
            diagnostics.append(row)
    return scores, pd.DataFrame(diagnostics)


def rank_unknown_spectrum(
    output_dir,
    wavelengths_nm,
    values,
    *,
    stage="corr",
    region=None,
    level="species",
    exclude_plant_ids=(),
    minimum_shared_fraction=0.5,
    allow_unverified_export_coordinates=False,
):
    """Rank supplied native-unit spectra against full quantile references.

    Pointwise pinball ranking is exploratory; scores are not identification
    probabilities. Query gaps/exclusions are preserved, with no extrapolation.
    Individual references represent repeated observations of one polygon.
    """
    if stage not in _STAGES or not 0 < minimum_shared_fraction <= 1:
        raise ValueError("Invalid stage or shared wavelength fraction")
    root = Path(output_dir)
    completion = root / "quantile_manifest.json"
    if not completion.is_file():
        raise ValueError("Quantile reference library must complete before matching")
    manifest = json.loads(completion.read_text())
    if (
        _file_hash(root / "model_index.parquet")
        != manifest["outputs"]["model_index.parquet"]
    ):
        raise ValueError("Quantile model index checksum failed")
    index = pd.read_parquet(root / "model_index.parquet")
    selected = index[
        (index.level == level) & (index.stage == stage) & (index.partition == "full")
    ]
    if level == "species":
        selected = selected[selected.region == (region or "ALL")]
    elif level == "individual":
        if region:
            selected = selected[selected.region == region]
        selected = selected[~selected.GlobalID.isin(exclude_plant_ids)]
    else:
        raise ValueError("Select species or individual reference level")
    if selected.empty:
        raise ValueError("No matching model references for requested scope/stage")
    rows = []
    queries = {}
    for reference in selected.itertuples():
        path = root / "checkpoints" / reference.checkpoint
        if _file_hash(path) != manifest["outputs"][str(path.relative_to(root))]:
            raise ValueError("Quantile reference checkpoint checksum failed")
        with np.load(path) as stored:
            target, q, curves = (
                stored["wavelengths_nm"],
                stored["quantiles"],
                stored["ordered_curves"],
            )
        if (
            stage == "micasense"
            and _micasense_labels_unverified(target)
            and not allow_unverified_export_coordinates
        ):
            raise ValueError(
                "MicaSense exported wavelength labels are unverified; physical-wavelength matching is blocked. Use verified source metadata, or explicitly allow unverified export coordinates for archive-only comparisons."
            )
        key = target.tobytes()
        if key not in queries:
            queries[key] = harmonize_spectrum(
                wavelengths_nm,
                values,
                target,
                excluded=((1340, 1450), (1790, 2000))
                if stage in ("raw", "corr")
                else (),
                max_gap_nm=8 if stage in ("raw", "corr") else 0,
            )
        query = queries[key]
        supported = np.isfinite(curves).all(axis=0).sum()
        score, bands = quantile_distance(
            query,
            curves,
            q,
            minimum_bands=max(2, int(np.ceil(supported * minimum_shared_fraction))),
        )
        rows.append(
            {
                "species": reference.species,
                "region": reference.region,
                "GlobalID": reference.GlobalID,
                "level": level,
                "stage": stage,
                "score": score,
                "shared_bands": bands,
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(["score", "species", "GlobalID"])
        .reset_index(drop=True)
    )


def run_boosted_quantile_atlas(
    comparisons_dir, output_dir, *, config=None, make_individual_pdf=True
):
    """Fit species/site and individual-polygon quantile signatures with checkpoints.

    All 1–99% quantiles are jointly trained with separate quantile tree outputs.
    Uses completed compact tables only. Models/plots are derivatives; original
    pixel library and parent plant tables remain immutable.
    """
    config = config or QuantileModelConfig()
    config.validate()
    xgb = _xgboost()
    comparisons, out = Path(comparisons_dir), Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    directory = out / "checkpoints"
    directory.mkdir(exist_ok=True)
    plants, data, observations, audits, hashes = _model_inputs(comparisons)
    identity = json.loads(
        json.dumps(
            {
                "inputs": hashes,
                "config": asdict(config),
                "xgboost": xgb.__version__,
                "implementation": _file_hash(__file__),
            }
        )
    )
    manifest_path = out / "quantile_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if (
            manifest["identity"] == identity
            and manifest["make_individual_pdf"] == make_individual_pdf
            and all(
                (out / name).is_file() and _file_hash(out / name) == digest
                for name, digest in manifest["outputs"].items()
            )
        ):
            _LOG.info("Reusing verified completed quantile atlas")
            return json.loads((out / "quantile_audit.json").read_text())
    cohort, requests = _tasks(plants, data, observations, config)
    if not requests:
        raise ValueError("No species meet the independent-plant threshold")
    positions = plants.set_index("GlobalID").assign(position=np.arange(len(plants)))[
        "position"
    ]
    cohort["source_position"] = positions.loc[cohort.GlobalID].to_numpy()
    cohort.to_parquet(out / "training_holdout_plants.parquet", index=False)
    _LOG.info(
        "Fitting %s signatures: %s quantiles, %s workers",
        len(requests),
        len(config.quantiles),
        config.workers,
    )
    records = []
    with ThreadPoolExecutor(max_workers=config.workers) as executor:
        pending = {
            executor.submit(
                _fit_checkpoint, directory, meta, w, values, config, identity
            ): meta
            for meta, w, values in requests
        }
        for future in as_completed(pending):
            records.append(future.result())
            if len(records) % 20 == 0 or len(records) == len(requests):
                _LOG.info(
                    "Quantile signatures completed: %s/%s; last=%s/%s/%s",
                    len(records),
                    len(requests),
                    records[-1]["level"],
                    records[-1]["region"],
                    records[-1]["species"],
                )
    index = pd.DataFrame(records).sort_values(
        ["level", "partition", "region", "species", "GlobalID", "stage"]
    )
    coordinate_status = {
        stage: (
            "unverified_export_labels"
            if stage == "micasense" and _micasense_labels_unverified(data[stage][0])
            else "supplied_grid"
        )
        for stage in config.stages
    }
    index["coordinate_status"] = index.stage.map(coordinate_status)
    index.to_parquet(out / "model_index.parquet", index=False)
    scores, summary = _evaluate_matching(cohort, data, index, directory, config)
    if not scores.empty:
        scores["coordinate_status"] = scores.stage.map(coordinate_status)
    if not summary.empty:
        summary["coordinate_status"] = summary.stage.map(coordinate_status)
    scores.to_csv(out / "held_out_species_matches.csv", index=False)
    summary.to_csv(out / "matching_validation.csv", index=False)
    # Individual matching is evaluated against other training plants, never itself.
    individual_results = _evaluate_individual_matching(
        cohort, data, index, directory, config
    )
    if not individual_results.empty:
        individual_results["coordinate_status"] = individual_results.stage.map(
            coordinate_status
        )
    individual_results.to_csv(
        out / "held_out_individual_reference_matches.csv", index=False
    )
    _plot_quantile_reports(out, index, config, make_individual_pdf=make_individual_pdf)
    audit = {
        "quantiles": config.quantiles,
        "quantile_lines": len(config.quantiles),
        "config": asdict(config),
        "independent_plants": len(cohort),
        "held_out_plants": int((cohort.partition == "held_out").sum()),
        "models": len(index),
        "full_species_models": int(
            ((index.level == "species") & (index.partition == "full")).sum()
        ),
        "individual_models": int((index.level == "individual").sum()),
        "individual_single_observation_models": int(
            ((index.level == "individual") & (index.spectra == 1)).sum()
        ),
        "crossing_model_count": int((index.crossing_wavelength_fraction > 0).sum()),
        "ordering": "Raw predictions retained; pointwise sorting across quantiles for ordered curves/matching",
        "replication": "Species: independent GlobalID medians; individual: equal repeated-flight polygon medians",
        "interpretation": "Fitted pointwise conditional quantiles are not independent plants or whole-spectrum trajectories",
        "matching": "Held-out GlobalIDs absent from species training and individual reference candidate sets",
        "validation": summary.to_dict("records"),
        "coordinate_status": coordinate_status,
        "micaSense_limit": "Detected legacy padded wavelength labels; archive ordinal-band comparisons only until source headers establish the physical grid",
        "backend": f"xgboost {xgb.__version__}",
    }
    (out / "quantile_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    _, _, _, _, final_hashes = _model_inputs(comparisons)
    if final_hashes != hashes:
        raise ValueError("Compact source products changed during fitting")
    outputs = {
        str(p.relative_to(out)): _file_hash(p)
        for p in out.rglob("*")
        if p.is_file() and p != manifest_path
    }
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(
            {
                "identity": identity,
                "make_individual_pdf": make_individual_pdf,
                "outputs": outputs,
            },
            indent=2,
        )
        + "\n"
    )
    temporary.replace(manifest_path)
    return json.loads(json.dumps(audit))


def _evaluate_individual_matching(cohort, data, index, directory, config):
    """Rank held-out plants against other training polygons within the known site.

    One fit belongs only to its own GlobalID, so filtering the held-out identities
    from references eliminates leakage without refitting individual models.
    """
    results = []
    for stage in config.stages:
        _, values = data[stage]
        for region, group in cohort.groupby("region"):
            held = group[group.partition == "held_out"]
            training_ids = set(group.loc[group.partition == "train", "GlobalID"])
            candidates = index[
                (index.level == "individual")
                & (index.stage == stage)
                & (index.region == region)
                & index.GlobalID.isin(training_ids)
            ]
            if held.empty or candidates.empty:
                continue
            _LOG.info(
                "Held-out individual-reference ranking: %s/%s, %s queries, %s references",
                region,
                stage,
                len(held),
                len(candidates),
            )
            queries = held.reset_index(drop=True)
            query_values = values[queries.source_position.to_numpy()]
            best_scores = np.full(len(queries), np.inf)
            best_ids = np.full(len(queries), "", dtype=object)
            best_species = np.full(len(queries), "", dtype=object)
            for reference in candidates.itertuples():
                with np.load(directory / reference.checkpoint) as stored:
                    curves = stored["ordered_curves"]
                scores = _quantile_distances_many(
                    query_values, curves, config.quantiles
                )
                improve = scores < best_scores
                best_scores[improve] = scores[improve]
                best_ids[improve] = reference.GlobalID
                best_species[improve] = reference.species
            best = {
                row.GlobalID: (float(best_scores[i]), best_ids[i], best_species[i])
                for i, row in enumerate(queries.itertuples())
            }
            bands = int(np.isfinite(curves).all(axis=0).sum())
            for query in held.itertuples():
                score, reference, species = best[query.GlobalID]
                results.append(
                    {
                        "GlobalID": query.GlobalID,
                        "region": region,
                        "stage": stage,
                        "true_species": query.species,
                        "reference_GlobalID": reference,
                        "predicted_species": species,
                        "top1_correct": species == query.species,
                        "score": score,
                        "shared_bands": bands,
                    }
                )
    return pd.DataFrame(results)


def _draw_quantile_panel(ax, records, root, excluded, limits, stages):
    colors = {
        "raw": "#355c70",
        "corr": "#355c70",
        "olioli": "#355c70",
        "micasense": "#8a6544",
    }
    for stage in stages:
        row = records[records.stage == stage]
        if row.empty:
            continue
        with np.load(root / "checkpoints" / row.iloc[0].checkpoint) as stored:
            w = stored["wavelengths_nm"]
            curves = stored["ordered_curves"]
            q = stored["quantiles"]
            empirical = stored["empirical_median"]
        style = "--" if stage == "micasense" else "-"
        ax.plot(
            w,
            curves.T,
            color=colors[stage],
            alpha=0.11,
            linewidth=0.45,
            linestyle=style,
        )
        ax.plot(
            w,
            curves[np.flatnonzero(q == 0.5)[0]],
            color=colors[stage],
            linewidth=1.2,
            linestyle=style,
        )
        ax.plot(w, empirical, color=".25", alpha=0.6, linewidth=0.7, linestyle=":")
        if stage in ("raw", "corr"):
            for lo, hi in excluded:
                ax.axvspan(lo, hi, color=".93", zorder=-1)
    if len(stages) == 1 and stages[0] in ("olioli", "micasense"):
        from matplotlib.ticker import MaxNLocator

        margin = (w[-1] - w[0]) * 0.025
        ax.set_xlim(w[0] - margin, w[-1] + margin)
        ax.xaxis.set_major_locator(MaxNLocator(4))
    else:
        ax.set_xlim(385, 2510)
        ax.set_xticks([500, 1000, 1500, 2000, 2500])
    ax.set_ylim(*limits)
    ax.tick_params(labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)


def _quantile_figure(
    root, records, row_keys, columns, title, limits, excluded, *, individual=False
):
    import matplotlib.pyplot as plt

    unverified = False
    ms = records[records.stage == "micasense"]
    if not ms.empty:
        with np.load(root / "checkpoints" / ms.iloc[0].checkpoint) as stored:
            unverified = _micasense_labels_unverified(stored["wavelengths_nm"])
    height = max(3, len(row_keys) * 1.35)
    fig, axes = plt.subplots(
        len(row_keys),
        len(columns),
        figsize=(3.4 * len(columns) + 2.6, height),
        sharex="col",
        sharey=True,
        squeeze=False,
    )
    fig.subplots_adjust(
        left=0.21,
        right=0.99,
        bottom=0.48 / height,
        top=1 - 0.75 / height,
        hspace=0.2,
        wspace=0.10,
    )
    fig.text(0.21, 1 - 0.07 / height, title, fontsize=10, fontweight="bold", va="top")
    with np.load(root / "checkpoints" / records.iloc[0].checkpoint) as first:
        q = first["quantiles"]
    fig.text(
        0.99,
        1 - 0.3 / height,
        f"{len(q)} fitted quantiles ({q[0] * 100:g}–{q[-1] * 100:g}%); strong 50%; dotted observed median",
        ha="right",
        fontsize=8,
        va="top",
    )
    for i, key in enumerate(row_keys):
        selected = (
            records[records.GlobalID == key]
            if individual
            else records[records.species == key]
        )
        representative = selected.iloc[0]
        for j, (heading, stages) in enumerate(columns):
            ax = axes[i, j]
            _draw_quantile_panel(ax, selected, root, excluded, limits, stages)
            ax.tick_params(labelbottom=i == len(row_keys) - 1)
            if i == 0:
                if unverified and "micasense" in stages:
                    heading = "MicaSense (export labels unverified)"
                ax.set_title(heading, fontsize=10, pad=10)
            if j == 0:
                label = representative.species
                if individual:
                    label += "\n" + key[:13] + "…"
                    sample = f"{representative.spectra} flight observations; one plant"
                else:
                    sample = f"n = {representative.independent_plants} plants"
                ax.text(
                    -0.23,
                    0.62,
                    label,
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontstyle="italic",
                    fontsize=8,
                )
                ax.text(
                    -0.23,
                    0.28,
                    sample,
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontsize=7,
                )
    fig.supxlabel(
        "Wavelength / supplied export label (nm)" if unverified else "Wavelength (nm)",
        fontsize=11,
        y=0.005 / height,
    )
    fig.supylabel("Spectral value (native stored units)", fontsize=11, x=0.006)
    return fig


def _plot_quantile_reports(root, index, config, *, make_individual_pdf):
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from .plant_spectral_comparison import _save

    full = index[index.partition == "full"]
    lo = float(full.plot_min.min())
    hi = float(full.plot_max.max())
    margin = (hi - lo) * 0.04 or 1
    limits = (lo - margin, hi + margin)
    columns = []
    if "raw" in config.stages:
        columns.append(("Raw NEON", ("raw",)))
    if "corr" in config.stages:
        columns.append(("Corrected NEON", ("corr",)))
    if "olioli" in config.stages:
        columns.append(("Landsat OLI (derived)", ("olioli",)))
    if "micasense" in config.stages:
        columns.append(("MicaSense (derived)", ("micasense",)))
    excluded = ((1340, 1450), (1790, 2000))
    with plt.rc_context(
        {"font.family": "DejaVu Sans", "pdf.fonttype": 42, "svg.fonttype": "none"}
    ):
        species = full[full.level == "species"]
        for region, group in species.groupby("region", sort=True):
            _LOG.info("Rendering species quantile atlas: %s", region)
            rows = sorted(group.species.unique(), key=str.casefold)
            fig = _quantile_figure(
                root,
                group,
                rows,
                columns,
                f"{region} — species boosted quantile signatures",
                limits,
                excluded,
            )
            _save(fig, root / f"{region}_species_quantiles", 350)
        individuals = full[full.level == "individual"]
        for region, group in individuals.groupby("region", sort=True):
            # One traceable example per species is a compact PNG/SVG/PDF overview.
            first = (
                group[["species", "GlobalID"]]
                .drop_duplicates()
                .sort_values(["species", "GlobalID"])
                .groupby("species", sort=True)
                .first()
            )
            rows = first.GlobalID.tolist()
            fig = _quantile_figure(
                root,
                group,
                rows,
                columns,
                f"{region} — example individual-plant quantile signatures",
                limits,
                excluded,
                individual=True,
            )
            _save(fig, root / f"{region}_individual_examples", 350)
            if not make_individual_pdf:
                continue
            ids = (
                group[["species", "GlobalID"]]
                .drop_duplicates()
                .sort_values(["species", "GlobalID"])
                .GlobalID.tolist()
            )
            destination = root / f"{region}_all_individual_quantiles.pdf"
            temporary = destination.with_suffix(".pdf.tmp")
            with PdfPages(temporary) as pdf:
                for start in range(0, len(ids), 5):
                    fig = _quantile_figure(
                        root,
                        group,
                        ids[start : start + 5],
                        columns,
                        f"{region} — individual polygons {start + 1}–{min(start + 5, len(ids))} of {len(ids)}",
                        limits,
                        excluded,
                        individual=True,
                    )
                    pdf.savefig(fig)
                    plt.close(fig)
                    if start % 100 == 0:
                        _LOG.info(
                            "Individual PDF %s: %s/%s plants", region, start, len(ids)
                        )
            temporary.replace(destination)


def _quantile_distances_many(observations, ordered_curves, quantiles):
    """Exact vector pinball scores via sorted-quantile prefix sums.

    Avoids a query-by-quantile-by-band tensor when ranking many held-out plants.
    NaN-query cases use the scalar finite-band contract.
    """
    y = np.asarray(observations, float)
    c = np.asarray(ordered_curves, float)
    q = np.asarray(quantiles, float)
    if y.ndim != 2 or c.shape != (len(q), y.shape[1]):
        raise ValueError("Batch queries and curves do not align")
    supported = np.isfinite(c).all(axis=0)
    if supported.sum() < 2:
        raise ValueError("Insufficient shared supported bands for matching")
    c = c[:, supported]
    y = y[:, supported]
    if not np.isfinite(y).all():
        return np.array([quantile_distance(row, c, q)[0] for row in y])
    if np.any(np.diff(c, axis=0) < 0):
        raise ValueError("Batch distance requires ordered quantile curves")
    below = np.column_stack(
        [np.searchsorted(c[:, i], y[:, i], side="left") for i in range(c.shape[1])]
    )
    prefix = np.vstack([np.zeros(c.shape[1]), np.cumsum(c, axis=0)])
    absolute = (
        (2 * below - len(q)) * y + prefix[-1] - 2 * prefix[below, np.arange(c.shape[1])]
    ) / len(q)
    adjustment = 2 * np.mean(q - 0.5) * y - 2 * np.mean((q - 0.5)[:, None] * c, axis=0)
    return np.mean(absolute + adjustment, axis=1)


def _fitting_parameters(parameters):
    """Scope/CPU settings do not alter an already supplied training matrix."""
    return {
        key: parameters[key]
        for key in (
            "quantiles",
            "boosting_rounds",
            "learning_rate",
            "max_depth",
            "max_bin",
            "seed",
        )
    }
