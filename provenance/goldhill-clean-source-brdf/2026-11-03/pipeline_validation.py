# ruff: noqa: E402
"""Actual drone producer/stage attempts and isolated hypothetical BRDF refusal."""

import json
import logging
from pathlib import Path
import sys

import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import (
    ROOT,
    WORK,
    SOURCE,
    WAVES,
    SCALE,
    Cube,
    HypothesisRadiometry,
    isolated,
    write,
)  # noqa:E402
from spectralbridge import corrections as c  # noqa:E402
from spectralbridge.pipelines.drone import (
    convert_drone_tiff_to_h5,
    export_h5_to_envi,
    run_drone_pipeline,
    apply_drone_corrections,
)  # noqa:E402
from spectralbridge.neon_cube import NeonCube  # noqa:E402
from spectralbridge.paths import FlightlinePaths  # noqa:E402
from spectralbridge.polygons import (
    build_polygon_pixel_index,
    extract_polygon_parquet_from_envi,
)  # noqa:E402
from spectralbridge.drone_translation import (
    load_drone_translation_plans,
    apply_drone_translation,
)  # noqa:E402


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    out = WORK / "production_attempt"
    out.mkdir(exist_ok=True)
    h5 = out / "goldhill_clean_hypothesis.h5"
    geometry = {}
    paths = {}
    for name in ["slope", "aspect", "solar_zn", "solar_az"]:
        path = (
            Path("/private/tmp/goldhill-end-to-end-20261103/ancillary")
            / f"legacy_{name}.tif"
        )
        paths[name] = path
        with rasterio.open(path) as src:
            geometry[name] = src.read(1)
    declaration = HypothesisRadiometry(
        SCALE,
        0,
        "HYPOTHETICAL_UNVERIFIED",
        "P172 isolated MicaSense_Metashape_DN_32768 hypothesis",
    ).record()
    convert_drone_tiff_to_h5(
        SOURCE,
        output_h5_path=h5,
        wavelengths_nm=WAVES,
        fwhm_nm=[28, 32, 14, 27, 16, 14, 10, 12, 18, 57],
        slope_tiff=paths["slope"],
        aspect_tiff=paths["aspect"],
        solar_zenith_tiff=paths["solar_zn"],
        solar_azimuth_tiff=paths["solar_az"],
        radiometry=declaration,
        require_solar_geometry=True,
    )
    cube = NeonCube(h5)
    science_paths = FlightlinePaths(out, "GOLDHILL_CLEAN_CONDITIONAL")
    img, hdr = export_h5_to_envi(
        h5, output_stem=science_paths.envi_img.with_suffix(""), cube=cube
    )
    checks = []
    with rasterio.open(SOURCE) as src, rasterio.open(img) as dest:
        assert src.shape == dest.shape and src.crs == dest.crs
        np.testing.assert_allclose(
            tuple(src.transform), tuple(dest.transform), atol=1e-6, rtol=0
        )
        assert np.array_equal(src.dataset_mask() > 0, cube.source_valid_mask)
        assert np.array_equal(cube.wavelengths, WAVES)
        for b in range(10):
            a = src.read(b + 1)
            z = dest.read(b + 1)
            valid = src.dataset_mask() > 0
            assert np.array_equal(a[valid], z[valid])
            decoded = np.asarray(a, np.float32) * np.float32(SCALE)
            # Experimental affine method remains unaccepted by production require_valid.
            rad = HypothesisRadiometry(**declaration)
            decoded2 = rad.to_physical(z)
            inverse = rad.to_stored(decoded2)
            checks.append(
                dict(
                    wavelength_nm=int(WAVES[b]),
                    max_decode_error=float(
                        np.nanmax(abs(decoded[valid] - decoded2[valid]))
                    ),
                    max_roundtrip_stored_error=float(
                        np.nanmax(abs(z[valid] - inverse[valid]))
                    ),
                    mask_exact=True,
                )
            )

    def attempt(name, fn):
        print("ACTUAL STAGE", name, flush=True)
        try:
            value = fn()
            item = dict(stage=name, status="EXECUTED", result=str(value))
        except Exception as exc:
            item = dict(
                stage=name,
                status="UNSUPPORTED",
                reason=str(exc),
                exception_type=type(exc).__name__,
                audit=getattr(exc, "audit", None),
            )
        return item

    stages = [
        dict(stage="source_ingestion", status="EXECUTED", h5=str(h5)),
        dict(stage="raw_ENVI_export", status="EXECUTED", img=str(img), hdr=str(hdr)),
    ]
    stages.append(attempt("current_topography", lambda: c.fit_scs_c_coefficients(cube)))
    model = c.fit_and_save_brdf_model(
        cube,
        out / "production_brdf_preflight_final",
        brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    record = json.loads(model.read_text())
    stages.append(
        dict(
            stage="current_BRDF_preflight",
            status=record["validation"]["status"],
            model=str(model),
            reasons=record["validation"]["reasons"],
        )
    )
    stages.append(
        attempt(
            "current_topo_BRDF_driver",
            lambda: apply_drone_corrections(
                cube=cube,
                envi_img=img,
                envi_hdr=hdr,
                corrected_stem=out / "corrected",
                apply_topo=True,
                apply_brdf=True,
            ),
        )
    )
    polygons = (
        ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
    )
    index = build_polygon_pixel_index(science_paths, polygons, reference_product="envi")
    stages.append(dict(stage="polygon_pixel_index", status="EXECUTED", path=str(index)))
    stages.append(
        attempt(
            "physical_polygon_library",
            lambda: extract_polygon_parquet_from_envi(
                img, hdr, index, out / "not_approved_library.parquet"
            ),
        )
    )
    for plan in load_drone_translation_plans(source_wavelengths_nm=WAVES):
        stages.append(
            attempt(
                "translation_" + plan.target_sensor,
                lambda p=plan: apply_drone_translation(
                    img,
                    hdr,
                    output_stem=out / "translation" / p.target_sensor.replace(" ", "_"),
                    plan=p,
                ),
            )
        )
    # The actual producer uses the ingested source and keeps all requested corrections enabled.
    result = run_drone_pipeline(
        input_h5_dir=h5,
        polygon_path=polygons,
        output_dir=WORK / "producer_run",
        apply_topo=True,
        apply_brdf=True,
        apply_translation=True,
        extraction_mode="polygon",
        merge_extractions=False,
        require_solar_geometry=True,
        raise_on_incomplete=False,
    )
    write("producer_untimed_result.json", result)
    # Explicit UTC timing scenario based on recovered camera evidence; not certified clock truth.
    timed_h5 = out / "goldhill_clean_hypothesis_timed.h5"
    convert_drone_tiff_to_h5(
        SOURCE,
        output_h5_path=timed_h5,
        wavelengths_nm=WAVES,
        fwhm_nm=[28, 32, 14, 27, 16, 14, 10, 12, 18, 57],
        slope_tiff=paths["slope"],
        aspect_tiff=paths["aspect"],
        solar_zenith_tiff=paths["solar_zn"],
        solar_azimuth_tiff=paths["solar_az"],
        acquisition_datetime="2023-08-15T19:53:07Z",
        require_solar_geometry=True,
        radiometry=declaration,
    )
    result = run_drone_pipeline(
        input_h5_dir=timed_h5,
        polygon_path=polygons,
        output_dir=WORK / "producer_run_timed",
        apply_topo=True,
        apply_brdf=True,
        apply_translation=True,
        extraction_mode="polygon",
        merge_extractions=False,
        require_solar_geometry=True,
        raise_on_incomplete=False,
    )
    write("producer_embedded_time_result.json", result)
    manifest = out / "conditional_UTC_timestamp_scenario.csv"
    manifest.write_text(
        "Plot,Day of data collection,Mean Time of data collection (24 hr clock)\nproduction_attempt,2023-08-15,19:53:07\n"
    )
    result = run_drone_pipeline(
        input_h5_dir=timed_h5,
        polygon_path=polygons,
        output_dir=WORK / "producer_run_utc_scenario",
        drone_manifest_path=manifest,
        drone_manifest_timezone="UTC",
        apply_topo=True,
        apply_brdf=True,
        apply_translation=True,
        extraction_mode="polygon",
        merge_extractions=False,
        require_solar_geometry=True,
        raise_on_incomplete=False,
    )
    write("producer_result.json", result)
    # Isolated calibration assumption reaches the angular gate; it is not an API approval.
    clean = np.load(WORK / "clean_candidate.npy", mmap_mode="r")
    masks = np.load(HERE / "filter_masks.npz")
    geometry.update(
        sensor_zn=np.zeros(masks["source_valid"].shape, np.float32),
        sensor_az=np.zeros(masks["source_valid"].shape, np.float32),
    )
    experimental = Cube(
        clean, masks["source_valid"], geometry, scale=1, footprint=masks["source_valid"]
    )
    for topo in [False, True]:
        path = isolated(c.fit_and_save_brdf_model)(
            experimental,
            WORK / f"E_after_final_{'combined' if topo else 'brdf'}",
            brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
            rho_max=None,
            apply_topography=topo,
        )
        model = json.loads(path.read_text())
        write(f"E_after_{'combined' if topo else 'brdf'}_model.json", model)
        assert model["validation"]["status"] == "UNSUPPORTED" and "iso" not in model
        stages.append(
            dict(
                stage="isolated_hypothesis_" + ("combined" if topo else "BRDF"),
                status="UNSUPPORTED",
                rank=[r["rank"] for r in model["validation"]["fits"]],
                stable_rank=[r["stable_rank"] for r in model["validation"]["fits"]],
                reasons=[r.get("reason") for r in model["validation"]["fits"]],
                image_created=False,
            )
        )
        try:
            isolated(c.apply_brdf_correct)(
                experimental,
                experimental.data[:128],
                0,
                128,
                0,
                experimental.columns,
                coeff_path=path,
            )
        except ValueError as exc:
            assert "UNSUPPORTED" in str(exc)
        else:
            raise AssertionError("Unsupported fit was applied")
    write("pipeline_stage_results.json", stages)
    write(
        "ingestion_and_scaling.json",
        dict(
            status="EXECUTED_NUMERICAL_AND_HYPOTHETICAL_DIAGNOSTICS_ONLY",
            calibration_status="HYPOTHETICAL_UNVERIFIED",
            checks=checks,
            physical_conversion_exactly_once=True,
            source_valid_pixels=int(cube.source_valid_mask.sum()),
            orientation_preserved=True,
            production_sensor_views_created=False,
            source_h5=str(h5),
            raw_envi=[str(img), str(hdr)],
            producer_status=result.get("status"),
            no_official_library_created=not (
                out / "not_approved_library.parquet"
            ).exists(),
        ),
    )
    print("PRODUCTION AND HYPOTHETICAL GATES VERIFIED", flush=True)


if __name__ == "__main__":
    main()
