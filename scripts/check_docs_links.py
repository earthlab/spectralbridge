#!/usr/bin/env python3
"""Check documentation links and, optionally, marker comments.

This script scans Markdown files in the ``docs`` directory and ensures local
Markdown links resolve. Marker comments such as ``<!-- FILLME:START -->`` are
reported by default because this repo uses them intentionally while drafts are
being filled. Pass ``--fail-on-fillme`` for a publication gate that requires
marker-free docs.

The script exits with a non-zero status if broken links are detected, or if
``--fail-on-fillme`` is used and marker comments remain.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Iterable
from urllib.parse import unquote


def extract_links(text: str) -> Iterable[str]:
    """Return an iterable of links found in Markdown text."""
    pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)|\[[^\]]*\]\(([^)]+)\)")
    for match in pattern.findall(text):
        # ``findall`` with alternation returns tuples; pick the non-empty part.
        link = match[0] or match[1]
        yield link.strip()


def iter_markdown_files(docs_dir: pathlib.Path) -> Iterable[pathlib.Path]:
    """Yield source Markdown files, excluding generated build output."""

    for md_file in sorted(docs_dir.rglob("*.md")):
        if "_build" in md_file.parts:
            continue
        yield md_file


FILLME_MARKER_RE = re.compile(r"<!--\s*FILLME(?::|-|\s)", re.IGNORECASE)


def check_file(
    md_file: pathlib.Path,
    *,
    fail_on_fillme: bool,
) -> tuple[list[str], list[str]]:
    """Check a single markdown file for broken links and optional markers."""
    errors: list[str] = []
    warnings: list[str] = []
    text = md_file.read_text(encoding="utf-8")

    if FILLME_MARKER_RE.search(text):
        message = f"FILLME marker found in {md_file}"
        if fail_on_fillme:
            errors.append(message)
        else:
            warnings.append(message)

    for link in extract_links(text):
        if link.startswith("http://") or link.startswith("https://"):
            continue
        if link.startswith("#") or link.startswith("mailto:"):
            continue
        cleaned = link.split("#", 1)[0].split("?", 1)[0]
        if not cleaned:
            continue
        target = (md_file.parent / unquote(cleaned)).resolve()
        if not target.exists():
            errors.append(f"Broken link in {md_file}: {link}")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fail-on-fillme",
        action="store_true",
        help="Treat FILLME markers as errors instead of warnings.",
    )
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parent.parent
    docs_dir = repo_root / "docs"

    all_errors: list[str] = []
    all_warnings: list[str] = []
    for md_file in iter_markdown_files(docs_dir):
        errors, warnings = check_file(md_file, fail_on_fillme=args.fail_on_fillme)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    for warning in all_warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        return 1
    print("All doc links valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
