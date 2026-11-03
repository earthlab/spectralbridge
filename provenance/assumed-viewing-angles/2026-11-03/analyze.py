"""Read-only assumed-angle design experiment on three real drone mosaics.

No drone reflectance fit, external-coefficient bypass, correction raster or
production metadata is created. Unknown radiometry remains unknown.
"""

from pathlib import Path
from types import SimpleNamespace
import importlib.util
import hashlib
import json
import subprocess
import sys

import geopandas as gpd
import h5py
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, geometry_window
from shapely import contains_xy, box

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge import corrections as corr  # noqa: E402
from spectralbridge.radiometry import Radiometry  # noqa: E402

WORK = Path("/private/tmp/assumed-viewing-angles-20261103")
WAVE = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
HEIGHT = dict(gordon=117, goldhill=123, ruby=114)
SCENARIOS = [
    "symmetric_footprints",
    "alternating_strips",
    "mosaic_edges",
    "smooth_map",
    "smooth_map_reflected",
]
CONFIG = corr.HYTOOLS_BRDF_KERNEL_CONFIG
LIMIT = float(1 / np.sqrt(np.finfo(np.float32).eps))
# Import tested prior identity/angle utilities, not its topographic replay/main.
spec = importlib.util.spec_from_file_location(
    "prior_drone_polygon_helpers",
    ROOT / "provenance/drone-brdf-strategy/2026-11-02/analyze.py",
)
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def relative_to_absolute(solar_azimuth_degrees, relative_degrees):
    """Clockwise absolute view azimuth = solar azimuth + signed relative azimuth."""
    return np.remainder(
        np.asarray(solar_azimuth_degrees, np.float64) + relative_degrees, 360
    ).astype(np.float32)


def design(sa, sz, va, vz, mask, scene_solar):
    angles = dict(solar_az=sa, solar_zn=sz, sensor_az=va, sensor_zn=vz)
    cube = SimpleNamespace(mask_no_data=mask)
    cube.get_ancillary = lambda name, radians=True: (
        np.deg2rad(angles[name].astype(np.float32)) if radians else angles[name]
    )
    return corr._brdf_design(cube, CONFIG, scene_solar=scene_solar)[:2]


def diagnostics(singular, n):
    s = np.asarray(singular, float)
    rank = (
        int(np.count_nonzero(s > s[0] * max(n, 3) * np.finfo(float).eps)) if s[0] else 0
    )
    condition = float(s[0] / s[-1]) if s[-1] > 0 else None
    return dict(
        n=int(n),
        rank=rank,
        singular_values=s.tolist(),
        condition_number=condition,
        stable_rank=float(np.sum((s / s[0]) ** 2)),
        condition_limit=LIMIT,
        angular_numerical_gate=bool(
            n >= 4 and rank == 3 and condition is not None and condition <= LIMIT
        ),
        physical_information="NOT_ESTABLISHED: imposed angles are not source observations",
        model_status="UNSUPPORTED: authoritative radiometry and measured angular provenance unavailable",
        response_fit="NOT_PERFORMED; no reflectance fit to assumed angles",
        supported_bands=0,
    )


def weighted_quantiles(x, weights):
    idx = np.argsort(x)
    a = np.asarray(x)[idx]
    w = np.asarray(weights)[idx]
    cum = np.cumsum(w)
    t = np.array([0, 0.01, 0.5, 0.99, 1]) * (cum[-1] - 1)
    lo = a[np.searchsorted(cum, np.floor(t), side="right")]
    hi = a[np.searchsorted(cum, np.ceil(t), side="right")]
    return (lo + (hi - lo) * (t - np.floor(t))).astype(float).tolist()


