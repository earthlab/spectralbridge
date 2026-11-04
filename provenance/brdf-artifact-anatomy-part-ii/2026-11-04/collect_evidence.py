"""Recompute matched report statistics; create a claim-level provenance ledger."""

import importlib.util
import json
from functools import lru_cache
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/brdf-artifact-part-ii-20261104")
WORK.mkdir(exist_ok=True)
P165 = ROOT / "provenance/brdf-artifact-anatomy/2026-11-03"
P172 = ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"
P173 = ROOT / "provenance/goldhill-viewing-geometry/2026-11-04"
P175 = ROOT / "provenance/drone-integrated-reliability/2026-11-04"
spec = importlib.util.spec_from_file_location(
    "p172_for_publication", P172 / "common.py"
)
old = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = old
spec.loader.exec_module(old)
sha, safe, dist = old.sha, old.safe, old.dist
WAVES = old.WAVES
SCALE = old.SCALE
ledger = []


@lru_cache(None)
def source_digest(path):
    return sha(path)


def read(path):
    return json.loads(Path(path).read_text())


def write(name, value):
    (HERE / name).write_text(json.dumps(safe(value), indent=2, allow_nan=False) + "\n")


def claim(key, value, units, source, calculation, population, status, notes=""):
    ledger.append(
        dict(
            claim_id=key,
            value=value,
            units=units,
            source_file=str(Path(source).relative_to(ROOT))
            if str(source).startswith(str(ROOT))
            else str(source),
            source_sha256=source_digest(str(source)),
            calculation=calculation,
            population=population,
            verification_status=status,
            notes=notes,
        )
    )


