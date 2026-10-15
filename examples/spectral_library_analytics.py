"""Staged experimental library analytics; explicit original/compact paths."""

from pathlib import Path
import argparse
import logging
import json
from spectralbridge.spectral_library_analytics import profile_learning, run_learning
from spectralbridge.spectral_learning import LearningConfig


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument("--compact", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--stage",
        choices=["profile", "learning", "extensions", "domains", "mixtures", "all"],
        default="profile",
    )
    p.add_argument("--first-pass", action="store_true")
    p.add_argument(
        "--previous-mixtures",
        type=Path,
        default=Path("provenance/mesma-readiness/2026-10-14/tables"),
    )
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--bootstraps", type=int, default=499)
    args = p.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    config = LearningConfig(bootstraps=args.bootstraps)
    sealed = args.output / "learning_manifest.json"
    if sealed.exists() and json.loads(sealed.read_text()).get("status") == "complete":
        if args.stage not in {"all", "learning"}:
            p.error(
                "Completed output is sealed; use a fresh output directory for profiling or secondary stages"
            )
        run_learning(
            args.source,
            args.compact,
            args.output,
            config=config,
            first_pass=args.first_pass,
            workers=args.workers,
        )
        return
    if args.stage in {"profile", "all"}:
        profile_learning(args.source, args.compact, args.output, config)
    if args.stage in {"extensions", "all"}:
        from spectralbridge.spectral_analytics_extensions import run_extensions

        run_extensions(args.source, args.compact, args.output, config=config)
    if args.stage in {"domains", "all"}:
        from spectralbridge.spectral_analytics_extensions import run_domains

        run_domains(args.source, args.compact, args.output, config=config)
    if args.stage in {"mixtures", "all"}:
        from spectralbridge.spectral_analytics_mixtures import run_selected_mixtures

        run_selected_mixtures(
            args.source, args.compact, args.output, args.previous_mixtures
        )
    if args.stage in {"learning", "all"}:
        run_learning(
            args.source,
            args.compact,
            args.output,
            config=config,
            first_pass=args.first_pass,
            workers=args.workers,
        )


if __name__ == "__main__":
    main()
