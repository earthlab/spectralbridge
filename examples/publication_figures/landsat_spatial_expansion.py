"""Expand independent-photo Landsat reference discovery without altering prior cohorts.

Stages are file-based and restartable. Locator classes propose patches only;
neither the maps nor Landsat spectra certify the researcher-defined PFT labels.
Reviewers annotate the dated aerial contexts before any Landsat test is fitted.
"""

import argparse
import hashlib
import json
from pathlib import Path
from itertools import product

import geopandas as gpd
from shapely import Polygon, box
from shapely.affinity import translate

from landsat_photo_annotation import image_classes, fractions, draw_geometry

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from pyproj import Transformer
from rasterio.transform import xy
from scipy.ndimage import label as connected_components

import landsat_regional_candidates as regional
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = regional.OUTPUT
SEASONAL = PREVIOUS / "seasonal-archive"
OUTPUT = PREVIOUS / "round-2"
CACHE = ROOT / "archive/local/landsat-spatial-expansion"
CONTEXT_METERS = 240
IMAGE_PIXELS = 600
TARGETS = [
    "Deciduous",
    "Evergreen",
    "Herbaceous",
    "Woody shrub",
    "Non-vegetated & dead",
]
# These labels come from the GAP item's label:classes legend. Even a named forest
# system can be mixed and its map dates to 2011: every proposal needs photo review.
EVERGREEN_CODES = [137, 141, 146, 151, 152, 153, 158, 159, 167, 168, 169, 171, 172, 173]
SHRUB_CODES = [296, 297, 298, 301, 302, 303, 382, 488, 489, 490, 491, 492, 493, 495]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def locator_masks(world, gap):
    """Cross-map hypotheses; never expose a researcher label as established."""
    return {
        "Deciduous": (world == 10) & (gap == 148),
        "Evergreen": (world == 10) & np.isin(gap, EVERGREEN_CODES),
        "Herbaceous": world == 30,
        "Woody shrub": np.isin(world, [10, 20]) & np.isin(gap, SHRUB_CODES),
        "Non-vegetated & dead": world == 60,
    }


def snap_center(east, north, anchor):
    """Snap to the exact existing reference scene's 30 m lattice, not a new grid."""
    dx = int(np.rint((east - anchor.easting) / 30))
    dy = int(np.rint((north - anchor.northing) / 30))
    return dict(
        easting=float(anchor.easting + 30 * dx),
        northing=float(anchor.northing + 30 * dy),
        landsat_col=int(anchor.landsat_col + dx),
        landsat_row=int(anchor.landsat_row - dy),
        landsat_epsg=int(anchor.landsat_epsg),
    )


def gap_catalogue(region):
    path = OUTPUT / f"{region}-gap-catalogue.json"
    if path.exists():
        return json.loads(path.read_text())["features"]
    old = PREVIOUS / f"{region}-gap.json"
    if old.exists():
        saved = json.loads(old.read_text())
    else:
        saved = regional.fetch_catalogue(
            requests.Session(),
            dict(collections=["gap"], bbox=regional.REGIONS[region], limit=100),
        )
    write_json_atomic(path, saved)
    return saved["features"]


