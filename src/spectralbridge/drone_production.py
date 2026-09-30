"""Restart-safe production orchestration above the drone and bulk pipelines."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import csv
import json
import os
import posixpath
import re
import shutil
import subprocess
from typing import Any, Mapping, Sequence

from spectralbridge import __version__
from spectralbridge.bulk import BulkResultsConfig
from spectralbridge.bulk.flightline_outputs import discover_completed_flightlines
from spectralbridge.bulk.results import summarize_bulk_results
from spectralbridge.pipelines.bulk import run_bulk_pipeline
from spectralbridge.pipelines.drone import (
    derive_drone_flight_stem,
    load_drone_manifest,
    lookup_flight_datetime,
    run_drone_pipeline,
)
from spectralbridge.remote import (
    GocmdRemoteBackend,
    RemoteCollectionBackend,
    RemoteEntry,
    normalize_remote_path,
    remote_join,
    remote_parent,
    remote_relative_path,
)
from spectralbridge.utils.paths import get_package_data_path


_INVENTORY_SCHEMA_VERSION = 2
_CAMPAIGN_SCHEMA_VERSION = 2
_PACKAGE_SCHEMA_VERSION = 1

DroneSource = str | Mapping[int, str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def _write_rows_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({str(key) for row in rows for key in row})
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        json.dumps(_jsonable(value), sort_keys=True)
                        if isinstance(value, (list, tuple, dict))
                        else _jsonable(value)
                    )
                    for key, value in row.items()
                }
            )
    temporary.replace(path)
    return path


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class RemoteDronePackage:
    """One candidate ExportPackage discovered without downloading its H5."""

    remote_package_path: str
    source_root: str
    package_name: str
    remote_h5_path: str | None
    h5_name: str | None
    size_bytes: int | None
    checksum: str | None
    flight_stem: str | None
    year: int | None
    manifest_id: str | None
    acquisition_datetime: str | None
    manifest_matched: bool
    required_source_exists: bool
    completed_local_result: bool
    local_flightline_path: str | None
    bulk_ready: bool
    eligibility: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DroneYearSource:
    """Resolved remote source and manifest expectation for one requested year."""

    year: int
    requested_source: str | None
    resolved_sources: tuple[str, ...]
    resolution_strategy: str
    source_status: str
    expected_manifest_flights: tuple[str, ...]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DroneCollectionInventory:
    """Serializable remote collection inventory and campaign expectation set."""

    source: str
    backend: str
    created_utc: str
    packages: tuple[RemoteDronePackage, ...]
    manifest_path: str
    requested_years: tuple[int, ...] = ()
    year_sources: tuple[DroneYearSource, ...] = ()
    result_parent: str | None = None
    schema_version: int = _INVENTORY_SCHEMA_VERSION

    @property
    def eligible_packages(self) -> tuple[RemoteDronePackage, ...]:
        return tuple(item for item in self.packages if item.eligibility == "eligible")

    @property
    def excluded_packages(self) -> tuple[RemoteDronePackage, ...]:
        return tuple(item for item in self.packages if item.eligibility != "eligible")

    def year_summaries(self) -> dict[str, dict[str, Any]]:
        """Return deterministic manifest-aware discovery evidence by year."""

        summaries: dict[str, dict[str, Any]] = {}
        for source in self.year_sources:
            packages = tuple(item for item in self.packages if item.year == source.year)
            eligible = tuple(item for item in packages if item.eligibility == "eligible")
            matched = tuple(item for item in packages if item.manifest_matched)
            eligible_ids = {
                item.manifest_id for item in eligible if item.manifest_id is not None
            }
            missing = tuple(
                sorted(set(source.expected_manifest_flights) - eligible_ids)
            )
            if not source.expected_manifest_flights:
                discovery_status = "complete_empty_manifest_year"
            elif source.source_status != "resolved":
                discovery_status = source.source_status
            elif missing:
                discovery_status = "expected_flights_not_discovered"
            else:
                discovery_status = "complete"
            summaries[str(source.year)] = {
                "requested_year": source.year,
                "requested_source": source.requested_source,
                "resolved_sources": list(source.resolved_sources),
                "resolution_strategy": source.resolution_strategy,
                "source_status": source.source_status,
                "source_reason": source.reason,
                "discovery_status": discovery_status,
                "manifest_flights": len(source.expected_manifest_flights),
                "manifest_flight_ids": list(source.expected_manifest_flights),
                "remote_packages_discovered": len(packages),
                "manifest_matched_packages": len(matched),
                "eligible_flights": len(eligible),
                "excluded_packages": len(packages) - len(eligible),
                "expected_flights_not_discovered": list(missing),
            }
        return summaries

    @property
    def discovery_complete(self) -> bool:
        summaries = self.year_summaries()
        return not summaries or all(
            item["discovery_status"]
            in {"complete", "complete_empty_manifest_year"}
            for item in summaries.values()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "backend": self.backend,
            "created_utc": self.created_utc,
            "manifest_path": self.manifest_path,
            "requested_years": list(self.requested_years),
            "result_parent": self.result_parent,
            "year_sources": [item.to_dict() for item in self.year_sources],
            "years": self.year_summaries(),
            "counts": {
                "remote_packages_discovered": len(self.packages),
                "eligible_flights": len(self.eligible_packages),
                "excluded_packages": len(self.excluded_packages),
            },
            "packages": [item.to_dict() for item in self.packages],
        }

    def write(self, output_dir: str | Path) -> tuple[Path, Path]:
        output = Path(output_dir)
        json_path = _atomic_json(output / "drone_collection_inventory.json", self.to_dict())
        csv_path = _write_rows_csv(
            output / "drone_collection_inventory.csv",
            [item.to_dict() for item in self.packages],
        )
        return json_path, csv_path


@dataclass(frozen=True)
class BulkReadinessValidation:
    """Result of classifying one producer directory with bulk's own discovery."""

    path: str
    bulk_ready: bool
    canonical_flightline_id: str | None
    candidate_count: int
    accepted_count: int
    translation_available: bool
    translation_eligible: bool
    exclusion_reasons: tuple[str, ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class StagedDroneInput:
    """Validated local copy of one required remote H5."""

    package_path: str
    local_path: str
    remote_path: str
    size_bytes: int
    status: str
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DroneCampaignConfig:
    """Explicit production settings for independent drone flight checkpoints."""

    years: tuple[int, ...] = ()
    manifest_path: str | Path | None = None
    manifest_timezone: str | None = "UTC"
    cleanup_inputs: bool = True
    resume: bool = True
    require_complete_campaign: bool = True
    apply_topo: bool = True
    apply_brdf: bool = True
    apply_brightness_adjustment: bool = False
    require_solar_geometry: bool = True
    extraction_mode: str = "full"
    parquet_chunk_size: int = 2048
    apply_translation: bool = True
    translation_strict: bool = False
    landsat_qa: bool = True
    extraction_workers: int = 1
    max_remote_depth: int = 8
    max_remote_entries: int = 100_000
    result_name: str | None = None

    def validate(self) -> None:
        if self.extraction_mode not in {"full", "polygon"}:
            raise ValueError("campaign extraction_mode must be 'full' or 'polygon'")
        if self.extraction_mode == "polygon":
            raise ValueError(
                "production campaign polygon extraction requires an explicit polygon "
                "path and is not supported by this full-extraction campaign config"
            )
        if self.parquet_chunk_size < 1 or self.extraction_workers < 1:
            raise ValueError("campaign chunk size and worker count must be positive")
        if self.max_remote_depth < 0 or self.max_remote_entries < 1:
            raise ValueError("remote inventory bounds must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DroneFlightStatus:
    """Durable campaign state for one expected remote flight package."""

    remote_package_path: str
    flight_stem: str | None
    state: str
    updated_utc: str
    local_input_path: str | None = None
    local_flightline_path: str | None = None
    transfer_status: str | None = None
    bulk_ready: bool = False
    reused: bool = False
    input_removed: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class DroneCampaignResult:
    """Completed, partial, or failed per-flight campaign outcome."""

    inventory: DroneCollectionInventory
    flights: tuple[DroneFlightStatus, ...]
    work_dir: str
    flight_outputs: str
    state_dir: str
    status: str
    started_utc: str
    completed_utc: str
    config: DroneCampaignConfig

    @property
    def completed_flights(self) -> tuple[DroneFlightStatus, ...]:
        return tuple(item for item in self.flights if item.bulk_ready)

    @property
    def failed_flights(self) -> tuple[DroneFlightStatus, ...]:
        return tuple(item for item in self.flights if item.state in {"failed", "blocked"})

    def year_summaries(self) -> dict[str, dict[str, Any]]:
        """Combine inventory evidence and durable processing state by year."""

        summaries = {
            year: dict(values)
            for year, values in self.inventory.year_summaries().items()
        }
        statuses = {item.remote_package_path: item for item in self.flights}
        for year, summary in summaries.items():
            numeric_year = int(year)
            expected_ids = set(summary["manifest_flight_ids"])
            packages = tuple(
                item for item in self.inventory.packages if item.year == numeric_year
            )
            year_statuses = tuple(
                statuses[item.remote_package_path]
                for item in packages
                if item.remote_package_path in statuses
                and item.manifest_id in expected_ids
            )
            ready_manifest_ids = {
                item.manifest_id
                for item in packages
                if item.manifest_id is not None
                and statuses.get(item.remote_package_path) is not None
                and statuses[item.remote_package_path].bulk_ready
            }
            summary.update(
                {
                    "completed": sum(item.bulk_ready for item in year_statuses),
                    "reused": sum(
                        item.bulk_ready and item.reused for item in year_statuses
                    ),
                    "newly_processed": sum(
                        item.bulk_ready and not item.reused for item in year_statuses
                    ),
                    "failed": sum(item.state == "failed" for item in year_statuses),
                    "blocked": sum(item.state == "blocked" for item in year_statuses),
                    "bulk_ready": sum(item.bulk_ready for item in year_statuses),
                    "expected_flights_not_bulk_ready": sorted(
                        expected_ids - ready_manifest_ids
                    ),
                }
            )
            summary["complete"] = bool(
                summary["discovery_status"]
                in {"complete", "complete_empty_manifest_year"}
                and not summary["expected_flights_not_bulk_ready"]
                and summary["failed"] == 0
                and summary["blocked"] == 0
            )
        return summaries

    @property
    def requested_years_complete(self) -> bool:
        years = self.year_summaries()
        return not years or all(item["complete"] for item in years.values())

    def summary(self) -> dict[str, Any]:
        states: dict[str, int] = {}
        for item in self.flights:
            states[item.state] = states.get(item.state, 0) + 1
        sites = {
            package.flight_stem.rsplit("_", 1)[0]
            for package in self.inventory.eligible_packages
            if package.flight_stem and package.flight_stem.rsplit("_", 1)[0]
        }
        years = {package.year for package in self.inventory.eligible_packages if package.year}
        return {
            **self.inventory.to_dict()["counts"],
            "campaign_status": self.status,
            "state_counts": states,
            "successfully_processed_or_reused": len(self.completed_flights),
            "successfully_processed": sum(
                item.bulk_ready and not item.reused for item in self.flights
            ),
            "downloaded": sum(
                item.transfer_status == "downloaded" for item in self.flights
            ),
            "staged_input_reused": sum(
                item.transfer_status == "reused" for item in self.flights
            ),
            "completed_result_reused": sum(
                item.reused and item.bulk_ready for item in self.flights
            ),
            "failed": states.get("failed", 0),
            "blocked": states.get("blocked", 0),
            "failed_or_blocked": len(self.failed_flights),
            "bulk_ready": len(self.completed_flights),
            "bulk_excluded": len(self.inventory.eligible_packages)
            - len(self.completed_flights),
            "years_represented": sorted(years),
            "requested_years_complete": self.requested_years_complete,
            "years": self.year_summaries(),
            "sites_represented": sorted(sites),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": _CAMPAIGN_SCHEMA_VERSION,
            "status": self.status,
            "work_dir": self.work_dir,
            "flight_outputs": self.flight_outputs,
            "state_dir": self.state_dir,
            "started_utc": self.started_utc,
            "completed_utc": self.completed_utc,
            "configuration": self.config.to_dict(),
            "summary": self.summary(),
            "inventory": self.inventory.to_dict(),
            "flights": [item.to_dict() for item in self.flights],
        }


@dataclass(frozen=True)
class BulkProductionResult:
    """Top-level campaign, bulk, summary, package, and upload result."""

    inventory: DroneCollectionInventory
    campaign: DroneCampaignResult
    bulk_result: Mapping[str, Any]
    summary_result: Mapping[str, Any]
    local_result_path: str
    remote_result_path: str | None
    preflight_result: Mapping[str, Any]
    status: str = "complete"

    @property
    def completed_flights(self) -> tuple[DroneFlightStatus, ...]:
        return self.campaign.completed_flights

    @property
    def failed_flights(self) -> tuple[DroneFlightStatus, ...]:
        return self.campaign.failed_flights

    def summary(self) -> dict[str, Any]:
        return {
            **self.campaign.summary(),
            "production_status": self.status,
            "bulk_accepted_flightlines": self.bulk_result.get(
                "accepted_flightline_count"
            ),
            "bulk_regressions": self.bulk_result.get("regression_count"),
            "local_result_path": self.local_result_path,
            "remote_result_path": self.remote_result_path,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "inventory": self.inventory.to_dict(),
            "campaign": self.campaign.to_dict(),
            "preflight_result": _jsonable(self.preflight_result),
            "bulk_result": _jsonable(self.bulk_result),
            "summary_result": _jsonable(self.summary_result),
            "local_result_path": self.local_result_path,
            "remote_result_path": self.remote_result_path,
        }


class DroneCampaignIncompleteError(RuntimeError):
    """The intended eligible population was not fully bulk-ready."""

    def __init__(self, message: str, result: DroneCampaignResult):
        super().__init__(message)
        self.result = result


def _manifest_path(path: str | Path | None) -> Path:
    return (
        Path(path).expanduser().resolve()
        if path is not None
        else get_package_data_path("drone_field_manifest.csv")
    )


def _remote_common_parent(paths: Sequence[str]) -> str:
    """Return the common remote collection containing resolved source roots."""

    normalized = tuple(normalize_remote_path(path) for path in paths)
    if not normalized:
        raise ValueError("at least one resolved remote source is required")
    prefixes = {"i:" if path.startswith("i:") else "" for path in normalized}
    if len(prefixes) != 1:
        raise ValueError("remote sources must use the same path namespace")
    prefix = prefixes.pop()
    bodies = [path[2:] if prefix else path for path in normalized]
    common = posixpath.commonpath(bodies)
    if common in {"", "/"}:
        return normalize_remote_path(prefix + "/")
    return normalize_remote_path(prefix + common)


def _manifest_expectations(
    manifest_rows: Mapping[str, datetime], requested_years: Sequence[int]
) -> dict[int, tuple[str, ...]]:
    requested = tuple(sorted({int(year) for year in requested_years}))
    return {
        year: tuple(
            sorted(
                flight_id
                for flight_id, acquisition in manifest_rows.items()
                if acquisition.year == year
            )
        )
        for year in requested
    }


def _match_manifest_flight(
    flight_stem: str | None,
    manifest_rows: Mapping[str, datetime],
) -> tuple[str | None, datetime | None]:
    if not flight_stem:
        return None, None
    acquisition = lookup_flight_datetime(flight_stem, dict(manifest_rows))
    if acquisition is None:
        return None, None
    matches = [
        flight_id
        for flight_id, candidate in manifest_rows.items()
        if candidate == acquisition
        and lookup_flight_datetime(flight_stem, {flight_id: candidate}) is not None
    ]
    if not matches:
        return None, acquisition
    return sorted(matches, key=lambda value: (-len(value), value))[0], acquisition


def _resolve_drone_sources(
    source: DroneSource,
    *,
    requested_years: Sequence[int],
    manifest_rows: Mapping[str, datetime],
    backend: RemoteCollectionBackend,
) -> tuple[str, tuple[DroneYearSource, ...], tuple[str, ...], str]:
    """Resolve campaign-root, year-sibling, or explicit year-bound sources."""

    requested = tuple(sorted({int(year) for year in requested_years}))
    expectations = _manifest_expectations(manifest_rows, requested)
    backend.ensure_available()

    if isinstance(source, Mapping):
        explicit: dict[int, str] = {}
        for raw_year, raw_path in source.items():
            year = int(raw_year)
            if year in explicit:
                raise ValueError(f"duplicate remote source mapping for year {year}")
            explicit[year] = normalize_remote_path(raw_path)
        if not requested:
            requested = tuple(sorted(explicit))
            expectations = _manifest_expectations(manifest_rows, requested)
        records: list[DroneYearSource] = []
        resolved: list[str] = []
        for year in requested:
            candidate = explicit.get(year)
            exists = bool(candidate and backend.path_exists(candidate))
            if exists and candidate is not None:
                backend.verify_access(candidate)
                resolved.append(candidate)
            records.append(
                DroneYearSource(
                    year=year,
                    requested_source=candidate,
                    resolved_sources=(candidate,) if exists and candidate else (),
                    resolution_strategy="explicit_year_mapping",
                    source_status="resolved" if exists else "no_remote_collection",
                    expected_manifest_flights=expectations.get(year, ()),
                    reason=(
                        None
                        if exists
                        else f"no accessible remote source was supplied for {year}"
                    ),
                )
            )
        unique = tuple(dict.fromkeys(resolved))
        parent = _remote_common_parent(unique) if unique else normalize_remote_path("/")
        return parent, tuple(records), unique, parent

    normalized_source = normalize_remote_path(source)
    backend.verify_access(normalized_source)
    body = normalized_source[2:] if normalized_source.startswith("i:") else normalized_source
    name = posixpath.basename(body)
    year_matches = tuple(re.finditer(r"(?<!\d)(20\d{2})(?!\d)", name))
    use_siblings = bool(requested and len(year_matches) == 1)
    if use_siblings:
        match = year_matches[0]
        parent = remote_parent(normalized_source)
        records = []
        resolved = []
        for year in requested:
            sibling_name = name[: match.start()] + str(year) + name[match.end() :]
            candidate = remote_join(parent, sibling_name)
            exists = backend.path_exists(candidate)
            if exists:
                backend.verify_access(candidate)
                resolved.append(candidate)
            records.append(
                DroneYearSource(
                    year=year,
                    requested_source=candidate,
                    resolved_sources=(candidate,) if exists else (),
                    resolution_strategy="year_token_sibling",
                    source_status="resolved" if exists else "no_remote_collection",
                    expected_manifest_flights=expectations.get(year, ()),
                    reason=(
                        None
                        if exists
                        else f"resolved sibling collection is unavailable: {candidate}"
                    ),
                )
            )
        return normalized_source, tuple(records), tuple(dict.fromkeys(resolved)), parent

    records = tuple(
        DroneYearSource(
            year=year,
            requested_source=normalized_source,
            resolved_sources=(normalized_source,),
            resolution_strategy="campaign_root",
            source_status="resolved",
            expected_manifest_flights=expectations.get(year, ()),
        )
        for year in requested
    )
    return normalized_source, records, (normalized_source,), normalized_source


def _remote_package_path(remote_h5: str) -> str | None:
    value = normalize_remote_path(remote_h5)
    prefix = "i:" if value.startswith("i:") else ""
    parts = (value[2:] if prefix else value).strip("/").split("/")
    indices = [index for index, part in enumerate(parts) if "exportpackage" in part.lower()]
    if not indices:
        return None
    return normalize_remote_path(prefix + "/" + "/".join(parts[: indices[-1] + 1]))


def _inventory_entries(
    source: str,
    backend: RemoteCollectionBackend,
    *,
    max_depth: int,
    max_entries: int,
) -> list[RemoteEntry]:
    queue: list[tuple[str, int]] = [(source, 0)]
    visited: set[str] = set()
    entries: list[RemoteEntry] = []
    while queue:
        current, depth = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        children = backend.list_directory(current)
        entries.extend(children)
        if len(entries) > max_entries:
            raise RuntimeError(
                f"remote inventory exceeded max_remote_entries={max_entries}"
            )
        collections = [item for item in children if item.is_collection]
        if collections and depth >= max_depth:
            raise RuntimeError(
                f"remote inventory reached max_remote_depth={max_depth} at {current}"
            )
        queue.extend((item.path, depth + 1) for item in collections)
    return entries


def validate_bulk_ready_flightline(path: str | Path) -> BulkReadinessValidation:
    """Apply bulk's real discovery/classification contract to one producer output."""

    candidate = Path(path).expanduser().resolve()
    try:
        _sources, records = discover_completed_flightlines(
            candidate,
            analysis_profile="translation",
        )
    except Exception as exc:
        return BulkReadinessValidation(
            path=str(candidate),
            bulk_ready=False,
            canonical_flightline_id=None,
            candidate_count=0,
            accepted_count=0,
            translation_available=False,
            translation_eligible=False,
            error=f"{type(exc).__name__}: {exc}",
        )
    accepted = [item for item in records if item.status == "accepted"]
    reasons = tuple(
        sorted(
            {
                code
                for item in records
                for code in json.loads(item.exclusion_reason_codes_json or "[]")
            }
        )
    )
    record = accepted[0] if len(accepted) == 1 else records[0] if records else None
    ready = bool(
        len(records) == 1
        and len(accepted) == 1
        and record is not None
        and record.translation_available
        and record.translation_eligible
    )
    return BulkReadinessValidation(
        path=str(candidate),
        bulk_ready=ready,
        canonical_flightline_id=(record.canonical_flightline_id if record else None),
        candidate_count=len(records),
        accepted_count=len(accepted),
        translation_available=bool(record and record.translation_available),
        translation_eligible=bool(record and record.translation_eligible),
        exclusion_reasons=reasons,
        error=(
            None
            if ready
            else "expected exactly one accepted, translation-eligible flightline"
        ),
    )


def inspect_drone_collection(
    source: DroneSource,
    *,
    backend: RemoteCollectionBackend | None = None,
    manifest: str | Path | None = None,
    years: Sequence[int] | None = None,
    local_output_dir: str | Path | None = None,
    max_depth: int = 8,
    max_entries: int = 100_000,
    inventory_output_dir: str | Path | None = None,
) -> DroneCollectionInventory:
    """Inventory remote ExportPackages and required H5s before large transfer."""

    backend = backend or GocmdRemoteBackend()
    manifest_path = _manifest_path(manifest)
    manifest_rows = load_drone_manifest(manifest_path)
    requested_years = tuple(sorted({int(year) for year in years or ()}))
    source_label, year_sources, scan_roots, result_parent = _resolve_drone_sources(
        source,
        requested_years=requested_years,
        manifest_rows=manifest_rows,
        backend=backend,
    )
    if not requested_years and year_sources:
        requested_years = tuple(item.year for item in year_sources)
    grouped: dict[str, list[RemoteEntry]] = {}
    package_sources: dict[str, str] = {}
    total_entries = 0
    for scan_root in scan_roots:
        entries = _inventory_entries(
            scan_root,
            backend,
            max_depth=max_depth,
            max_entries=max_entries - total_entries,
        )
        total_entries += len(entries)
        for entry in entries:
            if entry.is_collection and "exportpackage" in entry.name.lower():
                grouped.setdefault(entry.path, [])
                package_sources.setdefault(entry.path, scan_root)
                continue
            if (
                entry.is_collection
                or not entry.name.lower().endswith(".h5")
                or entry.name.lower().endswith("__working.h5")
            ):
                continue
            package_path = _remote_package_path(entry.path)
            if package_path is not None:
                grouped.setdefault(package_path, []).append(entry)
                package_sources.setdefault(package_path, scan_root)

    packages: list[RemoteDronePackage] = []
    for package_path, h5_entries in sorted(grouped.items()):
        package_name = package_path.rstrip("/").split("/")[-1]
        one_h5 = len(h5_entries) == 1
        h5_entry = h5_entries[0] if one_h5 else None
        flight_stem = derive_drone_flight_stem(
            Path(package_name) / (h5_entry.name if h5_entry is not None else "source.h5")
        )
        manifest_id, acquisition = _match_manifest_flight(
            flight_stem, manifest_rows
        )
        year = (
            acquisition.year
            if acquisition is not None
            else int(match.group(1))
            if flight_stem and (match := re.search(r"(20\d{2})\d{4}$", flight_stem))
            else None
        )
        eligibility = "eligible"
        reason = None
        if not one_h5:
            eligibility = "excluded"
            reason = f"expected one source H5, found {len(h5_entries)}"
        elif requested_years and year not in requested_years:
            eligibility = "excluded"
            reason = f"year {year!r} is outside requested years {requested_years}"
        elif manifest_id is None:
            eligibility = "excluded"
            reason = "remote package does not match a valid manifest acquisition"

        local_flightline = (
            Path(local_output_dir).expanduser().resolve() / flight_stem
            if local_output_dir is not None and flight_stem
            else None
        )
        validation = (
            validate_bulk_ready_flightline(local_flightline)
            if local_flightline is not None and local_flightline.is_dir()
            else None
        )
        packages.append(
            RemoteDronePackage(
                remote_package_path=package_path,
                source_root=package_sources[package_path],
                package_name=package_name,
                remote_h5_path=h5_entry.path if h5_entry else None,
                h5_name=h5_entry.name if h5_entry else None,
                size_bytes=h5_entry.size_bytes if h5_entry else None,
                checksum=h5_entry.checksum if h5_entry else None,
                flight_stem=flight_stem,
                year=year,
                manifest_id=manifest_id,
                acquisition_datetime=acquisition.isoformat() if acquisition else None,
                manifest_matched=acquisition is not None,
                required_source_exists=one_h5,
                completed_local_result=bool(validation and validation.bulk_ready),
                local_flightline_path=str(local_flightline) if local_flightline else None,
                bulk_ready=bool(validation and validation.bulk_ready),
                eligibility=eligibility,
                reason=reason,
            )
        )
    by_flight_stem: dict[str, list[int]] = {}
    for index, package in enumerate(packages):
        if package.eligibility == "eligible" and package.flight_stem:
            by_flight_stem.setdefault(package.flight_stem, []).append(index)
    for flight_stem, indices in by_flight_stem.items():
        if len(indices) < 2:
            continue
        paths = sorted(packages[index].remote_package_path for index in indices)
        for index in indices:
            packages[index] = replace(
                packages[index],
                eligibility="excluded",
                reason=(
                    f"duplicate remote scientific identity {flight_stem!r}: "
                    + ", ".join(paths)
                ),
            )
    inventory = DroneCollectionInventory(
        source=source_label,
        backend=backend.name,
        created_utc=_utc_now(),
        packages=tuple(packages),
        manifest_path=str(manifest_path),
        requested_years=requested_years,
        year_sources=year_sources,
        result_parent=result_parent,
    )
    if inventory_output_dir is not None:
        inventory.write(inventory_output_dir)
    return inventory


def stage_drone_package(
    package: RemoteDronePackage,
    *,
    source: str,
    staging_dir: str | Path,
    backend: RemoteCollectionBackend,
) -> StagedDroneInput:
    """Download or reuse one complete H5 while preserving ExportPackage layout."""

    if not package.remote_h5_path or not package.h5_name:
        raise ValueError(f"package has no unambiguous H5: {package.remote_package_path}")
    relative = remote_relative_path(package.remote_h5_path, source)
    staging_root = Path(staging_dir).expanduser().resolve()
    local_path = (staging_root / relative).resolve()
    if local_path == staging_root or staging_root not in local_path.parents:
        raise ValueError(f"staged path escapes staging root: {local_path}")
    expected_size = package.size_bytes
    status = "downloaded"
    if local_path.is_file() and local_path.stat().st_size > 0:
        size_matches = expected_size is None or local_path.stat().st_size == expected_size
        checksum_matches = (
            package.checksum is None or _sha256_file(local_path) == package.checksum
        )
        if size_matches and checksum_matches:
            status = "reused"
            return StagedDroneInput(
                package_path=str(local_path.parent),
                local_path=str(local_path),
                remote_path=package.remote_h5_path,
                size_bytes=local_path.stat().st_size,
                status=status,
                checksum=package.checksum,
            )
    local_path.parent.mkdir(parents=True, exist_ok=True)
    partial = local_path.with_suffix(local_path.suffix + ".part")
    if partial.exists():
        partial.unlink()
    backend.download_file(package.remote_h5_path, partial)
    if not partial.is_file() or partial.stat().st_size == 0:
        raise RuntimeError(f"downloaded H5 is missing or empty: {partial}")
    if expected_size is not None and partial.stat().st_size != expected_size:
        raise RuntimeError(
            f"downloaded H5 size mismatch for {package.remote_h5_path}: "
            f"expected {expected_size}, found {partial.stat().st_size}"
        )
    if package.checksum and _sha256_file(partial) != package.checksum:
        raise RuntimeError(f"downloaded H5 checksum mismatch: {package.remote_h5_path}")
    os.replace(partial, local_path)
    transfer = {
        "schema_version": 1,
        "created_utc": _utc_now(),
        "remote_path": package.remote_h5_path,
        "local_path": str(local_path),
        "size_bytes": local_path.stat().st_size,
        "remote_size_bytes": expected_size,
        "remote_checksum": package.checksum,
        "backend": backend.name,
    }
    _atomic_json(local_path.parent / "spectralbridge_transfer.json", transfer)
    return StagedDroneInput(
        package_path=str(local_path.parent),
        local_path=str(local_path),
        remote_path=package.remote_h5_path,
        size_bytes=local_path.stat().st_size,
        status=status,
        checksum=package.checksum,
    )


def stage_drone_collection(
    inventory: DroneCollectionInventory,
    *,
    staging_dir: str | Path,
    backend: RemoteCollectionBackend | None = None,
) -> tuple[StagedDroneInput, ...]:
    """Stage every eligible H5; campaign runners normally stage one at a time."""

    backend = backend or GocmdRemoteBackend()
    return tuple(
        stage_drone_package(
            package,
            source=package.source_root,
            staging_dir=staging_dir,
            backend=backend,
        )
        for package in inventory.eligible_packages
    )


def _write_campaign_state(state_dir: Path, statuses: Sequence[DroneFlightStatus]) -> None:
    rows = [item.to_dict() for item in statuses]
    _atomic_json(
        state_dir / "drone_campaign_status.json",
        {"schema_version": _CAMPAIGN_SCHEMA_VERSION, "updated_utc": _utc_now(), "flights": rows},
    )
    _write_rows_csv(state_dir / "drone_campaign_status.csv", rows)


def run_drone_campaign(
    source: DroneSource,
    *,
    work_dir: str | Path,
    years: Sequence[int] | None = None,
    manifest: str | Path | None = None,
    backend: RemoteCollectionBackend | None = None,
    config: DroneCampaignConfig | None = None,
) -> DroneCampaignResult:
    """Stage and run independent restart-safe drone producer checkpoints."""

    backend = backend or GocmdRemoteBackend()
    config = config or DroneCampaignConfig(
        years=tuple(int(year) for year in years or ()), manifest_path=manifest
    )
    if years is not None and config.years != tuple(int(year) for year in years):
        config = replace(config, years=tuple(int(year) for year in years))
    if manifest is not None and config.manifest_path != manifest:
        config = replace(config, manifest_path=manifest)
    config.validate()
    work = Path(work_dir).expanduser().resolve()
    staging = work / "staging"
    flight_outputs = work / "flight_outputs"
    state_dir = work / "state"
    for directory in (staging, flight_outputs, state_dir):
        directory.mkdir(parents=True, exist_ok=True)
    started = _utc_now()
    inventory = inspect_drone_collection(
        source,
        backend=backend,
        manifest=config.manifest_path,
        years=config.years,
        local_output_dir=flight_outputs,
        max_depth=config.max_remote_depth,
        max_entries=config.max_remote_entries,
        inventory_output_dir=state_dir,
    )
    expected_by_year = {
        item.year: set(item.expected_manifest_flights)
        for item in inventory.year_sources
    }
    statuses = []
    for item in inventory.packages:
        expected = bool(
            item.year in expected_by_year
            and item.manifest_id in expected_by_year[item.year]
        )
        statuses.append(
            DroneFlightStatus(
                remote_package_path=item.remote_package_path,
                flight_stem=item.flight_stem,
                state=(
                    "pending"
                    if item.eligibility == "eligible"
                    else "blocked"
                    if expected
                    else "excluded"
                ),
                updated_utc=_utc_now(),
                local_flightline_path=item.local_flightline_path,
                bulk_ready=item.bulk_ready,
                reused=item.bulk_ready,
                reason=item.reason,
            )
        )
    _write_campaign_state(state_dir, statuses)

    for package in inventory.eligible_packages:
        index = next(
            i
            for i, item in enumerate(statuses)
            if item.remote_package_path == package.remote_package_path
        )
        local_flightline = flight_outputs / str(package.flight_stem)
        existing = validate_bulk_ready_flightline(local_flightline)
        if config.resume and existing.bulk_ready:
            statuses[index] = replace(
                statuses[index],
                state="completed",
                updated_utc=_utc_now(),
                bulk_ready=True,
                reused=True,
                local_flightline_path=str(local_flightline),
                reason=None,
            )
            _write_campaign_state(state_dir, statuses)
            continue
        try:
            statuses[index] = replace(
                statuses[index], state="downloading", updated_utc=_utc_now(), reason=None
            )
            _write_campaign_state(state_dir, statuses)
            staged = stage_drone_package(
                package,
                source=package.source_root,
                staging_dir=staging,
                backend=backend,
            )
            statuses[index] = replace(
                statuses[index],
                state="downloaded",
                updated_utc=_utc_now(),
                local_input_path=staged.local_path,
                transfer_status=staged.status,
                reused=False,
            )
            _write_campaign_state(state_dir, statuses)
            statuses[index] = replace(
                statuses[index], state="processing", updated_utc=_utc_now()
            )
            _write_campaign_state(state_dir, statuses)
            run_drone_pipeline(
                staged.package_path,
                output_dir=flight_outputs,
                apply_topo=config.apply_topo,
                apply_brdf=config.apply_brdf,
                apply_brightness_adjustment=config.apply_brightness_adjustment,
                overwrite=False,
                drone_manifest_path=config.manifest_path,
                drone_manifest_timezone=config.manifest_timezone,
                require_solar_geometry=config.require_solar_geometry,
                extraction_mode=config.extraction_mode,
                parquet_chunk_size=config.parquet_chunk_size,
                merge_extractions=False,
                apply_translation=config.apply_translation,
                translation_strict=config.translation_strict,
                landsat_qa=config.landsat_qa,
                raise_on_incomplete=True,
            )
            validation = validate_bulk_ready_flightline(local_flightline)
            if not validation.bulk_ready:
                raise RuntimeError(
                    "producer returned but bulk readiness failed: "
                    + json.dumps(validation.to_dict(), sort_keys=True)
                )
            removed = False
            if config.cleanup_inputs:
                staged_path = Path(staged.local_path)
                if staged_path.is_file():
                    staged_path.unlink()
                    removed = True
            statuses[index] = replace(
                statuses[index],
                state="completed",
                updated_utc=_utc_now(),
                local_flightline_path=str(local_flightline),
                bulk_ready=True,
                reused=False,
                input_removed=removed,
                reason=None,
            )
        except Exception as exc:
            state = "blocked" if "scientific" in str(exc).lower() else "failed"
            statuses[index] = replace(
                statuses[index],
                state=state,
                updated_utc=_utc_now(),
                local_flightline_path=str(local_flightline),
                bulk_ready=False,
                reason=f"{type(exc).__name__}: {exc}",
            )
        _write_campaign_state(state_dir, statuses)

    eligible_paths = {item.remote_package_path for item in inventory.eligible_packages}
    incomplete = [
        item
        for item in statuses
        if item.remote_package_path in eligible_paths and not item.bulk_ready
    ]
    result = DroneCampaignResult(
        inventory=inventory,
        flights=tuple(statuses),
        work_dir=str(work),
        flight_outputs=str(flight_outputs),
        state_dir=str(state_dir),
        status=(
            "incomplete"
            if incomplete or not inventory.discovery_complete
            else "complete"
        ),
        started_utc=started,
        completed_utc=_utc_now(),
        config=config,
    )
    if result.status == "complete" and not result.requested_years_complete:
        result = replace(result, status="incomplete")
    _atomic_json(state_dir / "drone_campaign_result.json", result.to_dict())
    return result


_PACKAGE_SELECTIONS = (
    "catalog",
    "statistics",
    "analyses/dataset_census",
    "analyses/sensor_translation",
    "analyses/leave_one_site_out",
    "analyses/bulk_results",
    "coefficients",
    "figures/bulk_results",
    "reports",
)


def _copy_result_tree(source: Path, destination: Path) -> None:
    if source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return
    if not source.is_dir():
        return
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if path.name.endswith(".tmp") or "diagnostic_sample" in path.name:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _default_result_name(source: DroneSource, years: Sequence[int]) -> str:
    source_name = (
        normalize_remote_path(source).rstrip("/").split("/")[-1]
        if isinstance(source, str)
        else "multi-year-drone-campaign"
    )
    source_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", source_name).strip("._-")
    years_slug = "_".join(str(year) for year in years) if years else "all_years"
    version_slug = re.sub(r"[^A-Za-z0-9._-]+", "_", __version__)
    return f"SpectralBridge_Bulk_Results_{source_slug}_{years_slug}_{version_slug}"


def _package_is_valid(package_dir: Path) -> bool:
    manifest_path = package_dir / "PACKAGE_MANIFEST.json"
    if not manifest_path.is_file():
        return False
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return all(
            (package_dir / item["relative_path"]).is_file()
            and (package_dir / item["relative_path"]).stat().st_size == item["size_bytes"]
            and _sha256_file(package_dir / item["relative_path"]) == item["sha256"]
            for item in payload["files"]
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return False


def _campaign_identity_sha256(campaign: DroneCampaignResult) -> str:
    payload = {
        "requested_years": list(campaign.inventory.requested_years),
        "resolved_sources": {
            str(item.year): list(item.resolved_sources)
            for item in campaign.inventory.year_sources
        },
        "manifest_expectations": {
            str(item.year): list(item.expected_manifest_flights)
            for item in campaign.inventory.year_sources
        },
        "bulk_ready_flightlines": sorted(
            item.flight_stem
            for item in campaign.completed_flights
            if item.flight_stem is not None
        ),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def _package_matches_campaign(
    package_dir: Path, campaign: DroneCampaignResult
) -> bool:
    if not _package_is_valid(package_dir):
        return False
    try:
        payload = json.loads(
            (package_dir / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("campaign_identity_sha256") == _campaign_identity_sha256(
        campaign
    )


def _archive_stale_package(package_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = package_dir.with_name(f"{package_dir.name}.stale-{timestamp}")
    counter = 1
    while candidate.exists():
        candidate = package_dir.with_name(
            f"{package_dir.name}.stale-{timestamp}-{counter}"
        )
        counter += 1
    package_dir.rename(candidate)
    return candidate


def package_drone_bulk_results(
    *,
    campaign: DroneCampaignResult,
    preflight_output: str | Path,
    bulk_output: str | Path,
    package_dir: str | Path,
) -> Path:
    """Build a compact, checksummed closeout package without raw or cache data."""

    package = Path(package_dir).expanduser().resolve()
    if package.exists():
        if _package_matches_campaign(package, campaign):
            return package
        _archive_stale_package(package)
    results_root = package / "results"
    provenance = package / "provenance"
    preflight_root = package / "preflight"
    package.mkdir(parents=True)
    bulk = Path(bulk_output).expanduser().resolve()
    for relative in _PACKAGE_SELECTIONS:
        _copy_result_tree(bulk / relative, results_root / relative)
    _copy_result_tree(
        Path(preflight_output).expanduser().resolve() / "catalog",
        preflight_root / "catalog",
    )
    campaign.inventory.write(provenance)
    _atomic_json(provenance / "drone_campaign_result.json", campaign.to_dict())
    source_state = Path(campaign.state_dir)
    for name in ("drone_campaign_status.csv", "drone_campaign_status.json"):
        if (source_state / name).is_file():
            shutil.copy2(source_state / name, provenance / name)
    git_commit = None
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        git_commit = completed.stdout.strip() or None
    _atomic_json(
        provenance / "production_provenance.json",
        {
            "schema_version": _PACKAGE_SCHEMA_VERSION,
            "created_utc": _utc_now(),
            "spectralbridge_version": __version__,
            "git_commit": git_commit,
            "remote_source": campaign.inventory.source,
            "campaign_identity_sha256": _campaign_identity_sha256(campaign),
            "configuration": campaign.config.to_dict(),
            "excluded_from_package": [
                "downloaded source H5 files",
                "working/scratch directories",
                "DuckDB temporary data",
                "diagnostic pixel samples",
            ],
        },
    )
    files = [
        {
            "relative_path": path.relative_to(package).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in sorted(package.rglob("*"))
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    ]
    _atomic_json(
        package / "PACKAGE_MANIFEST.json",
        {
            "schema_version": _PACKAGE_SCHEMA_VERSION,
            "created_utc": _utc_now(),
            "file_count": len(files),
            "total_bytes": sum(item["size_bytes"] for item in files),
            "campaign_identity_sha256": _campaign_identity_sha256(campaign),
            "files": files,
        },
    )
    if not _package_is_valid(package):
        raise RuntimeError(f"new result package failed checksum validation: {package}")
    return package


def _recursive_remote_files(
    backend: RemoteCollectionBackend,
    root: str,
) -> dict[str, RemoteEntry]:
    queue = [root]
    files: dict[str, RemoteEntry] = {}
    while queue:
        current = queue.pop(0)
        for entry in backend.list_directory(current):
            if entry.is_collection:
                queue.append(entry.path)
            else:
                files[remote_relative_path(entry.path, root)] = entry
    return files


def verify_uploaded_results(
    local_package: str | Path,
    remote_path: str,
    *,
    backend: RemoteCollectionBackend,
) -> dict[str, Any]:
    """Verify every packaged file remotely by presence and size/checksum metadata."""

    local = Path(local_package).expanduser().resolve()
    expected = {
        path.relative_to(local).as_posix(): path
        for path in local.rglob("*")
        if path.is_file()
    }
    remote_files = _recursive_remote_files(backend, remote_path)
    missing = sorted(set(expected) - set(remote_files))
    size_mismatches = sorted(
        relative
        for relative, path in expected.items()
        if relative in remote_files
        and remote_files[relative].size_bytes is not None
        and remote_files[relative].size_bytes != path.stat().st_size
    )
    checksum_mismatches = sorted(
        relative
        for relative, path in expected.items()
        if relative in remote_files
        and remote_files[relative].checksum is not None
        and remote_files[relative].checksum != _sha256_file(path)
    )
    return {
        "verified": not missing and not size_mismatches and not checksum_mismatches,
        "remote_path": remote_path,
        "expected_files": len(expected),
        "remote_files": len(remote_files),
        "missing": missing,
        "size_mismatches": size_mismatches,
        "checksum_mismatches": checksum_mismatches,
    }


def _incomplete_campaign_message(campaign: DroneCampaignResult) -> str:
    lines = ["Requested drone campaign is incomplete."]
    for year, summary in campaign.year_summaries().items():
        lines.append(
            f"{year}: manifest={summary['manifest_flights']}, "
            f"discovered={summary['remote_packages_discovered']}, "
            f"eligible={summary['eligible_flights']}, "
            f"completed={summary['completed']}, reused={summary['reused']}, "
            f"new={summary['newly_processed']}, bulk_ready={summary['bulk_ready']}, "
            f"status={summary['discovery_status']}"
        )
        if summary["source_reason"]:
            lines.append(f"  source: {summary['source_reason']}")
        if summary["expected_flights_not_discovered"]:
            lines.append(
                "  expected flights not discovered/eligible: "
                + ", ".join(summary["expected_flights_not_discovered"])
            )
        if summary["expected_flights_not_bulk_ready"]:
            lines.append(
                "  expected flights not bulk-ready: "
                + ", ".join(summary["expected_flights_not_bulk_ready"])
            )
    return "\n".join(lines)


def _validate_campaign_bulk_population(campaign: DroneCampaignResult) -> None:
    """Require bulk discovery to see exactly the campaign's validated identities."""

    _sources, records = discover_completed_flightlines(
        campaign.flight_outputs,
        analysis_profile="translation",
    )
    accepted = {
        item.canonical_flightline_id
        for item in records
        if item.status == "accepted" and item.canonical_flightline_id
    }
    expected = {
        item.flight_stem
        for item in campaign.completed_flights
        if item.flight_stem is not None
    }
    if accepted != expected:
        missing = sorted(expected - accepted)
        unexpected = sorted(accepted - expected)
        raise DroneCampaignIncompleteError(
            "Bulk discovery population does not match the complete requested campaign. "
            f"Missing={missing}; unexpected={unexpected}.",
            campaign,
        )


def run_drone_bulk_production(
    *,
    source: DroneSource,
    years: Sequence[int],
    work_dir: str | Path,
    manifest: str | Path | None = None,
    backend: RemoteCollectionBackend | None = None,
    config: DroneCampaignConfig | None = None,
    upload_results: bool = False,
    require_complete_campaign: bool = True,
) -> BulkProductionResult:
    """Run remote inventory through producer, bulk, reporting, and optional upload."""

    backend = backend or GocmdRemoteBackend()
    if config is None:
        config = DroneCampaignConfig(
            years=tuple(int(year) for year in years),
            manifest_path=manifest,
            require_complete_campaign=require_complete_campaign,
        )
    else:
        config = replace(
            config,
            years=tuple(int(year) for year in years),
            manifest_path=manifest if manifest is not None else config.manifest_path,
            require_complete_campaign=require_complete_campaign,
        )
    campaign = run_drone_campaign(
        source,
        work_dir=work_dir,
        backend=backend,
        config=config,
    )
    if campaign.status != "complete" and config.require_complete_campaign:
        raise DroneCampaignIncompleteError(
            _incomplete_campaign_message(campaign)
            + "\nPopulation analysis was not started. See "
            + str(Path(campaign.state_dir) / "drone_campaign_status.csv"),
            campaign,
        )
    if not campaign.completed_flights:
        raise DroneCampaignIncompleteError(
            "No bulk-ready flights are available for population analysis.", campaign
        )
    _validate_campaign_bulk_population(campaign)
    work = Path(work_dir).expanduser().resolve()
    preflight_dir = work / "bulk_preflight"
    bulk_dir = work / "bulk_analysis"
    preflight = run_bulk_pipeline(
        campaign.flight_outputs,
        preflight_dir,
        input_mode="flightline_outputs",
        analysis="translation",
        on_invalid="exclude",
        materialize_observations=False,
        preflight_only=True,
        extraction_workers=config.extraction_workers,
        spectral_library=None,
        make_summary_plots=False,
        make_full_spectral_reports=False,
    )
    expected = len(campaign.completed_flights)
    if int(preflight["accepted_flightline_count"]) != expected:
        raise DroneCampaignIncompleteError(
            "Bulk preflight population does not match the campaign's bulk-ready set; "
            f"expected {expected}, accepted {preflight['accepted_flightline_count']}.",
            campaign,
        )
    bulk_result = run_bulk_pipeline(
        campaign.flight_outputs,
        bulk_dir,
        input_mode="flightline_outputs",
        analysis="translation",
        on_invalid="exclude",
        materialize_observations=False,
        preflight_only=False,
        extraction_workers=config.extraction_workers,
        spectral_library=None,
        make_summary_plots=False,
        make_full_spectral_reports=False,
    )
    summary_result = summarize_bulk_results(
        bulk_dir,
        config=BulkResultsConfig(),
        make_figures=True,
        make_report=True,
    )
    result_name = config.result_name or _default_result_name(source, config.years)
    package = package_drone_bulk_results(
        campaign=campaign,
        preflight_output=preflight_dir,
        bulk_output=bulk_dir,
        package_dir=work / "results" / result_name,
    )
    remote_result = None
    if upload_results:
        if campaign.inventory.result_parent is None:
            raise RuntimeError("campaign inventory has no resolved result destination")
        destination = remote_join(campaign.inventory.result_parent, package.name)
        if backend.path_exists(destination):
            verification = verify_uploaded_results(package, destination, backend=backend)
            if not verification["verified"]:
                raise FileExistsError(
                    "remote result destination exists and does not match this package: "
                    f"{destination}"
                )
            remote_result = destination
        else:
            remote_result = backend.upload_directory(
                package, campaign.inventory.result_parent
            )
            verification = verify_uploaded_results(
                package, remote_result, backend=backend
            )
            if not verification["verified"]:
                raise RuntimeError(
                    "result upload completed but verification failed: "
                    + json.dumps(verification, sort_keys=True)
                )
        _atomic_json(
            Path(campaign.state_dir) / "remote_result_verification.json",
            verification,
        )
    result = BulkProductionResult(
        inventory=campaign.inventory,
        campaign=campaign,
        preflight_result=preflight,
        bulk_result=bulk_result,
        summary_result=summary_result,
        local_result_path=str(package),
        remote_result_path=remote_result,
    )
    _atomic_json(work / "state" / "bulk_production_result.json", result.to_dict())
    return result


__all__ = [
    "BulkProductionResult",
    "BulkReadinessValidation",
    "DroneCampaignConfig",
    "DroneCampaignIncompleteError",
    "DroneCampaignResult",
    "DroneCollectionInventory",
    "DroneFlightStatus",
    "DroneSource",
    "DroneYearSource",
    "RemoteDronePackage",
    "StagedDroneInput",
    "inspect_drone_collection",
    "package_drone_bulk_results",
    "run_drone_bulk_production",
    "run_drone_campaign",
    "stage_drone_collection",
    "stage_drone_package",
    "validate_bulk_ready_flightline",
    "verify_uploaded_results",
]
