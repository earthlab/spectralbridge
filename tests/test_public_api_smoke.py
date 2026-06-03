"""Smoke coverage for intentionally public SpectralBridge exports."""

from __future__ import annotations

from contextlib import contextmanager
import importlib
import inspect
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@contextmanager
def _repo_import_context():
    saved_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "spectralbridge" or name.startswith("spectralbridge.")
    }
    for name in saved_modules:
        sys.modules.pop(name, None)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        for name in list(sys.modules):
            if name == "spectralbridge" or name.startswith("spectralbridge."):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        importlib.invalidate_caches()


def _iter_public_exports() -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    module_names = (
        "spectralbridge",
        "spectralbridge.cli",
        "spectralbridge.pipelines",
    )
    with _repo_import_context():
        for module_name in module_names:
            module = importlib.import_module(module_name)
            for export_name in getattr(module, "__all__", ()):
                exported = getattr(module, export_name, None)
                if callable(exported):
                    entries.append((module_name, export_name))
    return tuple(sorted(set(entries)))


PUBLIC_EXPORTS = _iter_public_exports()


def test_public_function_smoke_matrix_is_not_empty() -> None:
    assert PUBLIC_EXPORTS


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    PUBLIC_EXPORTS,
    ids=[f"{module}.{name}" for module, name in PUBLIC_EXPORTS],
)
def test_public_function_import_and_signature_smoke(
    module_name: str,
    function_name: str,
) -> None:
    with _repo_import_context():
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)

        assert callable(function)
        inspect.signature(function)


def test_only_expected_top_level_packages_are_present() -> None:
    packages = {
        path.name
        for path in SRC_ROOT.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    }

    assert packages == {"cross_sensor_cal", "spectralbridge"}


def test_common_orchestration_helpers_are_available_at_top_level() -> None:
    with _repo_import_context():
        import spectralbridge
        from spectralbridge.pipelines.pipeline import (
            go_forth_and_multiply,
            process_one_flightline,
        )

        assert spectralbridge.go_forth_and_multiply is go_forth_and_multiply
        assert spectralbridge.process_one_flightline is process_one_flightline


def test_cli_backwards_compatibility_exports_are_available() -> None:
    with _repo_import_context():
        from spectralbridge import cli

        assert callable(cli.download_main)
        assert callable(cli.pipeline_main)
        assert callable(cli.qa_main)
