"""Extend HLS references by cover-only review, preserving previous stages.

Nominal 30 m >=95% mapped cover is the working definition. The full 4x4 source
area remains a separate sensitivity. Cases are frozen before spectrum retrieval.
"""

import argparse
import json
import shutil
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from shapely import Polygon, box
from shapely.affinity import translate

import landsat_hls_reference_rebuild as builder
from landsat_photo_annotation import image_classes, draw_geometry
from landsat_spatial_expansion import CACHE as PHOTO_CACHE, OUTPUT as REFERENCES, sha
from spectralbridge.bulk.provenance import write_json_atomic

PARENT = REFERENCES / "hls-l30-rebuild"
OUTPUT = REFERENCES / "hls-l30-expanded-references"
ORIGINAL_CASES = builder.cases


def freeze_review():
    OUTPUT.mkdir(exist_ok=True)
    proposals = []
    for suffix in ["001", "002", "003", "010"]:
        key = f"r2-california_shrublands-woody-{suffix}"
        bounds = (-105, -105, 15, 45) if suffix == "003" else (-110, -110, 110, 110)
        west, south, east, north = bounds
        proposals.append(
            dict(
                context_patch_id=key,
                target="Woody shrub",
                patch=[[west, south], [east, south], [east, north], [west, north]],
                dark_unknown_max_ceiling=45,
                bright_unknown_floor=120,
                interpretation="Low dense chaparral-form woody cover; pale soil and deep darkness remain unknown. Single-interpreter growth-form label, not height-verified.",
            )
        )
    proposals.append(
        dict(
            context_patch_id="r2-california_shrublands-non-vegetated-001",
            target="Non-vegetated & dead",
            patch=[[40, -90], [110, -90], [110, 60], [40, 60]],
            dark_unknown_ceiling=100,
            interpretation="Eastern exposed grey rock slab; adjacent sparse shrubland excluded by geometry; dark cracks/vegetation remain unknown.",
        )
    )
    for case in proposals:
        key = case["context_patch_id"]
        meta = json.loads((PHOTO_CACHE / f"{key}.json").read_text())
        case.update(
            image_sha256=sha(PHOTO_CACHE / f"{key}.npy"),
            metadata_sha256=sha(PHOTO_CACHE / f"{key}.json"),
            aerial_year=int(meta["naip_datetime"][:4]),
            aerial_datetime=meta["naip_datetime"],
        )
    policy = dict(
        date="2026-11-19",
        interpreter="single Codex aerial interpretation",
        independently_verified=False,
        boundary_uncertainty_m=0.6,
        selection="growth form and cover only; no new Landsat values consulted",
        cases=proposals,
        working_cohort="nominal 30 m >=95%; additional 120 m source-area requirement is sensitivity",
    )
    path = OUTPUT / "additional_review_policy.json"
    if path.exists() and json.loads(path.read_text()) != policy:
        raise ValueError("Frozen review changed: create a new version")
    if not path.exists():
        write_json_atomic(path, policy)
    return policy


def supplemental_cases():
    policy = freeze_review()
    cases = []
    geometries = []
    for case in policy["cases"]:
        key = case["context_patch_id"]
        meta = json.loads((PHOTO_CACHE / f"{key}.json").read_text())
        if (
            sha(PHOTO_CACHE / f"{key}.npy") != case["image_sha256"]
            or sha(PHOTO_CACHE / f"{key}.json") != case["metadata_sha256"]
        ):
            raise ValueError("Changed reviewed context")
        image = np.load(PHOTO_CACHE / f"{key}.npy")
        domain = box(-120, -120, 120, 120)
        classes = image_classes(
            case, image, case["aerial_year"], boundary_uncertainty=0.6, domain=domain
        )
        belt = (
            Polygon(case["patch"])
            .boundary.buffer(0.6)
            .intersection(domain)
            .difference(classes["other"])
        )
        classes["target"] = classes["target"].difference(belt)
        classes["uncertain"] = classes["uncertain"].union(belt)
        target = translate(
            classes["target"], xoff=meta["easting"], yoff=meta["northing"]
        )
        cases.append(
            dict(
                key=key,
                meta=meta,
                target=case["target"],
                photo=target,
                basis="dated_photo_cover",
                structural_project="",
            )
        )
        for cover, geom in classes.items():
            geometries.append(
                dict(
                    context_patch_id=key,
                    target=case["target"],
                    cover=cover,
                    geometry=translate(
                        geom, xoff=meta["easting"], yoff=meta["northing"]
                    ),
                )
            )
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        for ax in axes:
            ax.imshow(np.moveaxis(image, 0, -1), extent=(-120, 120, -120, 120))
        draw_geometry(axes[1], classes["uncertain"], "#f5a623", 0.55)
        draw_geometry(axes[1], classes["other"], "#b53584", 0.5)
        axes[0].set_title("Dated aerial source")
        axes[1].set_title("Orange: unknown; magenta: other")
        fig.suptitle(
            f"{key}\n{case['target']}; {case['aerial_datetime'][:10]}; provisional cover interpretation",
            fontsize=10,
        )
        fig.tight_layout()
        fig.savefig(OUTPUT / f"{key}-cover-review.png", dpi=130)
        plt.close(fig)
    path = OUTPUT / "additional_photo_annotations.gpkg"
    # Write a fresh complete layer; upstream masks and policy remain untouched.
    gpd.GeoDataFrame(geometries, crs="EPSG:32611").to_file(
        path, layer="additional_cover_epsg32611", driver="GPKG"
    )
    return cases


def validate_parent():
    """Never reuse copied regional tables after the frozen parent has changed."""
    identity = dict(
        parent_manifest_sha256=sha(PARENT / "manifest.json"),
        parent_nominal_sha256=sha(PARENT / "hls_l30_nominal_95pct_observations.csv"),
    )
    path = OUTPUT / "parent_identity.json"
    if path.exists() and json.loads(path.read_text()) != identity:
        raise ValueError("Parent HLS stage changed; create a new expansion stage")
    if not path.exists():
        write_json_atomic(path, identity)


def initialize():
    freeze_review()
    validate_parent()
    for pattern in [
        "*-catalogue.json",
        "*-all_cover_measurements.csv",
        "*-nominal_reference_cells.csv",
        "*-hls_qa_audit.csv",
        "*-selected_observations.csv",
    ]:
        for source in PARENT.glob(pattern):
            destination = OUTPUT / source.name
            if not destination.exists():
                shutil.copy2(source, destination)
    builder.OUTPUT = OUTPUT
    builder.POLICY = builder.POLICY | dict(
        primary_support="nominal 30 m HLS footprint; full source area is sensitivity"
    )

    def all_cases():
        return ORIGINAL_CASES() + supplemental_cases()

    builder.cases = all_cases


def run():
    initialize()
    builder.extract("california_shrublands")
    builder.finalize()
    write_json_atomic(
        OUTPUT / "expansion_provenance.json",
        dict(
            parent_manifest_sha256=sha(PARENT / "manifest.json"),
            additional_policy_sha256=sha(OUTPUT / "additional_review_policy.json"),
            additional_geometry_sha256=sha(
                OUTPUT / "additional_photo_annotations.gpkg"
            ),
            builder_sha256=sha(Path(builder.__file__)),
            wrapper_sha256=sha(Path(__file__)),
            original_inputs_unchanged=True,
            selection_on_spectra=False,
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-only", action="store_true")
    args = parser.parse_args()
    if args.review_only:
        supplemental_cases()
    else:
        run()
