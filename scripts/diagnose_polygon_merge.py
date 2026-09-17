#!/usr/bin/env python3
"""Stage-by-stage diagnostic for polygon merge / empty CSV issues."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


def _qp(path: Path) -> str:
    return str(path).replace("'", "''")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "flight_dir",
        type=Path,
        help="Flightline output directory",
    )
    args = parser.parse_args()

    flight_dir = args.flight_dir.resolve()
    flight_id = flight_dir.name
    con = duckdb.connect()

    index_path = flight_dir / f"{flight_id}_polygon_pixel_index.parquet"
    corrected_path = flight_dir / f"{flight_id}_brdfandtopo_corrected_envi_polygons.parquet"
    raw_path = flight_dir / f"{flight_id}_envi_polygons.parquet"
    merged_path = flight_dir / f"{flight_id}_polygons_merged_pixel_extraction.parquet"

    def count_rows(path: Path) -> int:
        sql = f"SELECT COUNT(*) FROM read_parquet('{_qp(path)}')"
        return int(con.execute(sql).fetchone()[0])

    print("=" * 60)
    print(f"Flightline: {flight_id}")
    print("=" * 60)

    print("\nSTAGE 1: Polygon index")
    print(f"  Path: {index_path.name}")
    print(f"  Rows: {count_rows(index_path):,}")

    print("\nSTAGE 2: Product parquets")
    for p in sorted(flight_dir.glob("*_polygons.parquet")):
        print(f"  {p.name}: {count_rows(p):,} rows")

    print("\nSTAGE 3: pixel_id overlap (index vs corrected)")
    overlap_sql = f"""
        SELECT COUNT(*)
        FROM read_parquet('{_qp(index_path)}') idx
        INNER JOIN read_parquet('{_qp(corrected_path)}') p USING (pixel_id)
    """
    overlap = int(con.execute(overlap_sql).fetchone()[0])
    print(f"  Matched pixel_ids: {overlap:,}  (expect same as index)")

    print("\nSTAGE 4: Reflectance sanity (raw vs corrected, first 500 polygon pixels)")
    wl_pat = re.compile(r"_wl\d+nm", re.I)

    def spectral_stats(path: Path, label: str) -> None:
        if not path.exists():
            print(f"  {label}: MISSING {path.name}")
            return
        df = con.execute(
            f"SELECT * FROM read_parquet('{_qp(path)}') LIMIT 500"
        ).df()
        spec_cols = [
            c
            for c in df.columns
            if wl_pat.search(c) and not c.lower().startswith("raw_")
        ]
        if not spec_cols:
            print(f"  {label}: no spectral columns found")
            return
        spec = df[spec_cols].apply(pd.to_numeric, errors="coerce")
        finite = spec[np.isfinite(spec) & (spec > -9000)]
        print(f"  {label}:")
        print(f"    spectral columns: {len(spec_cols)}")
        if finite.size == 0:
            print("    ⚠️  ALL values are NaN or -9999")
        else:
            print(f"    min={finite.min().min():.4f}  max={finite.max().max():.4f}  mean={finite.mean().mean():.4f}")
        zero_frac = (spec.fillna(-9999) == 0).mean().mean()
        nodata_frac = (np.isclose(spec.fillna(0), -9999, atol=0.01)).mean().mean()
        print(f"    fraction exactly 0: {zero_frac:.1%}")
        print(f"    fraction -9999: {nodata_frac:.1%}")

    spectral_stats(raw_path, "raw ENVI")
    spectral_stats(corrected_path, "BRDF+topo corrected")

    print("\nSTAGE 5: Current merged parquet (post-filter)")
    if merged_path.exists():
        print(f"  Rows: {count_rows(merged_path):,}")
    else:
        print("  MISSING")

    print("\nSTAGE 6: Fresh test merge (no filter)")
    test_merge = flight_dir / f"{flight_id}_TEST_merge_no_filter.parquet"
    if test_merge.exists():
        test_merge.unlink()

    from spectralbridge.paths import FlightlinePaths
    from spectralbridge.polygons import merge_polygon_parquets_for_flightline

    flight_paths = FlightlinePaths(flight_dir.parent, flight_id)
    product_parquets = {
        p.stem.replace("_polygons", ""): p for p in sorted(flight_dir.glob("*_polygons.parquet"))
    }
    merge_polygon_parquets_for_flightline(
        flight_paths,
        index_path,
        product_parquets,
        output_path=test_merge,
        overwrite=True,
    )
    test_rows = count_rows(test_merge)
    print(f"  Fresh merge rows: {test_rows:,}  (expect same as index)")

    print("\nSTAGE 7: Filter simulation (would rows survive >90% invalid rule?)")
    if test_rows == 0:
        print("  Skipped (merge empty)")
    else:
        df = con.execute(
            f"SELECT * FROM read_parquet('{_qp(test_merge)}') LIMIT 500"
        ).df()
        meta_keywords = {
            "pixel_id", "row", "col", "x", "y", "lon", "lat", "polygon_id",
            "species", "aop_site", "source_image",
        }
        spec_cols = [
            c
            for c in df.columns
            if wl_pat.search(c)
            and not any(k in c.lower() for k in meta_keywords)
            and not c.lower().startswith("raw_")
        ]
        spec = df[spec_cols].apply(pd.to_numeric, errors="coerce")

        def invalid_frac(row: pd.Series) -> float:
            non_null = row.notna()
            nn = int(non_null.sum())
            if nn == 0:
                return 1.0
            vals = row[non_null]
            bad = np.isclose(vals, -9999.0, atol=0.01) | (vals < 0)
            return float(bad.sum()) / nn

        fracs = spec.apply(invalid_frac, axis=1)
        dropped = int((fracs > 0.90).sum())
        print(f"  Sample size: {len(fracs)}")
        print(f"  Would drop: {dropped}/{len(fracs)} rows")
        print(f"  Max invalid fraction: {fracs.max():.3f}")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
