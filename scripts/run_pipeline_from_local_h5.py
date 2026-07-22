#!/usr/bin/env python3
"""Run SpectralBridge from a local NEON H5 (no NEON download).

Expected layout after setup (pipeline contract)::

    <base_folder>/
      <flight_id>.h5
      <flight_id>/
        ... ENVI / corrected / parquet outputs created by the pipeline ...

Example (R10C L001)::

    python scripts/run_pipeline_from_local_h5.py \\
      --h5 /path/to/NEON_D10_R10C_DP1_L001-1_20210915_directional_reflectance.h5 \\
      --base-folder output_r10c \\
      --extraction-mode full

Or paste the CONFIG + RUN sections into a notebook after pointing ``sys.path``
at ``src/``.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


# =============================================================================
# CONFIG — edit these for notebook use, or override via CLI flags
# =============================================================================

FLIGHT_ID = "NEON_D10_R10C_DP1_L001-1_20210915_directional_reflectance"

# Where your local .h5 currently lives (file OR a directory containing it).
# Leave as None to search under --base-folder / repo.
H5_SOURCE: str | None = None

# Pipeline output root (created if missing).
BASE_FOLDER = "output_r10c"

# Full-scene parquet extraction by default. Use "polygon" + POLYGON_PATH for
# polygon mode.
EXTRACTION_MODE = "full"
POLYGON_PATH: str | None = None

TOPO_FIT_MODE = "scene"  # "scene" or "tile"
ENGINE = "thread"
MAX_WORKERS = 1
PRODUCT_CODE = "DP1.30006.001"


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


def _parse_site_and_month(flight_id: str) -> tuple[str, str]:
    """Best-effort site_code / year_month from a NEON directional reflectance id."""

    site_match = re.search(r"NEON_D\d+_([A-Z0-9]+)_DP1_", flight_id)
    site_code = site_match.group(1) if site_match else "UNKNOWN"
    date_match = re.search(r"_(\d{8})_", flight_id)
    if date_match:
        yyyymmdd = date_match.group(1)
        year_month = f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}"
    else:
        year_month = "0000-00"
    return site_code, year_month


def _resolve_h5_source(flight_id: str, base_folder: Path, h5_source: Path | None) -> Path:
    """Locate the user's local H5 file."""

    candidates: list[Path] = []
    if h5_source is not None:
        p = h5_source.expanduser().resolve()
        if p.is_file():
            return p
        if p.is_dir():
            candidates.extend(sorted(p.glob(f"{flight_id}*.h5")))
            candidates.extend(sorted(p.glob("*.h5")))
        else:
            raise FileNotFoundError(f"H5 source not found: {p}")

    # Common layouts on JupyterHub / local runs
    search_roots = [
        base_folder,
        base_folder.parent if base_folder.parent != base_folder else base_folder,
        Path.cwd(),
        _repo_root(),
        Path("/home/jovyan/data-store/spectralbridge"),
        Path("/home/jovyan/data-store"),
    ]
    for root in search_roots:
        if not root.exists():
            continue
        candidates.append(root / f"{flight_id}.h5")
        candidates.extend(sorted(root.glob(f"{flight_id}*.h5")))
        candidates.extend(sorted((root / flight_id).glob("*.h5")) if (root / flight_id).is_dir() else [])

    for cand in candidates:
        if cand.is_file() and cand.stat().st_size > 0:
            return cand.resolve()

    raise FileNotFoundError(
        f"Could not find local H5 for {flight_id}. "
        f"Pass --h5 /path/to/{flight_id}.h5"
    )


