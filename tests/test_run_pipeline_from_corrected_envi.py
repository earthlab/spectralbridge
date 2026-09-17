"""Contract tests for the resume-from-corrected-ENVI entry point."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_pipeline_from_corrected_envi.py"

FLIGHT_ID = "NEON_D10_R10C_DP1_L005-1_20210915_directional_reflectance"


def _load_script_module():
    spec = importlib.util.spec_from_file_location(
        "run_pipeline_from_corrected_envi", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


script = _load_script_module()


def _write_envi_pair(img: Path, hdr: Path, *, tag: str) -> None:
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(f"{tag}-img".encode("utf-8"))
    hdr.write_text(f"ENVI\ndescription = {{{tag}}}\n", encoding="utf-8")


def _make_flight(tmp_path: Path, *, raw: bool, corrected: bool, json_ok: bool):
    """Create a flight dir with the requested artefacts and return resolved paths."""

    base_folder = tmp_path / "NEON_TM_5"
    probe = script.inspect_flight_inputs(base_folder=base_folder, flight_id=FLIGHT_ID)
    probe.flight_dir.mkdir(parents=True, exist_ok=True)

    if corrected:
        _write_envi_pair(probe.corrected_img, probe.corrected_hdr, tag="corrected")
    if raw:
        _write_envi_pair(probe.raw_img, probe.raw_hdr, tag="raw")
    if json_ok:
        probe.correction_json.write_text(
            json.dumps({"geometry": {"solar_zn": 30.0}}), encoding="utf-8"
        )

    return base_folder, probe


def test_inspect_flight_inputs_reports_available_artifacts(tmp_path: Path) -> None:
    base_folder, _ = _make_flight(tmp_path, raw=False, corrected=True, json_ok=False)

    inputs = script.inspect_flight_inputs(base_folder=base_folder, flight_id=FLIGHT_ID)

    assert inputs.corrected_envi_valid is True
    assert inputs.raw_envi_valid is False
    assert inputs.correction_json_valid is False
    assert inputs.h5_present is False


def test_stage_requires_a_valid_corrected_envi_pair(tmp_path: Path) -> None:
    base_folder, _ = _make_flight(tmp_path, raw=True, corrected=False, json_ok=True)

    with pytest.raises(FileNotFoundError, match="No valid corrected ENVI pair"):
        script.stage_corrected_envi_flight(base_folder=base_folder, flight_id=FLIGHT_ID)


def test_stage_reuses_genuine_raw_envi_and_correction_json(tmp_path: Path) -> None:
    base_folder, probe = _make_flight(tmp_path, raw=True, corrected=True, json_ok=True)
    original_raw = probe.raw_img.read_bytes()
    original_json = probe.correction_json.read_text(encoding="utf-8")

    inputs = script.stage_corrected_envi_flight(
        base_folder=base_folder, flight_id=FLIGHT_ID
    )

    assert inputs.substitutions == []
    assert inputs.raw_envi_independent_of_corrected is True
    assert probe.raw_img.read_bytes() == original_raw
    assert probe.correction_json.read_text(encoding="utf-8") == original_json

    manifest = json.loads(
        (
            probe.flight_dir / f"{FLIGHT_ID}{script.RESUME_MANIFEST_SUFFIX}"
        ).read_text(encoding="utf-8")
    )
    assert manifest["substitutions"] == []
    assert manifest["raw_envi_independent_of_corrected"] is True
    assert manifest["notes"] == []


def test_stage_substitutes_missing_raw_envi_and_records_provenance(
    tmp_path: Path,
) -> None:
    base_folder, probe = _make_flight(tmp_path, raw=False, corrected=True, json_ok=False)

    inputs = script.stage_corrected_envi_flight(
        base_folder=base_folder, flight_id=FLIGHT_ID
    )

    assert sorted(inputs.substitutions) == [
        "correction_json_stub",
        "raw_envi_from_corrected",
    ]
    assert inputs.raw_envi_independent_of_corrected is False
    assert probe.raw_img.read_bytes() == probe.corrected_img.read_bytes()

    stub = json.loads(probe.correction_json.read_text(encoding="utf-8"))
    assert stub["spectralbridge_resume_stub"] is True
    assert stub["flight_stem"] == FLIGHT_ID
    assert "geometry" not in stub

    manifest = json.loads(
        (
            probe.flight_dir / f"{FLIGHT_ID}{script.RESUME_MANIFEST_SUFFIX}"
        ).read_text(encoding="utf-8")
    )
    assert manifest["raw_envi_independent_of_corrected"] is False
    assert manifest["substitutions"] == [
        "correction_json_stub",
        "raw_envi_from_corrected",
    ]
    assert any("stand-in" in note for note in manifest["notes"])


def test_stage_can_refuse_to_substitute_raw_envi(tmp_path: Path) -> None:
    base_folder, _ = _make_flight(tmp_path, raw=False, corrected=True, json_ok=True)

    with pytest.raises(FileNotFoundError, match="Raw ENVI missing"):
        script.stage_corrected_envi_flight(
            base_folder=base_folder,
            flight_id=FLIGHT_ID,
            allow_raw_envi_substitute=False,
        )


def test_dry_run_reports_without_writing_anything(tmp_path: Path) -> None:
    base_folder, probe = _make_flight(tmp_path, raw=False, corrected=True, json_ok=False)

    inputs = script.stage_corrected_envi_flight(
        base_folder=base_folder, flight_id=FLIGHT_ID, dry_run=True
    )

    assert sorted(inputs.substitutions) == [
        "correction_json_stub",
        "raw_envi_from_corrected",
    ]
    assert not probe.raw_img.exists()
    assert not probe.correction_json.exists()
    assert not (
        probe.flight_dir / f"{FLIGHT_ID}{script.RESUME_MANIFEST_SUFFIX}"
    ).exists()


def test_run_patches_download_stage_and_restores_it(tmp_path: Path, monkeypatch) -> None:
    base_folder, _ = _make_flight(tmp_path, raw=True, corrected=True, json_ok=True)

    from spectralbridge.pipelines import pipeline

    original_download = pipeline.stage_download_h5
    captured: dict[str, object] = {}

    def _fake_go_forth(**kwargs):
        # The patch must be active while the pipeline runs, not just around it.
        captured["kwargs"] = kwargs
        captured["download_patched"] = pipeline.stage_download_h5 is not original_download
        captured["download_result"] = pipeline.stage_download_h5(
            base_folder=kwargs["base_folder"],
            site_code=kwargs["site_code"],
            year_month=kwargs["year_month"],
            product_code=kwargs["product_code"],
            flight_stem=kwargs["flight_lines"][0],
        )
        return "done"

    monkeypatch.setattr(pipeline, "go_forth_and_multiply", _fake_go_forth)

    result = script.run(
        flight_id=FLIGHT_ID,
        base_folder=base_folder,
        extraction_mode="full",
    )

    assert result == "done"
    assert captured["download_patched"] is True
    assert Path(captured["download_result"]).name == f"{FLIGHT_ID}.h5"
    assert pipeline.stage_download_h5 is original_download

    kwargs = captured["kwargs"]
    assert kwargs["flight_lines"] == [FLIGHT_ID]
    assert kwargs["extraction_mode"] == "full"
    assert kwargs["polygon_path"] is None
    assert Path(kwargs["base_folder"]) == base_folder


def test_run_requires_polygon_path_in_polygon_mode(tmp_path: Path, monkeypatch) -> None:
    base_folder, _ = _make_flight(tmp_path, raw=True, corrected=True, json_ok=True)

    from spectralbridge.pipelines import pipeline

    monkeypatch.setattr(
        pipeline, "go_forth_and_multiply", lambda **_kwargs: pytest.fail("should not run")
    )

    with pytest.raises(ValueError, match="requires --polygon-path"):
        script.run(
            flight_id=FLIGHT_ID,
            base_folder=base_folder,
            extraction_mode="polygon",
            polygon_path=None,
        )
