"""Audit independently labelled footprints before testing Landsat PFT contrasts."""

from contextlib import ExitStack
from itertools import combinations
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import rowcol, xy
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window
from shapely import box, union_all

from landsat_pft_panel import BANDS, DRONE, EVIDENCE, EXTRA_ASSETS, LABEL, ROOT, SCENE
from spectralbridge.landsat_agreement import mask_landsat_qa, scale_landsat_sr
from spectralbridge.pft_method_audit import AuditConfig, method_statistics
from spectralbridge.plant_pft_statistics import holm
from spectralbridge.sensor_pft_transfer import OLI_CENTERS

OUTPUT = ROOT / "provenance/landsat-pure-pixels/2026-11-18"
SCENE_DATE = pd.Timestamp("2023-08-20", tz="UTC")
MAX_DATE_LAG_DAYS = 30
MARGIN_METERS = 10
BLOCK_METERS = 300
MIN_PER_CLASS = 10
MIN_MIXED_BLOCKS = 3
SOURCES = {
    "niwot_original": ROOT / "Datasets/niwot_aop_macrosystems_data_2023_12_8_23.gpkg",
    "merged_original": ROOT
    / "archive/research/polygons/merged_all_AOP_polygon_data_2023_2024.geojson",
}
CATEGORIES = pd.read_csv(EVIDENCE / "category_support.csv").researcher_category.tolist()


def read_reference(crs, scene_bounds):
    frames = []
    for source, path in SOURCES.items():
        frame = gpd.read_file(path, columns=["GlobalID", LABEL, "collection_date"])
        frame = frame.to_crs(crs)
        frame.geometry = frame.geometry.make_valid()
        frame = frame.loc[frame.geometry.intersects(scene_bounds)].copy()
        frame["source"] = source
        dates = pd.to_datetime(frame.collection_date, utc=True, errors="coerce")
        frame["lag_days"] = (dates.dt.normalize() - SCENE_DATE).abs().dt.days
        frames.append(frame)
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=crs)


def grid_cells(reference, grid):
    """Enumerate native cells touched by a label, without sampling the raster."""
    rows_cols = set()
    for geom in reference.geometry:
        left, bottom, right, top = geom.bounds
        row_min, col_min = rowcol(grid.transform, left, top)
        row_max, col_max = rowcol(grid.transform, right, bottom)
        rows_cols.update(
            (row, col)
            for row in range(max(0, row_min), min(grid.height, row_max + 1))
            for col in range(max(0, col_min), min(grid.width, col_max + 1))
        )
    for row, col in sorted(rows_cols):
        x, y = xy(grid.transform, row, col)
        yield row, col, x, y, box(x - 15, y - 15, x + 15, y + 15)


def footprint_evidence(reference, cell):
    left, bottom, right, top = cell.bounds
    m = MARGIN_METERS
    padded = box(left - m, bottom - m, right + m, top + m)
    evidence = reference.iloc[reference.sindex.query(padded, predicate="intersects")]
    core = evidence.geometry.intersection(cell)
    if not core.area.gt(0).any():
        return None
    near = evidence.lag_days.le(MAX_DATE_LAG_DAYS)
    coverage = {}
    buffered = {}
    for category in CATEGORIES:
        same = evidence[LABEL].eq(category)
        coverage[category] = union_all(core[same]).area / cell.area
        buffered[category] = (
            union_all(evidence.geometry[same & near]).intersection(padded).area
            / padded.area
        )
    best = max(coverage, key=coverage.get)
    best_near = max(buffered, key=buffered.get)
    conflict = (
        union_all(evidence.geometry[~evidence[LABEL].eq(best_near) & near])
        .intersection(padded)
        .area
    )
    return {
        "dominant_mapped_category": best,
        "dominant_fraction_any_date": coverage[best],
        "mapped_fraction_any_date": union_all(core).area / cell.area,
        "buffered_candidate_category": best_near if buffered[best_near] > 0 else None,
        "buffered_same_class_fraction_30d": buffered[best_near],
        "buffered_conflicting_fraction_30d": conflict / padded.area,
        "reference_records": ";".join(
            sorted({f"{r.source}:{r.GlobalID}" for r in evidence.itertuples()})
        ),
        **{
            f"mapped_{index + 1}_fraction_any_date": coverage[label]
            for index, label in enumerate(CATEGORIES)
        },
    }


