"""Read-only anatomy of the historical BRDF failure on verified repaired grids.

The pinned October 26 implementation is imported exclusively for isolated replay.
Current fail-closed production functions are never substituted into that replay.
"""

from pathlib import Path
from itertools import combinations
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, geometry_window
from scipy.ndimage import distance_transform_edt
from shapely import box, contains_xy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/brdf-artifact-anatomy-20261103")
PRIOR = Path("/private/tmp/goldhill-radiometric-recovery-20261102")
H5ROOT = Path("/private/tmp/assumed-viewing-angles-20261103")
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.neon_cube import NeonCube  # noqa: E402
from spectralbridge import corrections as modern  # noqa: E402
from spectralbridge.radiometry import dataset_radiometry  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "anatomy_polygon_helpers",
    ROOT / "provenance/drone-brdf-strategy/2026-11-02/analyze.py",
)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
WAVE = helpers.WAVE
OLD_PATH = (
    ROOT / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
)
OLD_HASH = "839cdf2b7264c5af53902c08994144c776f94f5a59f31dc42bd1574002998a42"
OLD_REV = "1cb2cf3a6c34e6665f0c5b1661724428f46f80ea"
STAGES = ["raw", "topo", "brdf", "combined"]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def dist(x):
    a = np.asarray(x)
    a = a[np.isfinite(a)]
    if not len(a):
        return dict(n=0, min=None, max=None, median=None, range=None, quantiles=None)
    q = np.percentile(a, [0, 1, 25, 50, 75, 95, 99, 100])
    return dict(
        n=int(len(a)),
        min=float(q[0]),
        max=float(q[-1]),
        median=float(q[3]),
        range=float(q[-1] - q[0]),
        quantiles=q.tolist(),
    )


def boundary_edges(state, valid):
    return [
        ((state[:, :-1] != state[:, 1:]) & valid[:, :-1] & valid[:, 1:]),
        ((state[:-1] != state[1:]) & valid[:-1] & valid[1:]),
    ]


def boundary_comparison(first, second, valid, pixel_m=0.1):
    a = boundary_edges(first, valid)
    b = boundary_edges(second, valid)
    na = sum(int(x.sum()) for x in a)
    nb = sum(int(x.sum()) for x in b)
    inter = sum(int((x & y).sum()) for x, y in zip(a, b))
    xor = sum(int((x != y).sum()) for x, y in zip(a, b))
    # Displacement measured between like-oriented edge grids, not image thresholds or smoothed contours.
    distances = []
    for x, y in zip(a, b):
        if y.any() and x.any():
            distances.append(distance_transform_edt(~y)[x] * pixel_m)
    dd = np.concatenate(distances) if distances else np.array([])
    return dict(
        actual_edges=na,
        predicted_edges=nb,
        intersection_edges=inter,
        xor_edges=xor,
        dice=2 * inter / (na + nb) if na + nb else None,
        max_directed_edge_displacement_m=float(dd.max()) if len(dd) else None,
        median_directed_edge_displacement_m=float(np.median(dd)) if len(dd) else None,
        population="Adjacent native pixels with valid measured source support at both ends; no morphological smoothing",
    )


def apply_factor(den, num, visited):
    """Exact historical factor policy; not a replacement production implementation."""
    positive = (den > 0) & (num > 0)
    factor = np.ones_like(den, dtype=np.float32)
    np.divide(num, den, out=factor, where=positive)
    ratio_bad = ~np.isfinite(factor) | (factor <= 0)
    factor = np.where(~ratio_bad, factor, 1.0).astype(np.float32)
    factor[~visited] = 1
    return factor, positive, ratio_bad


def visit_mask(old, cube, values, model):
    edges = np.asarray(model["ndvi_edges"], np.float32)
    ndvi = old.compute_ndvi(cube, values)
    ix = np.digitize(ndvi, edges, right=False) - 1
    ix[(ndvi < edges[0]) | (ndvi > edges[-1])] = -1
    ix[ix < 0] = 0
    return ix < len(edges) - 1


def fit_counts_and_ranks(raw, kv, kg, mask, model):
    rows = []
    for b in range(raw.shape[-1]):
        eligible = (
            mask & np.isfinite(raw[..., b]) & (raw[..., b] >= 0) & (raw[..., b] <= 2)
        )
        n = int(eligible.sum())
        actual = np.array([model[k][0][b] for k in ["iso", "vol", "geo"]], np.float32)
        row = dict(
            band=b + 1,
            wavelength_nm=int(WAVE[b]),
            eligible_pixels=n,
            actual_coefficients=actual.tolist(),
            rank=None,
            condition_number=None,
            reconstructed=None,
            coefficient_exact_match=None,
        )
        if n >= 3:
            X = np.column_stack(
                [np.ones(n, np.float32), kv[eligible], kg[eligible]]
            ).astype(float)
            beta, _, rank, s = np.linalg.lstsq(
                X, raw[..., b][eligible].astype(float), rcond=None
            )
            row.update(
                rank=int(rank),
                condition_number=float(s[0] / s[-1]) if s[-1] > 0 else None,
                reconstructed=beta.astype(np.float32).tolist(),
                coefficient_exact_match=bool(
                    np.array_equal(actual, beta.astype(np.float32))
                ),
            )
            # Exact-fit verification required for the two previously verified mechanism bands.
            if b in [3, 4]:
                assert row["coefficient_exact_match"], row
        rows.append(row)
    return rows