def discover(count):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "patch_proposals.csv"
    policy = dict(
        per_stratum=count,
        minimum_locator_interior_m=regional.MIN_MAP_INTERIOR_METERS,
        patch_spacing_m=1000,
        context_m=CONTEXT_METERS,
        pixels=IMAGE_PIXELS,
        regions=regional.REGIONS,
        evergreen_gap_codes=EVERGREEN_CODES,
        shrub_gap_codes=SHRUB_CODES,
        class_order=TARGETS,
        label_status="hypothesis_only",
        source_code_sha256=sha(__file__),
    )
    policy_path = OUTPUT / "discovery_policy.json"
    if path.exists():
        old = json.loads(policy_path.read_text())
        # Code edits outside discovery do not invalidate coordinates; parameters do.
        if {k: v for k, v in old.items() if k != "source_code_sha256"} != {
            k: v for k, v in policy.items() if k != "source_code_sha256"
        }:
            raise ValueError("Discovery settings changed; create a new expansion round")
        print("Reusing frozen patch proposals", flush=True)
        return
    references = pd.read_csv(PREVIOUS / "regional_candidate_dataset.csv")
    records = []
    for region in regional.REGIONS:
        world, transform = regional.map_grid(region)
        gap_items = gap_catalogue(region)
        gap, gap_transform = regional.map_grid(
            region, "gap", catalogue_features=gap_items
        )
        if gap_transform != transform or gap.shape != world.shape:
            raise ValueError("Locator grids differ")
        anchor = references.loc[references.region.eq(region)].iloc[0]
        inverse = Transformer.from_crs(int(anchor.landsat_epsg), 4326, always_xy=True)
        legend = gap_items[0]["properties"]["label:classes"][0]["classes"]
        for target, mask in locator_masks(world, gap).items():
            components, _ = connected_components(mask)
            for rank, (row, col, interior) in enumerate(
                regional.interior_centers(mask, count=count, spacing_m=1000), 1
            ):
                east, north = xy(transform, row, col)
                grid = snap_center(east, north, anchor)
                lon, lat = inverse.transform(grid["easting"], grid["northing"])
                key = f"r2-{region}-{target.lower().split()[0]}-{rank:03d}"
                code = int(gap[row, col])
                records.append(
                    dict(
                        context_patch_id=key,
                        region=region,
                        target_hypothesis=target,
                        locator_component_id=f"{region}-{target}-{int(components[row, col])}",
                        map_interior_m=interior,
                        worldcover_code=int(world[row, col]),
                        gap_code=code,
                        gap_label=legend[code] if code < len(legend) else "unknown",
                        reference_scene_id=anchor.scene_id,
                        scene_datetime=anchor.scene_datetime,
                        longitude=lon,
                        latitude=lat,
                        reference_review="pending",
                        pft_purity_verified=False,
                        **grid,
                    )
                )
            print(region, target, "cumulative proposals", len(records), flush=True)
    frame = pd.DataFrame(records)
    if frame.duplicated(["landsat_epsg", "easting", "northing"]).any():
        raise ValueError("Cross-stratum proposals duplicate a native footprint")
    write_text_atomic(path, frame.to_csv(index=False))
    write_json_atomic(policy_path, policy)
    print(frame.groupby(["region", "target_hypothesis"]).size().to_string(), flush=True)


def discover_live_oak(count=10):
    """A separate frozen stratum for evergreen broadleaf canopy, not mixed oaks.

    GAP 41 explicitly names Coastal Live Oak. Blue-oak and mixed oak/conifer
    systems are excluded because their leaf habit or composition is ambiguous.
    This is an additional locator hypothesis, never an independently verified label.
    """
    path = OUTPUT / "live_oak_patch_proposals.csv"
    if path.exists():
        print("Reusing frozen live-oak supplement", flush=True)
        return
    region = "california_shrublands"
    world, transform = regional.map_grid(region)
    gap, _ = regional.map_grid(region, "gap")
    reference = (
        pd.read_csv(PREVIOUS / "regional_candidate_dataset.csv")
        .query("region == @region")
        .iloc[0]
    )
    inverse = Transformer.from_crs(int(reference.landsat_epsg), 4326, always_xy=True)
    mask = (world == 10) & (gap == 41)
    components, _ = connected_components(mask)
    rows = []
    for rank, (row, col, distance) in enumerate(
        regional.interior_centers(mask, count=count), 1
    ):
        east, north = xy(transform, row, col)
        grid = snap_center(east, north, reference)
        lon, lat = inverse.transform(grid["easting"], grid["northing"])
        rows.append(
            dict(
                context_patch_id=f"r2-{region}-liveoak-{rank:03d}",
                region=region,
                target_hypothesis="Evergreen",
                locator_component_id=f"{region}-liveoak-{int(components[row, col])}",
                map_interior_m=distance,
                worldcover_code=10,
                gap_code=41,
                gap_label="California Coastal Live Oak Woodland and Savanna",
                reference_scene_id=reference.scene_id,
                scene_datetime=reference.scene_datetime,
                longitude=lon,
                latitude=lat,
                reference_review="pending",
                pft_purity_verified=False,
                **grid,
            )
        )
    write_text_atomic(path, pd.DataFrame(rows).to_csv(index=False))
    write_json_atomic(
        OUTPUT / "live_oak_discovery_policy.json",
        dict(
            gap_code=41,
            per_stratum=count,
            spacing_m=1000,
            minimum_locator_interior_m=60,
            purity_threshold_unchanged=0.95,
            label_status="hypothesis_only",
            code_sha256=sha(__file__),
        ),
    )
    print("Additional live-oak patch hypotheses", len(rows), flush=True)


