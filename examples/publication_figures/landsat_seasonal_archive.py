"""Collect seasonal Landsat repeats on the fixed regional reference footprints."""

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.transform import xy
from rasterio.windows import Window
from requests.adapters import HTTPAdapter
from shapely import box
from shapely.geometry import shape
from urllib3.util.retry import Retry

from landsat_regional_candidates import (
    BAND_ASSETS,
    OUTPUT as REFERENCE,
    REGIONS,
    fetch_catalogue,
    aerial_chip,
    open_asset,
)
from spectralbridge.bulk.provenance import (
    signature_sha256,
    write_json_atomic,
    write_text_atomic,
)
from spectralbridge.landsat_agreement import mask_landsat_qa, scale_landsat_sr

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REFERENCE / "seasonal-archive"
CACHE = ROOT / "archive/local/landsat-seasonal-archive"
BANDS = [f"B{index}" for index in range(1, 8)]
DEFAULT_YEARS = tuple(range(2020, 2026))
DEFAULT_HALF_WINDOW = 21


def season_window(reference_date, year, half_window=DEFAULT_HALF_WINDOW):
    """Use calendar dates so the reference season stays fixed in leap years."""
    reference = pd.Timestamp(reference_date)
    anchor = pd.Timestamp(year=year, month=reference.month, day=reference.day, tz="UTC")
    window = pd.Timedelta(days=half_window)
    return anchor - window, anchor + window, anchor


def grid_match(raster, reference):
    """Require the same 30 m ground square as the accepted reference grid."""
    if raster.crs.to_epsg() != int(reference.landsat_epsg):
        return False, None, None
    if not np.allclose(
        [
            raster.transform.a,
            raster.transform.b,
            raster.transform.d,
            raster.transform.e,
        ],
        [30, 0, 0, -30],
        rtol=0,
        atol=1e-8,
    ):
        return False, None, None
    row, col = raster.index(reference.easting, reference.northing)
    if not (0 <= row < raster.height and 0 <= col < raster.width):
        return False, row, col
    east, north = xy(raster.transform, row, col)
    matches = np.allclose(
        [east, north],
        [reference.easting, reference.northing],
        rtol=0,
        atol=1e-6,
    )
    return bool(matches), row, col


def quality_order(frame):
    """Order eligible observations using QA and seasonal timing only."""
    return frame.sort_values(
        ["preferred_aerosol", "season_offset_days", "aerosol_level", "scene_id"],
        ascending=[False, True, True, True],
        kind="stable",
    )


def reference_frame(region):
    frame = pd.read_csv(REFERENCE / "regional_candidate_dataset.csv")
    frame = frame.loc[frame.region.eq(region)].copy()
    if frame.empty or frame.candidate_id.duplicated().any():
        raise ValueError("Reference footprints must have unique candidate identities")
    return frame


