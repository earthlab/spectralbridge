"""Translate the three frozen conservative refits to OLI/OLI2 at stored ×1000.

Run from the repository root with `.venv/bin/python examples/run_shade_masked_drone_translations.py`.
No source/model/registry is modified. Completed products are reused by signature.
Full-grid arithmetic/mask verification is bounded by 128 image rows. Experimental
source uncertainty is retained; this does not admit products to approved libraries.
"""

import json
from pathlib import Path

import numpy as np

from spectralbridge.drone_translation import (
    apply_drone_translation,
    load_drone_translation_plans,
    translated_output_stem,
)
from spectralbridge.envi import hdr_to_dict, memmap_bsq
from drone_shade_mask_preview import file_sha256

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "archive/local/drone-calibration-translation/2026-11-19"
REPORT = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/translated-products"
)
REGISTRY = (
    REPORT.parent
    / "aop-translation-audit/aop_derived_micasense_to_landsat_fractional_reflectance_registry.json"
)


def run():
    REPORT.mkdir(parents=True, exist_ok=True)
    records = []
    for site in ["ruby", "gordon", "goldhill"]:
        source = next(
            (BASE / "conservative-refitted-products" / site).glob("*EXPERIMENTAL.img")
        )
        header = source.with_suffix(".hdr")
        before = {str(p): file_sha256(p) for p in [source, header]}
        hdr = hdr_to_dict(header)
        native = memmap_bsq(source, hdr)
        plans = load_drone_translation_plans(
            REGISTRY,
            source_wavelengths_nm=hdr["wavelength"],
            target_sensors=["Landsat_8_OLI", "Landsat_9_OLI-2"],
        )
        application = json.loads(
            (
                REPORT.parent
                / "conservative-refitted-products"
                / site
                / "application_complete.json"
            ).read_text()
        )
        run_metadata = {
            "site": site,
            "acquisition_date": "2023-08-14",
            "correction_order": "SCS+C topographic then combined BRDF",
            "shade_mask_policy": "conservative pre-correction visible brightness below 0.10 of source p95 excluded",
            "shade_mask_values": "0 keep; 1 excluded; 255 source nodata",
            "source_application_identity": application["identity"],
            "source_corrected_outputs_sha256": application["outputs"],
            "scientific_validation_status": "EXPERIMENTAL",
            "production_approved": False,
        }
        for plan in plans:
            print(f"{site}: translating {plan.target_sensor}", flush=True)
            stem = translated_output_stem(
                BASE / "translated-products" / site,
                f"{site}_20230814",
                plan.target_sensor,
                naming_style="micasense",
            )
            result = apply_drone_translation(
                source,
                header,
                output_stem=stem,
                plan=plan,
                experimental_input=True,
                experimental_input_provenance=(
                    "2026-11-19 original/prepared 30-band scale-chain audit; "
                    "72 original AOP training headers establish scale10000; "
                    "derived fractional registry preserves fit evidence; conservative "
                    "shade-excluded SCS+C/BRDF refits independently checked. "
                    "Conditional original DN/32768 calibration, not independent physical validation. "
                    "Source header omits BRDF schema; saved schema2 models verified in application_complete.json."
                ),
                output_scale_factor=1000,
                translation_metadata=run_metadata,
                chunk_lines=128,
            )
            out_hdr = hdr_to_dict(Path(result["output_hdr"]))
            embedded = json.loads(out_hdr["translation metadata"][5:])
            assert embedded["run_metadata"] == run_metadata
            assert embedded["output_scale_factor"] == 1000
            out = memmap_bsq(Path(result["output_img"]), out_hdr)
            assert out_hdr["scientific validation status"] == "EXPERIMENTAL"
            assert out_hdr["physical reflectance multiplier"] == 0.001
            for key in ["lines", "samples", "map info", "projection"]:
                assert hdr[key] == out_hdr[key]
            counts = []
            for index, band in enumerate(plan.bands):
                count = 0
                for start in range(0, int(hdr["lines"]), 128):
                    values = np.asarray(
                        native[band.native_source_band_index - 1, start : start + 128]
                    )
                    observed = np.asarray(out[index, start : start + 128])
                    expected = (
                        (
                            values * np.float32(hdr["physical reflectance multiplier"])
                            + np.float32(hdr["physical reflectance offset"])
                        )
                        * np.float32(band.slope)
                        + np.float32(band.intercept)
                    ) * np.float32(1000)
                    np.testing.assert_array_equal(
                        np.isfinite(values), np.isfinite(observed)
                    )
                    np.testing.assert_allclose(
                        observed, expected, rtol=1e-6, atol=1e-4, equal_nan=True
                    )
                    count += int(np.isfinite(observed).sum())
                counts.append(count)
            assert (
                apply_drone_translation(
                    source,
                    header,
                    output_stem=stem,
                    plan=plan,
                    experimental_input=True,
                    experimental_input_provenance=result[
                        "experimental_input_provenance"
                    ],
                    output_scale_factor=1000,
                    translation_metadata=run_metadata,
                )["status"]
                == "reused"
            )
            legacy_stem = translated_output_stem(
                BASE / "translated-products" / site,
                source.stem + "__scale1000",
                plan.target_sensor,
            )
            image_sha256 = file_sha256(Path(result["output_img"]))
            legacy_match = None
            if legacy_stem.with_suffix(".img").is_file():
                legacy_match = image_sha256 == file_sha256(
                    legacy_stem.with_suffix(".img")
                )
                assert legacy_match
            records.append(
                dict(
                    site=site,
                    target=plan.target_sensor,
                    status=result["status"],
                    output_img=result["output_img"],
                    output_hdr=result["output_hdr"],
                    provenance_json=result["provenance_json"],
                    valid_pixels_by_band=counts,
                    sha256={
                        str(p): file_sha256(p)
                        for p in [
                            Path(result["output_img"]),
                            Path(result["output_hdr"]),
                            Path(result["provenance_json"]),
                        ]
                    },
                    legacy_raster_bytes_unchanged=legacy_match,
                    full_grid_arithmetic_and_masks="PASS",
                    restart="PASS",
                    band_mapping=[b.native_source_band_index for b in plan.bands],
                )
            )
            print(
                f"{site}: {plan.target_sensor} verified all pixels, restart and hashes",
                flush=True,
            )
        assert before == {p: file_sha256(Path(p)) for p in before}
    (REPORT / "verification.json").write_text(
        json.dumps(
            dict(
                registry=str(REGISTRY),
                registry_sha256=file_sha256(REGISTRY),
                output_scale_factor=1000,
                scientific_status="EXPERIMENTAL",
                products=records,
            ),
            indent=2,
        )
        + "\n"
    )
    print(f"Completed {len(records)} translated products: {REPORT}", flush=True)


if __name__ == "__main__":
    run()
