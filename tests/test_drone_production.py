from __future__ import annotations

from pathlib import Path
import json
import subprocess

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import spectralbridge.drone_production as production
from spectralbridge.drone_production import (
    BulkReadinessValidation,
    DroneCampaignConfig,
    inspect_drone_collection,
    run_drone_bulk_production,
    run_drone_campaign,
    stage_drone_package,
    validate_bulk_ready_flightline,
)
from spectralbridge.remote import (
    GocmdRemoteBackend,
    RemoteEntry,
    normalize_remote_path,
    parse_gocmd_listing,
    remote_join,
    remote_relative_path,
)


class FakeRemoteBackend:
    name = "fake"

    def __init__(self, files: dict[str, bytes]):
        self.files = {normalize_remote_path(path): value for path, value in files.items()}
        self.downloads: list[tuple[str, Path]] = []
        self.uploads: list[tuple[Path, str]] = []

    def ensure_available(self) -> None:
        return None

    def verify_access(self, remote_path: str) -> None:
        root = normalize_remote_path(remote_path).rstrip("/") + "/"
        if not any(path.startswith(root) for path in self.files):
            raise FileNotFoundError(remote_path)

    def list_directory(self, remote_path: str) -> list[RemoteEntry]:
        root = normalize_remote_path(remote_path)
        prefix = root.rstrip("/") + "/"
        children: dict[tuple[str, bool], RemoteEntry] = {}
        for path, content in self.files.items():
            if not path.startswith(prefix):
                continue
            suffix = path[len(prefix) :]
            head, separator, _tail = suffix.partition("/")
            child = remote_join(root, head)
            if separator:
                entry = RemoteEntry(child, head, True)
            else:
                entry = RemoteEntry(child, head, False, len(content))
            children[(entry.path, entry.is_collection)] = entry
        return sorted(children.values(), key=lambda item: (not item.is_collection, item.path))

    def download_file(self, remote_path: str, local_path: Path) -> None:
        path = normalize_remote_path(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(self.files[path])
        self.downloads.append((path, local_path))

    def path_exists(self, remote_path: str) -> bool:
        path = normalize_remote_path(remote_path)
        prefix = path.rstrip("/") + "/"
        return path in self.files or any(item.startswith(prefix) for item in self.files)

    def upload_directory(self, local_path: Path, remote_parent: str) -> str:
        destination = remote_join(remote_parent, local_path.name)
        if self.path_exists(destination):
            raise FileExistsError(destination)
        for path in local_path.rglob("*"):
            if path.is_file():
                remote = remote_join(destination, path.relative_to(local_path).as_posix())
                self.files[remote] = path.read_bytes()
        self.uploads.append((local_path, normalize_remote_path(remote_parent)))
        return destination


def _remote_files() -> dict[str, bytes]:
    return {
        "i:/campaign/batch-a/SPR1-06-28-23-ExportPackage/source.h5": b"valid-h5",
        "i:/campaign/batch-b/JC1-07-11-23-ExportPackage/source.h5": b"valid-h5-2",
        "i:/campaign/readme.txt": b"metadata",
    }


def _ready(path: str | Path) -> BulkReadinessValidation:
    path = Path(path)
    identity = path / "spectralbridge_flightline.json"
    if not identity.is_file():
        return BulkReadinessValidation(
            str(path), False, None, 0, 0, False, False, error="missing identity"
        )
    flightline_id = json.loads(identity.read_text())["flightline_id"]
    return BulkReadinessValidation(
        str(path), True, flightline_id, 1, 1, True, True
    )


def _fake_producer(input_path: str | Path, *, output_dir: str | Path, **_kwargs):
    source = next(Path(input_path).glob("*.h5"))
    stem = production.derive_drone_flight_stem(source)
    flight = Path(output_dir) / stem
    flight.mkdir(parents=True, exist_ok=True)
    (flight / "spectralbridge_flightline.json").write_text(
        json.dumps({"flightline_id": stem, "site": stem.rsplit("_", 1)[0]}),
        encoding="utf-8",
    )
    return {"status": "complete", "processed": [str(source)]}


def _write_envi(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="ENVI",
        width=values.shape[2],
        height=values.shape[1],
        count=values.shape[0],
        dtype="float32",
        crs="EPSG:32613",
        transform=from_origin(500000, 4420000, 1, 1),
        nodata=-9999.0,
    ) as dataset:
        dataset.write(values.astype("float32"))


def test_gocmd_listing_and_commands_are_structured_without_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    listing = "collection package\ndata-object source.h5 123\n"
    entries = parse_gocmd_listing(listing, parent="i:/campaign")
    assert [(item.name, item.is_collection, item.size_bytes) for item in entries] == [
        ("package", True, None),
        ("source.h5", False, 123),
    ]
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):
        calls.append((list(command), kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=listing, stderr="")

    monkeypatch.setattr("spectralbridge.remote.shutil.which", lambda _name: "/bin/gocmd")
    monkeypatch.setattr("spectralbridge.remote.subprocess.run", fake_run)
    backend = GocmdRemoteBackend("gocmd")
    backend.list_directory("i:/campaign")
    backend.download_file("i:/campaign/source.h5", tmp_path / "source.h5")
    assert calls[0][0] == ["gocmd", "ls", "i:/campaign"]
    assert calls[1][0] == [
        "gocmd",
        "get",
        "--progress",
        "i:/campaign/source.h5",
        str(tmp_path / "source.h5"),
    ]
    assert all(call[1]["check"] is False for call in calls)
    assert all("shell" not in call[1] for call in calls)


def test_inventory_discovers_exportpackages_and_preserves_identity(tmp_path: Path) -> None:
    backend = FakeRemoteBackend(_remote_files())
    inventory = inspect_drone_collection(
        "i:/campaign",
        backend=backend,
        years=[2023],
        inventory_output_dir=tmp_path,
    )
    assert len(inventory.packages) == 2
    spr = next(item for item in inventory.packages if item.package_name.startswith("SPR1"))
    assert spr.flight_stem == "SPR1_20230628"
    assert spr.manifest_matched is True
    assert spr.acquisition_datetime.startswith("2023-06-28T17:30:21")
    assert spr.remote_package_path.endswith("SPR1-06-28-23-ExportPackage")
    assert (tmp_path / "drone_collection_inventory.json").is_file()
    assert remote_relative_path(spr.remote_h5_path, inventory.source).startswith(
        "batch-a/SPR1-06-28-23-ExportPackage/"
    )


def test_inventory_reports_missing_h5_and_duplicate_scientific_identity() -> None:
    files = {
        **_remote_files(),
        "i:/campaign/batch-c/EMPTY-01-01-23-ExportPackage/readme.txt": b"no h5",
        "i:/campaign/copy/SPR1-06-28-23-ExportPackage/source.h5": b"copy",
    }
    inventory = inspect_drone_collection(
        "i:/campaign", backend=FakeRemoteBackend(files), years=[2023]
    )
    empty = next(item for item in inventory.packages if item.package_name.startswith("EMPTY"))
    assert empty.required_source_exists is False
    assert empty.eligibility == "excluded"
    assert "found 0" in empty.reason
    duplicates = [item for item in inventory.packages if item.flight_stem == "SPR1_20230628"]
    assert len(duplicates) == 2
    assert all(item.eligibility == "excluded" for item in duplicates)
    assert all("duplicate remote scientific identity" in item.reason for item in duplicates)


def test_stage_reuses_valid_file_and_replaces_incomplete_download(tmp_path: Path) -> None:
    backend = FakeRemoteBackend(_remote_files())
    inventory = inspect_drone_collection("i:/campaign", backend=backend, years=[2023])
    package = inventory.eligible_packages[0]
    relative = remote_relative_path(package.remote_h5_path, inventory.source)
    local = tmp_path / relative
    local.parent.mkdir(parents=True)
    local.write_bytes(b"")
    staged = stage_drone_package(
        package, source=inventory.source, staging_dir=tmp_path, backend=backend
    )
    assert staged.status == "downloaded"
    assert Path(staged.local_path).read_bytes() == backend.files[package.remote_h5_path]
    assert len(backend.downloads) == 1
    reused = stage_drone_package(
        package, source=inventory.source, staging_dir=tmp_path, backend=backend
    )
    assert reused.status == "reused"
    assert len(backend.downloads) == 1


def test_bulk_readiness_uses_actual_bulk_discovery(tmp_path: Path) -> None:
    flight = tmp_path / "SPR1_20230628"
    flight.mkdir()
    (flight / "spectralbridge_flightline.json").write_text(
        json.dumps(
            {
                "flightline_id": "SPR1_20230628",
                "site": "SPR1",
                "acquisition_date": "2023-06-28",
                "platform": "drone",
            }
        ),
        encoding="utf-8",
    )
    base = np.arange(16, dtype="float32").reshape(4, 2, 2) / 100
    _write_envi(
        flight / "SPR1_20230628__micasense_to_match_tm_etm+_envi.img", base
    )
    _write_envi(
        flight / "SPR1_20230628__landsat_like_landsat_tm_translated_envi.img",
        base * 1.2 + 0.01,
    )
    validation = validate_bulk_ready_flightline(flight)
    assert validation.bulk_ready is True
    assert validation.accepted_count == 1
    assert validation.canonical_flightline_id == "SPR1_20230628"


def test_campaign_restart_reuses_success_and_retries_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = FakeRemoteBackend(_remote_files())
    calls: list[str] = []
    fail_jc = True

    def producer(input_path, *, output_dir, **kwargs):
        nonlocal fail_jc
        package = Path(input_path).name
        calls.append(package)
        if package.startswith("JC1") and fail_jc:
            raise RuntimeError("simulated producer failure")
        return _fake_producer(input_path, output_dir=output_dir, **kwargs)

    monkeypatch.setattr(production, "run_drone_pipeline", producer)
    monkeypatch.setattr(production, "validate_bulk_ready_flightline", _ready)
    config = DroneCampaignConfig(years=(2023,), cleanup_inputs=True, landsat_qa=False)
    first = run_drone_campaign(
        "i:/campaign", work_dir=tmp_path, backend=backend, config=config
    )
    assert first.status == "incomplete"
    assert len(first.completed_flights) == 1
    assert len(first.failed_flights) == 1
    assert all(
        not Path(item.local_input_path).exists()
        for item in first.completed_flights
        if item.local_input_path
    )
    fail_jc = False
    second = run_drone_campaign(
        "i:/campaign", work_dir=tmp_path, backend=backend, config=config
    )
    assert second.status == "complete"
    assert len(second.completed_flights) == 2
    assert calls.count("SPR1-06-28-23-ExportPackage") == 1
    assert calls.count("JC1-07-11-23-ExportPackage") == 2
    assert len({item.flight_stem for item in second.completed_flights}) == 2


def test_complete_fake_remote_orchestration_uploads_only_closeout_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = FakeRemoteBackend(_remote_files())
    monkeypatch.setattr(production, "run_drone_pipeline", _fake_producer)
    monkeypatch.setattr(production, "validate_bulk_ready_flightline", _ready)

    def fake_bulk(_input, output, *, preflight_only, **_kwargs):
        output = Path(output)
        (output / "catalog").mkdir(parents=True, exist_ok=True)
        (output / "catalog" / "bulk_manifest.json").write_text(
            json.dumps({"status": "complete"}), encoding="utf-8"
        )
        if not preflight_only:
            for relative in (
                "statistics/translation_sufficient_statistics.parquet",
                "coefficients/candidate_translation_coefficients.parquet",
                "analyses/sensor_translation/per_flightline.parquet",
                "analyses/leave_one_site_out/leave_one_site_out.parquet",
            ):
                path = output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"compact")
        return {
            "status": "preflight_only" if preflight_only else "complete",
            "accepted_flightline_count": 2,
            "regression_count": 4,
        }

    def fake_summary(output, **_kwargs):
        report = Path(output) / "reports/bulk_results/bulk_translation_results.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text("report", encoding="utf-8")
        return {"status": "created", "report": str(report)}

    monkeypatch.setattr(production, "run_bulk_pipeline", fake_bulk)
    monkeypatch.setattr(production, "summarize_bulk_results", fake_summary)
    result = run_drone_bulk_production(
        source="i:/campaign",
        years=[2023],
        work_dir=tmp_path,
        backend=backend,
        config=DroneCampaignConfig(
            years=(2023,), cleanup_inputs=True, landsat_qa=False
        ),
        upload_results=True,
    )
    package = Path(result.local_result_path)
    assert result.status == "complete"
    assert result.remote_result_path is not None
    assert (package / "PACKAGE_MANIFEST.json").is_file()
    assert not any(path.suffix == ".h5" for path in package.rglob("*"))
    assert len(backend.uploads) == 1
    uploaded_paths = [path for path in backend.files if path.startswith(result.remote_result_path)]
    assert any(path.endswith("PACKAGE_MANIFEST.json") for path in uploaded_paths)
    assert not any(path.endswith(".h5") for path in uploaded_paths)


def test_completeness_gate_stops_before_bulk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = FakeRemoteBackend(_remote_files())
    monkeypatch.setattr(production, "validate_bulk_ready_flightline", _ready)

    def always_fail(*_args, **_kwargs):
        raise RuntimeError("producer failed")

    monkeypatch.setattr(production, "run_drone_pipeline", always_fail)
    bulk_called = False

    def forbidden_bulk(*_args, **_kwargs):
        nonlocal bulk_called
        bulk_called = True
        raise AssertionError("bulk should not run")

    monkeypatch.setattr(production, "run_bulk_pipeline", forbidden_bulk)
    with pytest.raises(production.DroneCampaignIncompleteError) as captured:
        run_drone_bulk_production(
            source="i:/campaign",
            years=[2023],
            work_dir=tmp_path,
            backend=backend,
            config=DroneCampaignConfig(years=(2023,), landsat_qa=False),
            upload_results=False,
        )
    assert captured.value.result.status == "incomplete"
    assert bulk_called is False
    assert (tmp_path / "state/drone_campaign_status.csv").is_file()
