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
    862.0,
]


def _coefficient_rows() -> list[dict[str, object]]:
    return [
        {
            "reflectance_units": "physical_reflectance_v1",
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


def _write_coefficients(
    path: Path, rows: list[dict[str, object]] | None = None
) -> Path:
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
        [np.full((2, 3), 0.1 + band / 100.0, dtype=np.float32) for band in range(10)]
    )
    data[0, 0, 0] = -9999.0
    data.tofile(stem.with_suffix(".img"))
    stem.with_suffix(".hdr").write_text(
        "\n".join(
            [
                "ENVI",
                "radiometry status = VALID",
                "physical reflectance multiplier = 1",
                "physical reflectance offset = 0",
                "radiometry provenance = Synthetic translation fixture",
                "brdf status = NOT_REQUESTED",
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
                "wavelength = {"
                + ", ".join(str(value) for value in SOURCE_WAVELENGTHS)
                + "}",
            ]
        ),
        encoding="utf-8",
    )
    return stem.with_suffix(".img"), stem.with_suffix(".hdr"), data


def test_loader_selects_explicit_weighting_and_maps_by_wavelength(
    tmp_path: Path,
) -> None:
    coefficients = _write_coefficients(
        tmp_path / "candidate_translation_coefficients.parquet"
    )
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
        (
            lambda rows: rows[0].__setitem__("target_sensor", "Landsat_9_OLI-2"),
            "orientation",
        ),
        (
            lambda rows: rows[0].__setitem__(
                "equation", "source = slope * target + intercept"
            ),
            "equation",
        ),
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
    corrected_img, corrected_hdr, native = _write_corrected_envi(
        tmp_path / "flight__corrected"
    )
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
        expected = (1.0 + output_index / 10.0) * native[
            source_index
        ] + output_index / 100.0
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


def test_apply_translation_rejects_nonoverlapping_training_range(
    tmp_path: Path,
) -> None:
    rows = _coefficient_rows()
    for row in rows:
        row["x_min"] = 100.0
        row["x_max"] = 200.0
    coefficients = _write_coefficients(tmp_path / "coefficients.parquet", rows)
    corrected_img, corrected_hdr, _ = _write_corrected_envi(
        tmp_path / "flight__corrected"
    )
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


def test_experimental_translation_preserves_units_masks_and_uncertainty(tmp_path):
    from spectralbridge.corrections import (
        BRDF_KERNEL_MATH_VERSION,
        BRDF_VALIDATION_POLICY,
    )
    from spectralbridge.radiometry import Radiometry, require_library_header

    img, hdr, data = _write_corrected_envi(tmp_path / "conditional")
    data *= 5000.076295109484
    data[0, 0, 0] = -9999
    data[1, 0, 0] = np.nan
    data[3, 1, 1] = -25
    data.tofile(img)
    text = (
        hdr.read_text()
        .replace(
            "radiometry status = VALID", "radiometry status = HYPOTHETICAL_UNVERIFIED"
        )
        .replace(
            "physical reflectance multiplier = 1",
            "physical reflectance multiplier = 0.0001999969482421875",
        )
        .replace("brdf status = NOT_REQUESTED", "brdf status = VALID")
    )
    hdr.write_text(
        text
        + "\nscientific validation status = EXPERIMENTAL\nbrdf kernel math version = "
        + BRDF_KERNEL_MATH_VERSION
        + "\nbrdf validation policy = "
        + BRDF_VALIDATION_POLICY
        + "\n"
    )
    before = img.read_bytes(), hdr.read_bytes()
    plan = load_drone_translation_plans(
        _write_coefficients(tmp_path / "coeff.parquet"),
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    options = dict(output_stem=tmp_path / "translated", plan=plan)
    with pytest.raises(ValueError, match="Experimental correction"):
        apply_drone_translation(img, hdr, **options)
    with pytest.raises(ValueError, match="explicit provenance"):
        apply_drone_translation(img, hdr, experimental_input=True, **options)
    options.update(
        experimental_input=True,
        experimental_input_provenance="Synthetic declared-scale audit",
        output_scale_factor=1000,
    )
    result = apply_drone_translation(img, hdr, **options)
    out_header = hdr_to_dict(Path(result["output_hdr"]))
    actual = memmap_bsq(Path(result["output_img"]), out_header)
    for index, band in enumerate(plan.bands):
        native = data[band.native_source_band_index - 1]
        valid = np.isfinite(native) & (native != -9999)
        expected = (
            native * np.float32(0.0001999969482421875) * np.float32(band.slope)
            + np.float32(band.intercept)
        ) * 1000
        np.testing.assert_allclose(actual[index][valid], expected[valid], rtol=1e-6)
        assert np.all(actual[index][~valid] == -9999)
    assert out_header["scientific validation status"] == "EXPERIMENTAL"
    assert Radiometry.from_header(out_header).scale == 0.001
    assert Radiometry.from_header(out_header).status == "HYPOTHETICAL_UNVERIFIED"
    with pytest.raises(ValueError, match="Experimental correction"):
        require_library_header(out_header)
    assert (img.read_bytes(), hdr.read_bytes()) == before
    assert apply_drone_translation(img, hdr, **options)["status"] == "reused"
    old_signature = result["translation_signature_sha256"]
    options["output_scale_factor"] = 1
    changed = apply_drone_translation(img, hdr, **options)
    assert changed["status"] == "created"
    assert changed["translation_signature_sha256"] != old_signature


@pytest.mark.parametrize("scale", [0, -1, float("inf"), float("nan")])
def test_translation_rejects_invalid_output_scale_before_writing(tmp_path, scale):
    img, hdr, _ = _write_corrected_envi(tmp_path / "source")
    plan = load_drone_translation_plans(
        _write_coefficients(tmp_path / "coeff.parquet"),
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    with pytest.raises(ValueError, match="finite and positive"):
        apply_drone_translation(
            img, hdr, plan=plan, output_stem=tmp_path / "bad", output_scale_factor=scale
        )
    assert not (tmp_path / "bad.img").exists()


@pytest.mark.parametrize(
    "change, message",
    [
        (
            (
                "physical reflectance multiplier = 1",
                "physical reflectance multiplier = -1",
            ),
            "finite positive scale",
        ),
        (("brdf status = VALID", "brdf status = INVALID"), "supported BRDF"),
        (
            (
                "radiometry status = HYPOTHETICAL_UNVERIFIED",
                "radiometry status = UNSUPPORTED",
            ),
            "declared physical affine",
        ),
    ],
)
def test_experimental_translation_fails_closed_on_invalid_declarations(
    tmp_path, change, message
):
    from spectralbridge.corrections import (
        BRDF_KERNEL_MATH_VERSION,
        BRDF_VALIDATION_POLICY,
    )

    img, hdr, _ = _write_corrected_envi(tmp_path / "source")
    text = (
        hdr.read_text()
        .replace(
            "radiometry status = VALID", "radiometry status = HYPOTHETICAL_UNVERIFIED"
        )
        .replace("brdf status = NOT_REQUESTED", "brdf status = VALID")
    )
    text += (
        "\nscientific validation status = EXPERIMENTAL\nbrdf kernel math version = "
        + BRDF_KERNEL_MATH_VERSION
        + "\nbrdf validation policy = "
        + BRDF_VALIDATION_POLICY
        + "\n"
    )
    hdr.write_text(text.replace(*change))
    plan = load_drone_translation_plans(
        _write_coefficients(tmp_path / "coeff.parquet"),
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    with pytest.raises(ValueError, match=message):
        apply_drone_translation(
            img,
            hdr,
            plan=plan,
            output_stem=tmp_path / "bad",
            experimental_input=True,
            experimental_input_provenance="Declared fixture",
        )
    assert not (tmp_path / "bad.img").exists()


def test_scaled_approved_translation_accepts_string_paths(tmp_path):
    img, hdr, data = _write_corrected_envi(tmp_path / "source")
    plan = load_drone_translation_plans(
        _write_coefficients(tmp_path / "coeff.parquet"),
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    result = apply_drone_translation(
        str(img),
        str(hdr),
        plan=plan,
        output_stem=tmp_path / "scaled",
        output_scale_factor=1000,
    )
    header = hdr_to_dict(Path(result["output_hdr"]))
    assert header["physical reflectance multiplier"] == 0.001
    assert header["radiometry status"] == "VALID"
    out = memmap_bsq(Path(result["output_img"]), header)
    for i, band in enumerate(plan.bands):
        native = data[band.native_source_band_index - 1]
        valid = native != -9999
        np.testing.assert_allclose(
            out[i][valid] / 1000,
            (native * band.slope + band.intercept)[valid],
            rtol=1e-6,
        )


@pytest.mark.parametrize(
    "target, suffix", [("Landsat_8_OLI", "oli"), ("Landsat_9_OLI-2", "oli2")]
)
def test_concise_delivery_names_are_opt_in(tmp_path, target, suffix):
    stem = translated_output_stem(
        tmp_path, "ruby_20230814", target, naming_style="micasense"
    )
    assert stem.name == f"ruby_20230814_micasense_translated_to_{suffix}_envi"
    assert "landsat_like_" in translated_output_stem(tmp_path, "flight", target).name


def test_translation_metadata_roundtrips_and_invalidates_reuse(tmp_path):
    img, hdr, _ = _write_corrected_envi(tmp_path / "source")
    plan = load_drone_translation_plans(
        _write_coefficients(tmp_path / "coeff.parquet"),
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    options = dict(
        plan=plan,
        output_stem=tmp_path / "translated",
        output_scale_factor=1000,
        translation_metadata={
            "shade_mask_policy": "synthetic fixture",
            "mask_sha256": "fixturehash",
        },
    )
    result = apply_drone_translation(img, hdr, **options)
    header = hdr_to_dict(Path(result["output_hdr"]))
    metadata = json.loads(header["translation metadata"][5:])
    assert metadata["run_metadata"] == options["translation_metadata"]
    assert metadata["output_radiometry"]["scale"] == 0.001
    assert metadata["target_sensor"] == TARGET_SENSOR
    assert [b["native_source_band_index"] for b in metadata["bands"]] == [
        1,
        2,
        4,
        6,
        10,
    ]
    assert metadata["coefficient_sha256"] == plan.coefficient_sha256
    import rasterio

    with rasterio.open(result["output_img"]) as dataset:
        tags = dataset.tags(ns="ENVI")
        assert tags["translation_source_sensor"] == "MicaSense"
        assert tags["translation_target_sensor"] == TARGET_SENSOR
        assert tags["translation_coefficient_sha256"] == plan.coefficient_sha256
        assert float(tags["reflectance_scale_factor"]) == 1000

    assert apply_drone_translation(img, hdr, **options)["status"] == "reused"
    options["translation_metadata"] = {"shade_mask_policy": "new provenance"}
    updated = apply_drone_translation(img, hdr, **options)
    assert updated["status"] == "created"
    assert (
        updated["translation_signature_sha256"]
        != result["translation_signature_sha256"]
    )


def test_failed_brdf_null_requires_explicit_opt_in_and_retains_invalid_status(tmp_path):
    from dataclasses import replace
    from spectralbridge.corrections import (
        BRDF_KERNEL_MATH_VERSION,
        BRDF_VALIDATION_POLICY,
    )

    img, hdr, _ = _write_corrected_envi(tmp_path / "source")
    text = hdr.read_text().replace(
        "brdf status = NOT_REQUESTED", "brdf status = INVALID"
    )
    hdr.write_text(
        text
        + "\nscientific validation status = EXPERIMENTAL\nbrdf kernel math version = "
        + BRDF_KERNEL_MATH_VERSION
        + "\nbrdf validation policy = "
        + BRDF_VALIDATION_POLICY
        + "\n"
    )
    plan = load_drone_translation_plans(
        _write_coefficients(tmp_path / "coeff.parquet"),
        source_wavelengths_nm=SOURCE_WAVELENGTHS,
    )[0]
    options = dict(
        output_stem=tmp_path / "null",
        plan=plan,
        experimental_input=True,
        experimental_input_provenance="Explicit failed-QA null test",
    )
    with pytest.raises(ValueError, match="supported BRDF"):
        apply_drone_translation(img, hdr, **options)
    with pytest.raises(ValueError, match="recorded failed_brdf_qa"):
        apply_drone_translation(img, hdr, experimental_failed_brdf_qa=True, **options)
    options.update(
        experimental_failed_brdf_qa=True,
        translation_metadata={
            "failed_brdf_qa": {"status": "INVALID", "reason": "reference uncertainty"}
        },
    )
    with pytest.raises(ValueError, match="coefficient training units"):
        apply_drone_translation(
            img, hdr, **{**options, "plan": replace(plan, reflectance_units="unknown")}
        )
    result = apply_drone_translation(img, hdr, **options)
    actual = hdr_to_dict(Path(result["output_hdr"]))
    assert actual["brdf status"] == "INVALID"
    assert actual["scientific validation status"] == "EXPERIMENTAL"
    metadata = json.loads(actual["translation metadata"][5:])
    assert metadata["experimental_failed_brdf_qa"]
    assert metadata["run_metadata"]["failed_brdf_qa"]["status"] == "INVALID"