def audit_pixels():
    qa_path = Path(f"{SCENE}_QA_PIXEL.TIF")
    saturation_path = EXTRA_ASSETS / f"{SCENE.name}_QA_RADSAT.TIF"
    band_paths = [
        Path(f"{SCENE}_SR_B{idx}.TIF")
        if idx < 7
        else EXTRA_ASSETS / f"{SCENE.name}_SR_B7.TIF"
        for idx in range(1, 8)
    ]
    with ExitStack() as stack:
        qa, saturation, *rasters = [
            stack.enter_context(rasterio.open(p))
            for p in (qa_path, saturation_path, *band_paths)
        ]
        if qa.crs.to_epsg() != 32613 or (
            qa.transform.a,
            qa.transform.e,
            qa.transform.b,
            qa.transform.d,
        ) != (30, -30, 0, 0):
            raise ValueError("Expected the native 30 m Niwot Landsat grid")
        for raster in (saturation, *rasters):
            if (raster.crs, raster.transform, raster.shape) != (
                qa.crs,
                qa.transform,
                qa.shape,
            ):
                raise ValueError(f"Landsat grid mismatch in {raster.name}")
        reference = read_reference(qa.crs, box(*qa.bounds))
        drone_bounds = {}
        for site in ("goldhill", "gordon", "ruby"):
            (image,) = (DRONE / site).rglob("*__envi.img")
            with rasterio.open(image) as drone:
                bounds = gpd.GeoSeries([box(*drone.bounds)], crs=drone.crs)
                drone_bounds[site] = bounds.to_crs(qa.crs).iloc[0]
        rows = []
        for row, col, x, y, cell in grid_cells(reference, qa):
            evidence = footprint_evidence(reference, cell)
            if evidence is not None:
                rows.append(
                    dict(
                        evidence,
                        scene=SCENE.name,
                        row=row,
                        col=col,
                        x=x,
                        y=y,
                        geometry=cell,
                        drone_extent=";".join(
                            site
                            for site, bounds in drone_bounds.items()
                            if bounds.intersects(cell)
                        ),
                    )
                )
        audit = gpd.GeoDataFrame(rows, crs=qa.crs).sort_values(["row", "col"])
        coords = list(zip(audit.x, audit.y, strict=True))
        audit["qa_pixel"] = [sample[0] for sample in qa.sample(coords)]
        audit["qa_radsat"] = [sample[0] for sample in saturation.sample(coords)]
        audit["qa_pass"], _ = mask_landsat_qa(audit.qa_pixel, audit.qa_radsat)
        for name, raster in zip(BANDS, rasters, strict=True):
            audit[name] = scale_landsat_sr(
                [sample[0] for sample in raster.sample(coords)]
            )
    audit["valid_spectrum"] = np.isfinite(audit[BANDS]).all(axis=1)
    audit["full_buffered_single_class_30d"] = audit.buffered_same_class_fraction_30d.ge(
        1 - 1e-9
    ) & audit.buffered_conflicting_fraction_30d.le(1e-9)
    # Independent visual adjudication of the full buffered footprint is required.
    # No reviewed full-coverage reference chips have been supplied for this audit.
    audit["reference_review"] = "pending"
    audit["eligible"] = (
        audit.qa_pass
        & audit.valid_spectrum
        & audit.full_buffered_single_class_30d
        & audit.reference_review.eq("verified")
    )
    return audit


