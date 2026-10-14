"""Verify/freeze bounded MESMA evidence and render six scientific figure families."""

from pathlib import Path
import hashlib
import json
import shutil
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from spectralbridge.plant_spectral_comparison import _save
from spectralbridge.mesma_readiness import load_compact_inputs
from spectralbridge.mixtures import shade_model_errors
from spectralbridge.pft_method_audit import wavelength_weights

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "artifacts/plant_spectral_atlas/mesma_readiness"
TABLES = OUT / "tables"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


manifest = json.loads((RUN / "manifests/statistics_manifest.json").read_text())
assert all(sha(RUN / n) == h for n, h in manifest["outputs"].items())
assert manifest["identity"]["code"] == sha(
    ROOT / "src/spectralbridge/mesma_readiness.py"
)
assert manifest["identity"]["mixtures_code"] == sha(
    ROOT / "src/spectralbridge/mixtures.py"
)
exports = []
for path in (RUN / "tables").iterdir():
    if not path.is_file():
        continue
    if path.suffix == ".csv" and path.stat().st_size > 15_000_000:
        data = pd.read_csv(path, float_precision="round_trip")
        destination = TABLES / (path.stem + ".parquet")
        data.to_parquet(destination, index=False, compression="zstd")
        (TABLES / path.name).unlink(missing_ok=True)
        exports.append(
            dict(
                original_name=path.name,
                original_sha256=sha(path),
                compact_name=destination.name,
                compact_sha256=sha(destination),
                rows=len(data),
                conversion="lossless Parquet compression of round-trip-parsed CSV values",
            )
        )
    else:
        shutil.copy2(path, TABLES / path.name)
        exports.append(
            dict(
                original_name=path.name,
                original_sha256=sha(path),
                compact_name=path.name,
                compact_sha256=sha(TABLES / path.name),
            )
        )
(OUT / "manifests" / "table_exports.json").write_text(
    json.dumps(exports, indent=2) + "\n"
)


def read_table(name):
    path = TABLES / (name + ".parquet")
    return (
        pd.read_parquet(path)
        if path.exists()
        else pd.read_csv(TABLES / (name + ".csv"))
    )


shutil.copy2(
    RUN / "manifests/statistics_manifest.json",
    OUT / "manifests/statistics_manifest.json",
)
shutil.copy2(RUN / "manifests/design.json", OUT / "manifests/executed_design.json")
source = ROOT / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
assert sha(source) == manifest["identity"]["source_sha256"]
table, values, waves = load_compact_inputs(
    source, ROOT / "artifacts/plant_spectral_atlas/sensor_pft_transfer/compact"
)
errors = pd.read_csv(TABLES / "fraction_errors.csv")
detection = read_table("detection_errors")
ambiguity = read_table("mixture_ambiguity")
confusion = pd.read_csv(TABLES / "directed_confusion.csv")
members = pd.read_parquet(TABLES / "fold_membership.parquet")
selection = pd.read_csv(TABLES / "endmember_scores.csv")
estimates = pd.read_parquet(TABLES / "abundance_estimates.parquet")
uncertainty = pd.read_csv(TABLES / "uncertainty.csv")
assert (
    errors.negative_fraction_count.max() == 0 and errors.sum_violation_count.max() == 0
)
for (scheme, fold), g in members.groupby(["scheme", "fold"]):
    assert set(g[g.role.eq("train")].GlobalID).isdisjoint(
        g[g.role.eq("test")].GlobalID
    ), (scheme, fold)
# Assert actual source truth belongs only to held-out identities, across every method/sensor.
for (scheme, fold), g in estimates.groupby(["scheme", "fold"]):
    tests = set(
        members[
            (members.scheme == scheme)
            & (members.fold == fold)
            & members.role.eq("test")
        ].GlobalID
    )
    parents = {
        s.split("@")[0] for text in g.source_ids.unique() for s in text.split("|")
    }
    assert parents.issubset(tests), (scheme, fold)

