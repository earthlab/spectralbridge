#!/usr/bin/env python3
"""Fail unless release identity metadata matches a requested tag."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = r"[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?"
EXPECTED_DISTRIBUTION_NAME = "earthlab-spectralbridge"
EXPECTED_IMPORT_PACKAGE = "spectralbridge"


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
        rf'^##\s+\[({VERSION_PATTERN})\]',
        label="first semantic-version changelog heading",
    )
    return {
        "pyproject": pyproject,
        "package": package,
        "citation": citation,
        "changelog": changelog,
    }


def collect_release_identity(root: Path = ROOT) -> dict[str, str]:
    """Return the distribution and import identities declared by the source tree."""

    distribution_name = _match(
        root / "pyproject.toml",
        r'^name\s*=\s*["\']([^"\']+)["\']',
        label="project distribution name",
    )
    import_init = root / "src" / EXPECTED_IMPORT_PACKAGE / "__init__.py"
    if not import_init.is_file():
        raise RuntimeError(
            f"Expected import package {EXPECTED_IMPORT_PACKAGE!r} at {import_init}"
        )
    return {
        "distribution_name": distribution_name,
        "import_package": EXPECTED_IMPORT_PACKAGE,
    }


def validate_release_tag(tag: str, root: Path = ROOT) -> dict[str, str]:
    """Validate a PEP 440 final/pre-release tag and repository declarations."""

    match = re.fullmatch(rf"v({VERSION_PATTERN})", tag.strip())
    if match is None:
        raise RuntimeError(
            "Release tag must use vMAJOR.MINOR.PATCH with an optional "
            f"PEP 440 aN, bN, or rcN suffix: {tag!r}"
        )
    expected = match.group(1)
    identity = collect_release_identity(root)
    if identity["distribution_name"] != EXPECTED_DISTRIBUTION_NAME:
        raise RuntimeError(
            "Release distribution name must be "
            f"{EXPECTED_DISTRIBUTION_NAME!r}, found "
            f"{identity['distribution_name']!r}"
        )
    versions = collect_versions(root)
    mismatches = {name: value for name, value in versions.items() if value != expected}
    if mismatches:
        rendered = ", ".join(f"{name}={value}" for name, value in mismatches.items())
        raise RuntimeError(f"Release metadata does not match {tag}: {rendered}")
    return {**identity, **versions}


def is_prerelease_version(version: str) -> bool:
    """Return whether a validated release version has a pre-release suffix."""

    if re.fullmatch(VERSION_PATTERN, version) is None:
        raise RuntimeError(f"Invalid release version: {version!r}")
    return re.search(r"(?:a|b|rc)[0-9]+$", version) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag", required=True, help="Expected vMAJOR.MINOR.PATCH[rcN] tag"
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        help="Optional GitHub Actions output file receiving version metadata",
    )
    args = parser.parse_args()
    versions = validate_release_tag(args.tag)
    if args.github_output is not None:
        version = versions["pyproject"]
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"version={version}\n")
            stream.write(
                f"is_prerelease={str(is_prerelease_version(version)).lower()}\n"
            )
    print(f"Release metadata matches {args.tag}: {versions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
