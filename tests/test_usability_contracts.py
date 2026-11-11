"""Researcher entry points must preserve scientific metadata and explain failures."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_example(name):
    spec = importlib.util.spec_from_file_location(
        "audit_example", ROOT / "examples" / name
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resampled_header_remains_accepted_by_physical_library_gate(tmp_path):
    from spectralbridge.pipelines.pipeline import _build_resample_header_text
    from spectralbridge.envi import hdr_to_dict
    from spectralbridge.radiometry import Radiometry, require_library_header

    radiometry = Radiometry(
        0.0001, 0.0, "VALID", "Synthetic teaching calibration with spaces"
    )
    header = {
        **radiometry.header(),
        "brdf status": "NOT_REQUESTED",
        "description": "Synthetic convolved sensor bands",
    }
    path = tmp_path / "target.hdr"
    path.write_text(_build_resample_header_text(header))
    recovered = hdr_to_dict(path)
    require_library_header(recovered)
    assert Radiometry.from_header(recovered).record() == radiometry.record()


@pytest.mark.parametrize("script", ["run_neon_pipeline.py", "run_drone_pipeline.py"])
@pytest.mark.parametrize("content", [None, "not JSON", "[]"])
def test_configuration_failure_is_actionable_without_traceback(
    tmp_path, script, content
):
    path = tmp_path / "config.json"
    if content is not None:
        path.write_text(content)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples" / script),
            "--config",
            str(path),
            "--check",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "configuration" in result.stderr.lower() and "Traceback" not in result.stderr
    assert str(path) in result.stderr


def test_drone_json_accepts_existing_calibration_and_timezone_api(tmp_path):
    example = load_example("run_drone_pipeline.py")
    config = {
        "input_h5_dir": "source.tif",
        "output_dir": "outputs",
        "radiometry": {
            "scale": 0.0001,
            "offset": 0.0,
            "status": "VALID",
            "provenance": "Synthetic fixture",
        },
        "drone_manifest_timezone": "America/Denver",
        "raise_on_incomplete": False,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"schema_version": 1, "pipeline": config}))
    loaded = example.load_config(path)
    assert loaded["radiometry"] == config["radiometry"]
    assert loaded["drone_manifest_timezone"] == "America/Denver"


def test_drone_example_returns_failure_for_scientific_block(
    tmp_path, monkeypatch, capsys
):
    import spectralbridge

    example = load_example("run_drone_pipeline.py")
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pipeline": {
                    "input_h5_dir": str(tmp_path),
                    "output_dir": str(tmp_path / "out"),
                    "raise_on_incomplete": False,
                },
            }
        )
    )
    monkeypatch.setattr(
        spectralbridge,
        "run_drone_pipeline",
        lambda **kwargs: {
            "status": "incomplete",
            "processed": [],
            "failed": [],
            "blocked": [{"error": "Radiometry UNSUPPORTED"}],
            "qa_summary_path": "out/drone_qa_summary.json",
        },
    )
    assert example.main(["--config", str(path)]) == 1
    assert "Blocked: 1" in capsys.readouterr().out


def test_offline_example_persists_interpretable_outputs_without_overwriting(tmp_path):
    output = tmp_path / "lesson"
    script = ROOT / "examples/scientific_workflows_offline.py"
    result = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads((output / "example_summary.json").read_text())
    assert report["atlas_plants"] == 2 and report["identity_RMSE"] == 0
    assert (output / "teaching.parquet").is_file()
    before = (output / "example_summary.json").read_bytes()
    second = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output)],
        capture_output=True,
        text=True,
    )
    assert second.returncode == 2 and "fresh" in second.stderr.lower()
    assert (output / "example_summary.json").read_bytes() == before


@pytest.mark.parametrize(
    "module,expected",
    [
        ("spectralbridge.cli.pipeline_cli", "NEON_API_TOKEN"),
        ("spectralbridge.cli.bulk_cli", "--preflight-only"),
        ("spectralbridge.cli.drone_production_cli", "gocmd login"),
    ],
)
def test_primary_cli_help_shows_start_and_guide(module, expected):
    import importlib

    cli = importlib.import_module(module)
    parser = cli._parser() if hasattr(cli, "_parser") else cli._build_parser()
    help_text = parser.format_help()
    assert expected in help_text and "Guide: https://earthlab.github.io/" in help_text


def test_palette_diagnostic_works_with_current_duckdb_connection(tmp_path):
    import duckdb
    import pyarrow as pa
    import pyarrow.parquet as pq
    from spectralbridge.sensor_panel_plots import _palette_fraction_by_column

    source = tmp_path / "bands.parquet"
    pq.write_table(pa.table({"band": [1.0, 2.0, 0.5, None]}), source)
    with duckdb.connect() as connection:
        result = _palette_fraction_by_column(connection, source, ["band"])
        assert connection.sql("SELECT 42").fetchall() == [(42,)]
    assert result["band"] == pytest.approx(2 / 3)
