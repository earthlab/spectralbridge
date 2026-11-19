"""Retrieve bounded public lidar evidence for evergreen reference review.

Raw first-return canopy occupancy is a structural diagnostic, not evergreen truth.
No spectral values enter discovery. Missing returns remain unknown; no gap filling
is used. The primary photo-reference cohort is never modified by this script.
Requires optional laspy[lazrs]; run with PYTHONPATH pointing to that installation.
"""

import json
from itertools import product

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import planetary_computer
import requests
from pyproj import Transformer
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from shapely.geometry import box, mapping

from landsat_regional_candidates import open_asset
from landsat_spatial_expansion import CACHE, OUTPUT, sha
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

DEST = OUTPUT / "evergreen-pointcloud"


def first_return_grid(x, y, height, left, bottom, size=240):
    """One-metre maximum first-return height; unsampled bins stay unknown.

    Grids run from south to north. Nonfinite heights and outside points cannot
    contribute. Ground/low returns remain valid measurements, not missing data.
    """
    col = np.floor(x - left).astype(int)
    row = np.floor(y - bottom).astype(int)
    valid = (col >= 0) & (col < size) & (row >= 0) & (row < size) & np.isfinite(height)
    result = np.full((size, size), -np.inf)
    np.maximum.at(result, (row[valid], col[valid]), height[valid])
    result[~np.isfinite(result)] = np.nan
    return result


def cell_scores(grid):
    """Report structural area fractions over full 900-bin native footprints."""
    result = []
    for x, y in product(range(-90, 91, 30), repeat=2):
        cell = grid[y + 105 : y + 135, x + 105 : x + 135]
        assert cell.shape == (30, 30)
        result.append(
            dict(
                offset_east_m=x,
                offset_north_m=y,
                observed_fraction=float(np.isfinite(cell).mean()),
                above_2m_fraction=float((cell > 2).mean()),
                above_5m_fraction=float((cell > 5).mean()),
                above_10m_fraction=float((cell > 10).mean()),
            )
        )
    return result


