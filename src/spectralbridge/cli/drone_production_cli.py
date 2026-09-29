"""Command-line interface for remote drone campaign production."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from spectralbridge.drone_production import (
    DroneCampaignConfig,
    inspect_drone_collection,
    run_drone_bulk_production,
    run_drone_campaign,
)


def _common_campaign_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source", help="Remote source collection, such as i:/iplant/...")
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--years", type=int, nargs="+", required=True)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument(
        "--keep-inputs",
        action="store_true",
        help="Keep staged source H5 files after canonical bulk readiness passes.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Explicitly permit bulk analysis of the completed subset.",
    )
    parser.add_argument(
        "--no-landsat-qa",
        action="store_true",
        help="Disable optional actual-Landsat comparison QA.",
    )
    parser.add_argument("--extraction-workers", type=int, default=1)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory, process, and analyze a remote drone campaign."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inventory = subparsers.add_parser("inventory", help="Inspect without downloading H5s.")
    inventory.add_argument("source")
    inventory.add_argument("--years", type=int, nargs="*", default=())
    inventory.add_argument("--manifest", type=Path, default=None)
    inventory.add_argument("--output-dir", type=Path, default=None)

    campaign = subparsers.add_parser(
        "campaign", help="Stage and process each eligible flight independently."
    )
    _common_campaign_arguments(campaign)

    bulk = subparsers.add_parser(
        "bulk", help="Run the complete producer, bulk, report, package workflow."
    )
    _common_campaign_arguments(bulk)
    bulk.add_argument(
        "--upload-results",
        action="store_true",
        help="Upload and verify the compact closeout package beneath the source.",
    )
    return parser


def _config(args: argparse.Namespace) -> DroneCampaignConfig:
    return DroneCampaignConfig(
        years=tuple(args.years),
        manifest_path=args.manifest,
        cleanup_inputs=not args.keep_inputs,
        require_complete_campaign=not args.allow_partial,
        landsat_qa=not args.no_landsat_qa,
        extraction_workers=args.extraction_workers,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command == "inventory":
        result = inspect_drone_collection(
            args.source,
            manifest=args.manifest,
            years=args.years,
            inventory_output_dir=args.output_dir,
        )
        payload = result.to_dict()
    elif args.command == "campaign":
        result = run_drone_campaign(
            args.source,
            work_dir=args.work_dir,
            config=_config(args),
        )
        payload = result.to_dict()
    else:
        result = run_drone_bulk_production(
            source=args.source,
            years=args.years,
            work_dir=args.work_dir,
            manifest=args.manifest,
            config=_config(args),
            upload_results=args.upload_results,
            require_complete_campaign=not args.allow_partial,
        )
        payload = result.to_dict()
    print(json.dumps(payload, indent=2, sort_keys=True))


__all__ = ["main"]
