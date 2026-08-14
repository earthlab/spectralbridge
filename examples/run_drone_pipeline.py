#!/usr/bin/env python3
"""Run the local-input drone SpectralBridge workflow from JSON.

This wrapper calls ``spectralbridge.run_drone_pipeline`` and deliberately does
not enter the NEON download or sensor-convolution workflow. Use ``--check`` to
validate paths and options without reading imagery.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "examples" / "config" / "drone_pipeline.example.json"
REQUIRED_KEYS = {"input_h5_dir", "output_dir"}
ALLOWED_KEYS = {
    "input_h5_dir",
    "polygon_path",
    "output_dir",
    "apply_topo",
    "apply_brdf",
    "use_ndvi_brdf_bins",
    "apply_brightness_adjustment",
    "overwrite",
    "tiff_wavelengths_nm",
    "tiff_fwhm_nm",
    "tiff_solar_zenith_deg",
    "tiff_solar_azimuth_deg",
    "tiff_sensor_zenith_deg",
    "tiff_sensor_azimuth_deg",
    "drone_manifest_path",
    "require_solar_geometry",
}
PATH_KEYS = {"input_h5_dir", "polygon_path", "output_dir", "drone_manifest_path"}


def _ensure_importable() -> None:
    src = REPO_ROOT / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _repo_path(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    """Load and validate the drone example configuration."""

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
    resolved = dict(config)
    for key in PATH_KEYS & resolved.keys():
        resolved[key] = _repo_path(resolved[key])
    return resolved


def describe(config: dict[str, Any]) -> None:
    print("SpectralBridge drone pipeline configuration")
    print(f"  input: {config['input_h5_dir']}")
    print(f"  output: {config['output_dir']}")
    print(f"  polygon extraction: {config.get('polygon_path') or 'disabled'}")
    print(f"  topo / BRDF: {config.get('apply_topo', True)} / {config.get('apply_brdf', True)}")
    print("  convolution: skipped by the drone workflow contract")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and print configuration without reading imagery.",
    )
    args = parser.parse_args(argv)
    config = load_config(args.config.expanduser().resolve())
    describe(config)
    if args.check:
        print("Configuration is valid; no imagery was read or written.")
        return 0

    _ensure_importable()
    from spectralbridge import run_drone_pipeline

    result = run_drone_pipeline(**config)
    print(f"Processed: {len(result.get('processed', []))}")
    print(f"Failed: {len(result.get('failed', []))}")
    print(f"QA summary: {result.get('qa_summary_path')}")
    return 1 if result.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())

