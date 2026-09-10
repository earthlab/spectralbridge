from __future__ import annotations

import json
from pathlib import Path

import duckdb

from spectralbridge.bulk.analyses.streaming_translation import (
    run_streaming_translation_analyses,
)
from spectralbridge.bulk.models import BulkAnalysisPaths
from spectralbridge.bulk.registry import TranslationPair


def _statistics_row() -> dict[str, object]:
    return {
        "flightline_id": "NIWO_20260801",
        "site": "NIWO",
        "acquisition_date": "2026-08-01",
        "translation_pair": "fixture_pair",
        "source_sensor": "MicaSense fixture",
        "target_sensor": "Landsat fixture",
        "band_index": 1,
        "source_band_index": 1,
        "target_band_index": 1,
        "x_column": "source_b1",
        "y_column": "target_b1",
        "n": 3,
        "mean_x": 2.0,
        "mean_y": 3.0,
        "m2_x": 2.0,
        "m2_y": 2.0,
        "c_xy": 2.0,
        "x_min": 1.0,
        "x_max": 3.0,
        "y_min": 2.0,
        "y_max": 4.0,
    }


def test_compact_coefficient_and_loso_stage_reuses_valid_outputs(tmp_path: Path) -> None:
    paths = BulkAnalysisPaths(tmp_path)
    paths.ensure_directories()
    pair = TranslationPair(
        key="fixture_pair",
        source_sensor="MicaSense fixture",
        target_sensor="Landsat fixture",
        matching_group="fixture",
        band_pairs=((1, 1),),
    )
    con = duckdb.connect()
    try:
        created, created_loso = run_streaming_translation_analyses(
            con,
            paths,
            analysis_run_id="run",
            statistics_rows=[_statistics_row()],
            flightlines=[],
            minimum_reflectance=0.0,
            chunk_size=32,
            translation_pairs=[pair],
        )
        reused, reused_loso = run_streaming_translation_analyses(
            con,
            paths,
            analysis_run_id="run",
            statistics_rows=[_statistics_row()],
            flightlines=[],
            minimum_reflectance=0.0,
            chunk_size=32,
            translation_pairs=[pair],
        )
        invalidated, invalidated_loso = run_streaming_translation_analyses(
            con,
            paths,
            analysis_run_id="run",
            statistics_rows=[_statistics_row()],
            flightlines=[],
            minimum_reflectance=0.1,
            chunk_size=32,
            translation_pairs=[pair],
        )
    finally:
        con.close()

    assert created["status"] == "created"
    assert created_loso["status"] == "created"
    assert reused["status"] == "reused"
    assert reused_loso["status"] == "reused"
    assert invalidated["status"] == "created"
    assert invalidated_loso["status"] == "created"
    metadata = json.loads(
        (tmp_path / "analyses" / "sensor_translation" / "analysis_metadata.json").read_text()
    )
    assert metadata["stage_signature_sha256"] == invalidated["stage_signature_sha256"]
