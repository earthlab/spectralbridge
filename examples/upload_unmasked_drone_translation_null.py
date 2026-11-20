"""Upload only the verified null deliverables and full failed-QA evidence.

Uses the same readback/checksum/never-overwrite uploader as the 10% batch.
Requires python-irodsclient plus the existing user iRODS environment.
"""

import json
from pathlib import Path

from upload_shade_masked_drone_translations import (
    PARENT,
    ROOT,
    digest_file,
    run as upload,
)

REPORT = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/unmasked-null-products"
)
DEST = PARENT + "/gordon_goldhill_ruby_micasense_landsat_unmasked_null_20261119_v1"
PREVIOUS = PARENT + "/gordon_goldhill_ruby_micasense_landsat_translations_20261119_v1"


def payload_files(report=REPORT):
    verification = json.loads((report / "verification.json").read_text())
    if (
        verification.get("independent_native_algebra") != "PASS"
        or verification.get("gdal_metadata") != "PASS"
        or not verification.get("masked_reference_hashes_unchanged")
        or len(verification["products"]) != 6
    ):
        raise ValueError("Null batch verification is incomplete")
    files = []
    for product in verification["products"]:
        for key in ["output_img", "output_hdr", "provenance_json"]:
            local = Path(product[key])
            if digest_file(local) != product["sha256"][str(local)]:
                raise ValueError(f"Changed verified null product: {local.name}")
            files.append((local, f"{product['site']}/{local.name}"))
    for name in [
        "README.md",
        "verification.json",
        "translated_null_vs_10percent.csv",
        "independent_algebra_checks.csv",
    ]:
        files.append((report / name, name))
    for site in ["ruby", "gordon", "goldhill"]:
        for name in [
            "baseline_brdf_qa.json",
            "native_application_qa.csv",
            "native_complete.json",
        ]:
            files.append((report / site / name, f"provenance/{site}/{name}"))
    for name in [
        "run_unmasked_drone_translation_null.py",
        "verify_unmasked_drone_translation_null.py",
    ]:
        files.append((ROOT / "examples" / name, f"provenance/{name}"))
    registry = (
        report.parent
        / "aop-translation-audit/aop_derived_micasense_to_landsat_fractional_reflectance_registry.json"
    )
    files.append(
        (registry, "provenance/fractional_reflectance_translation_registry.json")
    )
    return files


if __name__ == "__main__":
    upload(
        report=REPORT,
        destination=DEST,
        previous=PREVIOUS,
        payload_files=payload_files(),
    )
