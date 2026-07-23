"""Tests for QA parquet reading helpers (DuckDB-first, clash-safe)."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from spectralbridge.qa_plots import _parquet_shape, _safe_read_parquet


def test_safe_read_parquet_and_shape(tmp_path: Path) -> None:
    path = tmp_path / "sample.parquet"
    table = pa.table(
        {
            "pixel_id": ["a", "b", "c", "d", "e"],
            "corr_b001_wl0450nm": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
    )
    pq.write_table(table, path)

    df = _safe_read_parquet(path)
    assert len(df) == 5
    assert "corr_b001_wl0450nm" in df.columns

    sampled = _safe_read_parquet(path, sample_rows=2)
    assert len(sampled) == 2

    shape = _parquet_shape(path)
    assert shape == (5, 2)
