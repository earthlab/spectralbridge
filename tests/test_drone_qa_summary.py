from __future__ import annotations

import json
from pathlib import Path

import pytest

from spectralbridge.utils.qa_summary import render_drone_qa_report


@pytest.mark.parametrize(
    ("landsat_status", "with_neon"),
    ((None, False), ("ok", False), ("ok", True)),
)
def test_drone_summary_handles_optional_validation_layers(
    tmp_path: Path, landsat_status: str | None, with_neon: bool
) -> None:
    translation_json = tmp_path / "flight__translation_qa.json"
    translation_json.write_text(
        json.dumps(
            {
                "bands": [
                    {
                        "valid_translated_fraction": 0.95,
                        "median_relative_shift_percent": -7.5,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    file_audit = {
        "flight_stem": "NIWO_20260801",
        "input_source_path": str(tmp_path / "source.tif"),
        "prepared_h5_path": str(tmp_path / "working.h5"),
        "flags": {"topo_applied": True, "brdf_applied": True},
        "status": "success_qa_only_no_polygons",
        "translation_qa_paths": [str(translation_json)],
        "translation_products": [
            {
                "analysis_level": "site_balanced",
                "analysis_run_id": "bulk-run",
                "training_range_checks": {"2": {"status": "overlap"}},
            }
        ],
    }
    if landsat_status is not None:
        file_audit["landsat_comparison"] = {
            "status": landsat_status,
            "bands": [
                {"drone_vs_actual": {"rmse": 0.02, "correlation": 0.98}}
            ],
        }
    payload = {
        "run_id": "drone-run",
        "success_count": 1,
        "failed_other_count": 0,
        "comparison_neon_product": "neon.img" if with_neon else None,
        "files": [file_audit],
    }
    (tmp_path / "drone_qa_summary.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )

    result = render_drone_qa_report(tmp_path)

    assert result["status"] == "created"
    assert Path(result["summary_png"]).read_bytes().startswith(b"\x89PNG")
    assert Path(result["report_pdf"]).read_bytes().startswith(b"%PDF")
    assert result["source_rasters_opened"] is False
    metrics = result["metrics"]["files"][0]
    assert metrics["valid_pixel_fraction"] == pytest.approx(0.95)
    assert metrics["largest_translation_shift_percent"] == pytest.approx(7.5)
    assert metrics["landsat"]["status"] == (landsat_status or "not_requested")
    assert metrics["neon_status"] == ("included" if with_neon else "not supplied")

    reused = render_drone_qa_report(tmp_path)
    assert reused["status"] == "reused"


def test_corrupted_drone_report_is_regenerated_without_source_rasters(
    tmp_path: Path,
) -> None:
    (tmp_path / "drone_qa_summary.json").write_text(
        json.dumps({"run_id": "run", "files": []}), encoding="utf-8"
    )
    first = render_drone_qa_report(tmp_path)
    Path(first["report_pdf"]).write_bytes(b"broken")

    repaired = render_drone_qa_report(tmp_path)

    assert repaired["status"] == "created"
    assert Path(repaired["report_pdf"]).read_bytes().startswith(b"%PDF")

