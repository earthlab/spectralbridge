# ruff: noqa: E402
"""Full native-grid reconstruction; source-only assignment, no reflectance tuning."""

import concurrent.futures
import json
from pathlib import Path
import sys
import time

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import CRS, Geod, Transformer
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"
sys.path.insert(0, str(PRIOR))
from common import SOURCE, sha, safe, dist  # noqa:E402
from spectralbridge.drone_view_geometry import (
    camera_rays,
    footprint_candidates,
    assign_camera,
    NadirFootprint,
    aggregate_kernels,
)  # noqa:E402
from spectralbridge import corrections as c  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")
POSES = (
    ROOT / "provenance/goldhill-end-to-end/2026-11-03/camera_poses_with_photo_times.csv"
)
DEM = Path("/private/tmp/photogrammetry-metadata-20261102/goldhill_aligned_dem.tif")
POLYS = ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
FIELDS = [
    "A_zenith",
    "A_azimuth",
    "A_camera",
    "B_zenith",
    "B_azimuth",
    "B_camera",
    "C_count",
    "C_min_zenith",
    "C_max_zenith",
    "C_median_zenith",
    "C_mean_azimuth",
    "C_azimuth_resultant",
    "C_mean_relative",
    "C_relative_resultant",
    "C_RossThick",
    "C_LiDenseR",
    "C_Ross_std",
    "C_Li_std",
    "C_weighted_Ross",
    "C_weighted_Li",
]


def write(n, v):
    (HERE / n).write_text(json.dumps(safe(v), indent=2, allow_nan=False) + "\n")


