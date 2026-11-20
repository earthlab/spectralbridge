"""Frozen paired polygon-level PFT comparison of translated null and10% arms.

No pixel-as-replicate inference. Same polygon identities/folds, physical B1-B5,
site-blocked NPC, fixed C=1 balanced logistic. Primary: OLI2/common pixels/site
holdout; other prespecified analyses are sensitivities. Artifacts stay immutable.
"""

import json
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from drone_shade_mask_preview import ROOT, file_sha256
from spectralbridge.envi import hdr_to_dict, memmap_bsq
from spectralbridge.pft_method_audit import AuditConfig, method_statistics
from spectralbridge.plant_pft_statistics import holm

BASE = ROOT / "archive/local/drone-calibration-translation/2026-11-19"
REPORT = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/pft-mask-comparison"
)
PRIOR = REPORT.parent
LABEL = "cover_category"
CATEGORIES = [
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "Non-vegetated & dead",
]
BANDS = [f"B{i}" for i in range(1, 6)]
SEED = 20261119
PERMUTATIONS = 9999
POLICY = dict(
    primary="Landsat_9_OLI-2/shared_pixels/held_out_site",
    arms=["null", "mask10"],
    samples=["shared_pixels", "retained_pixels"],
    targets=["Landsat_9_OLI-2", "Landsat_8_OLI"],
    unit="one five-band physical-reflectance median per labelled polygon",
    normalization="none; same physical-units protocol as prior calibration-library tests",
    minimum_pixels=1,
    paired_cohort="identical polygon IDs with complete five-band spectra in both arms",
    shared_pixels="same exact all-five-bands-finite pixel intersection before each polygon median",
    retained_pixels="each arm all-five-bands-finite pixels; common polygon IDs only",
    separability="existing site-blocked whole-polygon label NPC,9999 draws,Holm across10 per arm and across full80 contrast family",
    change_in_separation="paired whole-polygon arm-swap standardized RMS site-adjusted effect;9999 draws; Holm across40 pair contrasts",
    identifiability="training-only StandardScaler + balanced logistic C=1,5 stratified polygon folds and3 leave-site-out folds,unchanged splits between arms",
    change_in_identifiability="paired correctness swaps with equal true-class weights,9999 draws; Holm across8 target/population/scheme contrasts",
    direction="mask10 minus null; negative indicates lower information in mask10",
    limitations="Observational exploratory sensitivity, not randomized masking; same-site polygons may remain correlated; only3calibration sites; refit+coverage effects; conditional unverified radiometry; Ruby null failed BRDF QA; no external physical validation",
    seed=SEED,
    permutations=PERMUTATIONS,
)


POLICY["site_level_sensitivity"] = (
    "Exact paired arm swaps by site (up to8assignments), reported with Holm; polygon swaps are conditional exploratory sensitivity, not independent site evidence"
)


def polygon_medians(null, masked, labels):
    """Reduce only complete five-band pixels; use exact common pixels for primary."""
    if null.shape != masked.shape or null.shape != (len(labels), 5):
        raise ValueError("Aligned five-band pixels required")
    vn = np.isfinite(null).all(axis=1)
    vm = np.isfinite(masked).all(axis=1)
    common = vn & vm
    spectra = []
    coverage = []
    for gid, group in labels.groupby("GlobalID", sort=True):
        ix = group.index.to_numpy()
        category = group[LABEL].unique()
        if len(category) != 1:
            raise ValueError("Conflicting polygon labels")
        coverage.append(
            dict(
                GlobalID=gid,
                cover_category=category[0],
                source_pixels=len(ix),
                null_pixels=int(vn[ix].sum()),
                mask10_pixels=int(vm[ix].sum()),
                common_pixels=int(common[ix].sum()),
            )
        )
        if not vn[ix].any() or not vm[ix].any():
            continue
        for population in ["shared_pixels", "retained_pixels"]:
            if population == "shared_pixels" and not common[ix].any():
                continue
            for arm, values, valid in [("null", null, vn), ("mask10", masked, vm)]:
                select = common if population == "shared_pixels" else valid
                selected = ix[select[ix]]
                med = np.median(values[selected], axis=0)
                spectra.append(
                    dict(
                        GlobalID=gid,
                        cover_category=category[0],
                        population=population,
                        arm=arm,
                        n_pixels=len(selected),
                        **dict(zip(BANDS, med, strict=True)),
                    )
                )
    return pd.DataFrame(spectra), pd.DataFrame(coverage)


