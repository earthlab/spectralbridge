"""Conditional empirical PFT contrasts; fitted quantile curves are never replicates.

These are associational randomization diagnostics of the supplied sampled plants,
conditional on exchangeability within recorded blocks, not causal/transfer tests.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
import hashlib
import json
import logging
import platform

import scipy

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from .plant_spectral_atlas import _file_hash
from .plant_spectral_pfts import UNASSIGNED, load_pft_crosswalk, tag_pfts
from .plant_spectral_quantiles import _model_inputs
from .plant_spectral_years import _year_plant_spectra

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class PFTStatisticsConfig:
    """Explicit, reproducible inferential choices (not acceptance thresholds)."""
    permutations: int = 9999
    bootstraps: int = 999
    min_plants: int = 10
    seed: int = 20261014
    stages: tuple[str, ...] = ("raw", "corr", "olioli")

    def validate(self):
        if self.permutations < 19 or self.bootstraps < 19 or self.min_plants < 2:
            raise ValueError("Require >=19 resamples and >=2 plants per group")
        if not self.stages or not set(self.stages) <= {"raw", "corr", "olioli"}:
            raise ValueError("MicaSense physical coordinates remain unverified")


def holm(pvalues):
    """Holm family-wise adjustment; valid under arbitrary dependence."""
    p = np.asarray(pvalues, float)
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)):
        raise ValueError("Expected finite probabilities")
    order = np.argsort(p, kind="stable")
    result = np.empty(len(p))
    result[order] = np.minimum(1, np.maximum.accumulate(p[order] * (len(p) - np.arange(len(p)))))
    return result


def _center(values, blocks):
    result = values.copy()
    for block in np.unique(blocks):
        ix = np.flatnonzero(blocks == block)
        result[ix] -= result[ix].mean(axis=0)
    return result


def permute_within(labels, blocks, rng):
    """Shuffle whole plant labels jointly across bands, preserving block counts."""
    result = np.asarray(labels).copy()
    for block in np.unique(blocks):
        ix = np.flatnonzero(blocks == block)
        result[ix] = rng.permutation(result[ix])
    return result


def contrast(values, labels, blocks, *, permutations, bootstraps, seed):
    """Block-adjusted binary coefficient with fixed null scaling and max-T.

    Mixed blocks only; beta weights block contrasts by nA*nB/(nA+nB).
    Null scaling uses block-centered variation independent of PFT labels.
    Whole-curve max |T| and each-band max-T probabilities share one permutation
    distribution. Bootstrap intervals are pointwise/descriptive, not simultaneous.
    """
    y = np.asarray(values, float)
    z = np.asarray(labels, float)
    b = np.asarray(blocks)
    if y.ndim != 2 or len(z) != len(y) or len(b) != len(y):
        raise ValueError("Inconsistent contrast dimensions")
    if set(np.unique(z)) != {0.0, 1.0}:
        raise ValueError("Expected two nonempty binary groups")
    mixed = [v for v in np.unique(b) if len(np.unique(z[b == v])) == 2]
    rows = np.isin(b, mixed)
    y, z, b = y[rows], z[rows], b[rows]
    if not len(y):
        raise ValueError("No within-block PFT overlap")
    valid = np.isfinite(y).all(axis=0)
    yc = _center(y[:, valid], b)
    variance = (yc * yc).sum(axis=0) / (len(y) - len(mixed))
    informative = variance > 0
    columns = np.flatnonzero(valid)[informative]
    yc = yc[:, informative]
    variance = variance[informative]
    if not len(columns):
        raise ValueError("No complete variable spectral features")
    y = y[:, columns]
    xc = _center(z[:, None], b).ravel()
    xx = xc @ xc
    scale = np.sqrt(variance)
    beta = xc @ yc / xx
    denominator = scale / np.sqrt(xx)
    observed = np.abs(beta / denominator)
    rng = np.random.default_rng(seed)
    maxima = np.empty(permutations)
    rank_maxima = np.empty(permutations)
    ranks = np.empty_like(y)
    for block in mixed:
        ix = np.flatnonzero(b == block)
        ranks[ix] = rankdata(y[ix], axis=0, method="average")
    ranks = _center(ranks, b)
    rank_scale = np.sqrt((ranks * ranks).sum(axis=0) / (len(y) - len(mixed)))
    rank_y = ranks / rank_scale
    rank_observed = np.abs(xc @ rank_y / np.sqrt(xx))
    standardized_y = yc / scale
    # Fixed block counts make xx and the label-independent null scale invariant.
    for start in range(0, permutations, 128):
        count = min(128, permutations - start)
        shuffled = np.stack([permute_within(z, b, rng) for _ in range(count)])
        maxima[start:start+count] = np.max(np.abs(shuffled @ standardized_y / np.sqrt(xx)), axis=1)
        rank_maxima[start:start+count] = np.max(np.abs(shuffled @ rank_y / np.sqrt(xx)), axis=1)
    # Inclusive comparison with a numerical tie tolerance; random Monte Carlo +1.
    tolerance = 1e-12 * np.maximum(1.0, observed)
    p_band = (1 + (maxima[:, None] >= observed - tolerance).sum(axis=0)) / (permutations + 1)
    p = (1 + (maxima >= observed.max() - tolerance.max()).sum()) / (permutations + 1)
    p_rank = (1 + (rank_maxima >= rank_observed.max() - 1e-12 * max(1.0, rank_observed.max())).sum()) / (permutations + 1)
    # Sampling independently inside each PFT/block preserves both the estimand
    # and repeated-flight conditioning. Singleton cells cannot estimate variance.
    cells = [np.flatnonzero((b == block) & (z == label))
             for block in mixed for label in (0, 1)]
    draws = np.empty((bootstraps, len(columns)))
    for i in range(bootstraps):
        draw = np.concatenate([rng.choice(ix, len(ix), replace=True) for ix in cells])
        draws[i] = _center(z[draw, None], b[draw]).ravel() @ y[draw] / xx
    lower, upper = np.quantile(draws, [0.025, 0.975], axis=0)
    magnitude = float(np.sqrt(np.mean((beta / scale) ** 2)))
    rms_draws = np.sqrt(np.mean((draws / scale) ** 2, axis=1))
    return {
        "rows": np.flatnonzero(rows), "columns": columns,
        "beta": beta, "scale": scale, "lower": lower, "upper": upper,
        "p_band": p_band, "p": float(p), "p_rank": float(p_rank), "max_t": float(observed.max()),
        "rms_standardized_contrast": magnitude,
        "rms_ci_low": float(np.quantile(rms_draws, .025)),
        "rms_ci_high": float(np.quantile(rms_draws, .975)),
        "mixed_blocks": len(mixed),
        "singleton_cells": sum(len(ix) == 1 for ix in cells),
    }


def _seed(config, key):
    return int(hashlib.sha256((str(config.seed) + key).encode()).hexdigest()[:8], 16)


def _write_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def _history_keys(source):
    """Exact observation histories, including source and local polygon identity."""
    table = source.copy()
    # Polygon indices differ by plant, so they validate provenance but are not
    # part of shared flight exposure: use flight/source pairs as block identity.
    table["_exposure"] = table.apply(
        lambda r: json.dumps([str(r.flight_id), str(r.source_image)]), axis=1
    )
    return table.groupby(["GlobalID", "year"])._exposure.agg(
        lambda x: json.dumps(sorted(set(x)))
    ).rename("flight_history")


def _plot_summary(root, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    eligible = summary[summary.status == "tested"]
    stages = list(eligible.stage.unique())
    pairs = sorted(summary.pair.unique())
    cohorts = sorted(summary.cohort.unique())
    fig, axes = plt.subplots(len(stages), 2, figsize=(13, 4 * len(stages)), squeeze=False)
    for row, stage in enumerate(stages):
        for col, method in enumerate(["site_year", "flight_history"]):
            part = eligible[(eligible.stage == stage) & (eligible.blocking == method)]
            matrix = np.full((len(pairs), len(cohorts)), np.nan)
            for _, rec in part.iterrows():
                matrix[pairs.index(rec.pair), cohorts.index(rec.cohort)] = rec.rms_standardized_contrast
            ax = axes[row, col]
            im = ax.imshow(np.ma.masked_invalid(matrix), aspect="auto", cmap="viridis", vmin=0, vmax=max(1, eligible.rms_standardized_contrast.quantile(.98)))
            for _, rec in part.iterrows():
                marker = "*" if rec.p_holm <= .05 and rec.p_rank_holm <= .05 else ""
                ax.text(cohorts.index(rec.cohort), pairs.index(rec.pair), f"{rec.rms_standardized_contrast:.2f}{marker}", ha="center", va="center", fontsize=8, color="white", bbox={"facecolor":"black", "alpha":.45, "edgecolor":"none"})
            ax.set(xticks=range(len(cohorts)), xticklabels=cohorts, yticks=range(len(pairs)), yticklabels=pairs, title=f"{stage}: {method}")
            ax.tick_params(axis="x", rotation=25)
            fig.colorbar(im, ax=ax, label="RMS standardized block-adjusted contrast")
    fig.suptitle("Sampled-plant PFT differences | * both mean and rank whole-curve adjusted p ≤ 0.05\nBlank = insufficient overlap; magnitude is not classification accuracy", fontsize=12)
    fig.text(.5, .012, "DBS: deciduous broadleaf shrubs | DBT: deciduous broadleaf trees | EBS: evergreen broadleaf shrubs\nECS: evergreen conifer shrubs | ECT: evergreen conifer trees | Color saturates at the 98th percentile of effects", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .05, 1, .96))
    fig.savefig(root / "pft_distinguishability.png", dpi=170)
    fig.savefig(root / "pft_distinguishability.pdf")
    plt.close(fig)


def _plot_effects(root, summary, bands):
    import matplotlib.pyplot as plt
    pairs = sorted(summary.pair.unique())
    cohorts = sorted(summary.cohort.unique())
    fig, axes = plt.subplots(len(pairs), len(cohorts), figsize=(16, 2.1 * len(pairs)), squeeze=False)
    for i, pair in enumerate(pairs):
        for j, cohort in enumerate(cohorts):
            ax = axes[i, j]
            q = summary[(summary.stage == "corr") & (summary.pair == pair) & (summary.cohort == cohort) & (summary.blocking == "flight_history")]
            if q.empty or q.iloc[0].status != "tested":
                ax.text(.5, .5, "Insufficient matched-flight overlap", transform=ax.transAxes, ha="center", fontsize=7)
                ax.set(xticks=[], yticks=[])
            else:
                rec = q.iloc[0]
                sub = bands[bands.test_id == rec.test_id].sort_values("wavelength_nm")
                w = sub.wavelength_nm.to_numpy()
                # Split gaps instead of drawing across excluded atmospheric regions.
                segments = np.split(np.arange(len(w)), np.flatnonzero(np.diff(w) > 8) + 1)
                for ix in segments:
                    ax.plot(w[ix], sub.beta.to_numpy()[ix] / sub.scale.to_numpy()[ix], lw=.7, color="#1765a4")
                    ax.fill_between(w[ix], sub.ci_low.to_numpy()[ix] / sub.scale.to_numpy()[ix], sub.ci_high.to_numpy()[ix] / sub.scale.to_numpy()[ix], alpha=.2, color="#1765a4")
                sig = sub.p_band_fwer <= .05
                ax.scatter(sub.loc[sig, "wavelength_nm"], np.zeros(sig.sum()), s=2, color="crimson")
                ax.text(.02, .96, f"n={int(rec.n_a)}/{int(rec.n_b)}; p={rec.p_holm:.3g}; rank={rec.p_rank_holm:.3g}", transform=ax.transAxes, va="top", fontsize=7)
            ax.axhline(0, color="grey", lw=.5)
            if i == 0:
                ax.set_title(cohort)
            if j == 0:
                ax.set_ylabel(pair + "\nStandardized A − B", fontsize=8)
            if i == len(pairs) - 1:
                ax.set_xlabel("Wavelength (nm)")
    fig.suptitle("Corrected NEON: PFT contrasts conditional on exact flight history\nRibbons: pointwise plant-bootstrap 95% intervals; red: across-family max-T/Bonferroni band evidence\nY limits vary by panel; use the heatmap to compare overall magnitudes", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, .97))
    fig.savefig(root / "corrected_flight_matched_contrasts.png", dpi=140)
    fig.savefig(root / "corrected_flight_matched_contrasts.pdf")
    plt.close(fig)


def run_pft_statistics(comparisons, output, *, config=None, crosswalk=None):
    """Read verified compact products in place and write resumable statistics."""
    config = config or PFTStatisticsConfig()
    config.validate()
    comparisons, root = Path(comparisons), Path(output)
    root.mkdir(parents=True, exist_ok=True)
    (root / "checkpoints").mkdir(exist_ok=True)
    mapping = load_pft_crosswalk(crosswalk)
    _, _, observations, audits, hashes = _model_inputs(comparisons)
    identity = {"config": asdict(config), "sources": hashes,
                "crosswalk": hashlib.sha256(mapping.to_csv(index=False).encode()).hexdigest(),
                "code": _file_hash(Path(__file__)),
                "pft_code": _file_hash(Path(__file__).with_name("plant_spectral_pfts.py")),
                "year_code": _file_hash(Path(__file__).with_name("plant_spectral_years.py")),
                "runtime": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__}}
    identity = json.loads(json.dumps(identity))
    manifest_path = root / "statistics_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["identity"] == identity and all(
            (root / name).is_file() and _file_hash(root / name) == digest
            for name, digest in manifest["outputs"].items()
        ):
            return pd.read_csv(root / "pairwise_tests.csv")
    mapping.to_csv(root / "species_pft_crosswalk.csv", index=False)
    summaries, band_records, members, composition = [], [], [], []
    for stage in config.stages:
        table, cols, source = _year_plant_spectra(observations[stage][0], stage)
        table = tag_pfts(table, mapping)
        table = table.join(_history_keys(source), on=["GlobalID", "year"])
        composition.append(table.assign(stage=stage)[["GlobalID", "species", "site", "year", "pft", "pft_code", "habit_variable", "flight_observations", "stage"]])
        table = table[table.pft != UNASSIGNED].sort_values(["site", "year", "GlobalID"]).reset_index(drop=True)
        if table.duplicated(["GlobalID", "year"]).any():
            raise ValueError("Plant/year replication duplicated")
        wavelengths = np.array([float(c.split("_wl")[1][:-2]) for c in cols])
        for (site, year), cohort in table.groupby(["site", "year"], sort=True):
            for a, b in combinations(sorted(table.pft_code.unique()), 2):
                pair = cohort[cohort.pft_code.isin([a, b])].reset_index(drop=True)
                labels = pair.pft_code.eq(a).astype(int).to_numpy()
                for blocking in ["site_year", "flight_history"]:
                    key = f"{stage}-{site}-{year}-{a}-{b}-{blocking}"
                    blocks = np.zeros(len(pair), int) if blocking == "site_year" else pd.factorize(pair.flight_history)[0]
                    overlap = np.array([len(set(labels[blocks == v])) == 2 for v in blocks], dtype=bool)
                    n_a, n_b = int(((labels == 1) & overlap).sum()), int(((labels == 0) & overlap).sum())
                    meta = {"test_id": key, "stage": stage, "site": site, "year": year,
                            "cohort": f"{site}-{year}", "a": a, "b": b, "pair": f"{a} − {b}",
                            "blocking": blocking, "n_a_available": int((labels == 1).sum()),
                            "n_b_available": int((labels == 0).sum()), "n_a": n_a, "n_b": n_b,
                            "species_a": pair.loc[overlap & (labels == 1), "species"].nunique(),
                            "species_b": pair.loc[overlap & (labels == 0), "species"].nunique()}
                    if min(n_a, n_b) < config.min_plants:
                        summaries.append({**meta, "status": "insufficient_overlap"})
                        continue
                    _LOG.info("%s | matched plants %s/%s | %s permutations", key, n_a, n_b, config.permutations)
                    path = root / "checkpoints" / (key + ".json")
                    saved = json.loads(path.read_text()) if path.exists() else {}
                    if saved.get("identity") == identity:
                        digest = hashlib.sha256(json.dumps(saved["result"], sort_keys=True).encode()).hexdigest()
                        if digest != saved.get("result_sha256"):
                            raise ValueError(f"Checkpoint checksum mismatch: {path}")
                        result = saved["result"]
                    else:
                        calculated = contrast(pair[cols].to_numpy(float), labels, blocks,
                                              permutations=config.permutations, bootstraps=config.bootstraps,
                                              seed=_seed(config, key))
                        result = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in calculated.items()}
                        _write_json(path, {"identity": identity, "result": result, "result_sha256": hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()})
                    summaries.append({**meta, "status": "tested", **{k: result[k] for k in ["p", "p_rank", "max_t", "rms_standardized_contrast", "rms_ci_low", "rms_ci_high", "mixed_blocks", "singleton_cells"]}, "bands": len(result["columns"])})
                    for j, col in enumerate(result["columns"]):
                        band_records.append({"test_id": key, "stage": stage, "wavelength_nm": wavelengths[col],
                                             "column": cols[col], "beta": result["beta"][j], "scale": result["scale"][j],
                                             "ci_low": result["lower"][j], "ci_high": result["upper"][j],
                                             "p_band_max_t": result["p_band"][j]})
                    selected = pair.iloc[result["rows"]].copy()
                    selected["test_id"] = key
                    members.append(selected[["test_id", "GlobalID", "species", "pft_code", "site", "year", "flight_history"]])
    summary = pd.DataFrame(summaries)
    tested = summary.status == "tested"
    family = np.concatenate([summary.loc[tested, "p"].to_numpy(), summary.loc[tested, "p_rank"].to_numpy()])
    adjusted = holm(family)
    summary.loc[tested, "p_holm"] = adjusted[:int(tested.sum())]
    summary.loc[tested, "p_rank_holm"] = adjusted[int(tested.sum()):]
    bands = pd.DataFrame(band_records)
    bands["p_band_fwer"] = np.minimum(1, bands.p_band_max_t * len(family))
    summary.to_csv(root / "pairwise_tests.csv", index=False)
    bands.to_csv(root / "wavelength_tests.csv", index=False)
    pd.concat(members, ignore_index=True).to_parquet(root / "test_membership.parquet", index=False)
    comp = pd.concat(composition, ignore_index=True)
    comp.to_csv(root / "plant_year_pft_tags.csv", index=False)
    comp.groupby(["stage", "site", "year", "pft", "pft_code", "species"], dropna=False).size().rename("plants").reset_index().to_csv(root / "pft_species_composition.csv", index=False)
    _plot_summary(root, summary)
    _plot_effects(root, summary, bands)
    _write_report(root, summary, bands, comp, config, audits)
    outputs = {str(p.relative_to(root)): _file_hash(p) for p in sorted(root.rglob("*")) if p.is_file() and p != manifest_path}
    _write_json(manifest_path, {"identity": identity, "outputs": outputs})
    return summary


def _write_report(root, summary, bands, comp, config, audits):
    tested = summary[summary.status == "tested"]
    codebook = comp[["pft_code", "pft"]].drop_duplicates().sort_values("pft_code")
    lines = ["# PFT distinguishability among the sampled plants", "", "## Scope and methods", "",
             "Empirical plant/year median spectra, not boosted quantile lines or individual pixels, are the replicates. Every contrast is within one site and acquisition year. NIWO repeated years are separate views of overlapping plants, not independent replications.", "",
             "Primary site/year contrasts describe the observed plant mix. Exact flight-history contrasts retain only blocks containing both PFTs and condition on the same set of flight/source products. They target a narrower overlap subset; a change can reflect selection or power, not only confounding.", "",
             "For each binary contrast, regress each band on the centered PFT indicator after removing block means. The coefficient is A minus B, weighted across blocks by nA*nB/(nA+nB). Divide by label-independent block-centered spectral SD for the displayed standardized effect. The functional test uses the maximum absolute standardized coefficient across all complete, variable bands. Shuffle each whole plant PFT label jointly across bands within its block, preserving counts. Finite negative values remain; unsupported/nonfinite or constant bands are excluded from that contrast, never filled.", "",
             f"Monte Carlo permutations: {config.permutations}; bootstrap replicates: {config.bootstraps}; minimum overlap: {config.min_plants} plants per PFT. Inclusive +1 permutation probabilities never equal zero. Holm adjustment covers all {2 * len(tested)} mean/rank whole-curve tests across stages, cohorts and blocking methods. Band evidence for raw-unit mean contrasts uses the permutation maximum over bands and Bonferroni across that same family size. Alpha 0.05 is a reporting convention, not biological importance.", "",
             "The within-block/PFT plant bootstrap gives pointwise 95% band intervals and descriptive RMS intervals conditional on the sampled species and flight histories. Singleton cells contribute no bootstrap variance; intervals can understate spatial, flight, species and trait-assignment uncertainty. An RMS magnitude is nonnegative and has positive finite-sample bias: its interval must not be used as a null-hypothesis test.", "",
             "Permutation validity requires exchangeability within each block under the null; shared spatial environment, unequal distributions and unrecorded covariates can violate it. These are conditional associational diagnostics, not random treatment assignments or causal PFT effects. Species are nested in inferred PFTs; results do not establish a species-independent functional mechanism. No independent-site, new-species classification or sensor calibration claim is tested.", "", "## PFT codebook", ""]
    lines += [f"- {r.pft_code}: {r.pft}" for r in codebook.itertuples()]
    lines += ["", "The rank sensitivity repeats the same blocked maximum-statistic test after average-tie ranking each band within each block. This reduces amplitude-outlier influence and asks about distributional ordering, not raw-unit effect size. Both test versions are included in the Holm family; agreement strengthens robustness but does not establish a pure location effect under unequal distributions.", "", "## Sample support", "",
              f"{comp.GlobalID.nunique()} distinct plant identities across products/years; {comp[comp.pft != UNASSIGNED].GlobalID.nunique()} assigned and {comp[comp.pft == UNASSIGNED].GlobalID.nunique()} unassigned. Counts below use one stage so products do not multiply replication.", "",
              "| Site/year | PFT | Plants | Species |", "| --- | --- | ---: | ---: |"]
    for (site, year, pft), group in comp[comp.stage == comp.stage.iloc[0]].groupby(["site", "year", "pft"]):
        lines.append(f"| {site}-{year} | {pft} | {len(group)} | {group.species.nunique()} |")
    lines += ["", "## Findings by product and conditioning", "", "| Product | Conditioning | Contrasts | Mean p ≤ .05 | Rank p ≤ .05 | Both | Insufficient overlap |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for (stage, blocking), group in summary.groupby(["stage", "blocking"], sort=False):
        valid = group[group.status == "tested"]
        lines.append(f"| {stage} | {blocking} | {len(valid)} | {int(valid.p_holm.le(.05).sum())} | {int(valid.p_rank_holm.le(.05).sum())} | {int((valid.p_holm.le(.05) & valid.p_rank_holm.le(.05)).sum())} | {int(group.status.ne('tested').sum())} |")
    lines += ["", "## Strongest conditional patterns in corrected NEON", ""]
    matched = summary[(summary.stage == "corr") & (summary.blocking == "flight_history")]
    for pair, recs in matched.groupby("pair"):
        supported = recs[(recs.status == "tested") & recs.p_holm.le(.05) & recs.p_rank_holm.le(.05)]
        mean_only = recs[(recs.status == "tested") & recs.p_holm.le(.05) & recs.p_rank_holm.gt(.05)]
        lines.append(f"- **{pair}**: mean and rank evidence in {', '.join(supported.cohort) or 'no tested cohort'}; mean-only evidence in {', '.join(mean_only.cohort) or 'none'}. {int(recs.status.ne('tested').sum())} cohort(s) lack minimum matched-flight support.")
    lines += ["", f"The Monte Carlo minimum unadjusted p is {1/(config.permutations+1):.5g}; equal small adjusted values can reflect this resolution floor, not equal biological differences. Borderline decisions need more permutations. Differences in support or significance between products/conditioning methods are not themselves tests of those methods against each other."]
    lines += ["", "## Wavelength evidence shared across all available cohorts", "",
              "These are intersections of multiplicity-controlled mean-contrast band tests, not causal absorption assignments or band-specific rank tests. Only contrasts supported by both whole-curve tests in every site/year are listed. Isolated wavelengths and short runs are omitted below; the complete values remain in wavelength_tests.csv.", ""]
    for pair, recs in matched.groupby("pair"):
        if recs.status.eq("tested").all() and recs.p_holm.le(.05).all() and recs.p_rank_holm.le(.05).all():
            sets = [set(bands.loc[(bands.test_id == row.test_id) & bands.p_band_fwer.le(.05), "wavelength_nm"]) for row in recs.itertuples()]
            common = np.array(sorted(set.intersection(*sets)))
            intervals = np.split(common, np.flatnonzero(np.diff(common) > 8) + 1)
            spans = [f"{int(v[0])}–{int(v[-1])} nm" for v in intervals if len(v) >= 3]
            lines.append(f"- **{pair}**: {', '.join(spans) or 'no shared contiguous band interval'}.")
    lines += ["", "## Corrected NEON conclusions for each sampled cohort", "", "Distinguishable here means evidence of a spectral association under the recorded assumptions. Nonsignificance means insufficient evidence, **not equivalence** or proof that PFTs have the same spectra.", ""]
    for cohort, group in summary[summary.stage == "corr"].groupby("cohort"):
        lines += ["", f"### {cohort}", "", "| Contrast A − B | Site/year adjusted p | Flight-history mean/rank adjusted p | Matched n A/B | Interpretation |", "| --- | ---: | ---: | --- | --- |"]
        for pair, recs in group.groupby("pair"):
            base = recs[recs.blocking == "site_year"].iloc[0]
            match = recs[recs.blocking == "flight_history"].iloc[0]
            q1 = f"{base.p_holm:.4g}" if base.status == "tested" else "not estimable"
            q2 = f"{match.p_holm:.4g} / {match.p_rank_holm:.4g}" if match.status == "tested" else "not estimable"
            interpretation = ("Supported by mean and rank in matched-flight subset" if match.status == "tested" and match.p_holm <= .05 and match.p_rank_holm <= .05 else "Mean evidence only; rank sensitivity not conclusive" if match.status == "tested" and match.p_holm <= .05 else "Unresolved after flight conditioning" if base.status == "tested" and base.p_holm <= .05 else "No corrected whole-curve evidence at this threshold")
            lines.append(f"| {pair} | {q1} | {q2} | {match.n_a}/{match.n_b} | {interpretation} |")
    lines += ["", "## Interpretation limits and next decisions", "",
              "- PFT tags are species-name trait inferences, not measured individual leaf habit/growth form. Review the saved crosswalk, variable-habit flags and unassigned taxa before final publication; unassigned plants are not forced into a PFT.",
              "- Species count and plant count are distinct. A PFT represented by one species supports statements about that sampled species/PFT combination only. Dominant species and unequal sampling can drive apparent PFT differences; inspect pft_species_composition.csv.",
              "- Raw and corrected NEON are paired transformations of the same plants; derived OLI is a lower-dimensional synthetic view. P-values across products do not rank sensor accuracy or prove that correction improved distinguishability. No physical MicaSense test is included because its exported wavelength coordinates remain unverified (P107).",
              "- Statistical difference does not imply useful classification, ecological importance or equivalence of nonsignificant groups. Interpret effect sizes, direction, intervals, overlap and wavelength patterns together. No universal biological importance margin was supplied, so no equivalence test was invented.",
              "- Flight-history matching is a sensitivity analysis with potentially small/singleton cells, not a full spatial or mixed-effects model. Coordinates, illumination/crown structure and field trait measurements would be needed to test those mechanisms.",
              "- Because the plots were explored before these tests, all results are exploratory/post-exploration evidence; Holm correction covers this recorded test family, not every earlier analytical choice.", "", "## Outputs", "",
              "- pft_distinguishability.png/pdf: RMS effect heatmap, stars mark both mean and rank adjusted whole-curve evidence; blanks are unsupported comparisons.",
              "- corrected_flight_matched_contrasts.png/pdf: standardized A−B curves; shaded pointwise bootstrap intervals and multiplicity-controlled wavelength evidence. Gaps remain gaps. Panel y limits vary; compare overall magnitudes in the heatmap.",
              "- pairwise_tests.csv / wavelength_tests.csv: all test statuses, support, estimates and adjusted probabilities.",
              "- test_membership.parquet / plant_year_pft_tags.csv: exact included identities and full tag/exclusion audit.",
              "- statistics_manifest.json: source/config/code/crosswalk/runtime and output checksums; per-contrast checkpoints permit restart.", "",
              "## Methods references", "",
              "- [Phipson and Smyth: nonzero Monte Carlo permutation probabilities](https://gksmyth.github.io/pubs/PermPValuesPreprint.pdf)",
              "- [Holm: sequential family-wise testing](https://www.jstor.org/stable/4615733)",
              "- [SciPy average-tie ranks](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.rankdata.html)", ""]
    (root / "CONCLUSIONS.md").write_text("\n".join(lines))
