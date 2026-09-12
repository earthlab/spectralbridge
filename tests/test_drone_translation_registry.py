from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pandas as pd
import pytest
import numpy as np

from spectralbridge.bulk.registry import DEFAULT_PRODUCT_REGISTRY
from spectralbridge.drone_translation import (
    apply_drone_translation,
    load_drone_translation_plans,
    translated_output_stem,
)
from spectralbridge.drone_translation_registry import (
    L5_TM_B3_CAUTION,
    build_drone_translation_coefficient_registry,
    get_drone_translation_coefficient,
    load_drone_translation_coefficients,
    validate_drone_translation_coefficients,
)
from spectralbridge.sensor_pairs import (
    SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY,
    sensor_band_identity,
)
from spectralbridge.envi import hdr_to_dict, memmap_bsq


SOURCE_WAVELENGTHS = [
    444.0,
    475.0,
    531.0,
    560.0,
    650.0,
    668.0,
    705.0,
    717.0,
    740.0,
    842.0,
]


def _write_compact_bulk_fixture(root: Path) -> Path:
    coefficient_rows = []
    summaries = []
    weighting_rows = []
    flightline_rows = []
    site_rows = []
    loso_rows = []
    flag_rows = []
    for pair in DEFAULT_PRODUCT_REGISTRY.translation_pairs:
        for band_index, (source_band, target_band) in enumerate(
            pair.band_pairs, start=1
        ):
            identity = {
                "translation_pair": pair.key,
                "source_sensor": pair.source_sensor,
                "target_sensor": pair.target_sensor,
                "source_band_index": source_band,
                "target_band_index": target_band,
                "band_index": band_index,
            }
            for level, adjustment in (
                ("pixel_pooled", -0.02),
                ("flightline_balanced", -0.01),
                ("site_balanced", 0.0),
            ):
                coefficient_rows.append(
                    {
                        **identity,
                        "analysis_run_id": "bulk-production-fixture",
                        "analysis_level": level,
                        "weighting": f"synthetic fixture {level}",
                        "equation": "target = slope * source + intercept",
                        "status": "ok",
                        "slope": 0.97 + band_index / 1000 + adjustment,
                        "intercept": band_index / 10000,
                        "r2": 0.99,
                        "rmse": 0.01 + band_index / 1000,
                    }
                )
                weighting_rows.append(
                    {
                        **identity,
                        "analysis_level": level,
                        "fitted_correction_percent": 5.0 + band_index,
                    }
                )
            summaries.append(identity)
            flightline_rows.append({**identity, "slope_iqr": 0.02})
            site_rows.append({**identity, "slope_range": 0.03})
            loso_rows.append(
                {
                    **identity,
                    "held_out_r2_min": (
                        0.188
                        if pair.target_sensor == "Landsat_5_TM" and target_band == 3
                        else 0.95
                    ),
                    "held_out_rmse_max": (
                        347.5
                        if pair.target_sensor == "Landsat_5_TM" and target_band == 3
                        else 0.02
                    ),
                    "weakest_held_out_site": (
                        "WREF"
                        if pair.target_sensor == "Landsat_5_TM" and target_band == 3
                        else "NIWO"
                    ),
                }
            )
            if pair.target_sensor == "Landsat_5_TM" and target_band == 3:
                for flag in (
                    "weighting_dependence",
                    "site_dependence",
                    "weak_loso_transferability",
                    "large_fitted_correction",
                ):
                    flag_rows.append({**identity, "flag_code": flag})

    parquet_rows = {
        "coefficients/candidate_translation_coefficients.parquet": coefficient_rows,
        "analyses/bulk_results/pair_band_summary.parquet": summaries,
        "analyses/bulk_results/weighting_comparison.parquet": weighting_rows,
        "analyses/bulk_results/flightline_stability.parquet": flightline_rows,
        "analyses/bulk_results/site_stability.parquet": site_rows,
        "analyses/bulk_results/loso_transferability.parquet": loso_rows,
        "analyses/bulk_results/attention_flags.parquet": flag_rows,
    }
    for relative, rows in parquet_rows.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_parquet(path, index=False)
    summary = root / "analyses/bulk_results/bulk_results_summary.json"
    summary.write_text(
        json.dumps({"bulk_analysis_run_id": "bulk-production-fixture"}),
        encoding="utf-8",
    )
    return root


def _build_registry(tmp_path: Path) -> Path:
    bulk = _write_compact_bulk_fixture(tmp_path / "bulk")
    return build_drone_translation_coefficient_registry(
        bulk,
        tmp_path / "drone_translation_coefficients_v1.json",
    )