def session():
    client = requests.Session()
    client.mount(
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
    return client


def catalogue(region, references, years, half_window):
    client = session()
    path_rows = {value.split("_")[2] for value in references.scene_id}
    reference_dates = pd.to_datetime(references.scene_datetime).dt.normalize().unique()
    if len(path_rows) != 1 or len(reference_dates) != 1:
        raise ValueError("Region needs a single reference path/row and seasonal anchor")
    path_row = next(iter(path_rows))
    records = {}
    for year in years:
        start, end, anchor = season_window(reference_dates[0], year, half_window)
        payload = dict(
            collections=["landsat-c2-l2"],
            bbox=REGIONS[region],
            limit=100,
            datetime=f"{start.isoformat()}/{(end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).isoformat()}",
            query={
                "platform": {"in": ["landsat-8", "landsat-9"]},
                "landsat:wrs_path": {"eq": path_row[:3]},
                "landsat:wrs_row": {"eq": path_row[3:]},
            },
        )
        path = OUTPUT / f"{region}-{year}-catalogue.json"
        saved = json.loads(path.read_text()) if path.exists() else {}
        if saved.get("spectralbridge:query") != payload:
            saved = fetch_catalogue(client, payload)
            write_json_atomic(path, saved)
        records[year] = (saved["features"], anchor)
        print(region, year, len(saved["features"]), "catalogued scenes", flush=True)
    aerial_path = OUTPUT / f"{region}-aerial-catalogue.json"
    payload = dict(
        collections=["naip"],
        bbox=REGIONS[region],
        limit=100,
        datetime="2019-01-01T00:00:00Z/2025-12-31T23:59:59Z",
    )
    saved = json.loads(aerial_path.read_text()) if aerial_path.exists() else {}
    if saved.get("spectralbridge:query") != payload:
        saved = fetch_catalogue(client, payload)
        write_json_atomic(aerial_path, saved)
    return records, saved["features"]


def scene_qa(item, references, anchor, identity):
    path = CACHE / f"{item['id']}-{identity}-qa.json"
    if path.exists():
        return pd.DataFrame(json.loads(path.read_text())["records"])
    coords = list(zip(references.easting, references.northing, strict=True))
    with (
        open_asset(item, "qa_pixel") as qa,
        open_asset(item, "qa_radsat") as saturation,
        open_asset(item, "qa_aerosol") as aerosol,
    ):
        for raster in (saturation, aerosol):
            if (raster.crs, raster.transform, raster.shape) != (
                qa.crs,
                qa.transform,
                qa.shape,
            ):
                raise ValueError("Landsat quality grids differ")
        q = np.array([value[0] for value in qa.sample(coords)], dtype=np.uint16)
        r = np.array([value[0] for value in saturation.sample(coords)], dtype=np.uint16)
        a = np.array([value[0] for value in aerosol.sample(coords)], dtype=np.uint16)
        clear, _ = mask_landsat_qa(q, r)
        records = []
        for index, reference in enumerate(references.itertuples()):
            aligned, row, col = grid_match(qa, reference)
            neighborhood = False
            if aligned:
                context = qa.read(
                    1,
                    window=Window(col - 2, row - 2, 5, 5),
                    boundless=True,
                    fill_value=1,
                )
                neighborhood = bool(((context & 63) == 0).all())
            aerosol_level = int((a[index] >> 6) & 3)
            preferred = bool(a[index] & 2) and not bool(a[index] & 32)
            usable = (
                aligned
                and bool(clear[index])
                and neighborhood
                and not bool(q[index] & 128)
                and aerosol_level < 3
            )
            date = pd.Timestamp(item["properties"]["datetime"])
            records.append(
                dict(
                    candidate_id=reference.candidate_id,
                    scene_id=item["id"],
                    platform=item["properties"]["platform"],
                    acquisition_datetime=date.isoformat(),
                    year=anchor.year,
                    season_offset_days=abs((date.normalize() - anchor).days),
                    landsat_row=row,
                    landsat_col=col,
                    grid_match=aligned,
                    qa_pixel=int(q[index]),
                    qa_radsat=int(r[index]),
                    qa_aerosol=int(a[index]),
                    core_qa_clear=bool(clear[index]),
                    context_150m_clear=neighborhood,
                    aerosol_level=aerosol_level,
                    preferred_aerosol=preferred,
                    eligible_observation=bool(usable),
                )
            )
    write_json_atomic(path, dict(records=records))
    return pd.DataFrame(records)


def reflectance(item, references, identity):
    path = CACHE / f"{item['id']}-{identity}-bands.json"
    if path.exists():
        saved = json.loads(path.read_text())
        return np.asarray(saved["values"], dtype=float)
    coords = list(zip(references.easting, references.northing, strict=True))
    columns = []
    expected_grid = None
    with open_asset(item, "qa_pixel") as qa:
        expected_grid = qa.crs, qa.transform, qa.shape
    for key in BAND_ASSETS:
        with open_asset(item, key) as raster:
            if (raster.crs, raster.transform, raster.shape) != expected_grid:
                raise ValueError("Reflectance and quality grids differ")
            columns.append(
                scale_landsat_sr([value[0] for value in raster.sample(coords)])
            )
    values = np.asarray(columns).T
    write_json_atomic(path, dict(values=values.tolist()))
    return values


def aerial_reference(reference, date, aerials):
    # Full-cell coverage is checked against catalog geometry. RGB review is a later stage.
    footprint = (
        gpd.GeoSeries(
            [
                box(
                    reference.easting - 15,
                    reference.northing - 15,
                    reference.easting + 15,
                    reference.northing + 15,
                )
            ],
            crs=int(reference.landsat_epsg),
        )
        .to_crs(4326)
        .iloc[0]
    )
    candidates = [item for item in aerials if shape(item["geometry"]).covers(footprint)]
    if not candidates:
        return dict(aerial_id=None, cover_stability_status="missing_aerial_reference")
    closest = min(
        candidates,
        key=lambda item: (
            abs(
                (
                    pd.Timestamp(item["properties"]["datetime"]).normalize()
                    - date.normalize()
                ).days
            ),
            item["id"],
        ),
    )
    aerial_date = pd.Timestamp(closest["properties"]["datetime"])
    return dict(
        aerial_id=closest["id"],
        aerial_datetime=aerial_date.isoformat(),
        aerial_calendar_gap_days=abs((aerial_date.normalize() - date.normalize()).days),
        cover_stability_status="pending_image_and_change_review",
    )


def run_region(region, years, half_window):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    references = reference_frame(region)
    identity = signature_sha256(
        references[
            ["candidate_id", "easting", "northing", "landsat_epsg", "scene_datetime"]
        ].to_dict("records")
    )[:16]
    source, aerials = catalogue(region, references, years, half_window)
    positions = {value: index for index, value in enumerate(references.candidate_id)}
    for year, (scenes, anchor) in source.items():
        print(region, year, "screening", len(scenes), "scenes", flush=True)
        audits = []
        for item in scenes:
            audits.append(scene_qa(item, references, anchor, identity))
        audit = pd.concat(audits, ignore_index=True) if audits else pd.DataFrame()
        if not audit.empty:
            write_text_atomic(
                OUTPUT / f"{region}-{year}-qa.csv", audit.to_csv(index=False)
            )
            ranked = quality_order(audit.loc[audit.eligible_observation]).copy()
        else:
            ranked = pd.DataFrame()
        selected = {}
        scene_index = {item["id"]: item for item in scenes}
        while not ranked.empty:
            proposals = ranked.drop_duplicates("candidate_id")
            for scene_id, group in proposals.groupby("scene_id"):
                values = reflectance(scene_index[scene_id], references, identity)
                for row in group.itertuples():
                    bands = values[positions[row.candidate_id]]
                    if np.isfinite(bands).all():
                        selected[row.candidate_id] = row._asdict() | dict(
                            zip(BANDS, bands, strict=True)
                        )
                        selected[row.candidate_id].pop("Index", None)
                    else:
                        bad = ranked.candidate_id.eq(
                            row.candidate_id
                        ) & ranked.scene_id.eq(scene_id)
                        ranked = ranked.loc[~bad]
            ranked = ranked.loc[~ranked.candidate_id.isin(selected)]
        records = []
        for reference in references.itertuples():
            record = dict(
                candidate_id=reference.candidate_id,
                region=region,
                year=year,
                reference_scene_id=reference.scene_id,
                reference_month_day=pd.Timestamp(reference.scene_datetime).strftime(
                    "%m-%d"
                ),
                longitude=reference.longitude,
                latitude=reference.latitude,
                easting=reference.easting,
                northing=reference.northing,
                landsat_epsg=int(reference.landsat_epsg),
                map_label=reference.map_label,
                researcher_category=None,
                pft_purity_verified=False,
            )
            if reference.candidate_id in selected:
                record |= selected[reference.candidate_id]
                record["observation_status"] = "selected"
                record |= aerial_reference(
                    reference, pd.Timestamp(record["acquisition_datetime"]), aerials
                )
            else:
                record["observation_status"] = "no_eligible_scene"
                record["cover_stability_status"] = "no_observation"
            records.append(record)
        write_text_atomic(
            OUTPUT / f"{region}-{year}-observations.csv",
            pd.DataFrame(records).to_csv(index=False),
        )
        print(
            region,
            year,
            len(selected),
            "/",
            len(references),
            "footprints selected",
            flush=True,
        )


def review_aerials(region):
    references = reference_frame(region)
    aerials = json.loads((OUTPUT / f"{region}-aerial-catalogue.json").read_text())[
        "features"
    ]
    panels = []
    metadata = []
    for reference in references.itertuples():
        footprint = (
            gpd.GeoSeries(
                [
                    box(
                        reference.easting - 15,
                        reference.northing - 15,
                        reference.easting + 15,
                        reference.northing + 15,
                    )
                ],
                crs=int(reference.landsat_epsg),
            )
            .to_crs(4326)
            .iloc[0]
        )
        per_year = {}
        for item in aerials:
            if not shape(item["geometry"]).covers(footprint):
                continue
            date = pd.Timestamp(item["properties"]["datetime"])
            _, _, target = season_window(reference.scene_datetime, date.year, 0)
            offset = abs((date.normalize() - target).days)
            if offset <= 45:
                key = (offset, item["id"])
                if date.year not in per_year or key < per_year[date.year][0]:
                    per_year[date.year] = (key, item)
        epochs = [per_year[year][1] for year in sorted(per_year)]
        if len(epochs) > 3:
            epochs = [epochs[0], epochs[len(epochs) // 2], epochs[-1]]
        images = []
        for item in epochs:
            identity = signature_sha256(
                dict(
                    id=reference.candidate_id,
                    east=reference.easting,
                    north=reference.northing,
                    epsg=int(reference.landsat_epsg),
                    aerial=item["id"],
                )
            )[:20]
            path = CACHE / f"aerial-{identity}.npy"
            ledger = path.with_suffix(".json")
            image = None
            if ledger.exists():
                state = json.loads(ledger.read_text())
                if state["status"] == "full_window":
                    image = np.load(path)
            else:
                original = (
                    ROOT
                    / "archive/local/landsat-expanded-search"
                    / f"{reference.candidate_id}.json"
                )
                saved = json.loads(original.read_text()) if original.exists() else {}
                original_chip = original.with_suffix(".npy")
                if (
                    saved.get("naip_id") == item["id"]
                    and original_chip.exists()
                    and saved.get("landsat_epsg") == int(reference.landsat_epsg)
                    and np.allclose(
                        [saved.get("easting"), saved.get("northing")],
                        [reference.easting, reference.northing],
                        rtol=0,
                        atol=1e-6,
                    )
                ):
                    image = np.load(original_chip)
                else:
                    print(
                        region, reference.candidate_id, "aerial", item["id"], flush=True
                    )
                    _, image = aerial_chip(reference._asdict(), [item])
                state = dict(
                    status="full_window" if image is not None else "incomplete_window"
                )
                if image is not None:
                    temporary = path.with_suffix(".npy.tmp")
                    with temporary.open("wb") as handle:
                        np.save(handle, image)
                    temporary.replace(path)
                write_json_atomic(ledger, state)
            date = item["properties"]["datetime"]
            metadata.append(
                dict(
                    candidate_id=reference.candidate_id,
                    region=region,
                    aerial_id=item["id"],
                    aerial_date=date,
                    window_status=state["status"],
                    cover_stability_status="pending_visual_interpretation",
                )
            )
            images.append((date, image))
        panels.append((reference, images))
    write_text_atomic(
        OUTPUT / f"{region}-aerial-timeline.csv",
        pd.DataFrame(metadata).to_csv(index=False),
    )
    for start in range(0, len(panels), 4):
        subset = panels[start : start + 4]
        fig, axes = plt.subplots(
            len(subset), 3, figsize=(10, 2.6 * len(subset)), squeeze=False
        )
        for row, (reference, images) in enumerate(subset):
            for col, ax in enumerate(axes[row]):
                ax.axis("off")
                if col >= len(images):
                    continue
                date, image = images[col]
                if image is not None:
                    ax.imshow(
                        np.moveaxis(np.clip(image / 255, 0, 1), 0, -1),
                        extent=(-40, 40, -40, 40),
                    )
                    ax.add_patch(
                        plt.Rectangle(
                            (-15, -15),
                            30,
                            30,
                            fill=False,
                            edgecolor="cyan",
                            linewidth=1.5,
                        )
                    )
                else:
                    ax.text(
                        0.5,
                        0.5,
                        "Incomplete aerial window",
                        ha="center",
                        va="center",
                        transform=ax.transAxes,
                    )
                ax.set_title(
                    f"{reference.candidate_id}\n{pd.Timestamp(date).date()}", fontsize=8
                )
        fig.suptitle(
            region.replace("_", " ").title() + " · same-footprint aerial context",
            weight="bold",
        )
        fig.text(
            0.5,
            0.015,
            "Cyan = fixed 30 m cell. 80 m context. Seasonal aerial dates are retained for change review.",
            ha="center",
            fontsize=8,
        )
        fig.tight_layout(rect=(0, 0.04, 1, 0.96))
        fig.savefig(OUTPUT / f"{region}-timeline-{start // 4 + 1:02d}.png", dpi=130)
        plt.close(fig)


def finalize(years, half_window):
    files = [
        OUTPUT / f"{region}-{year}-observations.csv"
        for region in REGIONS
        for year in years
    ]
    table = pd.concat([pd.read_csv(path) for path in files], ignore_index=True)
    notes_path = OUTPUT / "cover_review_notes.csv"
    if notes_path.exists():
        notes = pd.read_csv(notes_path)
        table = table.merge(
            notes[["candidate_id", "temporal_cover_flag"]],
            how="left",
            on="candidate_id",
            validate="many_to_one",
        )
        table["temporal_cover_flag"] = table.temporal_cover_flag.fillna(
            "visual_review_purity_unresolved"
        )
        observed = table.observation_status.eq("selected")
        table.loc[observed, "cover_stability_status"] = table.loc[
            observed, "temporal_cover_flag"
        ]
    if table.duplicated(["candidate_id", "year"]).any():
        raise ValueError("More than one selected acquisition per footprint/year")
    write_text_atomic(OUTPUT / "seasonal_observations.csv", table.to_csv(index=False))
    selected = table.observation_status.eq("selected")
    summary = (
        table.assign(selected=selected)
        .groupby(["region", "year"], as_index=False)
        .agg(
            footprints=("candidate_id", "size"),
            selected=("selected", "sum"),
            preferred_aerosol=("preferred_aerosol", "sum"),
        )
    )
    write_text_atomic(OUTPUT / "seasonal_support.csv", summary.to_csv(index=False))
    manifest = dict(
        years=list(years),
        seasonal_half_window_days=half_window,
        reference_sha256=hashlib.sha256(
            (REFERENCE / "regional_candidate_dataset.csv").read_bytes()
        ).hexdigest(),
        builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        platforms=["landsat-8", "landsat-9"],
        footprint_count=int(table.candidate_id.nunique()),
        selected_observations=int(selected.sum()),
        inference_unit="footprint; repeated years remain linked to candidate_id",
        purity_verified_count=0,
        files={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(OUTPUT.iterdir())
            if p.suffix in {".csv", ".json", ".md", ".png"}
            and p.name != "manifest.json"
        },
    )
    write_json_atomic(OUTPUT / "manifest.json", manifest)
    print(json.dumps({key: value for key, value in manifest.items() if key != "files"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", choices=list(REGIONS))
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--half-window-days", type=int, default=DEFAULT_HALF_WINDOW)
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--review-region", choices=list(REGIONS))
    args = parser.parse_args()
    if not 0 <= args.half_window_days <= 60 or not all(
        2013 <= year <= 2026 for year in args.years
    ):
        parser.error("Require years 2013–2026 and a seasonal half-window of 0–60 days")
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        GDAL_HTTP_TIMEOUT=30,
        GDAL_HTTP_MAX_RETRY=2,
    ):
        if args.region:
            run_region(args.region, sorted(set(args.years)), args.half_window_days)
        if args.review_region:
            review_aerials(args.review_region)
        if args.finalize:
            finalize(sorted(set(args.years)), args.half_window_days)
