# ruff: noqa: E402
"""Six-branch controlled source/filter/model experiment with explicit refusals."""

import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import (
    ROOT,
    WORK,
    SOURCE,
    LEGACY,
    MODEL,
    PRIOR,
    WAVES,
    SCALE,
    Cube,
    load_module,
    write,
    sha,
    isolated,
    ensure_snapshot,
)  # noqa:E402


def design_audit(mod, cube, eligible, physical, threshold_max=2):
    g = [
        cube.get_ancillary(n)
        for n in ["solar_az", "solar_zn", "sensor_az", "sensor_zn"]
    ]
    g[1] = np.full_like(g[1], np.mean(g[1][cube.mask_no_data], dtype=np.float64))
    kv = mod.calc_volume_kernel(*g, kernel_type="RossThick")
    kg = mod.calc_geom_kernel(*g, kernel_type="LiDenseR", b_r=10, h_b=2)
    design = np.stack([np.ones_like(kv), kv, kg], axis=-1)
    rows = []
    for b, w in enumerate(WAVES):
        use = eligible & np.isfinite(physical[..., b]) & (physical[..., b] >= 0)
        if threshold_max is not None:
            use &= physical[..., b] <= threshold_max
        A = design[use].astype(float)
        y = physical[..., b][use].astype(float)
        if not len(y):
            rows.append(dict(band=b, wavelength_nm=w, n=0, status="UNSUPPORTED"))
            continue
        beta, _, rank, s = np.linalg.lstsq(A, y, rcond=None)
        stable_tol = s[0] * np.sqrt(np.finfo(np.float32).eps)
        stable_rank = int((s > stable_tol).sum())
        rows.append(
            dict(
                band=b,
                wavelength_nm=w,
                n=len(y),
                algebraic_rank=rank,
                stable_rank=stable_rank,
                singular_values=s,
                condition=float(s[0] / s[-1]) if s[-1] > 0 else None,
                coefficients_diagnostic_only=beta,
                status="UNSUPPORTED" if stable_rank < 3 else "ANGULAR_ONLY_SUPPORTED",
                effective_independent_samples="NOT_ESTIMATED; pixels are spatially correlated",
                radiometry_threshold_units="candidate fractional reflectance"
                if physical is not cube.data
                else "historical stored units",
            )
        )
    return rows


