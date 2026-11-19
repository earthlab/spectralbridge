"""Rebuild dated Landsat references on the HLS L30 v2 grid.

Separate, restartable outputs preserve the original Collection 2 archive. Photo
cover is remeasured from frozen projected geometries; evergreen structure is
remeasured from saved 1 m first-return grids. Neither becomes validated truth.
A nominal 95% table and a conservative 4x4 source-support 95% subset are both
retained. The latter is the primary strict-support reference dataset.
"""

import argparse
import json
from itertools import product
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import mapping
from shapely.ops import transform
import requests
from affine import Affine
from rasterio.windows import Window
from shapely import box

import landsat_regional_candidates as regional
from landsat_spatial_expansion import (
    CACHE as PATCH_CACHE,
    OUTPUT as REFERENCES,
    sha,
    patch_groups,
)
from landsat_seasonal_archive import season_window
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

OUTPUT = REFERENCES / "hls-l30-rebuild"
CACHE = regional.ROOT / "archive/local/landsat-hls-l30-rebuild"
BANDS = [f"B{i:02d}" for i in range(1, 8)]
POLICY = dict(
    product="HLS L30 v2",
    collection="hls2-l30",
    nominal_cover_threshold=0.95,
    primary_support="conservative bounding area of 4x4 native Landsat source pixels",
    primary_support_threshold=0.95,
    source_support_weights="unweighted area; not signed cubic weights or a confidence bound",
    allowed_grid="same UTM EPSG as frozen reference; 30 m square north-up",
    seasonal_window_days=21,
    aerial_same_year=True,
    aerial_max_gap_days=45,
    fmask_rejected_bits=[0, 1, 2, 3, 4, 5],
    fmask_fill=255,
    high_aerosol_excluded=True,
    context_qa="5x5 HLS pixels (150 m), lower six bits clear, no fill",
    scale=0.0001,
    reflectance_fill=-9999,
    reference_labels="single-interpreter provisional; evergreen structural/date uncertainty retained",
)


def fmask_clear(values):
    """HLS v2 lower six flags; reject high AOT, preserve climatology flag."""
    q = np.asarray(values, dtype=np.uint8)
    aerosol = (q >> 6) & 3
    return (q != 255) & ((q & 63) == 0) & (aerosol < 3), aerosol


def scale_hls(values):
    values = np.asarray(values)
    return np.where(values == -9999, np.nan, values.astype(float) * 0.0001)


def source_kernel(x, y, anchor):
    """Full 4x4 support of cubic convolution on the frozen native source lattice.

    Valid for same-UTM, same-phase native Landsat scenes only. Unlike weighted
    fractions, this conservative area diagnostic never cancels negative weights.
    """
    left = float(anchor["easting"]) - 15
    top = float(anchor["northing"]) + 15
    col = int(np.floor((x - left) / 30 - 0.5))
    row = int(np.floor((top - y) / 30 - 0.5))
    return box(
        left + (col - 1) * 30,
        top - (row + 3) * 30,
        left + (col + 3) * 30,
        top - (row - 1) * 30,
    )


def structural_fraction(grid, geometry, anchor):
    """Exact 1 m bin area for axis-aligned, integral footprints; outside unknown."""
    left = anchor["easting"] - 120
    bottom = anchor["northing"] - 120
    west, south, east, north = geometry.bounds
    indices = np.array([west - left, south - bottom, east - left, north - bottom])
    if not np.allclose(indices, np.round(indices), atol=1e-6):
        raise ValueError("Structural bins and HLS footprint need exact area handling")
    x0, y0, x1, y1 = np.round(indices).astype(int)
    view = grid[max(0, y0) : min(240, y1), max(0, x0) : min(240, x1)]
    if x1 <= 0 or y1 <= 0 or x0 >= 240 or y0 >= 240:
        return 0.0, 0.0
    return float((view > 5).sum() / geometry.area), float(
        np.isfinite(view).sum() / geometry.area
    )


