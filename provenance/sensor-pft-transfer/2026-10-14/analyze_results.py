"""Verified interpretation and publication figures for paired OLI retention."""

from pathlib import Path
import hashlib
import json
import shutil

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RUN = ROOT / "artifacts/plant_spectral_atlas/sensor_pft_transfer"
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


manifest = json.loads((RUN / "statistics_manifest.json").read_text())
assert all(digest(RUN / n) == h for n, h in manifest["outputs"].items())
r = pd.read_csv(RUN / "effect_retention.csv")
s = pd.read_csv(RUN / "sensor_contrasts.csv")
b = pd.read_csv(RUN / "band_retention.csv")
c = pd.read_csv(RUN / "cross_sensor_correlations.csv")
cs = pd.read_csv(RUN / "cross_site_consistency.csv")
records = {}
for row in r.itertuples():
    with np.load(RUN / "checkpoints" / (row.test_id + ".npz")) as f:
        records[row.test_id] = {k: f[k] for k in f.files}
# Compare actual primary references, not the older 324-test family.
legacy_a = pd.read_csv(
    ROOT
    / "artifacts/plant_spectral_atlas/pft_method_audit/empirical/method_comparison.csv"
)
legacy_b = pd.read_csv(
    ROOT
    / "artifacts/plant_spectral_atlas/researcher_pft_statistics/method_comparison.csv"
)
validation = []
for scheme, old in [("inferred_pft", legacy_a), ("researcher_category", legacy_b)]:
    old = old[(old.blocking == "flight_history") & (old.status == "tested")].set_index(
        "test_id"
    )
    current = s[(s.scheme == scheme) & (s.sensor == "NEON") & (s.status == "tested")]
    assert len(current) == len(old)
    for row in current.itertuples():
        prior = old.loc[row.legacy_id]
        assert row.n_a == prior.n_a and row.n_b == prior.n_b
        for stat in ["npc", "max", "integrated"]:
            assert abs(getattr(row, "p_" + stat) - prior["p_" + stat]) < 1e-12
            assert (
                abs(getattr(row, "p_" + stat + "_holm") - prior["p_" + stat + "_holm"])
                < 1e-12
            )
        validation.append(
            dict(
                scheme=scheme,
                test_id=row.test_id,
                n_a=row.n_a,
                n_b=row.n_b,
                raw_and_adjusted_probabilities="exactly_reproduced",
            )
        )
pd.DataFrame(validation).to_csv(HERE / "legacy_reproduction.csv", index=False)
# Export native signed curves as compact analytical evidence, not pixel rows.
native_rows = []
for row in r.itertuples():
    rec = records[row.test_id]
    lo, hi = np.quantile(rec["NEON_delta_boot"], [0.025, 0.975], axis=0)
    for j, wave in enumerate(rec["NEON_w"]):
        native_rows.append(
            dict(
                test_id=row.test_id,
                scheme=row.scheme,
                cohort=row.cohort,
                contrast=row.contrast,
                wavelength_nm=wave,
                beta=rec["NEON_beta"][j],
                standardized_delta=rec["NEON_delta"][j],
                pointwise_lo=lo[j],
                pointwise_hi=hi[j],
                NPC_adjusted_p=row.NEON_p_holm,
            )
        )
pd.DataFrame(native_rows).to_csv(HERE / "neon_signed_contrasts.csv", index=False)

# Retention percentages summarize dependent contrasts; bootstrap median ratio is
# conditional on observed sites/history strata, not random independent contrasts.
summary = []
for scheme, g in r.groupby("scheme"):
    ratios = np.column_stack(
        [
            records[k]["OLI_effect_boot"] / records[k]["NEON_effect_boot"]
            for k in g.test_id
        ]
    )
    med = np.median(ratios, axis=1)
    lo, hi = np.quantile(med, [0.025, 0.975])
    supported = g.NEON_supported
    summary.append(
        dict(
            scheme=scheme,
            eligible=len(g),
            NEON_supported=int(supported.sum()),
            retained=int(g.loc[supported, "OLI_supported"].sum()),
            retention_percent=100 * float(g.loc[supported, "OLI_supported"].mean()),
            NEON_unsupported=int((~supported).sum()),
            unsupported_remains_unsupported=int(
                (~g.loc[~supported, "OLI_supported"]).sum()
            ),
            median_effect_ratio=float(g.OLI_NEON_ratio.median()),
            median_ratio_lo=lo,
            median_ratio_hi=hi,
            all_band_direction_agreements=int(g.band_directions_preserved.sum()),
            band_comparisons=int(g.bands.sum()),
            dark_max_delta_error=float(g.dark_invariance_error.max()),
            width_decision_changes=int(
                (g.OLI_supported != g.OLI_width_supported).sum()
            ),
        )
    )