def context(region, limit=None, supplement=False):
    proposal_name = (
        "live_oak_patch_proposals.csv" if supplement else "patch_proposals.csv"
    )
    output_tag = region + "-live-oak" if supplement else region
    frame = pd.read_csv(OUTPUT / proposal_name)
    frame = frame.loc[frame.region.eq(region)]
    if limit is not None:
        frame = frame.head(limit)
    aerial_path = SEASONAL / f"{region}-aerial-catalogue.json"
    aerials = json.loads(aerial_path.read_text())["features"]
    records = []
    for number, proposal in enumerate(frame.to_dict("records"), 1):
        key = proposal["context_patch_id"]
        record_path = CACHE / f"{key}.json"
        image_path = CACHE / f"{key}.npy"
        identity = hashlib.sha256(
            json.dumps(
                dict(
                    proposal=proposal,
                    context_m=CONTEXT_METERS,
                    pixels=IMAGE_PIXELS,
                    aerial_catalogue_sha256=sha(aerial_path),
                ),
                sort_keys=True,
            ).encode()
        ).hexdigest()
        saved = json.loads(record_path.read_text()) if record_path.exists() else {}
        if saved.get("identity") == identity and saved.get("status") in {
            "context_ready",
            "no_complete_context",
        }:
            if saved["status"] == "context_ready" and (
                not image_path.exists() or sha(image_path) != saved["image_sha256"]
            ):
                raise ValueError(f"Context checkpoint corrupt: {key}")
            records.append(saved)
            continue
        print(region, f"context {number}/{len(frame)}", key, flush=True)
        try:
            metadata, image = regional.aerial_chip(
                proposal, aerials, context_m=CONTEXT_METERS, pixels=IMAGE_PIXELS
            )
            saved = dict(
                **proposal, **metadata, identity=identity, status="no_complete_context"
            )
            if image is not None:
                temporary = image_path.with_suffix(".tmp")
                with temporary.open("wb") as handle:
                    np.save(handle, image.astype(np.uint8))
                temporary.replace(image_path)
                source = next(
                    item for item in aerials if item["id"] == metadata["naip_id"]
                )
                saved.update(
                    status="context_ready",
                    image_sha256=sha(image_path),
                    naip_gsd_m=source["properties"].get("gsd"),
                    context_m=CONTEXT_METERS,
                    display_resolution_m=CONTEXT_METERS / IMAGE_PIXELS,
                )
            write_json_atomic(record_path, saved)
        except Exception as error:
            # A failed tile is not marked completed; later reruns retry it.
            saved = dict(
                **proposal, identity=identity, status="error", error=str(error)
            )
            write_json_atomic(record_path, saved)
            print(key, "retryable error", str(error)[:180], flush=True)
        records.append(saved)
        write_text_atomic(
            OUTPUT / f"{output_tag}-contexts.csv",
            pd.DataFrame(records).to_csv(index=False),
        )
    write_text_atomic(
        OUTPUT / f"{output_tag}-contexts.csv", pd.DataFrame(records).to_csv(index=False)
    )
    sheets(region, supplement=supplement)


def sheets(region, supplement=False):
    """Keep image review blind to Landsat reflectance and classification results."""
    output_tag = region + "-live-oak" if supplement else region
    rows = pd.read_csv(OUTPUT / f"{output_tag}-contexts.csv")
    rows = rows.loc[rows.status.eq("context_ready")]
    for start in range(0, len(rows), 4):
        figure, axes = plt.subplots(2, 2, figsize=(12, 12))
        for ax in axes.flat:
            ax.axis("off")
        for ax, (_, record) in zip(axes.flat, rows.iloc[start : start + 4].iterrows()):
            image = np.load(CACHE / f"{record.context_patch_id}.npy")
            half = CONTEXT_METERS / 2
            ax.imshow(np.moveaxis(image, 0, -1), extent=(-half, half, -half, half))
            for edge in np.arange(-105, 106, 30):
                ax.axvline(edge, color="cyan", lw=0.4, alpha=0.7)
                ax.axhline(edge, color="cyan", lw=0.4, alpha=0.7)
            ax.set_xticks(np.arange(-90, 91, 30))
            ax.set_yticks(np.arange(-90, 91, 30))
            ax.axis("on")
            ax.tick_params(labelsize=7)
            ax.set_title(
                f"{record.context_patch_id}\nHypothesis: {record.target_hypothesis}; {str(record.naip_datetime)[:10]}\n{record.gap_label}",
                fontsize=8,
            )
        figure.suptitle(
            f"{region}: 240 m aerial contexts; cyan = native 30 m lattice\nLocator hypotheses are not accepted PFT labels. Review before spectral extraction.",
            fontsize=11,
        )
        figure.tight_layout(rect=(0, 0, 1, 0.95))
        figure.savefig(
            OUTPUT / f"{output_tag}-context-review-{start // 4 + 1:02d}.png", dpi=170
        )
        plt.close(figure)


