#!/usr/bin/env python3
"""Stage-by-stage diagnosis for BRDF + topo producing -9999.

Run on JupyterHub against a flightline that has:
  - raw ENVI (+ HDR)
  - source H5
  - BRDF model JSON (canonical ``*_brdf_model.json`` name)

Example:
  python scripts/diagnose_brdf_topo_stage.py \\
    --flight-dir output_later/NEON_D13_NIWO_DP1_L003-1_20230724_directional_reflectance
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _summarize(name: str, arr: np.ndarray) -> None:
    finite = arr[np.isfinite(arr)]
    nodata = np.isclose(arr, -9999.0, atol=0.01) if np.issubdtype(arr.dtype, np.floating) else None
    print(f"  {name}:")
    print(f"    shape={arr.shape} dtype={arr.dtype}")
    if finite.size:
        print(
            f"    finite min={finite.min():.6g} max={finite.max():.6g} "
            f"mean={finite.mean():.6g} frac_finite={finite.size / arr.size:.3f}"
        )
    else:
        print("    finite: NONE")
    if nodata is not None:
        print(f"    frac_approx_-9999={float(nodata.mean()):.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flight-dir", type=Path, required=True)
    parser.add_argument("--row", type=int, default=None, help="Test pixel row")
    parser.add_argument("--col", type=int, default=None, help="Test pixel col")
    parser.add_argument("--chunk-y", type=int, default=100)
    parser.add_argument("--chunk-x", type=int, default=100)
    args = parser.parse_args()

    flight_dir = args.flight_dir.resolve()
    fid = flight_dir.name
    raw_img = flight_dir / f"{fid}_envi.img"
    corr_json = flight_dir / f"{fid}_brdfandtopo_corrected_envi.json"
    brdf_model = flight_dir / f"{fid}_brdf_model.json"

    # Prefer parent H5 naming used by pipeline
    h5_candidates = [
        flight_dir.parent / f"{fid}.h5",
        *flight_dir.glob("*.h5"),
        *flight_dir.parent.glob(f"{fid}*.h5"),
    ]
    h5_path = next((p for p in h5_candidates if p.exists()), None)
    if h5_path is None:
        raise FileNotFoundError(f"No H5 found for {fid}")
    if not corr_json.exists():
        raise FileNotFoundError(corr_json)
    if not brdf_model.exists():
        legacy = flight_dir / f"{fid}_brdfandtopo_corrected_brdf_model.json"
        if legacy.exists():
            raise FileNotFoundError(
                f"Canonical BRDF model missing. Copy:\n  {legacy.name}\n→ {brdf_model.name}"
            )
        raise FileNotFoundError(brdf_model)

    from spectralbridge.corrections import (
        HYTOOLS_BRDF_KERNEL_CONFIG,
        NDVIBinningConfig,
        apply_brdf_correct,
        apply_topo_correct,
        calc_cosine_i,
    )
    from spectralbridge.neon_cube import NeonCube

    params = json.loads(corr_json.read_text())
    params["h5_path"] = str(h5_path.resolve())
    params["coefficients_path"] = str(brdf_model.resolve())

    print("=" * 72)
    print(f"Flight: {fid}")
    print(f"H5: {h5_path}")
    print(f"BRDF model: {brdf_model}")
    print("=" * 72)

    cube = NeonCube(h5_path=h5_path)
    print("\n[1] Cube metadata")
    print(f"  lines={cube.lines} cols={cube.columns} bands={cube.bands}")
    print(f"  scale_factor={cube.scale_factor!r}")
    print(f"  no_data={cube.no_data!r}")
    print(f"  mask_valid_frac={float(cube.mask_no_data.mean()):.3f}")
    if abs(float(cube.scale_factor)) >= 1.0 and abs(float(cube.scale_factor) - 1.0) > 1e-6:
        print(
            "  ⚠️  scale_factor >= 1 looks unusual for integer×scale NEON reflectance "
            "(tests expect ~1e-4). Confirm H5 Scale_Factor semantics."
        )

    print("\n[2] BRDF coefficient JSON / naming")
    from spectralbridge.paths import scene_prefix_from_dir

    prefix = scene_prefix_from_dir(flight_dir)
    print(f"  scene_prefix_from_dir → {prefix!r}")
    expected_model = flight_dir / f"{prefix}_brdf_model.json"
    if expected_model.resolve() != brdf_model.resolve():
        print(f"  ⚠️  Using {brdf_model.name}; expected {expected_model.name}")
    model = json.loads(brdf_model.read_text())
    for key in ("iso", "vol", "geo"):
        arr = np.asarray(model.get(key), dtype=np.float64)
        print(f"  {key}: shape={arr.shape} min={arr.min():.4g} max={arr.max():.4g}")
    print(f"  ndvi_edges={model.get('ndvi_edges')}")
    print(f"  volume_kernel={model.get('volume_kernel')} geom_kernel={model.get('geom_kernel')}")

    print("\n[3] Ancillary raw vs radians")
    for name in ("solar_zn", "solar_az", "sensor_zn", "sensor_az", "slope", "aspect"):
        deg = cube.get_ancillary(name, radians=False)
        rad = cube.get_ancillary(name, radians=True)
        print(
            f"  {name}: deg[min={np.nanmin(deg):.3f}, max={np.nanmax(deg):.3f}]  "
            f"rad[min={np.nanmin(rad):.3f}, max={np.nanmax(rad):.3f}]"
        )
        # Heuristic: values already in radians wrongly passed through np.radians
        if np.nanmax(np.abs(deg)) < 3.5:
            print(
                f"    ⚠️  '{name}' raw max < 3.5 — may already be radians; "
                "double conversion would shrink angles."
            )

    row = args.row if args.row is not None else cube.lines // 2
    col = args.col if args.col is not None else cube.columns // 2
    cy, cx = args.chunk_y, args.chunk_x
    ys = (row // cy) * cy
    xs = (col // cx) * cx
    ye = min(ys + cy, cube.lines)
    xe = min(xs + cx, cube.columns)
    ri, ci = row - ys, col - xs

    print(f"\n[4] Test pixel row={row} col={col} in chunk [{ys}:{ye},{xs}:{xe}]")
    chunk = np.asarray(cube.data[ys:ye, xs:xe, :], dtype=np.float32)
    print(f"  raw band0/50/100 at pixel: {chunk[ri, ci, [0, 50, 100]].tolist()}")
    print(f"  mask_no_data at pixel: {bool(cube.mask_no_data[row, col])}")

    slope = cube.get_ancillary("slope", radians=True)[ys:ye, xs:xe]
    aspect = cube.get_ancillary("aspect", radians=True)[ys:ye, xs:xe]
    solar_zn = cube.get_ancillary("solar_zn", radians=True)[ys:ye, xs:xe]
    solar_az = cube.get_ancillary("solar_az", radians=True)[ys:ye, xs:xe]
    cos_i = calc_cosine_i(solar_zn, solar_az, aspect, slope)
    print(
        f"  cos_i at pixel={float(cos_i[ri, ci]):.4f}  "
        f"solar_zn_rad={float(solar_zn[ri, ci]):.4f} slope_rad={float(slope[ri, ci]):.4f}"
    )
    _summarize("cos_i (chunk)", cos_i)

    print("\n[5] TOPO only (SCS+C)")
    after_topo = apply_topo_correct(cube, chunk, ys, ye, xs, xe, use_scs_c=True)
    print(f"  after_topo bands 0/50/100: {after_topo[ri, ci, [0, 50, 100]].tolist()}")
    _summarize("after_topo band0", after_topo[..., 0])
    neg = (after_topo[ri, ci] < 0) & np.isfinite(after_topo[ri, ci])
    print(f"  test pixel negative finite bands: {int(neg.sum())}/{after_topo.shape[-1]}")

    print("\n[6] TOPO only (legacy cosine-ratio, use_scs_c=False)")
    after_topo_legacy = apply_topo_correct(cube, chunk, ys, ye, xs, xe, use_scs_c=False)
    print(
        f"  after_topo_legacy bands 0/50/100: {after_topo_legacy[ri, ci, [0, 50, 100]].tolist()}"
    )

    print("\n[7] BRDF only on RAW (skip topo)")
    after_brdf_raw = apply_brdf_correct(
        cube,
        chunk,
        ys,
        ye,
        xs,
        xe,
        coeff_path=brdf_model,
        ndvi_config=NDVIBinningConfig(enabled=False),
        brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    print(f"  after_brdf_raw bands 0/50/100: {after_brdf_raw[ri, ci, [0, 50, 100]].tolist()}")
    _summarize("after_brdf_raw band0", after_brdf_raw[..., 0])

    print("\n[8] TOPO then BRDF (pipeline order)")
    after_both = apply_brdf_correct(
        cube,
        after_topo.astype(np.float32, copy=False),
        ys,
        ye,
        xs,
        xe,
        coeff_path=brdf_model,
        ndvi_config=NDVIBinningConfig(enabled=False),
        brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    print(f"  after_both bands 0/50/100: {after_both[ri, ci, [0, 50, 100]].tolist()}")
    _summarize("after_both band0", after_both[..., 0])

    print("\n[9] Verdict")
    raw_v = float(chunk[ri, ci, 0])
    topo_v = float(after_topo[ri, ci, 0])
    brdf_only_v = float(after_brdf_raw[ri, ci, 0])
    both_v = float(after_both[ri, ci, 0])

    def _dead(v: float) -> bool:
        return (not np.isfinite(v)) or abs(v + 9999.0) < 0.1

    if _dead(topo_v) and not _dead(raw_v):
        print("  → FAIL at TOPO (raw valid, topo = nodata/invalid)")
    elif topo_v < 0 and not _dead(raw_v):
        print("  → FAIL at TOPO (produces negative reflectance; BRDF will promote to -9999)")
    elif _dead(brdf_only_v) and not _dead(raw_v):
        print("  → FAIL at BRDF alone (even without topo)")
    elif _dead(both_v) and not _dead(topo_v) and topo_v >= 0:
        print("  → FAIL at BRDF after otherwise-OK topo")
    elif not _dead(both_v):
        print("  → PASS for this test pixel (re-check more pixels if full ENVI is still -9999)")
    else:
        print("  → Inconclusive; inspect summaries above")

    print(
        f"\n  raw={raw_v:.3f} topo={topo_v:.3f} brdf_only={brdf_only_v:.3f} both={both_v:.3f}"
    )
    if abs(float(cube.scale_factor)) > 1.5:
        print(
            "\n  Also investigate scale_factor: "
            f"{cube.scale_factor}. Expected ~1e-4 for DN×scale NEON products."
        )


if __name__ == "__main__":
    main()
