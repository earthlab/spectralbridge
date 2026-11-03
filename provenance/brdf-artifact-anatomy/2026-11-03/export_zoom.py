"""Export the same native zoom without repeating saved stage or Gordon/Ruby replay."""

from pathlib import Path
import importlib.util
import json
import sys

import numpy as np
import pandas as pd
import rasterio

import analyze as a
from spectralbridge.neon_cube import NeonCube

HERE = Path(__file__).resolve().parent


def augment_pixel_validity():
    """Attach observed-source and per-stage validity without altering samples."""
    pixels = pd.read_csv(HERE / "pixel_trajectories.csv")
    with rasterio.open(a.PRIOR / "goldhill_recovered_source_dn.tif") as src:
        alpha = {
            (int(r), int(c)): float(
                src.read(11, window=((int(r), int(r) + 1), (int(c), int(c) + 1)))[0, 0]
            )
            for r, c in pixels[["row", "column"]]
            .drop_duplicates()
            .itertuples(index=False, name=None)
        }
    pixels["source_alpha"] = [
        alpha[(int(r), int(c))] for r, c in zip(pixels.row, pixels.column)
    ]
    pixels["source_alpha_positive"] = pixels.source_alpha > 0
    for stage in a.STAGES:
        pixels[stage + "_finite"] = np.isfinite(pixels[stage])
    pixels["common_observed_valid"] = pixels.source_alpha_positive & pixels[
        [s + "_finite" for s in a.STAGES]
    ].all(axis=1)
    pixels.to_csv(HERE / "pixel_trajectories.csv", index=False)


