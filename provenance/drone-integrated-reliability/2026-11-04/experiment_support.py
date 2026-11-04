"""Isolated actual scientific functions; production globals/calibration unchanged."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / "provenance/goldhill-viewing-geometry/2026-11-04"
WORK = Path("/private/tmp/drone-integrated-reliability-20261104/final_v2")
path = ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03/common.py"
spec = importlib.util.spec_from_file_location("p172_support_for_p175", path)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
from spectralbridge import corrections as c, topographic as topo  # noqa:E402
from spectralbridge.pipelines import drone as drone  # noqa:E402

Cube, sha, safe, dist, SOURCE, WAVES = (
    prior.Cube,
    prior.sha,
    prior.safe,
    prior.dist,
    prior.SOURCE,
    prior.WAVES,
)


def write(name, value):
    (HERE / name).write_text(json.dumps(safe(value), indent=2, allow_nan=False) + "\n")


def isolated(function, design=None, design_hash=None):
    result = prior.isolated(function)
    if function.__name__ == "apply_topo_correct":
        result.__globals__["apply_conditioned_scs_c"] = isolated(
            topo.apply_conditioned_scs_c
        )
    if function.__name__ == "fit_and_save_brdf_model":
        result.__globals__["apply_topo_correct"] = isolated(c.apply_topo_correct)
    if function.__name__ == "apply_drone_corrections":
        result.__globals__["apply_topo_correct"] = isolated(c.apply_topo_correct)
        result.__globals__["fit_and_save_brdf_model"] = isolated(
            c.fit_and_save_brdf_model, design, design_hash
        )
        result.__globals__["apply_brdf_correct"] = isolated(
            c.apply_brdf_correct, design, design_hash
        )
    if design is not None:

        def source_identity(cube):
            return hashlib.sha256(
                (c._brdf_source_identity(cube) + design_hash).encode()
            ).hexdigest()

        def kernel_input(cube, config, scene_solar=None, window=None):
            X = (
                design
                if window is None
                else design[window[0] : window[1], window[2] : window[3]]
            )
            valid = c._brdf_spatial_mask(cube, window=window) & np.isfinite(X).all(-1)
            return X, valid, scene_solar

        result.__globals__["_brdf_source_identity"] = source_identity
        result.__globals__["_brdf_design"] = kernel_input
    return result


def load_cube():
    raw = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
        mmap_mode="r",
    )
    maps = np.load(
        "/private/tmp/goldhill-viewing-geometry-20261104/geometry_native.npy",
        mmap_mode="r",
    )
    design = np.load(
        "/private/tmp/goldhill-viewing-geometry-20261104/C_center_design.npy",
        mmap_mode="r",
    )
    geometry = {}
    for n in ["slope", "aspect", "solar_zn", "solar_az"]:
        with rasterio.open(
            "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_" + n + ".tif"
        ) as src:
            geometry[n] = src.read(1)
    geometry.update(
        sensor_zn=np.zeros(raw.shape[:2], np.float32),
        sensor_az=np.zeros(raw.shape[:2], np.float32),
    )
    with rasterio.open(SOURCE) as src:
        mask = src.dataset_mask() > 0
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
    cube = Cube(raw, mask & (maps[..., 6] > 0), geometry, scale=1, footprint=mask)
    cube.h5_path = SOURCE
    cube.projection_wkt = crs.to_wkt()
    cube.transform = transform.to_gdal()
    cube.chunk_count = lambda chunk_y=128, chunk_x=None: int(
        np.ceil(cube.lines / chunk_y)
    )

    def header():
        return dict(
            samples=cube.columns,
            lines=cube.lines,
            bands=10,
            interleave="bsq",
            **{
                "data type": 4,
                "byte order": 0,
                "wavelength": WAVES.tolist(),
                "fwhm": [28, 32, 14, 27, 16, 14, 10, 12, 18, 57],
                "wavelength units": "Nanometers",
                "data ignore value": np.nan,
                "reflectance scale factor": 1,
                "map info": [
                    "UTM",
                    1,
                    1,
                    transform.c,
                    transform.f,
                    transform.a,
                    abs(transform.e),
                    13,
                    "North",
                ],
                "coordinate system string": crs.to_wkt(),
                "projection": crs.to_wkt(),
                "brdf status": "NOT_REQUESTED",
            },
            **cube.radiometry.header(),
        )

    cube.build_envi_header = header
    return (
        cube,
        design,
        sha(
            Path("/private/tmp/goldhill-viewing-geometry-20261104/C_center_design.npy")
        ),
        maps,
        profile,
    )
