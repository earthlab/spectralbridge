"""Use shared fits/guards unchanged; isolated calibration and kernel-input adapters."""

import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"
sys.path.insert(0, str(PRIOR))
from common import Cube, isolated, safe, dist, SOURCE, sha  # noqa:E402
from spectralbridge import corrections as c  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")


def write(name, value):
    (HERE / name).write_text(json.dumps(safe(value), indent=2, allow_nan=False) + "\n")


def blend_adapter(function, design, design_hash):
    """Supply simulated weighted kernel inputs; keep estimator and gates identical.

    No angles are averaged into a fictitious sensor ray. One design row corresponds
    to one orthomosaic reflectance. Source identity also fingerprints the complete
    simulated design. Production functions and globals are never modified.
    """
    func = isolated(function)
    original_identity = c._brdf_source_identity

    def identity(cube):
        return hashlib.sha256(
            (original_identity(cube) + design_hash).encode()
        ).hexdigest()

    def input_design(cube, config, scene_solar=None, window=None):
        X = (
            design
            if window is None
            else design[window[0] : window[1], window[2] : window[3]]
        )
        valid = c._brdf_spatial_mask(cube, window=window) & np.isfinite(X).all(-1)
        return X, valid, scene_solar

    func.__globals__["_brdf_design"] = input_design
    func.__globals__["_brdf_source_identity"] = identity
    return func