def extract():
    spectra = []
    coverage = []
    identity = {}
    configurations = json.loads(
        (ROOT / "provenance/drone-camera-rerun/2026-11-05/site_inputs.json").read_text()
    )
    manifests = {
        arm: json.loads((PRIOR / folder / "verification.json").read_text())
        for arm, folder in [
            ("null", "unmasked-null-products"),
            ("mask10", "translated-products"),
        ]
    }
    for arm, manifest in manifests.items():
        for item in manifest["products"]:
            for path, digest in item["sha256"].items():
                if file_sha256(Path(path)) != digest:
                    raise ValueError("Changed translated source")
                identity[path] = digest
    for config in configurations:
        site = config["site"].lower()
        index_path = Path(config["polygon_index"])
        labels = pd.read_parquet(
            index_path, columns=["GlobalID", LABEL, "row", "col", "x", "y"]
        ).reset_index(drop=True)
        if labels.duplicated(["GlobalID", "row", "col"]).any():
            raise ValueError("Duplicate polygon pixel")
        if not labels[LABEL].isin(CATEGORIES).all():
            raise ValueError("Unexpected category")
        identity[str(index_path)] = file_sha256(index_path)
        for target in POLICY["targets"]:
            values = {}
            for arm, manifest in manifests.items():
                item = next(
                    p
                    for p in manifest["products"]
                    if p["site"] == site and p["target"] == target
                )
                img = Path(item["output_img"])
                hdr = hdr_to_dict(img.with_suffix(".hdr"))
                with rasterio.open(img) as raster:
                    x, y = raster.transform * (
                        labels.col.to_numpy() + 0.5,
                        labels.row.to_numpy() + 0.5,
                    )
                    np.testing.assert_allclose(x, labels.x, rtol=0, atol=1e-7)
                    np.testing.assert_allclose(y, labels.y, rtol=0, atol=1e-7)
                cube = memmap_bsq(img, hdr)
                values[arm] = np.asarray(
                    cube[:, labels.row.to_numpy(), labels.col.to_numpy()], float
                ).T * float(hdr["physical reflectance multiplier"]) + float(
                    hdr["physical reflectance offset"]
                )
            med, cov = polygon_medians(values["null"], values["mask10"], labels)
            spectra.append(med.assign(site=site, target=target))
            coverage.append(cov.assign(site=site, target=target))
            print(site, target, "polygon extraction complete", flush=True)
    frame = pd.concat(spectra, ignore_index=True)
    cov = pd.concat(coverage, ignore_index=True)
    meta = frame[["GlobalID", LABEL, "site"]].drop_duplicates()
    if meta.GlobalID.duplicated().any():
        raise ValueError("Cross-site polygon identity requires purged folds")
    return frame, cov, identity


def aligned(frame):
    a = frame[frame.arm == "null"].sort_values("GlobalID").reset_index(drop=True)
    b = frame[frame.arm == "mask10"].sort_values("GlobalID").reset_index(drop=True)
    if not a.GlobalID.equals(b.GlobalID):
        raise ValueError("Paired cohort IDs differ")
    return a, b


def standard_effect(values, labels, sites):
    """Site-adjusted RMS standardized beta; accepts permutation batch ×N×bands."""
    values = np.asarray(values, float)
    if values.ndim == 2:
        values = values[None, ...]
    z = np.asarray(labels, float)
    sites = np.asarray(sites)
    x = z.copy()
    centered = values.copy()
    unique = np.unique(sites)
    for site in unique:
        ix = sites == site
        x[ix] -= z[ix].mean()
        centered[:, ix] -= values[:, ix].mean(axis=1, keepdims=True)
    xx = x @ x
    if xx <= 0:
        raise ValueError("No within-site class support")
    scale = np.sqrt((centered**2).sum(axis=1) / (len(z) - len(unique)))
    beta = np.einsum("n,pnb->pb", x, centered) / xx
    standardized = np.divide(beta, scale, out=np.zeros_like(beta), where=scale > 0)
    return np.sqrt(np.mean(standardized**2, axis=1))


