"""Contracts for the release metadata synchronization gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


def _load_script() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_release_metadata.py"
    spec = importlib.util.spec_from_file_location("release_metadata_check", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CHECK = _load_script()


def _write_release_files(root: Path, *, version: str) -> None:
    (root / "src" / "spectralbridge").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "spectralbridge"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (root / "src" / "spectralbridge" / "__init__.py").write_text(
        f'__version__ = "{version}"\n', encoding="utf-8"
    )
    (root / "CITATION.cff").write_text(f'version: "{version}"\n', encoding="utf-8")
    (root / "CHANGELOG.md").write_text(f"## [{version}] - release\n", encoding="utf-8")


def test_release_metadata_gate_accepts_synchronized_version(tmp_path: Path) -> None:
    _write_release_files(tmp_path, version="2.4.0")
    assert CHECK.validate_release_tag("v2.4.0", tmp_path) == {
        "pyproject": "2.4.0",
        "package": "2.4.0",
        "citation": "2.4.0",
        "changelog": "2.4.0",
    }


def test_release_metadata_gate_rejects_mismatch(tmp_path: Path) -> None:
    _write_release_files(tmp_path, version="2.4.0")
    with pytest.raises(RuntimeError, match="does not match"):
        CHECK.validate_release_tag("v2.5.0", tmp_path)


def test_release_metadata_gate_rejects_unversioned_tag(tmp_path: Path) -> None:
    _write_release_files(tmp_path, version="2.4.0")
    with pytest.raises(RuntimeError, match="vMAJOR.MINOR.PATCH"):
        CHECK.validate_release_tag("release-2.4.0", tmp_path)
