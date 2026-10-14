"""Paired, conditional PFT structure under synthetic spectral reduction.

MicaSense export identity remains gated. This is not independent sensor validation.
"""

from dataclasses import asdict
from itertools import combinations
from pathlib import Path
import json
import logging
import platform

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import scipy
from scipy.stats import rankdata

from .plant_spectral_atlas import _file_hash, run_plant_spectral_atlas
from .plant_spectral_years import _year_plant_spectra
from .plant_spectral_pfts import tag_pfts, load_pft_crosswalk, UNASSIGNED
from .plant_pft_statistics import _center, _history_keys, _seed, _write_json, holm
from .pft_method_audit import AuditConfig, method_statistics, npc_probability

LOG = logging.getLogger(__name__)
OLI_CENTERS = np.array([443, 482, 561.4, 654.6, 864.7, 1608.9, 2200.7])
OLI_WIDTHS = np.array([16, 60, 57.3, 37.5, 28.3, 84.7, 186.7])
OLI_NAMES = ["Coastal", "Blue", "Green", "Red", "NIR", "SWIR1", "SWIR2"]


def validate_sensor_coordinates(wavelengths, sensor):
    """No guessed ten-band relabeling; the supplied MicaSense cannot pass."""
    w = np.asarray(wavelengths, float)
    if (
        sensor == "OLI"
        and w.shape == (7,)
        and np.allclose(w, OLI_CENTERS, atol=0.51, rtol=0)
    ):
        return
    if sensor == "MicaSense":
        raise ValueError(
            "MicaSense biological inference requires verified original headers and response provenance; exported ordering alone is insufficient"
        )
    raise ValueError("Invalid OLI band coordinates")


def paired_observations(products):
    """Intersect valid observations before medians; reject identity/label drift."""
    keys = ["GlobalID", "flight_id", "source_image", "polygon_id"]
    common = None
    indexed = {}
    for stage, frame in products.items():
        if frame.duplicated(keys).any() or frame[keys].isna().any().any():
            raise ValueError("Duplicate or missing observation identity")
        cols = [c for c in frame if c.startswith(stage + "_wl")]
        good = np.isfinite(frame[cols].to_numpy(float))
        valid = good.sum(1) >= 2 if stage == "corr" else good.all(1)
        indexed[stage] = frame.loc[valid].set_index(keys)
        ids = set(indexed[stage].index)
        common = ids if common is None else common & ids
    if not common:
        raise ValueError("No common valid source observations")
    order = pd.MultiIndex.from_tuples(sorted(common), names=keys)
    out = {stage: frame.loc[order].reset_index() for stage, frame in indexed.items()}
    reference = next(iter(out.values()))
    for frame in out.values():
        for field in ["cover_category", "source_parquet", "aop_site", "pixel_count"]:
            if (
                field in reference
                and field in frame
                and not reference[field].equals(frame[field])
            ):
                raise ValueError("Paired observation metadata differ: " + field)
    return out


def joint_cluster_multiplicities(table, replicates, seed):
    """GlobalID clusters coupled across sensors, contrasts and repeated years.

    Stratify by label/site and complete year/history pattern to preserve cell
    counts. Singleton strata remain fixed and are explicitly reported.
    """
    ids = sorted(table.GlobalID.unique())
    positions = {v: i for i, v in enumerate(ids)}
    strata = {}
    for identity, group in table.groupby("GlobalID", sort=True):
        if group.label.nunique() != 1 or group.site.nunique() != 1:
            raise ValueError("Cluster spans labels or sites")
        pattern = tuple(sorted(zip(group.year, group.flight_history)))
        key = (group.label.iloc[0], group.site.iloc[0], pattern)
        strata.setdefault(key, []).append(positions[identity])
    rng = np.random.default_rng(seed)
    counts = np.zeros((replicates, len(ids)), np.int32)
    for members in strata.values():
        draw = rng.choice(members, size=(replicates, len(members)), replace=True)
        for i in range(replicates):
            counts[i] += np.bincount(draw[i], minlength=len(ids)).astype(np.int32)
    columns = np.array([positions[v] for v in table.GlobalID])
    return counts[:, columns], dict(
        clusters=len(ids),
        strata=len(strata),
        singleton_strata=sum(len(v) == 1 for v in strata.values()),
    )