# Primary fold-level macro estimates: neither spectral bands nor mixture draws are replicates.
primary = errors[
    (errors.kind == "plant")
    & errors.method.isin(["EAR_MESMA2", "EAR_MESMA3", "FCLS_medoid", "MC_mean_FCLS"])
]
primary.groupby(["scheme", "sensor", "method"], as_index=False).agg(
    fraction_RMSE=("fraction_RMSE", "mean"),
    fraction_MAE=("fraction_MAE", "mean"),
    reconstruction_RMSE=("mean_reconstruction_RMSE", "mean"),
    class_set_error=("class_set_error", "mean"),
    folds=("fold", "nunique"),
).to_csv(TABLES / "method_comparison.csv", index=False)
errors.groupby(["scheme", "kind", "sensor", "method"], as_index=False).agg(
    median_fraction_RMSE=("fraction_RMSE", "median"),
    p25_fraction_RMSE=("fraction_RMSE", lambda v: v.quantile(0.25)),
    p75_fraction_RMSE=("fraction_RMSE", lambda v: v.quantile(0.75)),
    folds=("fold", "nunique"),
).to_csv(TABLES / "transferability_summary.csv", index=False)
# Exact class-composition ambiguity, rather than interpreting a biological p-value.
a = ambiguity[ambiguity.tolerance.eq(0.01)].copy()
a["best_other_composition"] = a.wrong_composition.map(
    lambda x: " + ".join(k for k, v in json.loads(x).items() if v >= 0.01)
)
a.groupby(
    ["scheme", "kind", "sensor", "label", "best_other_composition"], as_index=False
).agg(
    heldout_records=("ambiguous", "size"),
    ambiguous=("ambiguous", "sum"),
    median_incorrect_RMSE=("incorrect_mixture_RMSE", "median"),
).to_csv(TABLES / "MIXTURE_AMBIGUITY_MATRIX.csv", index=False)
a.groupby(["scheme", "kind", "sensor", "label"], as_index=False).agg(
    heldout_records=("ambiguous", "size"),
    ambiguity_rate=("ambiguous", "mean"),
    median_correct_class_RMSE=("correct_class_RMSE", "median"),
    median_incorrect_RMSE=("incorrect_mixture_RMSE", "median"),
).to_csv(TABLES / "class_ambiguity_summary.csv", index=False)
# Explicit non-forced unknown status; recover year from the matching pure-target ledger.
unknown = read_table("unknown_detection").copy()
identity_fields = ["scheme", "fold", "kind", "sensor", "GlobalID", "label"]
assert (
    unknown[identity_fields]
    .reset_index(drop=True)
    .equals(a[identity_fields].reset_index(drop=True))
)
assert np.allclose(unknown.known_error, a.correct_class_RMSE, equal_nan=True)
unknown["year"] = a.year.to_numpy()
unknown["diagnostic_status"] = np.where(
    unknown.unknown_flagged,
    "NO_ADEQUATE_LIBRARY_MODEL",
    "LOW_RESIDUAL_NOT_VALIDATED_MEMBERSHIP",
)
unknown.to_parquet(
    TABLES / "unknown_model_status.parquet", index=False, compression="zstd"
)

# Training-pool in/out CoB and selected memberships, retaining original algorithm meanings.
records = []
base = table.set_index(["GlobalID", "year"])
cols = np.sqrt(wavelength_weights(waves["NEON"]) * len(waves["NEON"]))
for (scheme, fold), g in selection[selection.EAR.notna()].groupby(["scheme", "fold"]):
    pos = (
        table.reset_index()
        .set_index(["GlobalID", "year"])
        .loc[list(zip(g.GlobalID, g.year))]["index"]
        .to_numpy(int)
    )
    y = values["NEON"][pos] / g.training_scale_stored_units.iloc[0] * cols
    err = shade_model_errors(y, y)
    labels = g.label.to_numpy()
    same = labels[:, None] == labels[None, :]
    for j, row in enumerate(g.itertuples()):
        records.append(
            dict(
                scheme=scheme,
                fold=fold,
                GlobalID=row.GlobalID,
                year=row.year,
                label=row.label,
                EAR=row.EAR,
                MASA=row.MASA,
                in_CoB=int(((err <= 0.02) & same)[:, j].sum()),
                out_CoB=int(((err <= 0.02) & ~same)[:, j].sum()),
                threshold=0.02,
            )
        )