def drone_review(pixels):
    """Export review chips for the best mapped cell per category and drone site."""
    clear = pixels.loc[pixels.qa_pass & pixels.valid_spectrum]
    records = []
    chips = []
    for site in ("goldhill", "gordon", "ruby"):
        (image,) = (DRONE / site).rglob("*__envi.img")
        candidates = clear.loc[
            clear.drone_extent.str.split(";").map(lambda names: site in names)
        ]
        with rasterio.open(image) as mosaic, WarpedVRT(mosaic, crs=pixels.crs) as drone:
            for category, group in candidates.groupby(
                "dominant_mapped_category", sort=True
            ):
                for _, pixel in group.sort_values(
                    "dominant_fraction_any_date", ascending=False, kind="stable"
                ).iterrows():
                    x, y = pixel.x, pixel.y
                    left, bottom, right, top = drone.bounds
                    if not (
                        left <= x - 25
                        and x + 25 <= right
                        and bottom <= y - 25
                        and y + 25 <= top
                    ):
                        continue
                    col, row = ~drone.transform * (x - 25, y + 25)
                    window = Window(col, row, 50 / drone.res[0], 50 / drone.res[1])
                    rgb = (
                        drone.read(
                            (6, 4, 2),
                            window=window,
                            out_shape=(3, 250, 250),
                            masked=True,
                        )
                        .astype(float)
                        .filled(np.nan)
                    )
                    valid = np.isfinite(rgb).all(axis=0) & np.any(rgb != 0, axis=0)
                    if not valid.all():
                        continue
                    lo, hi = np.percentile(rgb, [2, 98])
                    if hi <= lo:
                        continue
                    records.append(
                        {
                            field: pixel[field]
                            for field in (
                                "scene",
                                "row",
                                "col",
                                "geometry",
                                "dominant_mapped_category",
                                "dominant_fraction_any_date",
                                "reference_records",
                            )
                        }
                        | {"review_site": site}
                    )
                    chips.append(
                        (
                            site,
                            category,
                            pixel,
                            np.moveaxis(np.clip((rgb - lo) / (hi - lo), 0, 1), 0, -1),
                        )
                    )
                    break
    if not chips:
        return
    gpd.GeoDataFrame(records, crs=pixels.crs).to_crs(4326).to_file(
        OUTPUT / "drone_review_shortlist.geojson",
        driver="GeoJSON",
    )
    cols = 4
    fig, axes = plt.subplots((len(chips) + cols - 1) // cols, cols, figsize=(12, 9))
    for ax in axes.flat:
        ax.axis("off")
    for ax, (site, category, pixel, rgb) in zip(axes.flat, chips):
        ax.imshow(rgb, extent=(-25, 25, -25, 25))
        ax.add_patch(
            plt.Rectangle((-15, -15), 30, 30, fill=False, color="#00edff", lw=1.5)
        )
        ax.set_title(
            f"{site.title()} · {category}\n"
            f"r{pixel.row} c{pixel.col} · {pixel.dominant_fraction_any_date:.1%} mapped",
            fontsize=9,
        )
    fig.suptitle("Drone RGB context for candidate Landsat footprints", weight="bold")
    fig.text(
        0.5,
        0.025,
        "Cyan = 30 m cell; each chip is 50 m across. "
        "Percentages show archived polygon coverage. Review candidates only.",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.95))
    fig.savefig(OUTPUT / "drone_review_chips.png", dpi=140)
    plt.close(fig)


def separability(verified):
    records = []
    config = AuditConfig()
    for a, b in combinations(CATEGORIES, 2):
        pair = verified.loc[verified.buffered_candidate_category.isin([a, b])].copy()
        pair["block"] = list(
            zip(
                pair.x.floordiv(BLOCK_METERS),
                pair.y.floordiv(BLOCK_METERS),
                strict=True,
            )
        )
        mixed = (
            pair.groupby("block").buffered_candidate_category.transform("nunique").eq(2)
        )
        pair = pair.loc[mixed]
        label = pair.buffered_candidate_category.eq(a)
        n_a, n_b = int(label.sum()), int((~label).sum())
        blocks = pair.block.nunique()
        rec = dict(
            a=a,
            b=b,
            verified_a=int(verified.buffered_candidate_category.eq(a).sum()),
            verified_b=int(verified.buffered_candidate_category.eq(b).sum()),
            mixed_block_a=n_a,
            mixed_block_b=n_b,
            mixed_blocks=blocks,
            status="insufficient_verified_support",
            p_npc=np.nan,
        )
        if min(n_a, n_b) >= MIN_PER_CLASS and blocks >= MIN_MIXED_BLOCKS:
            result = method_statistics(
                pair[BANDS].to_numpy(),
                label.to_numpy(float),
                pd.factorize(pair.block)[0],
                OLI_CENTERS,
                config=config,
                integration_weights=np.ones(len(BANDS)),
            )
            rec.update(status="tested", p_npc=result["p"]["npc"])
        records.append(rec)
    results = pd.DataFrame(records)
    tested = results.p_npc.notna()
    results["p_npc_holm"] = np.nan
    if tested.any():
        results.loc[tested, "p_npc_holm"] = holm(results.loc[tested, "p_npc"])
    return results


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    pixels = audit_pixels()
    verified = pixels.loc[pixels.eligible].copy()
    pixels.to_parquet(OUTPUT / "footprint_audit.parquet", index=False)
    verified.to_parquet(OUTPUT / "verified_pixels.parquet", index=False)
    separability(verified).to_csv(OUTPUT / "separability.csv", index=False)
    drone_review(pixels)
    print(f"Audited {len(pixels)} cells; {len(verified)} verified. Outputs in {OUTPUT}")
