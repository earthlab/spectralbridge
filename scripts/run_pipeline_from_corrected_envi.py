#!/usr/bin/env python3
"""Resume SpectralBridge from an existing BRDF+topo corrected ENVI pair.

The NEON pipeline stages are already skip-if-valid, so a flight directory that
still holds ``*_brdfandtopo_corrected_envi.img/.hdr`` does not need correction
recomputed.  The only stage that is not skip-based is the NEON download, which
this script patches to a no-op.  Everything downstream (resampling, parquet
export, merge, QA) then runs normally.

Expected layout (pipeline contract)::

    <base_folder>/
      <flight_id>.h5                     # optional; not needed here
      <flight_id>/
        <flight_id>_envi.img/.hdr                        # reused if present
        <flight_id>_brdfandtopo_corrected_envi.img/.hdr  # REQUIRED
        <flight_id>_brdfandtopo_corrected_envi.json      # reused if present

Example::

    python scripts/run_pipeline_from_corrected_envi.py \\
      --flight-id NEON_D10_R10C_DP1_L005-1_20210915_directional_reflectance \\
      --base-folder NEON_TM_5 \\
      --extraction-mode full

Notebook use::

    import sys; sys.path.insert(0, "scripts")
    from run_pipeline_from_corrected_envi import run
    run(flight_id="...", base_folder="NEON_TM_5", extraction_mode="full")

Provenance
----------
Raw ENVI and the correction JSON are only stood in for when they are genuinely
missing.  Any substitution is recorded in
``<flight_dir>/<flight_id>_resume_from_corrected.json`` so QA readers can tell
that a stand-in raw ENVI is a copy of the corrected cube rather than an
independent uncorrected export.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# CONFIG — edit these for notebook use, or override via CLI flags
# =============================================================================

FLIGHT_ID = "NEON_D10_R10C_DP1_L005-1_20210915_directional_reflectance"

# Pipeline output root that already contains <flight_id>/ with corrected ENVI.
BASE_FOLDER = "NEON_TM_5"

EXTRACTION_MODE = "full"
POLYGON_PATH: str | None = None

TOPO_FIT_MODE = "scene"
ENGINE = "thread"
MAX_WORKERS = 1
PRODUCT_CODE = "DP1.30006.001"

# Allow a stand-in raw ENVI (copy/symlink of the corrected cube) when the real
# uncorrected export is gone. Keeps the run going, but raw-vs-corrected QA
# comparisons become meaningless for that flight.
ALLOW_RAW_ENVI_SUBSTITUTE = True

LOG_PREFIX = "[from-corrected]"
RESUME_MANIFEST_SUFFIX = "_resume_from_corrected.json"


def _repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "src" / "spectralbridge" / "pipelines").exists():
        return cwd
    if (cwd / "spectralbridge" / "src" / "spectralbridge" / "pipelines").exists():
        return cwd / "spectralbridge"
    here = Path(__file__).resolve().parent.parent
    if (here / "src" / "spectralbridge" / "pipelines").exists():
        return here
    raise FileNotFoundError(f"Cannot find spectralbridge repo root from cwd={cwd}")


def _ensure_src_on_path(repo_root: Path) -> None:
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class FlightInputs:
    """Resolved artefact paths and readiness for one flight directory."""

    flight_id: str
    flight_dir: Path
    h5: Path
    raw_img: Path
    raw_hdr: Path
    corrected_img: Path
    corrected_hdr: Path
    correction_json: Path
    h5_present: bool
    raw_envi_valid: bool
    corrected_envi_valid: bool
    correction_json_valid: bool
    substitutions: list[str] = field(default_factory=list)

    @property
    def raw_envi_independent_of_corrected(self) -> bool:
        return "raw_envi_from_corrected" not in self.substitutions


def inspect_flight_inputs(
    *,
    base_folder: Path | str,
    flight_id: str,
    product_code: str = PRODUCT_CODE,
) -> FlightInputs:
    """Resolve canonical artefact paths and report which ones are usable."""

    from spectralbridge.utils.naming import get_flightline_products
    from spectralbridge.utils_checks import is_valid_envi_pair, is_valid_json

    products = get_flightline_products(Path(base_folder), product_code, flight_id)

    raw_img = Path(products["raw_envi_img"])
    raw_hdr = Path(products["raw_envi_hdr"])
    corrected_img = Path(products["corrected_img"])
    corrected_hdr = Path(products["corrected_hdr"])
    correction_json = Path(products["correction_json"])
    h5 = Path(products["h5"])

    return FlightInputs(
        flight_id=flight_id,
        flight_dir=Path(products["work_dir"]),
        h5=h5,
        raw_img=raw_img,
        raw_hdr=raw_hdr,
        corrected_img=corrected_img,
        corrected_hdr=corrected_hdr,
        correction_json=correction_json,
        h5_present=h5.exists() and h5.is_file() and h5.stat().st_size > 0,
        raw_envi_valid=is_valid_envi_pair(raw_img, raw_hdr),
        corrected_envi_valid=is_valid_envi_pair(corrected_img, corrected_hdr),
        correction_json_valid=is_valid_json(correction_json),
    )


def _link_or_copy(source: Path, target: Path) -> str:
    """Point ``target`` at ``source``, preferring a symlink over a full copy."""

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(source)
        return "symlink"
    except OSError:
        print(f"{LOG_PREFIX} Symlink failed for {target.name}; copying instead…")
        shutil.copy2(source, target)
        return "copy"


def _write_correction_json_stub(inputs: FlightInputs) -> None:
    """Write a JSON that satisfies the stage gate without faking parameters."""

    payload = {
        "spectralbridge_resume_stub": True,
        "flight_stem": inputs.flight_id,
        "created_utc": _utc_now_iso(),
        "corrected_envi_img": inputs.corrected_img.name,
        "reason": (
            "Resumed from an existing BRDF+topo corrected ENVI pair; correction "
            "parameters were not recomputed because the source HDF5 was unavailable."
        ),
        "warning": (
            "This file carries no illumination geometry or BRDF coefficients. QA "
            "geometry panels will be empty for this flight."
        ),
    }
    inputs.correction_json.parent.mkdir(parents=True, exist_ok=True)
    inputs.correction_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_resume_manifest(inputs: FlightInputs) -> Path:
    """Record what was reused vs stood in for, next to the flight outputs."""

    manifest_path = inputs.flight_dir / f"{inputs.flight_id}{RESUME_MANIFEST_SUFFIX}"
    notes: list[str] = []
    if not inputs.raw_envi_independent_of_corrected:
        notes.append(
            "Raw ENVI is a stand-in for the corrected cube. Raw-vs-corrected QA "
            "deltas will be zero and *_envi.parquet holds corrected values."
        )
    if "correction_json_stub" in inputs.substitutions:
        notes.append(
            "Correction JSON is a stub; BRDF/topo geometry provenance is unavailable."
        )

    payload = {
        "created_utc": _utc_now_iso(),
        "entry_point": "scripts/run_pipeline_from_corrected_envi.py",
        "flight_id": inputs.flight_id,
        "flight_dir": str(inputs.flight_dir),
        "h5_present": inputs.h5_present,
        "resumed_from": {
            "corrected_img": inputs.corrected_img.name,
            "corrected_hdr": inputs.corrected_hdr.name,
        },
        "substitutions": sorted(inputs.substitutions),
        "raw_envi_independent_of_corrected": inputs.raw_envi_independent_of_corrected,
        "notes": notes,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def stage_corrected_envi_flight(
    *,
    base_folder: Path | str,
    flight_id: str,
    product_code: str = PRODUCT_CODE,
    allow_raw_envi_substitute: bool = ALLOW_RAW_ENVI_SUBSTITUTE,
    dry_run: bool = False,
) -> FlightInputs:
    """Verify a flight can resume from corrected ENVI and stage what is missing."""

    inputs = inspect_flight_inputs(
        base_folder=base_folder,
        flight_id=flight_id,
        product_code=product_code,
    )

    if not inputs.corrected_envi_valid:
        raise FileNotFoundError(
            f"{LOG_PREFIX} No valid corrected ENVI pair for {flight_id}:\n"
            f"  {inputs.corrected_img}\n"
            f"  {inputs.corrected_hdr}\n"
            "This entry point resumes from corrected ENVI; it cannot create it."
        )

    print(f"{LOG_PREFIX} {flight_id}")
    print(f"{LOG_PREFIX}   corrected ENVI: {inputs.corrected_img.name} (reuse)")
    print(f"{LOG_PREFIX}   source H5     : {'present' if inputs.h5_present else 'absent'}")

    if inputs.raw_envi_valid:
        print(f"{LOG_PREFIX}   raw ENVI      : {inputs.raw_img.name} (reuse)")
    elif not allow_raw_envi_substitute:
        raise FileNotFoundError(
            f"{LOG_PREFIX} Raw ENVI missing for {flight_id}:\n"
            f"  {inputs.raw_img}\n"
            "Pass allow_raw_envi_substitute=True (--allow-raw-substitute) to stand "
            "in the corrected cube, accepting that raw-vs-corrected QA becomes "
            "meaningless for this flight."
        )
    else:
        inputs.substitutions.append("raw_envi_from_corrected")
        if dry_run:
            print(f"{LOG_PREFIX}   raw ENVI      : MISSING → would substitute corrected")
        else:
            mode_img = _link_or_copy(inputs.corrected_img, inputs.raw_img)
            mode_hdr = _link_or_copy(inputs.corrected_hdr, inputs.raw_hdr)
            print(
                f"{LOG_PREFIX}   raw ENVI      : substituted from corrected "
                f"({mode_img}/{mode_hdr}) — raw-vs-corrected QA will be flat"
            )

    if inputs.correction_json_valid:
        print(f"{LOG_PREFIX}   correction JSON: {inputs.correction_json.name} (reuse)")
    else:
        inputs.substitutions.append("correction_json_stub")
        if dry_run:
            print(f"{LOG_PREFIX}   correction JSON: MISSING → would write stub")
        else:
            _write_correction_json_stub(inputs)
            print(f"{LOG_PREFIX}   correction JSON: stub written (no geometry)")

    if not dry_run:
        manifest_path = _write_resume_manifest(inputs)
        print(f"{LOG_PREFIX}   manifest: {manifest_path.name}")

    return inputs


def run(
    *,
    flight_id: str = FLIGHT_ID,
    flight_lines: list[str] | None = None,
    base_folder: Path | str = BASE_FOLDER,
    extraction_mode: str = EXTRACTION_MODE,
    polygon_path: Path | str | None = POLYGON_PATH,
    topo_fit_mode: str = TOPO_FIT_MODE,
    product_code: str = PRODUCT_CODE,
    engine: str = ENGINE,
    max_workers: int = MAX_WORKERS,
    allow_raw_envi_substitute: bool = ALLOW_RAW_ENVI_SUBSTITUTE,
    dry_run: bool = False,
) -> object:
    repo_root = _repo_root()
    _ensure_src_on_path(repo_root)

    from spectralbridge.pipelines import pipeline

    base_path = Path(base_folder).expanduser()
    if not base_path.is_absolute():
        base_path = (repo_root / base_path).resolve()

    stems = list(flight_lines) if flight_lines else [flight_id]
    staged = [
        stage_corrected_envi_flight(
            base_folder=base_path,
            flight_id=stem,
            product_code=product_code,
            allow_raw_envi_substitute=allow_raw_envi_substitute,
            dry_run=dry_run,
        )
        for stem in stems
    ]

    if dry_run:
        print(f"\n{LOG_PREFIX} Dry run only; nothing was staged or executed.")
        return staged

    poly = Path(polygon_path).expanduser() if polygon_path else None
    if poly is not None and not poly.exists():
        raise FileNotFoundError(f"Polygon file not found: {poly}")

    kwargs = {
        "base_folder": base_path,
        "site_code": "MULTI",
        "year_month": "0000-00",
        "product_code": product_code,
        "flight_lines": stems,
        "engine": engine,
        "max_workers": max_workers,
        "extraction_mode": extraction_mode,
        "topo_fit_mode": topo_fit_mode,
    }
    if extraction_mode == "polygon":
        if poly is None:
            raise ValueError("extraction_mode='polygon' requires --polygon-path")
        kwargs["polygon_path"] = poly
    else:
        kwargs["polygon_path"] = None

    # The corrected ENVI is the resume point, so no HDF5 is required.
    def stage_download_h5_patched(*, flight_stem: str, base_folder: Path, **_kwargs):
        h5_path = Path(base_folder) / f"{flight_stem}.h5"
        print(f"{LOG_PREFIX} Skipping download for {flight_stem}")
        return h5_path

    original = pipeline.stage_download_h5
    pipeline.stage_download_h5 = stage_download_h5_patched
    print(f"{LOG_PREFIX} Patched stage_download_h5()")

    try:
        print("\n" + "=" * 80)
        print(f"🚀 Resume-from-corrected pipeline: {', '.join(stems)}")
        print(f"   base_folder={base_path}")
        print(f"   extraction_mode={extraction_mode}")
        print(f"   topo_fit_mode={topo_fit_mode}")
        print("=" * 80 + "\n")
        return pipeline.go_forth_and_multiply(**kwargs)
    finally:
        pipeline.stage_download_h5 = original
        print(f"{LOG_PREFIX} Restored stage_download_h5()")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flight-id", default=FLIGHT_ID)
    parser.add_argument(
        "--flight-lines",
        nargs="+",
        default=None,
        help="Process several flight stems in one run (overrides --flight-id)",
    )
    parser.add_argument("--base-folder", type=Path, default=Path(BASE_FOLDER))
    parser.add_argument(
        "--extraction-mode",
        choices=("full", "polygon"),
        default=EXTRACTION_MODE,
    )
    parser.add_argument("--polygon-path", type=Path, default=None)
    parser.add_argument("--topo-fit-mode", choices=("scene", "tile"), default=TOPO_FIT_MODE)
    parser.add_argument("--product-code", default=PRODUCT_CODE)
    parser.add_argument("--engine", default=ENGINE)
    parser.add_argument("--max-workers", type=int, default=MAX_WORKERS)
    substitute = parser.add_mutually_exclusive_group()
    substitute.add_argument(
        "--allow-raw-substitute",
        dest="allow_raw_envi_substitute",
        action="store_true",
        default=ALLOW_RAW_ENVI_SUBSTITUTE,
        help="Stand in the corrected cube when raw ENVI is missing (default)",
    )
    substitute.add_argument(
        "--require-raw-envi",
        dest="allow_raw_envi_substitute",
        action="store_false",
        help="Fail instead of substituting when raw ENVI is missing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report readiness without staging files or running the pipeline",
    )
    args = parser.parse_args(argv)

    run(
        flight_id=args.flight_id,
        flight_lines=args.flight_lines,
        base_folder=args.base_folder,
        extraction_mode=args.extraction_mode,
        polygon_path=args.polygon_path,
        topo_fit_mode=args.topo_fit_mode,
        product_code=args.product_code,
        engine=args.engine,
        max_workers=args.max_workers,
        allow_raw_envi_substitute=args.allow_raw_envi_substitute,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