def main():
    maps = np.load(WORK / "geometry_native.npy", mmap_mode="r")
    data = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
        mmap_mode="r",
    )
    with rasterio.open(SOURCE) as src:
        mask = src.dataset_mask() > 0
        profile = src.profile
    geometry = {}
    for name in ["slope", "aspect", "solar_zn", "solar_az"]:
        with rasterio.open(
            "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_"
            + name
            + ".tif"
        ) as src:
            geometry[name] = src.read(1)
    statuses = []
    start = time.monotonic()
    for scenario in ["A", "B", "C_uniform", "C_center"]:
        geometry_s = dict(geometry)
        design = None
        if scenario in ["A", "B"]:
            b = 0 if scenario == "A" else 3
            geometry_s.update(sensor_zn=maps[..., b], sensor_az=maps[..., b + 1])
        else:
            design = np.load(WORK / (scenario + "_design.npy"), mmap_mode="r")
            # Only a diagnostic metadata placeholder for inherited source hashing. The
            # supplied design is fingerprinted separately and never represented as a ray.
            geometry_s.update(
                sensor_zn=np.zeros(mask.shape, np.float32),
                sensor_az=np.zeros(mask.shape, np.float32),
            )
            design_hash = sha(WORK / (scenario + "_design.npy"))
        cube = Cube(
            data, mask & (maps[..., 6] > 0), geometry_s, scale=1, footprint=mask
        )
        cube.h5_path = SOURCE
        for topo in [False, True]:
            name = scenario + ("_combined" if topo else "_brdf")
            print(
                "ACTUAL SHARED FIT",
                name,
                "elapsed",
                round(time.monotonic() - start),
                flush=True,
            )
            fit = (
                isolated(c.fit_and_save_brdf_model)
                if design is None
                else blend_adapter(c.fit_and_save_brdf_model, design, design_hash)
            )
            model_path = fit(
                cube,
                WORK / name,
                brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
                apply_topography=topo,
            )
            model = json.loads(model_path.read_text())
            # These records explicitly retain hypothetical calibration, despite possible
            # computational VALID status under the isolated experiment.
            (HERE / (name + "_model.json")).write_text(
                json.dumps(model, indent=2) + "\n"
            )
            status = dict(
                scenario=scenario,
                branch=name,
                apply_topography=topo,
                numerical_status=model["validation"]["status"],
                scientific_status="EXPERIMENTAL_NOT_VALIDATED",
                calibration="HYPOTHETICAL_UNVERIFIED",
                geometry="NADIR_SCENARIO_NOT_VERIFIED_CONTRIBUTORS",
                supported_bands=sum(
                    f["status"] == "VALID" for f in model["validation"]["fits"]
                ),
                fits=model["validation"]["fits"],
                model_path=str(model_path),
                image_created=False,
            )
            if model["validation"]["status"] == "VALID":
                output = np.lib.format.open_memmap(
                    WORK / (name + ".npy"), mode="w+", dtype="float32", shape=data.shape
                )
                apply = (
                    isolated(c.apply_brdf_correct)
                    if design is None
                    else blend_adapter(c.apply_brdf_correct, design, design_hash)
                )
                for ys, ye, xs, xe, chunk in cube.iter_chunks(chunk_y=64):
                    values = chunk
                    if topo:
                        values = isolated(c.apply_topo_correct)(
                            cube,
                            chunk,
                            ys,
                            ye,
                            xs,
                            xe,
                            scs_c=np.array(model["topographic_c"], np.float32),
                        )
                    output[ys:ye, xs:xe] = apply(
                        cube,
                        values,
                        ys,
                        ye,
                        xs,
                        xe,
                        coeff_path=model_path,
                        brdf_kernel_config=c.HYTOOLS_BRDF_KERNEL_CONFIG,
                        input_stage="topographic_only" if topo else "uncorrected",
                    )
                output.flush()
                profile.update(
                    count=10,
                    dtype="float32",
                    nodata=np.nan,
                    compress="deflate",
                    predictor=3,
                    tiled=True,
                    blockxsize=256,
                    blockysize=256,
                )
                profile.pop("photometric", None)
                path = WORK / (name + "_EXPERIMENTAL.tif")
                with rasterio.open(path, "w", **profile) as dst:
                    for b in range(10):
                        dst.write(output[..., b], b + 1)
                        dst.set_band_description(b + 1, str(cube.wavelengths[b]) + "nm")
                    dst.update_tags(
                        STATUS="EXPERIMENTAL_NOT_VALIDATED",
                        CALIBRATION="HYPOTHETICAL_UNVERIFIED",
                        PHYSICAL_DECODER="OriginalDN/32768 candidate; not certified",
                        GEOMETRY="Nadir assumption; approximate footprint; unverified same height datum and contributor assignment",
                        SCENARIO=scenario,
                        MODEL_SHA256=sha(model_path),
                        UNITS="candidate fractional reflectance",
                        PRODUCTION_APPROVED="false",
                    )
                status.update(
                    image_created=True,
                    image=str(path),
                    array=str(WORK / (name + ".npy")),
                    statistics=[dist(output[..., b]) for b in range(10)],
                )
            statuses.append(status)
            write("experiment_status.json", statuses)
            print(
                name,
                status["numerical_status"],
                "bands",
                status["supported_bands"],
                "image",
                status["image_created"],
                flush=True,
            )
    # Spatial kernel support from actual shared input designs; not millions of
    # independent directional repetitions of a common target.
    support = []
    for scenario in ["A", "B", "C_uniform", "C_center"]:
        if scenario in ["A", "B"]:
            off = 0 if scenario == "A" else 3
            g = dict(geometry, sensor_zn=maps[..., off], sensor_az=maps[..., off + 1])
            cube = Cube(data, mask & (maps[..., 6] > 0), g, scale=1, footprint=mask)
            X, valid, _ = c._brdf_design(cube, c.HYTOOLS_BRDF_KERNEL_CONFIG)
        else:
            X = np.load(WORK / (scenario + "_design.npy"), mmap_mode="r")
            valid = mask & np.isfinite(X).all(-1)
        # Compact moments, singular values and spatial tiles. No duplicated rho rows.
        gram = np.zeros((3, 3))
        sums = np.zeros(3)
        n = 0
        tiles = []
        for y in range(0, mask.shape[0], 128):
            z = X[y : y + 128][valid[y : y + 128]]
            gram += z.T @ z
            sums += z.sum(0)
            n += len(z)
            if len(z):
                singular = np.linalg.svd(z, compute_uv=False)
                tiles.append(
                    dict(
                        row_start=y,
                        n=len(z),
                        singular_values=singular,
                        condition=float(singular[0] / singular[-1]),
                        stable_rank=int(
                            np.sum(
                                singular
                                > singular[0] * np.sqrt(np.finfo(np.float32).eps)
                            )
                        ),
                    )
                )
        singular = np.sqrt(np.maximum(np.linalg.eigvalsh(gram), 0))[::-1]
        support.append(
            dict(
                scenario=scenario,
                n=n,
                singular_values=singular,
                condition=float(singular[0] / singular[-1]),
                stable_rank=int(
                    np.sum(singular > singular[0] * np.sqrt(np.finfo(np.float32).eps))
                ),
                kernel_covariance=(gram - np.outer(sums, sums) / n) / (n - 1),
                tiles=tiles,
                independent_directional_repeated_target_count=None,
            )
        )
    write("design_support.json", support)
    print("ALL FITS COMPLETE", round(time.monotonic() - start), flush=True)


if __name__ == "__main__":
    main()