def main():
    ensure_snapshot()
    before = load_module(
        "spectralbridge._p172_baseline", HERE / "pre_edit_corrections.py"
    )
    old = load_module("p172_historical", LEGACY)
    original = Path(
        "/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif"
    )
    priorcfg = json.loads((PRIOR / "branches.json").read_text())
    oldraw = Path(priorcfg["branches"]["old_raw"]["path"])
    protected = [
        SOURCE,
        original,
        LEGACY,
        MODEL,
        oldraw,
        Path(priorcfg["polygon_index"]),
        Path("/Users/tuff/Downloads/AOP-GOLDHILL-camera_locations.csv"),
    ]
    for d in [PRIOR, ROOT / "provenance/goldhill-conditional-topographic/2026-11-03"]:
        protected += [p for p in d.iterdir() if p.is_file()]
    protected += [Path(v["path"]) for v in priorcfg["branches"].values()]
    protected = list(dict.fromkeys(protected))
    write(
        "input_manifest.json",
        dict(
            revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            initial_status=subprocess.check_output(
                ["git", "status", "--short"], text=True
            ),
            protected_hashes={str(p): sha(p) for p in protected},
            pre_edit_code={p.name: sha(p) for p in HERE.glob("pre_edit_*.py")},
        ),
    )
    with rasterio.open(SOURCE) as src:
        clean = src.read().transpose(1, 2, 0)
        alpha = src.dataset_mask() > 0
        profile = src.profile.copy()
    a = np.load(oldraw, mmap_mode="r")
    native = np.isfinite(a).all(-1) & (a != -9999).all(-1)
    geometry = {}
    for n in ["slope", "aspect", "solar_zn", "solar_az"]:
        with rasterio.open(
            f"/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_{n}.tif"
        ) as src:
            geometry[n] = src.read(1)
    # Legacy placeholders are replayed explicitly; never assigned to the new H5.
    geometry.update(
        sensor_zn=np.zeros(alpha.shape, np.float32),
        sensor_az=np.zeros(alpha.shape, np.float32),
    )
    with rasterio.open(original) as src:
        valid = (src.read(11) > 0).astype(np.float32)
        weight = np.full(alpha.shape, np.nan, np.float32)
        reproject(
            valid,
            weight,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=profile["transform"],
            dst_crs=profile["crs"],
            src_nodata=None,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    no_background_mix = np.isfinite(weight) & (
        weight >= 1 - 8 * np.finfo(np.float32).eps
    )
    geometry_valid = np.logical_and.reduce(
        [np.isfinite(v) & (v != -9999) for v in geometry.values()]
    )
    geometry_valid &= (
        (geometry["solar_zn"] >= 0)
        & (geometry["solar_zn"] < 90)
        & (geometry["sensor_zn"] >= 0)
        & (geometry["sensor_zn"] < 90)
    )
    cmask = alpha & native & no_background_mix & geometry_valid
    dmask = alpha & np.isfinite(clean).all(-1) & geometry_valid
    np.savez_compressed(
        HERE / "filter_masks.npz",
        historical_native=native,
        source_valid=alpha,
        legacy_estimated_no_background_mix=no_background_mix,
        geometry_numerical=geometry_valid,
        C_revised_prefit=cmask,
        D_revised_prefit=dmask,
        real_view_geometry_available=np.zeros(alpha.shape, bool),
    )
    # Original historical units and filters: no retrospective re-fitting to a prettier image.
    print(
        "Historical full-scene replays A and B with unchanged saved model", flush=True
    )
    for name, data, mask, nodata, prior in [
        ("A", a, native, -9999, priorcfg["branches"]["old_brdf"]["path"]),
        (
            "B",
            clean,
            alpha,
            np.nan,
            priorcfg["branches"]["new_historical_brdf"]["path"],
        ),
    ]:
        cube = Cube(data, mask, geometry, scale=1)
        cube.no_data = nodata
        out = old.apply_brdf_correct(
            cube,
            data,
            0,
            cube.lines,
            0,
            cube.columns,
            brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        np.save(WORK / f"{name}_historical_stored.npy", out)
        previous = np.load(prior, mmap_mode="r")
        finite = np.isfinite(out) & np.isfinite(previous) & (previous != -9999)
        write(
            f"{name}_replay.json",
            dict(
                native_pixels=int(mask.sum()),
                maximum_error_vs_preserved_previous=float(
                    np.max(abs(out[finite] - previous[finite]))
                ),
                validity_exact=bool(
                    np.array_equal(
                        np.isfinite(out) & (out != -9999),
                        np.isfinite(previous) & (previous != -9999),
                    )
                ),
                status="HISTORICAL_DIAGNOSTIC_ONLY_UNSUPPORTED",
                model_sha256=sha(MODEL),
            ),
        )
        del out
    print(
        "Audit historical and revised fitting populations, before angular refusal",
        flush=True,
    )
    oldcube = Cube(a, native, geometry, scale=1)
    cleancube = Cube(clean, alpha, geometry)
    # Known historical band-specific inverse normalization; common target R only a hypothesis.
    scale = np.full(10, SCALE)
    scale[9] = (65535 - 174) / (32768 * 10000)
    offset = np.zeros(10)
    offset[9] = 174 / 32768
    oldcube.radiometry = type(cleancube.radiometry)(
        tuple(scale),
        tuple(offset),
        "HYPOTHETICAL_UNVERIFIED",
        "P172 isolated MicaSense_Metashape_DN_32768 hypothesis",
    )
    raw_old = oldcube.radiometry.to_physical(a)
    raw_old[~native] = np.nan
    raw_clean = cleancube.radiometry.to_physical(clean)
    raw_clean[~alpha] = np.nan
    np.save(WORK / "old_candidate.npy", raw_old)
    np.save(WORK / "clean_candidate.npy", raw_clean)
    audits = {}
    audits["historical_old_stored"] = design_audit(old, oldcube, native, a)
    audits["historical_clean_stored"] = design_audit(old, cleancube, alpha, clean)
    audits["C_revised_historical_math"] = design_audit(old, oldcube, cmask, raw_old)
    audits["D_revised_historical_math"] = design_audit(old, cleancube, dmask, raw_clean)
    write("fitting_population_and_rank.json", audits)
    print(
        "Actual current shared fitter, isolated calibration precondition only",
        flush=True,
    )
    path = isolated(before.fit_and_save_brdf_model)(
        cleancube,
        WORK / "E_before_shared",
        brdf_kernel_config=before.HYTOOLS_BRDF_KERNEL_CONFIG,
        rho_min=0,
        rho_max=None,
    )
    e = json.loads(path.read_text())
    write("E_before_model.json", e)
    # This must refuse and not fabricate corrected E/F arrays.
    assert e["validation"]["status"] == "UNSUPPORTED" and "iso" not in e
    stages = []
    for branch, mask, description in [
        (
            "C",
            cmask,
            "historical contaminated source with revised prefit validity and historical kernel equations",
        ),
        (
            "D",
            dmask,
            "clean source with revised prefit validity and historical kernel equations",
        ),
    ]:
        records = audits[branch + "_revised_historical_math"]
        assert all(r.get("stable_rank", 0) < 3 for r in records)
        stages.append(
            dict(
                branch=branch,
                status="UNSUPPORTED",
                prefit_pixels=int(mask.sum()),
                application_pixels=0,
                image_created=False,
                reason="Numerically stable angular rank1; zero placeholder views are not measured contributors",
                description=description,
            )
        )
    stages += [
        dict(
            branch="E",
            status=e["validation"]["status"],
            prefit_pixels=int(dmask.sum()),
            application_pixels=0,
            image_created=False,
            reason="Correct shared kernels give angular rank1, candidate calibration still unverified",
        ),
        dict(
            branch="F",
            status="NOT_EVALUATED_MISSING_PREREQUISITES",
            application_pixels=0,
            image_created=False,
            reason="No recovered contributor map or independently validated transferable BRDF model. No angle proxy was used as measured geometry.",
        ),
    ]
    write(
        "factorial_status.json",
        [
            dict(
                branch="A",
                status="HISTORICAL_DIAGNOSTIC_ONLY_UNSUPPORTED",
                prefit_pixels=int(native.sum()),
                image_created=True,
            ),
            dict(
                branch="B",
                status="HISTORICAL_DIAGNOSTIC_ONLY_UNSUPPORTED",
                prefit_pixels=int(alpha.sum()),
                image_created=True,
            ),
            *stages,
        ],
    )
    write(
        "filter_counts.json",
        dict(
            total_pixels=int(alpha.size),
            historical_native=int(native.sum()),
            clean_source_valid=int(alpha.sum()),
            historical_on_clean_footprint=int((native & alpha).sum()),
            estimated_legacy_mixed_background_on_clean_footprint=int(
                (alpha & ~no_background_mix).sum()
            ),
            C_revised_prefit=int(cmask.sum()),
            D_revised_prefit=int(dmask.sum()),
            actual_viewing_geometry_available=0,
            BRDF_application_supported=0,
            calibration_status="HYPOTHETICAL_UNVERIFIED",
            hypothesis="MicaSense_Metashape_DN_32768",
            clean_scale=SCALE,
            clean_offset=0,
            historical_inverse_scale=scale,
            historical_inverse_offset=offset,
            mixing_evidence="Bilinear source-validity weight on existing target grid; estimated under the independently supported historical bilinear reconstruction, not an exact recovered exporter. No reflectance cutoff.",
        ),
    )
    print("Baseline experiment complete", flush=True)


if __name__ == "__main__":
    main()