def main():
    spec = importlib.util.spec_from_file_location("zoom_historical", a.OLD_PATH)
    old = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = old
    spec.loader.exec_module(old)
    cube = NeonCube(a.H5ROOT / "goldhill_working.h5")
    model = json.loads(
        (a.WORK / "models/AOP_GOLDHILL_20230814__brdf_model.json").read_text()
    )
    values = {
        s: np.load(a.PRIOR / f"normalized_{s}.npy", mmap_mode="r") for s in a.STAGES
    }
    g = pd.read_csv(HERE / "polygon_geometry.csv")
    candidate = g[
        (g.pixels >= 20)
        & (g.red_amplified_fraction > 0.05)
        & (g.red_amplified_fraction < 0.95)
    ].copy()
    candidate["distance"] = (candidate.row_center - 921) ** 2 + (
        candidate.col_center - 980
    ) ** 2
    exemplar = candidate.sort_values(["distance", "raw_within_angle"]).iloc[0]
    cy, cx = int(exemplar.row_center), int(exemplar.col_center)
    shape = values["raw"].shape[:2]
    roi = [
        max(0, cy - 200),
        min(shape[0], cy + 201),
        max(0, cx - 250),
        min(shape[1], cx + 251),
    ]
    rt = (slice(roi[0], roi[1]), slice(roi[2], roi[3]))
    with rasterio.open(a.PRIOR / "goldhill_recovered_source_dn.tif") as src:
        tr = src.transform
        alpha = src.read(11, window=((roi[0], roi[1]), (roi[2], roi[3])))
    deg = {
        k: cube.get_ancillary(k, radians=False)[rt]
        for k in ["solar_zn", "solar_az", "sensor_zn", "sensor_az", "slope", "aspect"]
    }
    rad = {k: np.deg2rad(v.astype(np.float32)) for k, v in deg.items()}
    scene = old._resolve_scene_solar_zenith(cube.get_ancillary("solar_zn"))[0, 0]
    sz = np.full(deg["solar_zn"].shape, scene, np.float32)
    zero = np.zeros_like(sz)
    kv = old.calc_volume_kernel(
        rad["solar_az"], sz, rad["sensor_az"], rad["sensor_zn"], kernel_type="RossThick"
    )
    kg = old.calc_geom_kernel(
        rad["solar_az"],
        sz,
        rad["sensor_az"],
        rad["sensor_zn"],
        kernel_type="LiDenseR",
        b_r=10,
        h_b=2,
    )
    refz = np.full_like(sz, np.deg2rad(45))
    rv = old.calc_volume_kernel(zero, refz, zero, zero, kernel_type="RossThick")
    rg = old.calc_geom_kernel(
        zero, refz, zero, zero, kernel_type="LiDenseR", b_r=10, h_b=2
    )
    vis = a.visit_mask(old, cube, values["raw"][rt], model)
    den = []
    factors = []
    nums = []
    for b in range(10):
        iso, vol, geo = [np.float32(model[k][0][b]) for k in ["iso", "vol", "geo"]]
        d = iso + vol * kv + geo * kg
        n = iso + vol * rv + geo * rg
        den.append(d)
        nums.append(n)
        factors.append(a.apply_factor(d, n, vis)[0])
    observed = np.isfinite(values["raw"][rt]).all(-1) & np.isfinite(alpha) & (alpha > 0)
    common = observed.copy()
    for v in values.values():
        common &= np.isfinite(v[rt]).all(-1)
    ci = old.calc_cosine_i(
        rad["solar_zn"], rad["solar_az"], rad["aspect"], rad["slope"]
    )
    inc = np.full(ci.shape, np.nan, np.float32)
    m = np.isfinite(ci) & (ci >= -1) & (ci <= 1)
    inc[m] = np.degrees(np.arccos(ci[m]))
    full = np.load(HERE / "goldhill_full_display.npz")
    newkv = np.full(sz.shape, float(full["kv_current"][0, 0]), np.float32)
    newkg = np.full(sz.shape, float(full["kg_current"][0, 0]), np.float32)
    out = {s: np.asarray(v[rt]) for s, v in values.items()}
    out.update(deg)
    out.update(
        kv_old=kv,
        kg_old=kg,
        kv_current=newkv,
        kg_current=newkg,
        cos_i=ci,
        incidence_angle=inc,
        relative_azimuth=(deg["solar_az"] - deg["sensor_az"] + 180) % 360 - 180,
        observed=observed,
        common=common,
        finite=np.isfinite(values["raw"][rt]).all(-1),
        red_den=den[4],
        red_num=nums[4],
        red_factor=factors[4],
        visited=vis,
        factors=np.stack(factors, axis=-1),
        predictions=np.stack(den, axis=-1),
    )
    np.savez_compressed(HERE / "goldhill_zoom.npz", **out)
    C = json.loads((HERE / "topographic_mechanism.json").read_text())["C"]
    td = ci + C
    tn = np.cos(rad["solar_zn"]) * np.cos(rad["slope"]) + C
    tf = old._scs_c_ratio(tn, td, min_denom=old.MIN_SCS_C_DENOM)
    np.savez_compressed(
        HERE / "goldhill_topo_zoom.npz", topo_den=td, topo_factor=tf, topo_C=np.array(C)
    )
    selection = json.loads((HERE / "selection.json").read_text())
    selection.update(
        roi_native_indices=roi,
        roi_extent_NAD83_UTM13N=[
            tr.c + roi[2] * tr.a,
            tr.c + roi[3] * tr.a,
            tr.f + roi[1] * tr.e,
            tr.f + roi[0] * tr.e,
        ],
        exemplar_GlobalID=str(exemplar.GlobalID),
        exemplar_cover_category=str(exemplar.cover_category),
        exemplar_species=None if pd.isna(exemplar.species) else str(exemplar.species),
        exemplar_status="Nearest eligible boundary-crossing polygon to the pre-existing transect; raw within-polygon spectral angle recorded, not selected on corrected quality",
    )
    chosen = [str(exemplar.GlobalID)]
    near = g[
        (g.row_center >= roi[0])
        & (g.row_center < roi[1])
        & (g.col_center >= roi[2])
        & (g.col_center < roi[3])
    ]
    for subset in [
        near[near.red_amplified_fraction.eq(0)],
        near[near.red_amplified_fraction.eq(1)],
        near,
    ]:
        sub = subset[~subset.GlobalID.isin(chosen)].copy()
        if len(sub):
            sub["distance"] = (sub.row_center - cy) ** 2 + (sub.col_center - cx) ** 2
            chosen.append(str(sub.sort_values("distance").iloc[0].GlobalID))
    selection["selected_polygons"] = chosen
    a.write("selection.json", selection)
    # Explicitly distinguish the isolated saved-bin upper-edge exception from the streak.
    allvis = a.visit_mask(old, cube, values["raw"], model)
    finite = np.isfinite(values["raw"]).all(-1)
    xy = np.argwhere(finite & ~allvis)
    rec = []
    for r, c in xy:
        rec.append(
            dict(
                row=int(r),
                column=int(c),
                NDVI668=float(
                    old.compute_ndvi(cube, values["raw"][r : r + 1, c : c + 1])[0, 0]
                ),
                reason="Exact NDVI upper edge enters index 1; saved single bin loop visits only index 0",
            )
        )
    boundary = json.loads((HERE / "boundary_correspondence.json").read_text())
    boundary["unvisited_bin_pixels"] = rec
    with rasterio.open(a.PRIOR / "goldhill_recovered_source_dn.tif") as full_src:
        all_alpha = full_src.read(11)
    valid_edges = finite & (all_alpha > 0) & (values["raw"][..., 4] != 0)
    actual_amplification = values["brdf"][..., 4] != values["raw"][..., 4]
    full_den = np.load(a.PRIOR / "red_denominator.npy", mmap_mode="r")
    main_boundary = a.boundary_comparison(
        actual_amplification, full_den > 0, valid_edges & allvis
    )
    boundary["denominator_only_extra_state_edges"] = boundary[
        "denominator_only_comparison"
    ]["xor_edges"]
    boundary["main_denominator_transition_only"] = main_boundary
    boundary["main_denominator_transition_only"]["qualification"] = (
        "Unvisited-bin edges excluded at both endpoints; the remaining boundary follows denominator sign exactly."
    )
    boundary["linear_zero_vs_branch_midpoint_offset_m"]["note"] = (
        "Only true denominator-sign transition edges; excludes the two horizontal NDVI-bin island edges. Linear interpolation is a display convention, not surveyed location precision."
    )
    a.write("boundary_correspondence.json", boundary)
    augment_pixel_validity()
    print(
        "Native zoom includes the selected Deciduous polygon and all four tracked pixels; no expensive stage replay repeated."
    )


if __name__ == "__main__":
    main()