def photo_fraction(target, geometry):
    return float(target.intersection(geometry).area / geometry.area)


def catalogue(region, year, anchor):
    start, end, _ = season_window(anchor, int(year))
    payload = dict(
        collections=["hls2-l30"],
        bbox=regional.REGIONS[region],
        datetime=f"{start.isoformat()}/{end.isoformat()}",
        limit=100,
    )
    path = OUTPUT / f"{region}-{year}-catalogue.json"
    if path.exists():
        data = json.loads(path.read_text())
        if data.get("spectralbridge:query") == payload:
            return data["features"]
    print(region, year, "cataloguing HLS L30", flush=True)
    data = regional.fetch_catalogue(requests.Session(), payload)
    write_json_atomic(path, data)
    return data["features"]


def cases():
    policy_path = REFERENCES / "reviewed_patch_policy.json"
    manifest = json.loads((REFERENCES / "annotation_manifest.json").read_text())
    if (
        sha(policy_path) != manifest["policy_sha256"]
        or sha(REFERENCES / "photo_reference_annotations.gpkg")
        != manifest["geometry_sha256"]
    ):
        raise ValueError("Frozen annotation policy/geometries changed")
    policy = json.loads(policy_path.read_text())
    grouped = {}
    gpkg = REFERENCES / "photo_reference_annotations.gpkg"
    for layer in gpd.list_layers(gpkg).name:
        f = gpd.read_file(gpkg, layer=layer)
        for key, g in f.groupby("context_patch_id"):
            grouped[key] = g.loc[g.cover.eq("target")].geometry.iloc[0]
    result = []
    for case in policy["cases"]:
        key = case["context_patch_id"]
        meta = json.loads((PATCH_CACHE / f"{key}.json").read_text())
        if (
            sha(PATCH_CACHE / f"{key}.json") != case["context_metadata_sha256"]
            or sha(PATCH_CACHE / f"{key}.npy") != case["image_sha256"]
        ):
            raise ValueError("Frozen photo image/metadata changed")
        result.append(
            dict(
                key=key,
                meta=meta,
                target=case["target"],
                photo=grouped[key],
                basis="dated_photo_cover",
                structural_project="",
            )
        )
    structural = REFERENCES / "evergreen-pointcloud"
    selected = pd.read_csv(structural / "structurally_screened_candidate_cells.csv")
    for key, g in selected.groupby("context_patch_id"):
        projects = (
            g[["structural_project", "structural_end_datetime"]]
            .drop_duplicates()
            .sort_values(["structural_end_datetime", "structural_project"])
        )
        project = projects.iloc[-1].structural_project
        path = structural / f"{key}-{project}.npy"
        saved = json.loads(path.with_suffix(".json").read_text())
        if sha(path) != saved["array_sha256"]:
            raise ValueError("Structural source changed")
        meta = json.loads((PATCH_CACHE / f"{key}.json").read_text())
        result.append(
            dict(
                key=key,
                meta=meta,
                target="Evergreen",
                grid=np.load(path),
                basis="older_lidar_structure_and_provisional_evergreen_identity",
                structural_project=project,
            )
        )
    return result


