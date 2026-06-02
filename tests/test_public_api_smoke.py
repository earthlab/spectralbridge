"""Smoke coverage for public SpectralBridge functions."""

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
SPECTRALBRIDGE_ROOT = SRC_ROOT / "spectralbridge"


def _module_name(path: Path) -> str:
    return ".".join(path.relative_to(SRC_ROOT).with_suffix("").parts)


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