def polygon_metrics(src, polys, values, common, factor_red, den_red):
    rows = []
    geometry = []
    for p in polys.itertuples():
        if p.geometry is None or p.geometry.is_empty:
            continue
        try:
            w = geometry_window(src, [p.geometry])
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
            & common[ry, rx]
        )
        if not inside.any():
            continue
        yy, xx = np.nonzero(inside)
        east = src.transform.c + (xx + w.col_off + 0.5) * src.transform.a
        north = src.transform.f + (yy + w.row_off + 0.5) * src.transform.e
        assert contains_xy(p.geometry, east, north).all()
        rawpix = values["raw"][ry, rx][inside]
        rawmed = np.median(rawpix, 0)
        af = float(np.mean(factor_red[ry, rx][inside] > 10))
        fall = float(np.mean(den_red[ry, rx][inside] <= 0))
        geom = dict(
            GlobalID=str(p.GlobalID),
            cover_category=str(p.cover_category),
            species=str(p.species),
            pixels=int(inside.sum()),
            row_center=float(
                (p.geometry.centroid.y - src.transform.f) / src.transform.e
            ),
            col_center=float(
                (p.geometry.centroid.x - src.transform.c) / src.transform.a
            ),
            geometry_wkt=p.geometry.wkt,
            red_amplified_fraction=af,
            red_nonpositive_fraction=fall,
            raw_within_angle=float(np.median(helpers.angle_degrees(rawpix, rawmed))),
        )
        geometry.append(geom)
        for name, array in values.items():
            pixels = array[ry, rx][inside]
            med = np.median(pixels, 0)
            sd = (
                pixels.std(0, ddof=1, dtype=float)
                if len(pixels) > 1
                else np.full(10, np.nan)
            )
            mean = pixels.mean(0, dtype=float)
            row = dict(
                GlobalID=str(p.GlobalID),
                cover_category=str(p.cover_category),
                species=str(p.species),
                stage=name,
                pixels=len(pixels),
                source_alpha_positive_common_mask=True,
                within_mean_variance_S2=float(np.mean(sd**2)),
                median_band_CV=float(np.nanmedian(sd / np.maximum(abs(mean), 1e-12))),
                median_within_pixel_angle_deg=float(
                    np.median(helpers.angle_degrees(pixels, med))
                ),
                median_spectrum_angle_from_raw_deg=float(
                    helpers.angle_degrees(med, rawmed)
                ),
                red_gain_over10_fraction=af,
                red_nonpositive_pred_fraction=fall,
                nonfinite_values=0,
            )
            for i, x in enumerate(med):
                row[f"b{i + 1}"] = float(x)
                row[f"q25_b{i + 1}"] = float(np.percentile(pixels[:, i], 25))
                row[f"q75_b{i + 1}"] = float(np.percentile(pixels[:, i], 75))
            for label, w1, w2 in [
                ("NDVI668", 862, 668),
                ("NDVI650", 862, 650),
                ("NDRE705", 862, 705),
                ("GNDVI560", 862, 560),
            ]:
                i = int(np.argmin(abs(WAVE - w1)))
                j = int(np.argmin(abs(WAVE - w2)))
                row[label] = float(np.nanmedian(helpers.ratio_index(pixels, i, j)))
            rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(geometry)