def constant_case(sa_values, counts, scene_solar, zenith, azimuth, absolute=False):
    sa = sa_values[None, :]
    sz = np.full_like(sa, np.rad2deg(scene_solar))
    vz = np.full_like(sa, zenith)
    va = np.full_like(sa, azimuth) if absolute else relative_to_absolute(sa, azimuth)
    X, mask = design(sa, sz, va, vz, np.ones(sa.shape, bool), scene_solar)
    assert mask.all()
    s = np.linalg.svd(
        X.reshape(-1, 3).astype(float) * np.sqrt(counts[:, None]), compute_uv=False
    )
    row = diagnostics(s, int(counts.sum()))
    # Canonical constant-relative geometry avoids float32 subtraction of varying absolute azimuths.
    k, _ = design(
        np.zeros((1, 1), np.float32),
        np.full((1, 1), np.rad2deg(scene_solar), np.float32),
        np.full((1, 1), azimuth, np.float32),
        np.full((1, 1), zenith, np.float32),
        np.ones((1, 1), bool),
        scene_solar,
    )
    row.update(
        view_zenith_degrees=zenith,
        relative_azimuth_degrees=None if absolute else azimuth,
        absolute_sensor_azimuth_degrees=azimuth if absolute else None,
        canonical_distinct_kernel_rows=None if absolute else 1,
        canonical_constant_relative_rank=None if absolute else 1,
        RossThick=float(k[0, 0, 1])
        if not absolute
        else float(np.average(X[0, :, 1], weights=counts)),
        LiDenseR=float(k[0, 0, 2])
        if not absolute
        else float(np.average(X[0, :, 2], weights=counts)),
        kernel_quantiles_0_1_50_99_100={
            name: weighted_quantiles(X[0, :, i], counts)
            for name, i in [("RossThick", 1), ("LiDenseR", 2)]
        },
        independent_coefficients_from_constant_relative_geometry=None
        if absolute
        else 1,
    )
    return row


def scenario_map(name, y0, y1, height, width, pixel_m, altitude):
    y, x = np.broadcast_arrays(
        np.arange(y0, y1, dtype=float)[:, None], np.arange(width, dtype=float)[None, :]
    )
    u = 2 * (x + 0.5) / width - 1
    v = 2 * (y + 0.5) / height - 1
    half_swath = altitude * (1280 * 0.00375 / 2) / 5.5
    if name == "symmetric_footprints":
        offset = ((x + 0.5) * pixel_m + half_swath) % (2 * half_swath) - half_swath
        zen = np.rad2deg(np.arctan(abs(offset) / altitude))
        az = np.where(offset >= 0, 90.0, 270.0)
    elif name == "alternating_strips":
        zen = np.full_like(x, 15.0)
        az = np.where(
            (np.floor((x + 0.5) * pixel_m / half_swath).astype(int) % 2) == 0,
            0.0,
            180.0,
        )
    elif name == "mosaic_edges":
        zen = 25 * np.maximum(abs(u), abs(v))
        az = (np.rad2deg(np.arctan2(u, -v)) + 360) % 360
    elif name in ("smooth_map", "smooth_map_reflected"):
        if name.endswith("reflected"):
            u = -u
        zen = 5 + 10 * (u + 1)
        az = (180 * (v + 1) + 60 * u) % 360
    else:
        raise ValueError(name)
    return zen.astype(np.float32), az.astype(np.float32)


def spectral_valid_mask(finite_h5, alpha):
    """Separate observed raw support from finite transparent-background storage."""
    return finite_h5 & np.isfinite(alpha) & (alpha > 0)


