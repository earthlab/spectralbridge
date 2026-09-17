#!/usr/bin/env python3
"""Build the packaged drone coefficient registry from compact bulk outputs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from spectralbridge.drone_translation_registry import (
    DRONE_TRANSLATION_COEFFICIENT_RESOURCE,
    DRONE_TRANSLATION_COEFFICIENT_SET_VERSION,
    build_drone_translation_coefficient_registry,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bulk_output",
        type=Path,
        help="Completed bulk output containing compact coefficient and QA products.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(__file__).resolve().parents[1]
            / "src"
            / "spectralbridge"
            / "data"
            / DRONE_TRANSLATION_COEFFICIENT_RESOURCE
        ),
        help="Versioned JSON registry to write.",
    )
    parser.add_argument(
        "--coefficient-set-version",
        default=DRONE_TRANSLATION_COEFFICIENT_SET_VERSION,
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--candidate-coefficients",
        type=Path,
        help="Original candidate Parquet when the supplied folder is flattened or renamed.",
    )
    parser.add_argument(
        "--bulk-results-summary",
        type=Path,
        help="Completed bulk-results JSON when the supplied folder is flattened or renamed.",
    )
    args = parser.parse_args(argv)
    overrides = {
        name: path
        for name, path in (
            ("candidate_coefficients", args.candidate_coefficients),
            ("bulk_results_summary", args.bulk_results_summary),
        )
        if path is not None
    }
    output = build_drone_translation_coefficient_registry(
        args.bulk_output,
        args.output,
        coefficient_set_version=args.coefficient_set_version,
        overwrite=args.overwrite,
        artifact_paths=overrides,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