def reference_cells(region):
    """Cover review precedes reflectance retrieval and never uses class separation."""
    records = []
    catalogues = {}
    for case in cases():
        m = case["meta"]
        if m["region"] != region:
            continue
        year = int(m["naip_datetime"][:4])
        key = (region, year)
        if key not in catalogues:
            catalogues[key] = catalogue(region, year, m["scene_datetime"])
        layouts = {}
        for item in catalogues[key]:
            props = item["properties"]
            if int(props.get("proj:epsg", 0)) != int(m["landsat_epsg"]):
                continue
            t = Affine(*props["proj:transform"][:6])
            if (t.a, t.b, t.d, t.e) != (30, 0, 0, -30):
                raise ValueError("Unexpected HLS lattice")
            layouts[(t.c % 30, t.f % 30)] = t
        if len(layouts) > 1:
            raise ValueError("HLS catalogue has inconsistent lattice phases")
        if not layouts:
            continue
        t = next(iter(layouts.values()))
        west, south, east, north = (
            m["easting"] - 120,
            m["northing"] - 120,
            m["easting"] + 120,
            m["northing"] + 120,
        )
        c0 = int(np.ceil((west - t.c) / 30))
        c1 = int(np.floor((east - t.c) / 30))
        r0 = int(np.ceil((t.f - north) / 30))
        r1 = int(np.floor((t.f - south) / 30))
        print(region, case["key"], "remeasuring HLS cover", flush=True)
        for row, col in product(range(r0, r1), range(c0, c1)):
            x, y = t * (col + 0.5, row + 0.5)
            cell = box(x - 15, y - 15, x + 15, y + 15)
            kernel = source_kernel(x, y, m)
            if "grid" in case:
                nominal, observed = structural_fraction(case["grid"], cell, m)
                support, kernel_observed = structural_fraction(case["grid"], kernel, m)
            else:
                nominal = photo_fraction(case["photo"], cell)
                support = photo_fraction(case["photo"], kernel)
                observed = kernel_observed = np.nan
            records.append(
                dict(
                    candidate_id=f"hls-epsg{m['landsat_epsg']}-e{x:.0f}-n{y:.0f}",
                    context_patch_id=case["key"],
                    region=region,
                    researcher_category=case["target"],
                    reference_basis=case["basis"],
                    aerial_year=year,
                    aerial_datetime=m["naip_datetime"],
                    aerial_id=m["naip_id"],
                    image_sha256=m["image_sha256"],
                    scene_datetime=m["scene_datetime"],
                    easting=x,
                    northing=y,
                    landsat_epsg=m["landsat_epsg"],
                    nominal_target_fraction=nominal,
                    source_kernel_target_fraction=support,
                    structural_observed_fraction=observed,
                    structural_kernel_observed_fraction=kernel_observed,
                    nominal_95pct=nominal >= 0.95 - 1e-12,
                    strict_support_95pct=support >= 0.95 - 1e-12,
                    structural_project=case["structural_project"],
                    pft_purity_verified=False,
                    independent_second_interpreter=False,
                    patch_easting=m["easting"],
                    patch_northing=m["northing"],
                )
            )
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError(f"No HLS reference layouts for {region}")
    write_text_atomic(
        OUTPUT / f"{region}-all_cover_measurements.csv", frame.to_csv(index=False)
    )
    accepted = frame.loc[frame.nominal_95pct].copy()
    conflicts = accepted.groupby(
        ["candidate_id", "aerial_year"]
    ).researcher_category.nunique()
    bad = set(conflicts[conflicts > 1].index)
    accepted = accepted.loc[
        [(x.candidate_id, x.aerial_year) not in bad for x in accepted.itertuples()]
    ]
    accepted = accepted.sort_values(
        [
            "source_kernel_target_fraction",
            "nominal_target_fraction",
            "context_patch_id",
        ],
        ascending=[False, False, True],
    ).drop_duplicates(["candidate_id", "aerial_year"])
    # Reuse the pre-existing transitive 240 m context grouping.
    accepted["patch_group_id"] = accepted.context_patch_id.map(patch_groups(accepted))
    write_text_atomic(
        OUTPUT / f"{region}-nominal_reference_cells.csv", accepted.to_csv(index=False)
    )
    return accepted, catalogues