pd.DataFrame(records).to_csv(TABLES / "EAR_MASA_CoB.csv", index=False)
selection[selection.selected_method.notna()].to_csv(
    TABLES / "selected_endmember_membership.csv", index=False
)
# Residual/ambiguity diagnostics are sensitivity thresholds, not an operational classifier.
flags = []
for (scheme, sensor), g in estimates[
    (estimates.kind == "plant") & estimates.method.eq("EAR_MESMA3")
].groupby(["scheme", "sensor"]):
    for residual_limit in [0.005, 0.01, 0.02]:
        accepted = g.reconstruction_RMSE <= residual_limit
        for error_limit in [0.1, 0.2]:
            bad = g.fraction_RMSE > error_limit
            flags.append(
                dict(
                    scheme=scheme,
                    sensor=sensor,
                    residual_limit=residual_limit,
                    fraction_RMSE_limit=error_limit,
                    N=len(g),
                    low_residual_N=int(accepted.sum()),
                    bad_fraction_rate_among_low_residual=float(bad[accepted].mean())
                    if accepted.any()
                    else np.nan,
                    bad_fraction_detection_by_near_range=float(
                        (g.loc[bad, "max_near_fraction_range"] > 0.2).mean()
                    )
                    if bad.any()
                    else np.nan,
                )
            )
pd.DataFrame(flags).to_csv(TABLES / "unreliable_fraction_flags.csv", index=False)

