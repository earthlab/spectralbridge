"""Independent original-value × SCS+C × diagnostic-BRDF checks for null outputs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from drone_shade_mask_preview import file_sha256
from run_unmasked_drone_translation_null import OUT, REPORT, refit


def run():
    rows = []
    for site in ["ruby", "gordon", "goldhill"]:
        completed = json.loads((REPORT / site / "native_complete.json").read_text())
        for group in [completed["identity"]["inputs"], completed["outputs"]]:
            for p, digest in group.items():
                assert file_sha256(Path(p)) == digest
        models = refit.DEST / site / "baseline"
        topo = json.loads((models / "conditioned_scsc_model.json").read_text())
        brdf = json.loads(
            next((models / "combined").glob("*brdf_model.json")).read_text()
        )
        raw = np.load(refit.BASE / site / "candidate_stored.npy", mmap_mode="r")
        design = np.load(refit.BASE / site / "center_design.npy", mmap_mode="r")
        config = next(
            c
            for c in json.loads((refit.PRIOR / "site_inputs.json").read_text())
            if c["site"].lower() == site
        )
        solar = np.load(config["solar_arrays"], mmap_mode="r")
        with rasterio.open(config["terrain_ancillary"]["slope"]) as ds:
            slope = ds.read(1)
        with rasterio.open(config["terrain_ancillary"]["aspect"]) as ds:
            aspect = ds.read(1)
        with rasterio.open(
            next((OUT / site).glob("*corrected_micasense_envi.img"))
        ) as ds:
            for band in range(10):
                values = ds.read(band + 1)
                eligible = np.flatnonzero(np.isfinite(values))
                points = eligible[np.linspace(0, len(eligible) - 1, 64, dtype=int)]
                rr, cc = np.unravel_index(points, values.shape)
                sl = np.deg2rad(slope[rr, cc].astype(np.float32))
                asp = np.deg2rad(aspect[rr, cc].astype(np.float32))
                sz = np.deg2rad(solar[rr, cc, 0].astype(np.float32))
                sa = np.deg2rad(solar[rr, cc, 1].astype(np.float32))
                ci = np.cos(sz) * np.cos(sl) + np.sin(sz) * np.sin(sl) * np.cos(
                    sa - asp
                )
                reference = np.cos(sz) * np.cos(sl)
                C = topo["fits"][band]["C"]
                fit = next(
                    f
                    for f in brdf["validation"]["fits"]
                    if f["band"] == band and f["bin"] == 0
                )
                beta = np.asarray(fit["diagnostic_coefficient_estimate"])
                expected = (
                    np.asarray(raw[rr, cc, band], float)
                    * (reference + C)
                    / (ci + C)
                    * (np.asarray(brdf["reference_design"]) @ beta)
                    / (np.asarray(design[rr, cc], float) @ beta)
                )
                np.testing.assert_allclose(
                    values[rr, cc], expected, rtol=1e-4, atol=1e-4
                )
                rows.append(
                    dict(
                        site=site,
                        band_1based=band + 1,
                        independent_samples=64,
                        original_fit_status=fit["status"],
                        algebra="PASS",
                    )
                )
    # Confirm every existing 10% reference artifact is unchanged.
    masked = json.loads(
        (REPORT.parent / "translated-products/verification.json").read_text()
    )
    for product in masked["products"]:
        for p, digest in product["sha256"].items():
            assert file_sha256(Path(p)) == digest
    result = json.loads((REPORT / "verification.json").read_text())
    for product in result["products"]:
        for p, digest in product["sha256"].items():
            assert file_sha256(Path(p)) == digest
        with rasterio.open(product["output_img"]) as ds:
            tags = ds.tags(ns="ENVI")
            assert tags["scientific_validation_status"] == "EXPERIMENTAL"
            assert tags["brdf_status"] == product["brdf_status"]
            assert float(tags["physical_reflectance_multiplier"]) == 0.001
            assert (
                tags["translation_shade_mask_policy"] == "NONE; no brightness exclusion"
            )
    pd.DataFrame(rows).to_csv(REPORT / "independent_algebra_checks.csv", index=False)
    result.update(
        independent_native_samples=1920,
        independent_native_algebra="PASS",
        masked_reference_hashes_unchanged=True,
        gdal_metadata="PASS",
    )
    (REPORT / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "1920 independent native algebra checks; null hashes, masked references and GDAL metadata PASS."
    )


if __name__ == "__main__":
    run()
