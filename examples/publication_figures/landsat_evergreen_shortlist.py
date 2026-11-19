"""Assemble Landsat observations for lidar-supported evergreen candidates.

This separate evidence table does not promote candidates to PFT ground truth.
Lidar canopy occupancy, evergreen identity, and temporal stability are distinct
claims. The first is measured here; the latter two require dated reference review.
"""

import json
from itertools import product

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform

import landsat_seasonal_archive as seasonal
from landsat_evergreen_pointcloud import DEST, cell_scores
from landsat_spatial_expansion import CACHE, SEASONAL, sha
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic


def assemble():
    records = []
    for path in sorted(DEST.glob("*.npy")):
        meta = json.loads(path.with_suffix(".json").read_text())
        if sha(path) != meta["array_sha256"]:
            raise ValueError("Changed structural window")
        key = path.name.split("-USGS_")[0].split("-WA_")[0]
        patch = json.loads((CACHE / f"{key}.json").read_text())
        grid = np.load(path)
        end = max(
            x.get("end_datetime") or x.get("datetime") for x in meta["source_intervals"]
        )
        for score in cell_scores(grid):
            x, y = score["offset_east_m"], score["offset_north_m"]
            east, north = patch["easting"] + x, patch["northing"] + y
            shifts = {}
            for shift in [3, 5]:
                shifts[f"shift_{shift}m_min_above_5m_fraction"] = min(
                    float(
                        (
                            grid[
                                y + 105 + dy : y + 135 + dy, x + 105 + dx : x + 135 + dx
                            ]
                            > 5
                        ).mean()
                    )
                    for dx, dy in product([-shift, 0, shift], repeat=2)
                )
            records.append(
                dict(
                    candidate_id=f"epsg{patch['landsat_epsg']}-e{east:.0f}-n{north:.0f}",
                    context_patch_id=key,
                    easting=east,
                    northing=north,
                    landsat_epsg=patch["landsat_epsg"],
                    landsat_row=patch["landsat_row"] - y // 30,
                    landsat_col=patch["landsat_col"] + x // 30,
                    researcher_category="Evergreen",
                    region="cascades",
                    scene_datetime=patch["scene_datetime"],
                    aerial_datetime=patch["naip_datetime"],
                    aerial_id=patch["naip_id"],
                    structural_project=meta["identity"]["project"],
                    structural_end_datetime=end,
                    structural_array_sha256=sha(path),
                    pft_purity_verified=False,
                    reference_status="structural_candidate_pending_identity_and_temporal_review",
                    **score,
                    **shifts,
                )
            )
    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError("No structural candidates at the fixed screen")
    # Choose the latest qualifying structural project, never the best spectral fit.
    frame = frame.sort_values(
        ["structural_end_datetime", "structural_project"]
    ).drop_duplicates("candidate_id", keep="last")
    frame = frame.loc[frame.above_5m_fraction.ge(0.95)].copy()
    write_text_atomic(
        DEST / "structurally_screened_candidate_cells.csv", frame.to_csv(index=False)
    )
    return frame


def extract():
    frame = assemble()
    seasonal.CACHE = CACHE / "evergreen-lidar-landsat"
    seasonal.CACHE.mkdir(exist_ok=True)
    year = pd.Timestamp(frame.aerial_datetime.iloc[0]).year
    if pd.to_datetime(frame.aerial_datetime, utc=True).dt.year.nunique() != 1:
        raise ValueError("Handle reference years separately")
    scenes = json.loads((SEASONAL / f"cascades-{year}-catalogue.json").read_text())[
        "features"
    ]
    _, _, anchor = seasonal.season_window(frame.scene_datetime.iloc[0], year)
    identity = sha(DEST / "structurally_screened_candidate_cells.csv")[:20]
    audits = []
    for item in scenes:
        print(item["id"], len(frame), "structural candidates: Landsat QA", flush=True)
        audit = seasonal.scene_qa(item, frame, anchor, identity)
        dates = pd.to_datetime(audit.acquisition_datetime, utc=True)
        aerial = pd.to_datetime(
            audit.candidate_id.map(frame.set_index("candidate_id").aerial_datetime),
            utc=True,
        )
        audit["aerial_gap_days"] = (
            dates.dt.normalize() - aerial.dt.normalize()
        ).dt.days.abs()
        audit["photo_date_match"] = dates.dt.year.eq(
            aerial.dt.year
        ) & audit.aerial_gap_days.le(45)
        audits.append(audit)
    audit = pd.concat(audits, ignore_index=True)
    write_text_atomic(
        DEST / "structural_candidates_landsat_qa_audit.csv", audit.to_csv(index=False)
    )
    chosen = seasonal.quality_order(
        audit.loc[audit.eligible_observation & audit.photo_date_match]
    ).drop_duplicates("candidate_id")
    records = []
    items = {i["id"]: i for i in scenes}
    for scene_id, group in chosen.groupby("scene_id"):
        refs = frame.set_index("candidate_id").loc[group.candidate_id].reset_index()
        values = seasonal.reflectance(items[scene_id], refs, identity)
        if not np.isfinite(values).all():
            raise ValueError("Nonfinite selected spectra")
        merged = refs.merge(
            group, on="candidate_id", validate="one_to_one", suffixes=("_reference", "")
        )
        for j, band in enumerate(seasonal.BANDS):
            merged[band] = values[:, j]
        records.extend(merged.to_dict("records"))
    result = pd.DataFrame(records)
    if result.empty:
        raise ValueError("No eligible Landsat observations for structural candidates")
    write_text_atomic(
        DEST / "landsat_evergreen_structural_candidate_observations.csv",
        result.to_csv(index=False),
    )
    features = []
    for cell in result.itertuples():
        project = Transformer.from_crs(int(cell.landsat_epsg), 4326, always_xy=True)
        footprint = box(
            cell.easting - 15, cell.northing - 15, cell.easting + 15, cell.northing + 15
        )
        features.append(
            dict(
                type="Feature",
                geometry=mapping(transform(project.transform, footprint)),
                properties={
                    key: getattr(cell, key)
                    for key in (
                        "candidate_id",
                        "context_patch_id",
                        "above_5m_fraction",
                        "shift_5m_min_above_5m_fraction",
                        "scene_id",
                        "pft_purity_verified",
                        "reference_status",
                    )
                },
            )
        )
    write_json_atomic(
        DEST / "evergreen_candidate_footprints.geojson",
        dict(type="FeatureCollection", features=features),
    )
    write_json_atomic(
        DEST / "validation_summary.json",
        dict(
            unique_native_cells=int(result.candidate_id.nunique()),
            distinct_context_patches=int(result.context_patch_id.nunique()),
            retaining_structural_screen_at_5m=int(
                result.shift_5m_min_above_5m_fraction.ge(0.95).sum()
            ),
            preferred_aerosol=int(result.preferred_aerosol.sum()),
            fallback_aerosol=int((~result.preferred_aerosol).sum()),
            source_landsat_scenes=int(result.scene_id.nunique()),
            all_seven_bands_finite=bool(
                np.isfinite(result[list(seasonal.BANDS)]).all().all()
            ),
            all_declared_scene_qa_passed=bool(
                (
                    result.grid_match
                    & result.core_qa_clear
                    & result.context_150m_clear
                    & result.photo_date_match
                    & result.aerosol_level.lt(3)
                ).all()
            ),
            accepted_primary_evergreen_references=0,
            current_evergreen_purity_validated=False,
        ),
    )
    print("QA-screened structural candidates:", len(result), flush=True)
    print(result.groupby("context_patch_id").size().to_string(), flush=True)


if __name__ == "__main__":
    extract()