def baseline_polygons(name, src, raw, valid, polygons, independent):
    rows = []
    for _, p in polygons.iterrows():
        try:
            w = geometry_window(src, [p.geometry], boundless=False)
        except rasterio.errors.WindowError:
            continue
        ry, rx = w.toslices()
        inside = (
            geometry_mask(
                [p.geometry],
                out_shape=(int(w.height), int(w.width)),
                transform=src.window_transform(w),
                invert=True,
                all_touched=False,
            )
            & valid[ry, rx]
        )
        if not inside.any():
            continue
        yy, xx = np.nonzero(inside)
        east = src.transform.c + (xx + w.col_off + 0.5) * src.transform.a
        north = src.transform.f + (yy + w.row_off + 0.5) * src.transform.e
        assert contains_xy(p.geometry, east, north).all()
        pixels = raw[ry, rx][inside]
        center = np.median(pixels, axis=0)
        sd = (
            pixels.std(axis=0, ddof=1, dtype=float)
            if len(pixels) > 1
            else np.full(10, np.nan)
        )
        c = p.geometry.centroid
        row = dict(
            flight=name,
            GlobalID=str(p.GlobalID),
            cover_category=str(p.cover_category),
            species=str(p.species),
            pixels=len(pixels),
            independent_component_representative=p.GlobalID in independent,
            spatial_block=f"{int(c.x // 100)}_{int(c.y // 100)}",
            median_pixel_angle_degrees=float(
                np.nanmedian(prior.angle_degrees(pixels, center))
            ),
            mean_band_variance_dn2=float(np.nanmean(sd**2)),
            median_band_cv=float(
                np.nanmedian(sd / np.maximum(abs(pixels.mean(0, dtype=float)), 1e-12))
            ),
        )
        row.update({f"b{i + 1}": float(t) for i, t in enumerate(center)})
        for label, i, j in prior.index_band_pairs(WAVE):
            row[label] = float(np.nanmedian(prior.ratio_index(pixels, i, j)))
        rows.append(row)
    return rows


