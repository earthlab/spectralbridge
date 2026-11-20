"""User-authorized unmasked fitted-correction null, compared at translated stage.

This research harness uses frozen baseline (no brightness exclusion) SCS+C and
BRDF fits. It explicitly computes the diagnostic BRDF estimate even when the
reference fails the 1.96-SE criterion, preserving every QA record and INVALID
status. It never changes approved application defaults or model files. Source,
geometry, topographic validity and positive numerical denominators still apply.
Run from repo root: .venv/bin/python examples/run_unmasked_drone_translation_null.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import drone_shade_excluded_refit as refit
from drone_shade_mask_preview import ROOT, file_sha256
from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.drone_translation import (
    apply_drone_translation,
    load_drone_translation_plans,
    translated_output_stem,
)
from spectralbridge.envi import hdr_to_dict, memmap_bsq
from spectralbridge.envi_writer import EnviWriter

BASE = ROOT / "archive/local/drone-calibration-translation/2026-11-19"
OUT = BASE / "unmasked-null-products"
REPORT = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/unmasked-null-products"
)
REGISTRY = (
    REPORT.parent
    / "aop-translation-audit/aop_derived_micasense_to_landsat_fractional_reflectance_registry.json"
)


def diagnostic_brdf(values, design, model):
    """Return diagnostic ratio result and unresolved counts; never approve a fit.

    Uses saved coefficient estimates and the existing reference/design, allowing
    uncertainty failures only. Rank-deficient/missing fits are still refused.
    Numerical cancellation/nonpositive predictions remain NoData, not identity.
    """
    if model["ndvi_binning_enabled"]:
        raise ValueError("This null requires the existing single-stratum design")
    result = np.full(values.shape, np.nan, np.float32)
    checks = []
    reference = np.asarray(model["reference_design"], float)
    for record in model["validation"]["fits"]:
        band = record["band"]
        if (
            record["bin"] != 0
            or record["rank"] != 3
            or record["status"] not in {"VALID", "INVALID"}
        ):
            raise ValueError("Null requires a full-rank finite saved estimate per band")
        beta = np.asarray(record["diagnostic_coefficient_estimate"], float)
        if beta.shape != (3,) or not np.isfinite(beta).all():
            raise ValueError("Missing finite diagnostic coefficients")
        pred = np.asarray(design, float) @ beta
        ref = float(reference @ beta)
        tolerance = 8 * np.finfo(np.float32).eps
        positive = np.isfinite(pred) & (
            pred > tolerance * (np.abs(design) @ np.abs(beta))
        )
        reference_positive = np.isfinite(ref) and ref > tolerance * (
            np.abs(reference) @ np.abs(beta)
        )
        valid = np.isfinite(values[..., band]) & positive & reference_positive
        ratio = np.full(pred.shape, np.nan)
        np.divide(ref, pred, out=ratio, where=valid)
        with np.errstate(over="ignore", invalid="ignore"):
            target = (values[..., band].astype(float) * ratio).astype(np.float32)
        target[~valid | ~np.isfinite(target)] = np.nan
        result[..., band] = target
        checks.append(
            dict(
                band_1based=band + 1,
                finite_output=int(np.isfinite(target).sum()),
                numerical_exclusions=int(
                    (np.isfinite(values[..., band]) & ~np.isfinite(target)).sum()
                ),
                reference_prediction=ref,
                original_fit_status=record["status"],
            )
        )
    return result, checks


def run():
    driver = refit.setup()
    REPORT.mkdir(parents=True, exist_ok=True)
    products, comparisons = [], []
    for site in ["ruby", "gordon", "goldhill"]:
        config = next(
            c
            for c in json.loads((refit.PRIOR / "site_inputs.json").read_text())
            if c["site"].lower() == site
        )
        raw, design, geometry, footprint, domain, training, groups, transform, crs = (
            refit.cube_inputs(driver, config)
        )
        models = refit.DEST / site / "baseline"
        completed = json.loads((models / "completed.json").read_text())
        for name, digest in completed["outputs"].items():
            assert file_sha256(models / name) == digest
        topo_path = models / "conditioned_scsc_model.json"
        brdf_path = next((models / "combined").glob("*brdf_model.json"))
        topo = json.loads(topo_path.read_text())
        brdf = json.loads(brdf_path.read_text())
        if not all(f["status"] == "VALID" for f in topo["fits"]):
            raise ValueError("Baseline topographic support is required")
        cube = driver.support.Cube(
            raw, domain, geometry, scale=driver.SCALE, footprint=footprint
        )
        cube.h5_path = Path(config["prepared"])
        cube.transform = transform.to_gdal()
        cube.projection_wkt = crs.to_wkt()
        raw_path = (
            refit.BASE / site / f"{config['flight_stem']}__experimental_candidate.img"
        )
        inputs = {
            str(p): file_sha256(p)
            for p in [
                raw_path,
                raw_path.with_suffix(".hdr"),
                topo_path,
                brdf_path,
                refit.BASE / site / "center_design.npy",
            ]
        }
        folder = OUT / site
        folder.mkdir(parents=True, exist_ok=True)
        evidence = REPORT / site
        evidence.mkdir(exist_ok=True)
        native_stem = folder / f"{site}_20230814_unmasked_null_corrected_micasense_envi"
        checkpoint = evidence / "native_complete.json"
        identity = dict(
            inputs=inputs,
            policy="unmasked-diagnostic-positive-ratio-v1",
            code_sha256=file_sha256(Path(__file__)),
        )
        previous = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
        apply_topo = driver.support.isolated(
            driver.support.topo.apply_conditioned_scs_c
        )
        if previous.get("identity") == identity:
            for p, digest in previous["outputs"].items():
                assert file_sha256(Path(p)) == digest
            print(site, "native null reused", flush=True)
        else:
            hdr = hdr_to_dict(raw_path.with_suffix(".hdr"))
            hdr.update(
                {
                    "description": "EXPERIMENTAL unmasked null; diagnostic fitted BRDF ratio, failed uncertainty checks retained",
                    "brdf status": brdf["validation"]["status"],
                    "brdf model schema": 2,
                    "brdf kernel math version": brdf["kernel_math_version"],
                    "brdf validation policy": brdf["validation_policy"],
                    "scientific validation status": "EXPERIMENTAL",
                    "data ignore value": np.nan,
                }
            )
            writer = EnviWriter(native_stem, hdr)
            qa = []
            try:
                with threadpool_limits(limits=1):
                    for start in range(0, cube.lines, 128):
                        end = min(cube.lines, start + 128)
                        topographic = apply_topo(
                            cube,
                            np.asarray(raw[start:end], np.float32),
                            start,
                            end,
                            0,
                            cube.columns,
                            model=topo,
                        ).values
                        corrected, checks = diagnostic_brdf(
                            topographic, design[start:end], brdf
                        )
                        assert not np.isfinite(corrected[~domain[start:end]]).any()
                        writer.write_chunk(corrected, start, 0)
                        qa.extend(dict(start_row=start, **row) for row in checks)
                        print(site, f"native null rows {end}/{cube.lines}", flush=True)
            finally:
                writer.close()
            pd.DataFrame(qa).to_csv(evidence / "native_application_qa.csv", index=False)
            write_json_atomic(
                checkpoint,
                dict(
                    identity=identity,
                    outputs={
                        str(p): file_sha256(p)
                        for p in [
                            native_stem.with_suffix(".img"),
                            native_stem.with_suffix(".hdr"),
                        ]
                    },
                ),
            )
        # Preserve the full baseline QA; do not rewrite a failed fit into VALID.
        write_json_atomic(evidence / "baseline_brdf_qa.json", brdf["validation"])
        hdr = hdr_to_dict(native_stem.with_suffix(".hdr"))
        native = memmap_bsq(native_stem.with_suffix(".img"), hdr)
        run_metadata = dict(
            site=site,
            acquisition_date="2023-08-14",
            comparison_arm="unmasked_null",
            shade_mask_policy="NONE; no brightness exclusion",
            correction_order="baseline unmasked SCS+C then diagnostic BRDF ratio",
            production_approved=False,
            failed_brdf_qa={
                "status": brdf["validation"]["status"],
                "full_record": str(evidence / "baseline_brdf_qa.json"),
                "failed_bands": [
                    {
                        key: fit.get(key)
                        for key in (
                            "band",
                            "status",
                            "reason",
                            "reference_prediction",
                            "reference_standard_error",
                            "reference_prediction_lower_margin",
                            "rejection_components",
                        )
                    }
                    for fit in brdf["validation"]["fits"]
                    if fit["status"] != "VALID"
                ],
            }
            if brdf["validation"]["status"] != "VALID"
            else None,
            original_brdf_status=brdf["validation"]["status"],
            baseline_model_sha256=dict(
                topo=file_sha256(topo_path), brdf=file_sha256(brdf_path)
            ),
            numerical_policy="Keep source/geometry/topographic validity and positive resolved numerical denominators; waive BRDF 1.96-SE acceptance only",
        )
        plans = load_drone_translation_plans(
            REGISTRY,
            source_wavelengths_nm=hdr["wavelength"],
            target_sensors=["Landsat_8_OLI", "Landsat_9_OLI-2"],
        )
        for plan in plans:
            stem = translated_output_stem(
                folder,
                f"{site}_20230814_unmasked_null",
                plan.target_sensor,
                naming_style="micasense",
            )
            options = dict(
                output_stem=stem,
                plan=plan,
                experimental_input=True,
                experimental_input_provenance="User-authorized unmasked null comparison; frozen baseline fits; failed BRDF uncertainty QA retained, not production approved",
                output_scale_factor=1000,
                translation_metadata=run_metadata,
                experimental_failed_brdf_qa=brdf["validation"]["status"] != "VALID",
            )
            result = apply_drone_translation(
                native_stem.with_suffix(".img"),
                native_stem.with_suffix(".hdr"),
                **options,
            )
            oh = hdr_to_dict(Path(result["output_hdr"]))
            out = memmap_bsq(Path(result["output_img"]), oh)
            masked_stem = translated_output_stem(
                BASE / "translated-products" / site,
                f"{site}_20230814",
                plan.target_sensor,
                naming_style="micasense",
            )
            mh = hdr_to_dict(masked_stem.with_suffix(".hdr"))
            masked = memmap_bsq(masked_stem.with_suffix(".img"), mh)
            for key in ["map info", "projection", "lines", "samples"]:
                assert oh[key] == mh[key]
            for i, band in enumerate(plan.bands):
                for start in range(0, cube.lines, 128):
                    n = np.asarray(
                        native[band.native_source_band_index - 1, start : start + 128]
                    )
                    expected = (
                        (
                            n * np.float32(hdr["physical reflectance multiplier"])
                            + np.float32(hdr["physical reflectance offset"])
                        )
                        * np.float32(band.slope)
                        + np.float32(band.intercept)
                    ) * 1000
                    np.testing.assert_allclose(
                        out[i, start : start + 128],
                        expected,
                        rtol=1e-6,
                        atol=1e-4,
                        equal_nan=True,
                    )
                a = np.asarray(out[i])
                b = np.asarray(masked[i])
                common = np.isfinite(a) & np.isfinite(b)
                delta = (a[common].astype(float) - b[common]) / 1000
                comparisons.append(
                    dict(
                        site=site,
                        target=plan.target_sensor,
                        target_band_1based=i + 1,
                        unmasked_valid=int(np.isfinite(a).sum()),
                        masked_valid=int(np.isfinite(b).sum()),
                        common_pixels=int(common.sum()),
                        null_only_pixels=int((np.isfinite(a) & ~np.isfinite(b)).sum()),
                        masked_only_pixels=int(
                            (~np.isfinite(a) & np.isfinite(b)).sum()
                        ),
                        mean_difference_fraction=float(delta.mean()),
                        median_difference_fraction=float(np.median(delta)),
                        rmse_difference_fraction=float(np.sqrt(np.mean(delta**2))),
                    )
                )
            assert (
                apply_drone_translation(
                    native_stem.with_suffix(".img"),
                    native_stem.with_suffix(".hdr"),
                    **options,
                )["status"]
                == "reused"
            )
            products.append(
                dict(
                    site=site,
                    target=plan.target_sensor,
                    output_img=result["output_img"],
                    output_hdr=result["output_hdr"],
                    provenance_json=result["provenance_json"],
                    brdf_status=brdf["validation"]["status"],
                    full_grid_translation="PASS",
                    restart="PASS",
                    sha256={
                        str(Path(result[k])): file_sha256(Path(result[k]))
                        for k in ["output_img", "output_hdr", "provenance_json"]
                    },
                )
            )
            print(site, plan.target_sensor, "null translated and compared", flush=True)
        assert inputs == {p: file_sha256(Path(p)) for p in inputs}
        del cube, raw, design, geometry, domain, training, groups, native, out, masked
    pd.DataFrame(comparisons).to_csv(
        REPORT / "translated_null_vs_10percent.csv", index=False
    )
    write_json_atomic(
        REPORT / "verification.json",
        dict(
            scientific_status="EXPERIMENTAL",
            shade_mask="NONE",
            output_scale_factor=1000,
            products=products,
            comparison="Common-pixel differences include model refitting; not mask-only removal",
        ),
    )
    print("Completed six unmasked null translations:", REPORT, flush=True)


if __name__ == "__main__":
    run()
