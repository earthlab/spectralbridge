"""Same-grid HLS BRDF ablation from official RTLS factors and actual angle assets.

Reconstructs pre-NBAR HLS reflectance, NOT native Collection2 observations. Uses
unmodified pinned NASA RTLS kernels, metadata target solar zenith and pixel SAA,
SZA,VAA,VZA. Original1e-4 quantization cannot be undone. No production data edited.
"""

import ctypes
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples/publication_figures"))
from landsat_regional_candidates import open_asset  # noqa:E402

sys.path.pop(0)
REPORT = ROOT / "provenance/brdf-benefit-audit/2026-11-19"
REFERENCE = REPORT / "source-reference"
COHORT = (
    ROOT
    / "provenance/landsat-pure-pixels/2026-11-18/expanded-search/round-2/power-directed-expansion/review-batch-2/hls-combined"
)
BANDS = [f"B{i}" for i in range(1, 8)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def factor_library():
    manifest = json.loads((REFERENCE / "source_manifest.json").read_text())
    for name, record in manifest["files"].items():
        if sha(REFERENCE / name) != record["sha256"]:
            raise ValueError("Changed pinned HLS reference")
    code = """/* Research wrapper of NASA-IMPACT HLS RTLS; source commit in manifest. */
#include "rtls.h"
#include "modis_brdf_coeff.h"
void hls_factors(int n, const double *sz, const double *vz, const double *ra,
                 double target, double *out) {
 int mapping[7]={0,0,1,2,6,7,8};
 double r=RossThick(target,0,0), l=LiSparseR(target,0,0);
 for(int i=0;i<n;i++){
  double kr=RossThick(sz[i],vz[i],ra[i]), kl=LiSparseR(sz[i],vz[i],ra[i]);
  for(int b=0;b<7;b++){
   int k=mapping[b];
   out[i*7+b]=(coeff[k][0]+coeff[k][1]*r+coeff[k][2]*l)/
              (coeff[k][0]+coeff[k][1]*kr+coeff[k][2]*kl);
  }
 }
}
"""
    signature = hashlib.sha256(
        (code + json.dumps(manifest, sort_keys=True)).encode()
    ).hexdigest()[:20]
    temp = Path("/tmp") / f"spectralbridge-hls-brdf-{signature}"
    temp.mkdir(exist_ok=True)
    wrapper = temp / "wrapper.c"
    wrapper.write_text(code)
    library = temp / "official_hls_rtls.so"
    if not library.exists():
        flags = ["-dynamiclib"] if platform.system() == "Darwin" else ["-shared"]
        subprocess.run(
            [
                "cc",
                "-O2",
                "-fPIC",
                *flags,
                "-I",
                str(REFERENCE),
                str(REFERENCE / "rtls.c"),
                str(wrapper),
                "-lm",
                "-o",
                str(library),
            ],
            check=True,
            capture_output=True,
        )
    dll = ctypes.CDLL(str(library))
    array = np.ctypeslib.ndpointer(dtype=np.float64, flags="C_CONTIGUOUS")
    dll.hls_factors.argtypes = [
        ctypes.c_int,
        array,
        array,
        array,
        ctypes.c_double,
        array,
    ]
    dll.hls_factors.restype = None
    return dll


def factors(sz, vz, relative_azimuth, target):
    sz = np.ascontiguousarray(sz, dtype=np.float64)
    vz = np.ascontiguousarray(vz, dtype=np.float64)
    ra = np.ascontiguousarray(relative_azimuth, dtype=np.float64)
    if sz.ndim != 1 or sz.shape != vz.shape or sz.shape != ra.shape:
        raise ValueError("Aligned one-dimensional degree angles required")
    if not (
        np.isfinite(sz).all()
        and np.isfinite(vz).all()
        and np.isfinite(ra).all()
        and np.isfinite(target)
    ):
        raise ValueError("Finite angles required")
    if np.any((sz < 0) | (sz >= 90) | (vz < 0) | (vz >= 90)) or not 0 <= target < 90:
        raise ValueError("Zenith angles outside physical domain")
    out = np.empty((len(sz), 7), np.float64)
    factor_library().hls_factors(len(sz), sz, vz, ra, float(target), out)
    if not np.isfinite(out).all() or not (out > 0).all():
        raise ValueError("Unsupported HLS factor")
    return out


def run():
    started = time.monotonic()
    dest = REPORT / "hls"
    dest.mkdir(parents=True, exist_ok=True)
    source = COHORT / "hls_l30_nominal_95pct_observations.csv"
    frame = pd.read_csv(source)
    signature = dict(
        source_sha256=sha(source),
        reference_sha256=sha(REFERENCE / "source_manifest.json"),
        code_sha256=sha(Path(__file__)),
    )
    checkpoint = dest / "completed.json"
    if checkpoint.exists():
        old = json.loads(checkpoint.read_text())
        if old["identity"] == signature and all(
            sha(dest / name) == digest for name, digest in old["outputs"].items()
        ):
            print("HLS counterfactual reused", flush=True)
            return
    all_cells = []
    metadata = []
    for item_id, group in frame.groupby("hls_item_id", sort=True):
        t0 = time.monotonic()
        cache = dest / (item_id + "-reconstructed.csv")
        metapath = dest / (item_id + "-metadata.json")
        if (
            cache.exists()
            and metapath.exists()
            and json.loads(metapath.read_text()).get("identity") == signature
        ):
            record = json.loads(metapath.read_text())
            if sha(cache) != record["csv_sha256"]:
                raise ValueError("Changed HLS stage cache")
            all_cells.append(pd.read_csv(cache))
            metadata.append(record)
            print(item_id, "verified reuse", flush=True)
            continue
        print(
            item_id,
            "reading public normalization metadata and angle windows",
            flush=True,
        )
        first = group.iloc[0]
        catalogue = json.loads(
            (COHORT / f"{first.region}-{int(first.year)}-catalogue.json").read_text()
        )
        item = next(f for f in catalogue["features"] if f["id"] == item_id)
        coords = list(zip(group.easting, group.northing, strict=True))
        angles = {}
        with open_asset(item, "B01") as raster:
            tags = raster.tags()
            transform = tuple(raster.transform)
            crs = raster.crs
            measured = np.array([v[0] for v in raster.sample(coords)]) * float(
                tags["scale_factor"]
            ) + float(tags.get("add_offset", 0))
            np.testing.assert_allclose(measured, group.B1, rtol=0, atol=1e-12)
        target = float(tags["NBAR_SOLAR_ZENITH"])
        angle_tags = {}
        for key in ["SZA", "SAA", "VZA", "VAA"]:
            with open_asset(item, key) as raster:
                if tuple(raster.transform) != transform or raster.crs != crs:
                    raise ValueError("HLS angle and reflectance grid differ")
                t = raster.tags()
                scale = float(t.get("scale_factor", 0.01))
                offset = float(t.get("add_offset", 0))
                if scale != 0.01 or offset != 0:
                    raise ValueError(
                        "Angle storage convention differs from official centidegrees"
                    )
                angles[key] = (
                    np.array([v[0] for v in raster.sample(coords)], dtype=float) * scale
                )
                angle_tags[key] = t
        cf = factors(
            angles["SZA"], angles["VZA"], angles["SAA"] - angles["VAA"], target
        )
        out = group.copy()
        for i, band in enumerate(BANDS):
            out[f"cf_{band}"] = cf[:, i]
            out[f"pre_nbar_{band}"] = out[band] / cf[:, i]
            out[f"rounding_bound_{band}"] = 0.00005 / cf[:, i]
            np.testing.assert_allclose(
                out[f"pre_nbar_{band}"] * cf[:, i], out[band], rtol=1e-14, atol=1e-14
            )
        for key, value in angles.items():
            out[key + "_degrees"] = value
        out["target_sza_degrees"] = target
        out.to_csv(cache, index=False)
        record = dict(
            identity=signature,
            hls_item_id=item_id,
            normalization_target_degrees=target,
            metadata=tags,
            angle_metadata=angle_tags,
            csv_sha256=sha(cache),
            cells=len(out),
            elapsed_seconds=time.monotonic() - t0,
            scope="Exact pinned algorithm recomputation from distributed angles/target metadata; pre-NBAR approximation due to original quantization, not original C2 pixels",
        )
        metapath.write_text(json.dumps(record, indent=2) + "\n")
        all_cells.append(out)
        metadata.append(record)
        print(item_id, "factor/reconstruction and B1 source checks pass", flush=True)
    cells = pd.concat(all_cells, ignore_index=True)
    cells.to_csv(dest / "paired_cells.csv", index=False)
    spectra = []
    for patch, g in cells.groupby("patch_group_id"):
        common = np.isfinite(g[BANDS]).all(axis=1) & np.isfinite(
            g[["pre_nbar_" + b for b in BANDS]]
        ).all(axis=1)
        for arm, prefix in [("no_brdf", "pre_nbar_"), ("brdf", "")]:
            med = g.loc[common, [prefix + b for b in BANDS]].median().to_numpy()
            spectra.append(
                dict(
                    identity=patch,
                    site=g.region.iloc[0],
                    category=g.researcher_category.iloc[0],
                    arm=arm,
                    n_pixels=int(common.sum()),
                    **dict(zip(BANDS, med, strict=True)),
                )
            )
    pd.DataFrame(spectra).to_csv(dest / "polygon_spectra.csv", index=False)
    summary = []
    for b in BANDS:
        x = cells["cf_" + b].to_numpy()
        summary.append(
            dict(
                band=b,
                n=len(x),
                factor_min=x.min(),
                factor_median=np.median(x),
                factor_max=x.max(),
                median_abs_percent_adjustment=float(np.median(abs(x - 1)) * 100),
                p95_abs_percent_adjustment=float(np.quantile(abs(x - 1), 0.95) * 100),
                max_directional_rounding_bound=float(
                    cells["rounding_bound_" + b].max()
                ),
            )
        )
    pd.DataFrame(summary).to_csv(dest / "correction_magnitudes.csv", index=False)
    outputs = {p.name: sha(p) for p in dest.glob("*.csv")}
    checkpoint.write_text(
        json.dumps(
            dict(
                identity=signature,
                outputs=outputs,
                cells=len(cells),
                patches=cells.patch_group_id.nunique(),
                granules=len(metadata),
                elapsed_seconds=time.monotonic() - started,
                metadata_files=[x["hls_item_id"] + "-metadata.json" for x in metadata],
            ),
            indent=2,
        )
        + "\n"
    )
    print(
        "HLS controlled counterfactual complete",
        len(cells),
        "cells;",
        len(spectra) // 2,
        "patches",
        flush=True,
    )


if __name__ == "__main__":
    run()