def test_registry_builder_uses_exact_site_balanced_rows_and_18_band_contract(
    tmp_path: Path,
) -> None:
    registry_path = _build_registry(tmp_path)
    payload = load_drone_translation_coefficients(registry_path)

    assert payload["record_count"] == 18
    assert payload["production_weighting_strategy"] == "site_balanced"
    assert {row["translation_pair_key"] for row in payload["records"]} == {
        pair.key for pair in DEFAULT_PRODUCT_REGISTRY.translation_pairs
    }
    counts = pd.Series(
        [row["target_sensor"] for row in payload["records"]]
    ).value_counts()
    assert counts.to_dict() == {
        "Landsat_5_TM": 4,
        "Landsat_7_ETM+": 4,
        "Landsat_8_OLI": 5,
        "Landsat_9_OLI-2": 5,
    }
    assert all(row["weighting_strategy"] == "site_balanced" for row in payload["records"])
    assert all(row["evidence_boundary"] == SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY for row in payload["records"])
    assert all(row["source_coefficient_sha256"] for row in payload["records"])

    l5_b3 = get_drone_translation_coefficient(
        "Landsat_5_TM", 3, path=registry_path
    )
    assert l5_b3["source_center_nm"] == 668.0
    assert l5_b3["source_spectral_identity"] == "red"
    assert l5_b3["target_spectral_identity"] == "red"
    assert l5_b3["status"] == "caution"
    assert L5_TM_B3_CAUTION in l5_b3["warnings"]
    assert {
        "weighting_dependence",
        "site_dependence",
        "weak_loso_transferability",
    } <= set(l5_b3["attention_flags"])


def test_registry_mapping_is_wavelength_aware_and_has_no_thermal_band(
    tmp_path: Path,
) -> None:
    payload = load_drone_translation_coefficients(_build_registry(tmp_path))
    by_target = {}
    for row in payload["records"]:
        by_target.setdefault(row["target_sensor"], []).append(row)

    for sensor in ("Landsat_5_TM", "Landsat_7_ETM+"):
        rows = sorted(by_target[sensor], key=lambda row: row["target_band"])
        assert [row["target_band"] for row in rows] == [1, 2, 3, 4]
        assert rows[-1]["source_center_nm"] == 842.0
        assert rows[-1]["target_center_nm"] == 837.5
        assert 6 not in {row["target_band"] for row in rows}
    for sensor in ("Landsat_8_OLI", "Landsat_9_OLI-2"):
        first = min(by_target[sensor], key=lambda row: row["target_band"])
        assert first["target_band"] == 1
        assert first["source_center_nm"] == 444.0
        expected = sensor_band_identity(sensor, 1)
        assert expected is not None
        assert first["target_center_nm"] == expected.wavelength_nm


def test_registry_loader_propagates_caution_and_strict_policy(tmp_path: Path) -> None:
    registry_path = _build_registry(tmp_path)
    plan = load_drone_translation_plans(
        registry_path,
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
        target_sensors=["Landsat_5_TM"],
    )[0]

    assert plan.analysis_level == "site_balanced"
    assert plan.coefficient_set_version == "v1"
    assert [band.native_source_band_index for band in plan.bands] == [2, 4, 6, 10]
    assert [band.target_band_index for band in plan.bands] == [1, 2, 3, 4]
    assert [band.target_spectral_identity for band in plan.bands] == [
        "blue",
        "green",
        "red",
        "near infrared",
    ]
    caution = plan.bands[2]
    assert caution.coefficient_status == "caution"
    assert caution.worst_loso_site == "WREF"
    assert caution.worst_loso_r2 == pytest.approx(0.188)
    assert caution.worst_loso_rmse == pytest.approx(347.5)
    assert L5_TM_B3_CAUTION in caution.coefficient_warnings

    with pytest.raises(ValueError, match="Strict translation policy rejects caution"):
        load_drone_translation_plans(
            registry_path,
            source_wavelengths_nm=SOURCE_WAVELENGTHS,
            target_sensors=["Landsat_5_TM"],
            strict=True,
        )


def test_registry_validation_rejects_duplicate_and_wavelength_conflict(
    tmp_path: Path,
) -> None:
    payload = load_drone_translation_coefficients(_build_registry(tmp_path))
    duplicate = deepcopy(payload)
    duplicate["records"].append(deepcopy(duplicate["records"][0]))
    duplicate["record_count"] = len(duplicate["records"])
    with pytest.raises(ValueError, match="Duplicate/conflicting"):
        validate_drone_translation_coefficients(duplicate)

    wrong_wavelength = deepcopy(payload)
    wrong_wavelength["records"][0]["source_center_nm"] += 10
    with pytest.raises(ValueError, match="Source wavelength conflicts"):
        validate_drone_translation_coefficients(wrong_wavelength)

    wrong_count = deepcopy(payload)
    wrong_count["record_count"] = 17
    with pytest.raises(ValueError, match="record_count does not match"):
        validate_drone_translation_coefficients(wrong_count)

    wrong_provenance = deepcopy(payload)
    wrong_provenance["records"][0]["source_coefficient_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source provenance conflicts"):
        validate_drone_translation_coefficients(wrong_provenance)


