"""Tests for streaming no-data row filtering on merged parquet outputs."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from spectralbridge.merge_duckdb import _filter_no_data_rows_from_parquet


def _write_merged_like(path: Path, rows: list[dict]) -> None:
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)


def test_filter_no_data_rows_streams_and_drops_invalid_majority(tmp_path: Path) -> None:
    parquet_path = tmp_path / "merged.parquet"
    _write_merged_like(
        parquet_path,
        [
            {
                "pixel_id": "keep",
                "raw_b001_wl0450nm": -9999.0,  # ignored (raw_*)
                "corr_b001_wl0450nm": 0.2,
                "corr_b002_wl0550nm": 0.3,
                "landsat_oli_b001_wl0482nm": 0.25,
            },
            {
                "pixel_id": "drop_all_nodata",
                "raw_b001_wl0450nm": 0.5,
                "corr_b001_wl0450nm": -9999.0,
                "corr_b002_wl0550nm": -9999.0,
                "landsat_oli_b001_wl0482nm": -1.0,
            },
            {
                "pixel_id": "drop_all_null_spectral",
                "raw_b001_wl0450nm": 0.1,
                "corr_b001_wl0450nm": None,
                "corr_b002_wl0550nm": None,
                "landsat_oli_b001_wl0482nm": None,
            },
            {
                "pixel_id": "keep_mostly_valid",
                "raw_b001_wl0450nm": -9999.0,
                "corr_b001_wl0450nm": 0.4,
                "corr_b002_wl0550nm": -9999.0,  # 1/3 invalid among non-null
                "landsat_oli_b001_wl0482nm": 0.35,
            },
        ],
    )

    con = duckdb.connect()
    _filter_no_data_rows_from_parquet(con, parquet_path)

    kept = con.execute(
        f"SELECT pixel_id FROM read_parquet('{parquet_path}') ORDER BY pixel_id"
    ).fetchall()
    assert [row[0] for row in kept] == ["keep", "keep_mostly_valid"]


def test_filter_no_data_rows_noop_when_all_valid(tmp_path: Path) -> None:
    parquet_path = tmp_path / "merged_ok.parquet"
    _write_merged_like(
        parquet_path,
        [
            {
                "pixel_id": "a",
                "corr_b001_wl0450nm": 0.1,
                "corr_b002_wl0550nm": 0.2,
            },
            {
                "pixel_id": "b",
                "corr_b001_wl0450nm": 0.3,
                "corr_b002_wl0550nm": 0.4,
            },
        ],
    )
    before = parquet_path.stat().st_mtime_ns
    con = duckdb.connect()
    _filter_no_data_rows_from_parquet(con, parquet_path)
    after_ids = [
        r[0]
        for r in con.execute(
            f"SELECT pixel_id FROM read_parquet('{parquet_path}') ORDER BY pixel_id"
        ).fetchall()
    ]
    assert after_ids == ["a", "b"]
    # No rewrite when nothing filtered
    assert parquet_path.stat().st_mtime_ns == before


def test_filter_implementation_avoids_pandas_full_table_load() -> None:
    import inspect

    source = inspect.getsource(_filter_no_data_rows_from_parquet)
    assert "import pandas" not in source
    assert "COPY (SELECT * FROM read_parquet" in source
    assert "Streaming filter" in source or "DuckDB streaming" in source
    # Full-table materialization must not return; only DESCRIBE may use .df().
    assert source.count(".df()") <= 1