def audit_item(item, refs, identity):
    path = CACHE / f"{item['id']}-{identity}-qa.json"
    if path.exists():
        return pd.DataFrame(json.loads(path.read_text())["records"])
    records = []
    with regional.open_asset(item, "Fmask") as src:
        if src.nodata != 255 or src.res != (30, 30):
            raise ValueError("Unexpected HLS QA contract")
        for x in refs.itertuples():
            if src.crs.to_epsg() != int(x.landsat_epsg):
                continue
            row, col = src.index(x.easting, x.northing)
            center = src.xy(row, col)
            if not np.allclose(center, [x.easting, x.northing], rtol=0, atol=1e-6):
                raise ValueError("HLS cell is not on actual raster grid")
            inside = 2 <= row < src.height - 2 and 2 <= col < src.width - 2
            q = 255
            context = False
            if inside:
                window = src.read(1, window=Window(col - 2, row - 2, 5, 5))
                q = int(window[2, 2])
                context = bool(((window != 255) & ((window & 63) == 0)).all())
            clear, aerosol = fmask_clear(q)
            date = pd.Timestamp(item["properties"]["datetime"])
            photo = pd.Timestamp(x.aerial_datetime)
            _, _, anchor = season_window(x.scene_datetime, int(x.aerial_year))
            gap = abs((date.normalize() - photo.normalize()).days)
            match = date.year == photo.year and gap <= 45
            records.append(
                dict(
                    candidate_id=x.candidate_id,
                    aerial_year=int(x.aerial_year),
                    hls_item_id=item["id"],
                    platform=item["properties"]["platform"],
                    acquisition_datetime=date.isoformat(),
                    year=date.year,
                    season_offset_days=abs(
                        (date.normalize() - anchor.normalize()).days
                    ),
                    aerial_gap_days=gap,
                    photo_date_match=match,
                    hls_row=row,
                    hls_col=col,
                    grid_match=True,
                    fmask=q,
                    aerosol_level=int(aerosol),
                    aerosol_climatology=int(aerosol) == 0,
                    core_qa_clear=bool(clear),
                    context_150m_clear=context,
                    eligible_observation=bool(clear and context and match),
                )
            )
    frame = pd.DataFrame(records)
    write_json_atomic(path, dict(records=records))
    return frame