def stage_local_h5(
    *,
    flight_id: str,
    base_folder: Path,
    h5_source: Path | None,
) -> Path:
    """Create pipeline folders and place H5 at the canonical path.

    Canonical contract::

        <base_folder>/<flight_id>.h5
        <base_folder>/<flight_id>/   (work directory)

    Uses a symlink when possible; falls back to copy.
    """

    base_folder = Path(base_folder).expanduser().resolve()
    base_folder.mkdir(parents=True, exist_ok=True)
    flight_dir = base_folder / flight_id
    flight_dir.mkdir(parents=True, exist_ok=True)

    canonical = base_folder / f"{flight_id}.h5"
    if canonical.exists() and canonical.stat().st_size > 0:
        print(f"[local-h5] Reusing canonical H5: {canonical}")
        return canonical

    src = _resolve_h5_source(flight_id, base_folder, h5_source)
    print(f"[local-h5] Found source H5: {src}")

    if src.resolve() == canonical.resolve():
        return canonical

    try:
        if canonical.exists() or canonical.is_symlink():
            canonical.unlink()
        canonical.symlink_to(src)
        print(f"[local-h5] Symlinked → {canonical}")
    except OSError:
        print(f"[local-h5] Symlink failed; copying (this may take a while)…")
        shutil.copy2(src, canonical)
        print(f"[local-h5] Copied → {canonical}")

    if not canonical.exists() or canonical.stat().st_size <= 0:
        raise FileNotFoundError(f"Failed to stage H5 at {canonical}")
    return canonical


def run(
    *,
    flight_id: str = FLIGHT_ID,
    base_folder: Path | str = BASE_FOLDER,
    h5_source: Path | str | None = H5_SOURCE,
    extraction_mode: str = EXTRACTION_MODE,
    polygon_path: Path | str | None = POLYGON_PATH,
    topo_fit_mode: str = TOPO_FIT_MODE,
    product_code: str = PRODUCT_CODE,
    engine: str = ENGINE,
    max_workers: int = MAX_WORKERS,
) -> object:
    repo_root = _repo_root()
    _ensure_src_on_path(repo_root)

    from spectralbridge.pipelines import pipeline

    base_path = Path(base_folder).expanduser()
    if not base_path.is_absolute():
        base_path = (repo_root / base_path).resolve()

    src_h5 = Path(h5_source).expanduser() if h5_source else None
    staged = stage_local_h5(flight_id=flight_id, base_folder=base_path, h5_source=src_h5)
    site_code, year_month = _parse_site_and_month(flight_id)
    print(f"[local-h5] site_code={site_code} year_month={year_month}")
    print(f"[local-h5] staged H5={staged}")
    print(f"[local-h5] work dir={base_path / flight_id}")

    # Skip NEON download; assert the staged file is present.
    def stage_download_h5_patched(*, flight_stem: str, base_folder: Path, **_kwargs):
        paths_h5 = Path(base_folder) / f"{flight_stem}.h5"
        if not paths_h5.exists() or paths_h5.stat().st_size <= 0:
            raise FileNotFoundError(
                f"[local-h5] Expected local H5 missing: {paths_h5}\n"
                "Stage the file first or pass --h5."
            )
        print(f"[local-h5] Skipping download; using {paths_h5.name}")
        return paths_h5

    original = pipeline.stage_download_h5
    pipeline.stage_download_h5 = stage_download_h5_patched
    print("[local-h5] Patched stage_download_h5()")

    poly = Path(polygon_path).expanduser() if polygon_path else None
    if poly is not None and not poly.exists():
        raise FileNotFoundError(f"Polygon file not found: {poly}")

    kwargs = {
        "base_folder": base_path,
        "site_code": site_code,
        "year_month": year_month,
        "product_code": product_code,
        "flight_lines": [flight_id],
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

    try:
        print("\n" + "=" * 80)
        print(f"🚀 Local-H5 pipeline: {flight_id}")
        print(f"   base_folder={base_path}")
        print(f"   extraction_mode={extraction_mode}")
        print(f"   topo_fit_mode={topo_fit_mode}")
        print("=" * 80 + "\n")
        return pipeline.go_forth_and_multiply(**kwargs)
    finally:
        pipeline.stage_download_h5 = original
        print("[local-h5] Restored stage_download_h5()")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flight-id", default=FLIGHT_ID)
    parser.add_argument(
        "--h5",
        type=Path,
        default=None,
        help="Path to the local .h5 (or a directory containing it)",
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
    args = parser.parse_args(argv)

    run(
        flight_id=args.flight_id,
        base_folder=args.base_folder,
        h5_source=args.h5,
        extraction_mode=args.extraction_mode,
        polygon_path=args.polygon_path,
        topo_fit_mode=args.topo_fit_mode,
        product_code=args.product_code,
        engine=args.engine,
        max_workers=args.max_workers,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
