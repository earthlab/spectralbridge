from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "audit_upstream_provenance.py"
MANIFEST = REPO_ROOT / "provenance" / "hytools.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_repository_hytools_provenance_guard_passes_offline() -> None:
    result = _run()
    assert result.returncode == 0, result.stderr
    assert "HyTools provenance audit passed" in result.stdout


def test_manifest_records_fixed_revisions_and_all_categories() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["spectralbridge"]["commit"] == (
        "30344404bf7787b135ed00424e624af43d42c6ab"
    )
    assert manifest["upstream"]["commit"] == (
        "31286d64541791a9815d29443a33726fa4d54031"
    )
    assert {item["classification"] for item in manifest["components"]} == {
        1,
        2,
        3,
        4,
        5,
        6,
    }


def test_guard_fails_if_required_attribution_is_removed(tmp_path: Path) -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for relative in ("HYTOOLS_PROVENANCE.md", "NOTICE", "provenance/hytools.json"):
        source = REPO_ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    for component in manifest["components"]:
        path_value = component["spectralbridge_path"]
        if ";" in path_value or "*" in path_value:
            continue
        source = REPO_ROOT / path_value
        target = tmp_path / path_value
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    target = tmp_path / "src/spectralbridge/standard_resample.py"
    source_text = target.read_text(encoding="utf-8")
    target.write_text(
        source_text.replace("Copyright (C) 2021 University of Wisconsin", "", 1),
        encoding="utf-8",
    )

    result = _run("--repo-root", str(tmp_path))
    assert result.returncode == 1
    assert "missing required marker" in result.stderr


def test_release_metadata_includes_notice_and_excludes_root_deprecated_tree() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert 'license-files = ["LICENSE", "NOTICE"]' in pyproject
    assert "include HYTOOLS_PROVENANCE.md" in manifest
    assert "recursive-include provenance *.json" in manifest
    assert "prune deprecated" in manifest
