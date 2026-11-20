"""Convert the verified AOP count-scale mapping to fractional reflectance units.

A mathematical change of units, not a refit or empirical drone calibration.
The original packaged registry and all archived fits remain unchanged. Requires
all72 training headers to have been retrieved, duplicate-checked and dimension-
matched, with the same explicit10000 reflectance storage divisor on both axes.
"""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from drone_shade_mask_preview import ROOT, file_sha256
from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.drone_translation_registry import (
    packaged_drone_translation_coefficients_path,
    validate_drone_translation_coefficients,
)
from spectralbridge.drone_translation import load_drone_translation_plans

DEST = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/aop-translation-audit"
)
DIMENSIONAL_FIELDS = [
    "intercept",
    "rmse",
    "worst_loso_rmse",
    "x_min",
    "x_max",
    "x_mean",
    "y_min",
    "y_max",
    "y_mean",
]


def convert_common_divisor(payload, divisor, evidence):
    """For M=D*m and L=D*l, l=b*m+a/D. Dimensionless fields stay fixed."""
    if not np.isfinite(divisor) or divisor <= 0:
        raise ValueError("Positive finite common divisor required")
    if any(
        r.get("reflectance_units") == "physical_reflectance_v1"
        for r in payload["records"]
    ):
        raise ValueError("Registry already in physical units; refuse double conversion")
    result = deepcopy(payload)
    version = payload["coefficient_set_version"] + "-fractional-reflectance-v1"
    result["coefficient_set_version"] = version
    result["reflectance_units"] = "physical_reflectance_v1"
    result["unit_conversion"] = dict(
        method="common-zero-offset-storage-divisor",
        source_divisor=float(divisor),
        target_divisor=float(divisor),
        equation="fractional_target = slope * fractional_source + original_intercept / divisor",
        original_coefficient_set_version=payload["coefficient_set_version"],
        evidence=evidence,
        coefficients_refitted=False,
        dimensionless_fields_unchanged=True,
        physical_accuracy_independently_validated=False,
    )
    for old, row in zip(payload["records"], result["records"]):
        row["coefficient_set_version"] = version
        row["reflectance_units"] = "physical_reflectance_v1"
        row["original_stored_intercept"] = old["intercept"]
        row["original_common_storage_divisor"] = float(divisor)
        for field in DIMENSIONAL_FIELDS:
            if row.get(field) is not None:
                row[field] = float(row[field]) / divisor
    return result


def run():
    path = DEST / "training_header_retrieval.json"
    audit = json.loads(path.read_text())
    if (
        not audit.get("complete")
        or len(audit["records"]) != 72
        or not all(r["status"] == "READ_VERIFIED" for r in audit["records"])
    ):
        raise ValueError("All72 training-product headers must be verified first")
    for r in audit["records"]:
        if (
            float(r["reflectance_scale_factor"]) != 10000
            or not r["matched_training_dimensions"]
        ):
            raise ValueError(
                "Training scales or identities do not support common conversion"
            )
        if file_sha256(DEST / "training_headers" / r["header"]) != r["header_sha256"]:
            raise ValueError("Verified header changed")
    source = packaged_drone_translation_coefficients_path()
    old = json.loads(source.read_text())
    converted = convert_common_divisor(
        old,
        10000,
        dict(
            original_registry_sha256=file_sha256(source),
            training_header_audit_sha256=file_sha256(path),
            header_count=72,
            header_scale_factor=10000,
            unit_convention="ENVI reflectance scale factor is divisor; fractional = stored/10000",
            identity_limit="Exact sensor/flightline names, training dimensions and agreeing archived duplicate headers; original compact catalogue did not retain separate historical header bytes.",
        ),
    )
    validate_drone_translation_coefficients(converted)
    checks = []
    for a, b in zip(old["records"], converted["records"]):
        x = np.array([a["x_min"], a["x_mean"], a["x_max"]], float)
        expected = (a["slope"] * x + a["intercept"]) / 10000
        actual = b["slope"] * (x / 10000) + b["intercept"]
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-12)
        assert (
            a["slope"] == b["slope"]
            and a["r2"] == b["r2"]
            and a["status"] == b["status"]
        )
        checks.append(
            dict(
                target=a["target_sensor"],
                band=a["target_band"],
                slope_unchanged=True,
                affine_units_equivalent=True,
            )
        )
    output = (
        DEST / "aop_derived_micasense_to_landsat_fractional_reflectance_registry.json"
    )
    write_json_atomic(output, converted)
    plans = load_drone_translation_plans(
        output, source_wavelengths_nm=[444, 475, 531, 560, 650, 668, 705, 717, 740, 842]
    )
    if not all(p.reflectance_units == "physical_reflectance_v1" for p in plans):
        raise ValueError("Loader did not retain converted unit declaration")
    write_json_atomic(
        DEST / "physical_registry_verification.json",
        dict(
            checks=checks,
            coefficient_rows=18,
            plans=len(plans),
            all_pass=True,
            code_sha256=file_sha256(Path(__file__)),
            registry_sha256=file_sha256(output),
            packaged_registry_unchanged=True,
            empirical_drone_calibration_claimed=False,
        ),
    )
    print("Verified physical-unit registry:", output)
    print(
        "All18 affine mappings equivalent; all4 target-sensor plans load in fractional-reflectance units."
    )


if __name__ == "__main__":
    run()
