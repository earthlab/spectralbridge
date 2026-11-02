"""Isolated three-flight identifiability and numerical-DN correction study.

Run from repo root using .venv/bin/python. No production API contracts relaxed.
Actual unknown units/illumination block approved corrections. Topography replay
is a separate explicitly numerical sensitivity using the unchanged archived
SCS+C equations from P160, never an approved physical product.
"""

import argparse
import hashlib
import importlib.util
import json
from itertools import combinations
from pathlib import Path
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, geometry_window
from shapely import contains_xy, box
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge import corrections as corr  # noqa: E402
from spectralbridge.neon_cube import NeonCube  # noqa: E402
from spectralbridge.library_analysis import spectral_separability  # noqa: E402
from spectralbridge.pipelines.drone import summarize_drone_h5_solar_geometry  # noqa: E402

WAVE = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])


def index_band_pairs(wavelengths):
    """Map numerical index definitions by wavelength, including reordered inputs."""
    wave = np.asarray(wavelengths, float)

    def band(target):
        return int(np.argmin(abs(wave - target)))

    return [
        (name, band(a), band(b))
        for name, a, b in [("NDVI", 862, 668), ("NDRE", 862, 705), ("GNDVI", 862, 560)]
    ]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def distribution(x):
    a = np.asarray(x)
    a = a[np.isfinite(a)]
    return (
        dict(
            n=int(a.size),
            quantiles_0_1_25_50_75_99_100=np.percentile(
                a, [0, 1, 25, 50, 75, 99, 100]
            ).tolist(),
        )
        if a.size
        else dict(n=0)
    )


def matrix_diagnostics(matrix):
    a = np.asarray(matrix, np.float64)
    s = np.linalg.svd(a, compute_uv=False)
    rank = int(np.linalg.matrix_rank(a))
    condition = float(s[0] / s[-1]) if s[-1] > 0 else None
    limit = float(1 / np.sqrt(np.finfo(np.float32).eps))
    return dict(
        n=int(len(a)),
        rank=rank,
        singular_values=s.tolist(),
        condition_number=condition,
        condition_limit=limit,
        stable_rank=float(np.sum((s / s[0]) ** 2)),
        supported=bool(rank == 3 and condition is not None and condition <= limit),
        independent_angular_observations=None,
        independent_angular_observations_status="Not recoverable without source-image identity and overlap provenance. Stable rank is an effective dimension, not a count of independent photographs.",
    )


def angle_degrees(a, b):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    norm = np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1)
    cosine = np.divide(
        np.sum(a * b, axis=-1), norm, out=np.full(norm.shape, np.nan), where=norm > 0
    )
    return np.degrees(np.arccos(np.clip(cosine, -1, 1)))


def ratio_index(a, i, j):
    den = a[..., i] + a[..., j]
    return np.divide(
        a[..., i] - a[..., j],
        den,
        out=np.full(den.shape, np.nan, dtype=float),
        where=np.isfinite(den) & (abs(den) > 1e-12),
    )


def load_old():
    path = (
        ROOT
        / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
    )
    assert (
        sha(path) == "839cdf2b7264c5af53902c08994144c776f94f5a59f31dc42bd1574002998a42"
    )
    spec = importlib.util.spec_from_file_location("strategy_topo_sensitivity", path)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)
    return old


