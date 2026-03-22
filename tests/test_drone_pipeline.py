from __future__ import annotations

from pathlib import Path

import json

import pytest

from spectralbridge.pipelines import run_drone_pipeline
from spectralbridge.pipelines.drone import (
    DRONE_TARGET_BANDS,
    build_drone_output_paths,
    _prepare_drone_h5_working_copy,
    clean_name,
    derive_drone_flight_stem,
    resolve_band_map,
)

h5py = pytest.importorskip("h5py")


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


def test_derive_drone_flight_stem_uses_parent_package_folder() -> None:
    inner_name = "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    h5_a = (
        Path("/tmp")
        / "SPR1-06-28-23-ExportPackage"
        / inner_name
    )
    h5_b = (
        Path("/tmp")
        / "SPR2-06-28-23-ExportPackage"
        / inner_name
    )

    assert derive_drone_flight_stem(h5_a) == "SPR1_20230628"
    assert derive_drone_flight_stem(h5_b) == "SPR2_20230628"
    assert derive_drone_flight_stem(h5_a) != derive_drone_flight_stem(h5_b)


def test_build_drone_output_paths_isolates_per_flight_outputs(tmp_path: Path) -> None:
    paths_a = build_drone_output_paths(tmp_path / "out", flight_stem="SPR1_20230628")
    paths_b = build_drone_output_paths(tmp_path / "out", flight_stem="SPR2_20230628")

    assert paths_a["flight_dir"] != paths_b["flight_dir"]
    assert paths_a["working_h5"] != paths_b["working_h5"]
    assert paths_a["polygon_parquet"] != paths_b["polygon_parquet"]
    assert paths_a["qa_png"] != paths_b["qa_png"]
    assert paths_a["flight_dir"] == tmp_path / "out" / "SPR1_20230628"
    assert paths_b["flight_dir"] == tmp_path / "out" / "SPR2_20230628"


def test_run_drone_pipeline_skips_polygons_cleanly(tmp_path: Path, monkeypatch) -> None:
    h5_path = (
        tmp_path
        / "input"
        / "SPR1-06-28-23-ExportPackage"
        / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    )
    h5_path.parent.mkdir(parents=True, exist_ok=True)
    h5_path.write_bytes(b"fake-h5")

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._prepare_drone_h5_working_copy",
        lambda path, *, working_path, overwrite=False: (Path(path), False),
    )
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
    assert file_summary["flight_stem"] == "SPR1_20230628"
    assert file_summary["resolved_band_map"]["nir"]["index"] == 3
    assert file_summary["working_h5_filename"] == "SPR1_20230628__working.h5"
    assert file_summary["working_raster"] == "SPR1_20230628__envi.img"
    assert file_summary["corrected_raster"] == "SPR1_20230628__corrected.img"
    assert file_summary["polygon_filename"] is None
    assert file_summary["qa_plot_filename"] == "SPR1_20230628__qa.png"
    assert file_summary["qa_json_filename"] == "SPR1_20230628__qa.json"
    assert Path(file_summary["flight_dir"]) == tmp_path / "out" / "SPR1_20230628"
    assert Path(results["qa_summary_path"]).exists()


def test_run_drone_pipeline_with_polygons_and_merge(
    tmp_path: Path, monkeypatch
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    h5_a = (
        input_dir
        / "SPR1-06-28-23-ExportPackage"
        / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    )
    h5_b = (
        input_dir
        / "SPR2-06-28-23-ExportPackage"
        / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    )
    h5_a.parent.mkdir(parents=True, exist_ok=True)
    h5_b.parent.mkdir(parents=True, exist_ok=True)
    h5_a.write_bytes(b"a")
    h5_b.write_bytes(b"b")
    polygon_path = tmp_path / "plots.geojson"
    polygon_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._prepare_drone_h5_working_copy",
        lambda path, *, working_path, overwrite=False: (Path(path), False),
    )
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
        "SPR1_20230628__polygons.parquet",
        "SPR2_20230628__polygons.parquet",
    }
    assert {entry["merged_filename"] for entry in qa_files} == {"drone_merged.parquet"}
    assert {entry["qa_plot_filename"] for entry in qa_files} == {
        "SPR1_20230628__qa.png",
        "SPR2_20230628__qa.png",
    }
    assert {Path(entry["flight_dir"]).name for entry in qa_files} == {
        "SPR1_20230628",
        "SPR2_20230628",
    }


