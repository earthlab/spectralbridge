#!/usr/bin/env python3
"""Check an installed SpectralBridge release candidate without scientific data.

Install the exact candidate first, then run this downloaded script from outside
the source checkout. For example::

    python -m pip install --pre "earthlab-spectralbridge==2.3.0rc1"
    python release_candidate_smoke.py --expected-version 2.3.0rc1

This checks release identity, public API imports, and installed console scripts.
It does not validate scientific results or production-scale behavior.
"""

from __future__ import annotations

import argparse
from importlib.metadata import distribution, entry_points
import json
from pathlib import Path
import sys

import spectralbridge
from spectralbridge import (
    build_harmonized_dataset,
    go_forth_and_multiply,
    inspect_spectral_library_preflight,
    run_bulk_pipeline,
    run_drone_pipeline,
    run_spectral_library_analysis,
    summarize_bulk_results,
)


EXPECTED_APIS = {
    "go_forth_and_multiply": go_forth_and_multiply,
    "run_drone_pipeline": run_drone_pipeline,
    "run_bulk_pipeline": run_bulk_pipeline,
    "summarize_bulk_results": summarize_bulk_results,
    "run_spectral_library_analysis": run_spectral_library_analysis,
    "inspect_spectral_library_preflight": inspect_spectral_library_preflight,
    "build_harmonized_dataset": build_harmonized_dataset,
}
EXPECTED_CLIS = (
    "spectralbridge-pipeline",
    "spectralbridge-bulk",
    "spectralbridge-qa",
    "spectralbridge-stage-qa",
)
EXPECTED_DISTRIBUTION = "earthlab-spectralbridge"
EXPECTED_IMPORT_PACKAGE = "spectralbridge"


def validate_installation(expected_version: str) -> dict[str, object]:
    """Return a machine-readable installation check or raise on failure."""

    installed_distribution = distribution(EXPECTED_DISTRIBUTION)
    distribution_name = installed_distribution.metadata["Name"]
    if distribution_name != EXPECTED_DISTRIBUTION:
        raise RuntimeError(
            f"Expected distribution {EXPECTED_DISTRIBUTION}, found {distribution_name}"
        )
    if installed_distribution.version != expected_version:
        raise RuntimeError(
            f"Expected distribution version {expected_version}, found "
            f"{installed_distribution.version}"
        )
    if spectralbridge.__version__ != expected_version:
        raise RuntimeError(
            f"Expected spectralbridge {expected_version}, found "
            f"{spectralbridge.__version__}"
        )
    invalid = sorted(name for name, value in EXPECTED_APIS.items() if not callable(value))
    if invalid:
        raise RuntimeError(f"Public APIs are not callable: {invalid}")
    declared = {item.name for item in entry_points(group="console_scripts")}
    missing = sorted(name for name in EXPECTED_CLIS if name not in declared)
    scripts_dir = Path(sys.executable).parent
    unavailable = sorted(
        name
        for name in EXPECTED_CLIS
        if not (scripts_dir / name).is_file()
        and not (scripts_dir / f"{name}.exe").is_file()
    )
    if missing or unavailable:
        raise RuntimeError(
            f"Console scripts incomplete: metadata={missing}, PATH={unavailable}"
        )
    return {
        "status": "PASS",
        "validation_scope": "installation_and_public_api_only",
        "distribution_name": distribution_name,
        "import_package": EXPECTED_IMPORT_PACKAGE,
        "version": spectralbridge.__version__,
        "module": spectralbridge.__file__,
        "public_apis": sorted(EXPECTED_APIS),
        "console_scripts": list(EXPECTED_CLIS),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-version", default="2.3.0rc1")
    args = parser.parse_args()
    print(json.dumps(validate_installation(args.expected_version), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