plt.rcParams.update(
    {
        "font.size": 10,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def save(fig, name, caption):
    fig.text(0.055, 0.015, caption, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.075, 1, 0.965))
    _save(fig, FIG / name, 300)


# Figure 1: support, full-value PCA and class spectral distributions with real gaps.
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
support = (
    table.groupby(["site", "year", "cover_category"])
    .GlobalID.nunique()
    .unstack("cover_category")
    .fillna(0)
)
support.plot.bar(stacked=True, ax=axes[0, 0], colormap="tab10")
axes[0, 0].set_title("Distinct polygon IDs per site/year; years repeat identities")
axes[0, 0].set_ylabel("GlobalIDs")
axes[0, 0].tick_params(axis="x", rotation=25)
y = values["NEON"]
center = y.mean(0)
u, s, v = np.linalg.svd(y - center, full_matrices=False)
pc = (y - center) @ v[:2].T
for label, g in table.groupby("cover_category"):
    axes[0, 1].scatter(
        pc[g.index, 0], pc[g.index, 1], s=7, alpha=0.45, label=label, rasterized=True
    )
axes[0, 1].set(
    xscale="symlog",
    yscale="symlog",
    xlabel="PC1 score (stored units; symlog)",
    ylabel="PC2 score (symlog)",
    title="All polygon-years; no PCA outlier deletion",
)
for label, g in table.groupby("cover_category"):
    med = np.median(y[g.index], 0)
    lo, hi = np.quantile(y[g.index], [0.25, 0.75], axis=0)
    # NaN breaks inserted only for plotting disconnected supported segments.
    x = waves["NEON"].copy()
    gap = np.flatnonzero(np.diff(x) > 8) + 1
    for arrname in ["x", "med", "lo", "hi"]:
        arr = locals()[arrname]
        for j in gap[::-1]:
            arr = np.insert(arr, j, np.nan)
        if arrname == "x":
            xx = arr
        elif arrname == "med":
            mm = arr
        elif arrname == "lo":
            ll = arr
        else:
            hh = arr
    line = axes[1, 0].plot(xx, mm, label=label)[0]
    axes[1, 0].fill_between(xx, ll, hh, color=line.get_color(), alpha=0.12)
axes[1, 0].set(
    xlabel="Supported NEON wavelength (nm)",
    ylabel="Native stored spectral value",
    title="Median and IQR; not pure endmember confidence intervals",
)
q = pd.read_csv(TABLES / "native_pixel_qc.csv").pivot(
    index="flight_id", columns="stage", values="mean_supported_second_difference_RMS"
)
axes[1, 1].scatter(q.raw, q["corr"], s=16, alpha=0.7)
lims = [min(q.min()), max(q.max())]
axes[1, 1].plot(lims, lims, "k--")
axes[1, 1].set(
    xscale="log",
    yscale="log",
    xlabel="Raw roughness (native stored units)",
    ylabel="Corrected roughness",
    title="122 flights: second differences outside absorption gaps",
)
axes[0, 0].legend(fontsize=8)
axes[1, 0].legend(fontsize=8)
save(
    fig,
    "01_library_atlas",
    "Polygon-year and flight summaries are descriptive, spatially/repeatedly sampled. PCA includes all values; symlog axes disclose the large dynamic range.\nPhysical reflectance scaling, saturation flags and purity are not verified for this merged library. Gaps are not interpolated.",
)

# Figure 2: directed target->candidate errors and wrong-mixture ambiguity.
fig, axes = plt.subplots(2, 2, figsize=(15, 11))
for j, sensor in enumerate(["NEON", "OLI"]):
    c = confusion[
        (confusion.scheme == "researcher")
        & (confusion.kind == "plant")
        & (confusion.sensor == sensor)
    ]
    matrix = (
        c.groupby(["target_class", "model_class"])
        .median_shade_model_RMSE.median()
        .unstack()
    )
    im = axes[0, j].imshow(matrix, aspect="auto", cmap="magma_r")
    fig.colorbar(im, ax=axes[0, j], fraction=0.035)
    axes[0, j].set(
        xticks=range(len(matrix.columns)),
        yticks=range(len(matrix.index)),
        xticklabels=matrix.columns,
        yticklabels=matrix.index,
        title=f"{sensor}: directed candidate+shade reconstruction",
    )
    axes[0, j].tick_params(axis="x", rotation=35)
    c = a[(a.scheme == "inferred_pft") & (a.kind == "plant") & (a.sensor == sensor)]
    rates = c.groupby("label").ambiguous.mean()
    axes[1, j].bar(rates.index, rates.values, color="#327b88")
    axes[1, j].set(
        ylim=(0, 1),
        ylabel="Wrong mixture no worse than own candidate + tolerance",
        title=f"{sensor}: held-out PFT nominal-pure ambiguity, tolerance 0.01",
    )
save(
    fig,
    "02_identifiability",
    "Top panels use the declared candidate+ideal black shade model (EAR-style), and are directed. Bottom uses no-shade candidate vs convex OTHER-class mixtures.\nTolerance is 0.01 of a training-only RMS scale, not reflectance or a universal noise floor. A biological spectral difference is not a fraction-identifiability result.",
)

# Figure 3: size curves and held-out method comparisons.
fig, axes = plt.subplots(3, 2, figsize=(15, 14))
lib = pd.read_csv(TABLES / "library_size.csv")
methods = pd.read_csv(TABLES / "method_comparison.csv")
for j, sensor in enumerate(["NEON", "OLI"]):
    library_subset = lib[
        (lib.scheme == "researcher")
        & lib.sensor.eq(sensor)
        & lib.status.eq("evaluated")
    ]
    for method, g in library_subset.groupby("method"):
        m = g.groupby("requested_per_class").median_RMSE.mean()
        axes[0, j].plot(m.index, m.values, "o-", label=method)
    axes[0, j].set(
        xlabel="Requested endmembers/class (common training candidate budget 12)",
        ylabel="Mean class/fold median modelling RMSE",
        title=f"{sensor}: held-out cover-category modelling",
    )
    axes[0, j].legend(ncol=2, fontsize=8)
    d = errors[
        (errors.scheme == "researcher")
        & errors.kind.eq("plant")
        & errors.sensor.eq(sensor)
        & ~errors.method.str.contains("stress")
    ]
    means = d.groupby("method").fraction_RMSE.mean().sort_values()
    axes[2, j].barh(means.index, means.values, color="#327b88")
    axes[2, j].set(
        xlabel="Macro class/fold fraction RMSE",
        title=f"{sensor}: bounded controlled recovery; no method selected on test",
    )
    sizes = pd.read_csv(TABLES / "library_size_fraction_recovery.csv")
    sizes = sizes[sizes.status.eq("evaluated") & sizes.sensor.eq(sensor)]
    for scheme, g in sizes.groupby("scheme"):
        curve = g.groupby("requested_per_class").fraction_RMSE.mean()
        axes[1, j].plot(curve.index, curve.values, "o-", label=scheme)
    axes[1, j].set(
        xlabel="EAR entries/class; exact model budget 20,000",
        ylabel="Macro fraction RMSE",
        title=f"{sensor}: known-fraction recovery vs library size",
    )
    axes[1, j].legend(fontsize=8)
save(
    fig,
    "03_library_optimization",
    "EAR/MASA multi-entry ranks and size-limited IES are explicit adaptations. CoB can stop early; IES may omit a rare class. Exact selections are archived.\n12 candidate identities/class is a controlled budget, not evidence of saturation at 12. Requested 20/50/100 entries remain untested; accumulation coverage is separately measured up to 500.",
)

# Figure 4: recovery and detection for predeclared strong/weak PFT contrasts.
fig, axes = plt.subplots(2, 3, figsize=(17, 10))
for j, (ca, cb) in enumerate([("DBS", "ECT"), ("DBT", "ECT"), ("DBT", "ECS")]):
    for sensor, color in [("NEON", "#237b85"), ("OLI", "#bd7541")]:
        g = estimates[
            (estimates.scheme == "inferred_pft")
            & estimates.kind.eq("plant")
            & estimates.method.eq("EAR_MESMA3")
            & estimates.sensor.eq(sensor)
        ].copy()
        truth = g.true_fractions.map(json.loads)
        keep = truth.map(
            lambda t: all(v == 0 for c, v in t.items() if c not in [ca, cb])
        )
        g = g[keep]
        truth = truth[keep]
        x = np.array([v.get(ca, 0) for v in truth])
        z = np.array([json.loads(v).get(ca, 0) for v in g.estimated_fractions])
        frame = pd.DataFrame({"truth": x, "estimate": z})
        curve = frame.groupby("truth").estimate
        axes[0, j].plot(
            curve.median().index, curve.median().values, "o-", color=color, label=sensor
        )
        axes[0, j].fill_between(
            curve.median().index,
            curve.quantile(0.25).values,
            curve.quantile(0.75).values,
            color=color,
            alpha=0.12,
        )
        detection_ = (
            frame.assign(detected=frame.estimate >= 0.1)
            .groupby("truth")
            .detected.mean()
        )
        axes[1, j].plot(
            detection_.index, detection_.values, "o-", color=color, label=sensor
        )
    axes[0, j].plot([0, 1], [0, 1], "k--")
    axes[0, j].set(
        xlabel=f"True {ca} fraction",
        ylabel="Estimated fraction, median and IQR",
        ylim=(0, 1),
        title=f"{ca} vs {cb}",
    )
    axes[1, j].set(
        xlabel=f"True {ca} fraction",
        ylabel="Conditional detection frequency (estimate >= 0.10)",
        ylim=(0, 1),
        title="At true zero, frequency is false-positive rate",
    )
axes[0, 0].legend()
axes[1, 0].legend()
save(
    fig,
    "04_fraction_recovery",
    "Mixtures are generated from held-out empirical polygon spectra, absent from the candidate pool in ALL acquisitions. Identical source IDs/fractions across sensors.\nCurves share parents; displayed counts are simulation draws, not independent biological replicates. These are nominal-label mixtures, not validated pure-material fractional cover.",
)

# Figure 5: paired sensor loss, geography and endmember-choice uncertainty.
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
paired = pd.read_csv(TABLES / "sensor_comparison.csv")
p = paired[(paired.kind == "plant") & paired.method.eq("EAR_MESMA3")]
for scheme, g in p.groupby("scheme"):
    axes[0, 0].scatter(g.NEON, g.OLI, label=scheme, s=25, alpha=0.65)
lim = max(p.NEON.max(), p.OLI.max()) * 1.05
axes[0, 0].plot([0, lim], [0, lim], "k--")
axes[0, 0].set(
    xlabel="NEON class/fold fraction RMSE",
    ylabel="OLI same sources and candidates",
    title="Spectral-representation comparison, not real Landsat",
)
axes[0, 0].legend(fontsize=8)
d = errors[(errors.scheme == "researcher") & errors.method.eq("EAR_MESMA3")]
for sensor, g in d.groupby("sensor"):
    cats = ["plant", "flight", "year", "within_site_year", "site"]
    vals = [g[g.kind.eq(c)].fraction_RMSE.median() for c in cats]
    axes[0, 1].plot(cats, vals, "o-", label=sensor)
axes[0, 1].set(
    ylabel="Median class/fold fraction RMSE",
    title="Higher-level holdouts; unsupported folds excluded explicitly",
)
axes[0, 1].legend()
u = uncertainty[
    uncertainty.interpretation.eq(
        "endmember_choice_stability_not_calibrated_confidence"
    )
]
for sensor, g in u.groupby("sensor"):
    axes[1, 0].scatter(
        g.mean_interval_width,
        g.conditional_interval_coverage,
        label=sensor,
        s=20,
        alpha=0.6,
    )
axes[1, 0].axhline(0.95, color="black", ls="--")
axes[1, 0].set(
    ylim=(0, 1),
    xlabel="Mean empirical 95% endmember-choice interval width",
    ylabel="Truth inside interval (conditional simulation)",
    title="Monte Carlo spread is not automatic 95% calibration",
)
axes[1, 0].legend()
f = pd.read_csv(TABLES / "unreliable_fraction_flags.csv")
f = f[f.residual_limit.eq(0.01) & f.fraction_RMSE_limit.eq(0.1)]
for sensor, g in f.groupby("sensor"):
    axes[1, 1].plot(
        g.scheme, g.bad_fraction_rate_among_low_residual, "o-", label=sensor
    )
for row in f.itertuples():
    if np.isfinite(row.bad_fraction_rate_among_low_residual):
        axes[1, 1].annotate(
            f"n={row.low_residual_N}",
            (
                list(f.scheme.unique()).index(row.scheme),
                row.bad_fraction_rate_among_low_residual,
            ),
            xytext=(0, -16),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
axes[1, 1].text(
    0.03,
    0.08,
    "NEON: n=0 below this cutoff; conditional rate undefined",
    transform=axes[1, 1].transAxes,
    fontsize=8,
)
axes[1, 1].set(
    ylim=(0, 1),
    ylabel="Fraction RMSE >0.10 among residual <=0.01",
    title="A small residual can give false confidence",
)
axes[1, 1].legend()
save(
    fig,
    "05_sensor_and_transfer",
    "NEON uses disconnected wavelength quadrature, OLI equal channels; differences include the declared spectral weighting. No per-spectrum brightness normalization.\nAll flight targets use actual held-out-flight spectra. Repeated identities are purged across dates; missing class/fold support remains in fold_support.csv. Real abundance truth is unavailable.",
)

# Figure 6: explicit readiness dimensions and material operational gate matrix.
fig, axes = plt.subplots(1, 2, figsize=(16, 10))
labels = [
    "Spectral integrity",
    "Material coverage",
    "Representativeness",
    "Distinguishability",
    "Mixture identifiability",
    "Fraction recovery",
    "Transferability",
    "Sensor robustness",
    "Uncertainty calibration",
    "Computation",
]
status = [
    "PARTIAL: grids/masks valid; absolute scales missing",
    "PARTIAL: Rock/Bare/dead labels; water/snow/litter/shade gaps",
    "PARTIAL: library holdouts, no same-site full imagery",
    "CONDITIONAL: sampled-group differences previously shown",
    "TESTED: substantial other-class convex ambiguity",
    "TESTED: conditional synthetic fraction errors, no real truth",
    "TESTED: bounded grouped holdouts; some unavailable",
    "TESTED: paired synthetic OLI only; no abundance ground truth",
    "NOT ESTABLISHED: empirical bundles not calibrated intervals",
    "FEASIBLE: bounded candidates, exact search and checkpoints",
]
axes[0].axis("off")
for i, (label, text) in enumerate(zip(labels, status)):
    y = 0.94 - i * 0.087
    axes[0].text(0, y, label, weight="bold", fontsize=11)
    axes[0].text(0, y - 0.035, text, fontsize=9)
rows = [
    "Green vegetation",
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "NPV / dead",
    "Rock",
    "Bare (not verified soil)",
    "Soil",
    "Water / snow",
    "Measured shade",
    "Species-level",
]
axes[1].axis("off")
axes[1].text(
    0, 0.98, "Operational material-abundance readiness", fontsize=13, weight="bold"
)
for i, label in enumerate(rows):
    y = 0.91 - i * 0.065
    axes[1].text(0, y, label, fontsize=10)
    axes[1].text(0.49, y, "INSUFFICIENT EVIDENCE", fontsize=9, color="#8e4b34")
axes[1].text(
    0,
    0.04,
    "Same status for NEON and Landsat-like abundance.\nNo cell is promoted to READY from a synthetic-only fit.",
    fontsize=10,
)
save(
    fig,
    "06_readiness_dimensions",
    "No opaque readiness score. Current support is for labelled-library diagnostics and explicitly conditional synthetic mixtures, not operational ecological abundance.\nMissing source-scale/purity/reference fractions are blocking data problems. Each material conclusion is tied to quantitative tables or explicitly insufficient evidence.",
)

groups = pd.read_csv(TABLES / "group_accumulation.csv")
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
for ax, field in zip(axes.flat, ["GlobalID", "species", "site", "year"]):
    for sensor, g in groups[groups.accumulated_by.eq(field)].groupby("sensor"):
        curve = g.groupby("groups").median_nearest_RMSE.median()
        ax.plot(curve.index, curve.values, "o-", label=sensor)
    ax.set(
        xlabel=f"Added training {field} groups",
        ylabel="Held-out-library nearest RMSE (stored units)",
        title="Identity-disjoint targets; not full-image coverage",
    )
    ax.legend()
save(
    fig,
    "S1_group_coverage",
    "Ten group-ordering replicates; medians shown. These reflect coverage of held-out library records, not landscape completeness or independent ecological replication.\nGroup additions change class composition/environment together; no causal site/year effect is identified.",
)

checks = dict(
    source_sha256=sha(source),
    analysis_outputs_verified=len(manifest["outputs"]),
    mixture_estimates=len(estimates),
    fold_membership_records=len(members),
    unique_supported_folds=int(errors[["scheme", "fold"]].drop_duplicates().shape[0]),
    unit_tests="see VALIDATION.md and checks/",
    independent_fraction_truth="NOT YET AVAILABLE",
)
(OUT / "manifests" / "interpretation_checks.json").write_text(
    json.dumps(checks, indent=2) + "\n"
)
print(json.dumps(checks, indent=2))