def effect_change(a, b, labels, sites, seed, permutations=PERMUTATIONS):
    ea = standard_effect(a, labels, sites)[0]
    eb = standard_effect(b, labels, sites)[0]
    observed = eb - ea
    rng = np.random.default_rng(seed)
    draws = []
    mid = (a + b) / 2
    half = (b - a) / 2
    for start in range(0, permutations, 128):
        signs = rng.choice([-1, 1], size=(min(128, permutations - start), len(a), 1))
        left = mid - half * signs
        right = mid + half * signs
        draws.extend(
            standard_effect(right, labels, sites) - standard_effect(left, labels, sites)
        )
    draws = np.asarray(draws)
    site_draws = []
    unique = np.unique(sites)
    for signs in product([-1, 1], repeat=len(unique)):
        sign = np.array([signs[np.flatnonzero(unique == site)[0]] for site in sites])[
            :, None
        ]
        site_draws.append(
            float(
                standard_effect(mid + half * sign, labels, sites)[0]
                - standard_effect(mid - half * sign, labels, sites)[0]
            )
        )
    site_draws = np.asarray(site_draws)
    return dict(
        p_loss_site_exact=float(np.mean(site_draws <= observed + 1e-12)),
        p_two_sided_site_exact=float(
            np.mean(np.abs(site_draws) >= abs(observed) - 1e-12)
        ),
        effect_null=ea,
        effect_mask10=eb,
        effect_delta=observed,
        p_loss=(1 + int((draws <= observed + 1e-12).sum())) / (permutations + 1),
        p_two_sided=(1 + int((np.abs(draws) >= abs(observed) - 1e-12).sum()))
        / (permutations + 1),
    )


def paired_accuracy(predictions, seed, permutations=PERMUTATIONS):
    a = predictions[predictions.arm == "null"].sort_values("GlobalID")
    b = predictions[predictions.arm == "mask10"].sort_values("GlobalID")
    if not a.GlobalID.reset_index(drop=True).equals(b.GlobalID.reset_index(drop=True)):
        raise ValueError("Unpaired predictions")
    truth = a.truth.to_numpy()
    ca = a.prediction.to_numpy() == truth
    cb = b.prediction.to_numpy() == truth
    classes, counts = np.unique(truth, return_counts=True)
    weights = np.array(
        [1 / (len(classes) * counts[np.flatnonzero(classes == y)[0]]) for y in truth]
    )
    differences = (cb.astype(float) - ca.astype(float)) * weights
    observed = differences.sum()
    rng = np.random.default_rng(seed)
    draws = []
    for start in range(0, permutations, 256):
        signs = rng.choice([-1, 1], size=(min(256, permutations - start), len(a)))
        draws.extend(signs @ differences)
    draws = np.asarray(draws)
    sites = a.site.to_numpy() if "site" in a else np.repeat("fixture", len(a))
    contributions = np.array(
        [differences[sites == site].sum() for site in np.unique(sites)]
    )
    site_draws = (
        np.array(list(product([-1, 1], repeat=len(contributions)))) @ contributions
    )
    return dict(
        p_loss_site_exact=float(np.mean(site_draws <= observed + 1e-12)),
        p_two_sided_site_exact=float(
            np.mean(np.abs(site_draws) >= abs(observed) - 1e-12)
        ),
        sites=len(contributions),
        ba_null=float(ca @ weights),
        ba_mask10=float(cb @ weights),
        delta_ba=float(observed),
        n=len(a),
        p_loss=(1 + int((draws <= observed + 1e-12).sum())) / (permutations + 1),
        p_two_sided=(1 + int((abs(draws) >= abs(observed) - 1e-12).sum()))
        / (permutations + 1),
    )