def bootstrap_contrasts(values, labels, blocks, multiplicities, integration_weights):
    """Stable centered sufficient moments for a fixed-count cluster bootstrap."""
    y = np.asarray(values, float)
    z = np.asarray(labels, float)
    b = np.asarray(blocks)
    m = np.asarray(multiplicities, float)
    if not np.isfinite(y).all() or m.shape[1] != len(y):
        raise ValueError("Bootstrap requires finite common bands and aligned weights")
    x = _center(z[:, None], b).ravel()
    q = x @ x
    yc = _center(y, b)
    total = m @ (yc * yc)
    for block in np.unique(b):
        ix = np.flatnonzero(b == block)
        if not np.allclose(m[:, ix].sum(1), len(ix)) or not np.allclose(
            m[:, ix] @ z[ix], z[ix].sum()
        ):
            raise ValueError("Bootstrap changed class/block sample counts")
        total -= (m[:, ix] @ yc[ix]) ** 2 / len(ix)
    scale = np.sqrt(np.maximum(total, 0) / (len(y) - len(np.unique(b))))
    beta = m @ (x[:, None] * yc) / q
    delta = np.divide(beta, scale, out=np.full_like(beta, np.nan), where=scale > 0)
    weights = np.asarray(integration_weights, float)
    weights = weights / weights.sum()
    effect = np.sqrt((delta * delta) @ weights)
    return effect, delta


def project_neon_to_oli(values, wavelengths):
    """Diagnostic response average AFTER medians, never interpolate OLI points."""
    y = np.asarray(values, float)
    w = np.asarray(wavelengths, float)
    if np.any(np.diff(w) <= 0):
        raise ValueError("NEON grid must increase")
    valid = np.isfinite(y).all(0)
    w = w[valid]
    y = y[:, valid]
    # No bridge over missing support: local quadrature with a maximum 8-nm gap.
    lengths = np.zeros(len(w))
    for i, d in enumerate(np.diff(w)):
        if d <= 8:
            lengths[i : i + 2] += d / 2
    responses = np.exp(
        -0.5 * ((w[:, None] - OLI_CENTERS) / (OLI_WIDTHS / 2.354820045)) ** 2
    )
    mass = (responses * lengths[:, None]).sum(0)
    full = OLI_WIDTHS / 2.354820045 * np.sqrt(2 * np.pi)
    if np.any(mass <= 0):
        raise ValueError("No supported NEON response mass")
    return y @ (responses * lengths[:, None] / mass), mass / full


def _prepare(source, root):
    params = {"species_field": "cover_category", "make_figures": False}
    observations = {}
    for stage in ["corr", "olioli_undarkened", "olioli"]:
        options = dict(params, spectral_stage=stage)
        if stage != "corr":
            options["grid_step_nm"] = None
        out = root / "compact" / stage
        run_plant_spectral_atlas(source, out, **options)
        observations[stage] = pd.read_parquet(out / "plant_flight_spectra.parquet")
    before = {k: len(v) for k, v in observations.items()}
    observations = paired_observations(observations)
    meta = (
        pq.read_table(source, columns=["GlobalID", "species"])
        .to_pandas()
        .drop_duplicates()
    )
    if meta.groupby("GlobalID").species.nunique().gt(1).any():
        raise ValueError("Conflicting species labels")
    taxonomy = meta.groupby("GlobalID", dropna=False).species.first()
    tables = {}
    columns = {}
    for stage, frame in observations.items():
        frame = frame.rename(columns={"cover_category": "species"})
        table, cols, original = _year_plant_spectra(frame, stage)
        table = table.rename(columns={"species": "cover_category"}).join(
            _history_keys(original), on=["GlobalID", "year"]
        )
        table["species"] = table.GlobalID.map(taxonomy)
        tables[stage] = table.set_index(["site", "year", "GlobalID"]).sort_index()
        columns[stage] = cols
    before_year = {k: len(v) for k, v in tables.items()}
    common = set.intersection(*(set(t.index) for t in tables.values()))
    index = pd.MultiIndex.from_tuples(
        sorted(common), names=["site", "year", "GlobalID"]
    )
    tables = {k: t.loc[index].reset_index() for k, t in tables.items()}
    reference = tables["corr"]
    fields = [
        "site",
        "year",
        "GlobalID",
        "cover_category",
        "species",
        "flight_history",
        "flight_observations",
    ]
    for table in tables.values():
        if not table[fields].equals(reference[fields]):
            raise ValueError("Polygon/year membership or acquisition history differs")
    validate_sensor_coordinates(
        [float(c.split("_wl")[1][:-2]) for c in columns["olioli_undarkened"]], "OLI"
    )
    for k, t in tables.items():
        t.to_parquet(root / "compact" / (k + "_polygon_year.parquet"), index=False)
    _write_json(
        root / "pairing_audit.json",
        dict(
            observations_before=before,
            observations_common=len(observations["corr"]),
            polygon_year_common=len(reference),
            unique_polygons=reference.GlobalID.nunique(),
            unmatched_polygon_year_by_sensor={
                k: v - len(common) for k, v in before_year.items()
            },
        ),
    )
    return tables, columns


