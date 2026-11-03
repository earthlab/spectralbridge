"""Read-only provenance, independent solar and terrain/correction diagnostics.

No correction algorithm or scientific source file is modified. Solar libraries
are installed separately under --work/python-libs; pvlib SPA is independent of
SpectralBridge's NOAA approximation. Historical ephem behavior is replay only.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import h5py
import rasterio
from rasterio.warp import reproject, Resampling, transform as project
from scipy.ndimage import convolve, binary_erosion

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.neon_cube import NeonCube  # noqa: E402
from spectralbridge.pipelines.drone import _compute_solar_geometry_arrays  # noqa: E402
from spectralbridge.corrections import calc_cosine_i  # noqa: E402


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def summary(x):
    a = np.asarray(x)
    a = a[np.isfinite(a)]
    return (
        dict(
            n=int(a.size), q0_1_50_99_100=np.percentile(a, [0, 1, 50, 99, 100]).tolist()
        )
        if a.size
        else dict(n=0)
    )


def circular_difference(a, b):
    return (np.asarray(a) - np.asarray(b) + 180) % 360 - 180


def horn_terrain(elevation, xres, yres, nodata=None):
    """Independent Horn 3x3 degree gradients. No claim of exact terra replay."""
    z = np.asarray(elevation, float)
    valid = np.isfinite(z)
    if nodata is not None and np.isfinite(nodata):
        valid &= z != nodata
    z = np.where(valid, z, 0.0)
    # ndimage convolution reverses kernels. East/north derivatives defined explicitly.
    dx = convolve(
        z,
        np.array([[1, 0, -1], [2, 0, -2], [1, 0, -1]], float) / (8 * xres),
        mode="nearest",
    )
    dn = convolve(
        z,
        np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], float) / (8 * yres),
        mode="nearest",
    )
    slope = np.degrees(np.arctan(np.hypot(dx, dn)))
    aspect = np.degrees(np.arctan2(-dx, -dn)) % 360
    support = binary_erosion(valid, structure=np.ones((3, 3)), border_value=0)
    slope[~support] = np.nan
    aspect[~support] = np.nan
    return slope.astype("float32"), aspect.astype("float32")


def load_old():
    p = (
        ROOT
        / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
    )
    spec = importlib.util.spec_from_file_location("metadata_historical_math", p)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)
    return old


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--work",
        type=Path,
        default=Path("/private/tmp/photogrammetry-metadata-20261102"),
    )
    args = parser.parse_args()
    work = args.work
    sys.path.insert(0, str(work / "python-libs"))
    import ephem
    import pvlib

    inputs = Path(
        "/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1"
    )
    prior = ROOT / "provenance/drone-three-flight-reprocess/2026-10-29"
    strategy = json.loads(
        (ROOT / "provenance/drone-brdf-strategy/2026-11-02/manifest.json").read_text()
    )
    arrays = Path(strategy["work"])
    hashes = {}
    records = {}
    solar_rows = []
    old = load_old()
    notes = {"gordon": "14:47", "goldhill": "13:41", "ruby": "12:42"}
    for name, package in [
        ("gordon", "AOP-GORDON-08-14-23-ExportPackage"),
        ("goldhill", "AOP-GOLDHILL-08-14-23-ExportPackage"),
        ("ruby", "AOP-Ruby-08-14-23-ExportPackage"),
    ]:
        print("Inspecting", name, flush=True)
        source = inputs / "staged_sources" / ("2023_" + package)
        old_h5 = next(source.glob("*.h5"))
        audit = json.loads((prior / package / "pipeline_result.json").read_text())[
            "qa_summary"
        ]["files"][0]
        current_h5 = Path(audit["working_h5_path"])
        cube = NeonCube(current_h5)
        recipe = inputs / "prepared_sources/2023" / package / "source_recipe.json"
        for p in [
            old_h5,
            current_h5,
            source / "aligned_orthomosaic.tif",
            source / "aligned_slope.tif",
            source / "aligned_aspect.tif",
            recipe,
        ]:
            hashes[str(p)] = sha(p)
        r = dict(
            source_h5=str(old_h5),
            working_h5=str(current_h5),
            recipe=json.loads(recipe.read_text()),
            execution={
                k: audit[k]
                for k in [
                    "input_source_type",
                    "input_source_path",
                    "manifest_flight_datetime",
                    "solar_geometry_source",
                    "acquisition_datetime_used",
                ]
            },
            angles={},
            terrain={},
        )
        with (
            rasterio.open(source / "aligned_orthomosaic.tif") as tif,
            h5py.File(old_h5) as oh,
            h5py.File(current_h5) as wh,
        ):
            om = next(iter(oh.values()))["Reflectance/Metadata"]
            wm = next(iter(wh.values()))["Reflectance/Metadata"]
            r["working_metadata_attributes"] = {
                k: v.item() if hasattr(v, "item") else v for k, v in wm.attrs.items()
            }
            h, w = tif.shape
            ys = np.array([0, h // 4, h // 2, 3 * h // 4, h - 1])
            xs = np.array([0, w // 4, w // 2, 3 * w // 4, w - 1])
            yy, xx = np.meshgrid(ys, xs, indexing="ij")
            ys = yy.ravel()
            xs = xx.ravel()
            east = tif.transform.c + (xs + 0.5) * tif.transform.a
            north = tif.transform.f + (ys + 0.5) * tif.transform.e
            lon, lat = project(tif.crs, "EPSG:4326", east.tolist(), north.tolist())
            lon = np.array(lon)
            lat = np.array(lat)
            mid = 12
            current_sz = np.array(
                [wm["Solar_Zenith_Angle"][y, x] for y, x in zip(ys, xs)]
            )
            current_sa = np.array(
                [wm["Solar_Azimuth_Angle"][y, x] for y, x in zip(ys, xs)]
            )
            prior_sz = np.array(
                [om["Logs/Solar_Zenith_Angle"][y, x] for y, x in zip(ys, xs)]
            )
            prior_sa = np.array(
                [om["Logs/Solar_Azimuth_Angle"][y, x] for y, x in zip(ys, xs)]
            )
            t = pd.Timestamp(audit["manifest_flight_datetime"])
            calc_sz, calc_sa = _compute_solar_geometry_arrays(
                acquisition_datetime=t.to_pydatetime(), longitude=lon, latitude=lat
            )
            assert np.array_equal(calc_sz, current_sz) and np.array_equal(
                calc_sa, current_sa
            )
            r["solar_replay"] = dict(
                points=len(ys),
                working_exact_zenith_mismatches=int((calc_sz != current_sz).sum()),
                working_exact_azimuth_mismatches=int((calc_sa != current_sa).sum()),
                center_lat=float(lat[mid]),
                center_lon=float(lon[mid]),
                altitude_assumption="Current NOAA implementation uses lat/lon/time, no DEM elevation or refraction. Independent SPA uses pressure=0, altitude=0 for geometric angles.",
                old_grid_zenith=summary(prior_sz),
                working_grid_zenith=summary(current_sz),
            )
            old_replay_sz = []
            old_replay_sa = []
            for la, lo in zip(lat, lon):
                observer = ephem.Observer()
                observer.date = ephem.Date(
                    t.tz_convert("UTC").tz_localize(None).to_pydatetime()
                )
                observer.lat = float(la)
                observer.lon = float(lo)
                sun = ephem.Sun(observer)
                old_replay_sz.append(np.float32(90 - float(sun.alt)))
                old_replay_sa.append(np.float32(np.degrees(sun.az)))
            old_replay_sz = np.array(old_replay_sz)
            old_replay_sa = np.array(old_replay_sa)
            r["historical_solar_bug_fingerprint"] = dict(
                points=len(ys),
                max_abs_zenith_error_degrees=float(
                    np.max(abs(old_replay_sz - prior_sz))
                ),
                max_abs_azimuth_error_degrees=float(
                    np.max(abs(circular_difference(old_replay_sa, prior_sa)))
                ),
                exact_zenith_matches=int((old_replay_sz == prior_sz).sum()),
                exact_azimuth_matches=int((old_replay_sa == prior_sa).sum()),
                mechanism="Archived ephem code assigns degree-valued numeric latitude/longitude to radian-valued Observer properties, then computes 90 - sun.alt (radians) as if degrees. Both errors replayed, never used as corrected geometry.",
                provenance_limit="Strong numerical/code fingerprint, not a per-file signed execution record or identification of a human executor.",
            )
            for field in ["Zenith", "Azimuth"]:
                olddata = om["to-sensor_" + field + "_Angle"][()]
                newdata = wm["to-sensor_" + field + "_Angle"][()]
                assert np.all(olddata == 0) and np.all(newdata == 0)
                r["angles"][field] = dict(
                    source_shape=list(olddata.shape),
                    working_shape=list(newdata.shape),
                    source_all_zero=True,
                    working_all_zero=True,
                    lineage="prepare_reference reads/validates source constant then supplies explicit tiff_sensor_*_deg to convert_drone_tiff_to_h5; reader broadcasts scalar. Not camera measurement.",
                )
            candidates = [
                ("manifest UTC (executed)", t),
                (
                    "notes Aug14 Denver",
                    pd.Timestamp(
                        "2023-08-14 " + notes[name], tz="America/Denver"
                    ).tz_convert("UTC"),
                ),
                (
                    "notes Aug14 UTC",
                    pd.Timestamp("2023-08-14 " + notes[name], tz="UTC"),
                ),
            ]
            for card in [1, 2]:
                csv = Path("/private/tmp") / (
                    f"SD{card}_image_metadata.csv"
                    if name == "goldhill"
                    else f"{name}-sd{card}-metadata.csv"
                )
                frame = pd.read_csv(csv)
                dates = pd.to_datetime(
                    frame.TIFFTAG_DATETIME, format="%Y:%m:%d %H:%M:%S"
                )
                dt = dates.sort_values().iloc[len(dates) // 2]
                for zone in ["UTC", "America/Denver"]:
                    candidates.append(
                        (
                            f"SD{card} median as " + zone,
                            dt.tz_localize(zone).tz_convert("UTC"),
                        )
                    )
                if card == 1:
                    r["camera_time_range"] = dict(
                        start=str(dates.min()),
                        stop=str(dates.max()),
                        span_minutes=float(
                            (dates.max() - dates.min()).total_seconds() / 60
                        ),
                        timezone_unknown=True,
                        warning="Band-file timestamp span, not independently verified flight exposure timing.",
                    )
            candidates.append(
                (
                    "notes Aug15 Denver sensitivity",
                    pd.Timestamp(
                        "2023-08-15 " + notes[name], tz="America/Denver"
                    ).tz_convert("UTC"),
                )
            )
            for label, stamp in candidates:
                spa = pvlib.solarposition.get_solarposition(
                    pd.DatetimeIndex([stamp]),
                    lat[mid],
                    lon[mid],
                    pressure=0,
                    altitude=0,
                )
                zen = float(spa.zenith.iloc[0])
                azi = float(spa.azimuth.iloc[0])
                solar_rows.append(
                    dict(
                        flight=name,
                        candidate=label,
                        utc=stamp.isoformat(),
                        latitude=float(lat[mid]),
                        longitude=float(lon[mid]),
                        stored_zenith=float(current_sz[mid]),
                        stored_azimuth=float(current_sa[mid]),
                        spa_zenith=zen,
                        spa_azimuth=azi,
                        zenith_difference=float(current_sz[mid]) - zen,
                        azimuth_difference=float(
                            circular_difference(current_sa[mid], azi)
                        ),
                        sun_above_horizon=zen < 90,
                    )
                )
            for field in ["slope", "aspect"]:
                with rasterio.open(source / ("aligned_" + field + ".tif")) as a:
                    raw = a.read(1)
                    actual = cube.get_ancillary(field, radians=False)
                    equal = np.array_equal(raw, actual, equal_nan=True)
                    r["terrain"][field] = dict(
                        path=str(a.name),
                        grid_matches=(a.crs == tif.crs and a.shape == tif.shape),
                        maximum_affine_corner_difference=float(
                            max(
                                np.max(
                                    abs(
                                        np.array(a.transform * corner)
                                        - np.array(tif.transform * corner)
                                    )
                                )
                                for corner in [(0, 0), (w, h)]
                            )
                        ),
                        tiff_h5_values_exact=equal,
                        units=a.units[0],
                        tags=a.tags(),
                        range=summary(raw),
                        h5_dataset_attributes={
                            k: str(v)
                            for k, v in wm[
                                "Ancillary_Imagery/" + field.title()
                            ].attrs.items()
                        },
                    )
                    assert equal
            # Independent candidate surface derivatives on native grids, then bilinear mapping.
            for surface in ["dem", "dtm"]:
                p = work / (name + "_" + surface + ".tif")
                hashes[str(p)] = sha(p)
                with rasterio.open(p) as dem:
                    z = dem.read(1)
                    sl, asp = horn_terrain(z, *dem.res, dem.nodata)
                    slwarped = np.full(tif.shape, np.nan, np.float32)
                    awarped = np.full(tif.shape, np.nan, np.float32)
                    for val, dst in [(sl, slwarped), (asp, awarped)]:
                        reproject(
                            val,
                            dst,
                            src_transform=dem.transform,
                            src_crs=dem.crs,
                            src_nodata=np.nan,
                            dst_transform=tif.transform,
                            dst_crs=tif.crs,
                            dst_nodata=np.nan,
                            resampling=Resampling.bilinear,
                        )
                    slope = cube.get_ancillary("slope", False)
                    aspect = cube.get_ancillary("aspect", False)
                    valid = (
                        np.isfinite(slwarped)
                        & np.isfinite(slope)
                        & (slope >= 0)
                        & (slope <= 90)
                    )
                    r["terrain"][surface + "_native_derivative_comparison"] = dict(
                        path=str(p),
                        crs=dem.crs.to_string(),
                        shape=list(dem.shape),
                        resolution=list(dem.res),
                        tags=dem.tags(),
                        slope_absolute_error=summary(
                            abs(slwarped[valid] - slope[valid])
                        ),
                        aspect_circular_absolute_error=summary(
                            abs(circular_difference(awarped[valid], aspect[valid]))
                        ),
                        note="Independent Horn/native-before-bilinear candidate, not proof of executed terra settings or DEM/DTM classification. Scalar aspect interpolation can cross North incorrectly.",
                    )
                    if surface == "dem":
                        np.savez_compressed(
                            HERE / (name + "_terrain_display.npz"),
                            native_z=z,
                            native_slope=sl,
                            stored_slope=slope[::10, ::10],
                            stored_aspect=aspect[::10, ::10],
                            candidate_slope=slwarped[::10, ::10],
                            candidate_aspect=awarped[::10, ::10],
                        )
            r["tiff_metadata"] = dict(
                crs=tif.crs.to_string(),
                transform=list(tif.transform),
                shape=list(tif.shape),
                tags=tif.tags(),
                scales=list(tif.scales),
                offsets=list(tif.offsets),
                units=list(tif.units),
                descriptions=list(tif.descriptions),
            )
        print("Topographic denominator audit", name, flush=True)
        data = np.load(arrays / (name + "_raw.npy"), mmap_mode="r")
        topo = np.load(arrays / (name + "_topo_diagnostic.npy"), mmap_mode="r")
        slope = cube.get_ancillary("slope")
        aspect = cube.get_ancillary("aspect")
        sz = cube.get_ancillary("solar_zn")
        sa = cube.get_ancillary("solar_az")
        cosi = calc_cosine_i(sz, sa, aspect, slope)
        valid = cube.mask_no_data & np.isfinite(data).all(2) & np.isfinite(cosi)
        xv = cosi[valid].astype(float)
        A = np.column_stack([xv, np.ones(len(xv))])
        svals = np.linalg.svd(A, compute_uv=False)
        cosSolar = np.cos(sz)[valid]
        cosBeta = np.cos(slope)[valid]
        cosvalid = cosi[valid]
        r["topography_fit_design"] = dict(
            rank=int(np.linalg.matrix_rank(A)),
            condition_number=float(svals[0] / svals[-1]),
            singular_values=svals.tolist(),
            units="Recovered numerical DN; no physical fit approval",
        )
        topobands = []
        for b, wave in enumerate(cube.wavelengths):
            y = data[:, :, b][valid].astype(float)
            coeff = np.linalg.lstsq(A, y, rcond=None)[0]
            a, beta = coeff
            C = float(beta / a) if not np.isclose(a, 0) else 0.0
            num = cosSolar * cosBeta + C
            den = cosvalid + C
            factor = old._scs_c_ratio(num, den, min_denom=old.MIN_SCS_C_DENOM)
            expected = data[:, :, b][valid] * factor
            actual = topo[:, :, b][valid]
            assert np.array_equal(expected, actual, equal_nan=True)
            worst = int(np.argmax(factor))
            rss = float(np.sum((y - A @ coeff) ** 2))
            se2 = rss / (len(y) - 2)
            cov = se2 * np.linalg.inv(A.T @ A)
            grad = (
                np.array([-beta / (a * a), 1 / a])
                if a != 0
                else np.array([np.nan, np.nan])
            )
            se_C = float(np.sqrt(max(0, grad @ cov @ grad)))
            topobands.append(
                dict(
                    band=b + 1,
                    wavelength_nm=float(wave),
                    slope_coefficient=float(a),
                    intercept=float(beta),
                    C=C,
                    C_standard_error=se_C,
                    r_squared=float(1 - rss / np.sum((y - y.mean()) ** 2)),
                    factor=summary(factor),
                    denominator=summary(den),
                    guard_neutral_den_le_0_001=int(
                        np.count_nonzero(den <= old.MIN_SCS_C_DENOM)
                    ),
                    max_gain_location=dict(
                        factor=float(factor[worst]),
                        cosine_incidence=float(cosvalid[worst]),
                        C=C,
                        denominator=float(den[worst]),
                        numerator=float(num[worst]),
                    ),
                    exact_output_mismatches=int(np.count_nonzero(expected != actual)),
                )
            )
            print(
                name, "band", b + 1, "max gain", float(factor.max()), "C", C, flush=True
            )
        r["topography_bands"] = topobands
        records[name] = r
        del cube, data, topo, A
    after = {p: sha(p) for p in hashes}
    assert hashes == after
    (HERE / "validation.json").write_text(
        json.dumps(records, indent=2, allow_nan=False) + "\n"
    )
    pd.DataFrame(solar_rows).to_csv(
        HERE / "solar_candidate_comparison.csv", index=False
    )
    (HERE / "preservation.json").write_text(
        json.dumps(
            dict(
                inputs_before=hashes,
                inputs_after=after,
                unchanged=True,
                libraries=dict(pvlib=pvlib.__version__, ephem=ephem.__version__),
                scope="Read-only source checks and isolated diagnostics, no corrected raster or calibration produced",
            ),
            indent=2,
        )
        + "\n"
    )
    print("Validation complete", flush=True)


if __name__ == "__main__":
    main()