def extract(region):
    refs, catalogues = reference_cells(region)
    if refs.empty:
        print(region, "no nominal purity passes", flush=True)
        write_text_atomic(
            OUTPUT / f"{region}-selected_observations.csv",
            pd.DataFrame(columns=list(refs.columns) + ["all_bands_finite"]).to_csv(
                index=False
            ),
        )
        return
    identity = (
        sha(OUTPUT / f"{region}-nominal_reference_cells.csv")[:10]
        + sha(Path(__file__))[:10]
    )
    audits = []
    items = {}
    for (_, year), entries in catalogues.items():
        group = refs.loc[refs.aerial_year.eq(year)]
        for i, item in enumerate(entries, 1):
            if group.empty:
                continue
            if int(item["properties"].get("proj:epsg", 0)) != int(
                group.landsat_epsg.iloc[0]
            ):
                continue
            items[item["id"]] = item
            print(
                region,
                f"QA {i}/{len(entries)}",
                item["id"],
                len(group),
                "cells",
                flush=True,
            )
            audits.append(audit_item(item, group, identity))
    audit = pd.concat(audits, ignore_index=True)
    write_text_atomic(OUTPUT / f"{region}-hls_qa_audit.csv", audit.to_csv(index=False))
    eligible = audit.loc[audit.eligible_observation]
    chosen = eligible.sort_values(
        ["aerosol_climatology", "season_offset_days", "aerial_gap_days", "hls_item_id"]
    ).drop_duplicates(["candidate_id", "aerial_year"])
    records = []
    for item_id, group in chosen.groupby("hls_item_id"):
        item = items[item_id]
        source = (
            refs.set_index(["candidate_id", "aerial_year"])
            .loc[list(zip(group.candidate_id, group.aerial_year))]
            .reset_index()
        )
        band_path = CACHE / f"{item_id}-{identity}-bands.json"
        if band_path.exists():
            saved = json.loads(band_path.read_text())
            if saved["candidate_ids"] != source.candidate_id.tolist():
                raise ValueError("Stale HLS band identities")
            values = np.asarray(saved["values"], dtype=float)
        else:
            coords = list(zip(source.easting, source.northing))
            columns = []
            print(region, item_id, "reading B01-B07", len(source), "cells", flush=True)
            for band in BANDS:
                with regional.open_asset(item, band) as src:
                    expected = Affine(*item["properties"]["proj:transform"][:6])
                    if (
                        src.crs.to_epsg() != int(source.landsat_epsg.iloc[0])
                        or src.transform != expected
                        or src.nodata != -9999
                    ):
                        raise ValueError("HLS band and QA grids/fill differ")
                    columns.append(scale_hls([x[0] for x in src.sample(coords)]))
            values = np.asarray(columns).T
            write_json_atomic(
                band_path,
                dict(
                    candidate_ids=source.candidate_id.tolist(), values=values.tolist()
                ),
            )
        merged = source.merge(
            group, on=["candidate_id", "aerial_year"], validate="one_to_one"
        )
        for i, band in enumerate(BANDS):
            merged[f"B{i + 1}"] = values[:, i]
        merged["all_bands_finite"] = np.isfinite(values).all(axis=1)
        merged["product"] = "HLS L30 v2 NBAR"
        merged["brdf_normalized"] = True
        merged["hls_collection"] = "hls2-l30"
        merged["hls_doi"] = "10.5067/HLS/HLSL30.002"
        records.extend(merged.to_dict("records"))
        write_text_atomic(
            OUTPUT / f"{region}-selected_observations.csv",
            pd.DataFrame(records).to_csv(index=False),
        )
    if not records:
        write_text_atomic(
            OUTPUT / f"{region}-selected_observations.csv",
            pd.DataFrame(columns=list(refs.columns) + ["all_bands_finite"]).to_csv(
                index=False
            ),
        )


