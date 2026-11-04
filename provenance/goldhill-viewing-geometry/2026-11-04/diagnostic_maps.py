"""Georeferenced shared-kernel maps for the two single-camera scenarios."""

import json
from pathlib import Path
import sys
import numpy as np
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"))
from common import Cube, SOURCE  # noqa:E402
from spectralbridge import corrections as c  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")


def main():
    maps = np.load(WORK / "geometry_native.npy", mmap_mode="r")
    raw = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
        mmap_mode="r",
    )
    with rasterio.open(SOURCE) as src:
        mask = src.dataset_mask() > 0
        profile = src.profile
    geom = {}
    for n in ["solar_az", "solar_zn"]:
        with rasterio.open(
            "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_" + n + ".tif"
        ) as src:
            geom[n] = src.read(1)
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
    for scenario, off in [("A", 0), ("B", 3)]:
        m = json.loads((HERE / (scenario + "_brdf_model.json")).read_text())
        g = dict(geom, sensor_zn=maps[..., off], sensor_az=maps[..., off + 1])
        cube = Cube(raw, mask & (maps[..., 6] > 0), g, scale=1, footprint=mask)
        X, valid, _ = c._brdf_design(
            cube, c.HYTOOLS_BRDF_KERNEL_CONFIG, scene_solar=m["scene_solar_zenith_rad"]
        )
        names = [
            "zenith_deg",
            "true_azimuth_deg",
            "relative_azimuth_deg",
            "RossThick",
            "LiDenseR",
            "assigned_acquisition_order",
            "BRDF_factor650",
            "BRDF_factor717",
            "prediction650",
            "prediction717",
        ]
        arrays = [
            maps[..., off],
            maps[..., off + 1],
            (geom["solar_az"] - maps[..., off + 1]) % 360,
            X[..., 1],
            X[..., 2],
            maps[..., off + 2],
        ]
        predictions = []
        for b in [4, 7]:
            beta = np.array([m[k][0][b] for k in ["iso", "vol", "geo"]])
            pred = X @ beta
            ref = np.array(m["reference_design"]) @ beta
            arrays.append(ref / pred)
            predictions.append(pred)
        arrays += predictions
        with rasterio.open(
            WORK / (scenario + "_view_and_kernel_maps_EXPERIMENTAL.tif"), "w", **profile
        ) as dst:
            for b, (name, a) in enumerate(zip(names, arrays), 1):
                dst.write(np.where(valid, a, np.nan).astype("float32"), b)
                dst.set_band_description(b, name)
            dst.update_tags(
                STATUS="EXPERIMENTAL_INFERRED_GEOMETRY",
                AZIMUTH="true north clockwise, to sensor",
                CALIBRATION="HYPOTHETICAL_UNVERIFIED",
                CONTRIBUTORS="not verified",
            )
        print(scenario, "kernel maps complete", flush=True)


if __name__ == "__main__":
    main()