summary = pd.DataFrame(summary)
summary.to_csv(HERE / "retention_summary.csv", index=False)
# Rank order within cohort; do not silently average dissimilar cohort support.
ranks = []
for (scheme, cohort), g in r.groupby(["scheme", "cohort"]):
    for row, nrank, orank in zip(
        g.itertuples(), rankdata(-g.NEON_effect), rankdata(-g.OLI_effect)
    ):
        ranks.append(
            dict(
                scheme=scheme,
                cohort=cohort,
                contrast=row.contrast,
                NEON_rank=nrank,
                OLI_rank=orank,
                rank_change=orank - nrank,
            )
        )
pd.DataFrame(ranks).to_csv(HERE / "contrast_ranks.csv", index=False)
# Recheck quoted recurring intervals using the CURRENT legacy matched-family
# simultaneous maximum envelopes across all four represented cohorts.
e = pd.read_csv(
    ROOT / "artifacts/plant_spectral_atlas/pft_method_audit/empirical/envelopes.csv"
)
regions = []
for a, bb, intervals in [
    ("DBS", "ECT", [(1500, 1785), (2260, 2285)]),
    ("DBT", "ECT", [(955, 1030), (1140, 1335), (1550, 1785)]),
]:
    old = legacy_a[
        (legacy_a.a == a)
        & (legacy_a.b == bb)
        & (legacy_a.blocking == "flight_history")
        & (legacy_a.status == "tested")
    ]
    selected = e[e.test_id.isin(old.test_id)]
    for lo, hi in intervals:
        supported = []
        for test_id, sub in selected.groupby("test_id"):
            window = sub[(sub.wavelength_nm >= lo) & (sub.wavelength_nm <= hi)]
            supported.append(float(window.excursion_family.mean()))
        for name, center, width in zip(
            ["Coastal", "Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"],
            [443, 482, 561.4, 654.6, 864.7, 1608.9, 2200.7],
            [16, 60, 57.3, 37.5, 28.3, 84.7, 186.7],
        ):
            from scipy.special import ndtr

            sigma = width / 2.354820045
            mass = float(ndtr((hi - center) / sigma) - ndtr((lo - center) / sigma))
            regions.append(
                dict(
                    a=a,
                    b=bb,
                    region_start_nm=lo,
                    region_end_nm=hi,
                    cohorts=len(supported),
                    minimum_fraction_family_excursions=min(supported),
                    all_cohorts_all_gridpoints=all(v == 1 for v in supported),
                    OLI_band=name,
                    Gaussian_response_fraction_in_interval=mass,
                    half_max_overlap=bool(
                        center - width / 2 <= hi and center + width / 2 >= lo
                    ),
                )
            )
pd.DataFrame(regions).to_csv(HERE / "neon_region_coverage.csv", index=False)

