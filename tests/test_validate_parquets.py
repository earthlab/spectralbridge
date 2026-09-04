from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from spectralbridge import parquet_validation as validator


def test_validate_parquets_hard_and_soft(tmp_path: Path, capsys) -> None:
    good = tmp_path / "good.parquet"
    table = pa.table(
        {
            "lon": [0.0],
            "lat": [0.0],
            "stage_b001_wl0500nm": [0.1],
        }
    )
    pq.write_table(table, good)

    exit_code = validator.main([str(tmp_path)])
    output = capsys.readouterr()
    assert exit_code == 0
    assert "✅" in output.out

    bad = tmp_path / "bad.parquet"
    bad.write_text("not parquet", encoding="utf-8")

    exit_code = validator.main([str(tmp_path)])
    output = capsys.readouterr()
    assert exit_code == 1
    assert "❌ Issues found:" in output.out
    assert "bad.parquet" in output.out

    exit_code = validator.main(["--soft", str(tmp_path)])
    output = capsys.readouterr()
    assert exit_code == 0
    assert "❌ Issues found:" in output.out


def test_validate_parquets_per_stage_ordering(tmp_path: Path, capsys) -> None:
    interleaved = tmp_path / "interleaved.parquet"
    table = pa.table(
        {
            "lon": [0.0],
            "lat": [0.0],
            "stage_a_b001_wl0400nm": [0.1],
            "stage_b_b001_wl0300nm": [0.2],
            "stage_a_b002_wl0500nm": [0.3],
        }
    )
    pq.write_table(table, interleaved)

    exit_code = validator.main([str(tmp_path)])
    output = capsys.readouterr()
    assert exit_code == 0
    assert "✅" in output.out

    unsorted = tmp_path / "unsorted.parquet"
    table_unsorted = pa.table(
        {
            "lon": [0.0],
            "lat": [0.0],
            "stage_a_b001_wl0500nm": [0.1],
            "stage_a_b002_wl0400nm": [0.2],
        }
    )
    pq.write_table(table_unsorted, unsorted)

    exit_code = validator.main([str(tmp_path)])
    output = capsys.readouterr()
    assert exit_code == 1
    assert "unsorted.parquet" in output.out


def test_validate_parquets_accepts_stub_json(tmp_path: Path, capsys) -> None:
    stub = tmp_path / "stub.parquet"
    stub.write_text('{"columns": ["lon", "lat", "stage_b001_wl0500nm"]}', encoding="utf-8")

    exit_code = validator.main([str(tmp_path)])
    output = capsys.readouterr()
    assert exit_code == 0
    assert "✅" in output.out
