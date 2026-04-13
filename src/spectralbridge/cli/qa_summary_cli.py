"""CLI entry point for the aggregate drone QA PDF summary."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from spectralbridge._cli_compat import warn_if_legacy_command

from ..utils.qa_summary import build_drone_qa_summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a multi-page PDF summary for drone QA PNGs.",
    )
    parser.add_argument(
        "base_dir",
        type=Path,
        help="Base drone output directory to search recursively for *__qa.png files.",
    )
    parser.add_argument(
        "--output-pdf",
        type=Path,
        help="Optional PDF output path. Defaults to <base_dir>/qa_summary.pdf.",
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
    pdf_path = build_drone_qa_summary(
        args.base_dir,
        output_html=args.output_pdf,
        pattern=args.pattern,
    )
    print(pdf_path)


__all__ = ["main"]