def annotate():
    """Measure all full native cells against frozen, dated photo annotations.

    A 95% pass is conditional on one image interpretation, never a declaration of
    independently verified ground truth. Unreviewed patch area is unknown.
    """
    policy_path = OUTPUT / "reviewed_patch_policy.json"
    policy = json.loads(policy_path.read_text())
    results = []
    geometries = []
    footprints = []
    directory = OUTPUT / "annotated-contexts"
    directory.mkdir(exist_ok=True)
    domain = box(-120, -120, 120, 120)
    for index, case in enumerate(policy["cases"], 1):
        key = case["context_patch_id"]
        metadata = json.loads((CACHE / f"{key}.json").read_text())
        image_path = CACHE / f"{key}.npy"
        if (
            sha(CACHE / f"{key}.json") != case["context_metadata_sha256"]
            or sha(image_path) != case["image_sha256"]
            or int(metadata["naip_datetime"][:4]) != case["aerial_year"]
        ):
            raise ValueError(f"Reviewed image identity/date changed: {key}")
        print(f"Annotating {index}/{len(policy['cases'])}: {key}", flush=True)
        image = np.load(image_path)
        classes = image_classes(
            case,
            image,
            case["aerial_year"],
            boundary_uncertainty=policy["boundary_uncertainty_m"],
            domain=domain,
        )
        # Apply the same uncertainty width to the manually traced outer boundary.
        belt = (
            Polygon(case["patch"])
            .boundary.buffer(policy["boundary_uncertainty_m"])
            .intersection(domain)
            .difference(classes["other"])
        )
        classes["target"] = classes["target"].difference(belt)
        classes["uncertain"] = classes["uncertain"].union(belt)
        for cover, geometry in classes.items():
            geometries.append(
                dict(
                    context_patch_id=key,
                    region=metadata["region"],
                    target=case["target"],
                    aerial_year=case["aerial_year"],
                    cover=cover,
                    epsg=int(metadata["landsat_epsg"]),
                    geometry=translate(
                        geometry, xoff=metadata["easting"], yoff=metadata["northing"]
                    ),
                )
            )
        cells = []
        for x, y in product(policy["cell_center_offsets_m"], repeat=2):
            cell = box(x - 15, y - 15, x + 15, y + 15)
            scores = fractions(classes, cell)
            if not np.isclose(sum(scores.values()), 1, atol=1e-9):
                raise ValueError("Cover fractions must partition the whole cell")
            sensitivity = {}
            for shift in [3, 5]:
                sensitivity[f"shift_{shift}m_min_target_fraction"] = min(
                    fractions(classes, translate(cell, xoff=dx, yoff=dy))["target"]
                    for dx, dy in product((-shift, 0, shift), repeat=2)
                )
            east, north = metadata["easting"] + x, metadata["northing"] + y
            identity = f"epsg{metadata['landsat_epsg']}-e{east:.0f}-n{north:.0f}"
            rec = dict(
                candidate_id=identity,
                context_patch_id=key,
                region=metadata["region"],
                locator_component_id=metadata["locator_component_id"],
                researcher_category=case["target"],
                easting=east,
                northing=north,
                landsat_epsg=metadata["landsat_epsg"],
                landsat_row=metadata["landsat_row"] - y // 30,
                landsat_col=metadata["landsat_col"] + x // 30,
                reference_scene_id=metadata["reference_scene_id"],
                scene_datetime=metadata["scene_datetime"],
                aerial_id=metadata["naip_id"],
                aerial_datetime=metadata["naip_datetime"],
                aerial_year=case["aerial_year"],
                image_sha256=case["image_sha256"],
                target_lower_fraction=scores["target"],
                target_upper_fraction=scores["target"] + scores["uncertain"],
                other_fraction=scores["other"],
                unknown_fraction=scores["uncertain"],
                photo_screen_95pct=scores["target"] >= 0.95 - 1e-12,
                pft_purity_verified=False,
                reference_status="single_interpreter_photo_annotation",
                **sensitivity,
            )
            results.append(rec)
            cells.append((cell, rec))
            footprints.append(
                dict(
                    **rec,
                    geometry=translate(
                        cell, xoff=metadata["easting"], yoff=metadata["northing"]
                    ),
                )
            )
        figure, axes = plt.subplots(1, 2, figsize=(12, 6))
        for ax in axes:
            ax.imshow(np.moveaxis(image, 0, -1), extent=(-120, 120, -120, 120))
            ax.set_xlim(-120, 120)
            ax.set_ylim(-120, 120)
            ax.tick_params(labelsize=7)
        draw_geometry(axes[1], classes["uncertain"], "#ff9000", 0.42)
        draw_geometry(axes[1], classes["other"], "#d81b60", 0.5)
        for cell, rec in cells:
            for ax in axes:
                ax.plot(*cell.exterior.xy, color="cyan", lw=0.35, alpha=0.7)
            if rec["photo_screen_95pct"]:
                axes[1].plot(*cell.exterior.xy, color="#00ff00", lw=1)
        axes[0].set_title(
            f"{key}\n{case['target']} · {metadata['naip_datetime'][:10]}", fontsize=9
        )
        axes[1].set_title(
            "Orange = unknown; green = ≥95% mapped target\nSingle-interpreter screen; not independently verified",
            fontsize=9,
        )
        figure.tight_layout()
        figure.savefig(directory / f"{key}-annotation.png", dpi=170)
        plt.close(figure)
        write_text_atomic(
            OUTPUT / "dated_cell_cover_fractions.csv",
            pd.DataFrame(results).to_csv(index=False),
        )
    # Keep projected annotation geometry so area measurements can be audited.
    path = OUTPUT / "photo_reference_annotations.gpkg"
    temporary = path.with_name("photo_reference_annotations.tmp.gpkg")
    if temporary.exists():
        temporary.unlink()
    for epsg in sorted({row["epsg"] for row in geometries}):
        group = [row for row in geometries if row["epsg"] == epsg]
        gpd.GeoDataFrame(group, crs=epsg).to_file(
            temporary, layer=f"cover_epsg{epsg}", driver="GPKG"
        )
    temporary.replace(path)
    layer = []
    for epsg in sorted({row["landsat_epsg"] for row in footprints}):
        rows = [row for row in footprints if row["landsat_epsg"] == epsg]
        layer.append(gpd.GeoDataFrame(rows, crs=epsg).to_crs(4326))
    gpd.GeoDataFrame(pd.concat(layer, ignore_index=True), crs=4326).to_file(
        OUTPUT / "reviewed_native_cells.geojson", driver="GeoJSON"
    )
    write_json_atomic(
        OUTPUT / "annotation_manifest.json",
        dict(
            policy_sha256=sha(policy_path),
            fractions_sha256=sha(OUTPUT / "dated_cell_cover_fractions.csv"),
            geometry_sha256=sha(path),
            code_sha256=sha(__file__),
            annotation_helper_sha256=sha(
                Path(__file__).with_name("landsat_photo_annotation.py")
            ),
            interpreter=policy["interpreter"],
            independent_second_interpreter=False,
        ),
    )
    print(
        pd.DataFrame(results)
        .groupby("researcher_category")
        .photo_screen_95pct.agg(["size", "sum"])
        .to_string(),
        flush=True,
    )