def classify(frame):
    a, b = aligned(frame)
    y = a[LABEL].to_numpy()
    folds = min(5, int(a[LABEL].value_counts().min()))
    if folds < 2:
        raise ValueError("Insufficient class support for polygon holdout")
    schemes = {
        "unseen_polygon": list(
            StratifiedKFold(folds, shuffle=True, random_state=SEED).split(a[BANDS], y)
        ),
        "held_out_site": [
            (np.flatnonzero(a.site.ne(site)), np.flatnonzero(a.site.eq(site)))
            for site in sorted(a.site.unique())
        ],
    }
    records = []
    members = []
    for scheme, splits in schemes.items():
        for fold, (train, test) in enumerate(splits):
            assert not set(a.iloc[train].GlobalID) & set(a.iloc[test].GlobalID)
            for arm, data in [("null", a), ("mask10", b)]:
                model = make_pipeline(
                    StandardScaler(),
                    LogisticRegression(class_weight="balanced", C=1, max_iter=2000),
                )
                model.fit(data.iloc[train][BANDS].to_numpy(), y[train])
                pred = model.predict(data.iloc[test][BANDS].to_numpy())
                for row, prediction in zip(test, pred, strict=True):
                    records.append(
                        dict(
                            arm=arm,
                            scheme=scheme,
                            fold=fold,
                            GlobalID=a.iloc[row].GlobalID,
                            site=a.iloc[row].site,
                            truth=y[row],
                            prediction=prediction,
                            truth_in_training=bool(y[row] in y[train]),
                        )
                    )
            for role, ix in [("train", train), ("test", test)]:
                members.extend(
                    dict(
                        scheme=scheme,
                        fold=fold,
                        role=role,
                        GlobalID=a.iloc[row].GlobalID,
                        site=a.iloc[row].site,
                        cover_category=y[row],
                    )
                    for row in ix
                )
    return pd.DataFrame(records), pd.DataFrame(members)


def analyze(frame):
    pairs = []
    changes = []
    predictions = []
    memberships = []
    accuracy = []
    for target in POLICY["targets"]:
        for population in POLICY["samples"]:
            group = frame[(frame.target == target) & (frame.population == population)]
            a, b = aligned(group)
            print(target, population, "classification; polygons", len(a), flush=True)
            pred, members = classify(group)
            pred = pred.assign(target=target, population=population)
            predictions.append(pred)
            memberships.append(members.assign(target=target, population=population))
            for scheme in ["held_out_site", "unseen_polygon"]:
                accuracy.append(
                    dict(
                        target=target,
                        population=population,
                        scheme=scheme,
                        **paired_accuracy(pred[pred.scheme == scheme], SEED),
                    )
                )
            for pair_id, (first, second) in enumerate(combinations(CATEGORIES, 2)):
                pair = a[a[LABEL].isin([first, second])]
                mixed = pair.groupby("site")[LABEL].nunique()
                pair = pair[pair.site.isin(mixed.index[mixed == 2])]
                ix = pair.index.to_numpy()
                labels = pair[LABEL].eq(first).astype(int).to_numpy()
                sites = pair.site.to_numpy()
                info = dict(
                    target=target,
                    population=population,
                    first=first,
                    second=second,
                    n_first=int((labels == 1).sum()),
                    n_second=int((labels == 0).sum()),
                    sites=len(np.unique(sites)),
                )
                print(
                    target,
                    population,
                    first,
                    "vs",
                    second,
                    info["n_first"],
                    info["n_second"],
                    flush=True,
                )
                if min(info["n_first"], info["n_second"]) < 2:
                    for arm in ["null", "mask10"]:
                        pairs.append(
                            dict(
                                **info,
                                arm=arm,
                                status="insufficient_support",
                                p_npc=np.nan,
                            )
                        )
                    continue
                changes.append(
                    dict(
                        **info,
                        **effect_change(
                            a.iloc[ix][BANDS].to_numpy(),
                            b.iloc[ix][BANDS].to_numpy(),
                            labels,
                            sites,
                            SEED + pair_id,
                        ),
                    )
                )
                for arm, data in [("null", a), ("mask10", b)]:
                    result = method_statistics(
                        data.iloc[ix][BANDS],
                        labels,
                        sites,
                        [444, 475, 560, 668, 842],
                        config=AuditConfig(
                            permutations=PERMUTATIONS, seed=SEED + pair_id
                        ),
                        integration_weights=np.ones(5),
                    )
                    pairs.append(
                        dict(
                            **info,
                            arm=arm,
                            status="tested",
                            p_npc=result["p"]["npc"],
                            standardized_rms=float(
                                standard_effect(
                                    data.iloc[ix][BANDS].to_numpy(), labels, sites
                                )[0]
                            ),
                        )
                    )
                write_table(pd.DataFrame(pairs), REPORT / "separability_progress.csv")
    pairs = pd.DataFrame(pairs)
    changes = pd.DataFrame(changes)
    accuracy = pd.DataFrame(accuracy)
    pairs["p_holm_all80"] = holm(pairs.p_npc.fillna(1))
    pairs.loc[pairs.p_npc.isna(), "p_holm_all80"] = np.nan
    pairs["p_holm_within10"] = np.nan
    for _, ix in pairs.groupby(["target", "population", "arm"]).groups.items():
        pairs.loc[ix, "p_holm_within10"] = holm(pairs.loc[ix, "p_npc"].fillna(1))
    for table in [changes, accuracy]:
        table["p_loss_holm"] = holm(table.p_loss)
        table["p_two_sided_holm"] = holm(table.p_two_sided)
        table["p_loss_site_holm"] = holm(table.p_loss_site_exact)
        table["p_two_sided_site_holm"] = holm(table.p_two_sided_site_exact)
    return (
        pairs,
        changes,
        pd.concat(predictions, ignore_index=True),
        pd.concat(memberships, ignore_index=True),
        accuracy,
    )


