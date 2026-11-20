"""Independent algebra spot checks for newly applied conservative corrections."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from drone_apply_conservative_refits import OUTPUT, EVIDENCE
from drone_shade_excluded_refit import DEST, BASE
from drone_shade_mask_preview import file_sha256
from spectralbridge.bulk.provenance import write_json_atomic


def run():
    rows = []
    for site in ["ruby", "gordon", "goldhill"]:
        application = json.loads(
            (EVIDENCE / site / "application_complete.json").read_text()
        )
        stem = next((OUTPUT / site).glob("*EXPERIMENTAL.img"))
        for suffix, digest in application["outputs"].items():
            if file_sha256(stem.with_suffix(suffix)) != digest:
                raise ValueError("Changed raster/header")
        topo = json.loads(
            (DEST / site / "conservative/conditioned_scsc_model.json").read_text()
        )
        brdf = json.loads(
            next(
                (DEST / site / "conservative/combined").glob("*brdf_model.json")
            ).read_text()
        )
        contract = json.loads((DEST / site / "input_contract.json").read_text())
        raw = np.load(BASE / site / "candidate_stored.npy", mmap_mode="r")
        design = np.load(BASE / site / "center_design.npy", mmap_mode="r")
        # Ancillary locations are retained in the original site configuration.
        configs = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "provenance/drone-camera-rerun/2026-11-05/site_inputs.json"
            ).read_text()
        )
        config = next(c for c in configs if c["site"].lower() == site)
        solar = np.load(config["solar_arrays"], mmap_mode="r")
        with rasterio.open(config["terrain_ancillary"]["slope"]) as ds:
            slope = ds.read(1)
        with rasterio.open(config["terrain_ancillary"]["aspect"]) as ds:
            aspect = ds.read(1)
        with rasterio.open(stem) as product:
            for band in range(10):
                values = product.read(band + 1)
                eligible = np.flatnonzero(np.isfinite(values))
                indices = eligible[np.linspace(0, len(eligible) - 1, 64, dtype=int)]
                rr, cc = np.unravel_index(indices, values.shape)
                slope_r = np.deg2rad(slope[rr, cc].astype(np.float32))
                aspect_r = np.deg2rad(aspect[rr, cc].astype(np.float32))
                sz = np.deg2rad(solar[rr, cc, 0].astype(np.float32))
                sa = np.deg2rad(solar[rr, cc, 1].astype(np.float32))
                incidence = np.cos(sz) * np.cos(slope_r) + np.sin(sz) * np.sin(
                    slope_r
                ) * np.cos(sa - aspect_r)
                reference = np.cos(sz) * np.cos(slope_r)
                C = topo["fits"][band]["C"]
                topographic_gain = (reference + C) / (incidence + C)
                beta = np.array([brdf[key][0][band] for key in ["iso", "vol", "geo"]])
                directional = np.asarray(design[rr, cc], float) @ beta
                nadir = np.array(brdf["reference_design"]) @ beta
                expected = (
                    np.asarray(raw[rr, cc, band], float)
                    * topographic_gain
                    * (nadir / directional)
                )
                observed = values[rr, cc]
                np.testing.assert_allclose(observed, expected, rtol=1e-4, atol=1e-4)
                rows.append(
                    dict(
                        site=site,
                        band_1based=band + 1,
                        samples=len(rr),
                        maximum_relative_error=float(
                            np.max(
                                np.abs(observed - expected)
                                / np.maximum(np.abs(expected), 1e-12)
                            )
                        ),
                        independent_algebra_pass=True,
                    )
                )
        if (
            file_sha256(next((BASE / site).glob("*experimental_candidate.img")))
            != application["identity"]["raw_sha256"]
        ):
            raise ValueError("Original input changed")
        assert contract["fit_settings"]["kernel_config"] == brdf["kernel_config"]
    pd.DataFrame(rows).to_csv(EVIDENCE / "independent_algebra_checks.csv", index=False)
    write_json_atomic(
        EVIDENCE / "verification.json",
        dict(
            checked_sites=3,
            checked_bands=30,
            independent_samples=1920,
            all_pass=True,
            rtol=1e-4,
            atol=1e-4,
            output_hashes_match=True,
            original_inputs_unchanged=True,
            code_sha256=file_sha256(Path(__file__)),
        ),
    )
    print(
        "Independent algebra: 1920 samples across30 bands/3sites pass; source/output hashes verified."
    )


if __name__ == "__main__":
    run()
