from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from spectralbridge.drone_translation import (
    TRANSLATION_EQUATION,
    apply_drone_translation,
    load_drone_translation_plans,
    translated_output_stem,
)
from spectralbridge.envi import hdr_to_dict, memmap_bsq


SOURCE_SENSOR = "MicaSense_to-match_OLI_and_OLI-2"
TARGET_SENSOR = "Landsat_8_OLI"
PAIR = f"{SOURCE_SENSOR}__to__{TARGET_SENSOR}"
SOURCE_WAVELENGTHS = [444.0, 475.0, 531.0, 560.0, 650.0, 668.0, 705.0, 717.0, 740.0, 862.0]


def _coefficient_rows() -> list[dict[str, object]]:
    return [
        {
            "analysis_run_id": "bulk-run-1",
            "analysis_level": "site_balanced",
            "weighting": "each site has equal total weight",
            "translation_pair": PAIR,
            "source_sensor": SOURCE_SENSOR,
            "target_sensor": TARGET_SENSOR,
            "source_band_index": index,
            "target_band_index": index,
            "band_index": index,
            "equation": TRANSLATION_EQUATION,
            "status": "ok",
            "slope": 1.0 + index / 10.0,
            "intercept": index / 100.0,
            "x_min": 0.0,
            "x_max": 1.0,
            "x_mean": 0.3,
            "r2": 0.99,
        }
        for index in range(1, 6)
    ]


def _write_coefficients(path: Path, rows: list[dict[str, object]] | None = None) -> Path:
    rows = rows or _coefficient_rows()
    pd.DataFrame(rows).to_parquet(path, index=False)
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "analysis_run_id": "bulk-run-1",
                "equation": TRANSLATION_EQUATION,
                "candidate_status": "review_required",
                "translation_pairs": [
                    {
                        "key": PAIR,
                        "source_sensor": SOURCE_SENSOR,
                        "target_sensor": TARGET_SENSOR,
                        "evidence_boundary": "synthetic same-source evidence",
                    }
                ],
                "candidate_coefficients": rows,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_corrected_envi(stem: Path) -> tuple[Path, Path, np.ndarray]:
    data = np.stack(
        [
            np.full((2, 3), 0.1 + band / 100.0, dtype=np.float32)
            for band in range(10)
        ]
    )
    data[0, 0, 0] = -9999.0
    data.tofile(stem.with_suffix(".img"))
    stem.with_suffix(".hdr").write_text(
        "\n".join(
            [
                "ENVI",
                "samples = 3",
                "lines = 2",
                "bands = 10",
                "data type = 4",
                "interleave = bsq",
                "byte order = 0",
                "map info = {UTM, 1, 1, 500000, 4400000, 1, 1, 13, North, WGS-84}",
                "projection = EPSG:32613",
                "wavelength units = Nanometers",
                "reflectance scale factor = 1",
                "data ignore value = -9999",
                "fwhm = {28, 32, 14, 27, 16, 14, 10, 12, 18, 57}",
                "wavelength = {" + ", ".join(str(value) for value in SOURCE_WAVELENGTHS) + "}",
            ]
        ),
        encoding="utf-8",
    )
    return stem.with_suffix(".img"), stem.with_suffix(".hdr"), data


def test_loader_selects_explicit_weighting_and_maps_by_wavelength(tmp_path: Path) -> None:
    coefficients = _write_coefficients(tmp_path / "candidate_translation_coefficients.parquet")
    plans = load_drone_translation_plans(
        coefficients,
        weighting="site-balanced",
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )

    assert len(plans) == 1
    plan = plans[0]
    assert plan.analysis_level == "site_balanced"
    assert plan.source_sensor == SOURCE_SENSOR
    assert plan.target_sensor == TARGET_SENSOR
    assert [band.native_source_band_index for band in plan.bands] == [1, 2, 4, 6, 10]
    assert [band.target_wavelength_nm for band in plan.bands] == pytest.approx(
        [443.0, 482.0, 561.4, 654.6, 864.7]
    )
    assert plan.evidence_boundary == "synthetic same-source evidence"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda rows: rows.__setitem__(slice(4, 5), []), "incomplete or unexpected"),
        (lambda rows: rows.append(dict(rows[0])), "Duplicate"),
        (lambda rows: rows[0].__setitem__("source_sensor", "MicaSense"), "orientation"),
        (lambda rows: rows[0].__setitem__("target_sensor", "Landsat_9_OLI-2"), "orientation"),
        (lambda rows: rows[0].__setitem__("equation", "source = slope * target + intercept"), "equation"),
        (lambda rows: rows[0].__setitem__("slope", float("nan")), "Non-finite"),
    ],
)
def test_loader_rejects_invalid_or_ambiguous_coefficients(
    tmp_path: Path, mutation, message: str
) -> None:
    rows = _coefficient_rows()
    mutation(rows)
    coefficients = _write_coefficients(tmp_path / "coefficients.parquet", rows)
    with pytest.raises(ValueError, match=message):
        load_drone_translation_plans(
            coefficients,
            weighting="site_balanced",
            source_wavelengths_nm=SOURCE_WAVELENGTHS,
        )


