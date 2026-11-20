"""Apply verified conservative refits on native grids; attempt normal translation.

Uses saved SCS+C then combined BRDF, with unchanged coefficients/reference and
historical conditional-radiometry boundary. Products remain explicitly
experimental. Production translation/library guards are called unchanged.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window
from threadpoolctl import threadpool_limits

import drone_shade_excluded_refit as refit
from drone_shade_mask_preview import ROOT, MASKS, file_sha256
from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.envi import hdr_to_dict
from spectralbridge.envi_writer import EnviWriter
from spectralbridge.drone_translation import (
    load_drone_translation_plans,
    apply_drone_translation,
    translated_output_stem,
)
from spectralbridge.drone_translation_registry import (
    packaged_drone_translation_coefficients_path,
)

OUTPUT = (
    ROOT
    / "archive/local/drone-calibration-translation/2026-11-19/conservative-refitted-products"
)
EVIDENCE = (
    ROOT
    / "provenance/drone-calibration-translation/2026-11-19/conservative-refitted-products"
)


def run(site):
    driver = refit.setup()
    config = next(
        c
        for c in json.loads((refit.PRIOR / "site_inputs.json").read_text())
        if c["site"].lower() == site
    )
    raw, design, geometry, footprint, domain, training, groups, transform, crs = (
        refit.cube_inputs(driver, config)
    )
    models = refit.DEST / site / "conservative"
    completed = json.loads((models / "completed.json").read_text())
    for name, digest in completed["outputs"].items():
        if file_sha256(models / name) != digest:
            raise ValueError("Refit model changed")
    topo = json.loads((models / "conditioned_scsc_model.json").read_text())
    brdf_path = next((models / "combined").glob("*brdf_model.json"))
    brdf = json.loads(brdf_path.read_text())
    if not all(f["status"] == "VALID" for f in topo["fits"]) or not all(
        f["status"] == "VALID" for f in brdf["validation"]["fits"]
    ):
        raise ValueError("All ten fitted bands must have valid support")
    mask_path = MASKS / refit.mask_filename(config["flight_stem"], 0.1)
    if file_sha256(mask_path) != completed["identity"]["mask_sha256"]:
        raise ValueError("Fit/application masks differ")
    with rasterio.open(mask_path) as mask:
        if (mask.shape, mask.transform, mask.crs) != (domain.shape, transform, crs):
            raise ValueError("Mask grid differs")
        retain = mask.read(1) == 0
    cube = driver.support.Cube(
        raw, domain & retain, geometry, scale=driver.SCALE, footprint=footprint
    )
    cube.h5_path = Path(config["prepared"])
    cube.transform = transform.to_gdal()
    cube.projection_wkt = crs.to_wkt()
    design_hash = file_sha256(refit.BASE / site / "center_design.npy")
    apply_topo = driver.support.isolated(driver.support.topo.apply_conditioned_scs_c)
    apply_brdf = driver.support.isolated(
        driver.support.c.apply_brdf_correct, design, design_hash
    )
    raw_path = (
        refit.BASE / site / f"{config['flight_stem']}__experimental_candidate.img"
    )
    header = hdr_to_dict(raw_path.with_suffix(".hdr"))
    header.update(
        {
            "description": "Shade-excluded refitted SCS+C then combined BRDF; EXPERIMENTAL conditional historical radiometry",
            "brdf status": "VALID",
            "scientific validation status": "EXPERIMENTAL",
            "shade mask sha256": file_sha256(mask_path),
            "brdf kernel math version": brdf["kernel_math_version"],
            "brdf validation policy": brdf["validation_policy"],
            "data ignore value": np.nan,
        }
    )
    folder = OUTPUT / site
    folder.mkdir(parents=True, exist_ok=True)
    evidence = EVIDENCE / site
    evidence.mkdir(parents=True, exist_ok=True)
    stem = (
        folder
        / f"{config['flight_stem']}__conservative_refitted_topo_brdf_EXPERIMENTAL"
    )
    identity = dict(
        raw_sha256=file_sha256(raw_path),
        raw_header_sha256=file_sha256(raw_path.with_suffix(".hdr")),
        topo_sha256=file_sha256(models / "conditioned_scsc_model.json"),
        brdf_sha256=file_sha256(brdf_path),
        mask_sha256=file_sha256(mask_path),
        design_sha256=design_hash,
        refit_input_contract_sha256=file_sha256(
            refit.DEST / site / "input_contract.json"
        ),
    )
    checkpoint = evidence / "application_complete.json"
    previous = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
    reuse = previous.get("identity") == identity
    if reuse:
        for suffix, digest in previous["outputs"].items():
            if file_sha256(stem.with_suffix(suffix)) != digest:
                raise ValueError("Changed application output")
        print(site, "verified application reuse", flush=True)
    else:
        writer = EnviWriter(stem, header)
        stats = [
            dict(
                site=site,
                band_1based=b + 1,
                wavelength_nm=float(cube.wavelengths[b]),
                valid_pixels=0,
                retained_domain_pixels=int(cube.mask_no_data.sum()),
                maximum_combined_gain=None,
                maximum_stored_value=None,
            )
            for b in range(10)
        ]
        try:
            with threadpool_limits(limits=1):
                for start in range(0, cube.lines, 128):
                    end = min(start + 128, cube.lines)
                    block = np.asarray(raw[start:end], dtype=np.float32)
                    topographic = apply_topo(
                        cube, block, start, end, 0, cube.columns, model=topo
                    ).values
                    corrected = apply_brdf(
                        cube,
                        topographic,
                        start,
                        end,
                        0,
                        cube.columns,
                        coeff_path=brdf_path,
                        input_stage="topographic_only",
                    )
                    excluded = ~cube.mask_no_data[start:end]
                    if np.isfinite(corrected[excluded]).any():
                        raise ValueError("Excluded shade/domain gained finite output")
                    for b in range(10):
                        valid = np.isfinite(corrected[..., b])
                        stats[b]["valid_pixels"] += int(valid.sum())
                        if valid.any():
                            value = float(np.max(corrected[..., b][valid]))
                            stats[b]["maximum_stored_value"] = max(
                                value, stats[b]["maximum_stored_value"] or value
                            )
                        positive = (
                            valid & np.isfinite(block[..., b]) & (block[..., b] > 0)
                        )
                        if positive.any():
                            gain = float(
                                np.max(
                                    corrected[..., b][positive]
                                    / block[..., b][positive]
                                )
                            )
                            stats[b]["maximum_combined_gain"] = max(
                                gain, stats[b]["maximum_combined_gain"] or gain
                            )
                    writer.write_chunk(corrected, start, 0)
                    print(site, f"application rows {end}/{cube.lines}", flush=True)
        finally:
            writer.close()
        with rasterio.open(stem.with_suffix(".img")) as output:
            if (output.shape, output.crs, output.transform) != (
                domain.shape,
                crs,
                transform,
            ):
                raise ValueError("Output grid changed")
            for start in range(0, cube.lines, 128):
                end = min(start + 128, cube.lines)
                values = output.read(window=Window(0, start, cube.columns, end - start))
                assert not np.isfinite(values[:, ~cube.mask_no_data[start:end]]).any()
        if not all(r["valid_pixels"] > 0 for r in stats):
            raise ValueError("A corrected band has no usable pixels")
        pd.DataFrame(stats).to_csv(evidence / "corrected_band_qa.csv", index=False)
        write_json_atomic(
            checkpoint,
            dict(
                identity=identity,
                outputs={
                    suffix: file_sha256(stem.with_suffix(suffix))
                    for suffix in [".img", ".hdr"]
                },
                all_ten_bands_populated=True,
                excluded_pixels_remain_nodata=True,
                grid_match=True,
                experimental=True,
                production_approved=False,
            ),
        )
    plans = load_drone_translation_plans(
        source_wavelengths_nm=header["wavelength"],
        target_sensors=["Landsat_8_OLI", "Landsat_9_OLI-2"],
    )
    translations = []
    for plan in plans:
        result = dict(
            target=plan.target_sensor,
            coefficient_units=plan.reflectance_units,
            coefficient_sha256=plan.coefficient_sha256,
        )
        try:
            translated = apply_drone_translation(
                stem.with_suffix(".img"),
                stem.with_suffix(".hdr"),
                plan=plan,
                output_stem=translated_output_stem(
                    folder,
                    config["flight_stem"] + "__conservative_refitted",
                    plan.target_sensor,
                ),
            )
            result.update(status=translated["status"], output=translated["output_img"])
        except ValueError as exc:
            result.update(status="UNSUPPORTED", reason=str(exc))
        translations.append(result)
    write_json_atomic(
        evidence / "translation_attempt.json",
        dict(
            site=site,
            corrected_input=str(stem.with_suffix(".img")),
            translations=translations,
            coefficient_registry=str(packaged_drone_translation_coefficients_path()),
            uploaded=False,
        ),
    )
    print(site, "translation attempts", translations, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, choices=["ruby", "gordon", "goldhill"])
    run(parser.parse_args().site)