plt.rcParams.update(
    {
        "font.size": 10,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
cohorts = ["NIWO-2020", "NIWO-2023", "WREF-2023", "YELL-2023"]
names = {
    "inferred_pft": "Inferred species-to-PFT labels",
    "researcher_category": "Researcher cover categories",
}
short = {
    "Deciduous": "D",
    "Evergreen": "E",
    "Herbaceous": "H",
    "Non-vegetated & dead": "N",
    "Woody shrub": "W",
}


def save(fig, name):
    for ext in ["pdf", "png", "svg"]:
        fig.savefig(FIG / (name + "." + ext), dpi=300, bbox_inches="tight")
    plt.close(fig)


# A: common effect scale, missing support and metadata block distinguished.
vmax = np.ceil(r[["NEON_effect", "OLI_effect"]].to_numpy().max() * 4) / 4
for scheme in names:
    candidates = s[(s.scheme == scheme) & (s.sensor == "NEON")]
    pairs = sorted(candidates.contrast.unique())
    fig, ax = plt.subplots(figsize=(16, 6.5))
    grid = np.full((len(pairs), 12), np.nan)
    for i, pair in enumerate(pairs):
        for j, cohort in enumerate(cohorts):
            row = r[(r.scheme == scheme) & (r.contrast == pair) & (r.cohort == cohort)]
            if len(row):
                grid[i, j] = row.iloc[0].NEON_effect
                grid[i, j + 4] = row.iloc[0].OLI_effect
    cmap = plt.colormaps["YlGnBu"].copy()
    cmap.set_bad("#f4f5f6")
    im = ax.imshow(
        np.ma.masked_invalid(grid), cmap=cmap, vmin=0, vmax=vmax, aspect="auto"
    )
    for i, pair in enumerate(pairs):
        for j, cohort in enumerate(cohorts):
            row = r[(r.scheme == scheme) & (r.contrast == pair) & (r.cohort == cohort)]
            if len(row):
                row = row.iloc[0]
                for offset, sensor in [(0, "NEON"), (4, "OLI")]:
                    value = getattr(row, sensor + "_effect")
                    star = "*" if getattr(row, sensor + "_supported") else ""
                    ax.text(
                        j + offset,
                        i,
                        f"{value:.2f}{star}",
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="white" if value > vmax * 0.56 else "#18313f",
                    )
    ax.add_patch(
        Rectangle(
            (7.5, -0.5),
            4,
            len(pairs),
            facecolor="#e5e8eb",
            hatch="///",
            edgecolor="#c5cbd0",
            lw=0,
        )
    )
    ax.text(
        9.5,
        (len(pairs) - 1) / 2,
        "MicaSense blocked\nUnverified physical band identities",
        ha="center",
        va="center",
        bbox=dict(facecolor="#e5e8eb", edgecolor="none"),
        fontsize=10,
    )
    ax.axvline(3.5, color="white", lw=3)
    ax.axvline(7.5, color="white", lw=3)
    ax.set(
        yticks=np.arange(len(pairs)),
        yticklabels=pairs,
        xticks=np.arange(12),
        xticklabels=cohorts * 3,
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    ax.set_title(names[scheme], pad=35)
    for center, title in [
        (1 / 6, "Corrected NEON"),
        (0.5, "Synthetic OLI"),
        (5 / 6, "MicaSense"),
    ]:
        ax.text(
            center,
            1.02,
            title,
            ha="center",
            va="bottom",
            transform=ax.transAxes,
            fontsize=12,
        )
    fig.colorbar(
        im,
        ax=ax,
        label="RMS standardized contrast (representation-specific weights)",
        fraction=0.025,
        pad=0.02,
    )
    fig.subplots_adjust(bottom=0.28)
    fig.text(
        0.12,
        0.01,
        "* NPC Holm adjusted p < 0.05, family fixed within label system and sensor. White/blank = insufficient common support; hatched = metadata gate.\nNEON: supported wavelength integral. OLI: equal channels. Values compare standardized separation, not literal information fractions.",
        fontsize=9,
    )
    save(fig, "A_effect_heatmap_" + scheme)

# B: paired effects and ratio uncertainty, not binomial retention CI.
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
colors = ["#215e82", "#4d9a98", "#bd7442", "#855a96"]
for ax, scheme in zip(axes, names):
    g = r[r.scheme == scheme]
    for cohort, color in zip(cohorts, colors):
        sub = g[g.cohort == cohort]
        ax.scatter(
            sub.NEON_effect,
            sub.OLI_effect,
            label=cohort,
            s=35,
            color=color,
            edgecolor="white",
            lw=0.4,
        )
    ax.plot([0, vmax], [0, vmax], color="#666666", ls="--", lw=1, label="Identity")
    ax.set(
        xlim=(0, vmax),
        ylim=(0, vmax),
        xlabel="Corrected NEON RMS standardized contrast",
        ylabel="Synthetic OLI RMS standardized contrast",
        title=names[scheme],
    )
    ax.set_aspect("equal")
    ax.legend(fontsize=8, loc="upper left")
fig.text(
    0.08,
    -0.035,
    "Paired observations and histories throughout. Ratios use different declared spectral norms; values above identity do not establish sensor superiority.",
    fontsize=9,
)
fig.tight_layout()
save(fig, "B_effect_retention")

# C: physical discrete points, pointwise paired-bootstrap intervals.
fig, axes = plt.subplots(
    2, 3, figsize=(15, 8), gridspec_kw={"width_ratios": [1.65, 1.2, 0.8]}
)
for i, (a, bb) in enumerate([("DBS", "ECT"), ("DBT", "ECT")]):
    row = r[
        (r.scheme == "inferred_pft")
        & (r.a == a)
        & (r.b == bb)
        & (r.cohort == "NIWO-2023")
    ].iloc[0]
    rec = records[row.test_id]
    for sensor, j in [("NEON", 0), ("OLI", 1)]:
        ax = axes[i, j]
        lo, hi = np.quantile(rec[sensor + "_delta_boot"], [0.025, 0.975], axis=0)
        if sensor == "NEON":
            w = rec["NEON_w"]
            delta = rec["NEON_delta"]
            for ix in np.split(np.arange(len(w)), np.flatnonzero(np.diff(w) > 8) + 1):
                ax.fill_between(w[ix], lo[ix], hi[ix], color="#c6dce8")
                ax.plot(w[ix], delta[ix], color="#174f6b", lw=1.2)
            ax.set_xlabel("Wavelength (nm)")
        else:
            delta = rec["OLI_delta"]
            xx = np.arange(7)
            # Plot intervals independently instead of assuming point estimate is
            # centered inside its percentile bootstrap interval.
            ax.vlines(xx, lo, hi, color="#91552c", lw=1.5)
            ax.scatter(xx, delta, color="#91552c", s=30, zorder=3)
            ax.set(
                xticks=xx,
                xticklabels=[
                    "Coastal\n443",
                    "Blue\n482",
                    "Green\n561",
                    "Red\n655",
                    "NIR\n865",
                    "SWIR1\n1609",
                    "SWIR2\n2201",
                ],
            )
            ax.tick_params(axis="x", labelsize=8)
            ax.set_xlabel("Actual implemented OLI channels / nominal nm")
        ax.axhline(0, color="#888888", lw=0.7)
        ax.set_ylabel("A - B / pooled within-block SD")
        prob = getattr(row, sensor + "_p_holm")
        ax.set_title(f"{a} - {bb} | {sensor}\nNIWO 2023 | NPC adj p={prob:.4g}")
    axes[i, 2].set_axis_off()
    axes[i, 2].text(
        0.5,
        0.5,
        "MicaSense\nNOT TESTED\n\nPhysical mapping\nunverified",
        ha="center",
        va="center",
        transform=axes[i, 2].transAxes,
        bbox=dict(facecolor="#edf0f2", edgecolor="#a8b3bb", pad=15),
    )
fig.text(
    0.1,
    -0.015,
    "Shading/vertical intervals: 95% pointwise GlobalID cluster-bootstrap intervals (not simultaneous). OLI bands are discrete and are not joined.\nThese are two prespecified strong exemplars at NIWO 2023; all cohorts and weaker contrasts are retained in the numerical tables.",
    fontsize=9,
)
fig.tight_layout()
save(fig, "C_strong_exemplar_contrasts")

# D: paired within-cohort rankings, no confounding through averaging support.
fig, axes = plt.subplots(2, 4, figsize=(16, 10), squeeze=False)
for i, scheme in enumerate(names):
    for j, cohort in enumerate(cohorts):
        ax = axes[i, j]
        g = r[(r.scheme == scheme) & (r.cohort == cohort)]
        nn = rankdata(-g.NEON_effect)
        oo = rankdata(-g.OLI_effect)
        for k, (row, left, right) in enumerate(zip(g.itertuples(), nn, oo)):
            label = (
                row.contrast
                if scheme == "inferred_pft"
                else short[row.a] + "/" + short[row.b]
            )
            color = plt.colormaps["tab10"](k % 10)
            ax.plot([0, 1], [left, right], marker="o", lw=1, color=color, ms=3)
            ax.text(-0.05, left, label, ha="right", va="center", fontsize=7)
            ax.text(1.05, right, label, ha="left", va="center", fontsize=7)
        ax.set(
            xlim=(-0.65, 1.6),
            ylim=(len(g) + 0.5, 0.5),
            xticks=[0, 1],
            xticklabels=["NEON", "OLI"],
            yticks=[],
            title=cohort,
        )
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        if j == 0:
            ax.set_ylabel(
                names[scheme] + "\nRank 1 = largest effect", fontsize=10, labelpad=8
            )
fig.text(
    0.1,
    0.005,
    "Ranks describe effect magnitude, not classifier performance. D=Deciduous; E=Evergreen; H=Herbaceous; N=Non-vegetated & dead; W=Woody shrub.\nWithin-cohort rankings avoid treating contrasts sharing plants as independent. Blank candidate contrasts are not ranked.",
    fontsize=9,
)
fig.tight_layout(rect=(0, 0.045, 1, 1))
save(fig, "D_contrast_rank_retention")

# E: useful extra summary of paired ratio uncertainty.
fig, axes = plt.subplots(1, 2, figsize=(13, 9))
for ax, scheme in zip(axes, names):
    g = r[r.scheme == scheme].sort_values("OLI_NEON_ratio").reset_index(drop=True)
    yy = np.arange(len(g))
    ax.hlines(yy, g.ratio_lo, g.ratio_hi, color="#8ca5b5", lw=1)
    ax.scatter(g.OLI_NEON_ratio, yy, color="#225d7a", s=15, zorder=3)
    labels = [
        (
            row.contrast
            if scheme == "inferred_pft"
            else short[row.a] + "/" + short[row.b]
        )
        + " "
        + row.cohort
        for row in g.itertuples()
    ]
    ax.set(
        yticks=yy,
        yticklabels=labels,
        xlabel="OLI / NEON RMS effect ratio",
        title=names[scheme],
    )
    ax.tick_params(axis="y", labelsize=6.5)
    ax.axvline(1, color="#666666", ls="--", lw=1)
fig.text(
    0.1,
    0.005,
    "Lines: paired 95% GlobalID bootstrap percentile intervals, conditional on observed sites and acquisition histories.\nD=Deciduous; E=Evergreen; H=Herbaceous; N=Non-vegetated & dead; W=Woody shrub. Ratios are not literal information fractions.",
    fontsize=8.5,
)
fig.tight_layout(rect=(0, 0.045, 1, 1))
save(fig, "E_effect_ratio_intervals")

# Copy compact evidence only; do not duplicate source or row-level spectra.
for name in [
    "sensor_support.csv",
    "sensor_contrasts.csv",
    "effect_retention.csv",
    "cross_sensor_correlations.csv",
    "band_retention.csv",
    "cross_site_consistency.csv",
    "pairing_audit.json",
    "cluster_bootstrap_audit.json",
]:
    shutil.copyfile(RUN / name, HERE / name)
# Published evidence explicitly distinguishes an available but inadmissible
# MicaSense export from an absent sensor observation.
published_correlations = c.assign(status="tested")
blocked = []
for (scheme, cohort), group in c.groupby(["scheme", "cohort"]):
    for sensor_pair in ["NEON_vs_MicaSense", "OLI_vs_MicaSense"]:
        for method in ["Pearson", "Spearman"]:
            blocked.append(
                dict(
                    scheme=scheme,
                    cohort=cohort,
                    sensors=sensor_pair,
                    method=method,
                    contrasts=0,
                    correlation=np.nan,
                    lo=np.nan,
                    hi=np.nan,
                    bootstrap_valid=0,
                    uncertainty="not_computed",
                    status="blocked_unverified_coordinates",
                )
            )
pd.concat([published_correlations, pd.DataFrame(blocked)], ignore_index=True).to_csv(
    HERE / "cross_sensor_correlations.csv", index=False
)
published_support = pd.read_csv(HERE / "sensor_support.csv")
source_support = pd.read_csv(HERE / "source_family_support.csv")
ms_source = source_support[source_support.stage == "micasense"].iloc[0]
assert ms_source.complete_pixels == ms_source.pixels
published_support["MicaSense_available_n"] = published_support.common_n
published_support["MicaSense_admitted_n"] = 0
published_support.to_csv(HERE / "sensor_support.csv", index=False)

lines = [
    "# Does the ecological pattern survive spectral reduction?",
    "",
    "## Direct answer",
    "",
    "**Synthetic Landsat OLI: largely yes for the sampled contrasts, with measurable effect compression and one lost borderline detection. MicaSense: currently untestable because physical band identities are unverified.** This is a paired synthetic spectral-reduction experiment, not independent satellite/drone validation or classification accuracy.",
    "",
    "## Identical units and corrected-NEON reproduction",
    "",
    "All 12,504 source polygon/acquisition observations are shared across corrected NEON, undarkened OLI and darkened OLI. Common support contains all 3,639 polygon IDs and 4,807 polygon/year spectra. No sensor-specific sample loss occurred. Inferred-PFT inference uses 1,944 assigned identities; researcher categories use all 3,639 identities, including 1,143 without species names. Inferred PFT codes are DBS = deciduous broadleaf shrub, DBT = deciduous broadleaf tree, EBS = evergreen broadleaf shrub, ECS = evergreen conifer shrub and ECT = evergreen conifer tree. Exact shared acquisition-history blocks and per-pair membership are identical. All 21 inferred-PFT and all 40 researcher-class corrected-NEON eligible contrasts reproduce legacy raw and adjusted max, integrated and NPC probabilities exactly.",
    "",
    "## Landsat OLI: primary inferred-PFT results",
    "",
]
a = summary[summary.scheme == "inferred_pft"].iloc[0]
rr = summary[summary.scheme == "researcher_category"].iloc[0]
lines += [
    f"- Detection retention: {a.retained}/{a.NEON_supported} NEON-supported contrasts ({a.retention_percent:.2f}%) remain supported. All {a.NEON_unsupported} NEON-unsupported comparisons remain unsupported. This percentage describes dependent contrasts; it has no binomial interpretation.",
    f"- Effect retention: median OLI/NEON standardized RMS ratio {a.median_effect_ratio:.3f} (paired conditional bootstrap 95% interval {a.median_ratio_lo:.3f}-{a.median_ratio_hi:.3f}); individual ratios {r[r.scheme == 'inferred_pft'].OLI_NEON_ratio.min():.3f}-{r[r.scheme == 'inferred_pft'].OLI_NEON_ratio.max():.3f}. Ratios compare an equal-channel metric with a wavelength-integrated metric, not a literal percent of all biological information.",
    "- Strong DBS/ECT and DBT/ECT differences persist in all four cohorts. DBS/ECT effect ratios range 0.728-0.787; DBT/ECT 0.744-0.872. The weak DBT/ECS contrasts remain unsupported in both NIWO years. No lower-resolution superiority is inferred from a smaller p-value.",
    "- NIWO 2023 DBS/DBT loses support: NEON adjusted NPC p=0.045, OLI p=0.855; the RMS effect falls from 0.353 to 0.234 (ratio 0.665, paired interval 0.619-0.938). The original NEON finding was already borderline/post-exploration and family-sensitive. With identical samples/history, membership loss is ruled out here; spectral averaging/coverage, changed variance, weighting and resulting statistical power remain inseparable contributors. This does not prove an intrinsically hyperspectral-only biological mechanism.",
    "",
    "## Pattern and direction retention",
    "",
]
for scheme in ["inferred_pft", "researcher_category"]:
    for row in c[(c.scheme == scheme) & (c.cohort == "all")].itertuples():
        lines.append(
            f"- {names[scheme]}, {row.method}: {row.correlation:.3f}, paired cluster-bootstrap 95% interval {row.lo:.3f}-{row.hi:.3f}. These are correlations across a fixed, dependent set of eligible contrast/cohort effects, not 21/40 independent experiments."
        )
lines += [
    "",
    "Every corresponding OLI-band point-estimate sign agrees with its NEON projection on that band support (147/147 inferred, 280/280 researcher). This is strong internal consistency for a shared-source Gaussian reduction, not an independent validation. Both pointwise intervals exclude zero in only 99/147 and 249/280 cases respectively; do not label the other directions resolved. Projection occurs after polygon/year medians while stored OLI reduction occurs before medians, so exact equality is not assumed. Response support fractions are in band_retention.csv.",
    "",
    "## Cross-site retention",
    "",
    "For the strong inferred contrasts in 2023, OLI standardized signed-vector cross-site cosines are 0.871-0.944 for DBS/ECT and 0.755-0.902 for DBT/ECT. Their matched NEON projections onto the same seven response supports are almost identical (0.872-0.944 and 0.757-0.902). Native-NEON full-domain standardized cosines span 0.859-0.955 and 0.781-0.936. Thus broad cross-site pattern similarity survives, while not every individual band has the same sign across sites. These standardized cosines differ from earlier raw-beta curve cosines and should not be equated with them. All pair/site comparisons, including weak and reversing directions, are retained in cross_site_consistency.csv.",
    "",
    "## Separate researcher-category analysis",
    "",
    f"All {rr.retained}/{rr.NEON_supported} corrected-NEON-supported researcher-class contrasts remain supported in OLI ({rr.retention_percent:.0f}%, descriptive). Median effect ratio {rr.median_effect_ratio:.3f} (conditional paired interval {rr.median_ratio_lo:.3f}-{rr.median_ratio_hi:.3f}). Deciduous/Evergreen effect ratios are 0.742-0.819 and Evergreen/Woody shrub ratios 0.771-0.865 across cohorts, showing that retained detection can coexist with compressed biological contrasts. The five broad researcher categories are retained as a separate label system, not pooled with inferred taxa. Non-vegetated & dead is a mixed cover comparator, not a living PFT. Broad differentiation does not imply nonoverlapping individuals.",
    "",
    "## Likely spectral reasons and ablation limits",
    "",
    "OLI retains two SWIR channels near 1609 and 2201 nm. All five quoted historical intervals are confirmed: every gridpoint is outside the current matched-family maximum envelope in all four cohorts (DBS/ECT: 1500-1785 and 2260-2285 nm; DBT/ECT: 955-1030, 1140-1335 and 1550-1785 nm). The verification and response coverage are recorded in neon_region_coverage.csv. Gaussian-response coverage is diagnostic, not proof that a response interval is the causal feature. OLI has no channel centered in the 955-1030 or 1140-1335 nm regions, and its SWIR2 tail samples some of the cited 2260-2285 nm interval. It therefore preserves broad SWIR-related contrasts while averaging or omitting finer features.",
    "Descriptive OLI-without-SWIR RMS effects are supplied for every contrast on the same polygons. Removing both SWIR bands reduces the descriptive equal-channel RMS effect to 0.394-0.616 of full OLI for DBS/ECT and 0.454-0.925 for DBT/ECT. DBT/ECT is largely retained in visible/NIR at YELL (0.925). This is not a proof that SWIR alone causes distinguishability: removing channels changes the equal-channel norm as well as support. No ablation significance family or classifier result was run.",
    "",
    "## MicaSense: no ecological inference",
    "",
    "The source contains ten complete values per pixel but its labels (475,560,668,717,840,841,842,843,844,845 nm) match a five-band fallback plus 1-nm padding, not the intended ten-band metadata (444,475,531,560,650,668,705,717,740,842 nm). No original headers or generation provenance establish the physical mapping. We stop this branch, do not guess relabeling, and mark all MicaSense cells blocked. Its intended VNIR-only configuration motivates a future SWIR-coverage hypothesis but does not establish an empirical MicaSense result.",
    "",
    "## Weighting, brightness and uncertainty sensitivity",
    "",
    "Equal OLI channel weights are primary; normalized FWHM weights are a distinct sensitivity. No supported/not-supported decisions change under that sensitivity in either label system. The actual darkened/undarkened OLI ratios match positive bandwise brightness gains. Their standardized effects differ by at most "
    + f"{r.dark_invariance_error.max():.2g}"
    + ", consistent with scale invariance; brightness adjustment is not responsible for the reported transfer pattern.",
    "The 499 GlobalID bootstrap draws couple sensors, overlapping contrasts and repeated NIWO years, stratifying by fixed site, label and complete joint-year history pattern. There are 342 strata (120 singleton) among 1,944 inferred IDs and 594 strata (169 singleton) among 3,639 researcher IDs. Singleton strata cannot contribute bootstrap variability. Intervals are conditional descriptive percentile intervals, not population-site uncertainty, simultaneous confidence bands or proof of exchangeability. Species/spatial confounding and earlier exploration remain.",
    "",
    "## What is sensor-robust, what is not established?",
    "",
    "- Sensor-robust here: strong DBS/ECT and DBT/ECT group differentiation, weak DBT/ECS non-support, broad researcher-category differentiation, and much of the effect ranking and corresponding band direction.",
    "- Spectral-resolution sensitive here: mean standardized separation is compressed for many inferred contrasts, with a lost borderline NIWO DBS/DBT detection and altered fine-feature coverage. This does not establish that hyperspectral information is universally necessary for that contrast.",
    "- Cannot currently test: MicaSense biological retention, independent real-sensor transfer, novel-region/species recognition, a causal PFT effect, or classification accuracy. Acquisition/spatial scale/noise differences of actual OLI or drone imagery are absent from this synthetic experiment.",
    "",
    "## Figures and tables",
    "",
    "A_effect_heatmap_*: identical-sample effects and NPC support, labels separated. B_effect_retention: paired NEON/OLI effects. C_strong_exemplar_contrasts: signed NEON curves and discrete OLI points with pointwise bootstrap intervals. D_contrast_rank_retention: within-cohort ordering. E_effect_ratio_intervals: paired uncertainty. All figures have PDF/PNG/SVG versions. Tables include all candidate comparisons, insufficient support, actual eligible members, bootstrap intervals, width sensitivity and MicaSense gate. See DESIGN.md, METHODS.md, SENSOR_AUDIT.md and VALIDATION.md for contracts and verification.",
]
(HERE / "RESULTS.md").write_text("\n".join(lines) + "\n")
# Hash the entire compact evidence/figure set; path roots are explicit.
evidence = {
    str(p.relative_to(HERE)): digest(p)
    for p in HERE.rglob("*")
    if p.is_file() and p.name != "statistics_manifest.json"
}
(HERE / "statistics_manifest.json").write_text(
    json.dumps(
        dict(
            analysis_root=str(RUN.relative_to(ROOT)),
            analysis_manifest_sha256=digest(RUN / "statistics_manifest.json"),
            sensor_definition_inputs={
                name: digest(ROOT / name)
                for name in [
                    "src/spectralbridge/data/landsat_band_parameters.json",
                    "src/spectralbridge/data/brightness/landsat_to_micasense.json",
                    "src/spectralbridge/sensor_pairs.py",
                    "src/spectralbridge/pipelines/pipeline.py",
                    "src/spectralbridge/standard_resample.py",
                    "src/spectralbridge/exports/schema_utils.py",
                    "src/spectralbridge/polygon_extraction.py",
                    "src/spectralbridge/parquet_export.py",
                ]
            },
            analysis_identity=manifest["identity"],
            analysis_outputs=manifest["outputs"],
            evidence_outputs=evidence,
            MicaSense_status="blocked_unverified_coordinates",
        ),
        indent=2,
    )
    + "\n"
)
print(summary.to_string(index=False))
