"""Reproduce bounded Goldhill rejection and synthetic cross-entry evidence.

Reads immutable prior products; writes only a new evidence directory. The
synthetic experiment demonstrates contracts, not ecological effectiveness.
"""

from pathlib import Path
import argparse
import hashlib
import json
import runpy
import tempfile

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from spectralbridge.corrections import (
    HYTOOLS_BRDF_KERNEL_CONFIG,
    _brdf_design,
    apply_brdf_correct,
    apply_topo_correct,
    fit_and_save_brdf_model,
)
from spectralbridge.neon_cube import NeonCube
from spectralbridge.pipelines.drone import (
    apply_drone_corrections,
    DroneCorrectionUnavailableError,
)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--goldhill-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    historical = sorted(args.goldhill_dir.glob("*__corrected.*")) + sorted(
        args.goldhill_dir.glob("*brdf_model.json")
    )
    before = {str(p): digest(p) for p in historical}
    h5 = next(args.goldhill_dir.glob("*__working.h5"))
    cube = NeonCube(h5)
    p = fit_and_save_brdf_model(
        cube,
        args.output / "goldhill_rejection",
        brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
    )
    new_model = json.loads(p.read_text())
    try:
        apply_drone_corrections(
            cube=cube,
            envi_img=next(args.goldhill_dir.glob("*__envi.img")),
            envi_hdr=next(args.goldhill_dir.glob("*__envi.hdr")),
            corrected_stem=args.output / "blocked_goldhill",
            apply_topo=True,
            apply_brdf=True,
        )
    except DroneCorrectionUnavailableError as exc:
        rejection = str(exc)
    else:
        raise AssertionError("Unverified real Goldhill unexpectedly passed")
    # Geometry-only computation does not assign physical units to Goldhill.
    X, mask, solar = _brdf_design(
        cube,
        HYTOOLS_BRDF_KERNEL_CONFIG,
        window=(0, min(64, cube.lines), 0, min(64, cube.columns)),
    )
    X = X[mask].astype("float64")
    singular = np.linalg.svd(X, compute_uv=False)
    actual = {
        "source": str(h5),
        "radiometry": cube.radiometry.record(),
        "rejection": rejection,
        "new_model_status": new_model["validation"]["status"],
        "sample_geometry_rank": int(np.linalg.matrix_rank(X)),
        "sample_geometry_singular_values": singular.tolist(),
        "scope": "64x64 geometry-only window; no inferred reflectance calibration",
        "historical_hashes_before": before,
        "historical_hashes_after": {str(p): digest(p) for p in historical},
    }
    assert actual["historical_hashes_before"] == actual["historical_hashes_after"]
    del cube
    scene = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "tests/test_aop_drone_equivalence.py")
    )["scene"]
    with tempfile.TemporaryDirectory(prefix="spectralbridge-affine-evidence-") as temp:
        root = Path(temp)
        ah, _, _, _ = scene(root, "NEON_D13_NIWO_DP1_evidence", 0.0001, 0.0)
        dh, _, _, _ = scene(root, "drone", 0.001, -0.05)
        a, d = NeonCube(ah), NeonCube(dh)
        ap = a.radiometry.to_physical(a.data)
        dp = d.radiometry.to_physical(d.data)
        p = fit_and_save_brdf_model(
            d, root / "synthetic_model", brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG
        )
        model = json.loads(p.read_text())
        assert model["validation"]["status"] == "VALID"
        raw = d.data.copy()
        topo = apply_topo_correct(d, raw, 0, d.lines, 0, d.columns)
        brdf = apply_brdf_correct(d, raw, 0, d.lines, 0, d.columns, coeff_path=p)
        combined_model = fit_and_save_brdf_model(
            d,
            root / "synthetic_combined",
            brdf_kernel_config=HYTOOLS_BRDF_KERNEL_CONFIG,
            apply_topography=True,
        )
        combined = apply_brdf_correct(
            d,
            topo,
            0,
            d.lines,
            0,
            d.columns,
            coeff_path=combined_model,
            input_stage="topographic_only",
        )
        conditions = {
            k: d.radiometry.to_physical(v).mean(axis=(0, 1)).tolist()
            for k, v in [
                ("Uncorrected", raw),
                ("Topographic only", topo),
                ("BRDF only", brdf),
                ("Combined", combined),
            ]
        }
        SX, sm, _ = _brdf_design(d, HYTOOLS_BRDF_KERNEL_CONFIG)
        synthetic = {
            "description": "Synthetic calibrated scene, identical angular support, flat terrain; not an independent ecological evaluation",
            "maximum_physical_difference": float(np.max(np.abs(ap - dp))),
            "conditions_mean_spectra": conditions,
            "model": model,
            "geometry_singular_values": np.linalg.svd(
                SX[sm].astype("float64"), compute_uv=False
            ).tolist(),
        }
        fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout="constrained")
        ax = axes[0, 0]
        ax.scatter(ap.reshape(-1), dp.reshape(-1), s=8, alpha=0.5)
        ax.plot([0.25, 0.55], [0.25, 0.55], c="black", lw=1)
        ax.set(
            title="Verified physical inputs agree (synthetic)",
            xlabel="NEON physical reflectance",
            ylabel="Drone physical reflectance",
        )
        ax.text(
            0.04,
            0.92,
            f"Maximum difference: {synthetic['maximum_physical_difference']:.2g}",
            transform=ax.transAxes,
        )
        ax = axes[0, 1]
        waves = [444, 475, 531, 560, 650, 668, 705, 717, 740, 862]
        counts = [3, 1, 9, 13, 14, 30, 8, 4, 1, 0]
        ax.bar(range(10), counts, color="#ae4039")
        ax.set(
            xticks=range(10),
            xticklabels=waves,
            title="Goldhill historical eligible pixels",
            xlabel="Band wavelength (nm)",
            ylabel="Pixels in the old 0..2 gate",
        )
        ax.tick_params(axis="x", rotation=60)
        ax.text(
            0.02,
            0.93,
            "7,068,376 finite pixels per band\nUnits unverified: this was not a valid fit",
            transform=ax.transAxes,
            va="top",
            fontsize=9,
        )
        ax = axes[0, 2]
        ax.semilogy(
            [1, 2, 3],
            np.maximum(singular, 1e-16),
            "o-",
            label=f"Goldhill geometry: rank {actual['sample_geometry_rank']}",
        )
        ax.semilogy(
            [1, 2, 3],
            synthetic["geometry_singular_values"],
            "o-",
            label="Synthetic supported geometry: rank 3",
        )
        ax.set(
            title="Angular design support (new kernels)",
            xlabel="Singular value index",
            ylabel="Singular value",
        )
        ax.legend(fontsize=8)
        ax = axes[1, 0]
        q = np.array(model["validation"]["fits"][0]["factor_quantiles"])
        ax.plot([0, 1, 50, 99, 100], q, "o-")
        ax.set(
            title="Supported correction factors (synthetic)",
            xlabel="Percentile",
            ylabel="BRDF normalization factor",
        )
        ax.text(
            0.03,
            0.92,
            "Goldhill: no validated factors produced",
            transform=ax.transAxes,
            fontsize=9,
        )
        ax = axes[1, 1]
        for name, spec in conditions.items():
            ax.plot([650, 860], spec, "o-", label=name, alpha=0.7)
        ax.set(
            title="Four valid synthetic processing conditions",
            xlabel="Wavelength (nm)",
            ylabel="Mean physical reflectance",
        )
        ax.legend(fontsize=8)
        ax.text(
            0.03,
            0.98,
            "Flat terrain: topo overlaps uncorrected",
            transform=ax.transAxes,
            va="top",
            fontsize=8,
        )
        ax = axes[1, 2]
        ax.axis("off")
        ax.text(
            0,
            0.92,
            "Real cross-sensor ecological validation\n\nNOT EVALUATED\n\nGoldhill scale/offset are unverified.\nMosaic angles are insufficient.\nNo matched held-out, calibrated PFT observations\nwere established in this investigation.\n\nSynthetic equivalence does not establish\nPFT accuracy or cross-year transferability.",
            va="top",
            fontsize=11,
        )
        fig.suptitle(
            "Shared radiometry and BRDF evidence | 30 October 2026", fontsize=16
        )
        fig.savefig(args.output / "scientific_evidence.png", dpi=170)
    (args.output / "validation.json").write_text(
        json.dumps(
            {"goldhill": actual, "synthetic": synthetic}, indent=2, allow_nan=False
        )
    )


if __name__ == "__main__":
    main()