def test_registry_reject_status_is_never_applied(tmp_path: Path) -> None:
    payload = load_drone_translation_coefficients(_build_registry(tmp_path))
    rejected = deepcopy(payload)
    rejected["records"][0]["status"] = "reject"
    registry_path = tmp_path / "rejected.json"
    registry_path.write_text(json.dumps(rejected), encoding="utf-8")

    with pytest.raises(ValueError, match="marked reject"):
        load_drone_translation_plans(
            registry_path,
            source_wavelengths_nm=SOURCE_WAVELENGTHS,
        )


def test_registry_builder_stops_when_l5_b3_caution_evidence_is_missing(
    tmp_path: Path,
) -> None:
    bulk = _write_compact_bulk_fixture(tmp_path / "bulk")
    flags_path = bulk / "analyses/bulk_results/attention_flags.parquet"
    flags = pd.read_parquet(flags_path)
    flags = flags.loc[flags["flag_code"] != "weak_loso_transferability"]
    flags.to_parquet(flags_path, index=False)

    with pytest.raises(ValueError, match="does not support the required"):
        build_drone_translation_coefficient_registry(
            bulk,
            tmp_path / "registry.json",
        )


def test_registry_builder_stops_on_cross_table_sensor_conflict(tmp_path: Path) -> None:
    bulk = _write_compact_bulk_fixture(tmp_path / "bulk")
    stability_path = bulk / "analyses/bulk_results/site_stability.parquet"
    stability = pd.read_parquet(stability_path)
    stability.loc[0, "target_sensor"] = "Landsat_9_OLI-2"
    stability.to_parquet(stability_path, index=False)

    with pytest.raises(ValueError, match="sensor identity conflicts"):
        build_drone_translation_coefficient_registry(
            bulk,
            tmp_path / "registry.json",
        )


def test_registry_builder_refuses_missing_compact_outputs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing required registry inputs"):
        build_drone_translation_coefficient_registry(
            tmp_path / "incomplete",
            tmp_path / "registry.json",
        )
    assert not (tmp_path / "registry.json").exists()


def test_production_registry_affine_translation_preserves_native_and_provenance(
    tmp_path: Path,
) -> None:
    registry_path = _build_registry(tmp_path)
    corrected_stem = tmp_path / "flight__corrected"
    source = np.stack(
        [np.full((2, 2), 0.1 + index / 100, dtype=np.float32) for index in range(10)]
    )
    source[1, 0, 0] = -9999.0
    source.tofile(corrected_stem.with_suffix(".img"))
    corrected_stem.with_suffix(".hdr").write_text(
        "\n".join(
            [
                "ENVI",
                "samples = 2",
                "lines = 2",
                "bands = 10",
                "data type = 4",
                "interleave = bsq",
                "byte order = 0",
                "map info = {UTM, 1, 1, 500000, 4400000, 1, 1, 13, North, WGS-84}",
                "projection = EPSG:32613",
                "data ignore value = -9999",
                "wavelength units = Nanometers",
                "wavelength = {" + ", ".join(map(str, SOURCE_WAVELENGTHS)) + "}",
                "fwhm = {28, 32, 14, 27, 16, 14, 10, 12, 18, 57}",
            ]
        ),
        encoding="utf-8",
    )
    corrected_img = corrected_stem.with_suffix(".img")
    corrected_hdr = corrected_stem.with_suffix(".hdr")
    native_before = corrected_img.read_bytes()
    plan = load_drone_translation_plans(
        registry_path,
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
        target_sensors=["Landsat_5_TM"],
    )[0]
    output_stem = translated_output_stem(tmp_path, "flight", "Landsat_5_TM")

    result = apply_drone_translation(
        corrected_img,
        corrected_hdr,
        output_stem=output_stem,
        plan=plan,
    )

    assert corrected_img.read_bytes() == native_before
    header = hdr_to_dict(output_stem.with_suffix(".hdr"))
    translated = memmap_bsq(output_stem.with_suffix(".img"), header)
    assert translated[0, 0, 0] == -9999.0
    valid = source[1] != -9999.0
    expected = plan.bands[0].slope * source[1] + plan.bands[0].intercept
    assert translated[0][valid] == pytest.approx(expected[valid])
    description = " ".join(header["description"])
    assert "target=Landsat_5_TM" in description
    assert "coefficient_set=v1" in description
    assert header["map info"] == hdr_to_dict(corrected_hdr)["map info"]
    assert header["projection"] == hdr_to_dict(corrected_hdr)["projection"]
    assert result["coefficient_set_version"] == "v1"
    assert result["caution_target_bands"] == [3]
    assert L5_TM_B3_CAUTION in result["warnings"]
    assert result["evidence_boundary"] == SYNTHETIC_REGRESSION_EVIDENCE_BOUNDARY
