#!/usr/bin/env python3
"""Read-only solar-geometry census for completed drone working H5 files.

Example (run from the checkout on the VM)::

    PYTHONPATH=src python scripts/diagnose_drone_solar_geometry.py \
      /home/jovyan/data-store/SpectralBridge_Drone_2023_2024_Production/flight_outputs \
      --output /home/jovyan/data-store/SpectralBridge_Drone_2023_2024_Production/solar_validation/solar_geometry.csv \
      --candidate-timezone UTC --candidate-timezone America/Denver

No H5 file or existing downstream product is written by this command.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re

from spectralbridge.pipelines.drone import (
    diagnose_drone_h5_solar_geometry,
    load_drone_manifest,
    lookup_flight_datetime,
)
from spectralbridge.utils.paths import get_package_data_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Root containing *__working.h5 files")
    parser.add_argument("--output", type=Path, required=True, help="Compact CSV output")
    parser.add_argument("--manifest", type=Path, default=get_package_data_path("drone_field_manifest.csv"))
    parser.add_argument("--naive-timezone", help="Only set after verifying the manifest time convention")
    parser.add_argument("--candidate-timezone", action="append", dest="candidate_timezones")
    args = parser.parse_args()

    paths = sorted(args.root.rglob("*__working.h5"))
    if not paths:
        parser.error(f"No working H5 files found under {args.root}")
    manifest = load_drone_manifest(args.manifest)
    rows: list[dict[str, str | float | None]] = []
    for path in paths:
        flight = path.name.removesuffix("__working.h5")
        flight_date_match = re.search(r"(20\d{6})$", flight)
        filename_date = flight_date_match.group(1) if flight_date_match else None
        try:
            result = diagnose_drone_h5_solar_geometry(
                path,
                acquisition_datetime=lookup_flight_datetime(flight, manifest),
                naive_timezone=args.naive_timezone,
                candidate_timezones=args.candidate_timezones or ("UTC",),
            )
        except Exception as exc:
            result = {
                "solar_geometry_consistency_status": "NOT_EVALUATED",
                "solar_geometry_consistency_reason": f"Diagnostic error: {exc}",
            }
        selected_zenith = result.get("source_solar_zenith") or {}
        selected_azimuth = result.get("source_solar_azimuth") or {}
        row = {
            "year": next((part for part in path.relative_to(args.root).parts if part in {"2023", "2024"}), ""),
            "flight": flight,
            "package": path.parent.parent.name,
            "h5_path": str(path),
            "acquisition_datetime": result.get("acquisition_datetime"),
            "flight_filename_date": filename_date,
            "manifest_date_matches_filename": (
                None if filename_date is None or not result.get("acquisition_datetime")
                else str(result["acquisition_datetime"])[:10].replace("-", "") == filename_date
            ),
            "timezone_interpretation": result.get("datetime_timezone_interpretation"),
            "solar_geometry_source": result.get("solar_geometry_source"),
            "solar_zenith_dataset": selected_zenith.get("original_path", selected_zenith.get("path")),
            "solar_azimuth_dataset": selected_azimuth.get("original_path", selected_azimuth.get("path")),
            "solar_zenith_min_deg": result.get("solar_zenith_min"),
            "solar_zenith_mean_deg": result.get("solar_zenith_mean"),
            "solar_zenith_max_deg": result.get("solar_zenith_max"),
            "solar_azimuth_min_deg": result.get("solar_azimuth_min"),
            "solar_azimuth_mean_deg": result.get("solar_azimuth_mean"),
            "solar_azimuth_circular_mean_deg": result.get("supplied_solar_azimuth_circular_mean_deg"),
            "solar_azimuth_max_deg": result.get("solar_azimuth_max"),
            "latitude": result.get("scene_center_latitude"),
            "longitude": result.get("scene_center_longitude"),
            "expected_zenith_deg": result.get("expected_solar_zenith_deg"),
            "expected_azimuth_deg": result.get("expected_solar_azimuth_deg"),
            "zenith_residual_deg": result.get("solar_zenith_difference_deg"),
            "azimuth_circular_residual_deg": result.get("solar_azimuth_difference_deg"),
            "status": result.get("solar_geometry_consistency_status"),
            "reason": result.get("solar_geometry_consistency_reason"),
            "candidate_positions_json": json.dumps(result.get("candidate_positions", {}), sort_keys=True),
            "source_zenith_metadata_json": json.dumps(selected_zenith, sort_keys=True),
            "source_azimuth_metadata_json": json.dumps(selected_azimuth, sort_keys=True),
        }
        rows.append(row)
        print(f"{len(rows)}/{len(paths)} {flight}: {row['status']} - {row['reason']}", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} flights to {args.output}")


if __name__ == "__main__":
    main()