def run_sensor_pft_transfer(source, output, *, config=None, bootstraps=499, minimum=10):
    """Primary inferred-PFT and separate researcher-category paired OLI experiment."""
    config = config or AuditConfig()
    config.validate()
    if bootstraps < 19 or minimum < 2:
        raise ValueError(
            "Need at least 19 bootstrap replicates and two units per group"
        )
    root = Path(output)
    source = Path(source)
    root.mkdir(parents=True, exist_ok=True)
    identity = {
        "source": _file_hash(source),
        "config": asdict(config),
        "bootstraps": bootstraps,
        "minimum": minimum,
        "code": _file_hash(__file__),
        "core": _file_hash(Path(__file__).with_name("pft_method_audit.py")),
        "year": _file_hash(Path(__file__).with_name("plant_spectral_years.py")),
        "atlas": _file_hash(Path(__file__).with_name("plant_spectral_atlas.py")),
        "helpers": _file_hash(Path(__file__).with_name("plant_pft_statistics.py")),
        "crosswalk": _file_hash(Path(__file__).parent / "data/plant_pft_crosswalk.csv"),
        "runtime": dict(
            python=platform.python_version(),
            numpy=np.__version__,
            scipy=scipy.__version__,
            pandas=pd.__version__,
        ),
    }
    manifest_path = root / "statistics_manifest.json"
    if manifest_path.exists():
        saved = json.loads(manifest_path.read_text())
        if saved["identity"] == identity and all(
            (root / n).is_file() and _file_hash(root / n) == h
            for n, h in saved["outputs"].items()
        ):
            LOG.info("Reusing verified completed paired sensor analysis")
            return pd.read_csv(root / "effect_retention.csv")
    tables, columns = _prepare(source, root)
    all_support = []
    summaries = []
    bands = []
    records = {}
    cluster_audits = {}
    memberships = []
    cache = root / "checkpoints"
    cache.mkdir(exist_ok=True)
    for scheme in ["inferred_pft", "researcher_category"]:
        base = tables["corr"].copy()
        if scheme == "inferred_pft":
            base = tag_pfts(base, load_pft_crosswalk())
            use = base.pft.ne(UNASSIGNED).to_numpy()
            base = base.loc[use].copy()
            base["label"] = base.pft_code
        else:
            use = np.ones(len(base), bool)
            base["label"] = base.cover_category
        base = base.reset_index(drop=True)
        sensor_values = {
            k: t.loc[use, columns[k]].to_numpy(float) for k, t in tables.items()
        }
        boot, cluster_audits[scheme] = joint_cluster_multiplicities(
            base, bootstraps, config.seed
        )
        for (site, year, label), g in base.groupby(["site", "year", "label"]):
            all_support.append(
                dict(
                    scheme=scheme,
                    site=site,
                    year=year,
                    label=label,
                    common_n=len(g),
                    common_observations=int(g.flight_observations.sum()),
                    NEON_n=len(g),
                    OLI_n=len(g),
                    MicaSense_n=np.nan,
                    MicaSense_status="blocked_unverified_coordinates",
                )
            )
        label_pairs = list(combinations(sorted(base.label.unique()), 2))
        for (site, year), cohort in base.groupby(["site", "year"], sort=True):
            for pair_index, (a, b) in enumerate(label_pairs):
                pair = cohort[cohort.label.isin([a, b])]
                blocks = pd.factorize(pair.flight_history)[0]
                z = pair.label.eq(a).to_numpy(float)
                mixed = [
                    v for v in np.unique(blocks) if len(np.unique(z[blocks == v])) == 2
                ]
                keep = np.isin(blocks, mixed)
                pair = pair.loc[keep]
                z = z[keep]
                blocks = blocks[keep]
                ix = pair.index.to_numpy()
                n_a, n_b = int(z.sum()), int((1 - z).sum())
                legacy_id = (
                    f"corr-{site}-{year}-{a}-{b}-flight_history"
                    if scheme == "inferred_pft"
                    else f"{site}_{year}_{pair_index}_flight_history"
                )
                key = scheme + "__" + legacy_id
                meta = dict(
                    test_id=key,
                    legacy_id=legacy_id,
                    scheme=scheme,
                    site=site,
                    year=year,
                    cohort=f"{site}-{year}",
                    a=a,
                    b=b,
                    contrast=a + " / " + b,
                    n_a=n_a,
                    n_b=n_b,
                    common_n=n_a + n_b,
                    blocks=len(mixed),
                    status="tested"
                    if min(n_a, n_b) >= minimum
                    else "insufficient_common_support",
                )
                if meta["status"] != "tested":
                    for sensor in ["NEON", "OLI", "OLI_width"]:
                        summaries.append(dict(meta, sensor=sensor))
                    continue
                LOG.info("%s | matched %s/%s | bootstrap %s", key, n_a, n_b, bootstraps)
                membership = pair[
                    [
                        "GlobalID",
                        "site",
                        "year",
                        "species",
                        "cover_category",
                        "label",
                        "flight_history",
                    ]
                ].copy()
                membership["test_id"] = key
                memberships.append(membership)
                path = cache / (key + ".npz")
                ledger = path.with_suffix(".json")
                saved = json.loads(ledger.read_text()) if ledger.exists() else {}
                if saved.get("identity") == identity:
                    if not path.is_file() or _file_hash(path) != saved["sha256"]:
                        raise ValueError("Sensor-transfer checkpoint checksum mismatch")
                    with np.load(path) as f:
                        rec = {k: f[k] for k in f.files}
                    probabilities = saved["probabilities"]
                else:
                    rec = {}
                    probabilities = {}
                    for sensor, stage in [
                        ("NEON", "corr"),
                        ("OLI", "olioli_undarkened"),
                    ]:
                        y = sensor_values[stage][ix]
                        w = np.array(
                            [float(c.split("_wl")[1][:-2]) for c in columns[stage]]
                        )
                        explicit = None if sensor == "NEON" else np.ones(7)
                        result = method_statistics(
                            y,
                            z,
                            blocks,
                            w,
                            config=config,
                            seed=_seed(config, legacy_id),
                            integration_weights=explicit,
                        )
                        assert np.array_equal(result["rows"], np.arange(len(ix)))
                        selected = result["columns"]
                        weights = result["weights"]
                        effect, delta_boot = bootstrap_contrasts(
                            y[:, selected], z, blocks, boot[:, ix], weights
                        )
                        delta = result["curves"][0] / result["scale"]
                        rec[sensor + "_effect_boot"] = effect
                        rec[sensor + "_delta_boot"] = delta_boot
                        rec[sensor + "_delta"] = delta
                        rec[sensor + "_beta"] = result["curves"][0]
                        rec[sensor + "_weights"] = weights
                        rec[sensor + "_w"] = w[selected]
                        rec[sensor + "_stats"] = result["stats"][0, :2]
                        rec[sensor + "_effect"] = np.sqrt(np.sum(weights * delta**2))
                        probabilities[sensor] = {
                            k: result["p"][k] for k in ["max", "integrated", "npc"]
                        }
                        # NPC combination score is the minimum partial probability;
                        # the calibrated NPC p is stored separately.
                        ensemble = result["stats"][:, :2]
                        from .pft_method_audit import upper_p

                        rec[sensor + "_npc_statistic"] = float(
                            np.minimum(
                                upper_p(ensemble[:, 0])[0], upper_p(ensemble[:, 1])[0]
                            )
                        )
                        if sensor == "OLI":
                            width = OLI_WIDTHS / OLI_WIDTHS.sum()
                            integral = (result["curves"] / result["se"]) ** 2 @ width
                            probabilities["OLI_width"] = {
                                "max": result["p"]["max"],
                                "integrated": float(
                                    (
                                        1
                                        + np.count_nonzero(
                                            integral[1:]
                                            >= integral[0]
                                            - 1e-12 * max(1, abs(integral[0]))
                                        )
                                    )
                                    / len(integral)
                                ),
                                "npc": npc_probability(
                                    np.column_stack([result["stats"][:, 0], integral])
                                ),
                            }
                            rec["OLI_width_stats"] = np.array(
                                [result["stats"][0, 0], integral[0]]
                            )
                            rec["OLI_width_effect"] = np.sqrt(np.sum(width * delta**2))
                            rec["OLI_width_effect_boot"] = np.sqrt(
                                (delta_boot**2) @ width
                            )
                            rec["OLI_width_npc_statistic"] = float(
                                min(
                                    upper_p(result["stats"][:, 0])[0],
                                    upper_p(integral)[0],
                                )
                            )
                    projection, mass = project_neon_to_oli(
                        sensor_values["corr"][ix],
                        np.array(
                            [float(c.split("_wl")[1][:-2]) for c in columns["corr"]]
                        ),
                    )
                    x = _center(z[:, None], blocks).ravel()
                    yc = _center(projection, blocks)
                    scale = np.sqrt(np.sum(yc**2, axis=0) / (len(ix) - len(mixed)))
                    rec["projected_delta"] = (x @ yc / (x @ x)) / scale
                    _, rec["projected_delta_boot"] = bootstrap_contrasts(
                        projection, z, blocks, boot[:, ix], np.ones(7)
                    )
                    rec["projection_mass"] = mass
                    dark = sensor_values["olioli"][ix]
                    x = _center(z[:, None], blocks).ravel()
                    yc = _center(dark, blocks)
                    darkdelta = (x @ yc / (x @ x)) / np.sqrt(
                        np.sum(yc**2, axis=0) / (len(ix) - len(mixed))
                    )
                    rec["dark_invariance_error"] = np.max(
                        np.abs(darkdelta - rec["OLI_delta"])
                    )
                    temp = path.with_suffix(".tmp.npz")
                    np.savez_compressed(temp, **rec)
                    temp.replace(path)
                    _write_json(
                        ledger,
                        dict(
                            identity=identity,
                            sha256=_file_hash(path),
                            probabilities=probabilities,
                        ),
                    )
                records[key] = rec
                for sensor in ["NEON", "OLI", "OLI_width"]:
                    effect = float(rec[sensor + "_effect"])
                    ci = np.nanquantile(rec[sensor + "_effect_boot"], [0.025, 0.975])
                    summaries.append(
                        dict(
                            meta,
                            sensor=sensor,
                            effect=effect,
                            effect_lo=ci[0],
                            effect_hi=ci[1],
                            maximum_statistic=float(rec[sensor + "_stats"][0]),
                            integrated_statistic=float(rec[sensor + "_stats"][1]),
                            npc_statistic=float(rec[sensor + "_npc_statistic"]),
                            **{"p_" + k: v for k, v in probabilities[sensor].items()},
                        )
                    )
                for j, name in enumerate(OLI_NAMES):
                    olo, ohi = np.nanquantile(
                        rec["OLI_delta_boot"][:, j], [0.025, 0.975]
                    )
                    nlo, nhi = np.nanquantile(
                        rec["projected_delta_boot"][:, j], [0.025, 0.975]
                    )
                    bands.append(
                        dict(
                            meta,
                            band=name,
                            center_nm=OLI_CENTERS[j],
                            OLI_delta=rec["OLI_delta"][j],
                            OLI_beta=rec["OLI_beta"][j],
                            OLI_lo=olo,
                            OLI_hi=ohi,
                            NEON_projected_delta=rec["projected_delta"][j],
                            NEON_projected_lo=nlo,
                            NEON_projected_hi=nhi,
                            response_mass_fraction=rec["projection_mass"][j],
                            direction_preserved=bool(
                                np.sign(rec["OLI_delta"][j])
                                == np.sign(rec["projected_delta"][j])
                            ),
                            both_sign_resolved=bool(olo * ohi > 0 and nlo * nhi > 0),
                        )
                    )
    if not memberships:
        raise ValueError("No eligible common-support comparisons")
    summary = pd.DataFrame(summaries)
    for scheme in summary.scheme.unique():
        for sensor in ["NEON", "OLI", "OLI_width"]:
            use = (
                summary.scheme.eq(scheme)
                & summary.sensor.eq(sensor)
                & summary.status.eq("tested")
            )
            for method in ["npc", "max", "integrated"]:
                summary.loc[use, "p_" + method + "_holm"] = holm(
                    summary.loc[use, "p_" + method]
                )
    summary.to_csv(root / "sensor_contrasts.csv", index=False)
    pd.DataFrame(all_support).to_csv(root / "sensor_support.csv", index=False)
    pd.DataFrame(bands).to_csv(root / "band_retention.csv", index=False)
    pd.concat(memberships, ignore_index=True).to_parquet(
        root / "membership.parquet", index=False
    )
    _write_json(root / "cluster_bootstrap_audit.json", cluster_audits)
    retention = []
    for row in summary[
        (summary.sensor == "NEON") & (summary.status == "tested")
    ].itertuples():
        other = summary[
            (summary.test_id == row.test_id) & summary.sensor.eq("OLI")
        ].iloc[0]
        width = summary[
            (summary.test_id == row.test_id) & summary.sensor.eq("OLI_width")
        ].iloc[0]
        rec = records[row.test_id]
        ratios = rec["OLI_effect_boot"] / rec["NEON_effect_boot"]
        stable = row.effect > 0.1
        bb = pd.DataFrame(bands)
        bb = bb[bb.test_id == row.test_id]
        ratio_ci = (
            np.nanquantile(ratios, [0.025, 0.975]) if stable else [np.nan, np.nan]
        )
        retention.append(
            dict(
                test_id=row.test_id,
                scheme=row.scheme,
                cohort=row.cohort,
                site=row.site,
                year=row.year,
                contrast=row.contrast,
                a=row.a,
                b=row.b,
                n_a=row.n_a,
                n_b=row.n_b,
                common_n=row.common_n,
                NEON_effect=row.effect,
                OLI_effect=other.effect,
                MicaSense_effect=np.nan,
                OLI_NEON_ratio=other.effect / row.effect if stable else np.nan,
                ratio_lo=ratio_ci[0],
                ratio_hi=ratio_ci[1],
                ratio_status="stable_denominator" if stable else "near_zero_NEON",
                NEON_supported=row.p_npc_holm < 0.05,
                OLI_supported=other.p_npc_holm < 0.05,
                NEON_p_holm=row.p_npc_holm,
                OLI_p_holm=other.p_npc_holm,
                OLI_width_effect=width.effect,
                OLI_width_supported=width.p_npc_holm < 0.05,
                band_directions_preserved=int(bb.direction_preserved.sum()),
                bands=7,
                resolved_bands=int(bb.both_sign_resolved.sum()),
                resolved_agreements=int(
                    (bb.both_sign_resolved & bb.direction_preserved).sum()
                ),
                OLI_without_SWIR_effect=float(
                    np.sqrt(np.mean(rec["OLI_delta"][:5] ** 2))
                ),
                dark_invariance_error=float(rec["dark_invariance_error"]),
                MicaSense_status="blocked_unverified_coordinates",
            )
        )
    retention = pd.DataFrame(retention)
    retention.to_csv(root / "effect_retention.csv", index=False)
    _correlations(retention, records, root)
    _cross_site(retention, records, root)
    # Manifest only owns analysis outputs, not future interpretation files.
    owned = [
        root / n
        for n in [
            "sensor_contrasts.csv",
            "sensor_support.csv",
            "band_retention.csv",
            "effect_retention.csv",
            "cross_sensor_correlations.csv",
            "cross_site_consistency.csv",
            "membership.parquet",
            "pairing_audit.json",
            "cluster_bootstrap_audit.json",
        ]
    ]
    owned += list(cache.glob("*")) + list((root / "compact").rglob("*"))
    if _file_hash(source) != identity["source"]:
        raise ValueError("Source changed during transfer analysis")
    _write_json(
        manifest_path,
        dict(
            identity=identity,
            outputs={
                str(p.relative_to(root)): _file_hash(p) for p in owned if p.is_file()
            },
            MicaSense_status="blocked_unverified_coordinates",
        ),
    )
    return retention


