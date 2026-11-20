"""Create readable BRDF benchmark tables/figures from completed compact outputs.

Never opens source rasters or refits models. All charts distinguish bundled AOP
processing from isolated conditional BRDF contrasts. No significance from pixels.
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "provenance/brdf-benefit-audit/2026-11-19"
OUT = BASE / "summary"
LABELS = {
    "hls": "Landsat HLS\nreconstructed control",
    "aop_archive": "AOP archive\nBRDF + topography",
    "drone_10pct": "Drone 10% mask\nincremental BRDF",
    "drone_unmasked": "Drone unmasked\nfailed Ruby QA",
}
COLORS = {
    "hls": "#246b8e",
    "aop_archive": "#168b7b",
    "drone_10pct": "#bf623f",
    "drone_unmasked": "#8b6760",
}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(fig, name):
    fig.savefig(OUT / (name + ".png"), dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / (name + ".svg"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#243745",
            "text.color": "#172e3c",
            "axes.titleweight": "bold",
        }
    )
    scores = pd.read_csv(BASE / "statistics/identifiability.csv")
    s = scores[(scores.bands == 5) & (scores.status == "SUPPORTED")].copy()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    positions = []
    names = []
    y = 0
    for sensor in LABELS:
        for scheme in ["unseen_identity", "held_site"]:
            rows = s[(s.sensor == sensor) & (s.scheme == scheme)]
            label = (
                LABELS[sensor].replace("\n", " / ")
                + " — "
                + ("unseen identity" if scheme == "unseen_identity" else "held site")
            )
            if len(rows):
                row = rows.iloc[0]
                x = row.delta_ba * 100
                ax.errorbar(
                    x,
                    y,
                    xerr=[[x - row.ci_low * 100], [row.ci_high * 100 - x]],
                    fmt="o",
                    color=COLORS[sensor],
                    capsize=3,
                    ms=7,
                )
            else:
                ax.text(
                    0.2,
                    y,
                    "unsupported: class–region confounding",
                    va="center",
                    fontsize=9,
                    color="#657482",
                )
            positions.append(y)
            names.append(label)
            y += 1
    ax.axvline(0, color="#263b48", lw=0.8)
    ax.axvspan(-2, 2, color="#e8edf0", zorder=-1)
    ax.set_yticks(positions, names)
    ax.invert_yaxis()
    ax.set_xlabel("Correction minus control balanced accuracy (percentage points)")
    ax.set_title(
        "No consistent recognition gain in these matched cohorts", loc="left", pad=14
    )
    ax.grid(axis="x", alpha=0.18)
    fig.tight_layout()
    save(fig, "recognition_effects")
    # Full5band rates, both methods and conditional95percent bootstrap delta interval.
    s.to_csv(OUT / "five_band_recognition.csv", index=False)
    r = pd.read_csv(BASE / "statistics/class_recalls.csv")
    r = r[(r.sensor == "drone_10pct") & (r.scheme == "held_site") & (r.bands == 5)]
    wide = r.pivot(index="class", columns="arm", values="recall").reindex(
        ["Deciduous", "Evergreen", "Herbaceous", "Woody shrub", "Non-vegetated & dead"]
    )
    fig, ax = plt.subplots(figsize=(9, 3.5))
    y = np.arange(len(wide))
    ax.barh(
        y - 0.16,
        wide.no_brdf * 100,
        height=0.3,
        color="#607d8b",
        label="Topographic only",
    )
    ax.barh(
        y + 0.16,
        wide.brdf * 100,
        height=0.3,
        color=COLORS["drone_10pct"],
        label="Topographic + BRDF",
    )
    ax.set_yticks(y, wide.index)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Held-site recall (%)")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.set_title("Drone loss is concentrated in non-vegetated & dead", loc="left")
    fig.tight_layout()
    save(fig, "drone_class_recalls")
    wide.to_csv(OUT / "drone_held_site_class_recalls.csv")
    # Repeat views: independently reduce each identity across observed days, equal IDs.
    repeat = pd.read_csv(BASE / "aop/repeat_view_consistency.csv")
    summary = []
    repeatunits = []
    rng = np.random.default_rng(20261119)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5), sharey=True)
    for col, n in enumerate([5, 7]):
        g = repeat.groupby(["identity", "site", "category"], as_index=False)[
            [f"rms_no_brdf_{n}", f"rms_brdf_{n}"]
        ].median()
        a = g[f"rms_no_brdf_{n}"].to_numpy()
        b = g[f"rms_brdf_{n}"].to_numpy()
        g["delta_rms"] = b - a
        g["bands"] = n
        g["percent_change"] = np.divide(
            100 * (b - a), a, out=np.full(len(a), np.nan), where=a > 1e-12
        )
        repeatunits.append(g)
        for site, h in [("ALL", g), *list(g.groupby("site"))]:
            d = h.delta_rms.to_numpy()
            bs = []
            for _ in range(1999):
                bs.append(float(np.median(d[rng.integers(len(d), size=len(d))])))
            summary.append(
                dict(
                    bands=n,
                    site=site,
                    identities=len(h),
                    median_rms_no_brdf=float(h[f"rms_no_brdf_{n}"].median()),
                    median_rms_brdf=float(h[f"rms_brdf_{n}"].median()),
                    median_delta_rms=float(np.median(d)),
                    ci_low=float(np.quantile(bs, 0.025)),
                    ci_high=float(np.quantile(bs, 0.975)),
                    median_percent_change=float(h.percent_change.median()),
                    percent_ratio_supported=int(h.percent_change.notna().sum()),
                    fraction_improved=float(np.mean(d < 0)),
                )
            )
        for site, h in g.groupby("site"):
            x = np.sort(h.percent_change.dropna())
            axes[col].plot(x, np.arange(1, len(x) + 1) / len(x), label=site, lw=1.8)
        axes[col].set_xlim(-60, 100)
        axes[col].axvline(0, color="#273d49", lw=0.7)
        axes[col].set_title(f"{n} bands")
        axes[col].set_xlabel("Repeat-view RMS change (%)")
        axes[col].grid(alpha=0.15)
    axes[0].set_ylabel("Fraction of polygon identities")
    axes[1].legend(frameon=False)
    fig.suptitle(
        "AOP archived correction: repeat-view gains vary by target and site",
        x=0.06,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    save(fig, "repeat_view_consistency")
    pd.DataFrame(summary).to_csv(OUT / "repeat_view_summary.csv", index=False)
    pd.concat(repeatunits, ignore_index=True).to_csv(
        OUT / "repeat_view_identity_effects.csv", index=False
    )
    # Separability: show effects, not a spurious count as mechanism.
    change = pd.read_csv(BASE / "statistics/separation_changes.csv")
    change = change[change.bands == 5]
    pairs = sorted(set(zip(change.category_a, change.category_b)))
    matrix = np.full((len(pairs), 4), np.nan)
    for j, sensor in enumerate(LABELS):
        for i, (c0, c1) in enumerate(pairs):
            row = change[
                (change.sensor == sensor)
                & (change.category_a == c0)
                & (change.category_b == c1)
            ]
            if len(row):
                matrix[i, j] = row.iloc[0].delta_effect
    fig, ax = plt.subplots(figsize=(9, 5))
    cmap = plt.get_cmap("BrBG").copy()
    cmap.set_bad("#d8dfe4")
    im = ax.imshow(matrix, cmap=cmap, vmin=-0.36, vmax=0.36, aspect="auto")
    ax.set_xticks(range(4), [LABELS[k] for k in LABELS], fontsize=9)
    ax.set_yticks(range(len(pairs)), [a + " / " + b for a, b in pairs], fontsize=9)
    for i in range(len(pairs)):
        for j in range(4):
            ax.text(
                j,
                i,
                "NA" if np.isnan(matrix[i, j]) else f"{matrix[i, j]:+.2f}",
                ha="center",
                va="center",
                fontsize=9,
                color="#172e3c",
            )
    fig.colorbar(
        im,
        ax=ax,
        label="Change in site-adjusted standardized RMS separation",
        shrink=0.8,
    )
    ax.set_title("Separation changes have mixed directions", loc="left")
    fig.tight_layout()
    save(fig, "separation_effects")
    # BRDF-only control, independent spatial fit support, association is not truth.
    control = pd.read_csv(BASE / "aop-control/heldout_band_diagnostics.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    w = control.wavelength_nm
    axes[0].plot(
        w, 100 * control.angular_r2_no_brdf, "o-", color="#607d8b", label="No BRDF"
    )
    axes[0].plot(w, 100 * control.angular_r2_brdf, "o-", color="#168b7b", label="BRDF")
    axes[0].set_ylabel("Within-block angular R² (%)")
    axes[0].set_ylim(bottom=0)
    axes[0].legend(frameon=False)
    axes[1].plot(w, control.median_abs_reflectance_change, "o-", color="#168b7b")
    axes[1].set_ylabel("Median absolute reflectance change")
    for ax in axes:
        ax.set_xlabel("Native AOP wavelength (nm)")
        ax.grid(alpha=0.15)
    fig.suptitle(
        "AOP BRDF-only holdout: no angular-association reduction here",
        x=0.05,
        ha="left",
        fontweight="bold",
    )
    fig.tight_layout()
    save(fig, "aop_brdf_only_control")
    # QA support and coverage are evidence, not effectiveness.
    q = []
    fits = (
        ROOT
        / "provenance/drone-calibration-translation/2026-11-19/shade-excluded-refit-v2"
    )
    for site in ["gordon", "goldhill", "ruby"]:
        for variant in ["baseline", "conservative"]:
            for stage in ["combined", "brdf_only"]:
                p = next((fits / site / variant / stage).glob("*brdf_model.json"))
                model = json.loads(p.read_text())
                q.append(
                    dict(
                        site=site,
                        variant=variant,
                        stage=stage,
                        status=model["validation"]["status"],
                        valid_bands=sum(
                            r["status"] == "VALID" for r in model["validation"]["fits"]
                        ),
                        model_sha256=sha(p),
                    )
                )
    pd.DataFrame(q).to_csv(OUT / "drone_qa_support.csv", index=False)
    # Per-flight magnitude audit also identifies archived near-identity stages.
    f = pd.read_csv(BASE / "aop/plant_flight_spectra.csv")
    keys = ["identity", "site", "category", "flight_id", "date", "year"]
    bands = [f"B{i}" for i in range(1, 8)]
    a = f[f.arm == "no_brdf"].set_index(keys)[bands]
    b = f[f.arm == "brdf"].set_index(keys)[bands]
    delta = (b - a).abs()
    flight = delta.groupby(level=["site", "flight_id"]).median().reset_index()
    flight.to_csv(OUT / "aop_flight_median_abs_changes.csv", index=False)
    summaryrecord = dict(
        note="All primary statistical families in statistics/*.csv. Repeat-view median bootstrap intervals condition on identities/fitted archives, not new independent sites. ECDF display clipped -60..100percent only; tables retain extremes.",
        five_band_identity_delta_pp={
            str(r.sensor): float(100 * r.delta_ba)
            for r in s[s.scheme == "unseen_identity"].itertuples()
        },
        aop_near_identity_plant_flights=int((delta.max(axis=1) <= 1e-12).sum()),
        aop_total_plant_flights=len(delta),
        control_all_angular_r2_increased=bool(
            (control.angular_r2_brdf > control.angular_r2_no_brdf).all()
        ),
        all_source_hashes={
            str(p.relative_to(BASE)): sha(p)
            for folder in ["statistics", "aop-control", "aop", "hls", "drone"]
            for p in (BASE / folder).glob("*.csv")
        },
        code_sha256=sha(Path(__file__)),
    )
    (OUT / "summary.json").write_text(json.dumps(summaryrecord, indent=2) + "\n")
    print("BRDF summary figures complete", flush=True)


if __name__ == "__main__":
    run()
