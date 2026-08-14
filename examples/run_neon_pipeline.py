#!/usr/bin/env python3
"""Run the complete restart-safe NEON SpectralBridge workflow from JSON.

This is a user-facing wrapper around ``spectralbridge.go_forth_and_multiply``.
It contains no scientific processing logic. Use ``--check`` to validate the
configuration without downloading or processing data.

Examples
--------
python examples/run_neon_pipeline.py --check
python examples/run_neon_pipeline.py --config examples/config/neon_pipeline.example.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "examples" / "config" / "neon_pipeline.example.json"
REQUIRED_KEYS = {"base_folder", "site_code", "year_month", "flight_lines"}
ALLOWED_KEYS = {
    "base_folder",
    "site_code",
    "year_month",
    "flight_lines",
    "product_code",
    "resample_method",
    "brightness_offset",
    "use_ndvi_brdf_bins",
    "max_workers",
    "parquet_chunk_size",
    "engine",
    "merge_memory_limit_gb",
    "merge_threads",
    "merge_row_group_size",
    "merge_temp_directory",
    "polygon_path",
    "polygon_pixel_size",
    "polygon_overwrite",
    "polygon_min_overlap",
    "polygon_search_buffer_m",
    "extraction_mode",
    "topo_fit_mode",
}
PATH_KEYS = {"base_folder", "merge_temp_directory", "polygon_path"}


def _ensure_importable() -> None:
    """Allow a fresh clone to run before an editable install."""

    src = REPO_ROOT / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _repo_path(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate the example configuration schema."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Expected schema_version 1")
    config = payload.get("pipeline")
    if not isinstance(config, dict):
        raise ValueError("Expected a JSON object at pipeline")
    missing = sorted(REQUIRED_KEYS - config.keys())
    unknown = sorted(config.keys() - ALLOWED_KEYS)
    if missing:
        raise ValueError(f"Missing pipeline keys: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"Unknown pipeline keys: {', '.join(unknown)}")
    if not isinstance(config["flight_lines"], list) or not config["flight_lines"]:
        raise ValueError("pipeline.flight_lines must be a non-empty list")
    if int(config.get("max_workers", 1)) < 1:
        raise ValueError("pipeline.max_workers must be at least 1")
    resolved = dict(config)
    for key in PATH_KEYS & resolved.keys():
        resolved[key] = _repo_path(resolved[key])
    return resolved


def describe(config: dict[str, Any]) -> None:
    """Print the resolved run without opening data or contacting NEON."""

    print("SpectralBridge NEON pipeline configuration")
    print(f"  output: {config['base_folder']}")
    print(f"  site/month: {config['site_code']} / {config['year_month']}")
    print(f"  flightlines: {len(config['flight_lines'])}")
    print(f"  engine/workers: {config.get('engine', 'ray')} / {config.get('max_workers', 8)}")
    print(f"  extraction: {config.get('extraction_mode', 'automatic')}")
    print("  stages: download → raw ENVI → topo/BRDF → sensor convolution → Parquet → QA")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and print configuration without running the pipeline.",
    )
    args = parser.parse_args(argv)
    config_path = args.config.expanduser().resolve()
    config = load_config(config_path)
    describe(config)
    if args.check:
        print("Configuration is valid; no network or processing work was performed.")
        return 0

    _ensure_importable()
    from spectralbridge import go_forth_and_multiply

    go_forth_and_multiply(**config)
    print(f"Pipeline complete. Inspect outputs and QA under {config['base_folder']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