def main():
    print("Hashing immutable source inputs", flush=True)
    protected = json.loads(
        (ROOT / "provenance/drone-brdf-strategy/2026-11-02/manifest.json").read_text()
    )["inputs_before"]
    polygon = (
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
    )
    inputs = {str(polygon): sha(polygon)}
    restored = []
    missing = []
    for path, digest in protected.items():
        p = Path(path)
        if p.exists():
            inputs[str(p)] = sha(p)
            assert inputs[str(p)] == digest, str(p)
        elif path.endswith("__working.h5"):
            name = (
                "gordon"
                if "GORDON" in path
                else "goldhill"
                if "GOLDHILL" in path
                else "ruby"
            )
            p = WORK / f"{name}_working.h5"
            inputs[str(p)] = sha(p)
            assert inputs[str(p)] == digest, str(p)
            restored.append(
                dict(
                    previous_path=path,
                    restored_path=str(p),
                    sha256=digest,
                    remote_origin="i:/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/gordon_goldhill_ruby_20261029_v1/flight_products/"
                    + path.split("/flight_products/")[1],
                )
            )
        else:
            missing.append(
                dict(
                    path=path,
                    previous_sha256=digest,
                    status="Not present locally; not overwritten or reconstructed",
                )
            )
    for p in [
        ROOT / "src/spectralbridge/corrections.py",
        ROOT / "src/spectralbridge/radiometry.py",
        ROOT / "src/spectralbridge/io/neon.py",
        ROOT
        / "provenance/drone-scale-confirmation/2026-10-30/verified_numeric_mapping.json",
    ]:
        inputs[str(p)] = sha(p)
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    source_status = subprocess.check_output(
        ["git", "status", "--short"], cwd=ROOT, text=True
    )
    write(
        "input_manifest.json",
        dict(
            revision=revision,
            dirty_worktree=True,
            status_at_start=source_status,
            inputs_before=inputs,
            restored=restored,
            prior_inputs_not_present=missing,
        ),
    )
    polys = gpd.read_file(polygon)
    assert polys.GlobalID.is_unique
    const = []
    absolute = []
    spatial = []
    baseline = []
    flights = {}
    angle_poly = []
    for name in ["gordon", "goldhill", "ruby"]:
        print("Analyzing", name, flush=True)
        raw = np.load(
            f"/private/tmp/drone-brdf-strategy-20261102/{name}_raw.npy", mmap_mode="r"
        )
        raw_hash = sha(f"/private/tmp/drone-brdf-strategy-20261102/{name}_raw.npy")
        inputs[f"/private/tmp/drone-brdf-strategy-20261102/{name}_raw.npy"] = raw_hash
        h5 = WORK / f"{name}_working.h5"
        with h5py.File(h5, "r") as h:
            group = h[next(iter(h))]["Reflectance"]
            meta = group["Metadata"]
            data = group["Reflectance_Data"]
            np.testing.assert_array_equal(
                meta["Spectral_Data"]["Wavelength"][...], WAVE
            )
            sa = meta["Solar_Azimuth_Angle"][...]
            sz = meta["Solar_Zenith_Angle"][...]
            assert (
                float(meta["to-sensor_Zenith_Angle"][()])
                == float(meta["to-sensor_Azimuth_Angle"][()])
                == 0.0
            )
            valid = np.zeros(raw.shape[:2], bool)
            with rasterio.open(
                f"/private/tmp/goldhill-radiometric-recovery-20261102/{name}_recovered_source_dn.tif"
            ) as src:
                assert raw.shape[:2] == src.shape == data.shape[:2]
                assert (
                    src.crs.to_epsg() == 26913
                    and src.transform.e < 0
                    and src.transform.a > 0
                )
                for y in range(0, len(raw), 128):
                    a = np.asarray(data[y : y + 128])
                    valid[y : y + 128] = np.isfinite(a).all(-1)
                    b = src.read(
                        list(range(1, 11)),
                        window=((y, min(y + 128, len(raw))), (0, src.width)),
                    ).transpose(1, 2, 0)
                    np.testing.assert_array_equal(raw[y : y + 128], b)
                frame = polys.to_crs(src.crs)
                frame = (
                    frame[frame.intersects(box(*src.bounds))]
                    .copy()
                    .reset_index(drop=True)
                )
                indep = set(prior.independent_polygons(frame).GlobalID)
                # Alpha zero is transparent background, even where H5 values are finite.
                alpha = src.read(11)
                library_valid = spectral_valid_mask(valid, alpha)
                baseline += baseline_polygons(
                    name, src, raw, library_valid, frame, indep
                )
                del alpha
                tr = list(src.transform)
                bounds = list(src.bounds)
            assert np.array_equal(valid, np.isfinite(raw).all(-1))
            count = int(valid.sum())
            assert (
                count
                == json.loads(
                    (
                        ROOT
                        / f"provenance/drone-brdf-strategy/2026-11-02/{name}_angular_diagnostics.json"
                    ).read_text()
                )["source_valid_pixels"]
            )
            scene = float(
                np.mean(np.deg2rad(sz.astype(np.float32))[valid], dtype=np.float64)
            )
            sv, weights = np.unique(sa[valid], return_counts=True)
            for theta in [0, 5, 10, 15, 20, 25, 30]:
                for rel in [0] if theta == 0 else [0, 45, 90, 135, 180]:
                    row = constant_case(sv, weights, scene, theta, rel)
                    row.update(flight=name, case="constant_relative")
                    const.append(row)
                    assert not row["angular_numerical_gate"]
            for theta in [10, 15]:
                for az in [0, 90, 180, 270]:
                    row = constant_case(sv, weights, scene, theta, az, True)
                    row.update(flight=name, case="constant_absolute")
                    absolute.append(row)
            # Numerical rank reduction streams QR; no pixel-scale state table/cache.
            displays = {}
            for scenario in SCENARIOS:
                print(name, scenario, flush=True)
                R = np.zeros((0, 3))
                n = 0
                extrema = np.array([[np.inf, -np.inf], [np.inf, -np.inf]])
                total = np.zeros(2)
                sample = []
                # Compact raster of kernel geometry only for plotting and polygon angle summaries.
                kmap = np.empty((*valid.shape, 2), np.float32)
                for y in range(0, len(raw), 128):
                    end = min(y + 128, len(raw))
                    vz, va = scenario_map(
                        scenario, y, end, *valid.shape, tr[0], HEIGHT[name]
                    )
                    X, ok = design(sa[y:end], sz[y:end], va, vz, valid[y:end], scene)
                    A = X[ok].astype(float)
                    n += len(A)
                    R = np.linalg.qr(np.vstack([R, A]), mode="r")
                    total += A[:, 1:].sum(0)
                    for b in range(2):
                        extrema[b, 0] = min(extrema[b, 0], A[:, b + 1].min())
                        extrema[b, 1] = max(extrema[b, 1], A[:, b + 1].max())
                    sample.append(A[::97, 1:])
                    kmap[y:end] = X[..., 1:]
                d = diagnostics(np.linalg.svd(R, compute_uv=False), n)
                d.update(
                    flight=name,
                    scenario=scenario,
                    angle_type="SYNTHETIC / illustrative, not recovered",
                    kernel_min_max=extrema.tolist(),
                    kernel_mean=(total / n).tolist(),
                    kernel_sample_quantiles=np.percentile(
                        np.vstack(sample), [0, 1, 50, 99, 100], axis=0
                    ).tolist(),
                    quantile_scope="Deterministic every-97th supported cell within each 128-row strip; rank/extrema/means use all source-valid pixels",
                )
                spatial.append(d)
                # Source-polygon averages of imposed kernels: potential confounding, not a reflectance regression.
                with rasterio.open(
                    f"/private/tmp/goldhill-radiometric-recovery-20261102/{name}_recovered_source_dn.tif"
                ) as src:
                    for _, p in frame.iterrows():
                        try:
                            w = geometry_window(src, [p.geometry], boundless=False)
                        except rasterio.errors.WindowError:
                            continue
                        ry, rx = w.toslices()
                        inside = (
                            geometry_mask(
                                [p.geometry],
                                out_shape=(int(w.height), int(w.width)),
                                transform=src.window_transform(w),
                                invert=True,
                            )
                            & valid[ry, rx]
                        )
                        if inside.any():
                            v = kmap[ry, rx][inside].mean(0, dtype=float)
                            angle_poly.append(
                                dict(
                                    flight=name,
                                    scenario=scenario,
                                    GlobalID=str(p.GlobalID),
                                    cover_category=str(p.cover_category),
                                    RossThick_mean=float(v[0]),
                                    LiDenseR_mean=float(v[1]),
                                )
                            )
                vz, va = scenario_map(
                    scenario, 0, len(raw), *valid.shape, tr[0], HEIGHT[name]
                )
                displays[scenario + "_zenith"] = vz[::8, ::8]
                displays[scenario + "_azimuth"] = va[::8, ::8]
                displays[scenario + "_kv"] = kmap[::8, ::8, 0]
                displays[scenario + "_kg"] = kmap[::8, ::8, 1]
                del kmap, vz, va
            displays.update(
                raw=raw[::8, ::8],
                valid=library_valid[::8, ::8],
                finite_h5_valid=valid[::8, ::8],
                solar_zenith=sz[::8, ::8],
                solar_azimuth=sa[::8, ::8],
            )
            np.savez_compressed(HERE / f"{name}_display.npz", **displays)
            flights[name] = dict(
                shape=list(raw.shape),
                source_valid_pixels=count,
                alpha_positive_raw_pixels=int(library_valid.sum()),
                spectral_population="Finite H5 source values intersect positive retained TIFF alpha; transparent background excluded without altering files",
                solar_scene_zenith_degrees=float(np.rad2deg(scene)),
                solar_azimuth_min_max=[float(sa[valid].min()), float(sa[valid].max())],
                solar_metadata={k: str(v) for k, v in meta.attrs.items()},
                grid_transform=tr,
                crs="EPSG:26913",
                bounds=bounds,
                source_dn_array_equals_recovered_tiff=True,
                polygons_overlapping=len(frame),
                flying_altitude_report_m=HEIGHT[name],
                nominal_focal_length_mm=5.5,
                pixel_pitch_mm=0.00375,
                sensor_resolution=[1280, 960],
                horizontal_half_fov_deg=float(
                    np.rad2deg(np.arctan(1280 * 0.00375 / 11))
                ),
                vertical_half_fov_deg=float(np.rad2deg(np.arctan(960 * 0.00375 / 11))),
                diagonal_half_fov_deg=float(
                    np.rad2deg(np.arctan(np.hypot(1280 * 0.00375, 960 * 0.00375) / 11))
                ),
                reference="45 degree solar, nadir view, relative azimuth 0; unchanged package reference",
                units="RECOVERED_SOURCE_DN - PHYSICAL_UNITS_UNVERIFIED",
                factor_distribution=None,
                invalid_model_predictions=None,
                corrected_PFT_changes=None,
                correction_status="NOT_EVALUATED: no suitable independent coefficients; no assumed-angle refits",
            )
        del raw, sa, sz, valid
    frame = pd.DataFrame(baseline)
    frame.to_csv(HERE / "baseline_polygon_spectra.csv", index=False)
    # Existing polygon summary algorithms; no topo branch, no correction and no reflectance fit.
    frame["branch"] = "uncorrected_source_dn"
    frame["incidence_median"] = np.nan
    prior.HERE = HERE
    prior.evaluate_polygons(frame)
    pd.DataFrame(angle_poly).to_csv(HERE / "synthetic_polygon_kernels.csv", index=False)
    write("constant_geometries.json", const)
    write("constant_absolute_checks.json", absolute)
    write("spatial_geometries.json", spatial)
    write("flight_baselines.json", flights)
    pd.DataFrame(
        [{k: v for k, v in r.items() if not isinstance(v, (dict, list))} for r in const]
    ).to_csv(HERE / "constant_geometries.csv", index=False)
    pd.DataFrame(
        [
            {k: v for k, v in r.items() if not isinstance(v, (dict, list))}
            for r in spatial
        ]
    ).to_csv(HERE / "spatial_geometries.csv", index=False)
    # Re-evaluate the actual zero-view fitter: unknown units stop it without invented calibration.
    z = SimpleNamespace(
        data=np.full((4, 5, 2), 250.0, np.float32),
        mask_no_data=np.ones((4, 5), bool),
        bands=2,
        no_data=-9999.0,
        wavelengths=np.array([650.0, 862.0]),
        radiometry=Radiometry(
            None,
            None,
            "UNSUPPORTED",
            "Actual flight physical calibration remains unverified",
        ),
    )
    z.get_ancillary = lambda name, radians=True: np.full(
        (4, 5), 0.5 if name == "solar_zn" else 0.0, np.float32
    )
    p = corr.fit_and_save_brdf_model(
        z, WORK / "unknown_radiometry_gate", brdf_kernel_config=CONFIG
    )
    gate = json.loads(p.read_text())
    assert gate["validation"]["status"] == "UNSUPPORTED" and "iso" not in gate
    write(
        "gate_contract_control.json",
        dict(
            scope="Small synthetic contract control, not imagery or fitted flight",
            validation=gate["validation"],
            no_usable_coefficients=True,
        ),
    )
    after = {p: sha(p) for p in inputs}
    assert after == inputs
    write(
        "preservation.json",
        dict(
            inputs_before=inputs,
            inputs_after=after,
            unchanged=True,
            restored=restored,
            prior_inputs_not_present=missing,
            revision=revision,
            production_writes=False,
            generated_corrected_rasters=0,
        ),
    )
    write(
        "experiment_summary.json",
        dict(
            flights=flights,
            constant_cases=len(const),
            spatial_cases=len(spatial),
            absolute_checks=len(absolute),
            constant_numerical_gate_passes=sum(
                r["angular_numerical_gate"] for r in const
            ),
            spatial_numerical_gate_passes=sum(
                r["angular_numerical_gate"] for r in spatial
            ),
            physically_supported_fits=0,
            eligible_independent_coefficient_sets=0,
            baseline_polygons=len(frame),
            baseline_polygon_pixel_memberships=int(frame.pixels.sum()),
            correction_comparisons_status="NOT_EVALUATED; no eligible independent coefficient set, no refit to invented angles",
            protected_inputs_unchanged=True,
        ),
    )
    print("Completed read-only designs and raw polygon baseline", flush=True)


if __name__ == "__main__":
    main()
