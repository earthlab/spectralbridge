from __future__ import annotations

from pathlib import Path

import json

from spectralbridge.pipelines import run_drone_pipeline
from spectralbridge.pipelines.drone import (
    DRONE_TARGET_BANDS,
    clean_name,
    resolve_band_map,
)


class _FakeCube:
    def __init__(self, h5_path: str | Path):
        self.h5_path = Path(h5_path)
        self.wavelengths = [440.0, 561.0, 649.0, 861.5]
        self.fwhm = [10.0, 10.0, 10.0, 10.0]
        self.no_data = -9999.0
        self.scale_factor = 1.0
        self.lines = 2
        self.columns = 2
        self.bands = 4
        self.wavelength_units = "nanometers"
        self.transform = (0.0, 1.0, 0.0, 2.0, 0.0, -1.0)
        self.projection_wkt = "EPSG:32613"

    def build_envi_header(self):
        return {"samples": self.columns, "lines": self.lines, "bands": self.bands}

    def chunk_count(self, *, chunk_y: int, chunk_x: int) -> int:
        return 1

    def iter_chunks(self, *, chunk_y: int, chunk_x: int):
        yield 0, self.lines, 0, self.columns, [
            [[0.1, 0.2, 0.3, 0.4], [0.2, 0.3, 0.4, 0.5]],
            [[0.3, 0.4, 0.5, 0.6], [0.4, 0.5, 0.6, 0.7]],
        ]

    def get_ancillary(self, name: str, radians: bool = True):
        return [[1.0, 1.0], [1.0, 1.0]]


class _FakeWriter:
    def __init__(self, stem, header):
        self.stem = Path(stem)
        self.stem.with_suffix(".hdr").write_text(json.dumps(header), encoding="utf-8")
        self._chunks = []

    def write_chunk(self, chunk, ys: int, xs: int):
        self._chunks.append((ys, xs, chunk))

    def close(self):
        self.stem.with_suffix(".img").write_bytes(b"fake-img")


class _FakeReporter:
    def __init__(self, *args, **kwargs):
        pass

    def update(self, *_args, **_kwargs):
        return None

    def close(self):
        return None


def _fake_render_drone_panel(**kwargs):
    output_png = Path(kwargs["output_png"])
    output_png.write_text("png", encoding="utf-8")
    output_png.with_suffix(".json").write_text("{}", encoding="utf-8")
    return output_png, {
        "nodata": {"raw_nodata_pct": 1.0, "corrected_nodata_pct": 2.0},
        "polygon": {"path": str(kwargs.get("polygon_path")) if kwargs.get("polygon_path") else None},
        "merged_preview": {"path": str(kwargs.get("merged_path")) if kwargs.get("merged_path") else None},
    }


def test_resolve_band_map_is_wavelength_driven() -> None:
    band_map = resolve_band_map([441.0, 558.0, 652.0, 860.0], DRONE_TARGET_BANDS)
    assert band_map["blue"]["index"] == 0
    assert band_map["green"]["index"] == 1
    assert band_map["red"]["index"] == 2
    assert band_map["nir"]["index"] == 3


def test_clean_name_preserves_provenance_minimally() -> None:
    assert clean_name("Drone Flight #01") == "Drone_Flight_01"
    assert clean_name("drone.flight-01") == "drone.flight-01"


def test_run_drone_pipeline_skips_polygons_cleanly(tmp_path: Path, monkeypatch) -> None:
    h5_path = tmp_path / "input" / "Drone Flight #01.h5"
    h5_path.parent.mkdir(parents=True, exist_ok=True)
    h5_path.write_bytes(b"fake-h5")

    monkeypatch.setattr("spectralbridge.pipelines.drone.NeonCube", _FakeCube)
    monkeypatch.setattr("spectralbridge.pipelines.drone.EnviWriter", _FakeWriter)
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.TileProgressReporter", _FakeReporter
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )
    monkeypatch.setattr(
        "spectralbridge.qa_plots.render_drone_panel",
        _fake_render_drone_panel,
    )

    results = run_drone_pipeline(
        tmp_path / "input", output_dir=tmp_path / "out", apply_topo=False
    )

    assert results["platform"] == "drone"
    assert results["processed"] == [str(h5_path)]
    assert results["outputs"] == []
    assert results["merged"] is None
    qa_summary = results["qa_summary"]
    assert qa_summary["platform"] == "drone"
    assert qa_summary["convolution"] == "skipped"
    file_summary = qa_summary["files"][0]
    assert file_summary["resolved_band_map"]["nir"]["index"] == 3
    assert file_summary["working_raster"] == "Drone_Flight_01__envi.img"
    assert file_summary["corrected_raster"] == "Drone_Flight_01__corrected.img"
    assert file_summary["polygon_filename"] is None
    assert file_summary["qa_plot_filename"] == "Drone_Flight_01__qa.png"
    assert file_summary["qa_json_filename"] == "Drone_Flight_01__qa.json"
    assert Path(results["qa_summary_path"]).exists()


def test_run_drone_pipeline_with_polygons_and_merge(
    tmp_path: Path, monkeypatch
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    h5_a = input_dir / "drone-a.h5"
    h5_b = input_dir / "drone-b.h5"
    h5_a.write_bytes(b"a")
    h5_b.write_bytes(b"b")
    polygon_path = tmp_path / "plots.geojson"
    polygon_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("spectralbridge.pipelines.drone.NeonCube", _FakeCube)
    monkeypatch.setattr("spectralbridge.pipelines.drone.EnviWriter", _FakeWriter)
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.TileProgressReporter", _FakeReporter
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )

    def _fake_build_index(**kwargs):
        path = kwargs["output_path"]
        path.write_text("index", encoding="utf-8")
        return path

    def _fake_extract(
        envi_img, envi_hdr, polygon_index_path, output_parquet_path, overwrite=False
    ):
        output_parquet_path.write_text(output_parquet_path.stem, encoding="utf-8")
        return output_parquet_path

    def _fake_merge(outputs, output_path, overwrite=False):
        output_path.write_text("\n".join(outputs), encoding="utf-8")
        return output_path

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._build_polygon_pixel_index_for_raster",
        _fake_build_index,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.extract_polygon_parquet_from_envi",
        _fake_extract,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._merge_drone_polygon_outputs", _fake_merge
    )
    monkeypatch.setattr(
        "spectralbridge.qa_plots.render_drone_panel",
        _fake_render_drone_panel,
    )

    results = run_drone_pipeline(
        input_dir,
        polygon_path=polygon_path,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    assert len(results["processed"]) == 2
    assert len(results["outputs"]) == 2
    assert results["merged"] == str(tmp_path / "out" / "drone_merged.parquet")
    assert Path(results["merged"]).exists()
    qa_files = results["qa_summary"]["files"]
    assert {entry["polygon_filename"] for entry in qa_files} == {
        "drone-a__polygons.parquet",
        "drone-b__polygons.parquet",
    }
    assert {entry["merged_filename"] for entry in qa_files} == {"drone_merged.parquet"}
    assert {entry["qa_plot_filename"] for entry in qa_files} == {
        "drone-a__qa.png",
        "drone-b__qa.png",
    }
