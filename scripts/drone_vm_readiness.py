"""Small-file CyVerse campaign readiness checks; never launches raster processing.

The public producer consumes explicitly declared camera geometry. This audit
checks preparation, without treating a downloaded CSV as already applied geometry. Brightness calibration and sensor translation are separate contracts.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path


from spectralbridge.drone_view_geometry import read_metashape_camera_locations
from spectralbridge.remote import remote_join

from spectralbridge.drone_campaign_inputs import (
    BRIGHTNESS_EQUATION as BRIGHTNESS_EQUATION,
    compose_brightness_calibration as compose_brightness_calibration,
)


def camera_entry(backend, collection, *, explicit_name=None):
    """Select one CSV inside an explicitly associated package, never by fuzzy site match."""
    matches = [e for e in backend.list_directory(collection)
               if not e.is_collection and (
                   e.name == explicit_name if explicit_name is not None
                   else e.name.lower().endswith("-camera-locations.csv"))]
    if len(matches) != 1 or not matches[0].size_bytes:
        raise ValueError(f"Expected exactly one sized camera CSV in {collection}; found {len(matches)}")
    return matches[0]


def stage_camera(backend, entry, destination, *, crs_override=None, crs_override_provenance=None):
    """Download only the small camera table, verify/reuse bytes, and retain its CRS evidence."""
    from drone_cloud_workflow import sha256, write_json

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    if Path(entry.name).name != entry.name or entry.name in {".", ".."}:
        raise ValueError("Camera remote name must be a single filename")
    target = destination / entry.name
    receipt = target.with_suffix(target.suffix + ".transfer.json")
    saved = json.loads(receipt.read_text()) if receipt.exists() else {}
    if not (target.is_file() and saved.get("remote") == entry.to_dict()
            and saved.get("sha256") == sha256(target)):
        temporary = target.with_name(target.name + ".part")
        try:
            backend.download_file(entry.path, temporary)
            if temporary.stat().st_size != entry.size_bytes:
                raise ValueError("Incomplete camera transfer")
            # Validate before replacing a previously valid local copy.
            read_metashape_camera_locations(temporary, crs_override=crs_override,
                                            crs_override_provenance=crs_override_provenance)
            temporary.replace(target)
            write_json(receipt, {"remote": entry.to_dict(), "sha256": sha256(target)})
        finally:
            temporary.unlink(missing_ok=True)
    _, metadata = read_metashape_camera_locations(
        target, crs_override=crs_override, crs_override_provenance=crs_override_provenance)
    return metadata


def readiness_report(inventory, *, cameras, calibrations, translation_coefficients, wavelengths_by_flight, flight_contracts=None):
    """Report every manifest flight; schema/file presence alone cannot approve a campaign."""
    from spectralbridge.pipelines.drone import run_drone_pipeline
    from spectralbridge.drone_translation import load_drone_translation_plans

    blockers = []
    if not inventory.discovery_complete:
        blockers.append("Datastore inventory does not cover the requested manifest population")
    if not inventory.eligible_packages:
        blockers.append("No eligible flights discovered")
    parameters = inspect.signature(run_drone_pipeline).parameters
    required = {"brightness_calibration", "camera_geometry", "processing_mask",
                "translation_target_sensors", "translation_naming_style", "translation_output_scale_factor"}
    if not required.issubset(parameters):
        blockers.append("Installed producer lacks the camera/calibration/delivery integration; update the VM checkout")
    if flight_contracts is None:
        blockers.append("Per-flight VM execution contracts have not been supplied")
    flights = []
    for package in inventory.eligible_packages:
        key = package.remote_package_path
        reasons = []
        if flight_contracts is not None:
            contract = flight_contracts.get(key, {})
            for field in ['camera_geometry', 'camera_collection', 'brightness_json', 'pipeline', 'source_sha256']:
                if not contract.get(field):
                    reasons.append(f"Missing VM execution contract: {field}")
        if key not in cameras:
            reasons.append("Camera table missing or invalid")
        if key not in calibrations:
            reasons.append("Reviewed source-bound brightness calibration missing")
        waves = wavelengths_by_flight.get(key)
        if waves is None:
            reasons.append("Authoritative flight wavelengths not supplied")
        else:
            try:
                load_drone_translation_plans(translation_coefficients, source_wavelengths_nm=waves)
            except (ValueError, FileNotFoundError, KeyError) as exc:
                reasons.append(f"Translation registry: {exc}")
        flights.append({"package": package.package_name, "remote_package_path": key,
                       "blockers": reasons, "camera": cameras.get(key)})
    ready = not blockers and all(not item['blockers'] for item in flights)
    return {"status": "READY_FOR_PILOT" if ready else "BLOCKED", "production_ready": False,
            "ready_for_pilot": ready, "pilot_required_before_campaign": True,
            "raster_downloads_started": False, "uploads_started": False,
            "blockers": blockers, "flights": flights,
            "producer_parameters": sorted(parameters)}


def associated_camera_collection(package, camera_sources):
    """Original-year camera collection with exact package identity retained."""
    return remote_join(camera_sources[package.year], package.package_name)