def main():
    WORK.mkdir(exist_ok=True, parents=True)
    assert sha(OLD_PATH) == OLD_HASH
    pinned = subprocess.check_output(
        ["git", "show", OLD_REV + ":src/spectralbridge/corrections.py"], cwd=ROOT
    )
    assert hashlib.sha256(pinned).hexdigest() == OLD_HASH
    spec = importlib.util.spec_from_file_location(
        "isolated_artifact_historical", OLD_PATH
    )
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)
    polygon_path = (
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
    )
    protected = [
        OLD_PATH,
        polygon_path,
        ROOT / "src/spectralbridge/corrections.py",
        ROOT / "src/spectralbridge/io/neon.py",
    ]
    for name, tag in [("gordon", "GORDON"), ("goldhill", "GOLDHILL"), ("ruby", "Ruby")]:
        protected += [
            H5ROOT / f"{name}_working.h5",
            PRIOR / f"{name}_recovered_source_dn.tif",
            WORK / "models" / f"AOP_{tag}_20230814__brdf_model.json",
        ]
    protected += [PRIOR / f"normalized_{s}.npy" for s in STAGES] + [
        PRIOR / "red_factor.npy",
        PRIOR / "red_denominator.npy",
    ]
    before = {str(p): sha(p) for p in protected}
    write(
        "provenance.json",
        dict(
            repository_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            historical_implementation_revision=OLD_REV,
            historical_sha256=OLD_HASH,
            original_run_QA_revision="ecd0df27dc98ebe30e40bfad0e7d7e7c9d28b563",
            source_hashes_before=before,
            scope="Isolated diagnostic replay. No production writes. Restored H5s have prior-verified identities; Goldhill saved arrays reused.",
        ),
    )
    polygons = gpd.read_file(polygon_path)
    allbands = []
    allfits = []
    flights = {}
    geostats = []
    comparison = {}
    pixelrows = []
    transects = []
    classrows = []
    oldminmax = json.loads(
        (
            ROOT
            / "provenance/drone-scale-confirmation/2026-10-30/verified_numeric_mapping.json"
        ).read_text()
    )
    for name, tag in [("goldhill", "GOLDHILL"), ("gordon", "GORDON"), ("ruby", "Ruby")]:
        print("Historical geometry and factors", name, flush=True)
        cube = NeonCube(H5ROOT / f"{name}_working.h5")
        np.testing.assert_array_equal(cube.wavelengths, WAVE)
        model = json.loads(
            (WORK / "models" / f"AOP_{tag}_20230814__brdf_model.json").read_text()
        )
        cube.brdf_coefficients = copy.deepcopy(model)
        raw = cube.data
        with rasterio.open(PRIOR / f"{name}_recovered_source_dn.tif") as src:
            alpha = src.read(11)
            tr = src.transform
            crs = src.crs
            bounds = src.bounds
            assert raw.shape[:2] == src.shape and crs.to_epsg() == 26913 and tr.e < 0
            pol = polygons.to_crs(crs)
            pol = pol[pol.intersects(box(*bounds))].copy()
        finite = np.isfinite(raw).all(-1) & cube.mask_no_data
        observed = finite & np.isfinite(alpha) & (alpha > 0)
        deg = {
            k: cube.get_ancillary(k, radians=False)
            for k in [
                "solar_zn",
                "solar_az",
                "sensor_zn",
                "sensor_az",
                "slope",
                "aspect",
            ]
        }
        rad = {k: cube.get_ancillary(k, radians=True) for k in deg}
        scenez = old._resolve_scene_solar_zenith(rad["solar_zn"])
        kv = old.calc_volume_kernel(
            rad["solar_az"],
            scenez,
            rad["sensor_az"],
            rad["sensor_zn"],
            kernel_type=model["volume_kernel"],
        )
        kg = old.calc_geom_kernel(
            rad["solar_az"],
            scenez,
            rad["sensor_az"],
            rad["sensor_zn"],
            kernel_type=model["geom_kernel"],
            b_r=model["b_r"],
            h_b=model["h_b"],
        )
        zero = np.zeros_like(kv)
        rs = np.full_like(kv, np.deg2rad(45.0))
        rv = old.calc_volume_kernel(
            zero, rs, zero, zero, kernel_type=model["volume_kernel"]
        )
        rg = old.calc_geom_kernel(
            zero,
            rs,
            zero,
            zero,
            kernel_type=model["geom_kernel"],
            b_r=model["b_r"],
            h_b=model["h_b"],
        )
        X = np.stack([np.ones_like(kv), kv, kg], axis=-1)
        oldrank = helpers.matrix_diagnostics(X[finite])
        del X
        newX, newmask, _ = modern._brdf_design(cube, modern.HYTOOLS_BRDF_KERNEL_CONFIG)
        newrank = helpers.matrix_diagnostics(newX[finite & newmask])
        newkv = newX[..., 1].copy()
        newkg = newX[..., 2].copy()
        del newX
        vis = visit_mask(old, cube, raw, model)
        if name == "goldhill":
            values = {
                s: np.load(PRIOR / f"normalized_{s}.npy", mmap_mode="r") for s in STAGES
            }
            np.testing.assert_array_equal(raw, values["raw"])
        else:
            print(
                "Necessary uncached historical SCS+C/combined reconstruction",
                name,
                flush=True,
            )
            top = old.apply_topo_correct(cube, raw, 0, cube.lines, 0, cube.columns)
            comb = old.apply_brdf_correct(
                cube,
                top,
                0,
                cube.lines,
                0,
                cube.columns,
                brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
            )
            br = old.apply_brdf_correct(
                cube,
                raw,
                0,
                cube.lines,
                0,
                cube.columns,
                brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
            )
            values = dict(raw=raw, topo=top, brdf=br, combined=comb)
        common = observed.copy()
        for data in values.values():
            common &= np.isfinite(data).all(-1)
        fitinfo = (
            fit_counts_and_ranks(raw, kv, kg, finite, model)
            if name == "goldhill"
            else []
        )
        allfits += fitinfo
        shape = raw.shape[:2]
        stride = 6 if name == "goldhill" else 8
        ss = (slice(None, None, stride), slice(None, None, stride))
        displays = {s: np.asarray(v[ss]) for s, v in values.items()}
        displays.update(
            observed=observed[ss],
            finite=finite[ss],
            common=common[ss],
            kv_old=kv[ss],
            kg_old=kg[ss],
            kv_current=newkv[ss],
            kg_current=newkg[ss],
        )
        displays.update({k: v[ss] for k, v in deg.items()})
        fac_small = []
        den_small = []
        num_scalar = []
        red_den = None
        red_num = None
        red_factor = None
        for b in range(10):
            iso, vol, geo = [np.float32(model[k][0][b]) for k in ["iso", "vol", "geo"]]
            den = iso + vol * kv + geo * kg
            num = iso + vol * rv + geo * rg
            factor, positive, bad = apply_factor(den, num, vis)
            expected = raw[..., b] * factor
            actual = values["brdf"][..., b]
            good = np.isfinite(actual) & finite
            mismatch = int(np.count_nonzero(expected[good] != actual[good]))
            assert mismatch == 0, (name, b, mismatch)
            row = dict(
                flight=name,
                band=b + 1,
                wavelength_nm=int(WAVE[b]),
                iso=float(iso),
                vol=float(vol),
                geo=float(geo),
                predicted_observed=dist(den[finite]),
                predicted_reference=dist(num[finite]),
                factor_full_H5=dist(factor[finite]),
                factor_observed_alpha=dist(factor[observed]),
                factor_common=dist(factor[common]),
                nonpositive_observed_fraction=float(np.mean(den[finite] <= 0)),
                nonpositive_reference_fraction=float(np.mean(num[finite] <= 0)),
                historical_positivity_fallback_fraction=float(
                    np.mean(~positive[finite])
                ),
                unvisited_bin_pixels=int((finite & ~vis).sum()),
                gains_over10=int((finite & (factor > 10)).sum()),
                gains_over1000=int((finite & (factor > 1000)).sum()),
                gains_over10_observed_fraction=float(np.mean(factor[observed] > 10)),
                invalid_ratio_fallback_pixels=int((finite & bad).sum()),
                formula_replay_mismatches=mismatch,
                raw_stored_S=dist(raw[..., b][common]),
                combined_stored_S=dist(values["combined"][..., b][common]),
            )
            allbands.append(row)
            fac_small.append(factor[ss])
            den_small.append(den[ss])
            num_scalar.append(float(num[0, 0]))
            if b == 4:
                red_den = den.copy()
                red_num = num.copy()
                red_factor = factor.copy()
                if name == "goldhill":
                    np.testing.assert_array_equal(
                        factor, np.load(PRIOR / "red_factor.npy", mmap_mode="r")
                    )
                    np.testing.assert_array_equal(
                        den, np.load(PRIOR / "red_denominator.npy", mmap_mode="r")
                    )
        displays.update(
            factors=np.stack(fac_small, axis=-1),
            predictions=np.stack(den_small, axis=-1),
            reference=np.array(num_scalar),
            red_factor=red_factor[ss],
            red_den=red_den[ss],
            visited=vis[ss],
        )
        # Actual solar gradients in projected metres; no inference about camera trajectories.
        yy, xx = np.indices(shape)
        east = tr.c + (xx + 0.5) * tr.a
        north = tr.f + (yy + 0.5) * tr.e
        for k, array in deg.items():
            rec = dict(flight=name, field=k, **dist(array[observed]))
            if k in ["solar_zn", "solar_az"]:
                v = array[ss]
                m = observed[ss]
                ex = east[ss][m]
                ny = north[ss][m]
                A = np.column_stack([ex - ex.mean(), ny - ny.mean(), np.ones(len(ex))])
                beta = np.linalg.lstsq(A, v[m].astype(float), rcond=None)[0]
                rec.update(
                    east_gradient_degrees_per_m=float(beta[0]),
                    north_gradient_degrees_per_m=float(beta[1]),
                    gradient_bearing_clockwise_north_degrees=float(
                        np.degrees(np.arctan2(beta[0], beta[1])) % 360
                    ),
                    status="DERIVED - ACQUISITION TIME UNVERIFIED",
                )
            elif k.startswith("sensor"):
                rec["status"] = "PLACEHOLDER - NOT MEASURED VIEWING GEOMETRY"
            else:
                rec["status"] = (
                    "Stored terrain, original surface/generation provenance partly unverified"
                )
            geostats.append(rec)
        ci = old.calc_cosine_i(
            rad["solar_zn"], rad["solar_az"], rad["aspect"], rad["slope"]
        )
        inc = np.full(shape, np.nan, np.float32)
        m = np.isfinite(ci) & (ci >= -1) & (ci <= 1)
        inc[m] = np.degrees(np.arccos(ci[m]))
        displays.update(
            cos_i=ci[ss],
            incidence_angle=inc[ss],
            relative_azimuth=((deg["solar_az"] - deg["sensor_az"] + 180) % 360 - 180)[
                ss
            ],
        )
        if name == "goldhill":
            print("Goldhill boundary and polygon diagnostics", flush=True)
            # Compare output-derived amplification with predictions, at contiguous native edges.
            actual_amp = np.isfinite(values["brdf"][..., 4]) & (
                values["brdf"][..., 4] != raw[..., 4]
            )
            declared_amp = red_factor != 1
            branch = (red_den > 0) & (red_num > 0) & vis
            valid_edge = (
                observed & (raw[..., 4] != 0) & np.isfinite(values["brdf"][..., 4])
            )
            edgecmp = boundary_comparison(actual_amp, branch, valid_edge)
            assert edgecmp["xor_edges"] == 0
            signcmp = boundary_comparison(actual_amp, red_den > 0, valid_edge)
            crossings = boundary_edges(branch, valid_edge)
            dy = np.array([], float)
            if crossings[0].any():
                d0 = red_den[:, :-1][crossings[0]]
                d1 = red_den[:, 1:][crossings[0]]
                t = -d0 / (d1 - d0)
                dy = np.abs(t - 0.5) * abs(tr.a)
            edgecmp["linear_zero_vs_branch_midpoint_offset_m"] = dist(dy)
            edgecmp["denominator_only_comparison"] = signcmp
            write("boundary_correspondence.json", edgecmp)
            df, geometry = polygon_metrics(
                src
                if False
                else rasterio.open(PRIOR / "goldhill_recovered_source_dn.tif"),
                pol,
                values,
                common,
                red_factor,
                red_den,
            )
            df.to_csv(HERE / "polygon_stage_spectra.csv", index=False)
            geometry.to_csv(HERE / "polygon_geometry.csv", index=False)
            candidates = geometry[
                (geometry.pixels >= 20)
                & (geometry.red_amplified_fraction > 0.05)
                & (geometry.red_amplified_fraction < 0.95)
            ]
            if len(candidates):
                candidates = candidates.assign(
                    distance_to_prior=(candidates.row_center - 921) ** 2
                    + (candidates.col_center - 980) ** 2
                )
                exemplar = candidates.sort_values(
                    ["raw_within_angle", "distance_to_prior"]
                ).iloc[0]
                cy, cx = int(exemplar.row_center), int(exemplar.col_center)
                exemplar_status = "Crosses actual amplification boundary; chosen for relatively homogeneous raw spectral angles before comparing stage medians"
            else:
                geometry["distance_to_prior"] = (geometry.row_center - 921) ** 2 + (
                    geometry.col_center - 980
                ) ** 2
                exemplar = geometry.sort_values("distance_to_prior").iloc[0]
                cy, cx = int(exemplar.row_center), int(exemplar.col_center)
                exemplar_status = "Nearest eligible researcher polygon to prior boundary marker; no qualifying crossing polygon"
            # Keep the known native crossing as a separate mechanistic transect.
            roi = (
                max(0, cy - 200),
                min(shape[0], cy + 201),
                max(0, cx - 250),
                min(shape[1], cx + 251),
            )
            ry = slice(roi[0], roi[1])
            rx = slice(roi[2], roi[3])
            rt = (ry, rx)
            boundsroi = [
                tr.c + roi[2] * tr.a,
                tr.c + roi[3] * tr.a,
                tr.f + roi[1] * tr.e,
                tr.f + roi[0] * tr.e,
            ]
            chosen = [str(exemplar.GlobalID)]
            for selection in [
                geometry[geometry.red_amplified_fraction.eq(0)],
                geometry[geometry.red_amplified_fraction.eq(1)],
                geometry,
            ]:
                g = selection[~selection.GlobalID.isin(chosen)].copy()
                if len(g):
                    g["distance"] = (g.row_center - cy) ** 2 + (g.col_center - cx) ** 2
                    chosen.append(str(g.sort_values("distance").iloc[0].GlobalID))
            # Exact pixel indices selected on actual shared-valid source support; no spectral smoothing.
            cy0, cx0 = 921, 980
            line_valid = common[cy0] & vis[cy0] & np.isfinite(red_den[cy0])
            crossing_cols = np.where(
                (red_den[cy0, :-1] <= 0)
                & (red_den[cy0, 1:] > 0)
                & line_valid[:-1]
                & line_valid[1:]
            )[0]
            if not len(crossing_cols):
                crossing_cols = np.where(
                    (red_factor[cy0, :-1] > 1) != (red_factor[cy0, 1:] > 1)
                )[0]
            cross = int(crossing_cols[np.argmin(abs(crossing_cols - cx0))])
            choices = [
                ("nonpositive_outside", cy0, cross),
                ("near_zero_inside", cy0, cross + 1),
                ("inside_artifact", cy0, min(cross + 20, shape[1] - 1)),
            ]
            unaffected = np.argwhere(common & vis & (red_den <= 0))
            idx = np.argmin(
                (unaffected[:, 0] - cy0) ** 2 + (unaffected[:, 1] - (cross - 150)) ** 2
            )
            rr, cc = unaffected[idx]
            choices.append(("unaffected_reference", int(rr), int(cc)))
            trcols = np.arange(max(0, cross - 140), min(shape[1], cross + 141))
            for label, r, c0 in choices:
                e, n = tr * (c0 + 0.5, r + 0.5)
                for b in range(10):
                    iso, vol, geo = [
                        np.float32(model[k][0][b]) for k in ["iso", "vol", "geo"]
                    ]
                    den = iso + vol * kv[r, c0] + geo * kg[r, c0]
                    num = np.float32(num_scalar[b])
                    factor, positive, bad = apply_factor(
                        np.array([[den]], np.float32),
                        np.array([[num]], np.float32),
                        np.array([[vis[r, c0]]]),
                    )
                    rec = dict(
                        label=label,
                        row=r,
                        column=c0,
                        easting=e,
                        northing=n,
                        wavelength_nm=int(WAVE[b]),
                        raw=float(raw[r, c0, b]),
                        topo=float(values["topo"][r, c0, b]),
                        brdf=float(values["brdf"][r, c0, b]),
                        combined=float(values["combined"][r, c0, b]),
                        pred_observed=float(den),
                        pred_reference=float(num),
                        factor=float(factor[0, 0]),
                        positive_branch=bool(positive[0, 0]),
                        visited_bin=bool(vis[r, c0]),
                        fallback=bool(not positive[0, 0] or bad[0, 0]),
                        iso_term=float(iso),
                        vol_term=float(vol * kv[r, c0]),
                        geo_term=float(geo * kg[r, c0]),
                    )
                    pixelrows.append(rec)
            for r in [max(0, cy0 - 40), cy0, min(shape[0] - 1, cy0 + 40)]:
                for c0 in trcols:
                    rec = dict(
                        row=int(r),
                        column=int(c0),
                        easting=float(tr * (int(c0) + 0.5, int(r) + 0.5))[0]
                        if False
                        else float(tr.c + (c0 + 0.5) * tr.a),
                        northing=float(tr.f + (r + 0.5) * tr.e),
                        den=float(red_den[r, c0]),
                        num=float(red_num[r, c0]),
                        factor=float(red_factor[r, c0]),
                        raw=float(raw[r, c0, 4]),
                        brdf=float(values["brdf"][r, c0, 4]),
                        combined=float(values["combined"][r, c0, 4]),
                        visited=bool(vis[r, c0]),
                        observed=bool(observed[r, c0]),
                        common=bool(common[r, c0]),
                    )
                    transects.append(rec)
            zoom = {s: np.asarray(v[rt]) for s, v in values.items()}
            zoom.update({k: v[rt] for k, v in deg.items()})
            zoom.update(
                kv_old=kv[rt],
                kg_old=kg[rt],
                kv_current=newkv[rt],
                kg_current=newkg[rt],
                cos_i=ci[rt],
                incidence_angle=inc[rt],
                relative_azimuth=(
                    (deg["solar_az"] - deg["sensor_az"] + 180) % 360 - 180
                )[rt],
                observed=observed[rt],
                common=common[rt],
                finite=finite[rt],
                red_den=red_den[rt],
                red_num=red_num[rt],
                red_factor=red_factor[rt],
                visited=vis[rt],
            )
            # Per-band predictions on exactly the same zoom grid.
            zoom["factors"] = np.stack(
                [
                    apply_factor(
                        np.float32(model["iso"][0][b])
                        + np.float32(model["vol"][0][b]) * kv[rt]
                        + np.float32(model["geo"][0][b]) * kg[rt],
                        np.full(kv[rt].shape, np.float32(num_scalar[b])),
                        vis[rt],
                    )[0]
                    for b in range(10)
                ],
                axis=-1,
            )
            zoom["predictions"] = np.stack(
                [
                    np.float32(model["iso"][0][b])
                    + np.float32(model["vol"][0][b]) * kv[rt]
                    + np.float32(model["geo"][0][b]) * kg[rt]
                    for b in range(10)
                ],
                axis=-1,
            )
            np.savez_compressed(HERE / "goldhill_zoom.npz", **zoom)
            # Separate topographic denominator: use the actual historical full-scene fit for 531 nm.
            vmask = finite & np.isfinite(ci)
            A = np.stack([ci[vmask].astype(float), np.ones(int(vmask.sum()))], axis=1)
            beta = np.linalg.lstsq(A, raw[..., 2][vmask].astype(float), rcond=None)[0]
            C = float(beta[1] / beta[0])
            td = ci + C
            tn = np.cos(rad["solar_zn"]) * np.cos(rad["slope"]) + C
            tf = old._scs_c_ratio(tn, td, min_denom=old.MIN_SCS_C_DENOM)
            expected = raw[..., 2] * tf
            actual = values["topo"][..., 2]
            gm = vmask & np.isfinite(actual)
            err = expected[gm] - actual[gm]
            topcheck = dict(
                wavelength_nm=531,
                C=C,
                coefficient_a=float(beta[0]),
                coefficient_b=float(beta[1]),
                factor=dist(tf[gm]),
                denominator=dist(td[gm]),
                bitwise_mismatches=int((err != 0).sum()),
                maximum_absolute_S_error=float(np.max(abs(err))),
                minimum_guard=float(old.MIN_SCS_C_DENOM),
                scope="Historical SCS+C source-normalized full-scene fit, not the BRDF predicted response",
            )
            write("topographic_mechanism.json", topcheck)
            displays.update(topo_den=td[ss], topo_factor=tf[ss], topo_C=np.array(C))
            zoomtop = dict(topo_den=td[rt], topo_factor=tf[rt], topo_C=np.array(C))
            np.savez_compressed(HERE / "goldhill_topo_zoom.npz", **zoomtop)
            selection = dict(
                roi_native_indices=list(roi),
                roi_extent_NAD83_UTM13N=boundsroi,
                roi_resolution_m=0.1,
                exemplar_GlobalID=str(exemplar.GlobalID),
                exemplar_cover_category=str(exemplar.cover_category),
                exemplar_species=str(exemplar.species),
                exemplar_status=exemplar_status,
                selected_polygons=chosen,
                pixels=[dict(label=l, row=r, column=c0) for l, r, c0 in choices],
                main_transect_row=cy0,
                main_transition_left_column=cross,
                main_transect_columns=[int(trcols[0]), int(trcols[-1])],
                array_order="row,column,band",
                source_alpha_policy="Display and polygon membership require alpha>0; H5 arrays unchanged; exact replay diagnostics also retain original full finite-H5 support",
            )
            write("selection.json", selection)
            pd.DataFrame(pixelrows).to_csv(HERE / "pixel_trajectories.csv", index=False)
            pd.DataFrame(transects).to_csv(HERE / "red_transects.csv", index=False)
            # Native wavelength-position heatmaps on contiguous source columns.
            strip = {s: np.asarray(v[cy0, trcols, :]) for s, v in values.items()}
            strip.update(
                factors=np.stack(
                    [
                        apply_factor(
                            np.float32(model["iso"][0][b])
                            + np.float32(model["vol"][0][b]) * kv[cy0, trcols]
                            + np.float32(model["geo"][0][b]) * kg[cy0, trcols],
                            np.full(len(trcols), num_scalar[b], np.float32),
                            vis[cy0, trcols],
                        )[0]
                        for b in range(10)
                    ],
                    axis=-1,
                ),
                columns=trcols,
            )
            np.savez_compressed(HERE / "goldhill_transect_bands.npz", **strip)
            for stage, g in df.groupby("stage"):
                for first, second in combinations(sorted(g.cover_category.unique()), 2):
                    aa = g[g.cover_category.eq(first)][
                        [f"b{i}" for i in range(1, 11)]
                    ].to_numpy()
                    bb = g[g.cover_category.eq(second)][
                        [f"b{i}" for i in range(1, 11)]
                    ].to_numpy()
                    if min(len(aa), len(bb)) < 5:
                        continue
                    sd = np.sqrt((aa.var(0, ddof=1) + bb.var(0, ddof=1)) / 2)
                    effect = np.divide(
                        abs(aa.mean(0) - bb.mean(0)),
                        sd,
                        out=np.full(10, np.nan),
                        where=sd > 0,
                    )
                    a1, a3 = np.percentile(aa, [25, 75], axis=0)
                    b1, b3 = np.percentile(bb, [25, 75], axis=0)
                    union = np.maximum(a3, b3) - np.minimum(a1, b1)
                    over = np.divide(
                        np.maximum(0, np.minimum(a3, b3) - np.maximum(a1, b1)),
                        union,
                        out=np.full(10, np.nan),
                        where=union > 0,
                    )
                    classrows.append(
                        dict(
                            stage=stage,
                            first=first,
                            second=second,
                            n_first=len(aa),
                            n_second=len(bb),
                            mean_abs_standardized_difference=float(np.nanmean(effect)),
                            median_spectrum_angle_deg=float(
                                helpers.angle_degrees(
                                    np.median(aa, 0), np.median(bb, 0)
                                )
                            ),
                            mean_band_IQR_overlap=float(np.nanmean(over)),
                            interpretation="Descriptive paired-polygon numerical distortion, not classification accuracy or calibration benefit",
                        )
                    )
            # Reuse, rather than recreate, the prior all-production-value validation record.
            prior_replay = json.loads(
                (
                    ROOT
                    / "provenance/drone-radiometric-recovery/2026-11-02/replay_diagnostics.json"
                ).read_text()
            )["historical_exact_replay"]
            # Current replay of the exact old function on both cached input stages.
            for stage, outstage in [("raw", "brdf"), ("topo", "combined")]:
                replay = old.apply_brdf_correct(
                    cube,
                    values[stage],
                    0,
                    cube.lines,
                    0,
                    cube.columns,
                    brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
                )
                np.testing.assert_array_equal(replay, values[outstage])
                del replay
            write(
                "replay_validation.json",
                dict(
                    previous_production_comparison=prior_replay,
                    current_historical_function_brdf_values=int(raw.size),
                    current_historical_function_combined_values=int(raw.size),
                    current_cached_stage_mismatches=0,
                    current_cached_mask_mismatches=0,
                    red_factor_cache_exact=True,
                    red_denominator_cache_exact=True,
                    spatial_reference="Repaired source TIFF grid, never the reflected legacy export",
                    production_raster_currently_local=False,
                ),
            )
        np.savez_compressed(HERE / f"{name}_full_display.npz", **displays)
        flights[name] = dict(
            shape=list(raw.shape),
            transform=list(tr),
            crs=crs.to_string(),
            bounds=list(bounds),
            display_stride=stride,
            finite_H5_pixels=int(finite.sum()),
            observed_alpha_pixels=int(observed.sum()),
            common_four_stage_pixels=int(common.sum()),
            modern_angular_design=newrank,
            historical_defective_design=oldrank,
            old_kernel_volume=dist(kv[finite]),
            old_kernel_geometry=dist(kg[finite]),
            current_kernel_volume=dist(newkv[finite]),
            current_kernel_geometry=dist(newkg[finite]),
            model=model,
            solar_scene_zenith_degrees=float(np.rad2deg(scenez[0, 0])),
            same_grid="All stages use identical repaired row/column order; Goldhill saved source arrays equal restored H5 exactly",
            alpha_observation_filter="Only analytical/display selection, not a source-file mask rewrite",
        )
        del (
            cube,
            raw,
            values,
            deg,
            rad,
            kv,
            kg,
            rv,
            rg,
            red_den,
            red_num,
            red_factor,
            newkv,
            newkg,
            alpha,
            observed,
            common,
            finite,
            xx,
            yy,
            east,
            north,
            ci,
            inc,
            displays,
        )
    write("flight_comparison.json", flights)
    write("band_diagnostics.json", allbands)
    write("historical_fit_reconstruction.json", allfits)
    write("geometry_statistics.json", geostats)
    pd.DataFrame(classrows).to_csv(HERE / "between_PFT_distortion.csv", index=False)
    flat = []
    for r in allbands:
        flat.append(
            {k: v for k, v in r.items() if not isinstance(v, dict)}
            | {f"factor_{k}": r["factor_full_H5"][k] for k in ["min", "median", "max"]}
            | dict(
                den_min=r["predicted_observed"]["min"],
                den_max=r["predicted_observed"]["max"],
                ref_value=r["predicted_reference"]["median"],
            )
        )
    pd.DataFrame(flat).to_csv(HERE / "band_diagnostics.csv", index=False)
    pd.DataFrame(
        [{k: v for k, v in r.items() if not isinstance(v, list)} for r in geostats]
    ).to_csv(HERE / "geometry_statistics.csv", index=False)
    after = {p: sha(p) for p in before}
    assert before == after
    write(
        "preservation.json",
        dict(
            inputs_before=before,
            inputs_after=after,
            unchanged=True,
            production_writes=False,
            generated_production_libraries=0,
        ),
    )
    write(
        "summary.json",
        dict(
            flights=["gordon", "goldhill", "ruby"],
            historical_revision=OLD_REV,
            current_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            all_source_hashes_unchanged=True,
            goldhill_band_rows=10,
            all_band_rows=len(allbands),
            fixed_diagnostic_RGB_nm=[650, 560, 475],
            generic_production_QA_RGB_targets_nm=[660, 560, 490],
            resolved_generic_QA_RGB_nm=[668, 560, 475],
            QA_semantic_named_RGB_nm=[650, 560, 444],
            reference_geometry=dict(solar_zenith=45, view_zenith=0, relative_azimuth=0),
            units="Stored normalized S and explicitly inverse-encoded DN equivalents, never physical reflectance",
            full_scene_prediction_pixel_resolution_m=0.1,
        ),
    )
    print("Anatomy diagnostics complete; immutable source hashes match", flush=True)


if __name__ == "__main__":
    main()
