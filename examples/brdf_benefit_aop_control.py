"""Bounded real-angle AOP BRDF-only spatial holdout diagnostic.

No PFT labels or truth reflectance. Held-out20m groups never fit BRDF. Residual
angular association is descriptive and land-cover confounded; lower is not accuracy.
"""

import hashlib
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from spectralbridge.neon_cube import NeonCube
from spectralbridge import corrections

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "provenance/brdf-benefit-audit/2026-11-19/aop-control"
SOURCE = (
    ROOT
    / "archive/local/validation-input/NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5"
)
WAVES = [444, 475, 531, 560, 650, 668, 705, 717, 740, 862]


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def association(design, values, groups):
    """Within-block adjusted-free linear angular R2 (diagnostic, not calibration)."""
    x = np.asarray(design, float).copy()
    y = np.asarray(values, float).copy()
    for g in np.unique(groups):
        ix = groups == g
        x[ix] -= x[ix].mean(axis=0)
        y[ix] -= y[ix].mean()
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    sst = y @ y
    return float(1 - np.sum((y - x @ beta) ** 2) / sst) if sst > 0 else float("nan")


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    identity = {
        "code": sha(Path(__file__)),
        "corrections": sha(ROOT / "src/spectralbridge/corrections.py"),
        "source": sha(SOURCE),
    }
    done = OUT / "completed.json"
    if done.exists():
        old = json.loads(done.read_text())
        if old["identity"] == identity and all(
            sha(OUT / p) == h for p, h in old["outputs"].items()
        ):
            print("Verified AOP control reuse", flush=True)
            return
    start = time.monotonic()
    print("AOP BRDF-only: loading bounded120x3000 native window", flush=True)
    c = NeonCube(SOURCE, line_slice=(350, 470), sample_slice=(1000, 4000))
    selected = np.array([np.argmin(abs(c.wavelengths - w)) for w in WAVES])
    c.data = c.data[..., selected].copy()
    c.wavelengths = c.wavelengths[selected]
    c.bands = len(selected)
    if c.fwhm is not None:
        c.fwhm = c.fwhm[selected]
    c.radiometry.require_valid()
    yy, xx = np.indices(c.data.shape[:2])
    groups = (yy // 20) * ((c.columns + 19) // 20) + xx // 20
    unique = np.unique(groups)
    rng = np.random.default_rng(20261119)
    held = np.sort(
        rng.choice(unique, size=int(np.ceil(0.2 * len(unique))), replace=False)
    )
    train = ~np.isin(groups, held)
    config = corrections.HYTOOLS_BRDF_KERNEL_CONFIG
    fitstart = time.monotonic()
    with threadpool_limits(limits=1):
        path = corrections.fit_and_save_brdf_model(
            c,
            OUT / "model",
            brdf_kernel_config=config,
            apply_topography=False,
            fitting_mask=train,
            uncertainty_groups=groups,
            fitting_provenance={
                "study": "BRDF benefit audit",
                "held_groups": held.tolist(),
                "grouping": "20m nonoverlap grid; fixed random20percent holdout",
            },
        )
    model = json.loads(path.read_text())
    fitseconds = time.monotonic() - fitstart
    record = dict(
        identity=identity,
        status=model["validation"]["status"],
        fit_seconds=fitseconds,
        train_groups=int(sum(~np.isin(unique, held))),
        held_groups=len(held),
        model_path=str(path.relative_to(ROOT)),
        model_sha256=sha(path),
        supported_bands=sum(
            f["status"] == "VALID" for f in model["validation"]["fits"]
        ),
    )
    if model["validation"]["status"] != "VALID":
        record["limitation"] = "No correction applied: current normal QA guard failed"
        record["elapsed_seconds"] = time.monotonic() - start
        record["outputs"] = {}
        done.write_text(json.dumps(record, indent=2) + "\n")
        print(record, flush=True)
        return
    appstart = time.monotonic()
    with threadpool_limits(limits=1):
        after = corrections.apply_brdf_correct(
            c,
            c.data,
            0,
            c.lines,
            0,
            c.columns,
            coeff_path=path,
            brdf_kernel_config=config,
            input_stage="uncorrected",
        )
    before = c.radiometry.to_physical(c.data)
    after = c.radiometry.to_physical(after)
    design, valid, solar = corrections._brdf_design(
        c, config, scene_solar=model["scene_solar_zenith_rad"]
    )
    output = []
    blockrows = []
    for band, wave in enumerate(c.wavelengths):
        keep = (
            (~train)
            & valid
            & np.isfinite(before[..., band])
            & np.isfinite(after[..., band])
        )
        a = before[..., band][keep]
        b = after[..., band][keep]
        g = groups[keep]
        x = design[keep, 1:]
        for group in np.unique(g):
            ix = g == group
            blockrows.append(
                dict(
                    band=band + 1,
                    wavelength_nm=float(wave),
                    group=int(group),
                    pixels=int(ix.sum()),
                    sd_no_brdf=float(np.std(a[ix], ddof=1)),
                    sd_brdf=float(np.std(b[ix], ddof=1)),
                    mean_no_brdf=float(a[ix].mean()),
                    mean_brdf=float(b[ix].mean()),
                )
            )
        output.append(
            dict(
                band=band + 1,
                wavelength_nm=float(wave),
                held_pixels=len(a),
                angular_r2_no_brdf=association(x, a, g),
                angular_r2_brdf=association(x, b, g),
                median_abs_reflectance_change=float(np.median(abs(b - a))),
                p95_abs_reflectance_change=float(np.quantile(abs(b - a), 0.95)),
            )
        )
    pd.DataFrame(output).to_csv(OUT / "heldout_band_diagnostics.csv", index=False)
    pd.DataFrame(blockrows).to_csv(OUT / "heldout_block_diagnostics.csv", index=False)
    record.update(
        application_seconds=time.monotonic() - appstart,
        elapsed_seconds=time.monotonic() - start,
        outputs={p.name: sha(p) for p in OUT.glob("*.csv")},
        limitation="One real R10C scene,120x3000 bounded window, no PFT or absolute truth. Same20mblock residual angular R2 diagnostic; spatial landcover-angle confounding remains. No masks/refits selected by endpoint.",
    )
    done.write_text(json.dumps(record, indent=2) + "\n")
    print("AOP holdout control complete", record["status"], flush=True)


if __name__ == "__main__":
    run()