def run():
    import laspy
    from laspy.copc import Bounds

    DEST.mkdir(exist_ok=True)
    patches = pd.read_csv(OUTPUT / "patch_proposals.csv")
    patches = patches.loc[
        patches.region.eq("cascades") & patches.target_hypothesis.eq("Evergreen")
    ]
    terrain = json.loads(
        (OUTPUT / "public-lidar/cascades-dtm-catalogue.json").read_text()
    )["features"]
    reports = []
    for _, patch in patches.iterrows():
        key = patch.context_patch_id
        catalogue = DEST / f"{key}-copc-catalogue.json"
        if not catalogue.exists():
            to_wgs = Transformer.from_crs(int(patch.landsat_epsg), 4326, always_xy=True)
            west, south = to_wgs.transform(patch.easting - 120, patch.northing - 120)
            east, north = to_wgs.transform(patch.easting + 120, patch.northing + 120)
            query = dict(
                collections=["3dep-lidar-copc"],
                intersects=mapping(box(west, south, east, north)),
                limit=100,
            )
            response = requests.post(
                "https://planetarycomputer.microsoft.com/api/stac/v1/search",
                json=query,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            if any(x.get("rel") == "next" for x in data.get("links", [])):
                raise ValueError(
                    "Incomplete point-cloud catalogue; pagination required"
                )
            write_json_atomic(catalogue, data)
        items = json.loads(catalogue.read_text())["features"]
        # Keep acquisition projects separate; never combine years to fill gaps.
        for project in sorted(
            {
                i["assets"]["data"]["href"].split("/usgs-copc/")[1].split("/")[0]
                for i in items
            }
        ):
            selected = [
                i
                for i in items
                if f"/usgs-copc/{project}/" in i["assets"]["data"]["href"]
            ]
            meta = DEST / f"{key}-{project}.json"
            array = DEST / f"{key}-{project}.npy"
            identity = dict(
                catalogue_sha256=sha(catalogue),
                project=project,
                method="first_return_1m_no_fill_v1",
            )
            saved = json.loads(meta.read_text()) if meta.exists() else {}
            if (
                saved.get("identity") == identity
                and array.exists()
                and sha(array) == saved.get("array_sha256")
            ):
                grid = np.load(array)
            else:
                grid = np.full((240, 240), np.nan)
                for item in selected:
                    print(key, project, item["id"], "reading bounded cloud", flush=True)
                    with laspy.CopcReader.open(
                        planetary_computer.sign(item["assets"]["data"]["href"]),
                        http_num_threads=2,
                    ) as reader:
                        cloud_crs = reader.header.parse_crs()
                        forward = Transformer.from_crs(
                            int(patch.landsat_epsg), cloud_crs, always_xy=True
                        )
                        inverse = Transformer.from_crs(
                            cloud_crs, int(patch.landsat_epsg), always_xy=True
                        )
                        a, b = forward.transform(
                            patch.easting - 121, patch.northing - 121
                        )
                        c, d = forward.transform(
                            patch.easting + 121, patch.northing + 121
                        )
                        cloud = reader.query(
                            bounds=Bounds(
                                np.array([a, b, reader.header.mins[2]]),
                                np.array([c, d, reader.header.maxs[2]]),
                            )
                        )
                    good = (
                        (np.asarray(cloud.return_number) == 1)
                        & ~np.isin(np.asarray(cloud.classification), [7, 18])
                        & ~np.asarray(cloud.withheld, dtype=bool)
                    )
                    xx, yy = inverse.transform(
                        np.asarray(cloud.x)[good], np.asarray(cloud.y)[good]
                    )
                    zz = np.asarray(cloud.z)[good]
                    # Terrain and cloud must belong to exactly the same project.
                    ground = np.full((120, 120), np.nan)
                    for dtm in sorted(
                        [
                            t
                            for t in terrain
                            if t["properties"]["3dep:usgs_id"] == project
                        ],
                        key=lambda t: t["id"],
                    ):
                        with open_asset(dtm, "data") as src:
                            with WarpedVRT(
                                src,
                                crs=cloud_crs,
                                transform=from_origin(a, b + 242, 242 / 120, 242 / 120),
                                width=120,
                                height=120,
                                resampling=Resampling.nearest,
                                nodata=float("nan"),
                            ) as vrt:
                                z = vrt.read(1, masked=True).filled(np.nan)
                        missing = ~np.isfinite(ground)
                        ground[missing] = z[missing]
                    # Terrain lookup in its declared source vertical datum; no
                    # ellipsoidal/orthometric elevation mixing is introduced.
                    sx, sy = forward.transform(xx, yy)
                    ci = np.floor((sx - a) / (242 / 120)).astype(int)
                    ri = np.floor((b + 242 - sy) / (242 / 120)).astype(int)
                    inside = (ci >= 0) & (ci < 120) & (ri >= 0) & (ri < 120)
                    height = np.full(len(zz), np.nan)
                    height[inside] = zz[inside] - ground[ri[inside], ci[inside]]
                    tile = first_return_grid(
                        xx, yy, height, patch.easting - 120, patch.northing - 120
                    )
                    grid = np.fmax(grid, tile)
                np.save(array, grid)
                saved = dict(
                    identity=identity,
                    array_sha256=sha(array),
                    source_items=[x["id"] for x in selected],
                    source_intervals=[
                        {
                            k: x["properties"].get(k)
                            for k in ["datetime", "start_datetime", "end_datetime"]
                        }
                        for x in selected
                    ],
                    structural_only=True,
                    pft_purity_verified=False,
                )
                write_json_atomic(meta, saved)
            scores = pd.DataFrame(cell_scores(grid))
            scores["context_patch_id"] = key
            scores["project"] = project
            scores["pft_purity_verified"] = False
            reports.extend(scores.to_dict("records"))
            rgb = np.load(CACHE / f"{key}.npy")
            fig, axes = plt.subplots(1, 2, figsize=(11, 5))
            axes[0].imshow(np.moveaxis(rgb, 0, -1), extent=(-120, 120, -120, 120))
            im = axes[1].imshow(
                grid,
                origin="lower",
                extent=(-120, 120, -120, 120),
                vmin=0,
                vmax=50,
                cmap="viridis",
            )
            axes[0].set_title("Aerial reference: separate epoch")
            axes[1].set_title("First-return height; missing bins white")
            for ax in axes:
                for edge in range(-105, 106, 30):
                    ax.axvline(edge, color="cyan", lw=0.3)
                    ax.axhline(edge, color="cyan", lw=0.3)
            fig.colorbar(
                im,
                ax=axes[1],
                label="Height above interpolated terrain (m)",
                shrink=0.7,
            )
            fig.suptitle(
                f"{key}: {project}\nStructural candidate only; evergreen identity/date review pending",
                fontsize=10,
            )
            fig.tight_layout()
            fig.savefig(DEST / f"{key}-{project}.png", dpi=150)
            plt.close(fig)
            write_text_atomic(
                DEST / "native_cell_structural_support.csv",
                pd.DataFrame(reports).to_csv(index=False),
            )


if __name__ == "__main__":
    run()
