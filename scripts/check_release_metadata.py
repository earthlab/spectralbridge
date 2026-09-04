#!/usr/bin/env python3
"""Fail unless release-facing version metadata matches a requested tag."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def _match(path: Path, pattern: str, *, label: str) -> str:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise RuntimeError(f"Could not find {label} in {path}")
    return match.group(1)


def collect_versions(root: Path = ROOT) -> dict[str, str]:
    """Return the release versions declared by authoritative repository files."""

    pyproject = _match(
        root / "pyproject.toml",
        r'^version\s*=\s*["\']([^"\']+)["\']',
        label="project version",
    )
    package = _match(
        root / "src" / "spectralbridge" / "__init__.py",
        r'^__version__\s*=\s*["\']([^"\']+)["\']',
        label="package version",
    )
    citation = _match(
        root / "CITATION.cff",
        r'^version:\s*["\']?([^"\'\s]+)',
        label="citation version",
    )
    changelog = _match(
        root / "CHANGELOG.md",
        r'^##\s+\[([0-9]+\.[0-9]+\.[0-9]+)\]',
        label="first semantic-version changelog heading",
    )
    return {
        "pyproject": pyproject,
        "package": package,
        "citation": citation,
        "changelog": changelog,
    }


def validate_release_tag(tag: str, root: Path = ROOT) -> dict[str, str]:
    """Validate ``vMAJOR.MINOR.PATCH`` and all repository version declarations."""

    match = re.fullmatch(r"v([0-9]+\.[0-9]+\.[0-9]+)", tag.strip())
    if match is None:
        raise RuntimeError(f"Release tag must use vMAJOR.MINOR.PATCH: {tag!r}")
    expected = match.group(1)
    versions = collect_versions(root)
    mismatches = {name: value for name, value in versions.items() if value != expected}
    if mismatches:
        rendered = ", ".join(f"{name}={value}" for name, value in mismatches.items())
        raise RuntimeError(f"Release metadata does not match {tag}: {rendered}")
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Expected vMAJOR.MINOR.PATCH tag")
    args = parser.parse_args()
    versions = validate_release_tag(args.tag)
    print(f"Release metadata matches {args.tag}: {versions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
