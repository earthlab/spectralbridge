"""Smoke coverage for public SpectralBridge functions."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SPECTRALBRIDGE_ROOT = SRC_ROOT / "spectralbridge"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _ensure_repo_package_preferred() -> None:
    for name, module in list(sys.modules.items()):
        if name != "spectralbridge" and not name.startswith("spectralbridge."):
            continue

        module_file = getattr(module, "__file__", None)
        if module_file is not None and Path(module_file).resolve().is_relative_to(SRC_ROOT):
            continue
        sys.modules.pop(name, None)


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(SRC_ROOT).with_suffix("").parts)


def _module_path(module_name: str) -> Path:
    parts = module_name.split(".")
    file_path = SRC_ROOT.joinpath(*parts).with_suffix(".py")
    if file_path.exists():
        return file_path

    package_init = SRC_ROOT.joinpath(*parts, "__init__.py")
    if package_init.exists():
        return package_init

    raise ModuleNotFoundError(module_name)


def _load_repo_module(module_name: str):
    _ensure_repo_package_preferred()

    cached = sys.modules.get(module_name)
    if cached is not None:
        module_file = getattr(cached, "__file__", None)
        if module_file is not None and Path(module_file).resolve().is_relative_to(SRC_ROOT):
            return cached

    module_path = _module_path(module_name)
    if module_path.name == "__init__.py":
        submodule_locations = [str(module_path.parent)]
    else:
        parent_name = module_name.rsplit(".", 1)[0]
        if "." in module_name:
            _load_repo_module(parent_name)
        submodule_locations = None

    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
        submodule_search_locations=submodule_locations,
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ModuleNotFoundError(module_name)

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _iter_public_functions() -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    for path in sorted(SPECTRALBRIDGE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_name = _module_name(path)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    entries.append((module_name, node.name))
    return tuple(entries)


PUBLIC_FUNCTIONS = _iter_public_functions()


def test_public_function_smoke_matrix_is_not_empty() -> None:
    assert PUBLIC_FUNCTIONS


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    PUBLIC_FUNCTIONS,
    ids=[f"{module}.{name}" for module, name in PUBLIC_FUNCTIONS],
)
def test_public_function_import_and_signature_smoke(
    module_name: str,
    function_name: str,
) -> None:
    module = _load_repo_module(module_name)
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
    _ensure_repo_package_preferred()
    import spectralbridge
    from spectralbridge.pipelines.pipeline import (
        go_forth_and_multiply,
        process_one_flightline,
    )

    assert spectralbridge.go_forth_and_multiply is go_forth_and_multiply
    assert spectralbridge.process_one_flightline is process_one_flightline
