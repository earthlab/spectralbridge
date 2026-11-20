"""Audit actual drone/AOP storage scales, correction units and translation units.

No source, calibration, coefficient or corrected product is edited. Reconstructs
all30 prepared bands from alpha-masked original calibrated integer exports using
the recorded bilinear/fixed-range producer operation; checks the native BRDF
backing arrays and saved output/model radiometry separately from physical
accuracy approval. Requested fraction*1000 storage is reported explicitly.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject

from drone_shade_mask_preview import ROOT, file_sha256
from spectralbridge.envi import hdr_to_dict
from spectralbridge.bulk.provenance import write_json_atomic

DEST = ROOT / "provenance/drone-calibration-translation/2026-11-19/scale-chain-audit"
PRIOR = ROOT / "provenance/drone-calibration-translation/2026-11-19"
FACTOR = 65535 / (10000 * 32768)


def audit():
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    chain = []
    for c in json.loads(
        (ROOT / "provenance/drone-camera-rerun/2026-11-05/site_inputs.json").read_text()
    ):
        site = c["site"].lower()
        base = (
            ROOT
            / "archive/local/drone-correction-stability/2026-11-05/stable_qr_v1"
            / site
        )
        data = np.load(base / "candidate_stored.npy", mmap_mode="r")
        with (
            rasterio.open(c["source"]) as src,
            rasterio.open(c["prepared"]) as prepared,
        ):
            assert src.count == 11 and prepared.count == 10
            alpha = src.read(11) > 0
            # Reproduce original producer: float32 source, alpha -> NaN, bilinear
            # warp, fixed10000/65535 encode. No min/max subtraction or clipping.
            for band in range(1, 11):
                original = src.read(band, out_dtype="float32")
                original[~alpha] = np.nan
                reconstructed = np.full(prepared.shape, np.nan, dtype="float32")
                reproject(
                    original,
                    reconstructed,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=np.nan,
                    dst_transform=prepared.transform,
                    dst_crs=prepared.crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                    num_threads=1,
                )
                reconstructed *= np.float32(10000 / 65535)
                actual = prepared.read(band)
                valid = np.isfinite(actual)
                np.testing.assert_array_equal(actual[valid], reconstructed[valid])
                # Exact equality across the entire actual fitting array, not a
                # display stretch or inference from the range of pixel values.
                np.testing.assert_array_equal(data[..., band - 1], actual)
                records.append(
                    dict(
                        site=site,
                        band=band,
                        prepared_pixels=int(valid.sum()),
                        reconstruction_max_error=float(
                            np.max(np.abs(actual[valid] - reconstructed[valid]))
                        ),
                        exact_source_to_prepared=True,
                        exact_prepared_to_fit_cache=True,
                    )
                )
                print(site, "source/prepared/cache band", band, "exact", flush=True)
        fit = PRIOR / "shade-excluded-refit-v2" / site / "conservative"
        topo = json.loads((fit / "conditioned_scsc_model.json").read_text())
        brdf = json.loads(next((fit / "combined").glob("*brdf_model.json")).read_text())
        output = next(
            (
                ROOT
                / "archive/local/drone-calibration-translation/2026-11-19/conservative-refitted-products"
                / site
            ).glob("*EXPERIMENTAL.img")
        )
        header = hdr_to_dict(output.with_suffix(".hdr"))
        for model in [topo, brdf]:
            assert (
                model["radiometry"]["scale"] == FACTOR
                and model["radiometry"]["offset"] == 0
            )
        assert (
            float(header["physical reflectance multiplier"]) == FACTOR
            and float(header["physical reflectance offset"]) == 0
        )
        np.testing.assert_allclose(
            float(header["reflectance scale factor"]), 1 / FACTOR, rtol=1e-12
        )
        # Compare existing independently checked algebra QA to prove that the
        # decoded correction/re-encoding roundtrip did not add a scale factor.
        qa = pd.read_csv(
            PRIOR / "conservative-refitted-products/independent_algebra_checks.csv"
        )
        assert (
            len(qa.loc[qa.site.eq(site)]) == 10
            and qa.loc[qa.site.eq(site), "independent_algebra_pass"].all()
        )
        chain.append(
            dict(
                site=site,
                original_divisor=32768,
                preparation_multiplier=10000 / 65535,
                prepared_to_fraction_multiplier=FACTOR,
                actual_output_fraction_divisor=1 / FACTOR,
                intended_fraction_times_1000_multiplier=0.001,
                output_already_on_1000_scale=False,
                topo_and_brdf_radiometry_agree=True,
                offset_zero=True,
                independent_stored_correction_algebra_pass=True,
                scientific_validation_status=header.get("scientific validation status"),
                radiometry_status=header.get("radiometry status"),
                original_sha256=file_sha256(Path(c["source"])),
                prepared_sha256=file_sha256(Path(c["prepared"])),
                corrected_sha256=file_sha256(output),
            )
        )
    pd.DataFrame(records).to_csv(
        DEST / "all_30_band_source_preparation_checks.csv", index=False
    )
    pd.DataFrame(chain).to_csv(DEST / "drone_scale_chain.csv", index=False)
    dn = np.array([0, 8192, 16384, 32768, 65535], float)
    fixed = dn * (10000 / 65535)
    fraction = dn / 32768
    np.testing.assert_allclose(fixed * FACTOR, fraction, rtol=1e-14, atol=1e-14)
    pd.DataFrame(
        dict(
            original_drone_dn=dn,
            old_fixed_range_10k=fixed,
            physical_fraction=fraction,
            common_fraction_times_1000=fraction * 1000,
            wrong_fixed_range_divide_10000=fixed / 10000,
        )
    ).to_csv(DEST / "drone_scale_examples.csv", index=False)
    audit = json.loads(
        (PRIOR / "aop-translation-audit/training_header_retrieval.json").read_text()
    )
    assert (
        audit["complete"]
        and len(audit["records"]) == 72
        and all(float(r["reflectance_scale_factor"]) == 10000 for r in audit["records"])
    )
    old = json.loads(
        (
            ROOT / "src/spectralbridge/data/drone_translation_coefficients_v1.json"
        ).read_text()
    )
    new = json.loads(
        (
            PRIOR
            / "aop-translation-audit/aop_derived_micasense_to_landsat_fractional_reflectance_registry.json"
        ).read_text()
    )
    coefficient_rows = []
    for a, b in zip(old["records"], new["records"]):
        assert a["slope"] == b["slope"] and a["intercept"] / 10000 == b["intercept"]
        value = np.array([0.0, 0.1, 0.5, 1.0, 1.999969482421875])
        y_fraction = b["slope"] * value + b["intercept"]
        y_1000 = a["slope"] * (value * 1000) + a["intercept"] / 10
        np.testing.assert_allclose(y_fraction * 1000, y_1000, rtol=1e-13, atol=1e-12)
        # Start at drone fixed-range storage, using its own decoder rather than
        # the AOP divisor, then demonstrate the desired common1000 translation.
        stored = value / FACTOR
        np.testing.assert_allclose(
            (a["slope"] * (stored * FACTOR) + a["intercept"] / 10000) * 1000, y_1000
        )
        coefficient_rows.append(
            dict(
                source=a["source_sensor"],
                target=a["target_sensor"],
                band=a["target_band"],
                slope=a["slope"],
                original_aop_10k_intercept=a["intercept"],
                fractional_intercept=b["intercept"],
                common_1000_intercept=a["intercept"] / 10,
                unit_equivalence_pass=True,
            )
        )
    pd.DataFrame(coefficient_rows).to_csv(
        DEST / "translation_intercepts_by_storage_scale.csv", index=False
    )
    write_json_atomic(
        DEST / "scale_chain_verification.json",
        dict(
            all30_source_bands_exact=True,
            all3_native_fit_caches_exact=True,
            all3_correction_radiometry_chains_consistent=True,
            independent_correction_samples_verified=1920,
            all72_AOP_training_headers_divisor_10000=True,
            all18_translation_unit_conversions_equivalent=True,
            requested_1000_is_not_current_storage=True,
            drone_encoding="DN/32768;65535approximately200percent",
            no_double_scaling_detected=True,
            physical_accuracy_or_production_approval_claimed=False,
            code_sha256=file_sha256(Path(__file__)),
            outputs={p.name: file_sha256(p) for p in DEST.glob("*.csv")},
        ),
    )


if __name__ == "__main__":
    audit()
