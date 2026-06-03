from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from pandas.api.types import (
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_string_dtype,
)

from spectralbridge.polygons import extract_polygon_parquet_from_envi


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.register("df_view", df)
        con.execute(
            "COPY (SELECT * FROM df_view) TO '"
            + str(path).replace("'", "''")
            + "' (FORMAT PARQUET)"
        )
    finally:
        con.close()


class _ChunkIter:
    def __init__(self, chunks: list[pd.DataFrame]) -> None:
        self._chunks = iter(chunks)
        self.context = {"band_wavelengths": [450]}

    def __iter__(self) -> "_ChunkIter":
        return self

    def __next__(self) -> pd.DataFrame:
        return next(self._chunks)


def test_extract_polygon_parquet_from_envi_stabilizes_null_only_metadata_chunks(
    tmp_path: Path,
    monkeypatch,
) -> None:
    polygon_index_path = tmp_path / "polygon_index.parquet"
    output_parquet_path = tmp_path / "TEST_raw_polygon.parquet"

    polygon_index_df = pd.DataFrame(
        {
            "pixel_id": pd.Series([0, 1, 2, 3], dtype="int64"),
            "polygon_id": pd.Series([101, 101, 101, 101], dtype="int64"),
            "species": [None, None, "PIPO", "ABLA"],
            "cover_subcategory": [None, None, "tree", "understory"],
            "dead_subcategory": [None, None, "snag", "live"],
            "polygon_geometry_wkb": [None, None, b"\x01\x02", b"\x03\x04"],
            "surveyed_at": [
                pd.NaT,
                pd.NaT,
                pd.Timestamp("2024-06-01T12:00:00"),
                pd.Timestamp("2024-06-02T12:00:00"),
            ],
            "canopy_cover": [np.nan, np.nan, 0.65, 0.35],
        }
    )
    _write_parquet(polygon_index_df, polygon_index_path)

    chunk_iter = _ChunkIter(
        [
            pd.DataFrame(
                {
                    "pixel_id": [0, 1],
                    "row": [0, 0],
                    "col": [0, 1],
                    "x": [100.0, 101.0],
                    "y": [200.0, 200.0],
                    "raw_b001_wl0450nm": [0.10, 0.20],
                }
            ),
            pd.DataFrame(
                {
                    "pixel_id": [2, 3],
                    "row": [1, 1],
                    "col": [0, 1],
                    "x": [100.0, 101.0],
                    "y": [199.0, 199.0],
                    "raw_b001_wl0450nm": [0.30, 0.40],
                }
            ),
        ]
    )

    captured_chunks: list[pd.DataFrame] = []

    def _capture_chunks(parquet_path, filtered_iter, stage_key, **kwargs) -> None:
        assert parquet_path == output_parquet_path
        assert stage_key == "raw"
        captured_chunks.extend(filtered_iter)

    monkeypatch.setattr(
        "cross_sensor_cal.parquet_export.read_envi_in_chunks",
        lambda *args, **kwargs: chunk_iter,
    )
    monkeypatch.setattr(
        "cross_sensor_cal.parquet_export._write_parquet_chunks",
        _capture_chunks,
    )

    result = extract_polygon_parquet_from_envi(
        tmp_path / "dummy.img",
        tmp_path / "dummy.hdr",
        polygon_index_path,
        output_parquet_path,
        chunk_size=2,
        overwrite=True,
    )

    assert result == output_parquet_path
    assert len(captured_chunks) == 2

    first_chunk, second_chunk = captured_chunks

    for column_name in ("species", "cover_subcategory", "dead_subcategory"):
        assert is_string_dtype(first_chunk[column_name].dtype)
        assert is_string_dtype(second_chunk[column_name].dtype)

    assert is_integer_dtype(first_chunk["polygon_id"].dtype)
    assert is_integer_dtype(second_chunk["polygon_id"].dtype)
    assert is_datetime64_any_dtype(first_chunk["surveyed_at"].dtype)
    assert is_datetime64_any_dtype(second_chunk["surveyed_at"].dtype)
    assert is_float_dtype(first_chunk["canopy_cover"].dtype)
    assert is_float_dtype(second_chunk["canopy_cover"].dtype)
    assert str(first_chunk["polygon_geometry_wkb"].dtype) == str(
        second_chunk["polygon_geometry_wkb"].dtype
    )

    assert first_chunk["species"].isna().all()
    assert second_chunk["species"].tolist() == ["PIPO", "ABLA"]
    assert first_chunk["cover_subcategory"].isna().all()
    assert second_chunk["cover_subcategory"].tolist() == ["tree", "understory"]
    assert first_chunk["dead_subcategory"].isna().all()
    assert second_chunk["dead_subcategory"].tolist() == ["snag", "live"]

    assert first_chunk["polygon_id"].tolist() == [101, 101]
    assert second_chunk["polygon_id"].tolist() == [101, 101]
    assert pd.isna(first_chunk.loc[first_chunk.index[0], "surveyed_at"])
    assert second_chunk.loc[second_chunk.index[0], "surveyed_at"] == pd.Timestamp(
        "2024-06-01T12:00:00"
    )
    assert np.isnan(first_chunk.loc[first_chunk.index[0], "canopy_cover"])
    assert second_chunk.loc[second_chunk.index[0], "canopy_cover"] == 0.65

    first_wkb = first_chunk["polygon_geometry_wkb"].tolist()
    second_wkb = second_chunk["polygon_geometry_wkb"].tolist()
    assert pd.isna(first_wkb[0])
    assert pd.isna(first_wkb[1])
    assert second_wkb == [b"\x01\x02", b"\x03\x04"]
