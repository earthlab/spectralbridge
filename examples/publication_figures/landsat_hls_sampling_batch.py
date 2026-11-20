"""Fixed cover-only proposal batches, distant from previously proposed contexts.

Land-cover/GAP are locators, never reference truth. No HLS spectra or p-values
enter selection. Dates, QA and reference verification remain downstream stages.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from rasterio.transform import xy
from scipy.ndimage import label

import landsat_regional_candidates as regional
import landsat_spatial_expansion as expansion
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

ROOT = expansion.OUTPUT / "power-directed-expansion"
CACHE = regional.ROOT / "archive/local/landsat-power-expansion"
BATCH = {
    "cascades": {"Evergreen": 24, "Herbaceous": 8, "Non-vegetated & dead": 8},
    "gunnison_aspen": {"Deciduous": 12, "Herbaceous": 8, "Non-vegetated & dead": 8},
    "front_range": {"Evergreen": 8, "Herbaceous": 8, "Non-vegetated & dead": 8},
    "yellowstone": {"Evergreen": 8, "Herbaceous": 8, "Non-vegetated & dead": 8},
    "california_shrublands": {
        "Woody shrub": 8,
        "Herbaceous": 8,
        "Non-vegetated & dead": 8,
    },
}
POLICY = dict(
    batch=BATCH,
    spacing_m=1000,
    maximum_locator_rank=100,
    old_proposals_excluded=True,
    context_m=240,
    selection="locator interior and physical spacing only; no spectra or significance",
    herbaceous_locator="WorldCover grass intersect GAP grassland/meadow, excluding shrub/steppe/woodland/forest/savanna names",
)


def discover():
    ROOT.mkdir(exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    path = ROOT / "patch_proposals.csv"
    policy = ROOT / "sampling_batch_policy.json"
    if path.exists():
        if json.loads(policy.read_text()) != POLICY:
            raise ValueError("Frozen sampling batch changed")
        print("Reusing frozen sampling batch", flush=True)
        return
    write_json_atomic(policy, POLICY)
    old = pd.read_csv(expansion.OUTPUT / "patch_proposals.csv")
    previous = pd.read_csv(expansion.PREVIOUS / "regional_candidate_dataset.csv")
    records = []
    for region, targets in BATCH.items():
        world, t = regional.map_grid(region)
        gap_items = expansion.gap_catalogue(region)
        gap, gt = regional.map_grid(region, "gap", catalogue_features=gap_items)
        if gt != t:
            raise ValueError("Locator grids differ")
        masks = expansion.locator_masks(world, gap)
        classes = gap_items[0]["properties"]["label:classes"][0]["classes"]
        herb_codes = [
            i
            for i, name in enumerate(classes)
            if any(w in name.lower() for w in ["grassland", "meadow"])
            and not any(
                w in name.lower()
                for w in ["shrub", "steppe", "woodland", "forest", "savanna"]
            )
        ]
        masks["Herbaceous"] &= np.isin(gap, herb_codes)
        anchor = previous.loc[previous.region.eq(region)].iloc[0]
        inverse = Transformer.from_crs(int(anchor.landsat_epsg), 4326, always_xy=True)
        old_coords = old.loc[old.region.eq(region), ["easting", "northing"]].to_numpy()
        accepted = []
        for target, count in targets.items():
            components, _ = label(masks[target])
            found = 0
            for row, col, interior in regional.interior_centers(
                masks[target], count=100, spacing_m=1000
            ):
                east, north = xy(t, row, col)
                grid = expansion.snap_center(east, north, anchor)
                coord = np.array([grid["easting"], grid["northing"]])
                excluded = (
                    np.vstack([old_coords, np.array(accepted).reshape(-1, 2)])
                    if accepted
                    else old_coords
                )
                if (
                    len(excluded)
                    and np.linalg.norm(excluded - coord, axis=1).min() < 1000
                ):
                    continue
                lon, lat = inverse.transform(*coord)
                found += 1
                accepted.append(coord)
                records.append(
                    dict(
                        context_patch_id=f"power-{region}-{target.lower().split()[0]}-{found:03d}",
                        region=region,
                        target_hypothesis=target,
                        locator_component_id=f"{region}-{target}-{components[row, col]}",
                        map_interior_m=interior,
                        worldcover_code=int(world[row, col]),
                        gap_code=int(gap[row, col]),
                        gap_label=classes[int(gap[row, col])],
                        reference_scene_id=anchor.scene_id,
                        scene_datetime=anchor.scene_datetime,
                        longitude=lon,
                        latitude=lat,
                        reference_review="not_reviewed",
                        pft_purity_verified=False,
                        **grid,
                    )
                )
                if found >= count:
                    break
            print(
                region,
                target,
                "new separated proposals",
                found,
                "of",
                count,
                flush=True,
            )
    write_text_atomic(path, pd.DataFrame(records).to_csv(index=False))
    write_json_atomic(
        ROOT / "sampling_batch_manifest.json",
        dict(
            code_sha256=expansion.sha(Path(__file__)),
            proposals_sha256=expansion.sha(path),
            policy=POLICY,
            prior_proposals_sha256=expansion.sha(
                expansion.OUTPUT / "patch_proposals.csv"
            ),
        ),
    )


def contexts(region):
    expansion.OUTPUT = ROOT
    expansion.CACHE = CACHE
    expansion.context(region)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--discover", action="store_true")
    p.add_argument("--context", choices=list(BATCH))
    args = p.parse_args()
    if args.discover:
        discover()
    if args.context:
        contexts(args.context)