def finalize():
    paths = sorted(OUTPUT.glob("*-selected_observations.csv"))
    if len(paths) != len(regional.REGIONS):
        raise ValueError("All five regional stages must complete before finalization")
    frame = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    if frame.empty:
        raise ValueError(
            "No eligible HLS observations; inspect regional support and QA"
        )
    if frame.duplicated(["candidate_id", "aerial_year"]).any():
        raise ValueError("Repeated HLS footprints/year")
    frame = frame.loc[frame.all_bands_finite].copy()
    if not np.isfinite(frame[[f"B{i}" for i in range(1, 8)]]).all().all():
        raise ValueError("Nonfinite HLS SR")
    if not (
        frame.nominal_95pct
        & frame.core_qa_clear
        & frame.context_150m_clear
        & frame.photo_date_match
        & frame.aerosol_level.lt(3)
        & frame.grid_match
    ).all():
        raise ValueError(
            "Selected HLS observations fail their declared reference/QA contract"
        )
    if frame.pft_purity_verified.any():
        raise ValueError("HLS transformation cannot validate provisional labels")
    frame["nominal_area_m2"] = 900
    frame["source_kernel_area_m2"] = 14400
    frame["saturation_qa_status"] = "not_exposed_in_HLS_Fmask"
    audits = pd.concat(
        [pd.read_csv(p) for p in OUTPUT.glob("*-hls_qa_audit.csv")], ignore_index=True
    )
    checked = frame.merge(
        audits,
        on=["candidate_id", "aerial_year", "hls_item_id"],
        suffixes=("", "_audit"),
        validate="one_to_one",
    )
    if len(checked) != len(frame) or not checked.eligible_observation_audit.all():
        raise ValueError("Selected records do not match their saved QA audits")
    for field in ["fmask", "hls_row", "hls_col", "aerial_gap_days"]:
        if not checked[field].eq(checked[field + "_audit"]).all():
            raise ValueError(f"Selected QA field differs from audit: {field}")
    strict = frame.loc[frame.strict_support_95pct].copy()
    footprints = []
    kernels = []
    for cell in frame.itertuples():
        projection = Transformer.from_crs(int(cell.landsat_epsg), 4326, always_xy=True)
        props = {
            key: getattr(cell, key)
            for key in (
                "candidate_id",
                "context_patch_id",
                "patch_group_id",
                "researcher_category",
                "hls_item_id",
                "nominal_target_fraction",
                "source_kernel_target_fraction",
                "strict_support_95pct",
                "pft_purity_verified",
                "reference_basis",
            )
        }
        nominal = box(
            cell.easting - 15, cell.northing - 15, cell.easting + 15, cell.northing + 15
        )
        kernel = source_kernel(
            cell.easting,
            cell.northing,
            dict(easting=cell.patch_easting, northing=cell.patch_northing),
        )
        footprints.append(
            dict(
                type="Feature",
                properties=props,
                geometry=mapping(transform(projection.transform, nominal)),
            )
        )
        kernels.append(
            dict(
                type="Feature",
                properties=props,
                geometry=mapping(transform(projection.transform, kernel)),
            )
        )
    write_json_atomic(
        OUTPUT / "hls_native_footprints.geojson",
        dict(type="FeatureCollection", features=footprints),
    )
    write_json_atomic(
        OUTPUT / "hls_source_kernel_support.geojson",
        dict(type="FeatureCollection", features=kernels),
    )
    write_text_atomic(
        OUTPUT / "hls_l30_nominal_95pct_observations.csv", frame.to_csv(index=False)
    )
    write_text_atomic(
        OUTPUT / "hls_l30_strict_source_support_95pct_observations.csv",
        strict.to_csv(index=False),
    )
    support = []
    for name, table in [
        ("nominal_95pct", frame),
        ("strict_source_support_95pct", strict),
    ]:
        for category in regional_category_order():
            g = table.loc[table.researcher_category.eq(category)]
            support.append(
                dict(
                    cohort=name,
                    researcher_category=category,
                    cells=len(g),
                    patch_groups=g.patch_group_id.nunique(),
                    regions=g.region.nunique(),
                    acquisitions=g.hls_item_id.nunique(),
                    independently_validated_references=0,
                )
            )
    write_text_atomic(
        OUTPUT / "reference_support.csv", pd.DataFrame(support).to_csv(index=False)
    )
    write_json_atomic(
        OUTPUT / "manifest.json",
        dict(
            policy=POLICY,
            code_sha256=sha(Path(__file__)),
            annotation_geometry_sha256=sha(
                REFERENCES / "photo_reference_annotations.gpkg"
            ),
            outputs={p.name: sha(p) for p in sorted(OUTPUT.glob("*.csv"))},
            policy_sha256=sha(REFERENCES / "reviewed_patch_policy.json"),
            structural_inputs_sha256={
                p.name: sha(p)
                for p in sorted((REFERENCES / "evergreen-pointcloud").glob("*.npy"))
            },
            catalogue_sha256={
                p.name: sha(p) for p in sorted(OUTPUT.glob("*-catalogue.json"))
            },
            original_c2_products_preserved=True,
            figure_updated=False,
        ),
    )
    print(pd.DataFrame(support).to_string(index=False), flush=True)


def regional_category_order():
    return [
        "Deciduous",
        "Evergreen",
        "Herbaceous",
        "Woody shrub",
        "Non-vegetated & dead",
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", choices=list(regional.REGIONS))
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    policy_path = OUTPUT / "rebuild_policy.json"
    if policy_path.exists():
        if json.loads(policy_path.read_text()) != POLICY:
            raise ValueError("Rebuild policy changed; use a new output stage")
    else:
        write_json_atomic(policy_path, POLICY)
    if args.region:
        extract(args.region)
    if args.finalize:
        finalize()
