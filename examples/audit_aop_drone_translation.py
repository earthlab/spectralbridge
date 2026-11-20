"""Verify the archived AOP-derived MicaSense-like -> Landsat translation chain.

Reads compact sufficient statistics and exact coefficient artifacts only. No
rasters, coefficient values, unit declarations or production guards are changed.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from spectralbridge.bulk.analyses.streaming_translation import (
    _merge,
    _merge_normalized,
    _fit,
)
from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.drone_translation_registry import (
    packaged_drone_translation_coefficients_path,
)
from drone_shade_mask_preview import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "archive/research/bulk-calibration"
DEST = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/aop-translation-audit"
)


def run():
    DEST.mkdir(parents=True, exist_ok=True)
    original = json.loads(packaged_drone_translation_coefficients_path().read_text())
    reproduced = json.loads((DEST / "reproduced_registry.json").read_text())
    frame = pd.read_parquet(SOURCE / "candidate_translation_coefficients.parquet-2")
    moments = pd.read_parquet(SOURCE / "translation_sufficient_statistics.parquet-2")
    checks = []
    for record in original["records"]:
        pair = record["translation_pair_key"]
        band = record["band_index"]
        same = next(
            r
            for r in reproduced["records"]
            if r["translation_pair_key"] == pair and r["band_index"] == band
        )
        assert (
            same["slope"] == record["slope"]
            and same["intercept"] == record["intercept"]
        )
        selected = frame.loc[
            frame.translation_pair.eq(pair)
            & frame.band_index.eq(band)
            & frame.analysis_level.eq("site_balanced")
        ]
        assert len(selected) == 1
        candidate = selected.iloc[0]
        assert (
            candidate.source_sensor == record["source_sensor"]
            and candidate.target_sensor == record["target_sensor"]
        )
        assert (
            candidate.slope == record["slope"]
            and candidate.intercept == record["intercept"]
        )
        m = moments.loc[moments.translation_pair.eq(pair) & moments.band_index.eq(band)]
        # The same stable merging implementation used by production. All archived
        # moments are reaggregated; no coefficient is copied into this calculation.
        sites = [_merge(g.to_dict("records")) for _, g in m.groupby("site", sort=True)]
        slope, intercept, _ = _fit(_merge_normalized(sites))
        np.testing.assert_allclose(
            [slope, intercept],
            [record["slope"], record["intercept"]],
            rtol=1e-10,
            atol=1e-10,
        )
        checks.append(
            dict(
                source_sensor=record["source_sensor"],
                target_sensor=record["target_sensor"],
                source_band=record["source_band"],
                source_center_nm=record["source_center_nm"],
                target_band=record["target_band"],
                target_center_nm=record["target_center_nm"],
                equation="target = slope * source + intercept",
                slope=record["slope"],
                intercept_stored_units=record["intercept"],
                moment_recomputed_slope=slope,
                moment_recomputed_intercept=intercept,
                exact_registry_and_candidate_match=True,
                moment_fit_agrees=True,
                flightlines=m.flightline_id.nunique(),
                sites=m.site.nunique(),
                candidate_unit_field_present="reflectance_units" in selected.columns,
                registry_reflectance_units=record.get("reflectance_units"),
            )
        )
    pd.DataFrame(checks).to_csv(DEST / "coefficient_chain_checks.csv", index=False)
    manifest = json.loads((SOURCE / "bulk_manifest.json").read_text())
    files = manifest["input_signature"]["catalog"]["source_files"]
    pd.DataFrame(
        [
            {
                k: r.get(k)
                for k in [
                    "canonical_flightline_id",
                    "site",
                    "sensor_name",
                    "relative_path",
                    "header_path",
                    "source_signature_sha256",
                ]
            }
            for r in files
        ]
    ).to_csv(DEST / "training_product_inventory.csv", index=False)
    metadata = {}
    for name in [
        "candidate_translation_coefficients.parquet-2",
        "translation_sufficient_statistics.parquet-2",
        "site_balanced.parquet",
    ]:
        schema = pq.read_schema(SOURCE / name)
        metadata[name] = dict(
            columns=list(schema.names),
            metadata_keys=[
                k.decode() for k in (schema.metadata or {}) if k != b"pandas"
            ],
        )
    write_json_atomic(
        DEST / "audit_results.json",
        dict(
            analysis_run_id=original["bulk_analysis_run_id"],
            training_sites=sorted(moments.site.unique()),
            training_flightlines=int(moments.flightline_id.nunique()),
            selected_observations=manifest["counts"]["accepted_rows"],
            source_sensor_products=len(files),
            verified_coefficient_rows=len(checks),
            orientation_verified=True,
            exact_registry_reproduction=True,
            stable_moment_recomputation_matches=True,
            intended_relationship="AOP-derived MicaSense-passband proxy predicts AOP-derived Landsat-passband response; apply that response mapping to corrected MicaSense within its evidence/domain limits",
            physical_unit_metadata_missing_at="original compact coefficient/moment artifacts, not solely registry import",
            archived_parquet_metadata=metadata,
            coefficient_values_changed=False,
            units_inferred_from_magnitudes=False,
            code_sha256=file_sha256(Path(__file__)),
            source_sha256={
                name: file_sha256(SOURCE / name)
                for name in [
                    "bulk_manifest.json",
                    "candidate_translation_coefficients.parquet-2",
                    "translation_sufficient_statistics.parquet-2",
                ]
            },
            outputs={p.name: file_sha256(p) for p in DEST.glob("*.csv")},
        ),
    )
    print(
        "All18 registry rows match exact archived candidates and recreated site-balanced moment fits."
    )
    print(
        pd.DataFrame(checks)
        .loc[
            lambda x: x.target_sensor.eq("Landsat_9_OLI-2"),
            ["source_center_nm", "target_band", "slope", "intercept_stored_units"],
        ]
        .to_string(index=False)
    )


if __name__ == "__main__":
    run()
