"""Read-only audit of the camera-position orthomosaic correction run.

Attempts the existing public translation entry point, retaining its scientific
unit/acceptance guards. Source rasters/headers and the coefficient registry are
never edited. An unsupported product is not written or uploaded.
Run from the repository root with .venv/bin/python and MPLCONFIGDIR=/tmp.
"""

from pathlib import Path

from spectralbridge.drone_translation import (
    apply_drone_translation,
    load_drone_translation_plans,
    translated_output_stem,
)
from spectralbridge.drone_translation_registry import (
    packaged_drone_translation_coefficients_path,
)
from spectralbridge.envi import hdr_to_dict
from spectralbridge.radiometry import library_radiometry
from spectralbridge.utils_checks import is_valid_envi_pair
from spectralbridge.bulk.provenance import write_json_atomic

ROOT = Path.cwd()
DEST = ROOT / "provenance/drone-calibration-translation/2026-11-19"
SOURCE = ROOT / "archive/local/drone-correction-stability/2026-11-05/stable_qr_v1"
OUTPUT = ROOT / "archive/local/drone-calibration-translation/2026-11-19"


def main():
    reports = []
    registry = packaged_drone_translation_coefficients_path()
    for site, stem in [
        ("gordon", "AOP_GORDON_20230814"),
        ("goldhill", "AOP_GOLDHILL_20230814"),
        ("ruby", "AOP_Ruby_20230814"),
    ]:
        directory = SOURCE / site / "combined"
        img = directory / f"{stem}__combined_EXPERIMENTAL.img"
        hdr = img.with_suffix(".hdr")
        record = dict(
            site=site,
            selected_run=str(SOURCE.relative_to(ROOT)),
            requested_branch="combined",
            source_img=str(img.relative_to(ROOT)),
            source_exists=img.exists(),
            valid_envi_pair=is_valid_envi_pair(img, hdr),
            native_source_preserved=True,
            outputs_written=[],
            uploaded=False,
        )
        if hdr.exists():
            header = hdr_to_dict(hdr)
            record["header_status"] = {
                k: header.get(k)
                for k in [
                    "radiometry status",
                    "radiometry provenance",
                    "brdf status",
                    "scientific validation status",
                    "wavelength",
                ]
            }
        if not record["valid_envi_pair"] or site == "ruby":
            record["status"] = "NO_ACCEPTED_COMBINED_CORRECTION"
            record["reason"] = (
                "Ruby combined BRDF rejected in final_checks.json; partial fragments are not a corrected source."
            )
        else:
            try:
                library_radiometry(img)
                record["input_units_status"] = "supported"
            except ValueError as exc:
                record["input_units_status"] = str(exc)
            plans = load_drone_translation_plans(
                registry,
                source_wavelengths_nm=header["wavelength"],
                target_sensors=["Landsat_8_OLI", "Landsat_9_OLI-2"],
            )
            record["translations"] = []
            for plan in plans:
                output = translated_output_stem(OUTPUT / site, stem, plan.target_sensor)
                entry = dict(
                    target=plan.target_sensor,
                    coefficient_units=plan.reflectance_units,
                    native_bands=[b.native_source_band_index for b in plan.bands],
                    expected_output_name=output.with_suffix(".img").name,
                )
                try:
                    result = apply_drone_translation(
                        img, hdr, output_stem=output, plan=plan
                    )
                    entry.update(status=result["status"], output=result["output_img"])
                    record["outputs_written"].append(result["output_img"])
                except ValueError as exc:
                    entry.update(status="UNSUPPORTED", reason=str(exc))
                record["translations"].append(entry)
            record["status"] = (
                "UNSUPPORTED" if not record["outputs_written"] else "created"
            )
        reports.append(record)
    write_json_atomic(
        DEST / "selected_run_translation_preflight.json",
        dict(
            selected_input="camera-position orthomosaic correction; stable_qr_v1; no original-image reconstruction",
            coefficient_registry=str(registry.relative_to(ROOT)),
            source_report="DRONE_CORRECTION_STABILITY_REPORT.md",
            sites=reports,
            upload_performed=False,
            upload_reason="No scientifically supported translated products were generated.",
        ),
    )
    for record in reports:
        print(record["site"], record["status"])
        for entry in record.get("translations", []):
            print(" ", entry["target"], entry.get("reason", entry["status"]))


if __name__ == "__main__":
    main()
