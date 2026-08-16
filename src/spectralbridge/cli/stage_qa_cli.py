"""CLI for deterministic stage-by-stage QA on completed flightlines."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from spectralbridge.qa.runner import run_completed_flightline_qa


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build stage and combined QA reports from a flightline directory."
    )
    parser.add_argument("--flightline-dir", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=["standard", "deep"], default="standard"
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--topo-fit-mode", choices=["scene", "tile"], default="scene"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    reports = run_completed_flightline_qa(
        args.flightline_dir,
        mode=args.mode,
        force=args.force,
        topo_fit_mode=args.topo_fit_mode,
    )
    combined = reports["combined"]
    print(f"[spectralbridge-stage-qa] {combined['report']['status']} {combined['html']}")


__all__ = ["main"]


if __name__ == "__main__":  # pragma: no cover - console passthrough
    main()
