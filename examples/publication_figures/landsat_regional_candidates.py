"""Find regional Landsat review candidates using an external land-cover map.

Candidate discovery uses Sentinel-derived WorldCover. PFT labels require
independent aerial/field review before these records enter separability tests.
"""

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import planetary_computer
import rasterio
import requests
from pyproj import Transformer
from rasterio.transform import from_origin, xy
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from scipy.ndimage import distance_transform_edt
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely import Point, box
from shapely.geometry import shape

from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic
from spectralbridge.landsat_agreement import mask_landsat_qa, scale_landsat_sr

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "provenance/landsat-pure-pixels/2026-11-18/expanded-search"
CACHE = ROOT / "archive/local/landsat-expanded-search"
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
REGIONS = {
    "front_range": [-105.85, 39.85, -105.40, 40.45],
    "yellowstone": [-110.85, 44.60, -110.15, 45.10],
    "cascades": [-122.10, 45.65, -121.70, 45.95],
    "gunnison_aspen": [-107.05, 38.70, -106.80, 39.00],
    "california_shrublands": [-120.00, 34.60, -119.60, 34.85],
}
EPSGS = dict(
    front_range=32613,
    yellowstone=32612,
    cascades=32610,
    gunnison_aspen=32613,
    california_shrublands=32611,
)
ACQUISITIONS = {
    "front_range": ("2023-08-01", "2023-09-30", "2023-08-21"),
    "yellowstone": ("2024-07-01", "2024-08-31", "2024-08-01"),
    "cascades": ("2023-07-01", "2023-09-15", "2023-07-15"),
    "gunnison_aspen": ("2023-08-20", "2023-10-10", "2023-09-25"),
    "california_shrublands": ("2024-05-01", "2024-07-15", "2024-05-29"),
}

MAP_CLASSES = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 60: "Bare / sparse"}
BAND_ASSETS = ["coastal", "blue", "green", "red", "nir08", "swir16", "swir22"]
DISCOVERY_GRID_METERS = 20
MIN_MAP_INTERIOR_METERS = 60
SPACING_METERS = 1000
PER_CLASS = 3


def fetch_catalogue(session, payload, depth=0):
    """Avoid slow deep NAIP pagination by querying smaller spatial partitions."""
    response = session.post(STAC, json=payload, timeout=45)
    response.raise_for_status()
    data = response.json()
    if any(link.get("rel") == "next" for link in data["links"]):
        if depth >= 6:
            raise ValueError("Catalog remains truncated after six spatial subdivisions")
        left, bottom, right, top = payload["bbox"]
        mid_x, mid_y = (left + right) / 2, (bottom + top) / 2
        partitions = [
            [left, bottom, mid_x, mid_y],
            [mid_x, bottom, right, mid_y],
            [left, mid_y, mid_x, top],
            [mid_x, mid_y, right, top],
        ]
        features = []
        for bounds in partitions:
            subset = fetch_catalogue(session, payload | {"bbox": bounds}, depth + 1)
            features.extend(subset["features"])
        data["features"] = list({item["id"]: item for item in features}.values())
    data["links"] = [link for link in data["links"] if link.get("rel") != "next"]
    data["spectralbridge:query"] = payload
    return data


def catalogue():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.mount(
        "https://",
        HTTPAdapter(
            max_retries=Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST"],
            )
        ),
    )
    write_json_atomic(OUTPUT / "regions.json", REGIONS)
    for region, bounds in REGIONS.items():
        collections = ("esa-worldcover", "naip", "landsat-c2-l2")
        if region == "gunnison_aspen":
            collections += ("gap",)
        for collection in collections:
            path = OUTPUT / f"{region}-{collection}.json"
            payload = dict(collections=[collection], bbox=bounds, limit=100)
            if collection == "landsat-c2-l2":
                payload.update(
                    datetime=f"{ACQUISITIONS[region][0]}T00:00:00Z/{ACQUISITIONS[region][1]}T23:59:59Z",
                    query={
                        "platform": {"eq": "landsat-9"},
                        "eo:cloud_cover": {"lt": 35},
                    },
                )
            elif collection == "naip":
                payload["datetime"] = "2022-01-01T00:00:00Z/2024-12-31T23:59:59Z"
            elif collection == "esa-worldcover":
                payload["datetime"] = "2021-01-01T00:00:00Z/2021-12-31T23:59:59Z"
            if path.exists():
                saved = json.loads(path.read_text())
                if saved.get("spectralbridge:query") == payload:
                    continue
            data = fetch_catalogue(session, payload)
            write_json_atomic(path, data)
            print(region, collection, len(data["features"]), flush=True)