def test_loader_requires_available_explicit_weighting(tmp_path: Path) -> None:
    coefficients = _write_coefficients(tmp_path / "coefficients.parquet")
    with pytest.raises(ValueError, match="no rows for weighting"):
        load_drone_translation_plans(
            coefficients,
            weighting="flightline_balanced",
            source_wavelengths_nm=SOURCE_WAVELENGTHS,
        )
    with pytest.raises(ValueError, match="must be one of"):
        load_drone_translation_plans(
            coefficients,
            weighting="automatic",
            source_wavelengths_nm=SOURCE_WAVELENGTHS,
        )


def test_loader_rejects_wavelength_mismatch(tmp_path: Path) -> None:
    coefficients = _write_coefficients(tmp_path / "coefficients.parquet")
    with pytest.raises(ValueError, match="No drone band matches"):
        load_drone_translation_plans(
            coefficients,
            weighting="site_balanced",
            source_wavelengths_nm=[1000, 1100, 1200, 1300, 1400],
        )


def test_apply_translation_is_exact_preserves_nodata_native_and_restarts(
    tmp_path: Path,
) -> None:
    coefficients = _write_coefficients(tmp_path / "coefficients.parquet")
    corrected_img, corrected_hdr, native = _write_corrected_envi(tmp_path / "flight__corrected")
    native_before = corrected_img.read_bytes()
    plan = load_drone_translation_plans(
        coefficients,
        weighting="site_balanced",
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    output_stem = translated_output_stem(tmp_path, "flight", TARGET_SENSOR)

    created = apply_drone_translation(
        corrected_img,
        corrected_hdr,
        output_stem=output_stem,
        plan=plan,
    )
    header = hdr_to_dict(output_stem.with_suffix(".hdr"))
    translated = memmap_bsq(output_stem.with_suffix(".img"), header)

    assert created["status"] == "created"
    assert created["is_actual_landsat_observation"] is False
    assert created["spectralbridge_version"]
    assert created["coefficient_sha256"]
    assert corrected_img.read_bytes() == native_before
    assert translated[0, 0, 0] == -9999.0
    source_indices = [0, 1, 3, 5, 9]
    for output_index, source_index in enumerate(source_indices, start=1):
        expected = (1.0 + output_index / 10.0) * native[source_index] + output_index / 100.0
        valid = native[source_index] != -9999.0
        assert translated[output_index - 1][valid] == pytest.approx(expected[valid])
    output_mtime = output_stem.with_suffix(".img").stat().st_mtime_ns
    reused = apply_drone_translation(
        corrected_img,
        corrected_hdr,
        output_stem=output_stem,
        plan=plan,
    )
    assert reused["status"] == "reused"
    assert output_stem.with_suffix(".img").stat().st_mtime_ns == output_mtime


def test_apply_translation_rejects_nonoverlapping_training_range(tmp_path: Path) -> None:
    rows = _coefficient_rows()
    for row in rows:
        row["x_min"] = 100.0
        row["x_max"] = 200.0
    coefficients = _write_coefficients(tmp_path / "coefficients.parquet", rows)
    corrected_img, corrected_hdr, _ = _write_corrected_envi(tmp_path / "flight__corrected")
    plan = load_drone_translation_plans(
        coefficients,
        weighting="site_balanced",
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    output_stem = translated_output_stem(tmp_path, "flight", TARGET_SENSOR)
    with pytest.raises(ValueError, match="reflectance units/scale"):
        apply_drone_translation(
            corrected_img,
            corrected_hdr,
            output_stem=output_stem,
            plan=plan,
        )
    assert not output_stem.with_suffix(".img").exists()
    assert not output_stem.with_suffix(".hdr").exists()


def test_training_range_check_uses_all_source_chunks(tmp_path: Path) -> None:
    rows = _coefficient_rows()
    for row in rows:
        row["x_min"] = 0.0
        row["x_max"] = 1.0
    coefficients = _write_coefficients(tmp_path / "coefficients.parquet", rows)
    corrected_img, corrected_hdr, _ = _write_corrected_envi(
        tmp_path / "flight__corrected"
    )
    native = np.memmap(corrected_img, dtype=np.float32, mode="r+", shape=(10, 2, 3))
    native[:, 0, :] = -9999.0
    native[:, 1, :] = 50.0
    native.flush()
    plan = load_drone_translation_plans(
        coefficients,
        weighting="site_balanced",
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    output_stem = translated_output_stem(tmp_path, "flight", TARGET_SENSOR)

    with pytest.raises(ValueError, match="reflectance units/scale"):
        apply_drone_translation(
            corrected_img,
            corrected_hdr,
            output_stem=output_stem,
            plan=plan,
            chunk_lines=1,
        )

    assert not output_stem.with_suffix(".img").exists()


def test_json_coefficient_artifact_is_supported(tmp_path: Path) -> None:
    parquet = _write_coefficients(tmp_path / "coefficients.parquet")
    plans = load_drone_translation_plans(
        parquet.with_suffix(".json"),
        weighting="site_balanced",
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )
    assert plans[0].analysis_run_id == "bulk-run-1"
