"""CLI entry point for the scrollable drone QA HTML summary."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from spectralbridge._cli_compat import warn_if_legacy_command

from ..utils.qa_summary import build_drone_qa_summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a scrollable HTML summary page for drone QA PNGs.",
    )
    parser.add_argument(
        "base_dir",
        type=Path,
        help="Base drone output directory to search recursively for *__qa.png files.",
    )
    parser.add_argument(
        "--output-html",
        type=Path,
        help="Optional HTML output path. Defaults to <base_dir>/qa_summary.html.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*__qa.png",
        help="Recursive filename pattern used to find QA PNGs.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    warn_if_legacy_command()

    parser = _build_parser()
    args = parser.parse_args(argv)
    html_path = build_drone_qa_summary(
        args.base_dir,
        output_html=args.output_html,
        pattern=args.pattern,
    )
    print(html_path)


__all__ = ["main"]
