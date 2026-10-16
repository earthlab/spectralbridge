"""Metadata-only annotation-date and exact source-pixel overlap audit."""

from pathlib import Path
from itertools import combinations
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from spectralbridge.bulk.provenance import write_json_atomic

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]


def run():
    index = pd.read_parquet(
        REPO
        / "artifacts/plant_spectral_atlas/closure_20261015/canonical_analysis_index.parquet"
    )
    audit = (
        index.groupby(["site", "year", "field_year", "imagery_year"], dropna=False)
        .agg(
            polygon_years=("GlobalID", "size"),
            unique_polygon_ids=("GlobalID", "nunique"),
        )
        .reset_index()
    )
    audit["extraction_year_matches_polygon_imagery_year"] = audit.year.eq(
        audit.imagery_year
    )
    audit.to_csv(BASE / "tables/annotation_year_audit.csv", index=False)
    plots = (
        index.groupby(["site", "year", "plot", "location"], dropna=False)
        .GlobalID.nunique()
        .rename("unique_polygon_ids")
        .reset_index()
    )
    plots["interpretation"] = (
        "source plot/location annotations; independent populations and individual identity are not verified"
    )
    plots.to_csv(BASE / "tables/plot_location_support.csv", index=False)

    columns = [
        "GlobalID",
        "flight_id",
        "source_image",
        "row",
        "col",
        "x",
        "y",
        "epsg",
        "area_m",
    ]
    table = pq.read_table(
        REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet", columns=columns
    ).to_pandas()
    keycols = ["GlobalID", "flight_id", "source_image", "row", "col"]
    missing = table[keycols].isna().any(axis=1)
    unique = table.loc[~missing, keycols].drop_duplicates()
    sizes = unique.groupby(
        ["flight_id", "source_image", "row", "col"], dropna=False
    ).GlobalID.nunique()
    shared = sizes[sizes > 1]
    edges = {}
    if len(shared):
        multi = (
            unique.set_index(["flight_id", "source_image", "row", "col"])
            .loc[shared.index]
            .reset_index()
        )
        for _, g in multi.groupby(["flight_id", "source_image", "row", "col"]):
            for pair in combinations(sorted(g.GlobalID.unique()), 2):
                edges[pair] = edges.get(pair, 0) + 1
    frame = pd.DataFrame(
        [
            dict(first_GlobalID=a, second_GlobalID=b, shared_source_pixels=n)
            for (a, b), n in edges.items()
        ],
        columns=["first_GlobalID", "second_GlobalID", "shared_source_pixels"],
    )
    frame.to_csv(BASE / "tables/exact_pixel_overlap_edges.csv", index=False)
    involved = set(frame.first_GlobalID) | set(frame.second_GlobalID)
    spatial = []
    for flight, g in table.groupby("flight_id"):
        xy = g[["x", "y"]].to_numpy(float)
        rc = g[["col", "row"]].to_numpy(float)
        centered = rc - rc.mean(0)
        coords = xy - xy.mean(0)
        transform, _, rank, _ = np.linalg.lstsq(centered, coords, rcond=None)
        residual = float(np.max(np.abs(centered @ transform - coords)))
        code = g.epsg.dropna().astype(str).unique()
        try:
            from pyproj import CRS

            units = (
                CRS.from_user_input("EPSG:" + str(int(float(code[0]))))
                .axis_info[0]
                .unit_name
                if len(code) == 1
                else "mixed"
            )
        except (ImportError, ValueError, IndexError):
            units = "unverified"
        spatial.append(
            dict(
                flight_id=flight,
                pixel_col_vector_length=float(np.linalg.norm(transform[0]))
                if rank == 2
                else np.nan,
                pixel_row_vector_length=float(np.linalg.norm(transform[1]))
                if rank == 2
                else np.nan,
                fit_rank=int(rank),
                maximum_coordinate_residual=residual,
                coordinate_units=units,
                epsg="|".join(code),
            )
        )
    pd.DataFrame(spatial).to_csv(
        BASE / "tables/native_spatial_support.csv", index=False
    )
    polygon = (
        table.groupby(["GlobalID", "flight_id"])
        .size()
        .rename("extracted_pixel_rows")
        .reset_index()
    )
    polygon.to_csv(BASE / "tables/polygon_acquisition_pixel_support.csv", index=False)
    labels = index[["GlobalID", "cover_category"]].drop_duplicates("GlobalID")
    byclass = (
        polygon.merge(labels, on="GlobalID", validate="many_to_one")
        .groupby("cover_category")
        .extracted_pixel_rows.agg(
            observations="size",
            median="median",
            minimum="min",
            maximum="max",
            single_pixel_fraction=lambda v: float(v.eq(1).mean()),
        )
        .reset_index()
    )
    byclass.to_csv(BASE / "tables/pixel_support_by_category.csv", index=False)
    result = dict(
        status="passed",
        original_rows=len(table),
        unique_ID_source_pixel_memberships=len(unique),
        missing_key_rows=int(missing.sum()),
        source_pixel_keys=len(sizes),
        source_pixel_keys_shared_by_distinct_IDs=len(shared),
        distinct_ID_pairs=len(edges),
        distinct_source_images=table.source_image.nunique(),
        polygon_acquisition_observations=len(polygon),
        median_extracted_pixels_per_polygon_acquisition=float(
            polygon.extracted_pixel_rows.median()
        ),
        minimum_extracted_pixels_per_polygon_acquisition=int(
            polygon.extracted_pixel_rows.min()
        ),
        maximum_extracted_pixels_per_polygon_acquisition=int(
            polygon.extracted_pixel_rows.max()
        ),
        involved_IDs=len(involved),
        interpretation="Exact same source-image/flight/row/col pixels; absence does not exclude spatial autocorrelation or unresolved geometry overlap",
    )
    write_json_atomic(BASE / "manifests/metadata_audit.json", result)
    print(result)


if __name__ == "__main__":
    run()