def write_table(table, path):
    """Avoid CSV readers interpreting the literal arm label 'null' as missing."""
    table = table.copy()
    if "arm" in table:
        table["arm"] = table.arm.replace({"null": "unmasked"})
    table.to_csv(path, index=False)


def run():
    REPORT.mkdir(parents=True, exist_ok=True)
    policy_path = REPORT / "analysis_policy.json"
    if policy_path.exists() and json.loads(policy_path.read_text()) != POLICY:
        raise ValueError("Frozen analysis policy changed; use new directory")
    policy_path.write_text(json.dumps(POLICY, indent=2) + "\n")
    manifest_path = REPORT / "manifest.json"
    if manifest_path.exists():
        saved = json.loads(manifest_path.read_text())
        same_code = saved["identity"].get("analysis_code") == file_sha256(
            Path(__file__)
        )
        if (
            same_code
            and all(
                Path(path).is_file() and file_sha256(Path(path)) == digest
                for path, digest in saved["identity"].items()
                if path != "analysis_code"
            )
            and all(
                (REPORT / name).is_file() and file_sha256(REPORT / name) == digest
                for name, digest in saved["outputs"].items()
            )
        ):
            print("Reusing verified completed mask-PFT comparison", flush=True)
            return
    frame, coverage, identity = extract()
    write_table(frame, REPORT / "polygon_spectra.csv")
    write_table(coverage, REPORT / "polygon_coverage.csv")
    with threadpool_limits(limits=1):
        pairs, changes, predictions, memberships, accuracy = analyze(frame)
    for name, table in [
        ("separability", pairs),
        ("separability_change", changes),
        ("held_out_predictions", predictions),
        ("fold_memberships", memberships),
        ("identifiability_change", accuracy),
    ]:
        write_table(table, REPORT / f"{name}.csv")
    rows = []
    for (target, population, arm), group in predictions.groupby(
        ["target", "population", "arm"]
    ):
        for category in CATEGORIES:
            p = group[group.truth == category]
            tests = pairs[
                (pairs.target == target)
                & (pairs.population == population)
                & (pairs.arm == arm)
                & (pairs["first"].eq(category) | pairs["second"].eq(category))
            ]
            row = dict(
                target=target,
                population=population,
                arm=arm,
                category=category,
                n_polygons=p.GlobalID.nunique(),
                tested_pairs=int(tests.p_npc.notna().sum()),
                supported_within10=int((tests.p_holm_within10 <= 0.05).sum()),
                supported_all80=int((tests.p_holm_all80 <= 0.05).sum()),
            )
            for scheme in ["unseen_polygon", "held_out_site"]:
                q = p[p.scheme == scheme]
                row[scheme + "_recall"] = (
                    float((q.prediction == q.truth).mean())
                    if len(q) and q.truth_in_training.all()
                    else np.nan
                )
            rows.append(row)
    write_table(pd.DataFrame(rows), REPORT / "class_summary.csv")
    identity["analysis_code"] = file_sha256(Path(__file__))
    outputs = {p.name: file_sha256(p) for p in REPORT.glob("*.csv")}
    (REPORT / "manifest.json").write_text(
        json.dumps(
            dict(
                identity=identity,
                outputs=outputs,
                policy=POLICY,
                versions=dict(
                    numpy=np.__version__,
                    pandas=pd.__version__,
                    sklearn=__import__("sklearn").__version__,
                ),
            ),
            indent=2,
        )
        + "\n"
    )
    print(accuracy.to_string(index=False), flush=True)


if __name__ == "__main__":
    run()