def main():
    raw = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
        mmap_mode="r",
    )
    stored = np.load(
        "/private/tmp/goldhill-radiometric-recovery-20261102/normalized_raw.npy",
        mmap_mode="r",
    )
    historical = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/B_historical_stored.npy",
        mmap_mode="r",
    )
    arrays = {"raw": (raw, 1.0), "historical": (historical, SCALE)}
    for label, name in [
        ("nearest", "A_brdf"),
        ("central", "B_brdf"),
        ("uniform", "C_uniform_brdf"),
        ("weighted", "C_center_brdf"),
    ]:
        arrays[label] = (
            np.load(
                "/private/tmp/goldhill-viewing-geometry-20261104/" + name + ".npy",
                mmap_mode="r",
            ),
            1.0,
        )
    input_files = [Path(a.filename) for a, _ in arrays.values()] + [
        Path(stored.filename),
        old.SOURCE,
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg",
    ]
    for folder in [
        P165,
        P172,
        P173,
        ROOT / "provenance/drone-scale-confirmation/2026-10-30",
        ROOT / "provenance/goldhill-original-source/2026-11-03",
        ROOT / "provenance/brdf-mathematical-validation/2026-11-03",
    ]:
        input_files.extend(
            p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        )
    write(
        "input_manifest.json",
        dict(
            revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            protected_hashes={str(p): sha(p) for p in input_files},
            scope="Report generation and fresh statistics only; historical kernels/products are not recomputed or refitted",
        ),
    )
    with rasterio.open(old.SOURCE) as src:
        alpha = src.dataset_mask() > 0
        profile = dict(
            crs=str(src.crs),
            transform=list(src.transform),
            width=src.width,
            height=src.height,
            bounds=list(src.bounds),
        )
    geom = np.load(
        "/private/tmp/goldhill-viewing-geometry-20261104/geometry_native.npy",
        mmap_mode="r",
    )
    native = alpha & (geom[..., 6] > 0)
    masks = np.load(P172 / "filter_masks.npz")
    mapping = read(
        ROOT
        / "provenance/drone-scale-confirmation/2026-10-30/verified_numeric_mapping.json"
    )["goldhill"]["bands"]
    mins = np.array([b["original_min"] for b in mapping])
    maxs = np.array([b["original_max"] for b in mapping])
    inverse_scale = (maxs - mins) / 10000
    selection = read(P165 / "selection.json")
    y0, y1, x0, x1 = selection["roi_native_indices"]
    roi = np.s_[y0:y1, x0:x1]
    rr0 = selection["main_transect_row"]
    c0, c1 = selection["main_transect_columns"]
    caches = {}
    distributions = []
    residuals = []
    eligibility = []
    counts = []
    oldmask = masks["historical_native"]
    newmask = masks["D_revised_prefit"]
    redeligible = (
        oldmask
        & np.isfinite(stored[..., 4])
        & (stored[..., 4] >= 0)
        & (stored[..., 4] <= 2)
    )
    assert redeligible.sum() == 14
    for b, wave in enumerate(WAVES):
        S = stored[..., b]
        recovered = (mins[b] + S.astype(float) * inverse_scale[b]).astype("float32")
        choose = alpha & np.isfinite(S)
        caches["stored_sample_" + str(wave)] = S[choose][::31]
        caches["DN_sample_" + str(wave)] = recovered[choose][::31]
        e = (recovered[oldmask].astype(float) - mins[b]) / inverse_scale[b] - S[oldmask]
        residuals.append(
            dict(
                wavelength_nm=int(wave),
                test="10cm_inverse_forward_roundtrip",
                **dist(abs(e)),
            )
        )
        distributions.append(
            dict(
                wavelength_nm=int(wave),
                stored=dist(S[choose]),
                recovered_DN=dist(recovered[choose]),
            )
        )
        oldeligible = oldmask & np.isfinite(S) & (S >= 0) & (S <= 2)
        neweligible = (
            newmask & np.isfinite(raw[..., b]) & (raw[..., b] >= 0) & (raw[..., b] <= 2)
        )
        counts.append(
            dict(
                wavelength_nm=int(wave),
                historical=int(oldeligible.sum()),
                controlled_corrected=int(neweligible.sum()),
            )
        )
        eligibility.append(
            dict(
                wavelength_nm=int(wave),
                historical_red_selected_candidate=dist(recovered[redeligible] / 32768),
                corrected_population_candidate=dist(raw[..., b][newmask]),
            )
        )
        claim(
            "FILTER_OLD_" + str(wave),
            int(oldeligible.sum()),
            "pixels",
            Path(stored.filename),
            "finite historical footprint & 0<=stored S<=2 at this band",
            "historical finite H5 footprint",
            "RECOMPUTED_EXACT",
        )
        claim(
            "FILTER_CORRECTED_" + str(wave),
            int(neweligible.sum()),
            "pixels",
            P172 / "filter_masks.npz",
            "controlled clean prefit mask & finite candidate R in [0,2]",
            "controlled source/ancillary subset, fixed zero-view geometry",
            "RECOMPUTED_EXACT",
            "Not the same mask as native reconstructed geometry",
        )
        claim(
            "ROUNDTRIP_" + str(wave),
            float(np.max(abs(e))),
            "stored S units",
            Path(stored.filename),
            "S -> Float32 DN-equivalent -> Float64 S; max absolute error",
            "all historical finite source pixels",
            "RECOMPUTED_NUMERICAL",
        )
    # Fresh independent paired25cm test, not merely a forward/inverse identity.
    base = Path("/private/tmp/spectralbridge-scale-confirmation/base/goldhill.tif")
    scaled = Path("/private/tmp/spectralbridge-scale-confirmation/rescale/goldhill.tif")
    if base.exists() and scaled.exists():
        with rasterio.open(base) as a, rasterio.open(scaled) as b:
            assert a.shape == b.shape and a.transform == b.transform
            paired_raw, paired_scaled = a.read()[:10], b.read()[:10]
    else:
        import h5py

        base = Path("/private/tmp/p168-goldhill-sources/h5_original/source.h5")
        scaled = Path("/private/tmp/p168-goldhill-sources/h5_rescaled/source.h5")

        def source_array(path):
            with h5py.File(path) as handle:
                found = []
                handle.visititems(
                    lambda name, obj: (
                        found.append(name)
                        if isinstance(obj, h5py.Dataset)
                        and name.endswith("Reflectance_Data")
                        else None
                    )
                )
                assert len(found) == 1
                return np.moveaxis(handle[found[0]][...], -1, 0)

        paired_raw, paired_scaled = source_array(base), source_array(scaled)
    for i, wave in enumerate(WAVES):
        x = paired_raw[i].astype(float)
        y = paired_scaled[i].astype(float)
        valid = np.isfinite(x) & np.isfinite(y)
        e = y[valid] - (x[valid] - mins[i]) * 10000 / (maxs[i] - mins[i])
        residuals.append(
            dict(
                wavelength_nm=int(wave),
                test="25cm_independent_file_equation",
                **dist(abs(e)),
            )
        )
        claim(
            "INDEPENDENT_ENCODING_" + str(wave),
            float(np.max(abs(e))),
            "stored S units",
            scaled,
            "normalized source array minus independent unnormalized source array under verified equation",
            "paired finite25cm archived samples, identical grid",
            "RECOMPUTED_INDEPENDENT_FILE_COMPARISON",
        )
    write("encoding_distributions.json", distributions)
    write("encoding_residuals.json", residuals)
    write("eligibility_counts.json", counts)
    write("eligibility_spectra.json", eligibility)
    caches["eligible_historical"] = redeligible[::4, ::4]
    caches["eligible_corrected"] = newmask[::4, ::4]
    caches["historical_eligible_rows"], caches["historical_eligible_cols"] = np.nonzero(
        redeligible
    )
    assert [r["historical"] for r in counts] == [3, 1, 9, 13, 14, 30, 8, 4, 1, 0]
    geometry = read(P173 / "geometry_summary.json")
    svd = read(P173 / "design_support.json")
    for key, value, unit, pop in [
        ("SOURCE_ALPHA", int(alpha.sum()), "pixels", "clean alpha-valid source"),
        (
            "RECONSTRUCTED_NATIVE",
            int(native.sum()),
            "pixels",
            "source alpha & finite terrain & eligible footprint",
        ),
        (
            "CONTROLLED_FILTER",
            int(newmask.sum()),
            "pixels",
            "controlled prefit source/ancillary support",
        ),
    ]:
        claim(
            key,
            value,
            unit,
            P172 / "filter_masks.npz"
            if key != "RECONSTRUCTED_NATIVE"
            else P173 / "geometry_summary.json",
            "explicit boolean support count",
            pop,
            "RECOMPUTED_EXACT",
        )
    for key in ["camera_records", "positions"]:
        value = geometry.get(key) or (
            int(pd.read_csv(P173 / "acquisition_path.csv").band_records.sum())
            if key == "camera_records"
            else len(pd.read_csv(P173 / "acquisition_path.csv"))
        )
        claim(
            key.upper(),
            value,
            "records" if key == "camera_records" else "positions",
            P173 / "acquisition_path.csv",
            "unique acquisition path positions; ten pose records each",
            "recovered timestamped camera metadata",
            "PRIOR_VERIFIED_METADATA_AND_FRESH_COUNT",
        )
    for record in svd:
        claim(
            "CONDITION_" + record["scenario"],
            record["condition"],
            "dimensionless",
            P173 / "design_support.json",
            "largest / smallest design singular value",
            f"{record['n']}native design rows",
            "PRIOR_NATIVE_FIT_AND_SVD",
        )
        claim(
            "RANK_" + record["scenario"],
            record["stable_rank"],
            "rank",
            P173 / "design_support.json",
            "precision-aware independent singular directions",
            f"{record['n']}native design rows",
            "PRIOR_NATIVE_FIT_AND_SVD",
        )
    # Native matched metrics and factors; encoded historical values explicitly decoded.
    historicalphysical = historical[..., 4].astype(float) * SCALE
    state = historicalphysical > raw[..., 4] * 1.01
    h = (state[:, :-1] != state[:, 1:]) & native[:, :-1] & native[:, 1:]
    v = (state[:-1] != state[1:]) & native[:-1] & native[1:]
    metrics = []
    factor_records = []
    for label, (a, scale) in arrays.items():
        caches[label + "_rgb_full"] = np.where(
            native[::4, ::4, None], a[::4, ::4][:, :, [4, 3, 1]] * scale, np.nan
        )
        caches[label + "_rgb_roi"] = np.where(
            native[roi][..., None], a[roi][:, :, [4, 3, 1]] * scale, np.nan
        )
        for b, wave in enumerate(WAVES):
            values = a[..., b].astype(float) * scale
            valid = native & np.isfinite(values)
            source = raw[..., b]
            eligible = valid & (source > 0)
            factor = values[eligible] / source[eligible]
            factor_records.append(
                dict(
                    branch=label,
                    wavelength_nm=int(wave),
                    factor=dist(factor),
                    reflectance=dist(values[valid]),
                )
            )
            claim(
                "GAIN_RATIO_" + label + "_" + str(wave),
                float(factor.max()),
                "dimensionless",
                Path(a.filename),
                "decoded output / same source candidate reflectance; zero source excluded",
                "matched native reconstruction footprint",
                "RECOMPUTED_OUTPUT_RATIO",
                "Float32 output inversion can differ by ULPs from saved applied gain",
            )
            if b in [4, 7]:
                caches[label + "_factor_" + str(wave)] = np.divide(
                    values, source, out=np.full(source.shape, np.nan), where=source != 0
                )[::4, ::4]
                caches[label + "_factor_roi_" + str(wave)] = np.divide(
                    values[roi],
                    source[roi],
                    out=np.full(source[roi].shape, np.nan),
                    where=source[roi] != 0,
                )
                caches[label + "_transect_" + str(wave)] = values[rr0, c0:c1]
                caches[label + "_transect_factor_" + str(wave)] = np.divide(
                    values[rr0, c0:c1],
                    source[rr0, c0:c1],
                    out=np.full(c1 - c0, np.nan),
                    where=source[rr0, c0:c1] != 0,
                )
                jump = np.r_[
                    abs(np.diff(values, axis=1))[h], abs(np.diff(values, axis=0))[v]
                ]
                median = float(np.median(jump))
                metrics.append(
                    dict(
                        branch=label,
                        wavelength_nm=int(wave),
                        edges=len(jump),
                        median_boundary_jump=median,
                        fixed_pair_jump=float(abs(values[rr0, 981] - values[rr0, 980])),
                        native_maximum=float(values[valid].max()),
                    )
                )
                claim(
                    "BOUNDARY_" + label + "_" + str(wave),
                    median,
                    "candidate fractional reflectance",
                    Path(a.filename),
                    "median absolute adjacent-pixel jump across fixed historical sign edges",
                    f"{len(jump)}matched native edges",
                    "RECOMPUTED_MATCHED_NATIVE",
                )
    write("factor_and_band_distributions.json", factor_records)
    write("matched_boundary_metrics.json", metrics)
    # All-band raw/old/new spectra from unchanged memberships; medians, not means.
    cfg = read(ROOT / "provenance/goldhill-end-to-end/2026-11-03/branches.json")
    index = pd.read_parquet(cfg["polygon_index"])
    rr = index.row.to_numpy()
    cc = index.col.to_numpy()
    common = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/common_spectral_support.npy",
        mmap_mode="r",
    )
    keep = common[rr, cc]
    ids = set(
        pd.read_csv(
            ROOT
            / "provenance/goldhill-end-to-end/2026-11-03/independent_polygon_representatives.csv"
        ).GlobalID
    )
    assert keep.sum() == 144406
    rows = []
    exemplar = {}
    encoding_examples = []
    for label, (a, scale) in arrays.items():
        values = a[rr, cc].astype(float) * scale
        for identity, g in index.groupby("GlobalID", sort=True):
            z = g.index.to_numpy()
            z = z[keep[z]]
            if not len(z) or identity not in ids:
                continue
            vv = values[z]
            median = np.median(vv, axis=0)
            lo, hi = np.quantile(vv, [0.25, 0.75], axis=0)
            row = dict(
                branch=label,
                GlobalID=identity,
                PFT=g.cover_category.iloc[0],
                memberships=len(z),
            )
            row.update({f"median_{w}": median[i] for i, w in enumerate(WAVES)})
            row.update({f"q25_{w}": lo[i] for i, w in enumerate(WAVES)})
            row.update({f"q75_{w}": hi[i] for i, w in enumerate(WAVES)})
            rows.append(row)
            if identity == selection["exemplar_GlobalID"]:
                exemplar[label] = dict(
                    median=median,
                    q25=lo,
                    q75=hi,
                    n=len(z),
                    GlobalID=identity,
                    PFT=g.cover_category.iloc[0],
                )
                caches["exemplar_rows"] = rr[z]
                caches["exemplar_cols"] = cc[z]
    for identity in selection["selected_polygons"]:
        g = index[index.GlobalID == identity]
        z = g.index.to_numpy()
        z = z[keep[z]]
        if not len(z):
            continue
        S = stored[rr[z], cc[z]].astype(float)
        DN = mins + S * inverse_scale
        encoding_examples.append(
            dict(
                GlobalID=identity,
                PFT=g.cover_category.iloc[0],
                n=len(z),
                stored_fraction=np.median(S / 10000, axis=0),
                recovered_candidate=np.median(DN / 32768, axis=0),
                without_offset=np.median(S * inverse_scale / 32768, axis=0),
            )
        )
    pd.DataFrame(rows).to_csv(HERE / "polygon_median_spectra.csv", index=False)
    write("exemplar_median_spectra.json", exemplar)
    write("encoding_polygon_examples.json", encoding_examples)
    claim(
        "POLYGON_MEMBERSHIPS",
        int(keep.sum()),
        "memberships",
        Path(cfg["polygon_index"]),
        "source index intersected with frozen common support",
        "157analysis polygons; counts are memberships, not independent samples",
        "RECOMPUTED_EXACT",
    )
    claim(
        "POLYGON_UNITS",
        len(set(r["GlobalID"] for r in rows)),
        "polygon identities",
        HERE / "polygon_median_spectra.csv",
        "unique fixed researcher identities",
        "same157independent-index identities",
        "RECOMPUTED_EXACT",
    )
    # Saved classification evaluated on means remains separate from new descriptive medians.
    scores = read(P173 / "classification_summary.json")
    gains = read(P173 / "paired_gain.json")
    for r in scores:
        claim(
            "BA_" + r["branch"],
            r["balanced_accuracy"] * 100,
            "percent",
            P173 / "classification_summary.json",
            "balanced accuracy from fixed mean-spectrum OOF predictions",
            "157polygons, same3folds, C=1, train-only preprocessing",
            "PRIOR_PACKAGE_EVALUATION",
        )
    for r in gains:
        claim(
            "PAIRED_GAIN_" + r["branch"],
            r["difference"] * 100,
            "percentage points",
            P173 / "paired_gain.json",
            "class-stratified identity bootstrap of fixed OOF predictions",
            "157polygon identities",
            "PRIOR_PAIRED_BOOTSTRAP",
            f"95% interval [{r['low'] * 100},{r['high'] * 100}], does not include training/site-year uncertainty",
        )
    for row in read(P173 / "assignment_boundary_metrics.json"):
        if row["wavelength"] == 650 and row["edge_set"] == "assignment_change":
            claim(
                "SEAM99_" + row["scenario"],
                row["factor_jump"]["quantiles"][6],
                "dimensionless",
                P173 / "assignment_boundary_metrics.json",
                "99th percentile absolute horizontal factor change",
                "scenario-specific assignment/candidate-count boundary edges",
                "PRIOR_NATIVE_DIAGNOSTIC",
            )
    claim(
        "HISTORICAL_APPLIED_GAIN650",
        11742750.0,
        "dimensionless",
        P165 / "band_diagnostics.json",
        "saved actual applied gain; distinct from quotient reconstructed from Float32 output",
        "historical650nm positive prediction branch",
        "PRIOR_EXACT_FROZEN_REPLAY",
    )
    claim(
        "EXACT_REPLAY_VALUES",
        70832700,
        "array values",
        P165 / "replay_validation.json",
        "exact preserved historical stage equality",
        "2238x3165x10",
        "PRIOR_EXACT_FLOAT32_AND_MASK_COMPARISON",
    )
    claim(
        "NIR_MINIMUM_OFFSET",
        174,
        "source-DN equivalent",
        ROOT
        / "provenance/drone-scale-confirmation/2026-10-30/verified_numeric_mapping.json",
        "verified862nm normalization minimum",
        "original numerical mapping",
        "PRIOR_INDEPENDENT_ENCODING_COMPARISON",
    )
    claim(
        "CONDITIONAL_DN_DIVISOR",
        32768,
        "DN per candidate unit",
        ROOT / "provenance/goldhill-micasense-calibration/2026-11-03/verification.json",
        "conditional MicaSense hypothesis; not a certified Goldhill calibration",
        "all new candidate reflectance comparisons",
        "SUPPORTED_BUT_UNVERIFIED",
    )
    # Scope/literature/verification evidence is linked rather than rerunning any old correction.
    write(
        "report_contract.json",
        dict(
            profile=profile,
            selection=selection,
            wavelengths_nm=WAVES,
            diagnostic_RGB_nm=[650, 560, 475],
            RGB_display=dict(
                black=0, white=0.25, gamma=0.5, same_limits_all_branches=True
            ),
            full_scene_stride=4,
            native_metric_pixels=int(native.sum()),
            source_alpha_pixels=int(alpha.sum()),
            controlled_filter_pixels=int(newmask.sum()),
            common_polygon_memberships=int(keep.sum()),
            polygon_units=157,
            calibration="HYPOTHETICAL_UNVERIFIED",
            geometry="INFERRED_NOT_VERIFIED_CONTRIBUTORS",
            classification_aggregation="mean; new median spectra are descriptive only",
            historical_branch="Frozen historical model/kernel replay on the common clean source; existing B array read only, no kernel recomputation/refit",
            units="candidate fractional reflectance via common clean multiplier; no encoded/physical comparison without explicit conversion",
        ),
    )
    np.savez_compressed(WORK / "report_arrays.npz", **caches)
    pd.DataFrame(ledger).to_csv(HERE / "numerical_evidence.csv", index=False)
    write(
        "numeric_summary.json",
        dict(
            ledger_rows=len(ledger),
            native=int(native.sum()),
            source=int(alpha.sum()),
            filter_controlled=int(newmask.sum()),
            encoding_max_roundtrip=max(
                r["maximum"]
                for r in residuals
                if r["test"] == "10cm_inverse_forward_roundtrip"
            ),
            encoding_max_independent=max(
                r["maximum"]
                for r in residuals
                if r["test"] == "25cm_independent_file_equation"
            ),
            boundaries=metrics,
        ),
    )
    print(
        "Evidence ledger:",
        len(ledger),
        "claims; same144406memberships,157identities",
        flush=True,
    )


if __name__ == "__main__":
    main()
