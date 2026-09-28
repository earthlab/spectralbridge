#!/usr/bin/env python3
"""Offline guardrail for the documented SpectralBridge/HyTools relationship.

The default check needs only the SpectralBridge checkout.  Pass a local HyTools
checkout with ``--hytools-root`` to verify its pinned revision and re-check the
Category 1 function-level matches.  This script never accesses the network.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


DEFAULT_MANIFEST = Path("provenance/hytools.json")
REQUIRED_REPOSITORY_FILES = (
    Path("HYTOOLS_PROVENANCE.md"),
    Path("NOTICE"),
    DEFAULT_MANIFEST,
)


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"provenance manifest is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"provenance manifest is invalid JSON: {path}: {exc}") from exc

    if data.get("schema_version") != 1:
        raise ValueError("provenance manifest schema_version must be 1")
    if not data.get("components"):
        raise ValueError("provenance manifest has no component records")
    return data


def _single_path(value: str) -> Path | None:
    """Return a literal path, or None for grouped/glob manifest entries."""

    if ";" in value or "*" in value:
        return None
    return Path(value)


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            del body[0]
    return tree


def _function_asts(path: Path) -> dict[str, list[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError(f"cannot parse Python source {path}: {exc}") from exc

    found: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            normalized = _strip_docstrings(node)
            dump = ast.dump(normalized, annotate_fields=True, include_attributes=False)
            found.setdefault(node.name, []).append(dump)
    return found


def _git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"not a readable Git checkout: {path}")
    return result.stdout.strip()


def audit(repo_root: Path, manifest_path: Path, hytools_root: Path | None) -> list[str]:
    errors: list[str] = []
    manifest = _load_manifest(manifest_path)

    for relative in REQUIRED_REPOSITORY_FILES:
        if not (repo_root / relative).is_file():
            errors.append(f"required provenance file is missing: {relative}")

    categories_seen: set[int] = set()
    for index, component in enumerate(manifest["components"], start=1):
        category = component.get("classification")
        if category not in {1, 2, 3, 4, 5, 6}:
            errors.append(f"component {index} has invalid classification: {category!r}")
            continue
        categories_seen.add(category)

        path_value = component.get("spectralbridge_path", "")
        local_relative = _single_path(path_value)
        markers = component.get("required_markers", [])
        if local_relative is None:
            if markers:
                errors.append(
                    f"component {index} uses a grouped path but declares required markers"
                )
            continue

        local_path = repo_root / local_relative
        if not local_path.is_file():
            errors.append(f"classified source is missing: {local_relative}")
            continue
        try:
            source = local_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"classified source is not UTF-8 text: {local_relative}")
            continue
        for marker in markers:
            if marker not in source:
                errors.append(f"{local_relative} is missing required marker: {marker!r}")

    if categories_seen != {1, 2, 3, 4, 5, 6}:
        missing = sorted({1, 2, 3, 4, 5, 6} - categories_seen)
        errors.append(f"manifest does not exercise all classifications; missing {missing}")

    if hytools_root is not None:
        expected_commit = manifest["upstream"]["commit"]
        actual_commit = _git_head(hytools_root)
        if actual_commit != expected_commit:
            errors.append(
                "local HyTools checkout is not the pinned audit revision: "
                f"expected {expected_commit}, found {actual_commit}"
            )

        for component in manifest["components"]:
            if component.get("classification") != 1:
                continue
            local_relative = _single_path(component["spectralbridge_path"])
            upstream_relative = _single_path(component["upstream_path"])
            if local_relative is None or upstream_relative is None:
                continue
            local_path = repo_root / local_relative
            upstream_path = hytools_root / upstream_relative
            if not upstream_path.is_file():
                errors.append(f"pinned upstream source is missing: {upstream_relative}")
                continue
            local_functions = _function_asts(local_path)
            upstream_functions = _function_asts(upstream_path)
            exact_symbol_found = False
            for symbol in component.get("spectralbridge_symbols", []):
                left = local_functions.get(symbol, [])
                right = upstream_functions.get(symbol, [])
                if set(left) & set(right):
                    exact_symbol_found = True
                    break
            if not exact_symbol_found:
                errors.append(
                    "Category 1 function match is no longer reproducible for "
                    f"{local_relative} against {upstream_relative}; review and update the audit"
                )

    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="SpectralBridge checkout (default: repository containing this script)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="manifest path (default: <repo-root>/provenance/hytools.json)",
    )
    parser.add_argument(
        "--hytools-root",
        type=Path,
        default=None,
        help="optional local HyTools checkout at the pinned commit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    manifest_path = (
        args.manifest.resolve()
        if args.manifest is not None
        else repo_root / DEFAULT_MANIFEST
    )
    try:
        errors = audit(repo_root, manifest_path, args.hytools_root)
    except ValueError as exc:
        print(f"provenance audit failed: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("provenance audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    mode = "manifest and notices"
    if args.hytools_root is not None:
        mode += ", pinned checkout, and Category 1 function matches"
    print(f"HyTools provenance audit passed ({mode}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
