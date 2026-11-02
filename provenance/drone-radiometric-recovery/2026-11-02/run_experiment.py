"""Real-data isolated Goldhill replay. Run from repo root with .venv/bin/python.

No source writes; large intermediates go to --work. Historical invalid model is
replayed exclusively for diagnosis, never via the validated production API.
"""

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT / "src"), str(HERE)]
from recover import recover_raster  # noqa: E402
from spectralbridge.neon_cube import NeonCube  # noqa: E402
from spectralbridge import corrections as current  # noqa: E402


def load_historical():
    path = HERE / "historical_corrections.py"
    assert (
        sha(path) == "839cdf2b7264c5af53902c08994144c776f94f5a59f31dc42bd1574002998a42"
    )
    spec = importlib.util.spec_from_file_location("goldhill_historical", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def summarize(x):
    x = np.asarray(x)
    x = x[np.isfinite(x)]
    return (
        dict(
            n=int(x.size),
            quantiles_0_1_50_95_99_100=np.percentile(
                x, [0, 1, 50, 95, 99, 100]
            ).tolist(),
        )
        if x.size
        else dict(n=0)
    )


def factors(cube, old, model):
    names = ["solar_az", "solar_zn", "sensor_az", "sensor_zn"]
    a = [cube.get_ancillary(n, radians=True) for n in names]
    a[1] = old._resolve_scene_solar_zenith(a[1])
    kv = old.calc_volume_kernel(*a, kernel_type=model["volume_kernel"])
    kg = old.calc_geom_kernel(
        *a, kernel_type=model["geom_kernel"], b_r=model["b_r"], h_b=model["h_b"]
    )
    ref = [
        np.zeros_like(a[0]),
        np.full_like(a[1], np.deg2rad(45)),
        np.zeros_like(a[2]),
        np.zeros_like(a[3]),
    ]
    rv = old.calc_volume_kernel(*ref, kernel_type=model["volume_kernel"])
    rg = old.calc_geom_kernel(
        *ref, kernel_type=model["geom_kernel"], b_r=model["b_r"], h_b=model["h_b"]
    )
    iso, vol, geo = [np.float32(model[k][0][4]) for k in ["iso", "vol", "geo"]]
    den = iso + vol * kv + geo * kg
    num = iso + vol * rv + geo * rg
    cf = np.ones_like(den)
    positive = (den > 0) & (num > 0)
    np.divide(num, den, out=cf, where=positive)
    cf = np.where(np.isfinite(cf) & (cf > 0), cf, 1)
    # Historical saved edges [-1, 1] leave exact upper-edge NDVI unvisited.
    ndvi = old.compute_ndvi(cube, cube.data)
    edges = np.asarray(model["ndvi_edges"], np.float32)
    indices = np.digitize(ndvi, edges, right=False) - 1
    indices[(ndvi < edges[0]) | (ndvi > edges[-1])] = -1
    indices[indices < 0] = 0
    cf[indices >= len(edges) - 1] = 1
    return cf, den, num


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--work",
        type=Path,
        default=Path("/private/tmp/goldhill-radiometric-recovery-20261102"),
    )
    args = p.parse_args()
    work = args.work
    work.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    scale_dir = ROOT / "provenance/drone-scale-confirmation/2026-10-30"
    evidence = json.loads((scale_dir / "evidence.json").read_text())
    mapping = json.loads((scale_dir / "verified_numeric_mapping.json").read_text())
    flight = Path(
        "/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1/flight_products/2023_AOP-GOLDHILL-08-14-23-ExportPackage/AOP_GOLDHILL_20230814"
    )
    protected = list(flight.iterdir())
    protected = [f for f in protected if f.is_file()]
    protected += [
        Path(evidence[n]["files"][k]["path"])
        for n in evidence
        for k in evidence[n]["files"]
    ]
    before = {str(f): sha(f) for f in protected}
    validation = {}
    for name in ["gordon", "goldhill", "ruby"]:
        print("Recovery", name, flush=True)
        source = Path(evidence[name]["files"]["target_10cm"]["path"])
        target = work / (name + "_recovered_source_dn.tif")
        if target.exists():
            target.unlink()  # Only own reproducible experimental output.
        if target.with_suffix(".tif.msk").exists():
            target.with_suffix(".tif.msk").unlink()
        record = recover_raster(source, target, mapping[name])
        with (
            rasterio.open(target) as dst,
            rasterio.open(evidence[name]["files"]["original"]["path"]) as orig,
        ):
            for band in range(1, 11):
                warped = np.full(dst.shape, np.nan, np.float32)
                reproject(
                    orig.read(band),
                    warped,
                    src_transform=orig.transform,
                    src_crs=orig.crs,
                    dst_transform=dst.transform,
                    dst_crs=dst.crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )
                recovered = dst.read(band)
                mask = (
                    np.isfinite(warped)
                    & np.isfinite(recovered)
                    & (dst.read_masks(band) > 0)
                )
                err = recovered[mask].astype(float) - warped[mask]
                record["bands"][band - 1][
                    "independent_original_bilinear_comparison"
                ] = dict(
                    absolute_error=summarize(abs(err)),
                    rmse=float(np.sqrt(np.mean(err**2))),
                    note="Independent GDAL warp, not exact original exporter. All border discrepancies retained, no trimming.",
                )
                print(
                    name,
                    "band",
                    band,
                    "DN median/max abs error",
                    np.median(abs(err)),
                    np.max(abs(err)),
                    flush=True,
                )
        validation[name] = record
    save("radiometric_recovery_validation.json", validation)
    old = load_historical()
    cube = NeonCube(next(flight.glob("*__working.h5")))
    model = json.loads(next(flight.glob("*__brdf_model.json")).read_text())
    cube.brdf_coefficients = copy.deepcopy(
        model
    )  # Isolated in-memory historical adapter; bypasses model-path renamer.
    with rasterio.open(evidence["goldhill"]["files"]["target_10cm"]["path"]) as src:
        spatial = dict(
            crs_wkt=src.crs.to_wkt(),
            transform=list(src.transform),
            width=src.width,
            height=src.height,
            array_axis_order="row,column,band",
            wavelengths_nm=cube.wavelengths.tolist(),
            nodata="NaN",
            source_path=str(src.name),
            resolution=list(src.res),
        )
        (work / "spatial_metadata.json").write_text(
            json.dumps(spatial, indent=2) + "\n"
        )
        raw = src.read(list(range(1, 11))).transpose(1, 2, 0)
    assert np.array_equal(raw, cube.data, equal_nan=True)
    del raw
    cf, den, num = factors(cube, old, model)
    valid = (
        np.isfinite(cube.data).all(2)
        & cube.mask_no_data
        & (cube.data[:, :, 0] != cube.no_data)
    )
    np.save(work / "valid.npy", valid)
    np.save(work / "red_factor.npy", cf)
    np.save(work / "red_denominator.npy", den)
    # Use full-scene mean and the original full-scene topographic fitting extent.
    replay = {}
    stages = ["raw", "topo", "brdf", "combined"]
    for branch in ["normalized", "recovered", "hypothetical"]:
        print("Historical fixed-model replay", branch, flush=True)
        if branch == "normalized":
            data = cube.data
        else:
            with rasterio.open(work / "goldhill_recovered_source_dn.tif") as src:
                data = src.read(list(range(1, 11))).transpose(1, 2, 0)
            if branch == "hypothetical":
                data = (data / np.float32(32768)).astype("float32")
        np.save(work / (branch + "_raw.npy"), data)
        topo = old.apply_topo_correct(cube, data, 0, cube.lines, 0, cube.columns)
        np.save(work / (branch + "_topo.npy"), topo)
        combined = old.apply_brdf_correct(
            cube,
            topo,
            0,
            cube.lines,
            0,
            cube.columns,
            brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        np.save(work / (branch + "_combined.npy"), combined)
        if branch == "normalized":
            with rasterio.open(next(flight.glob("*__corrected.img"))) as src:
                mismatch = mask_mismatch = 0
                for row in range(0, src.height, 128):
                    block = src.read(
                        window=rasterio.windows.Window(
                            0, row, src.width, min(128, src.height - row)
                        )
                    ).transpose(1, 2, 0)
                    actual = combined[row : row + len(block)]
                    mask_mismatch += int(
                        np.count_nonzero(np.isfinite(block) != np.isfinite(actual))
                    )
                    mismatch += int(
                        np.count_nonzero(np.isfinite(block) & (block != actual))
                    )
            assert mismatch == mask_mismatch == 0
            replay["historical_exact_replay"] = dict(
                values=int(combined.size),
                finite_mismatches=mismatch,
                mask_mismatches=mask_mismatch,
            )
        del combined, topo
        brdf = old.apply_brdf_correct(
            cube,
            data,
            0,
            cube.lines,
            0,
            cube.columns,
            brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        np.save(work / (branch + "_brdf.npy"), brdf)
        nonzero = valid & (data[:, :, 4] != 0)
        ratio = brdf[:, :, 4][nonzero].astype(float) / data[:, :, 4][nonzero]
        relative = abs(ratio / cf[nonzero] - 1)
        assert relative.max() < 1e-6, "Historical factor reconstruction changed"
        replay[branch] = dict(
            factor_ratio_relative_roundoff=summarize(relative),
            valid_pixels=int(valid.sum()),
            coverage={
                s: int(
                    np.count_nonzero(
                        valid
                        & np.isfinite(
                            np.load(work / (branch + "_" + s + ".npy"), mmap_mode="r")
                        ).all(2)
                    )
                )
                for s in stages
            },
        )
        del brdf, data
    # Validated kernel geometry first. Do not attempt radiometry-labelled fits on DN.
    print("Validated angular support assessment", flush=True)
    X, mask, solar = current._brdf_design(cube, current.HYTOOLS_BRDF_KERNEL_CONFIG)
    matrix = X[valid & mask].astype(float)
    singular = np.linalg.svd(matrix, compute_uv=False)
    rank = int(np.linalg.matrix_rank(matrix))
    condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else None
    del matrix, X
    assert rank < 3, (
        "If geometry now supports fitting, explicitly review and run validated refits"
    )
    support = dict(
        status="UNSUPPORTED",
        rank=rank,
        required_rank=3,
        singular_values=singular.tolist(),
        condition_number=condition,
        geometry_pixels=int(np.count_nonzero(valid & mask)),
        scene_solar_zenith_radians=solar,
        refitted_models=0,
        unsupported_band_fits=10,
        reason="Rank-deficient angular design; no refit forced. DN branches additionally lack physical calibration.",
        hypothetical_status="HYPOTHETICAL_METASHAPE_32768: computational sensitivity only, no absolute validity",
    )
    # Full-rank invariance under the actual validated fitting API, synthetic control.
    import runpy
    import tempfile
    from spectralbridge.radiometry import Radiometry

    scene = runpy.run_path(str(ROOT / "tests/test_aop_drone_equivalence.py"))["scene"]
    with tempfile.TemporaryDirectory(dir=work, prefix="supported-invariance-") as temp:
        h5, _, _, _ = scene(Path(temp), "supported_scale_control", 1.0, 0.0)
        synthetic = NeonCube(h5)
        # This synthetic scene has exactly known physical units.
        a = current.fit_and_save_brdf_model(
            synthetic,
            Path(temp) / "one",
            brdf_kernel_config=current.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        aa = json.loads(a.read_text())
        r1 = current.apply_brdf_correct(
            synthetic,
            synthetic.data,
            0,
            synthetic.lines,
            0,
            synthetic.columns,
            coeff_path=a,
            brdf_kernel_config=current.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        factor1 = r1 / synthetic.data
        synthetic.data = (synthetic.data * np.float32(2)).astype(np.float32)
        synthetic.radiometry = Radiometry(
            1.0, 0.0, "VALID", "Synthetic rescaling experiment only"
        )
        # Remove source identity cache after replacing this synthetic array.
        for key in list(vars(synthetic)):
            if "digest" in key or "signature" in key:
                delattr(synthetic, key)
        b = current.fit_and_save_brdf_model(
            synthetic,
            Path(temp) / "two",
            brdf_kernel_config=current.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        bb = json.loads(b.read_text())
        r2 = current.apply_brdf_correct(
            synthetic,
            synthetic.data,
            0,
            synthetic.lines,
            0,
            synthetic.columns,
            coeff_path=b,
            brdf_kernel_config=current.HYTOOLS_BRDF_KERNEL_CONFIG,
        )
        invariance = dict(
            scope="Synthetic full-rank control through actual validated fit/application API; a=2 stays within unchanged 0..2 eligibility; not a Goldhill fit",
            statuses=[aa["validation"]["status"], bb["validation"]["status"]],
            max_abs_factor_difference=float(np.max(abs(factor1 - r2 / synthetic.data))),
            same_eligible_population=True,
        )
        assert invariance["max_abs_factor_difference"] < 1e-5
    replay["validated_refit"] = support
    replay["supported_invariance"] = invariance
    replay["historical_red_factor"] = dict(
        **summarize(cf[valid]),
        nonpositive_or_invalid_predictions=int(
            np.count_nonzero(
                valid
                & ((den <= 0) | (num <= 0) | ~np.isfinite(den) | ~np.isfinite(num))
            )
        ),
        neutral_fallback_pixels=int(np.count_nonzero(valid & (cf == 1))),
        gains_over_10=int(np.count_nonzero(valid & (cf > 10))),
        gains_over_1000=int(np.count_nonzero(valid & (cf > 1000))),
    )
    replay["fixed_coefficient_factor_difference"] = 0.0
    save("replay_diagnostics.json", replay)
    after = {str(f): sha(f) for f in protected}
    assert before == after
    manifest = dict(
        work=str(work),
        historical_flight=str(flight),
        source_evidence=str(scale_dir / "evidence.json"),
        source_normalization=str(scale_dir / "verified_numeric_mapping.json"),
        historical_code_sha256=sha(HERE / "historical_corrections.py"),
        source_hashes_before=before,
        source_hashes_after=after,
        all_protected_files_unchanged=True,
        elapsed_seconds=time.monotonic() - started,
        scope="Isolated experimental replay of historical invalid model, not production processing or approval",
        intermediates="Float32 NPY arrays retain original grid and masks; recovered TIFFs preserve complete georeferencing and tags.",
        branches={
            "normalized": "Historical normalized values, physical units unverified",
            "recovered": "RECOVERED_SOURCE_DN — PHYSICAL_UNITS_UNVERIFIED",
            "hypothetical": "HYPOTHETICAL_METASHAPE_32768",
        },
        no_brdf_control="recovered_topo.npy",
        kernel_portability="Historical coefficients apply ONLY with archived historical kernels; never transferred to repaired kernels",
    )
    save("experiment_manifest.json", manifest)
    print("Replay complete", flush=True)


if __name__ == "__main__":
    main()