def items(region, collection):
    return json.loads((OUTPUT / f"{region}-{collection}.json").read_text())["features"]


def open_asset(item, key):
    return rasterio.open(planetary_computer.sign(item["assets"][key]["href"]))


def map_grid(region, collection="esa-worldcover"):
    CACHE.mkdir(parents=True, exist_ok=True)
    transformer = Transformer.from_crs(4326, EPSGS[region], always_xy=True)
    left, bottom, right, top = transformer.transform_bounds(*REGIONS[region])
    resolution = DISCOVERY_GRID_METERS
    left, top = (
        np.floor(left / resolution) * resolution,
        np.ceil(top / resolution) * resolution,
    )
    transform = from_origin(left, top, resolution, resolution)
    height, width = (
        int(np.ceil((top - bottom) / resolution)),
        int(np.ceil((right - left) / resolution)),
    )
    tag = "worldcover" if collection == "esa-worldcover" else collection
    path = CACHE / f"{region}-{tag}.npz"
    if path.exists():
        with np.load(path) as data:
            grid = data["grid"]
        if grid.shape != (height, width):
            raise ValueError("Cached WorldCover grid differs from requested region")
        return grid, transform
    grid = np.zeros((height, width), dtype=np.uint16)
    for item in items(region, collection):
        print(region, "reading", item["id"], flush=True)
        with (
            open_asset(
                item, "map" if collection == "esa-worldcover" else "data"
            ) as raster,
            WarpedVRT(
                raster,
                crs=EPSGS[region],
                transform=transform,
                width=width,
                height=height,
                resampling=rasterio.enums.Resampling.nearest,
                nodata=0,
            ) as warped,
        ):
            local = warped.read(1)
        grid[local != 0] = local[local != 0]
    temporary = path.with_suffix(".npz.tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, grid=grid)
    temporary.replace(path)
    return grid, transform


def interior_centers(mask, count=PER_CLASS):
    """Rank coarse map interiors with a minimum separation between proposals."""
    padded = np.pad(mask, 1, constant_values=False)
    distances = distance_transform_edt(padded)[1:-1, 1:-1] * DISCOVERY_GRID_METERS
    ranked = distances.copy()
    for _ in range(count):
        row, col = np.unravel_index(np.argmax(ranked), ranked.shape)
        score = float(ranked[row, col])
        if score < MIN_MAP_INTERIOR_METERS:
            return
        yield row, col, score
        radius = int(np.ceil(SPACING_METERS / DISCOVERY_GRID_METERS))
        r0, r1 = max(0, row - radius), min(mask.shape[0], row + radius + 1)
        c0, c1 = max(0, col - radius), min(mask.shape[1], col + radius + 1)
        dy, dx = np.ogrid[r0 - row : r1 - row, c0 - col : c1 - col]
        ranked[r0:r1, c0:c1][dx * dx + dy * dy < radius * radius] = 0


def discover(region):
    grid, transform = map_grid(region)
    to_lonlat = Transformer.from_crs(EPSGS[region], 4326, always_xy=True)
    rows = []
    for code, label in MAP_CLASSES.items():
        for rank, (row, col, distance) in enumerate(
            interior_centers(grid == code), start=1
        ):
            east, north = xy(transform, row, col)
            lon, lat = to_lonlat.transform(east, north)
            rows.append(
                dict(
                    region=region,
                    map_class=code,
                    map_label=label,
                    rank=rank,
                    map_interior_m=distance,
                    longitude=lon,
                    latitude=lat,
                    researcher_category=None,
                    reference_review="pending",
                )
            )
    if region == "gunnison_aspen":
        forest_types, _ = map_grid(region, "gap")
        # GAP code 148 is Rocky Mountain Aspen Forest and Woodland.
        # The 2011 map is a locator, while dated aerial chips provide current context.
        for rank, (row, col, distance) in enumerate(
            interior_centers(forest_types == 148), start=1
        ):
            east, north = xy(transform, row, col)
            lon, lat = to_lonlat.transform(east, north)
            rows.append(
                dict(
                    region=region,
                    map_class=148,
                    map_label="Aspen forest (2011 map)",
                    rank=rank,
                    map_interior_m=distance,
                    longitude=lon,
                    latitude=lat,
                    researcher_category=None,
                    reference_review="pending",
                )
            )
    return pd.DataFrame(rows)


def scene_order(point, scenes, target_date="2023-08-14"):
    available = [item for item in scenes if shape(item["geometry"]).covers(point)]
    # Rank by aerial-reference season and scene cloudiness, then check local QA.
    return sorted(
        available,
        key=lambda item: (
            abs(
                (
                    pd.Timestamp(item["properties"]["datetime"])
                    - pd.Timestamp(target_date, tz="UTC")
                ).days
            ),
            item["properties"]["eo:cloud_cover"],
            item["id"],
        ),
    )


def landsat_sample(candidate, scenes):
    point = Point(candidate["longitude"], candidate["latitude"])
    for scene in scene_order(point, scenes, ACQUISITIONS[candidate["region"]][2]):
        with (
            open_asset(scene, "qa_pixel") as qa,
            open_asset(scene, "qa_radsat") as saturation,
        ):
            project = Transformer.from_crs(4326, qa.crs, always_xy=True)
            coord = project.transform(point.x, point.y)
            row, col = qa.index(*coord)
            if not (0 <= row < qa.height and 0 <= col < qa.width):
                continue
            east, north = xy(qa.transform, row, col)
            coord = east, north
            pixel_qa = next(qa.sample([coord]))[0]
            if (saturation.crs, saturation.transform, saturation.shape) != (
                qa.crs,
                qa.transform,
                qa.shape,
            ):
                raise ValueError("Scene QA grids differ")
            sat_qa = next(saturation.sample([coord]))[0]
            valid, _ = mask_landsat_qa([pixel_qa], [sat_qa])
            if not valid[0]:
                continue
            grid = qa.crs, qa.transform, qa.shape
        values = []
        for key in BAND_ASSETS:
            with open_asset(scene, key) as band:
                if (band.crs, band.transform, band.shape) != grid:
                    raise ValueError("Scene band grid differs from QA")
                values.append(next(band.sample([coord]))[0])
        values = scale_landsat_sr(values)
        if not np.isfinite(values).all():
            continue
        inverse = Transformer.from_crs(grid[0], 4326, always_xy=True)
        lon, lat = inverse.transform(east, north)
        return candidate | {
            "scene_id": scene["id"],
            "scene_datetime": scene["properties"]["datetime"],
            "landsat_row": row,
            "landsat_col": col,
            "landsat_epsg": grid[0].to_epsg(),
            "longitude": lon,
            "latitude": lat,
            "easting": east,
            "northing": north,
            "qa_pixel": int(pixel_qa),
            "qa_radsat": int(sat_qa),
            **dict(zip([f"B{i}" for i in range(1, 8)], values, strict=True)),
        }
    return candidate | {"scene_id": None, "screening_status": "no_clear_scene"}


def aerial_chip(candidate, aerials):
    point = Point(candidate["longitude"], candidate["latitude"])
    scenes = [item for item in aerials if shape(item["geometry"]).covers(point)]
    scenes.sort(
        key=lambda item: (
            abs(
                (
                    pd.Timestamp(item["properties"]["datetime"])
                    - pd.Timestamp(candidate["scene_datetime"])
                ).days
            ),
            item["id"],
        )
    )
    for item in scenes:
        with (
            open_asset(item, "image") as image,
            WarpedVRT(
                image,
                crs=candidate["landsat_epsg"],
                resampling=rasterio.enums.Resampling.bilinear,
            ) as aerial,
        ):
            east, north = candidate["easting"], candidate["northing"]
            if not box(*aerial.bounds).covers(
                box(east - 40, north - 40, east + 40, north + 40)
            ):
                continue
            col, row = ~aerial.transform * (east - 40, north + 40)
            window = Window(col, row, 80 / aerial.res[0], 80 / aerial.res[1])
            rgb = aerial.read(
                (1, 2, 3), window=window, out_shape=(3, 200, 200), masked=True
            )
            rgb = rgb.astype(float).filled(np.nan)
            if not np.isfinite(rgb).all() or np.any(np.all(rgb == 0, axis=0)):
                continue
            return dict(
                naip_id=item["id"],
                naip_datetime=item["properties"]["datetime"],
                naip_lag_days=abs(
                    (
                        pd.Timestamp(item["properties"]["datetime"])
                        - pd.Timestamp(candidate["scene_datetime"])
                    ).days
                ),
            ), rgb
    return dict(naip_id=None), None


def review_sheet(region, records, chips):
    figure, axes = plt.subplots(3, 4, figsize=(12, 10))
    for ax in axes.flat:
        ax.axis("off")
    for ax, (record, image) in zip(axes.flat, chips):
        ax.imshow(
            np.moveaxis(np.clip(image / 255, 0, 1), 0, -1), extent=(-40, 40, -40, 40)
        )
        ax.add_patch(
            plt.Rectangle(
                (-15, -15), 30, 30, fill=False, edgecolor="#00ffff", linewidth=1.5
            )
        )
        ax.set_title(
            f"{record['map_label']}\n"
            f"#{record['rank']} · {record['latitude']:.4f}, {record['longitude']:.4f}\n"
            f"NAIP date gap {record['naip_lag_days']} d",
            fontsize=8,
        )
    figure.suptitle(
        region.replace("_", " ").title() + " · regional review candidates",
        weight="bold",
    )
    figure.text(
        0.5,
        0.02,
        "Cyan = native 30 m Landsat cell. 80 m context. Map discovery labels require full-footprint PFT review.",
        ha="center",
        fontsize=9,
    )
    figure.subplots_adjust(
        left=0.03, right=0.99, bottom=0.07, top=0.90, wspace=0.10, hspace=0.35
    )
    figure.savefig(OUTPUT / f"{region}-aerial-review.png", dpi=150)
    plt.close(figure)
    frame = pd.DataFrame(records)
    write_text_atomic(OUTPUT / f"{region}-candidates.csv", frame.to_csv(index=False))
    spatial = gpd.GeoDataFrame(
        frame.drop(columns=[f"B{i}" for i in range(1, 8)], errors="ignore"),
        geometry=gpd.points_from_xy(frame.longitude, frame.latitude),
        crs=4326,
    )
    spatial.to_file(OUTPUT / f"{region}-candidates.geojson", driver="GeoJSON")
    return frame


def run_region(region):
    proposals_path = OUTPUT / f"{region}-proposals.csv"
    if proposals_path.exists():
        proposals = (
            pd.read_csv(proposals_path).astype(object).where(lambda d: d.notna(), None)
        )
        if region == "gunnison_aspen" and not proposals.map_class.eq(148).any():
            proposals = discover(region)
            proposals.to_csv(proposals_path, index=False)
    else:
        proposals = discover(region)
        proposals.to_csv(proposals_path, index=False)
    records, chips = [], []
    scenes, aerials = items(region, "landsat-c2-l2"), items(region, "naip")
    for proposal in proposals.to_dict("records"):
        key = f"{region}-{proposal['map_class']}-{proposal['rank']}"
        checkpoint = CACHE / f"{key}.json"
        chip_path = CACHE / f"{key}.npy"
        record = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
        signature = list(ACQUISITIONS[region])
        if record.get("acquisition_selection") == signature:
            chip = (
                np.load(chip_path)
                if record.get("naip_id") and chip_path.exists()
                else None
            )
        else:
            print(key, "checking Landsat", flush=True)
            record = landsat_sample(proposal, scenes)
            chip = None
            if record["scene_id"] is not None:
                print(key, "checking aerial", flush=True)
                metadata, chip = aerial_chip(record, aerials)
                record |= metadata
                if chip is not None:
                    temporary = chip_path.with_suffix(".npy.tmp")
                    with temporary.open("wb") as handle:
                        np.save(handle, chip)
                    temporary.replace(chip_path)
            record["acquisition_selection"] = signature
            write_json_atomic(checkpoint, record)
        if record.get("naip_id"):
            record["naip_lag_days"] = abs(
                (
                    pd.Timestamp(record["naip_datetime"]).normalize()
                    - pd.Timestamp(record["scene_datetime"]).normalize()
                ).days
            )
            write_json_atomic(checkpoint, record)
        records.append(record)
        if chip is not None:
            chips.append((record, chip))
        print(key, record.get("scene_id"), record.get("naip_id"), flush=True)
        # Persist progress after each completed candidate.
        write_text_atomic(
            OUTPUT / f"{region}-candidates.csv",
            pd.DataFrame(records).to_csv(index=False),
        )
    review_sheet(region, records, chips)


def finalize_quality():
    frames = [pd.read_csv(OUTPUT / f"{region}-candidates.csv") for region in REGIONS]
    frame = pd.concat(frames, ignore_index=True)
    frame["candidate_id"] = (
        frame.region
        + "-"
        + frame.map_class.astype(str)
        + "-"
        + frame["rank"].astype(str)
    )
    frame["aerosol_level"] = np.nan
    frame["aerosol_retrieval_valid"] = False
    frame["aerosol_interpolated"] = False
    frame["qa_clear_150m_context"] = False
    scene_index = {
        item["id"]: item
        for region in REGIONS
        for item in items(region, "landsat-c2-l2")
    }
    for scene_id, group in frame.dropna(subset=["scene_id"]).groupby("scene_id"):
        print("Auditing atmospheric/context QA", scene_id, flush=True)
        item = scene_index[scene_id]
        with (
            open_asset(item, "qa_aerosol") as aerosol,
            open_asset(item, "qa_pixel") as qa,
        ):
            if (aerosol.crs, aerosol.transform, aerosol.shape) != (
                qa.crs,
                qa.transform,
                qa.shape,
            ):
                raise ValueError("Aerosol and pixel QA grids differ")
            coords = list(zip(group.easting, group.northing, strict=True))
            aerosol_bits = np.array(
                [sample[0] for sample in aerosol.sample(coords)], dtype=np.uint16
            )
            frame.loc[group.index, "aerosol_level"] = (aerosol_bits >> 6) & 3
            frame.loc[group.index, "aerosol_retrieval_valid"] = (aerosol_bits & 2) != 0
            frame.loc[group.index, "aerosol_interpolated"] = (aerosol_bits & 32) != 0
            for index, row in group.iterrows():
                window = Window(row.landsat_col - 2, row.landsat_row - 2, 5, 5)
                values = qa.read(1, window=window, boundless=True, fill_value=1)
                frame.loc[index, "qa_clear_150m_context"] = bool(
                    ((values & 63) == 0).all()
                )
    frame["landsat_water_flag"] = (
        frame.qa_pixel.fillna(0).astype(int).map(lambda q: bool(q & 128))
    )
    frame["priority_observation"] = (
        ~frame.landsat_water_flag
        & frame.scene_id.notna()
        & frame.naip_id.notna()
        & frame.qa_clear_150m_context
        & frame.aerosol_level.le(2)
        & frame.aerosol_retrieval_valid
        & ~frame.aerosol_interpolated
        & frame.naip_lag_days.le(45)
    )
    frame["pft_purity_verified"] = False
    write_text_atomic(
        OUTPUT / "regional_candidate_dataset.csv", frame.to_csv(index=False)
    )
    valid = frame.loc[frame.scene_id.notna()].copy()
    if valid.duplicated(["scene_id", "landsat_row", "landsat_col"]).any():
        raise ValueError("Repeated native Landsat cell in regional cohort")
    geometry = gpd.GeoSeries(
        [
            box(
                row.easting - 15, row.northing - 15, row.easting + 15, row.northing + 15
            )
            for row in valid.itertuples()
        ]
    )
    # Transform each cell from its own scene UTM CRS before concatenation.
    geometries = [
        gpd.GeoSeries([geom], crs=int(epsg)).to_crs(4326).iloc[0]
        for geom, epsg in zip(geometry, valid.landsat_epsg, strict=True)
    ]
    blinded = valid.drop(columns=[f"B{i}" for i in range(1, 8)])
    gpd.GeoDataFrame(blinded, geometry=geometries, crs=4326).to_file(
        OUTPUT / "regional_review_footprints.geojson", driver="GeoJSON"
    )
    paths = sorted(
        path
        for path in OUTPUT.iterdir()
        if path.suffix in {".json", ".csv", ".png", ".md", ".geojson"}
    )
    manifest = dict(
        selection="WorldCover and GAP coarse interiors; no Landsat band value used for discovery",
        grid_resolution_m=DISCOVERY_GRID_METERS,
        minimum_map_interior_m=MIN_MAP_INTERIOR_METERS,
        per_class_spacing_m=SPACING_METERS,
        candidate_count=len(frame),
        observed_seven_band_count=int(frame.scene_id.notna().sum()),
        priority_observation_count=int(frame.priority_observation.sum()),
        purity_verified_count=0,
        builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        files={
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
            if path.name != "source_manifest.json"
        },
    )
    write_json_atomic(OUTPUT / "source_manifest.json", manifest)
    print(json.dumps({key: value for key, value in manifest.items() if key != "files"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue", action="store_true")
    parser.add_argument("--region", choices=list(REGIONS))
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.catalogue:
        catalogue()
    if args.region:
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            GDAL_HTTP_TIMEOUT=30,
            GDAL_HTTP_MAX_RETRY=2,
        ):
            run_region(args.region)
    if args.finalize:
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            GDAL_HTTP_TIMEOUT=30,
            GDAL_HTTP_MAX_RETRY=2,
        ):
            finalize_quality()