def patch_groups(frame):
    """Merge overlapping reviewed contexts so their pixels cannot cross CV folds."""
    patches = frame.drop_duplicates("context_patch_id").sort_values("context_patch_id")
    keys = patches.context_patch_id.tolist()
    parent = {key: key for key in keys}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    rows = list(patches.itertuples())
    for i, a in enumerate(rows):
        for b in rows[i + 1 :]:
            if (
                a.landsat_epsg == b.landsat_epsg
                and abs(a.patch_easting - b.patch_easting) <= CONTEXT_METERS
                and abs(a.patch_northing - b.patch_northing) <= CONTEXT_METERS
            ):
                first, second = sorted(
                    [find(a.context_patch_id), find(b.context_patch_id)]
                )
                parent[second] = first
    return {key: find(key) for key in keys}


def reference_cohort(persist=True):
    """Deduplicate native cells and retain only the frozen primary photo screen."""
    manifest = json.loads((OUTPUT / "annotation_manifest.json").read_text())
    if manifest["policy_sha256"] != sha(
        OUTPUT / "reviewed_patch_policy.json"
    ) or manifest["fractions_sha256"] != sha(OUTPUT / "dated_cell_cover_fractions.csv"):
        raise ValueError(
            "Finish/rebuild the current annotation stage before extracting spectra"
        )
    frame = pd.read_csv(OUTPUT / "dated_cell_cover_fractions.csv")
    frame = frame.loc[frame.photo_screen_95pct].copy()
    proposal_sources = [OUTPUT / "patch_proposals.csv"]
    if (OUTPUT / "live_oak_patch_proposals.csv").exists():
        proposal_sources.append(OUTPUT / "live_oak_patch_proposals.csv")
    proposals = pd.concat(
        [pd.read_csv(path) for path in proposal_sources], ignore_index=True
    )[["context_patch_id", "easting", "northing"]].rename(
        columns={"easting": "patch_easting", "northing": "patch_northing"}
    )
    frame = frame.merge(
        proposals, on="context_patch_id", how="left", validate="many_to_one"
    )
    if frame[["patch_easting", "patch_northing"]].isna().any().any():
        raise ValueError("Annotated cells are missing their patch proposal metadata")
    conflicts = frame.groupby(
        ["candidate_id", "aerial_year"]
    ).researcher_category.nunique()
    bad = set(conflicts.index[conflicts.gt(1)])
    frame["conflicting_photo_labels"] = [
        (a, b) in bad
        for a, b in zip(frame.candidate_id, frame.aerial_year, strict=True)
    ]
    if persist:
        write_text_atomic(
            OUTPUT / "conflicting_reference_cells.csv",
            frame.loc[frame.conflicting_photo_labels].to_csv(index=False),
        )
    frame = (
        frame.loc[~frame.conflicting_photo_labels]
        .sort_values(
            [
                "target_lower_fraction",
                "shift_5m_min_target_fraction",
                "context_patch_id",
            ],
            ascending=[False, False, True],
            kind="stable",
        )
        .drop_duplicates(["candidate_id", "aerial_year"])
    )
    groups = patch_groups(frame)
    frame["patch_group_id"] = frame.context_patch_id.map(groups)
    previous = pd.read_csv(PREVIOUS / "regional_candidate_dataset.csv")
    previous["native_id"] = [
        f"epsg{int(row.landsat_epsg)}-e{row.easting:.0f}-n{row.northing:.0f}"
        for row in previous.itertuples()
    ]
    aliases = previous.groupby("native_id").candidate_id.agg(
        lambda names: ";".join(names)
    )
    frame["previous_candidate_ids"] = frame.candidate_id.map(aliases).fillna("")
    frame["independent_second_interpreter"] = False
    if persist:
        write_text_atomic(
            OUTPUT / "photo_screened_reference_cells.csv", frame.to_csv(index=False)
        )
    return frame