def independent_polygons(frame):
    """Keep one identity per connected overlapping-polygon component.

    Prevent duplicated/shared image support from becoming independent spectra.
    This outcome-blind rule selects lexicographically first GlobalID per component.
    """
    if frame.empty:
        return frame
    parent = list(range(len(frame)))

    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i, j in frame.sindex.query(frame.geometry, predicate="intersects").T:
        if i != j:
            parent[root(int(j))] = root(int(i))
    components = {}
    for i, g in enumerate(frame.GlobalID.astype(str)):
        key = root(i)
        if key not in components or g < frame.GlobalID.iloc[components[key]]:
            components[key] = i
    return frame.iloc[sorted(components.values())].copy()


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--work", type=Path, default=Path("/private/tmp/drone-brdf-strategy-20261102")
    )
    args = p.parse_args()
    work = args.work
    work.mkdir(parents=True, exist_ok=True)
    prior = ROOT / "provenance/drone-scale-confirmation/2026-10-30/evidence.json"
    evidence = json.loads(prior.read_text())
    flightroot = Path(
        "/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1/flight_products"
    )
    recovery = Path("/private/tmp/goldhill-radiometric-recovery-20261102")
    polygon_path = (
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
    )
    polygons = gpd.read_file(polygon_path)
    assert polygons.GlobalID.is_unique
    old = load_old()
    records = {}
    geometry_rows = []
    poly_rows = []
    stability = []
    input_hashes = {str(polygon_path): sha(polygon_path)}
    for name, tag in [("gordon", "GORDON"), ("goldhill", "GOLDHILL"), ("ruby", "Ruby")]:
        print("Angular audit", name, flush=True)
        h5 = next(flightroot.glob("*" + tag + "*/*/*__working.h5"))
        flight = h5.parent
        cube = NeonCube(h5)
        np.testing.assert_array_equal(cube.wavelengths, WAVE)
        target = Path(evidence[name]["files"]["target_10cm"]["path"])
        recovered = recovery / (name + "_recovered_source_dn.tif")
        for path in [
            h5,
            target,
            recovered,
            next(flight.glob("*__corrected.img")),
            next(flight.glob("*__corrected.hdr")),
            next(flight.glob("*__brdf_model.json")),
        ]:
            input_hashes[str(path)] = sha(path)
        valid = (
            np.isfinite(cube.data).all(2)
            & (cube.data != cube.no_data).all(2)
            & cube.mask_no_data
        )
        angles = [
            cube.get_ancillary(n, radians=False)
            for n in ["solar_zn", "solar_az", "sensor_zn", "sensor_az"]
        ]
        X, angmask, solar = corr._brdf_design(cube, corr.HYTOOLS_BRDF_KERNEL_CONFIG)
        support = valid & angmask
        diagnostics = matrix_diagnostics(X[support])
        assert not diagnostics["supported"], (
            "Actual support changed: review and execute validated fits if calibration also valid"
        )
        numeric = np.column_stack([a[support] for a in angles])
        variable = np.ptp(numeric, axis=0) > 0
        configurations = (
            np.unique(numeric[:, variable], axis=0)
            if variable.any()
            else np.zeros((1, 0))
        )
        rounded = (
            np.unique(np.round(numeric[:, variable] / 0.01).astype(np.int64), axis=0)
            if variable.any()
            else np.zeros((1, 0))
        )
        diagnostics.update(
            source_valid_pixels=int(valid.sum()),
            angle_valid_pixels=int(support.sum()),
            distinct_stored_angular_tuples=int(len(configurations)),
            distinct_tuples_at_0_01_degrees=int(len(rounded)),
            genuine_observation_configurations=None,
            percentage_pixels_meeting_complete_BRDF_requirements=0.0,
            physical_eligible_percentage=None,
            supported_bands=0,
            unsupported_bands=10,
            radiometry=cube.radiometry.record(),
            solar_metadata=summarize_drone_h5_solar_geometry(h5),
            geometry_origin="View zenith and azimuth are scalar zero datasets, broadcast by reader; source solar grids have no observation IDs or provenance attributes. Small solar variation is not recovered camera viewing diversity.",
            angles={
                k: distribution(a[support])
                for k, a in zip(
                    ["solar_zenith", "solar_azimuth", "view_zenith", "view_azimuth"],
                    angles,
                )
            },
            relative_azimuth=distribution(
                (angles[1][support] - angles[3][support] + 180) % 360 - 180
            ),
            kernels={
                "RossThick": distribution(X[:, :, 1][support]),
                "LiDenseR": distribution(X[:, :, 2][support]),
            },
            scene_solar_zenith_degrees=float(np.rad2deg(solar)),
            provenance_qualified_solar_geometry="UNVERIFIED: embedded grids plausible in degree range, but acquisition date/timezone and source-pixel observation provenance unresolved",
        )
        write(name + "_angular_diagnostics.json", diagnostics)
        # Real production entry records unknown physical units, rather than fitting DN.
        fitpath = corr.fit_and_save_brdf_model(
            cube,
            work / (name + "_blocked_model"),
            brdf_kernel_config=corr.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        fit = json.loads(fitpath.read_text())
        assert fit["validation"]["status"] == "UNSUPPORTED" and "iso" not in fit
        del numeric, configurations, rounded, X
        with rasterio.open(recovered) as src:
            data = src.read(list(range(1, 11))).transpose(1, 2, 0)
            transform = src.transform
            crs = src.crs
            bounds = src.bounds
            # Verify recovery grid against source; allow no spatial resampling here.
            with rasterio.open(target) as target_src:
                assert (
                    src.transform == target_src.transform
                    and src.crs == target_src.crs
                    and src.shape == target_src.shape
                )
            np.save(work / (name + "_raw.npy"), data)
            print("Topographic DN sensitivity", name, flush=True)
            # Mathematical replay only: no physical radiometry is asserted.
            topo = old.apply_topo_correct(cube, data, 0, cube.lines, 0, cube.columns)
            np.save(work / (name + "_topo_diagnostic.npy"), topo)
            geometry_valid = np.isfinite(topo).all(2) & (topo != cube.no_data).all(2)
            common = valid & geometry_valid
            np.save(work / (name + "_common_mask.npy"), common)
            slope = cube.get_ancillary("slope")
            aspect = cube.get_ancillary("aspect")
            sz = cube.get_ancillary("solar_zn")
            sa = cube.get_ancillary("solar_az")
            incidence = corr.calc_cosine_i(sz, sa, aspect, slope)
            np.save(work / (name + "_incidence.npy"), incidence)
            # Fit/application uses existing full-scene SCS+C local-scene solution.
            geometry_rows.append(
                dict(
                    flight=name,
                    **{
                        k: diagnostics[k]
                        for k in [
                            "source_valid_pixels",
                            "angle_valid_pixels",
                            "distinct_stored_angular_tuples",
                            "distinct_tuples_at_0_01_degrees",
                            "rank",
                            "condition_number",
                            "stable_rank",
                            "supported_bands",
                            "unsupported_bands",
                            "percentage_pixels_meeting_complete_BRDF_requirements",
                        ]
                    },
                )
            )
            covered = polygons.to_crs(crs)
            covered = (
                covered[covered.intersects(box(*bounds))].copy().reset_index(drop=True)
            )
            kept = independent_polygons(covered)
            all_retained = set(kept.GlobalID)
            for _, polygon in covered.iterrows():
                try:
                    window = geometry_window(src, [polygon.geometry], boundless=False)
                except rasterio.errors.WindowError:
                    continue
                ry, rx = window.toslices()
                inside = geometry_mask(
                    [polygon.geometry],
                    out_shape=(int(window.height), int(window.width)),
                    transform=src.window_transform(window),
                    invert=True,
                    all_touched=False,
                )
                same = inside & common[ry, rx]
                if not same.any():
                    continue
                yy, xx = np.nonzero(same)
                east = transform.c + (xx + window.col_off + 0.5) * transform.a
                north = transform.f + (yy + window.row_off + 0.5) * transform.e
                assert np.all(contains_xy(polygon.geometry, east, north)), (
                    "Independent centroid membership mismatch"
                )
                centroid = polygon.geometry.centroid
                for branch, values in [("raw", data), ("topo_diagnostic", topo)]:
                    pixels = values[ry, rx][same]
                    center = np.median(pixels, axis=0)
                    within_angle = angle_degrees(pixels, center)
                    means = pixels.mean(0, dtype=float)
                    sd = (
                        pixels.std(0, dtype=float, ddof=1)
                        if len(pixels) > 1
                        else np.full(10, np.nan)
                    )
                    cv = np.divide(
                        sd,
                        abs(means),
                        out=np.full(10, np.nan),
                        where=abs(means) > 1e-12,
                    )
                    rec = dict(
                        flight=name,
                        branch=branch,
                        GlobalID=polygon.GlobalID,
                        cover_category=str(polygon.cover_category),
                        species=str(polygon.species),
                        pixels=int(same.sum()),
                        centroid_east=centroid.x,
                        centroid_north=centroid.y,
                        spatial_block=f"{int(np.floor(centroid.x / 100))}_{int(np.floor(centroid.y / 100))}",
                        independent_component_representative=polygon.GlobalID
                        in all_retained,
                        median_pixel_angle_degrees=float(np.nanmedian(within_angle)),
                        mean_band_variance_dn2=float(np.nanmean(sd**2)),
                        median_band_cv=float(np.nanmedian(cv)),
                        incidence_median=float(np.nanmedian(incidence[ry, rx][same])),
                    )
                    rec.update({f"b{i + 1}": float(v) for i, v in enumerate(center)})
                    for index, i, j in index_band_pairs(cube.wavelengths):
                        rec[index] = float(np.nanmedian(ratio_index(pixels, i, j)))
                    poly_rows.append(rec)
            status = dict(
                raw="RECOVERED_SOURCE_DN — PHYSICAL_UNITS_UNVERIFIED",
                topographic_only="UNSUPPORTED for approved correction: physical calibration and illumination/terrain provenance unverified",
                topographic_numerical_sensitivity="EXECUTED as isolated DN diagnostic only",
                BRDF_only="UNSUPPORTED: rank deficient and physical calibration unverified",
                topographic_BRDF="UNSUPPORTED: independent topographic/BRDF gates fail",
                recommended_alternative="No additional fitted normalization executed: no invariant targets, verified calibration or overlapping independent observations support one. Preserve raw DN as baseline.",
                view_geometry="ASSIGNED_NADIR, not actual contributing camera geometry",
            )
            per_band = []
            for band in range(10):
                f = np.divide(
                    topo[:, :, band],
                    data[:, :, band],
                    out=np.full(common.shape, np.nan),
                    where=common & (data[:, :, band] != 0),
                )
                fv = f[common]
                finite = fv[np.isfinite(fv)]
                per_band.append(
                    dict(
                        band=band + 1,
                        wavelength_nm=int(WAVE[band]),
                        topo_factor=distribution(finite),
                        gains_over_10=int((finite > 10).sum()),
                        gains_over_1000=int((finite > 1000).sum()),
                        negative_raw=int(
                            np.count_nonzero(common & (data[:, :, band] < 0))
                        ),
                        negative_topo=int(
                            np.count_nonzero(common & (topo[:, :, band] < 0))
                        ),
                        zero_raw_factor_undefined=int(
                            np.count_nonzero(common & (data[:, :, band] == 0))
                        ),
                    )
                )
            for branch, values in [("raw", data), ("topo_diagnostic", topo)]:
                # Unlabelled full-scene masks and numerical index checks, not empirical validation.
                entry = dict(
                    flight=name,
                    branch=branch,
                    source_valid_pixels=int(valid.sum()),
                    common_valid_pixels=int(common.sum()),
                    pixels_lost_to_topography=int(
                        np.count_nonzero(valid & ~geometry_valid)
                    ),
                    nonfinite_output_values_on_source_valid=int(
                        np.count_nonzero(~np.isfinite(values[valid]))
                    ),
                    negative_values_on_common=int(np.count_nonzero(values[common] < 0)),
                    extreme_factors_over_10=sum(b["gains_over_10"] for b in per_band)
                    if branch != "raw"
                    else 0,
                    BRDF_invalid_predictions=None,
                    BRDF_status="UNSUPPORTED / not applied",
                )
                for index, i, j in index_band_pairs(cube.wavelengths):
                    ix = ratio_index(values, i, j)[common]
                    entry[index + "_median"] = float(np.nanmedian(ix))
                    entry[index + "_outside_minus1_plus1"] = int(
                        np.count_nonzero(np.isfinite(ix) & (abs(ix) > 1))
                    )
                stability.append(entry)
            sample = (slice(None, None, 6), slice(None, None, 6))
            np.savez_compressed(
                HERE / (name + "_display_samples.npz"),
                raw=data[sample],
                topo=topo[sample],
                valid=common[sample],
                solar_zenith=angles[0][sample],
                solar_azimuth=angles[1][sample],
                incidence=incidence[sample],
            )
            records[name] = dict(
                flight_dir=str(flight),
                target=str(target),
                recovered_dn=str(recovered),
                grid=dict(
                    transform=list(transform),
                    crs=crs.to_string(),
                    width=src.width,
                    height=src.height,
                ),
                branches=status,
                angular=diagnostics,
                topographic_diagnostic_per_band=per_band,
                polygons_intersecting=int(len(covered)),
                polygon_components_retained=int(len(kept)),
                source_geometry_masks=int(valid.sum()),
                common_mask=int(common.sum()),
                support_models=str(fitpath),
            )
        del data, topo, cube, angles, valid, common, incidence
    frame = pd.DataFrame(poly_rows)
    frame.to_csv(HERE / "polygon_spectra.csv", index=False)
    pd.DataFrame(geometry_rows).to_csv(HERE / "angular_comparison.csv", index=False)
    pd.DataFrame(stability).to_csv(HERE / "numerical_stability.csv", index=False)
    write("flight_analysis.json", records)
    print("Polygon-level comparisons", flush=True)
    evaluate_polygons(frame)
    after = {p: sha(p) for p in input_hashes}
    assert input_hashes == after
    write(
        "manifest.json",
        dict(
            work=str(work),
            inputs_before=input_hashes,
            inputs_after=after,
            all_protected_unchanged=True,
            units="Recovered source DN; no physical calibration established",
            polygons="Researcher cover_category preserved verbatim; Non-vegetated & dead is a cover comparator, not a biological PFT.",
            statistical_unit="One median ten-band spectrum per polygon, using identical raw/topographic-valid pixels; one lexicographic identity retained per connected overlap component. 100 m spatial blocks for conditional permutations; no pixel train/test split.",
            topographic_scope="Unchanged archived SCS+C numerical sensitivity only, embedded geometry unverified. No accepted corrected products.",
            BRDF_scope="Actual current shared angular design and unknown-radiometry fitter exercised; unsupported coefficients never applied.",
            alternative_scope="No better-supported fitted alternative identified; raw is recommended temporary numerical baseline.",
            permutations=1999,
            seed=20261102,
        ),
    )
    print("Analysis complete", flush=True)


def evaluate_polygons(frame):
    """Polygon-level, spatial-blocked diagnostics; no pixel pseudo-replication."""
    summary = []
    bands = []
    angles_table = []
    separability = []
    for (flight, branch), group in frame[
        frame.independent_component_representative
    ].groupby(["flight", "branch"]):
        for label, g in group.groupby("cover_category"):
            X = g[[f"b{i}" for i in range(1, 11)]].to_numpy(float)
            if len(g) < 5:
                continue
            mean = X.mean(0)
            sd = X.std(0, ddof=1)
            angles = angle_degrees(X, np.median(X, axis=0))
            cv = sd / np.maximum(abs(mean), 1e-12)
            for band in range(10):
                bands.append(
                    dict(
                        flight=flight,
                        branch=branch,
                        cover_category=label,
                        polygons=len(g),
                        wavelength_nm=int(WAVE[band]),
                        mean_dn=float(mean[band]),
                        variance_dn2=float(sd[band] ** 2),
                        coefficient_of_variation=float(cv[band]),
                    )
                )
            for identity, angle in zip(g.GlobalID, angles):
                angles_table.append(
                    dict(
                        flight=flight,
                        branch=branch,
                        cover_category=label,
                        GlobalID=identity,
                        angle_degrees=float(angle),
                    )
                )
            correlation = spearmanr(g.incidence_median, np.mean(X, axis=1))
            summary.append(
                dict(
                    flight=flight,
                    branch=branch,
                    cover_category=label,
                    polygons=len(g),
                    mean_band_variance_dn2=float(np.mean(sd**2)),
                    median_band_cv=float(np.median(cv)),
                    median_polygon_angle_degrees=float(np.median(angles)),
                    median_within_polygon_pixel_angle_degrees=float(
                        g.median_pixel_angle_degrees.median()
                    ),
                    brightness_incidence_spearman=float(correlation.statistic)
                    if np.isfinite(correlation.statistic)
                    else None,
                    NDVI_median=float(g.NDVI.median()),
                    NDRE_median=float(g.NDRE.median()),
                    GNDVI_median=float(g.GNDVI.median()),
                )
            )
        for first, second in combinations(sorted(group.cover_category.unique()), 2):
            pair = group[group.cover_category.isin([first, second])]
            mixed = pair.groupby("spatial_block").cover_category.nunique()
            retained = pair[pair.spatial_block.isin(mixed[mixed == 2].index)]
            counts = retained.cover_category.value_counts()
            item = dict(
                flight=flight,
                branch=branch,
                first=first,
                second=second,
                status="INSUFFICIENT_SUPPORT",
                first_polygons=int(counts.get(first, 0)),
                second_polygons=int(counts.get(second, 0)),
                spatial_block_size_m=100,
                permutations=1999,
            )
            if min(counts.get(first, 0), counts.get(second, 0)) >= 5:
                try:
                    result = spectral_separability(
                        retained[[f"b{i}" for i in range(1, 11)]].to_numpy(),
                        retained.cover_category.to_numpy(),
                        WAVE,
                        groups=retained.GlobalID.to_numpy(),
                        blocks=retained.spatial_block.to_numpy(),
                        permutations=1999,
                        seed=20261102,
                        integration_weights=np.ones(10),
                        max_gap=200,
                    )
                    stats = result["pairs"].iloc[0].to_dict()
                    item.update(stats)
                    item["status"] = "DESCRIPTIVE_CONDITIONAL_TEST"
                    item["mean_absolute_standardized_effect"] = (
                        float(result["wavelengths"].standardized_effect.abs().mean())
                        if "wavelengths" in result
                        else None
                    )
                except ValueError as error:
                    item["reason"] = str(error)
            separability.append(item)
    pd.DataFrame(bands).to_csv(HERE / "bandwise_class_metrics.csv", index=False)
    pd.DataFrame(angles_table).to_csv(HERE / "polygon_class_angles.csv", index=False)
    summary = pd.DataFrame(summary)
    summary.to_csv(HERE / "within_class_metrics.csv", index=False)
    tests = pd.DataFrame(separability)
    from spectralbridge.plant_pft_statistics import holm

    evaluated = tests.status.eq("DESCRIPTIVE_CONDITIONAL_TEST")
    # Correct across all tested flight/branch/class-pair comparisons, not pair-local outputs.
    if evaluated.any():
        tests.loc[evaluated, "p_max_holm_all_comparisons"] = holm(
            tests.loc[evaluated, "p_max"].to_numpy(float)
        )
    tests.to_csv(HERE / "separability.csv", index=False)


if __name__ == "__main__":
    main()
