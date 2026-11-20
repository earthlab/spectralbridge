"""Build a separately versioned HLS cohort from a frozen, cover-only review.

Run --freeze before downloading spectra. --extract REGION is restartable through
existing HLS QA/band checkpoints. --finalize combines completed additions with
the immutable 496-cell parent; no old spectrum or reference label is replaced.
Review coordinates are metres relative to each dated 240 m aerial context.
"""

import argparse
import json
import shutil
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import Polygon, box
from shapely.affinity import translate

import landsat_hls_reference_rebuild as builder
from landsat_hls_sampling_batch import ROOT, CACHE
from landsat_photo_annotation import image_classes
from landsat_spatial_expansion import sha
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

PARENT = builder.REFERENCES / "hls-l30-expanded-references"
REVIEW = ROOT / "review-batch-1"
ADDITIONS = REVIEW / "hls-additions"
COMBINED = REVIEW / "hls-combined"
REGIONS = ["cascades", "gunnison_aspen", "front_range"]


def rectangle(w=-110, s=-110, e=110, n=110):
    return [[w, s], [e, s], [e, n], [w, n]]


def review_specification():
    """Explicit photo interpretations; none uses reflectance or test performance."""
    cases = []
    for i in [1, 2, 3, 4, 5, 6, 8, 9, 10, 12]:
        bounds = {
            1: (-75, -110, 110, 110),
            2: (15, -110, 110, -15),
            10: (-105, -75, -15, 105),
        }.get(i, (-110, -110, 110, 110))
        holes = {
            5: [rectangle(25, -100, 110, 25)],
            6: [rectangle(-25, -30, 60, 60)],
            8: [rectangle(-110, -80, -35, -10)],
            9: [rectangle(-85, 35, -5, 110)],
        }.get(i, [])
        cases.append(
            dict(
                context_patch_id=f"power-gunnison_aspen-deciduous-{i:03}",
                target="Deciduous",
                patch=rectangle(*bounds),
                other_polygons=holes,
                dark_unknown_max_ceiling=65,
                bright_unknown_floor=185,
                interpretation="Golden broadleaf canopy; green mixed stands, dead crowns, meadow and deep shadow excluded by the frozen polygon/unknown mask. Provisional growth-form interpretation.",
            )
        )
    # Clearly exposed rock/talus; dark crevices remain unknown, never imputed rock.
    for region, indices in [
        ("gunnison_aspen", [2, 3, 6, 7, 8]),
        ("front_range", [1, 2, 3, 4, 5, 6, 8]),
    ]:
        for i in indices:
            bounds = (-110, -110, 110, 110)
            if region == "gunnison_aspen" and i == 2:
                bounds = (-110, -110, 0, 60)
            if region == "gunnison_aspen" and i == 3:
                bounds = (-110, -110, 110, 60)
            if region == "front_range" and i == 5:
                bounds = (-110, -25, 110, 110)
            if region == "front_range" and i == 6:
                bounds = (-110, -110, 110, -20)
            cases.append(
                dict(
                    context_patch_id=f"power-{region}-non-vegetated-{i:03}",
                    target="Non-vegetated & dead",
                    patch=rectangle(*bounds),
                    dark_unknown_ceiling=100,
                    interpretation="Exposed bedrock/talus; exclude deep shadows and, where present, snow through geometry. Lichen identity unresolved; provisional non-vegetated cover.",
                )
            )
    for i, bounds in [
        (1, (-10, -30, 60, 100)),
        (6, (-105, -45, 70, 65)),
        (8, (-35, -110, 110, -20)),
    ]:
        cases.append(
            dict(
                context_patch_id=f"power-front_range-herbaceous-{i:03}",
                target="Herbaceous",
                patch=rectangle(*bounds),
                dark_unknown_max_ceiling=50,
                bright_unknown_floor=180,
                interpretation="Continuous low grass/meadow texture within selected polygon; woody clumps, roads and structures outside. Pale rock/deep darkness unknown; managed cover allowed as in parent.",
            )
        )
    # Tall-canopy masks require BOTH a reviewed forest photo and the historical
    # no-fill first-return >5m area screen. This is not current validated truth.
    for i in [2, 3, 8, 11, 13, 15, 17, 18]:
        key = f"power-cascades-evergreen-{i:03}"
        paths = sorted((ROOT / "pointcloud-cascades").glob(f"{key}-*.npy"))
        if len(paths) != 1:
            raise ValueError(f"Expected one frozen lidar project for {key}")
        pathsaved = paths[0].with_suffix(".json")
        saved = json.loads(pathsaved.read_text())
        cases.append(
            dict(
                context_patch_id=key,
                target="Evergreen",
                structural_array=str(paths[0].relative_to(ROOT)),
                structural_sha256=sha(paths[0]),
                structural_metadata_sha256=sha(pathsaved),
                structural_project=saved["identity"]["project"],
                interpretation="Aerial forest crowns consistent with conifer canopy; old lidar constrains tall-cover occupancy. Shadowed growth form and acquisition-year stability remain provisional, not independently verified.",
            )
        )
    return cases


def freeze():
    REVIEW.mkdir(parents=True, exist_ok=True)
    cases = review_specification()
    for case in cases:
        key = case["context_patch_id"]
        meta = json.loads((CACHE / f"{key}.json").read_text())
        case.update(
            image_sha256=sha(CACHE / f"{key}.npy"),
            metadata_sha256=sha(CACHE / f"{key}.json"),
            aerial_year=int(meta["naip_datetime"][:4]),
        )
    policy = dict(
        cases=cases,
        date="2026-11-19",
        independently_verified=False,
        interpreter="single Codex aerial interpretation",
        boundary_uncertainty_m=0.6,
        nominal_cover_threshold=0.95,
        structural_threshold_m=5,
        selection="Frozen cover/photo/structure review before new HLS spectra; no selection by statistics",
        parent_manifest_sha256=sha(PARENT / "manifest.json"),
        parent_observations_sha256=sha(
            PARENT / "hls_l30_nominal_95pct_observations.csv"
        ),
        deferred="Other 116-batch contexts remain unaccepted pending review; no implicit labels.",
    )
    path = REVIEW / "frozen_review_policy.json"
    if path.exists() and json.loads(path.read_text()) != policy:
        raise ValueError("Frozen review changed; create another version")
    if not path.exists():
        write_json_atomic(path, policy)
    return policy