def extract(region):
    """Get same-year, same-season QA and B1-B7 only after independent photo review.

    Reuses the existing native-grid, cloud/saturation/context and aerosol checks.
    Quality and calendar date determine scene choice; no spectral response is used
    to choose reference labels or favorable class separation.
    """
    import landsat_seasonal_archive as seasonal

    seasonal.CACHE = CACHE / "landsat"
    seasonal.CACHE.mkdir(parents=True, exist_ok=True)
    frame = reference_cohort(persist=False)
    frame = frame.loc[frame.region.eq(region)].copy()
    if frame.empty:
        print(region, "no primary photo-screened reference cells", flush=True)
        return
    identity = hashlib.sha256(
        frame[["candidate_id", "aerial_year", "easting", "northing"]].to_json().encode()
    ).hexdigest()[:20]
    records = []
    all_audits = []
    for year, group in frame.groupby("aerial_year"):
        path = SEASONAL / f"{region}-{int(year)}-catalogue.json"
        scenes = json.loads(path.read_text())["features"]
        _, _, anchor = seasonal.season_window(group.scene_datetime.iloc[0], int(year))
        audits = []
        for index, item in enumerate(scenes, 1):
            print(
                region,
                year,
                f"QA scene {index}/{len(scenes)}",
                item["id"],
                f"cells={len(group)}",
                flush=True,
            )
            audits.append(seasonal.scene_qa(item, group, anchor, identity))
        if not audits:
            continue
        audit = pd.concat(audits, ignore_index=True)
        aerial = group.set_index("candidate_id").aerial_datetime
        photo_dates = pd.to_datetime(
            audit.candidate_id.map(aerial), utc=True, format="mixed"
        )
        dates = pd.to_datetime(audit.acquisition_datetime, utc=True, format="mixed")
        audit["aerial_gap_days"] = (
            dates.dt.normalize() - photo_dates.dt.normalize()
        ).dt.days.abs()
        audit["photo_date_match"] = dates.dt.year.eq(
            photo_dates.dt.year
        ) & audit.aerial_gap_days.le(45)
        all_audits.append(audit)
        eligible = audit.loc[audit.eligible_observation & audit.photo_date_match].copy()
        selected = seasonal.quality_order(eligible).drop_duplicates("candidate_id")
        items = {item["id"]: item for item in scenes}
        for scene_id, observations in selected.groupby("scene_id"):
            references = (
                group.set_index("candidate_id")
                .loc[observations.candidate_id]
                .reset_index()
            )
            band_identity = hashlib.sha256(
                references[["candidate_id", "easting", "northing"]].to_json().encode()
            ).hexdigest()[:20]
            print(
                region,
                year,
                "reading seven bands",
                scene_id,
                len(references),
                flush=True,
            )
            values = seasonal.reflectance(items[scene_id], references, band_identity)
            if not np.isfinite(values).all():
                raise ValueError("Nonfinite selected reflectance")
            merged = references.merge(
                observations,
                on="candidate_id",
                validate="one_to_one",
                suffixes=("_reference", ""),
            )
            for i, band in enumerate(seasonal.BANDS):
                merged[band] = values[:, i]
            records.extend(merged.to_dict("records"))
            write_text_atomic(
                OUTPUT / f"{region}-screened_landsat_observations.csv",
                pd.DataFrame(records).to_csv(index=False),
            )
    if all_audits:
        write_text_atomic(
            OUTPUT / f"{region}-landsat_qa_audit.csv",
            pd.concat(all_audits, ignore_index=True).to_csv(index=False),
        )
    if records:
        table = pd.DataFrame(records)
        write_text_atomic(
            OUTPUT / f"{region}-screened_landsat_observations.csv",
            table.to_csv(index=False),
        )
        print(
            table.groupby("researcher_category").candidate_id.nunique().to_string(),
            flush=True,
        )


