"""Actual production entry points plus explicitly isolated historical replays.

No physical calibration or per-pixel viewing geometry is invented. Production
stage refusals are outcomes. Historical functions remain unmodified and emit
DIAGNOSTIC_ONLY products into a fresh experimental namespace.
"""

import copy
import hashlib
import importlib.util
import json
import logging
from pathlib import Path
import subprocess
import sys

import h5py
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/goldhill-end-to-end-20261103")
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.pipelines.drone import (  # noqa: E402
    convert_drone_tiff_to_h5,
    export_h5_to_envi,
    apply_drone_corrections,
)  # noqa: E402
from spectralbridge.neon_cube import NeonCube  # noqa: E402
from spectralbridge.paths import FlightlinePaths  # noqa: E402
from spectralbridge.polygons import (  # noqa: E402
    build_polygon_pixel_index,
    extract_polygon_parquet_from_envi,
)  # noqa: E402
from spectralbridge.drone_translation import (  # noqa: E402
    load_drone_translation_plans,
    apply_drone_translation,
    ensure_matched_source_product,
)  # noqa: E402
from spectralbridge import corrections  # noqa: E402

NEW = Path(
    "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
)
OLDTIFF = Path("/private/tmp/p168-goldhill-sources/ten_cm/aligned_orthomosaic.tif")
ORIGINAL = Path("/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif")
LEGACY_H5 = Path("/private/tmp/assumed-viewing-angles-20261103/goldhill_working.h5")
POLYGONS = (
    ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
)
OLD_MODULE = (
    ROOT / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
)
MODEL = (
    ROOT
    / "provenance/goldhill-correction-diagnosis/2026-10-30/saved_production_brdf_model.json"
)
PRIOR = Path("/private/tmp/goldhill-radiometric-recovery-20261102")
CAMERAS = Path("/Users/tuff/Downloads/AOP-GOLDHILL-camera_locations.csv")


def sha(path):
    d = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024**2), b""):
            d.update(b)
    return d.hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return safe(value.tolist())
    if isinstance(value, np.generic):
        return safe(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def write(name, value):
    (HERE / name).write_text(json.dumps(safe(value), indent=2, allow_nan=False) + "\n")


def attempt(name, function):
    print("PRODUCTION", name, flush=True)
    try:
        value = function()
        outcome = dict(stage=name, status="EXECUTED", result=safe(value))
    except Exception as error:
        outcome = dict(
            stage=name,
            status="UNSUPPORTED",
            error_type=type(error).__name__,
            reason=str(error),
            audit=safe(getattr(error, "audit", None)),
        )
    write(name + ".json", outcome)
    return outcome


def raster(array, path, profile, description):
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    bands = 1 if array.ndim == 2 else array.shape[-1]
    with (
        rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True),
        rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=array.shape[0],
            width=array.shape[1],
            count=bands,
            dtype="float32",
            crs=profile["crs"],
            transform=profile["transform"],
            nodata=np.nan,
            tiled=True,
            compress="deflate",
            predictor=3,
        ) as dst,
    ):
        for b in range(bands):
            values = array if bands == 1 else array[..., b]
            dst.write(np.asarray(values, np.float32), b + 1)
        dst.update_tags(
            EXPERIMENT_STATUS=description, PHYSICAL_CALIBRATION_STATUS="UNVERIFIED"
        )