def test_prepare_drone_h5_working_copy_patches_only_working_copy(tmp_path: Path) -> None:
    source_h5 = tmp_path / "source.h5"
    working_h5 = tmp_path / "prepared" / "source__working.h5"

    with h5py.File(source_h5, "w") as h5_file:
        dataset = h5_file.create_group("NIWO").create_group("Reflectance").create_dataset(
            "Reflectance_Data",
            data=[[[0.1, 0.2]]],
        )
        assert "Data_Ignore_Value" not in dataset.attrs

    prepared_path, patched = _prepare_drone_h5_working_copy(
        source_h5,
        working_path=working_h5,
    )

    assert prepared_path == working_h5
    assert patched is True
    assert prepared_path.exists()

    with h5py.File(source_h5, "r") as h5_file:
        source_attrs = h5_file["NIWO/Reflectance/Reflectance_Data"].attrs
        assert "Data_Ignore_Value" not in source_attrs
        assert "_FillValue" not in source_attrs

    with h5py.File(prepared_path, "r") as h5_file:
        attrs = h5_file["NIWO/Reflectance/Reflectance_Data"].attrs
        assert float(attrs["Data_Ignore_Value"]) == pytest.approx(-9999.0)
        assert float(attrs["_FillValue"]) == pytest.approx(-9999.0)
        assert float(attrs["NoData"]) == pytest.approx(-9999.0)
        assert float(attrs["no_data"]) == pytest.approx(-9999.0)
        assert float(attrs["nodata"]) == pytest.approx(-9999.0)


def test_run_drone_pipeline_prepares_working_copy_before_neoncube(
    tmp_path: Path, monkeypatch
) -> None:
    h5_path = (
        tmp_path
        / "input"
        / "SPR1-06-28-23-ExportPackage"
        / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    )
    h5_path.parent.mkdir(parents=True, exist_ok=True)
    h5_path.write_bytes(b"fake-h5")

    prepared_path = tmp_path / "out" / "SPR1_20230628" / "SPR1_20230628__working.h5"
    helper_calls: list[tuple[Path, Path, bool]] = []
    cube_calls: list[Path] = []

    def _fake_prepare(path, *, working_path, overwrite=False):
        helper_calls.append((Path(path), Path(working_path), overwrite))
        prepared_path.parent.mkdir(parents=True, exist_ok=True)
        prepared_path.write_bytes(b"prepared-h5")
        return prepared_path, True

    class _RecordingCube(_FakeCube):
        def __init__(self, h5_path: str | Path):
            cube_calls.append(Path(h5_path))
            super().__init__(h5_path)

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._prepare_drone_h5_working_copy",
        _fake_prepare,
    )
    monkeypatch.setattr("spectralbridge.pipelines.drone.NeonCube", _RecordingCube)
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
        h5_path.parent,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    assert results["processed"] == [str(h5_path)]
    assert helper_calls == [(h5_path, prepared_path, False)]
    assert cube_calls
    assert all(call == prepared_path for call in cube_calls)
    assert all(call != h5_path for call in cube_calls)
    file_summary = results["qa_summary"]["files"][0]
    assert file_summary["flight_stem"] == "SPR1_20230628"
    assert Path(file_summary["flight_dir"]) == tmp_path / "out" / "SPR1_20230628"
    assert Path(file_summary["qa_plot_path"]) == (
        tmp_path / "out" / "SPR1_20230628" / "SPR1_20230628__qa.png"
    )