def finalize():
    """Publish compact candidate data and technical validation-readiness counts.

    No accuracy claim is generated for missing classes or unvalidated references.
    Multiple pixels within one reviewed patch remain grouped observations.
    """
    references = reference_cohort()
    paths = sorted(OUTPUT.glob("*-screened_landsat_observations.csv"))
    frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    if frame.candidate_id.duplicated().any():
        raise ValueError("Repeated native cells cannot become independent observations")
    if set(frame.candidate_id) - set(references.candidate_id):
        raise ValueError(
            "Stored Landsat observations no longer match the current reference policy"
        )
    # An unchanged cell ID is insufficient: a new interpretation or image epoch
    # must invalidate the previously selected observation as well.
    current = references.set_index("candidate_id").loc[frame.candidate_id]
    for column in (
        "researcher_category",
        "image_sha256",
        "aerial_datetime",
        "patch_group_id",
    ):
        if not np.array_equal(
            frame[column].astype(str).to_numpy(), current[column].astype(str).to_numpy()
        ):
            raise ValueError(f"Stored Landsat reference metadata changed: {column}")
    for column in (
        "target_lower_fraction",
        "target_upper_fraction",
        "unknown_fraction",
    ):
        if not np.allclose(frame[column], current[column], rtol=0, atol=1e-12):
            raise ValueError(f"Stored Landsat reference cover changed: {column}")
    if not np.isfinite(frame[[f"B{i}" for i in range(1, 8)]]).all().all():
        raise ValueError("Selected spectra must have all seven finite bands")
    if not (
        frame.grid_match
        & frame.core_qa_clear
        & frame.context_150m_clear
        & frame.photo_date_match
        & frame.aerosol_level.lt(3)
    ).all():
        raise ValueError("Selected records fail their declared QA/date contract")
    if frame.pft_purity_verified.any() or frame.independent_second_interpreter.any():
        raise ValueError(
            "This single-interpreter cohort cannot claim independent verification"
        )
    write_text_atomic(
        OUTPUT / "expanded_photo_screened_landsat_dataset.csv",
        frame.to_csv(index=False),
    )
    write_text_atomic(
        OUTPUT / "preferred_aerosol_subset.csv",
        frame.loc[frame.preferred_aerosol].to_csv(index=False),
    )
    support = []
    for category in TARGETS:
        subset = frame.loc[frame.researcher_category.eq(category)]
        patch_count = subset.patch_group_id.nunique()
        support.append(
            dict(
                researcher_category=category,
                native_cells=subset.candidate_id.nunique(),
                patch_groups=patch_count,
                regions=subset.region.nunique(),
                acquisitions=subset.scene_id.nunique(),
                preferred_aerosol_cells=int(subset.preferred_aerosol.sum()),
                cells_retaining_95pct_at_5m_shift=int(
                    subset.shift_5m_min_target_fraction.ge(0.95 - 1e-12).sum()
                ),
                technical_three_fold_patch_support=patch_count >= 3,
                technical_leave_region_out_support=subset.region.nunique() >= 2,
                independently_validated_references=0,
                identifiability_test_status="not_run_pending_reference_validation"
                if len(subset)
                else "not_run_no_accepted_reference",
            )
        )
    write_text_atomic(
        OUTPUT / "identifiability_readiness.csv",
        pd.DataFrame(support).to_csv(index=False),
    )
    measurements = pd.read_csv(OUTPUT / "dated_cell_cover_fractions.csv")
    sensitivity = []
    for threshold in [0.9, 0.95, 1.0]:
        for shift, column in [
            (0, "target_lower_fraction"),
            (3, "shift_3m_min_target_fraction"),
            (5, "shift_5m_min_target_fraction"),
        ]:
            for category in TARGETS:
                selection = measurements.loc[
                    measurements.researcher_category.eq(category)
                    & measurements[column].ge(threshold - 1e-12)
                ]
                sensitivity.append(
                    dict(
                        threshold=threshold,
                        shift_m=shift,
                        researcher_category=category,
                        photo_only_unique_cells=selection.candidate_id.nunique(),
                        retained_primary_dataset_cells=frame.loc[
                            frame.researcher_category.eq(category)
                            & frame[column].ge(threshold - 1e-12)
                        ].candidate_id.nunique(),
                    )
                )
    write_text_atomic(
        OUTPUT / "purity_and_registration_sensitivity.csv",
        pd.DataFrame(sensitivity).to_csv(index=False),
    )
    # The final dataset remains directly mappable in common GIS tools.
    pieces = []
    for epsg, group in frame.groupby("landsat_epsg"):
        geometry = [
            box(
                row.easting - 15, row.northing - 15, row.easting + 15, row.northing + 15
            )
            for row in group.itertuples()
        ]
        pieces.append(
            gpd.GeoDataFrame(group, geometry=geometry, crs=int(epsg)).to_crs(4326)
        )
    gpd.GeoDataFrame(pd.concat(pieces, ignore_index=True), crs=4326).to_file(
        OUTPUT / "expanded_landsat_reference_footprints.geojson", driver="GeoJSON"
    )
    print(pd.DataFrame(support).to_string(index=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--discover-live-oak", action="store_true")
    parser.add_argument("--live-oak-context", action="store_true")
    parser.add_argument("--annotate", action="store_true")
    parser.add_argument("--extract", choices=list(regional.REGIONS))
    parser.add_argument("--per-stratum", type=int, default=10)
    parser.add_argument("--context", choices=list(regional.REGIONS))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sheets", choices=list(regional.REGIONS))
    args = parser.parse_args()
    if args.finalize:
        finalize()
    if args.discover_live_oak:
        discover_live_oak(args.per_stratum)
    if args.live_oak_context:
        context("california_shrublands", supplement=True)
    if args.extract:
        extract(args.extract)
    if args.annotate:
        annotate()
    if args.discover:
        discover(args.per_stratum)
    if args.context:
        context(args.context, args.limit)
    if args.sheets:
        sheets(args.sheets)