def additional_cases(write_geometry=False):
    policy = freeze()
    result, geometries = [], []
    domain = box(-120, -120, 120, 120)
    for case in policy["cases"]:
        key = case["context_patch_id"]
        meta = json.loads((CACHE / f"{key}.json").read_text())
        record = dict(
            key=key,
            meta=meta,
            target=case["target"],
            basis="dated_photo_cover",
            structural_project="",
        )
        if "structural_array" in case:
            path = ROOT / case["structural_array"]
            if (
                sha(path) != case["structural_sha256"]
                or sha(path.with_suffix(".json")) != case["structural_metadata_sha256"]
            ):
                raise ValueError("Changed frozen lidar evidence")
            record.update(
                grid=np.load(path),
                structural_project=case["structural_project"],
                basis="older_lidar_structure_and_provisional_evergreen_identity",
            )
        else:
            classes = image_classes(
                case,
                np.load(CACHE / f"{key}.npy"),
                case["aerial_year"],
                boundary_uncertainty=0.6,
                domain=domain,
            )
            belt = (
                Polygon(case["patch"])
                .boundary.buffer(0.6)
                .intersection(domain)
                .difference(classes["other"])
            )
            classes["target"] = classes["target"].difference(belt)
            classes["uncertain"] = classes["uncertain"].union(belt)
            record["photo"] = translate(
                classes["target"], xoff=meta["easting"], yoff=meta["northing"]
            )
            for cover, geom in classes.items():
                geometries.append(
                    dict(
                        context_patch_id=key,
                        target=case["target"],
                        cover=cover,
                        epsg=meta["landsat_epsg"],
                        geometry=translate(
                            geom, xoff=meta["easting"], yoff=meta["northing"]
                        ),
                    )
                )
        result.append(record)
    if geometries and write_geometry:
        frame = pd.DataFrame(geometries)
        for epsg, group in frame.groupby("epsg"):
            gpd.GeoDataFrame(
                group, geometry="geometry", crs=f"EPSG:{int(epsg)}"
            ).to_file(
                REVIEW / "reviewed_photo_cover.gpkg",
                layer=f"cover_epsg{int(epsg)}",
                driver="GPKG",
            )
    return result


def initialize():
    freeze()
    ADDITIONS.mkdir(exist_ok=True)
    # Public regional catalogues already cover the same fixed seasons and bounds.
    for path in PARENT.glob("*-catalogue.json"):
        destination = ADDITIONS / path.name
        if not destination.exists():
            shutil.copy2(path, destination)
    builder.OUTPUT = ADDITIONS
    builder.cases = additional_cases


def combine_tables(parent, additions, keys=None):
    """Append new rows only; duplicate physical identities fail rather than win."""
    frame = pd.concat([parent, additions], ignore_index=True)
    if keys and frame.duplicated(keys).any():
        raise ValueError("Repeated physical identity across parent and new batch")
    return frame


def finalize():
    policy = freeze()
    COMBINED.mkdir(exist_ok=True)
    for region in builder.regional.REGIONS:
        if (
            region in REGIONS
            and not (ADDITIONS / f"{region}-selected_observations.csv").exists()
        ):
            raise ValueError(f"Incomplete addition stage: {region}")
        for suffix in [
            "all_cover_measurements",
            "nominal_reference_cells",
            "hls_qa_audit",
            "selected_observations",
        ]:
            name = f"{region}-{suffix}.csv"
            parent = pd.read_csv(PARENT / name)
            path = ADDITIONS / name
            added = pd.read_csv(path) if path.exists() else parent.iloc[:0]
            keys = (
                ["candidate_id", "aerial_year"]
                if suffix in ["nominal_reference_cells", "selected_observations"]
                else None
            )
            frame = combine_tables(parent, added, keys)
            write_text_atomic(COMBINED / name, frame.to_csv(index=False))
    for directory in [PARENT, ADDITIONS]:
        for source in directory.glob("*-catalogue.json"):
            target = COMBINED / source.name
            if target.exists() and sha(target) != sha(source):
                raise ValueError("Regional catalogue identity changed")
            shutil.copy2(source, target)
    builder.OUTPUT = COMBINED
    builder.POLICY = builder.POLICY | dict(
        primary_support="nominal 30 m HLS footprint; full source area is sensitivity"
    )
    builder.finalize()
    write_json_atomic(
        COMBINED / "expansion_provenance.json",
        dict(
            review_policy_sha256=sha(REVIEW / "frozen_review_policy.json"),
            parent_manifest_sha256=policy["parent_manifest_sha256"],
            parent_observations_sha256=policy["parent_observations_sha256"],
            geometry_sha256=sha(REVIEW / "reviewed_photo_cover.gpkg"),
            wrapper_sha256=sha(Path(__file__)),
            parent_rows_preserved=True,
            independently_validated=False,
            selection_on_spectra=False,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--extract", choices=REGIONS)
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        print("Frozen review cases:", len(freeze()["cases"]))
        additional_cases(write_geometry=True)
    if args.extract:
        initialize()
        builder.extract(args.extract)
    if args.finalize:
        finalize()