def main():
    WORK.mkdir(exist_ok=True, parents=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    protected = [
        NEW,
        OLDTIFF,
        ORIGINAL,
        LEGACY_H5,
        POLYGONS,
        OLD_MODULE,
        MODEL,
        CAMERAS,
    ]
    protected += [
        PRIOR / f"normalized_{stage}.npy"
        for stage in ["raw", "topo", "brdf", "combined"]
    ]
    protected += [
        ROOT / "src/spectralbridge" / p
        for p in [
            "corrections.py",
            "pipelines/drone.py",
            "radiometry.py",
            "library_analysis.py",
            "polygons.py",
            "drone_translation.py",
        ]
    ]
    before = {str(p): sha(p) for p in protected}
    previous = HERE / "input_manifest.json"
    if previous.exists():
        assert json.loads(previous.read_text())["protected_hashes"] == before
    else:
        write(
            "input_manifest.json",
            dict(
                protected_hashes=before,
                repository_revision=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
                source_derivative_record=json.loads(
                    NEW.with_suffix(".radiometry.json").read_text()
                ),
                production_code_changes=False,
            ),
        )
    with rasterio.open(NEW) as src:
        profile = src.profile.copy()
        new_mask = src.dataset_mask() > 0
        assert (
            src.count == 10
            and src.dtypes[0] == "float32"
            and src.crs.to_epsg() == 26913
        )
        np.testing.assert_allclose(src.res, [0.1, 0.1], atol=1e-10, rtol=0)
    legacy = NeonCube(LEGACY_H5)
    shape = legacy.data.shape[:2]
    assert shape == new_mask.shape
    waves = legacy.wavelengths.copy()
    with h5py.File(LEGACY_H5, "r") as h:
        meta = h["AOP-GOLDHILL-08-14-23-ExportPackage/Reflectance/Metadata"]
        fwhm = meta["Spectral_Data/FWHM"][:]
        solar_provenance = {k: meta.attrs[k] for k in meta.attrs}
    inputs = {}
    for name in ["slope", "aspect", "solar_zn", "solar_az"]:
        arr = legacy.get_ancillary(name, radians=False)
        path = WORK / "ancillary" / f"legacy_{name}.tif"
        raster(
            arr,
            path,
            profile,
            "LEGACY_PROVENANCE_GEOMETRY; acquisition datetime unresolved",
        )
        inputs[name] = path
    write(
        "geometry_provenance.json",
        dict(
            source=str(LEGACY_H5),
            solar=solar_provenance,
            source_metadata_nominal_acquisition="2023-08-14 13:41 local; original Metadata.txt",
            datetime_conflict=True,
            terrain_paths=inputs,
            sensor_views="NOT_AVAILABLE per orthomosaic pixel; CSV poses not assigned to contributing pixels",
            camera_csv=str(CAMERAS),
            camera_crs_conflict="CSV says 5070; coordinates align with TIFF 26913; convention unresolved",
            wavelengths_nm=waves,
            fwhm_nm=fwhm,
        ),
    )
    declaration = json.loads(NEW.with_suffix(".radiometry.json").read_text())[
        "radiometry"
    ]
    # Original derivation quality provenance stays in the immutable manifest;
    # the TIFF reader attaches its own actual ingestion-mask provenance.
    declaration["encoding"].pop("quality_mask", None)
    # The TIFF has an internal GDAL mask. Reader must persist that source footprint.
    paths = FlightlinePaths(
        WORK / "production_attempt", "AOP_GOLDHILL_FIXED10K_20230814"
    )
    h5 = WORK / "production_attempt" / "new_source.h5"
    h5.parent.mkdir(exist_ok=True)
    convert_drone_tiff_to_h5(
        NEW,
        output_h5_path=h5,
        wavelengths_nm=waves,
        fwhm_nm=fwhm,
        slope_tiff=inputs["slope"],
        aspect_tiff=inputs["aspect"],
        solar_zenith_tiff=inputs["solar_zn"],
        solar_azimuth_tiff=inputs["solar_az"],
        radiometry=declaration,
        require_solar_geometry=True,
    )
    cube = NeonCube(h5)
    assert np.array_equal(cube.mask_no_data, new_mask)
    assert np.array_equal(cube.wavelengths, waves)
    rawstem = paths.envi_img.with_suffix("")
    img, hdr = export_h5_to_envi(h5, output_stem=rawstem, cube=cube)
    with rasterio.open(NEW) as src, rasterio.open(img) as envi:
        assert src.shape == envi.shape and src.crs == envi.crs
        np.testing.assert_allclose(
            tuple(src.transform), tuple(envi.transform), atol=1e-6, rtol=0
        )
        finite_exact = True
        for y in range(0, src.height, 128):
            w = rasterio.windows.Window(0, y, src.width, min(128, src.height - y))
            a = src.read(window=w)
            b = envi.read(window=w)
            finite = np.isfinite(a)
            finite_exact &= bool(
                np.array_equal(a[finite], b[finite])
                and np.array_equal(np.isfinite(a), np.isfinite(b))
            )
        assert finite_exact
    write(
        "ingestion.json",
        dict(
            status="EXECUTED",
            h5=h5,
            envi_img=img,
            envi_hdr=hdr,
            valid_pixels=int(new_mask.sum()),
            finite_values_and_missingness_exact=True,
            no_flips=True,
            crs=str(profile["crs"]),
            source_transform=list(profile["transform"]),
            physical_status=cube.radiometry.status,
            sensor_view_datasets_created=False,
        ),
    )
    stages = []
    for name, topo, brdf in [
        ("A_raw", False, False),
        ("B_topographic", True, False),
        ("C_brdf", False, True),
        ("D_combined", True, True),
    ]:
        (WORK / "production_attempt" / name).mkdir(parents=True, exist_ok=True)
        outcome = attempt(
            name,
            lambda n=name, t=topo, b=brdf: apply_drone_corrections(
                cube=cube,
                envi_img=img,
                envi_hdr=hdr,
                corrected_stem=WORK / "production_attempt" / n / n,
                apply_topo=t,
                apply_brdf=b,
            ),
        )
        stages.append(outcome)
    # Current topographic entry point is attempted independently as requested.
    stages.append(
        attempt("B_direct_scs_c_fit", lambda: corrections.fit_scs_c_coefficients(cube))
    )
    stages.append(
        attempt(
            "C_direct_brdf_fit",
            lambda: corrections.fit_and_save_brdf_model(
                cube, WORK / "production_attempt" / "C_direct_model"
            ),
        )
    )
    print("PRODUCTION polygon index", flush=True)
    index = build_polygon_pixel_index(paths, POLYGONS, reference_product="envi")
    stages.append(dict(stage="F_polygon_index", status="EXECUTED", output=str(index)))
    stages.append(
        attempt(
            "F_physical_polygon_library",
            lambda: extract_polygon_parquet_from_envi(
                img,
                hdr,
                index,
                WORK / "production_attempt" / "physical_library.parquet",
            ),
        )
    )
    try:
        plans = load_drone_translation_plans(source_wavelengths_nm=waves)
        seen = set()
        for plan in plans:
            slug = plan.target_sensor.replace(" ", "_")
            stages.append(
                attempt(
                    "E_" + slug,
                    lambda p=plan, s=slug: apply_drone_translation(
                        img,
                        hdr,
                        output_stem=WORK / "production_attempt" / "translation" / s,
                        plan=p,
                    ),
                )
            )
            if plan.source_sensor not in seen:
                seen.add(plan.source_sensor)
                # This function selects native bands only and retains the unverified encoding.
                # It is a numerical MicaSense subset diagnostic, not spectral calibration.
                (WORK / "numerical_native_subsets").mkdir(parents=True, exist_ok=True)
                out = attempt(
                    "E_numerical_" + plan.source_sensor,
                    lambda p=plan: ensure_matched_source_product(
                        img,
                        hdr,
                        output_stem=WORK
                        / "numerical_native_subsets"
                        / p.source_sensor.replace(" ", "_"),
                        plan=p,
                    ),
                )
                stages.append(out)
    except Exception as error:
        stages.append(
            dict(stage="E_plan_loading", status="UNSUPPORTED", reason=str(error))
        )
    write("production_stage_results.json", stages)
    # Historical replay retains the exact old source and coefficient bytes.
    spec = importlib.util.spec_from_file_location("p169_historical", OLD_MODULE)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)

    class Replay:
        def __init__(self):
            self.data = cube.data
            self.lines, self.columns, self.bands = self.data.shape
            self.mask_no_data = new_mask
            self.no_data = np.nan
            self.scale_factor = 1.0
            self.wavelengths = waves
            self.brdf_coefficients = copy.deepcopy(json.loads(MODEL.read_text()))

        def get_ancillary(self, name, radians=True):
            return legacy.get_ancillary(name, radians=radians)

        def iter_chunks(self, chunk_y=500, chunk_x=None):
            for y in range(0, self.lines, chunk_y):
                yield (
                    y,
                    min(y + chunk_y, self.lines),
                    0,
                    self.columns,
                    self.data[y : y + chunk_y],
                )

    replay = Replay()
    print("DIAGNOSTIC historical SCS+C fit", flush=True)
    c = old.fit_scs_c_coefficients(replay)
    branches = dict(
        new_raw=dict(
            path=str(NEW), format="tif", status="UNCALIBRATED_NUMERICAL_BASELINE"
        )
    )
    for name in ["raw", "topo", "brdf", "combined"]:
        branches["old_" + name] = dict(
            path=str(PRIOR / f"normalized_{name}.npy"),
            format="npy",
            status="HISTORICAL_UNSUPPORTED"
            if name != "raw"
            else "HISTORICAL_NUMERICAL_BASELINE",
        )
    for stage in ["topo", "brdf", "combined"]:
        output = WORK / "historical_diagnostic" / f"new_historical_{stage}.npy"
        output.parent.mkdir(exist_ok=True)
        if not output.exists():
            print("DIAGNOSTIC historical", stage, flush=True)
            if stage == "topo":
                values = old.apply_topo_correct(
                    replay, replay.data, 0, replay.lines, 0, replay.columns, scs_c=c
                )
            else:
                values = (
                    replay.data
                    if stage == "brdf"
                    else np.load(
                        WORK / "historical_diagnostic/new_historical_topo.npy",
                        mmap_mode="r",
                    )
                )
                values = old.apply_brdf_correct(
                    replay,
                    values,
                    0,
                    replay.lines,
                    0,
                    replay.columns,
                    brdf_kernel_config=old.HYTOOLS_BRDF_KERNEL_CONFIG,
                )
            np.save(output, values)
            del values
        arr = np.load(output, mmap_mode="r")
        raster(
            arr,
            output.with_suffix(".tif"),
            profile,
            "DIAGNOSTIC_ONLY historical coefficients/placeholder views; not physical reflectance",
        )
        branches["new_historical_" + stage] = dict(
            path=str(output),
            tif=str(output.with_suffix(".tif")),
            format="npy",
            status="DIAGNOSTIC_ONLY_UNSUPPORTED",
        )
    write(
        "historical_replay.json",
        dict(
            status="DIAGNOSTIC_ONLY",
            module=str(OLD_MODULE),
            module_sha256=sha(OLD_MODULE),
            model=str(MODEL),
            model_sha256=sha(MODEL),
            new_source_C=c,
            geometry="Legacy zero-view placeholders replayed only as historical controls; not assigned to current cube",
            physical_units="Unverified stored numerical units; scale=1 is only the unchanged old implementation assumption",
            current_scs_c="BLOCKED; no new production SCS+C applied",
            legacy_fallback_policy="Unchanged historical denominator/ratio identity guards remain visible; no new clipping or caps added",
        ),
    )
    # Illumination is geometry-only; it needs no fabricated reflectance calibration.
    ci = corrections.calc_cosine_i(
        legacy.get_ancillary("solar_zn"),
        legacy.get_ancillary("solar_az"),
        legacy.get_ancillary("aspect"),
        legacy.get_ancillary("slope"),
    )
    np.save(WORK / "illumination_cosine.npy", ci)
    write(
        "branches.json",
        dict(
            branches=branches,
            work=str(WORK),
            polygon_index=str(index),
            profile=dict(
                crs=str(profile["crs"]),
                transform=list(profile["transform"]),
                height=shape[0],
                width=shape[1],
            ),
            illumination=str(WORK / "illumination_cosine.npy"),
        ),
    )
    after = {p: sha(Path(p)) for p in before}
    assert before == after
    write(
        "pipeline_verification.json",
        dict(
            status="PASS",
            protected_files_unchanged=True,
            protected_count=len(before),
            production_functions_attempted=[x["stage"] for x in stages],
            production_radiometric_correction_completed=False,
            production_data_written=False,
            experiment_only=True,
        ),
    )
    print("Pipeline exercise and isolated historical replays complete", flush=True)


if __name__ == "__main__":
    main()