def main():
    completed = HERE / "native_artifacts.json"
    if completed.exists():
        saved = json.loads(completed.read_text())
        if saved["script_sha256"] != sha(Path(__file__)) or saved[
            "module_sha256"
        ] != sha(ROOT / "src/spectralbridge/drone_view_geometry.py"):
            raise ValueError(
                "Reconstruction implementation changed; preserve evidence and choose a fresh dated namespace"
            )
        for path, expected in {
            **json.loads((HERE / "input_manifest.json").read_text())[
                "protected_hashes"
            ],
            **saved["artifacts"],
        }.items():
            if sha(path) != expected:
                raise ValueError(
                    "Input or output identity changed; preserve evidence and choose a fresh namespace: "
                    + path
                )
        print("Reusing exact verified native geometry outputs", flush=True)
        return
    WORK.mkdir(exist_ok=True, parents=True)
    inputs = [
        SOURCE,
        DEM,
        POSES,
        POLYS,
        ROOT
        / "provenance/goldhill-micasense-calibration/2026-11-03/goldhill_processing_report_text.txt",
    ]
    # Freeze all completed P172 artifacts, not a recursive hash assertion about changed source code.
    inputs += [
        p for p in PRIOR.rglob("*") if p.is_file() and "__pycache__" not in p.parts
    ]
    write(
        "input_manifest.json",
        dict(
            protected_hashes={str(p): sha(p) for p in inputs},
            revision=__import__("subprocess")
            .check_output(["git", "rev-parse", "HEAD"], text=True)
            .strip(),
            source_module_sha256=sha(ROOT / "src/spectralbridge/corrections.py"),
        ),
    )
    poses = pd.read_csv(POSES)
    positions = (
        poses.drop_duplicates(["X", "Y", "Z"])
        .sort_values(["timestamp_unzoned", "PhotoID"])
        .reset_index(drop=True)
    )
    positions["order"] = np.arange(len(positions))
    positions["band_records"] = (
        poses.groupby(["X", "Y", "Z"])
        .size()
        .reindex(pd.MultiIndex.from_frame(positions[["X", "Y", "Z"]]))
        .to_numpy()
    )
    xy = positions[["X", "Y"]].to_numpy()
    vel = np.gradient(xy, axis=0)
    heading = np.arctan2(vel[:, 0], vel[:, 1])
    # Flight is near N/S: segment on sign reversal of smoothed northing travel.
    north_sign = np.sign(vel[:, 1])
    line = np.cumsum(np.r_[False, north_sign[1:] != north_sign[:-1]])
    turn = np.abs(vel[:, 0]) > np.abs(vel[:, 1]) * 0.577350269
    positions["heading_grid_deg"] = np.rad2deg(heading)
    positions["leg"] = line
    positions["turn_candidate"] = turn
    positions["spacing_m"] = np.r_[np.nan, np.linalg.norm(np.diff(xy, axis=0), axis=1)]
    times = pd.to_datetime(positions.timestamp_unzoned)
    positions["seconds_since_first"] = (times - times.iloc[0]).dt.total_seconds()
    positions.to_csv(HERE / "acquisition_path.csv", index=False)
    with rasterio.open(SOURCE) as src:
        mask = src.dataset_mask() > 0
        shape = mask.shape
        transform = src.transform
        bounds = src.bounds
        profile = src.profile
    with rasterio.open(DEM) as src:
        assert src.shape == shape and src.crs == CRS.from_epsg(26913)
        assert np.allclose(tuple(src.transform), tuple(transform), rtol=0, atol=1e-6)
        terrain = src.read(1)
        terrain = np.where(src.read_masks(1) > 0, terrain, np.nan)
    cam = positions[["X", "Y", "Z"]].to_numpy()
    row, col = rasterio.transform.rowcol(transform, cam[:, 0], cam[:, 1])
    under = terrain[row, col]
    ll = Transformer.from_crs(26913, 4326, always_xy=True)
    geod = Geod(ellps="GRS80")
    xcenter, ycenter = (
        (bounds.left + bounds.right) / 2,
        (bounds.bottom + bounds.top) / 2,
    )
    gamma = geod.inv(
        *ll.transform(xcenter, ycenter), *ll.transform(xcenter, ycenter + 10)
    )[0]
    corners = [(bounds.left, bounds.bottom), (bounds.right, bounds.top)]
    gammas = [
        geod.inv(*ll.transform(x, y), *ll.transform(x, y + 10))[0] for x, y in corners
    ]
    field = gpd.read_file(POLYS).to_crs(26913)
    fieldgold = field.cx[bounds.left : bounds.right, bounds.bottom : bounds.top]
    wrong = Transformer.from_crs(5070, 26913, always_xy=True).transform(
        cam[:, 0], cam[:, 1]
    )
    rotation = (
        poses[[f"r{i}{j}" for i in range(1, 4) for j in range(1, 4)]]
        .to_numpy()
        .reshape(-1, 3, 3)
    )
    write(
        "flight_and_crs.json",
        dict(
            records=len(poses),
            positions=len(cam),
            bands_per_position=positions.band_records.value_counts().to_dict(),
            timestamp_start=str(times.iloc[0]),
            timestamp_end=str(times.iloc[-1]),
            duration_seconds=float((times.iloc[-1] - times.iloc[0]).total_seconds()),
            timestamp_status="Recovered camera tags; UTC interpretation conditional; no independent clock certification",
            report_project_and_DEM_CRS="NAD83 / UTM zone 13N (EPSG::26913), processing report page18/19",
            CSV_declared_CRS=5070,
            adopted_horizontal_CRS=26913,
            decision="Explicit evidence-backed interpretation of reported XY; source CSV unchanged",
            camera_center_lonlat_26913=ll.transform(*xy.mean(0)),
            camera_center_lonlat_5070=Transformer.from_crs(
                5070, 4326, always_xy=True
            ).transform(*xy.mean(0)),
            minimum_wrong_CRS_distance_to_scene_m=float(
                np.min(np.hypot(wrong[0] - xcenter, wrong[1] - ycenter))
            ),
            positions_in_source_alpha=int(mask[row, col].sum()),
            researcher_polygons_in_scene=len(fieldgold),
            north_rotation_deg=gamma,
            north_rotation_corner_range_deg=gammas,
            height_above_aligned_surface=dist(cam[:, 2] - under),
            report_flying_altitude_m=123,
            vertical_status="Shared metre-height datum unverified; same-datum baseline and explicit camera-height offsets +/-30m",
            camera_Z=dist(cam[:, 2]),
            terrain_Z=dist(terrain[mask]),
            spacing=dist(positions.spacing_m),
            speed_m_s=dist(
                np.linalg.norm(np.diff(xy, axis=0), axis=1)
                / times.diff().dt.total_seconds().to_numpy()[1:]
            ),
            legs=int(line.max() + 1),
            turn_candidates=int(turn.sum()),
            rotation_determinant=dist(np.linalg.det(rotation)),
            rotation_orthogonality_error=dist(
                np.linalg.norm(
                    rotation @ rotation.transpose(0, 2, 1) - np.eye(3), axis=(1, 2)
                )
            ),
            orientation_status="Matrices orthogonal but camera/world conventions unresolved; optical axes forced nadir by experimental assumption",
            intrinsics=dict(
                width_px=1280,
                height_px=960,
                focal_mm=5.5,
                pixel_um=3.75,
                source="Goldhill report pages2-3; ideal pinhole footprint, not full calibrated distortion or recovered yaw",
            ),
            footprint_heading="Image height follows smoothed flight direction; width across track. Rotation90 and size multipliers tested separately.",
            solar_policy="Retain inherited spatial solar azimuth and scene-mean solar zenith; no assignment-time solar overwrite",
        ),
    )
    solar = {}
    for name in ["solar_az", "solar_zn"]:
        with rasterio.open(
            "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_"
            + name
            + ".tif"
        ) as src:
            solar[name] = src.read(1)
    scene = float(
        np.mean(
            np.deg2rad(solar["solar_zn"][mask].astype(np.float32)), dtype=np.float64
        )
    )
    fp = NadirFootprint(1280, 960, 5.5, 3.75)
    out = np.lib.format.open_memmap(
        WORK / "geometry_native.npy",
        mode="w+",
        dtype="float32",
        shape=(*shape, len(FIELDS)),
    )
    out[:] = np.nan
    designs = [
        np.lib.format.open_memmap(
            WORK / f"C_{weight}_design.npy",
            mode="w+",
            dtype="float64",
            shape=(*shape, 3),
        )
        for weight in ["uniform", "center"]
    ]
    for a in designs:
        a[:] = np.nan
    indices = np.flatnonzero(mask & np.isfinite(terrain))
    ncol = shape[1]

    def block(ids):
        rr, cc = ids // ncol, ids % ncol
        gx = transform.c + (cc + 0.5) * transform.a
        gy = transform.f + (rr + 0.5) * transform.e
        ground = np.stack([gx, gy, terrain[rr, cc]], axis=-1)
        vz, va, delta = camera_rays(ground, cam, grid_to_true_deg=gamma)
        good, central = footprint_candidates(delta, heading, fp)
        ii, jj = np.nonzero(good)
        sa = np.deg2rad(solar["solar_az"][rr, cc].astype(np.float32))
        # Same float32 ancillary conversion and scene zenith as the shared design builder.
        va32 = np.deg2rad(np.rad2deg(va[ii, jj]).astype(np.float32))
        vz32 = np.deg2rad(np.rad2deg(vz[ii, jj]).astype(np.float32))
        kv = np.full(good.shape, np.nan)
        kg = kv.copy()
        kv[ii, jj] = c.calc_volume_kernel(
            sa[ii], np.float32(scene), va32, vz32, "RossThick"
        )
        kg[ii, jj] = c.calc_geom_kernel(
            sa[ii], np.float32(scene), va32, vz32, "LiDenseR", b_r=10, h_b=2
        )
        fields = np.full((len(ids), len(FIELDS)), np.nan, np.float32)
        for prefix, rule, offset in [("A", "nearest", 0), ("B", "central", 3)]:
            assigned = assign_camera(delta, good, central, rule=rule)
            valid = assigned >= 0
            k = np.flatnonzero(valid)
            j = assigned[valid]
            fields[k, offset] = np.rad2deg(vz[k, j])
            fields[k, offset + 1] = np.rad2deg(va[k, j])
            fields[:, offset + 2] = assigned
        count = good.sum(1)
        covered = count > 0
        v = np.where(good, vz, np.nan)
        with __import__("warnings").catch_warnings():
            __import__("warnings").simplefilter("ignore", RuntimeWarning)
            fields[:, 6] = count
            fields[:, 7] = np.rad2deg(np.nanmin(v, axis=1))
            fields[:, 8] = np.rad2deg(np.nanmax(v, axis=1))
            fields[:, 9] = np.rad2deg(np.nanmedian(v, axis=1))
            for az, offset in [(va, 10), ((sa[:, None] - va) % (2 * np.pi), 12)]:
                co = np.sum(np.where(good, np.cos(az), 0), axis=1) / np.maximum(
                    count, 1
                )
                si = np.sum(np.where(good, np.sin(az), 0), axis=1) / np.maximum(
                    count, 1
                )
                fields[:, offset] = np.rad2deg(np.arctan2(si, co) % (2 * np.pi))
                fields[:, offset + 1] = np.hypot(co, si)
            uniform = aggregate_kernels(kv, kg, good)
            center = aggregate_kernels(kv, kg, good, centrality=central)
            fields[:, 14:16] = uniform[:, 1:]
            fields[:, 16] = np.nanstd(kv, axis=1)
            fields[:, 17] = np.nanstd(kg, axis=1)
            fields[:, 18:20] = center[:, 1:]
        fields[~covered, 7:] = np.nan
        return ids, fields, uniform, center

    start = time.monotonic()
    chunks = [indices[i : i + 1024] for i in range(0, len(indices), 1024)]
    print(
        "Native geometry",
        len(indices),
        "ground observations,",
        len(chunks),
        "bounded chunks",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for i, (ids, fields, uniform, center) in enumerate(pool.map(block, chunks)):
            out.reshape(-1, len(FIELDS))[ids] = fields
            designs[0].reshape(-1, 3)[ids] = uniform
            designs[1].reshape(-1, 3)[ids] = center
            if i % 200 == 0:
                print(
                    "geometry chunks",
                    i + 1,
                    "/",
                    len(chunks),
                    "elapsed_s",
                    round(time.monotonic() - start),
                    flush=True,
                )
    out.flush()
    for a in designs:
        a.flush()
    profile.update(
        count=len(FIELDS),
        dtype="float32",
        nodata=np.nan,
        compress="deflate",
        predictor=3,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )
    profile.pop("photometric", None)
    with rasterio.open(
        WORK / "goldhill_experimental_geometry.tif", "w", **profile
    ) as dst:
        for b, name in enumerate(FIELDS):
            dst.write(out[..., b], b + 1)
            dst.set_band_description(b + 1, name)
        dst.update_tags(
            STATUS="EXPERIMENTAL_CANDIDATE_GEOMETRY_NOT_VERIFIED_CONTRIBUTORS",
            CRS_INTERPRETATION="26913 supported by processing report and spatial tests; original CSV says5070",
            VERTICAL_DATUM="UNVERIFIED_SAME_DATUM_SCENARIO",
            ASSIGNMENT="A nearest rectangular-eligible; B minimum normalized edge distance; C simulated kernel mixtures",
            AZIMUTH="clockwise true north, ground-to-sensor",
            CALIBRATION="HYPOTHETICAL_UNVERIFIED",
        )
    write(
        "geometry_summary.json",
        dict(
            status="EXPERIMENTAL",
            native_grid=shape,
            fields=FIELDS,
            source_pixels=len(indices),
            covered_pixels=int(np.sum(out[..., 6] > 0)),
            scenario_A_B_different=int(np.sum(mask & (out[..., 2] != out[..., 5]))),
            native_map=str(WORK / "goldhill_experimental_geometry.tif"),
            kernel_designs=[
                str(WORK / f"C_{w}_design.npy") for w in ["uniform", "center"]
            ],
            elapsed_seconds=time.monotonic() - start,
            statistics={name: dist(out[..., i][mask]) for i, name in enumerate(FIELDS)},
            memory="1024 ground points x565cameras x3workers; persistent native maps outside repo; no reflectance duplication",
        ),
    )
    write(
        "native_artifacts.json",
        dict(
            script_sha256=sha(Path(__file__)),
            module_sha256=sha(ROOT / "src/spectralbridge/drone_view_geometry.py"),
            artifacts={
                str(path): sha(path)
                for path in [
                    WORK / "geometry_native.npy",
                    WORK / "C_uniform_design.npy",
                    WORK / "C_center_design.npy",
                    WORK / "goldhill_experimental_geometry.tif",
                ]
            },
        ),
    )
    print("COMPLETE", time.monotonic() - start, flush=True)


if __name__ == "__main__":
    main()