def _correlations(retention, records, root):
    rows = []
    for scheme, g in retention.groupby("scheme"):
        for cohort, sub in [("all", g), *list(g.groupby("cohort"))]:
            if len(sub) < 3:
                continue
            x = sub.NEON_effect.to_numpy()
            y = sub.OLI_effect.to_numpy()
            bx = np.column_stack([records[k]["NEON_effect_boot"] for k in sub.test_id])
            by = np.column_stack([records[k]["OLI_effect_boot"] for k in sub.test_id])
            for name, xx, yy, bxx, byy in [
                ("Pearson", x, y, bx, by),
                (
                    "Spearman",
                    rankdata(x),
                    rankdata(y),
                    rankdata(bx, axis=1),
                    rankdata(by, axis=1),
                ),
            ]:
                point = float(np.corrcoef(xx, yy)[0, 1])
                bxx = bxx - bxx.mean(1, keepdims=True)
                byy = byy - byy.mean(1, keepdims=True)
                corr = np.sum(bxx * byy, axis=1) / np.sqrt(
                    np.sum(bxx * bxx, axis=1) * np.sum(byy * byy, axis=1)
                )
                ci = np.nanquantile(corr, [0.025, 0.975])
                rows.append(
                    dict(
                        scheme=scheme,
                        cohort=cohort,
                        sensors="NEON_vs_OLI",
                        method=name,
                        contrasts=len(sub),
                        correlation=point,
                        lo=ci[0],
                        hi=ci[1],
                        bootstrap_valid=int(np.isfinite(corr).sum()),
                        uncertainty="paired_GlobalID_bootstrap_fixed_sites_histories",
                    )
                )
    pd.DataFrame(rows).to_csv(root / "cross_sensor_correlations.csv", index=False)


