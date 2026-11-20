"""Summarize every frozen shade-excluded refit, retaining unavailable bands.

A VALID aggregate model with NOT_APPLICABLE bands is not a ten-band pass.
This report separates conditional fit support from production/calibration gates.
"""

import json
from pathlib import Path

import pandas as pd
from drone_shade_excluded_refit import DEST, POLICY
from drone_shade_mask_preview import file_sha256
from spectralbridge.bulk.provenance import write_json_atomic


def band_support(model, bands=10):
    fits = model["validation"]["fits"]
    present = {f["band"] for f in fits}
    valid = {
        band
        for band in present
        if all(f["status"] == "VALID" for f in fits if f["band"] == band)
    }
    return dict(
        valid_bands=len(valid),
        full_band_pass=present == set(range(bands)) and len(valid) == bands,
        unavailable_bands=[
            band + 1
            for band in range(bands)
            if not any(
                f["band"] == band and f["status"] != "NOT_APPLICABLE" for f in fits
            )
        ],
        failed_bands=sorted(band + 1 for band in present - valid),
    )


def run():
    rows, details = [], []
    for site in ["ruby", "gordon", "goldhill"]:
        for variant in POLICY["variants"]:
            folder = DEST / site / variant
            if not (folder / "completed.json").exists():
                raise ValueError(f"Incomplete native refit: {site}/{variant}")
            summary = json.loads((folder / "summary.json").read_text())
            topo = json.loads((folder / "conditioned_scsc_model.json").read_text())
            topo_valid = sum(f["status"] == "VALID" for f in topo["fits"])
            for branch in ["brdf_only", "combined"]:
                model = json.loads(
                    next((folder / branch).glob("*brdf_model.json")).read_text()
                )
                support = band_support(model)
                row = dict(
                    site=site,
                    variant=variant,
                    branch=branch,
                    retained_training_pixels=summary["training_pixels"],
                    retained_spatial_pixels=summary["spatial_pixels"],
                    topographic_status=topo["validation_status"],
                    topographic_valid_bands=topo_valid,
                    aggregate_brdf_status=model["validation"]["status"],
                    **support,
                    full_correction_fit_support=support["full_band_pass"]
                    and (branch == "brdf_only" or topo_valid == 10),
                    production_approved=False,
                )
                rows.append(row)
                for f in model["validation"]["fits"]:
                    details.append(
                        dict(
                            site=site,
                            variant=variant,
                            branch=branch,
                            band_1based=f["band"] + 1,
                            wavelength_nm=model["wavelengths_nm"][f["band"]],
                            **{
                                k: f.get(k)
                                for k in [
                                    "status",
                                    "reason",
                                    "eligible",
                                    "reference_prediction",
                                    "reference_standard_error",
                                    "reference_prediction_lower_margin",
                                    "reference_prediction_resolved",
                                    "rejection_components",
                                    "unresolved_observed_geometry_predictions",
                                    "factor_quantiles",
                                ]
                            },
                        )
                    )
    pd.DataFrame(rows).to_csv(DEST / "all_variant_fit_support.csv", index=False)
    pd.DataFrame(details).to_csv(DEST / "all_band_reference_checks.csv", index=False)
    write_json_atomic(
        DEST / "summary_manifest.json",
        dict(
            code_sha256=file_sha256(Path(__file__)),
            outputs={p.name: file_sha256(p) for p in DEST.glob("*.csv")},
            all_variants_reported=True,
            calibration_or_translation_approved=False,
        ),
    )
    print(
        pd.DataFrame(rows)[
            [
                "site",
                "variant",
                "branch",
                "topographic_valid_bands",
                "valid_bands",
                "full_correction_fit_support",
                "unavailable_bands",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    run()
