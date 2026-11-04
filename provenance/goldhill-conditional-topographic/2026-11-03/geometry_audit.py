"""Read-only terrain/native-grid and angular sensitivity audit; no new truth geometry."""

from pathlib import Path
import sys

import numpy as np
import rasterio
from pyproj import Proj, Transformer
from rasterio.warp import reproject, Resampling

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import SOURCE, write, distribution, sha  # noqa: E402
from spectralbridge.corrections import calc_cosine_i  # noqa: E402


def main():
    with rasterio.open(SOURCE) as src:
        profile = src.profile.copy()
        mask = src.dataset_mask() > 0
        lon, lat = Transformer.from_crs(src.crs, 4326, always_xy=True).transform(
            *src.xy(src.height // 2, src.width // 2)
        )
    g = {}
    inventory = []
    for n in ["slope", "aspect", "solar_zn", "solar_az"]:
        path = (
            Path("/private/tmp/goldhill-end-to-end-20261103/ancillary")
            / f"legacy_{n}.tif"
        )
        with rasterio.open(path) as src:
            a = src.read(1)
            a[~(src.read_masks(1) > 0)] = np.nan
            g[n] = np.deg2rad(a)
            inventory.append(
                dict(
                    path=str(path),
                    sha256=sha(path),
                    pixel_size=src.res,
                    shape=src.shape,
                    units="degrees in stored ancillary; converted once to radians",
                    valid_statistics=distribution(a[mask]),
                )
            )
    convergence = Proj(profile["crs"]).get_factors(lon, lat).meridian_convergence
    base = calc_cosine_i(g["solar_zn"], g["solar_az"], g["aspect"], g["slope"])
    valid = mask & np.isfinite(base)
    comparisons = []
    for label, aspect, slope in [
        (
            "aspect_plus_grid_convergence",
            g["aspect"] + np.deg2rad(convergence),
            g["slope"],
        ),
        (
            "aspect_minus_grid_convergence",
            g["aspect"] - np.deg2rad(convergence),
            g["slope"],
        ),
    ]:
        ci = calc_cosine_i(g["solar_zn"], g["solar_az"], aspect, slope)
        comparisons.append(
            dict(
                case=label,
                absolute_ci_difference=distribution(abs(ci[valid] - base[valid])),
            )
        )
    # Native DTM/DEM slope at each delivered raster resolution: diagnostic only.
    native = []
    maps = {}
    for name in ["goldhill_dtm", "goldhill_dem", "goldhill_aligned_dem"]:
        path = Path("/private/tmp/photogrammetry-metadata-20261102") / (name + ".tif")
        with rasterio.open(path) as src:
            z = src.read(1).astype(float)
            z[src.read_masks(1) == 0] = np.nan
            dy, dx = np.gradient(z, src.res[1], src.res[0])
            slope = np.arctan(np.hypot(dx, dy))
            aspect = np.mod(np.arctan2(-dx, dy), 2 * np.pi)
            warped = np.full(mask.shape, np.nan, np.float32)
            reproject(
                np.rad2deg(slope).astype("float32"),
                warped,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=profile["transform"],
                dst_crs=profile["crs"],
                src_nodata=np.nan,
                dst_nodata=np.nan,
                resampling=Resampling.bilinear,
            )
            v = valid & np.isfinite(warped)
            native.append(
                dict(
                    name=name,
                    path=str(path),
                    sha256=sha(path),
                    resolution_m=src.res,
                    shape=src.shape,
                    crs=str(src.crs),
                    elevation_units=src.units,
                    gradient_assumption="vertical values metres, north-up grid; diagnostic, not independently certified terrain",
                    slope_degrees=distribution(warped[v]),
                    legacy_slope_difference_degrees=distribution(
                        warped[v] - np.rad2deg(g["slope"][v])
                    ),
                )
            )
            maps[name] = warped[::6, ::6]
            # Keep no derived elevation/slope raster as production input.
            del aspect
    write(
        "terrain_audit.json",
        dict(
            ancillary_inventory=inventory,
            original_terrain=native,
            meridian_convergence_degrees=convergence,
            grid_north_sensitivity=comparisons,
            terrain_provenance="Available R scripts intend 0.25m ground-classified TIN then degree slope/aspect and scalar bilinear alignment; exact execution/source linkage unresolved. 10cm sampling does not imply independent 10cm terrain information. Scalar aspect interpolation near 0/360 is a possible artifact, not established cause here.",
            shadows="cos(i)<=0 is local terrain self-shadow only; cast/canopy shadows cannot be certified without horizon/visibility and contributor information.",
            terrain_diagnostic_hashes_preserved=all(
                sha(x["path"]) == x["sha256"] for x in native
            ),
        ),
    )
    np.savez_compressed(HERE / "terrain_maps.npz", **maps)


if __name__ == "__main__":
    main()