def _cos(a, b):
    return float(np.dot(a, b) / np.sqrt(np.dot(a, a) * np.dot(b, b)))


def _cross_site(retention, records, root):
    rows = []
    for (scheme, a, b), g in retention[retention.year == 2023].groupby(
        ["scheme", "a", "b"]
    ):
        for aa, bb in combinations(list(g.itertuples()), 2):
            ra, rb = records[aa.test_id], records[bb.test_id]
            for sensor, key in [
                ("NEON_OLI_support", "projected_delta"),
                ("OLI", "OLI_delta"),
            ]:
                rows.append(
                    dict(
                        scheme=scheme,
                        a=a,
                        b=b,
                        site_a=aa.site,
                        site_b=bb.site,
                        year=2023,
                        sensor=sensor,
                        cosine=_cos(ra[key], rb[key]),
                        sign_agreement=float(
                            np.mean(np.sign(ra[key]) == np.sign(rb[key]))
                        ),
                    )
                )
            # Native NEON curve comparison on shared supported wavelengths only.
            wa, ia, ib = np.intersect1d(ra["NEON_w"], rb["NEON_w"], return_indices=True)
            rows.append(
                dict(
                    scheme=scheme,
                    a=a,
                    b=b,
                    site_a=aa.site,
                    site_b=bb.site,
                    year=2023,
                    sensor="NEON",
                    cosine=_cos(ra["NEON_delta"][ia], rb["NEON_delta"][ib]),
                    sign_agreement=float(
                        np.mean(
                            np.sign(ra["NEON_delta"][ia])
                            == np.sign(rb["NEON_delta"][ib])
                        )
                    ),
                    bands=len(wa),
                )
            )
    pd.DataFrame(rows).to_csv(root / "cross_site_consistency.csv", index=False)
