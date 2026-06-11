from __future__ import annotations

from datetime import datetime
from pathlib import Path

import json

import duckdb
import pytest
import numpy as np
import pandas as pd
import spectralbridge.qa_plots as qa_plots

from spectralbridge.pipelines import run_drone_pipeline
from spectralbridge.pipelines.drone import (
    DRONE_TARGET_BANDS,
    DroneCorrectionUnavailableError,
    _discover_drone_input_sources,
    _enrich_drone_polygon_parquet_with_index,
    _export_csv_copy_from_parquet,
    _prepare_drone_source_working_h5,
    apply_drone_corrections,
    build_drone_output_paths,
    collect_drone_spatial_diagnostics,
    convert_drone_tiff_to_h5,
    _prepare_drone_h5_working_copy,
    clean_name,
    derive_drone_flight_stem,
    load_drone_manifest,
    lookup_flight_datetime,
    resolve_band_map,
    save_drone_overlay_debug_plot,
    summarize_drone_h5_solar_geometry,
)
from spectralbridge.utils.paths import get_package_data_path
from spectralbridge.qa_plots import (
    _classify_drone_scene,
    _correction_report,
    _deterministic_drone_valid_sample,
    _summarize_full_diff,
    _summarize_sample_support,
    _render_drone_band_fidelity,
    _render_drone_correction_magnitude,
    _render_delta,
    _render_drone_merged_preview,
    render_drone_panel,
)

h5py = pytest.importorskip("h5py")
geopandas = pytest.importorskip("geopandas")
rasterio = pytest.importorskip("rasterio")
shapely_geometry = pytest.importorskip("shapely.geometry")
from_origin = rasterio.transform.from_origin
Polygon = shapely_geometry.Polygon


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


class _RecordingCube(_FakeCube):
    def __init__(self, h5_path: str | Path):
        super().__init__(h5_path)
        self.chunk_args: list[tuple[int, int]] = []

    def chunk_count(self, *, chunk_y: int, chunk_x: int) -> int:
        self.chunk_args.append((chunk_y, chunk_x))
        return 1

    def iter_chunks(self, *, chunk_y: int, chunk_x: int):
        self.chunk_args.append((chunk_y, chunk_x))
        yield from super().iter_chunks(chunk_y=chunk_y, chunk_x=chunk_x)


class _FakeWriter:
    last_header = None
    last_chunks = None

    def __init__(self, stem, header):
        self.stem = Path(stem)
        self.stem.with_suffix(".hdr").write_text(json.dumps(header), encoding="utf-8")
        self._chunks = []
        type(self).last_header = header
        type(self).last_chunks = self._chunks

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


class _FakeTable:
    def auto_set_font_size(self, *_args, **_kwargs):
        return None

    def set_fontsize(self, *_args, **_kwargs):
        return None

    def scale(self, *_args, **_kwargs):
        return None


class _FakeAxes:
    transAxes = object()

    def axis(self, *_args, **_kwargs):
        return None

    def set_title(self, *_args, **_kwargs):
        return None

    def text(self, *_args, **_kwargs):
        return None

    def table(self, *args, **kwargs):
        return _FakeTable()


def _write_envi_pair(base_path: Path, data: np.ndarray, wavelengths: list[float]) -> None:
    data = np.asarray(data, dtype=np.float32)
    img_path = base_path.with_suffix(".img")
    hdr_path = base_path.with_suffix(".hdr")
    data.tofile(img_path)
    header_lines = [
        "ENVI",
        f"samples = {data.shape[2]}",
        f"lines = {data.shape[1]}",
        f"bands = {data.shape[0]}",
        "data type = 4",
        "interleave = bsq",
        "byte order = 0",
        "wavelength units = Nanometers",
        "fwhm = {" + ", ".join("10" for _ in wavelengths) + "}",
        "wavelength = {" + ", ".join(f"{w}" for w in wavelengths) + "}",
    ]
    hdr_path.write_text("\n".join(header_lines), encoding="utf-8")


def _patch_basic_drone_runtime(monkeypatch) -> None:
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
        "spectralbridge.pipelines.drone._has_required_ancillary",
        lambda cube, names: True,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_topo_correct",
        lambda cube, chunk, ys, ye, xs, xe: np.asarray(chunk, dtype=np.float32),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_brdf_correct",
        lambda cube, chunk, ys, ye, xs, xe, coeff_path=None: np.asarray(
            chunk, dtype=np.float32
        ),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.fit_and_save_brdf_model",
        lambda cube, out_dir: Path(out_dir) / "coeffs.json",
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )
    monkeypatch.setattr(
        "spectralbridge.qa_plots.render_drone_panel",
        _fake_render_drone_panel,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.summarize_drone_h5_solar_geometry",
        lambda h5_path: {
            "solar_geometry_source": "raster",
            "acquisition_datetime_used": None,
            "solar_zenith_mean": 45.0,
            "solar_zenith_min": 45.0,
            "solar_zenith_max": 45.0,
            "solar_azimuth_mean": 180.0,
            "solar_azimuth_min": 180.0,
            "solar_azimuth_max": 180.0,
        },
    )


def _fake_render_drone_panel(**kwargs):
    output_png = Path(kwargs["output_png"])
    output_png.write_text("png", encoding="utf-8")
    output_png.with_suffix(".json").write_text("{}", encoding="utf-8")
    return output_png, {
        "nodata": {"raw_nodata_pct": 1.0, "corrected_nodata_pct": 2.0},
        "polygon": {"path": str(kwargs.get("polygon_path")) if kwargs.get("polygon_path") else None},
        "merged_preview": {"path": str(kwargs.get("merged_path")) if kwargs.get("merged_path") else None},
    }


def _fake_csv_export(parquet_path, csv_path=None, *, overwrite=False):
    target = Path(csv_path) if csv_path is not None else Path(parquet_path).with_suffix(".csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("csv", encoding="utf-8")
    return target


def _fake_polygon_enrichment(parquet_path, polygon_index_path, *, overwrite=True):
    return Path(parquet_path)


def _write_test_raster(
    path: Path,
    *,
    crs: str = "EPSG:32613",
    transform=None,
    nodata: float = -9999.0,
) -> Path:
    transform = transform or from_origin(500000.0, 4100000.0, 10.0, 10.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(np.ones((4, 4), dtype="float32"), 1)
    return path


def _write_test_multiband_raster(
    path: Path,
    *,
    count: int = 10,
    crs: str = "EPSG:32613",
    transform=None,
    nodata: float = -9999.0,
) -> Path:
    transform = transform or from_origin(500000.0, 4100000.0, 10.0, 10.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.stack(
        [
            np.full((4, 4), 0.1 + idx * 0.01, dtype="float32")
            for idx in range(count)
        ],
        axis=0,
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=count,
        dtype="float32",
        crs=crs,
        transform=transform,
        nodata=nodata,
    ) as dst:
        dst.write(data)
    return path


def _write_test_polygons(path: Path, *, crs: str, polygons: list[Polygon]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf = geopandas.GeoDataFrame(
        {"name": [f"poly_{idx}" for idx in range(len(polygons))]},
        geometry=polygons,
        crs=crs,
    )
    gdf.to_file(path, driver="GeoJSON")
    return path


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


def test_discover_drone_input_sources_prefers_h5_and_skips_ancillary_tiffs(
    tmp_path: Path,
) -> None:
    package = tmp_path / "input" / "SPR1-06-28-23-ExportPackage"
    package.mkdir(parents=True, exist_ok=True)
    h5_path = package / "aligned_orthomosaic.h5"
    tif_path = package / "aligned_orthomosaic.tif"
    slope_path = package / "slope.tif"
    h5_path.write_bytes(b"fake-h5")
    tif_path.write_bytes(b"fake-tif")
    slope_path.write_bytes(b"fake-slope")

    sources = _discover_drone_input_sources(tmp_path / "input")

    assert len(sources) == 1
    assert sources[0].source_type == "h5"
    assert sources[0].source_path == h5_path
    assert sources[0].flight_stem == "SPR1_20230628"


def test_run_drone_pipeline_reports_empty_input_discovery(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_dir = tmp_path / "empty_inputs"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    results = run_drone_pipeline(
        input_h5_dir=input_dir,
        output_dir=output_dir,
        apply_topo=False,
        apply_brdf=False,
    )

    captured = capsys.readouterr()
    summary = results["qa_summary"]
    assert "No supported drone inputs discovered" in captured.err
    assert summary["discovered_total"] == 0
    assert summary["attempted_total"] == 0
    assert summary["input_discovery_status"] == "no_supported_drone_inputs_found"
    assert summary["input_source_path"] == str(input_dir)
    assert summary["input_source_path_exists"] is True
    assert summary["input_source_path_type"] == "directory"
    assert summary["supported_input_extensions"] == [".h5", ".tif", ".tiff"]
    assert "input_h5_dir" in summary["skip_reason"]

    qa_summary = json.loads(Path(results["qa_summary_path"]).read_text())
    assert qa_summary["input_discovery_status"] == "no_supported_drone_inputs_found"
    assert qa_summary["input_source_path_resolved"] == str(input_dir.resolve())


def test_run_drone_pipeline_skips_polygons_cleanly(tmp_path: Path, monkeypatch) -> None:
    h5_path = (
        tmp_path
        / "input"
        / "SPR1-06-28-23-ExportPackage"
        / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    )
    h5_path.parent.mkdir(parents=True, exist_ok=True)
    h5_path.write_bytes(b"fake-h5")

    _patch_basic_drone_runtime(monkeypatch)

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
    assert file_summary["status"] == "success_qa_only_no_polygons"
    assert file_summary["resolved_band_map"]["nir"]["index"] == 3
    assert file_summary["working_h5_filename"] == "SPR1_20230628__working.h5"
    assert file_summary["working_raster"] == "SPR1_20230628__envi.img"
    assert file_summary["corrected_raster"] == "SPR1_20230628__corrected.img"
    assert file_summary["polygon_filename"] is None
    assert file_summary["qa_plot_filename"] == "SPR1_20230628__qa.png"
    assert file_summary["qa_json_filename"] == "SPR1_20230628__qa.json"
    assert file_summary["flags"]["topo_requested"] is False
    assert file_summary["flags"]["brdf_requested"] is True
    assert file_summary["flags"]["brdf_applied"] is True
    assert file_summary["polygon_extraction_attempted"] is False
    assert file_summary["polygon_extraction_ran"] is False
    assert file_summary["polygon_extraction_skipped_reason"] == "no polygons provided"
    assert Path(file_summary["flight_dir"]) == tmp_path / "out" / "SPR1_20230628"
    assert Path(results["qa_summary_path"]).exists()
    assert qa_summary["success_count"] == 1
    assert qa_summary["success_qa_only_no_polygons_count"] == 1


def test_run_drone_pipeline_accepts_tiff_sources(tmp_path: Path, monkeypatch) -> None:
    tif_path = (
        tmp_path
        / "input"
        / "SPR1-06-28-23-ExportPackage"
        / "aligned_orthomosaic.tif"
    )
    tif_path.parent.mkdir(parents=True, exist_ok=True)
    tif_path.write_bytes(b"fake-tif")
    manifest_path = tmp_path / "manifest.csv"
    manifest_path.write_text(
        "Plot,Day of data collection,Mean Time of data collection (24 hr clock)\n"
        "SPR1,2023-06-28,19:53:07\n",
        encoding="utf-8",
    )

    _patch_basic_drone_runtime(monkeypatch)

    created_paths: list[Path] = []
    prepare_kwargs: list[dict[str, object]] = []

    def _fake_prepare(
        source_path,
        *,
        source_type,
        working_path,
        overwrite=False,
        **_kwargs,
    ):
        prepared = Path(working_path)
        prepared.parent.mkdir(parents=True, exist_ok=True)
        prepared.write_bytes(b"fake-h5")
        created_paths.append(prepared)
        prepare_kwargs.append(dict(_kwargs))
        return prepared, False

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._prepare_drone_source_working_h5",
        _fake_prepare,
    )

    results = run_drone_pipeline(
        tmp_path / "input",
        output_dir=tmp_path / "out",
        apply_topo=False,
        apply_brdf=False,
        drone_manifest_path=manifest_path,
    )

    assert created_paths == [tmp_path / "out" / "SPR1_20230628" / "SPR1_20230628__working.h5"]
    assert prepare_kwargs[0]["acquisition_datetime"] == datetime(2023, 6, 28, 19, 53, 7)
    assert prepare_kwargs[0]["require_solar_geometry"] is False
    assert results["processed"] == [str(tif_path)]
    file_summary = results["qa_summary"]["files"][0]
    assert file_summary["input_source_type"] == "tiff"
    assert file_summary["input_source_filename"] == "aligned_orthomosaic.tif"
    assert file_summary["manifest_flight_datetime"] == "2023-06-28T19:53:07"
    assert file_summary["solar_geometry_source"] == "raster"
    assert results["qa_summary"]["drone_manifest_path"] == str(manifest_path)
    assert file_summary["prepared_h5_filename"] == "SPR1_20230628__working.h5"
    assert file_summary["status"] == "success_qa_only_no_polygons"


def test_apply_drone_corrections_uses_full_scene_chunk(
    tmp_path: Path, monkeypatch
) -> None:
    cube = _RecordingCube(tmp_path / "fake.h5")
    raw_img = tmp_path / "raw.img"
    raw_hdr = tmp_path / "raw.hdr"
    raw_img.write_bytes(b"raw")
    raw_hdr.write_text("hdr", encoding="utf-8")

    monkeypatch.setattr("spectralbridge.pipelines.drone.EnviWriter", _FakeWriter)
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.TileProgressReporter", _FakeReporter
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._has_required_ancillary",
        lambda cube, names: True,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_topo_correct",
        lambda cube, chunk, ys, ye, xs, xe: np.asarray(chunk, dtype=np.float32),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_brdf_correct",
        lambda cube, chunk, ys, ye, xs, xe, coeff_path=None: np.asarray(
            chunk, dtype=np.float32
        ),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.fit_and_save_brdf_model",
        lambda cube, out_dir: Path(out_dir) / "coeffs.json",
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )

    corrected_img, corrected_hdr, audit = apply_drone_corrections(
        cube=cube,
        envi_img=raw_img,
        envi_hdr=raw_hdr,
        corrected_stem=tmp_path / "corrected",
        apply_topo=True,
        apply_brdf=True,
    )

    assert corrected_img.exists()
    assert corrected_hdr.exists()
    assert audit["topo_applied"] is True
    assert audit["brdf_applied"] is True
    assert cube.chunk_args == [(cube.lines, cube.columns), (cube.lines, cube.columns)]
    corrected_header = json.loads(corrected_hdr.read_text(encoding="utf-8"))
    assert corrected_header["data ignore value"] == pytest.approx(-9999.0)
    assert corrected_header["reflectance scale factor"] == pytest.approx(1.0)


def test_apply_drone_corrections_reverts_topo_chunk_when_it_becomes_all_nodata(
    tmp_path: Path, monkeypatch
) -> None:
    cube = _RecordingCube(tmp_path / "fake.h5")
    raw_img = tmp_path / "raw.img"
    raw_hdr = tmp_path / "raw.hdr"
    raw_img.write_bytes(b"raw")
    raw_hdr.write_text("hdr", encoding="utf-8")

    monkeypatch.setattr("spectralbridge.pipelines.drone.EnviWriter", _FakeWriter)
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.TileProgressReporter", _FakeReporter
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._has_required_ancillary",
        lambda cube, names: True,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_topo_correct",
        lambda cube, chunk, ys, ye, xs, xe: np.asarray(chunk, dtype=np.float32),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_brdf_correct",
        lambda cube, chunk, ys, ye, xs, xe, coeff_path=None: np.asarray(
            chunk, dtype=np.float32
        ),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.fit_and_save_brdf_model",
        lambda cube, out_dir: Path(out_dir) / "coeffs.json",
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_topo_correct",
        lambda cube, chunk, ys, ye, xs, xe: np.full_like(
            np.asarray(chunk, dtype=np.float32), cube.no_data, dtype=np.float32
        ),
    )

    with pytest.raises(
        DroneCorrectionUnavailableError,
        match="reverted because it collapsed valid reflectance to no-data",
    ) as exc_info:
        apply_drone_corrections(
            cube=cube,
            envi_img=raw_img,
            envi_hdr=raw_hdr,
            corrected_stem=tmp_path / "corrected",
            apply_topo=True,
            apply_brdf=False,
        )

    audit = exc_info.value.audit
    assert audit["topo_applied"] is False
    assert audit["topo_fallback_due_to_nodata"] is True
    assert not (tmp_path / "corrected.img").exists()
    assert not (tmp_path / "corrected.hdr").exists()


def test_apply_drone_corrections_reuses_existing_qa_flags(
    tmp_path: Path, monkeypatch
) -> None:
    flight_dir = tmp_path / "SPR1_20230628"
    flight_dir.mkdir()
    cube = _RecordingCube(flight_dir / "fake.h5")
    raw_img = flight_dir / "SPR1_20230628__envi.img"
    raw_hdr = flight_dir / "SPR1_20230628__envi.hdr"
    raw_img.write_bytes(b"raw")
    raw_hdr.write_text("hdr", encoding="utf-8")
    corrected_stem = flight_dir / "SPR1_20230628__corrected"
    corrected_stem.with_suffix(".img").write_bytes(b"corr")
    corrected_stem.with_suffix(".hdr").write_text("hdr", encoding="utf-8")
    qa_json = flight_dir / "SPR1_20230628__qa.json"
    qa_json.write_text(
        json.dumps(
            {
                "audit": {
                    "flags": {
                        "topo_applied": True,
                        "brdf_applied": True,
                        "topo_fallback_due_to_nodata": False,
                        "brdf_fallback_due_to_nodata": False,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._has_required_ancillary",
        lambda cube, names: True,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )

    corrected_img, corrected_hdr, audit = apply_drone_corrections(
        cube=cube,
        envi_img=raw_img,
        envi_hdr=raw_hdr,
        corrected_stem=corrected_stem,
        apply_topo=True,
        apply_brdf=True,
        overwrite=False,
    )

    assert corrected_img == corrected_stem.with_suffix(".img")
    assert corrected_hdr == corrected_stem.with_suffix(".hdr")
    assert audit["reused_existing_corrected"] is True
    assert audit["correction_status_source"] == "existing_qa_json"
    assert audit["topo_applied"] is True
    assert audit["brdf_applied"] is True


def test_render_drone_panel_includes_correction_status(tmp_path: Path) -> None:
    raw_base = tmp_path / "SPR1_20230628__envi"
    corrected_base = tmp_path / "SPR1_20230628__corrected"
    wavelengths = [490.0, 560.0, 660.0, 820.0]
    raw = np.full((4, 4, 4), 0.2, dtype=np.float32)
    corrected = raw * np.float32(0.92) + np.float32(0.01)
    _write_envi_pair(raw_base, raw, wavelengths)
    _write_envi_pair(corrected_base, corrected, wavelengths)

    output_png, qa_payload = render_drone_panel(
        raw_path=raw_base.with_suffix(".img"),
        corrected_path=corrected_base.with_suffix(".img"),
        output_png=tmp_path / "SPR1_20230628__qa.png",
        qa_summary={
            "flags": {
                "topo_requested": True,
                "brdf_requested": True,
                "topo_applied": True,
                "brdf_applied": True,
                "reused_existing_corrected": False,
            },
            "correction_status_source": "live_run",
        },
        save_json=True,
    )

    assert output_png.exists()
    assert qa_payload["correction"]["topo_requested"] is True
    assert qa_payload["correction"]["brdf_requested"] is True
    assert qa_payload["correction"]["topo_applied"] is True
    assert qa_payload["correction"]["brdf_applied"] is True
    assert qa_payload["correction"]["status_source"] == "live_run"
    assert qa_payload["correction"]["observed_change"] is True
    assert qa_payload["merged_preview"]["path"] is None
    assert qa_payload["polygon"]["path"] is None

    saved_payload = json.loads(output_png.with_suffix(".json").read_text(encoding="utf-8"))
    assert saved_payload["correction"]["topo_applied"] is True
    assert saved_payload["correction"]["observed_change"] is True


def test_render_drone_panel_logs_sampling_debug_and_writes_debug_payload(
    tmp_path: Path, caplog
) -> None:
    raw_base = tmp_path / "SPR1_20230628__envi"
    corrected_base = tmp_path / "SPR1_20230628__corrected"
    wavelengths = [490.0, 560.0, 660.0, 820.0]
    raw = np.full((4, 4, 4), 0.2, dtype=np.float32)
    corrected = raw.copy()
    corrected[0, :, :] = np.float32(-9999.0)
    corrected[1, 0, 0] = np.float32(0.25)
    corrected[2, 1, 1] = np.float32(1.6)
    _write_envi_pair(raw_base, raw, wavelengths)
    _write_envi_pair(corrected_base, corrected, wavelengths)

    with caplog.at_level("INFO", logger="spectralbridge.qa_plots"):
        _, qa_payload = render_drone_panel(
            raw_path=raw_base.with_suffix(".img"),
            corrected_path=corrected_base.with_suffix(".img"),
            output_png=tmp_path / "SPR1_20230628__qa.png",
            qa_summary={"flags": {}, "correction_status_source": "live_run"},
            save_json=False,
        )

    debug_sampling = qa_payload["debug_sampling"]
    assert debug_sampling["scene_id"] == "SPR1_20230628"
    assert debug_sampling["raw_cube_shape"] == [4, 4, 4]
    assert debug_sampling["corr_cube_shape"] == [4, 4, 4]
    assert debug_sampling["sample_shape"] == [4, 16]
    assert debug_sampling["total_pixels"] == 16
    assert debug_sampling["eligible_pixels_for_sampling"] == 16
    assert debug_sampling["sampled_pixels"] == 16
    assert debug_sampling["min_valid_band_fraction_for_sampling"] == pytest.approx(0.25)
    assert debug_sampling["bands_with_any_sample_support"] == 3
    assert debug_sampling["bands_with_gt10_support"] >= 1
    assert debug_sampling["band_support_pct"]["any"] == pytest.approx(75.0)
    assert debug_sampling["support_wavelength_ranges_nm"]["any"].startswith("560.0-820.0")
    assert debug_sampling["fraction_above_change_threshold"] >= 0.0
    assert "scene_classification" in qa_payload["correction"]
    assert "sample_valid_counts_summary" in qa_payload["correction"]
    assert "polygon parquet rows are not the direct source" in caplog.text
    assert "sampling eligible=" in caplog.text
    assert "sample support counts_per_band=" in caplog.text


def test_render_drone_panel_uses_larger_default_sampling_cap(
    tmp_path: Path, monkeypatch
) -> None:
    raw_path = tmp_path / "SPR1_20230628__envi.img"
    corrected_path = tmp_path / "SPR1_20230628__corrected.img"
    raw_path.write_bytes(b"raw")
    corrected_path.write_bytes(b"corr")

    large_raw = np.full((4, 600, 600), 0.2, dtype=np.float32)
    large_corr = large_raw * np.float32(0.95) + np.float32(0.01)
    wavelengths = np.array([490.0, 560.0, 660.0, 820.0], dtype=np.float32)
    sample_calls: list[int] = []

    monkeypatch.setattr(qa_plots, "hdr_to_dict", lambda path: {"data ignore value": -9999.0})
    monkeypatch.setattr(
        qa_plots,
        "read_envi_cube",
        lambda path, hdr: large_raw if Path(path) == raw_path else large_corr,
    )
    monkeypatch.setattr(
        qa_plots,
        "wavelengths_from_hdr",
        lambda hdr: (wavelengths, "header"),
    )

    def _recording_sample(cube, mask, n_sample):
        sample_calls.append(int(n_sample))
        bands = cube.shape[0]
        return (
            np.full((bands, 8), 0.2, dtype=np.float32),
            np.ones((bands, 8), dtype=bool),
            {
                "total_pixels": int(cube.shape[1] * cube.shape[2]),
                "eligible_pixels_for_sampling": 8,
                "eligible_pixel_pct": 1.0,
                "sampled_pixels": 8,
                "sampled_vs_eligible_pct": 100.0,
                "min_valid_band_fraction_for_sampling": 0.25,
            },
        )

    monkeypatch.setattr(qa_plots, "_deterministic_drone_valid_sample", _recording_sample)

    output_png, _ = render_drone_panel(
        raw_path=raw_path,
        corrected_path=corrected_path,
        output_png=tmp_path / "SPR1_20230628__qa.png",
        qa_summary={"flags": {}, "correction_status_source": "live_run"},
        save_json=False,
    )

    assert output_png.exists()
    assert sample_calls == [250_000, 250_000]


def test_render_drone_panel_honors_safe_sampling_override(
    tmp_path: Path, monkeypatch
) -> None:
    raw_path = tmp_path / "SPR1_20230628__envi.img"
    corrected_path = tmp_path / "SPR1_20230628__corrected.img"
    raw_path.write_bytes(b"raw")
    corrected_path.write_bytes(b"corr")

    large_raw = np.full((4, 600, 600), 0.2, dtype=np.float32)
    large_corr = large_raw.copy()
    wavelengths = np.array([490.0, 560.0, 660.0, 820.0], dtype=np.float32)
    sample_calls: list[int] = []

    monkeypatch.setattr(qa_plots, "hdr_to_dict", lambda path: {"data ignore value": -9999.0})
    monkeypatch.setattr(
        qa_plots,
        "read_envi_cube",
        lambda path, hdr: large_raw if Path(path) == raw_path else large_corr,
    )
    monkeypatch.setattr(
        qa_plots,
        "wavelengths_from_hdr",
        lambda hdr: (wavelengths, "header"),
    )

    def _recording_sample(cube, mask, n_sample):
        sample_calls.append(int(n_sample))
        bands = cube.shape[0]
        return (
            np.full((bands, 8), 0.2, dtype=np.float32),
            np.ones((bands, 8), dtype=bool),
            {
                "total_pixels": int(cube.shape[1] * cube.shape[2]),
                "eligible_pixels_for_sampling": 8,
                "eligible_pixel_pct": 1.0,
                "sampled_pixels": 8,
                "sampled_vs_eligible_pct": 100.0,
                "min_valid_band_fraction_for_sampling": 0.25,
            },
        )

    monkeypatch.setattr(qa_plots, "_deterministic_drone_valid_sample", _recording_sample)

    output_png, _ = render_drone_panel(
        raw_path=raw_path,
        corrected_path=corrected_path,
        output_png=tmp_path / "SPR1_20230628__qa.png",
        qa_summary={"flags": {}, "correction_status_source": "live_run"},
        save_json=False,
        qa_max_samples=12_345,
    )

    assert output_png.exists()
    assert sample_calls == [12_345, 12_345]


def test_drone_scene_classification_detects_effective_noop() -> None:
    wavelengths = np.array([490.0, 560.0, 660.0, 820.0], dtype=np.float32)
    full_diff = np.full((4, 3, 3), 1e-6, dtype=np.float32)
    sample_mask = np.ones((4, 12), dtype=bool)

    diff_summary = _summarize_full_diff(full_diff, wavelengths)
    support_summary = _summarize_sample_support(wavelengths, sample_mask)
    flags = _classify_drone_scene(diff_summary, support_summary)

    assert "effective_noop_correction" in flags
    assert "outlier_dominated_correction" not in flags


def test_drone_scene_classification_detects_outlier_dominated() -> None:
    wavelengths = np.array([490.0, 560.0, 660.0, 820.0], dtype=np.float32)
    full_diff = np.full((4, 8, 8), 0.001, dtype=np.float32)
    full_diff[2, 0, 0] = 20.0
    full_diff[3, 1, 1] = 5.0
    sample_mask = np.ones((4, 200), dtype=bool)

    diff_summary = _summarize_full_diff(full_diff, wavelengths)
    support_summary = _summarize_sample_support(wavelengths, sample_mask)
    flags = _classify_drone_scene(diff_summary, support_summary)

    assert "outlier_dominated_correction" in flags
    assert diff_summary["n_abs_diff_gt_10"] >= 1


def test_drone_support_summary_detects_support_collapse() -> None:
    wavelengths = np.array([490.0, 560.0, 660.0, 820.0], dtype=np.float32)
    sample_mask = np.array(
        [
            [True, False, False, False],
            [False, False, False, False],
            [True, False, False, False],
            [False, False, False, False],
        ],
        dtype=bool,
    )

    support_summary = _summarize_sample_support(wavelengths, sample_mask)
    diff_summary = _summarize_full_diff(np.zeros((4, 2, 2), dtype=np.float32), wavelengths)
    flags = _classify_drone_scene(diff_summary, support_summary)

    assert support_summary["bands_with_any_support"] == 2
    assert support_summary["bands_with_gt10_support"] == 0
    assert "band_support_collapsed" in flags


def test_deterministic_drone_valid_sample_avoids_nodata_edges() -> None:
    cube = np.zeros((4, 8, 8), dtype=np.float32)
    mask = np.zeros((4, 8, 8), dtype=bool)
    mask[:, 2:6, 2:6] = True

    sample_a, sample_mask_a, diagnostics_a = _deterministic_drone_valid_sample(
        cube,
        mask,
        12,
    )
    sample_b, sample_mask_b, diagnostics_b = _deterministic_drone_valid_sample(
        cube,
        mask,
        12,
    )

    assert sample_a.shape == (4, 12)
    assert np.array_equal(sample_a, sample_b)
    assert np.array_equal(sample_mask_a, sample_mask_b)
    assert np.all(sample_mask_a)
    assert diagnostics_a == diagnostics_b
    assert diagnostics_a["total_pixels"] == 64
    assert diagnostics_a["eligible_pixels_for_sampling"] == 16
    assert diagnostics_a["sampled_pixels"] == 12
    assert diagnostics_a["min_valid_band_fraction_for_sampling"] == pytest.approx(0.25)


def test_deterministic_drone_valid_sample_falls_back_to_any_valid_pixel() -> None:
    cube = np.zeros((4, 4, 4), dtype=np.float32)
    mask = np.zeros((4, 4, 4), dtype=bool)
    mask[0, 1, 1] = True
    mask[1, 1, 1] = True

    sample, sample_mask, diagnostics = _deterministic_drone_valid_sample(cube, mask, 4)

    assert sample.shape[1] == 1
    assert sample_mask.shape[1] == 1
    assert diagnostics["eligible_pixels_for_sampling"] == 1
    assert diagnostics["sampled_pixels"] == 1


def test_render_drone_panel_places_invalid_maps_on_bottom_row(
    tmp_path: Path, monkeypatch
) -> None:
    plt = pytest.importorskip("matplotlib.pyplot")

    raw_base = tmp_path / "SPR1_20230628__envi"
    corrected_base = tmp_path / "SPR1_20230628__corrected"
    wavelengths = [490.0, 560.0, 660.0, 820.0]
    raw = np.full((4, 4, 4), 0.2, dtype=np.float32)
    corrected = raw * np.float32(0.92) + np.float32(0.01)
    _write_envi_pair(raw_base, raw, wavelengths)
    _write_envi_pair(corrected_base, corrected, wavelengths)

    captured: dict[str, object] = {}
    original_subplots = qa_plots.plt.subplots

    def _capture_subplots(*args, **kwargs):
        fig, axes = original_subplots(*args, **kwargs)
        captured["fig"] = fig
        captured["axes"] = axes
        return fig, axes

    monkeypatch.setattr(qa_plots.plt, "subplots", _capture_subplots)
    monkeypatch.setattr(qa_plots.plt, "close", lambda fig=None: None)

    output_png, _ = render_drone_panel(
        raw_path=raw_base.with_suffix(".img"),
        corrected_path=corrected_base.with_suffix(".img"),
        output_png=tmp_path / "SPR1_20230628__qa.png",
        qa_summary={"flags": {}, "correction_status_source": "live_run"},
        save_json=False,
    )

    assert output_png.exists()
    axes = captured["axes"]
    assert axes[0, 0].get_title().startswith("Raw Reflectance RGB Preview")
    assert axes[0, 1].get_title() == "Median Spectra And Sampled Pixel Traces"
    assert axes[1, 0].get_title() == "Correction Distribution By Wavelength"
    assert axes[1, 1].get_title() == "Spatial Median Absolute Correction Across Bands"
    assert axes[2, 0].get_title() == "Polygon Overlay On Corrected Raster"
    assert axes[2, 1].get_title() == "Merged Polygon Parquet Preview"
    assert axes[3, 0].get_title() == "Raw Invalid / NoData Band Fraction"
    assert axes[3, 1].get_title() == "Corrected Invalid / NoData Band Fraction"
    assert all(ax.get_title() != "% changed" for ax in captured["fig"].axes)

    plt.close(captured["fig"])


def test_render_drone_merged_preview_prefers_non_nodata_rows(
    tmp_path: Path, monkeypatch
) -> None:
    merged_path = tmp_path / "merged.parquet"
    merged_path.write_text("placeholder", encoding="utf-8")
    df = pd.DataFrame(
        {
            "flight_id": ["SPR1_20230628", "SPR1_20230628"],
            "pixel_id": [1, 2],
            "row": [0, 1],
            "col": [0, 1],
            "corr_b001_wl0440nm": [-9999.0, 0.12],
            "corr_b002_wl0560nm": [-9999.0, 0.23],
            "corr_b003_wl0650nm": [-9999.0, 0.34],
        }
    )
    monkeypatch.setattr(pd, "read_parquet", lambda path: df.copy())

    summary = _render_drone_merged_preview(_FakeAxes(), merged_path, "SPR1_20230628")

    assert summary["rows_total"] == 2
    assert summary["rows_previewed"] == 1
    assert "non-nodata spectral rows" in str(summary["filter_applied"])


def test_render_drone_merged_preview_explains_missing_extraction() -> None:
    fake_ax = _FakeAxes()
    summary = _render_drone_merged_preview(
        fake_ax,
        None,
        "SPR1_20230628",
        qa_summary={"status": "success_qa_only_no_polygon_overlap"},
    )

    assert summary["path"] is None


def test_render_drone_merged_preview_prioritizes_rightmost_columns(
    tmp_path: Path, monkeypatch
) -> None:
    merged_path = tmp_path / "merged.parquet"
    merged_path.write_text("placeholder", encoding="utf-8")
    df = pd.DataFrame(
        {
            "flight_id": ["SPR1_20230628"],
            "pixel_id": [1],
            "row": [0],
            "col": [1],
            "x": [100.0],
            "y": [200.0],
            "left_a": [10.0],
            "left_b": [20.0],
            "corr_b001_wl0440nm": [0.12],
            "corr_b002_wl0560nm": [0.23],
            "corr_b003_wl0650nm": [0.34],
            "corr_b004_wl0862nm": [0.45],
        }
    )
    monkeypatch.setattr(pd, "read_parquet", lambda path: df.copy())

    summary = _render_drone_merged_preview(_FakeAxes(), merged_path, "SPR1_20230628")

    assert summary["rows_previewed"] == 1
    assert "pixel_id" in summary["columns_previewed"]
    assert "row" in summary["columns_previewed"]
    assert "col" in summary["columns_previewed"]
    assert "corr_b004_wl0862nm" in summary["columns_previewed"]
    assert "corr_b003_wl0650nm" in summary["columns_previewed"]


def test_render_drone_band_fidelity_suppresses_display_spikes() -> None:
    plt = pytest.importorskip("matplotlib.pyplot")

    fig, ax = plt.subplots()
    try:
        wavelengths = np.array([440.0, 560.0, 650.0, 862.0], dtype=np.float32)
        raw = np.array([110.0, 260.0, 180.0, 950.0], dtype=np.float32)
        corrected = np.array([112.0, 255.0, 15000.0, 960.0], dtype=np.float32)

        _render_drone_band_fidelity(ax, wavelengths, raw, corrected, band_map=None)

        _, ymax = ax.get_ylim()
        assert ymax < 2_000.0
    finally:
        plt.close(fig)


def test_render_drone_band_fidelity_adds_sampled_traces() -> None:
    plt = pytest.importorskip("matplotlib.pyplot")

    wavelengths = np.array([440.0, 560.0, 650.0, 862.0], dtype=np.float32)
    raw = np.array([0.10, 0.20, 0.30, 0.40], dtype=np.float32)
    corrected = np.array([0.11, 0.19, 0.31, 0.39], dtype=np.float32)
    raw_sample = np.array(
        [
            [0.08, 0.12, -9999.0],
            [0.18, 0.22, 0.21],
            [0.28, 0.33, 0.29],
            [0.38, 0.42, 0.41],
        ],
        dtype=np.float32,
    )
    corr_sample = raw_sample + np.array([[0.01], [-0.01], [0.02], [-0.02]], dtype=np.float32)
    sample_mask = np.array(
        [
            [True, True, False],
            [True, True, True],
            [True, True, True],
            [True, True, True],
        ],
        dtype=bool,
    )

    fig_plain, ax_plain = plt.subplots()
    fig_cloud, ax_cloud = plt.subplots()
    try:
        _render_drone_band_fidelity(ax_plain, wavelengths, raw, corrected, band_map=None)
        _render_drone_band_fidelity(
            ax_cloud,
            wavelengths,
            raw,
            corrected,
            band_map=None,
            raw_sample=raw_sample,
            corr_sample=corr_sample,
            sample_mask=sample_mask,
            max_traces=3,
        )

        assert len(ax_cloud.lines) > len(ax_plain.lines)
        assert len(ax_plain.lines) == 2
        assert len(ax_cloud.lines) >= 4
    finally:
        plt.close(fig_plain)
        plt.close(fig_cloud)


def test_correction_report_and_delta_render_handle_distribution_stats() -> None:
    plt = pytest.importorskip("matplotlib.pyplot")

    raw_sample = np.array(
        [
            [0.10, 0.20, -9999.0, 0.40],
            [0.20, 0.30, 0.40, 0.50],
            [0.30, 0.40, 0.50, 2000.0],
        ],
        dtype=np.float32,
    )
    corr_sample = np.array(
        [
            [0.12, 0.18, 0.50, 0.41],
            [0.19, 0.28, 0.45, 0.48],
            [0.36, 0.35, 0.55, -9999.0],
        ],
        dtype=np.float32,
    )
    sample_mask = np.array(
        [
            [True, True, True, True],
            [True, True, True, True],
            [True, True, True, True],
        ],
        dtype=bool,
    )

    report = _correction_report(raw_sample, corr_sample, sample_mask)

    assert len(report.delta_q10) == 3
    assert len(report.delta_q25) == 3
    assert len(report.delta_q75) == 3
    assert len(report.delta_q90) == 3
    assert len(report.delta_abs_median) == 3
    assert all(np.isfinite(np.array(report.delta_abs_median, dtype=float)))

    fig, ax = plt.subplots()
    try:
        _render_delta(ax, np.array([440.0, 560.0, 650.0], dtype=np.float32), report)
        assert len(ax.lines) >= 3
        assert len(ax.collections) >= 2
    finally:
        plt.close(fig)


def test_render_drone_correction_magnitude_returns_richer_spatial_summary() -> None:
    plt = pytest.importorskip("matplotlib.pyplot")

    raw_cube = np.array(
        [
            [[0.10, 0.10], [0.10, -9999.0]],
            [[0.20, 0.20], [0.20, -9999.0]],
            [[0.30, 0.30], [0.30, -9999.0]],
        ],
        dtype=np.float32,
    )
    corr_cube = np.array(
        [
            [[0.12, 0.11], [0.09, -9999.0]],
            [[0.24, 0.19], [0.23, -9999.0]],
            [[0.34, 0.27], [0.31, -9999.0]],
        ],
        dtype=np.float32,
    )
    valid_mask = (raw_cube > -9990.0) & (corr_cube > -9990.0)
    full_diff = np.where(valid_mask, corr_cube - raw_cube, np.nan)

    fig, ax = plt.subplots()
    try:
        summary = _render_drone_correction_magnitude(
            ax,
            full_diff,
            {"scene_classification": ["outlier_dominated_correction"]},
        )
    finally:
        plt.close(fig)

    assert summary["spatial_abs_delta_median"] >= 0.0
    assert np.isfinite(summary["spatial_abs_delta_p95"])
    assert np.isfinite(summary["spatial_abs_delta_p90"])
    assert np.isfinite(summary["spatial_abs_delta_max"])
    assert np.isfinite(summary["pixels_above_change_threshold_pct"])
    assert np.isfinite(summary["spatial_changed_frac_median"])
    assert np.isfinite(summary["median_valid_bands_per_pixel"])
    assert summary["change_threshold"] > 0.0


def test_export_csv_copy_from_parquet_writes_csv_sidecar(tmp_path: Path) -> None:
    parquet_path = tmp_path / "demo.parquet"
    csv_path = tmp_path / "demo.csv"
    con = duckdb.connect()
    try:
        con.execute(
            "COPY (SELECT * FROM (VALUES "
            "(1, 0.1, 'a'), "
            "(2, 0.2, 'b')) AS t(pixel_id, band_1, label)) "
            "TO ? (FORMAT PARQUET)",
            [str(parquet_path)],
        )
    finally:
        con.close()

    written_csv = _export_csv_copy_from_parquet(parquet_path, overwrite=True)

    assert written_csv == csv_path
    assert csv_path.exists()
    round_trip = pd.read_csv(csv_path)
    assert round_trip["pixel_id"].tolist() == [1, 2]
    assert round_trip["label"].tolist() == ["a", "b"]


def test_enrich_drone_polygon_parquet_with_index_duplicates_polygon_metadata(
    tmp_path: Path,
) -> None:
    polygon_parquet = tmp_path / "pixels.parquet"
    polygon_index = tmp_path / "index.parquet"

    con = duckdb.connect()
    try:
        con.execute(
            "COPY (SELECT * FROM (VALUES "
            "(1001, 10.0, 20.0), "
            "(1002, 11.0, 21.0)) AS t(pixel_id, raw_b001_wl0444nm, raw_b002_wl0560nm)) "
            "TO ? (FORMAT PARQUET)",
            [str(polygon_parquet)],
        )
        con.execute(
            "COPY (SELECT * FROM (VALUES "
            "(1001, 7, 'PIPO', 'tree_a'), "
            "(1002, 7, 'PIPO', 'tree_a')) AS t(pixel_id, polygon_id, species, stem_tag)) "
            "TO ? (FORMAT PARQUET)",
            [str(polygon_index)],
        )
    finally:
        con.close()

    enriched = _enrich_drone_polygon_parquet_with_index(
        polygon_parquet,
        polygon_index,
    )

    con = duckdb.connect()
    try:
        df = con.execute("SELECT * FROM read_parquet(?)", [str(enriched)]).df()
    finally:
        con.close()
    assert "polygon_id" in df.columns
    assert "species" in df.columns
    assert "stem_tag" in df.columns
    assert df["polygon_id"].tolist() == [7, 7]
    assert df["species"].tolist() == ["PIPO", "PIPO"]
    assert df["stem_tag"].tolist() == ["tree_a", "tree_a"]
    assert df["raw_b001_wl0444nm"].tolist() == [10.0, 11.0]


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

    _patch_basic_drone_runtime(monkeypatch)

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
        "spectralbridge.pipelines.drone._enrich_drone_polygon_parquet_with_index",
        _fake_polygon_enrichment,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._export_csv_copy_from_parquet",
        _fake_csv_export,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.collect_drone_spatial_diagnostics",
        lambda *, raster_img, polygons_path: {
            "raster_crs": "EPSG:32613",
            "polygon_crs": "EPSG:4326",
            "polygon_reprojected": True,
            "bounds_overlap_after_reproject": True,
            "intersecting_polygon_count": 1,
            "raster_bounds": [0.0, 0.0, 10.0, 10.0],
        },
    )

    def _fake_overlay_plot(**kwargs):
        output_path = Path(kwargs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        return output_path

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.save_drone_overlay_debug_plot",
        _fake_overlay_plot,
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
    assert results["merged_csv"] == str(tmp_path / "out" / "drone_merged.csv")
    assert Path(results["merged"]).exists()
    assert Path(results["merged_csv"]).exists()
    qa_files = results["qa_summary"]["files"]
    assert {entry["polygon_filename"] for entry in qa_files} == {
        "SPR1_20230628__polygons.parquet",
        "SPR2_20230628__polygons.parquet",
    }
    assert {entry["polygon_csv_filename"] for entry in qa_files} == {
        "SPR1_20230628__polygons.csv",
        "SPR2_20230628__polygons.csv",
    }
    assert {entry["merged_filename"] for entry in qa_files} == {"drone_merged.parquet"}
    assert {entry["merged_csv_filename"] for entry in qa_files} == {"drone_merged.csv"}
    assert {entry["qa_plot_filename"] for entry in qa_files} == {
        "SPR1_20230628__qa.png",
        "SPR2_20230628__qa.png",
    }
    assert {Path(entry["flight_dir"]).name for entry in qa_files} == {
        "SPR1_20230628",
        "SPR2_20230628",
    }
    assert {entry["status"] for entry in qa_files} == {"success_extracted"}


def test_run_drone_pipeline_still_renders_qa_when_csv_export_fails(
    tmp_path: Path, monkeypatch
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    h5_path = (
        input_dir
        / "SPR1-06-28-23-ExportPackage"
        / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    )
    h5_path.parent.mkdir(parents=True, exist_ok=True)
    h5_path.write_bytes(b"a")
    polygon_path = tmp_path / "plots.geojson"
    polygon_path.write_text("{}", encoding="utf-8")

    _patch_basic_drone_runtime(monkeypatch)

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
        "spectralbridge.pipelines.drone._enrich_drone_polygon_parquet_with_index",
        _fake_polygon_enrichment,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._export_csv_copy_from_parquet",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("csv export boom")),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.collect_drone_spatial_diagnostics",
        lambda *, raster_img, polygons_path: {
            "raster_crs": "EPSG:32613",
            "polygon_crs": "EPSG:4326",
            "polygon_reprojected": True,
            "bounds_overlap_after_reproject": True,
            "intersecting_polygon_count": 1,
            "raster_bounds": [0.0, 0.0, 10.0, 10.0],
        },
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.save_drone_overlay_debug_plot",
        lambda **kwargs: Path(kwargs["output_path"]).write_bytes(b"png")
        or Path(kwargs["output_path"]),
    )

    results = run_drone_pipeline(
        input_dir,
        polygon_path=polygon_path,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    assert results["processed"] == [str(h5_path)]
    assert results["failed"] == []
    assert results["merged"] == str(tmp_path / "out" / "drone_merged.parquet")
    assert results["merged_csv"] is None
    file_summary = results["qa_summary"]["files"][0]
    assert file_summary["status"] == "success_extracted"
    assert file_summary["polygon_csv_filename"] is None
    assert file_summary["polygon_csv_error"] == "csv export boom"
    assert file_summary["merged_csv_filename"] is None
    assert file_summary["merged_csv_error"] == "csv export boom"
    assert Path(file_summary["qa_plot_path"]).exists()
    assert Path(file_summary["qa_json_path"]).exists()


def test_collect_drone_spatial_diagnostics_records_raster_and_polygon_metadata(
    tmp_path: Path,
) -> None:
    raster_path = _write_test_raster(tmp_path / "flight.tif")
    polygon_path = _write_test_polygons(
        tmp_path / "plots.geojson",
        crs="EPSG:32613",
        polygons=[
            Polygon(
                [
                    (500005.0, 4099995.0),
                    (500020.0, 4099995.0),
                    (500020.0, 4099980.0),
                    (500005.0, 4099980.0),
                ]
            )
        ],
    )

    diagnostics = collect_drone_spatial_diagnostics(
        raster_img=raster_path,
        polygons_path=polygon_path,
    )

    assert diagnostics["raster_path"] == str(raster_path)
    assert diagnostics["raster_crs"] == "EPSG:32613"
    assert diagnostics["raster_bounds"] == [
        500000.0,
        4099960.0,
        500040.0,
        4100000.0,
    ]
    assert diagnostics["raster_transform"] == [
        10.0,
        0.0,
        500000.0,
        0.0,
        -10.0,
        4100000.0,
    ]
    assert diagnostics["raster_nodata"] == pytest.approx(-9999.0)
    assert diagnostics["polygon_crs"] == "EPSG:32613"
    assert diagnostics["polygon_count"] == 1
    assert diagnostics["polygon_total_bounds"] == [
        500005.0,
        4099980.0,
        500020.0,
        4099995.0,
    ]
    assert diagnostics["bounds_overlap_after_reproject"] is True
    assert diagnostics["intersecting_polygon_count"] == 1


def test_collect_drone_spatial_diagnostics_reprojects_before_overlap_check(
    tmp_path: Path,
) -> None:
    raster_path = _write_test_raster(tmp_path / "flight.tif")
    polygon_path = _write_test_polygons(
        tmp_path / "plots.geojson",
        crs="EPSG:4326",
        polygons=[
            Polygon(
                [
                    (-105.00001, 37.04618),
                    (-104.99990, 37.04618),
                    (-104.99990, 37.04605),
                    (-105.00001, 37.04605),
                ]
            )
        ],
    )

    diagnostics = collect_drone_spatial_diagnostics(
        raster_img=raster_path,
        polygons_path=polygon_path,
    )

    assert diagnostics["polygon_crs"] == "EPSG:4326"
    assert diagnostics["polygon_reprojected"] is True
    assert diagnostics["reprojected_polygon_crs"] == "EPSG:32613"
    assert diagnostics["polygon_total_bounds"] != diagnostics["reprojected_polygon_total_bounds"]
    assert diagnostics["bounds_overlap_after_reproject"] is True
    assert diagnostics["intersecting_polygon_count"] == 1


def test_save_drone_overlay_debug_plot_writes_png(tmp_path: Path) -> None:
    polygon_path = _write_test_polygons(
        tmp_path / "plots.geojson",
        crs="EPSG:32613",
        polygons=[
            Polygon(
                [
                    (500005.0, 4099995.0),
                    (500020.0, 4099995.0),
                    (500020.0, 4099980.0),
                    (500005.0, 4099980.0),
                ]
            )
        ],
    )
    output_path = tmp_path / "overlay.png"

    written = save_drone_overlay_debug_plot(
        polygons_path=polygon_path,
        raster_bounds=[500000.0, 4099960.0, 500040.0, 4100000.0],
        raster_crs="EPSG:32613",
        output_path=output_path,
    )

    assert written == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0


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


def test_convert_drone_tiff_to_h5_creates_neoncube_readable_working_file(
    tmp_path: Path,
) -> None:
    from spectralbridge.neon_cube import NeonCube

    package = tmp_path / "SPR1-06-28-23-ExportPackage"
    reflectance_tif = _write_test_multiband_raster(package / "aligned_orthomosaic.tif")
    slope_tif = _write_test_raster(package / "slope.tif")
    aspect_tif = _write_test_raster(package / "aspect.tif")
    sensor_zenith_tif = _write_test_raster(package / "sensor_zenith.tif")
    sensor_azimuth_tif = _write_test_raster(package / "sensor_azimuth.tif")
    output_h5 = tmp_path / "out" / "SPR1_20230628__working.h5"

    written = convert_drone_tiff_to_h5(
        reflectance_tif,
        output_h5_path=output_h5,
        slope_tiff=slope_tif,
        aspect_tiff=aspect_tif,
        sensor_zenith_tiff=sensor_zenith_tif,
        sensor_azimuth_tiff=sensor_azimuth_tif,
        solar_zenith_deg=88.9,
        solar_azimuth_deg=287.69,
    )

    assert written == output_h5
    assert output_h5.exists()

    cube = NeonCube(h5_path=output_h5)
    assert cube.lines == 4
    assert cube.columns == 4
    assert cube.bands == 10
    np.testing.assert_allclose(
        cube.wavelengths,
        np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862], dtype=np.float32),
    )
    np.testing.assert_allclose(cube.get_ancillary("slope", radians=False), np.ones((4, 4), dtype=np.float32))
    np.testing.assert_allclose(cube.get_ancillary("solar_zn", radians=False), np.full((4, 4), 88.9, dtype=np.float32))


def test_load_drone_manifest_parses_flight_datetime(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.csv"
    manifest_path.write_text(
        " Plot , Day of data collection , Mean Time of data collection (24 hr clock) \n"
        " AOP_GOLDHILL , 2023-08-15 , 19:53:07 \n",
        encoding="utf-8",
    )

    manifest = load_drone_manifest(manifest_path)

    assert manifest["AOP_GOLDHILL"] == datetime(2023, 8, 15, 19, 53, 7)


def test_run_drone_pipeline_resolves_manifest_relative_to_input_dir(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    manifest_path = input_dir / "manifest.csv"
    manifest_path.write_text(
        "Plot,Day of data collection,Mean Time of data collection (24 hr clock)\n"
        "SPR-1,2023-06-28,17:30:21\n",
        encoding="utf-8",
    )

    results = run_drone_pipeline(
        input_dir,
        output_dir=tmp_path / "out",
        apply_topo=False,
        apply_brdf=False,
        drone_manifest_path="manifest.csv",
    )

    assert results["processed"] == []
    assert results["qa_summary"]["drone_manifest_path"] == str(manifest_path)


def test_run_drone_pipeline_uses_bundled_manifest_by_default(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    results = run_drone_pipeline(
        input_dir,
        output_dir=tmp_path / "out",
        apply_topo=False,
        apply_brdf=False,
    )

    assert results["processed"] == []
    assert results["qa_summary"]["drone_manifest_path"] == str(
        get_package_data_path("drone_field_manifest.csv")
    )


def test_run_drone_pipeline_resolves_original_manifest_filename_to_bundle(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    results = run_drone_pipeline(
        input_dir,
        output_dir=tmp_path / "out",
        apply_topo=False,
        apply_brdf=False,
        drone_manifest_path="Drone Field Data Macrosystems - UAS Data Processing For Extraction.csv",
    )

    assert results["processed"] == []
    assert results["qa_summary"]["drone_manifest_path"] == str(
        get_package_data_path("drone_field_manifest.csv")
    )


def test_run_drone_pipeline_resolves_manifest_relative_to_relative_input_folder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_dir = tmp_path / "work"
    input_dir = work_dir / "drone_inputs"
    input_dir.mkdir(parents=True)
    manifest_path = input_dir / "manifest.csv"
    manifest_path.write_text(
        "Plot,Day of data collection,Mean Time of data collection (24 hr clock)\n"
        "SPR-1,2023-06-28,17:30:21\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(work_dir)

    results = run_drone_pipeline(
        "drone_inputs",
        output_dir=tmp_path / "out",
        apply_topo=False,
        apply_brdf=False,
        drone_manifest_path="manifest.csv",
    )

    assert results["processed"] == []
    assert results["qa_summary"]["drone_manifest_path"] == str(manifest_path)


def test_run_drone_pipeline_missing_manifest_error_lists_checked_paths(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="Drone manifest CSV not found") as excinfo:
        run_drone_pipeline(
            input_dir,
            output_dir=tmp_path / "out",
            apply_topo=False,
            apply_brdf=False,
            drone_manifest_path="missing_manifest.csv",
        )

    message = str(excinfo.value)
    assert "Pass an absolute path" in message
    assert str(input_dir / "missing_manifest.csv") in message


def test_lookup_flight_datetime_matches_manifest_id_without_date_suffix() -> None:
    manifest = {"AOP_GOLDHILL": datetime(2023, 8, 15, 19, 53, 7)}

    acquisition_datetime = lookup_flight_datetime("AOP_GOLDHILL_20230814", manifest)

    assert acquisition_datetime == datetime(2023, 8, 15, 19, 53, 7)


def test_lookup_flight_datetime_matches_compact_mixed_separator_id() -> None:
    manifest = {"SPR_1": datetime(2023, 6, 28, 17, 30, 21)}

    acquisition_datetime = lookup_flight_datetime("SPR1_20230628", manifest)

    assert acquisition_datetime == datetime(2023, 6, 28, 17, 30, 21)


def test_convert_drone_tiff_to_h5_computes_manifest_solar_geometry(
    tmp_path: Path,
) -> None:
    package = tmp_path / "AOP_GOLDHILL_20230814"
    reflectance_tif = _write_test_multiband_raster(package / "aligned_orthomosaic.tif")
    output_h5 = tmp_path / "out" / "AOP_GOLDHILL_20230814__working.h5"

    written = convert_drone_tiff_to_h5(
        reflectance_tif,
        output_h5_path=output_h5,
        acquisition_datetime=datetime(2023, 8, 15, 19, 53, 7),
        require_solar_geometry=True,
    )

    assert written == output_h5
    with h5py.File(output_h5, "r") as h5_file:
        metadata = h5_file["AOP_GOLDHILL_20230814/Reflectance/Metadata"]
        solar_zenith = metadata["Solar_Zenith_Angle"][()]
        solar_azimuth = metadata["Solar_Azimuth_Angle"][()]
        assert solar_zenith.shape == (4, 4)
        assert solar_azimuth.shape == (4, 4)
        assert np.isfinite(solar_zenith).all()
        assert np.isfinite(solar_azimuth).all()
        assert metadata.attrs["solar_geometry_source"] == "manifest_computed"
        assert metadata.attrs["acquisition_datetime_used"] == "2023-08-15T19:53:07"

    summary = summarize_drone_h5_solar_geometry(output_h5)
    assert summary["solar_geometry_source"] == "manifest_computed"
    assert summary["acquisition_datetime_used"] == "2023-08-15T19:53:07"
    assert summary["solar_zenith_mean"] is not None


def test_convert_drone_tiff_to_h5_requires_solar_geometry_when_requested(
    tmp_path: Path,
) -> None:
    package = tmp_path / "AOP_GOLDHILL_20230814"
    reflectance_tif = _write_test_multiband_raster(package / "aligned_orthomosaic.tif")

    with pytest.raises(RuntimeError, match="requires solar geometry"):
        convert_drone_tiff_to_h5(
            reflectance_tif,
            output_h5_path=tmp_path / "out" / "missing_geometry.h5",
            require_solar_geometry=True,
        )


def test_prepare_drone_source_working_h5_converts_tiff_sources(tmp_path: Path) -> None:
    package = tmp_path / "SPR1-06-28-23-ExportPackage"
    reflectance_tif = _write_test_multiband_raster(package / "aligned_orthomosaic.tif")
    _write_test_raster(package / "slope.tif")
    _write_test_raster(package / "aspect.tif")
    _write_test_raster(package / "sensor_zenith.tif")
    _write_test_raster(package / "sensor_azimuth.tif")
    working_h5 = tmp_path / "prepared" / "SPR1_20230628__working.h5"

    prepared_path, patched = _prepare_drone_source_working_h5(
        reflectance_tif,
        source_type="tiff",
        working_path=working_h5,
        tiff_solar_zenith_deg=88.9,
        tiff_solar_azimuth_deg=287.69,
    )

    assert prepared_path == working_h5
    assert patched is False
    assert prepared_path.exists()


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
        "spectralbridge.pipelines.drone._has_required_ancillary",
        lambda cube, names: True,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_topo_correct",
        lambda cube, chunk, ys, ye, xs, xe: np.asarray(chunk, dtype=np.float32),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_brdf_correct",
        lambda cube, chunk, ys, ye, xs, xe, coeff_path=None: np.asarray(
            chunk, dtype=np.float32
        ),
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.fit_and_save_brdf_model",
        lambda cube, out_dir: Path(out_dir) / "coeffs.json",
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )
    monkeypatch.setattr(
        "spectralbridge.qa_plots.render_drone_panel",
        _fake_render_drone_panel,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.summarize_drone_h5_solar_geometry",
        lambda h5_path: {
            "solar_geometry_source": "raster",
            "acquisition_datetime_used": None,
            "solar_zenith_mean": 45.0,
            "solar_zenith_min": 45.0,
            "solar_zenith_max": 45.0,
            "solar_azimuth_mean": 180.0,
            "solar_azimuth_min": 180.0,
            "solar_azimuth_max": 180.0,
        },
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


def test_run_drone_pipeline_reports_progress_and_statuses(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for stem in ("SPR1-06-28-23-ExportPackage", "SPR2-06-28-23-ExportPackage"):
        h5_path = input_dir / stem / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
        h5_path.parent.mkdir(parents=True, exist_ok=True)
        h5_path.write_bytes(stem.encode("utf-8"))

    _patch_basic_drone_runtime(monkeypatch)

    run_drone_pipeline(input_dir, output_dir=tmp_path / "out", apply_topo=False)

    captured = capsys.readouterr()
    assert "[drone] Starting batch: 2 discovered | 2 to process" in captured.err
    assert "[drone] [1/2] SPR1_20230628 | source=" in captured.err
    assert "| type=h5 | stage=preparing working H5" in captured.err
    assert "[drone] [2/2] SPR2_20230628 -> success_qa_only_no_polygons (" in captured.err
    assert "[drone] Complete: 2 total | 2 success_total | 0 success_extracted | 0 success_qa_only_no_polygon_overlap | 2 success_qa_only_no_polygons | 0 failed_other" in captured.err


def test_run_drone_pipeline_builds_qa_summary_pdf(
    tmp_path: Path, monkeypatch
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    h5_path = (
        input_dir
        / "SPR1-06-28-23-ExportPackage"
        / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
    )
    h5_path.parent.mkdir(parents=True, exist_ok=True)
    h5_path.write_bytes(b"a")

    _patch_basic_drone_runtime(monkeypatch)

    summary_calls: list[Path] = []

    def _fake_build_summary(base_dir: Path, output_html=None, pattern="*__qa.png"):
        summary_calls.append(Path(base_dir))
        html_path = Path(base_dir) / "qa_summary.pdf"
        html_path.write_text("summary", encoding="utf-8")
        return html_path

    monkeypatch.setattr(
        "spectralbridge.utils.qa_summary.build_drone_qa_summary",
        _fake_build_summary,
    )

    results = run_drone_pipeline(
        input_dir,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    assert summary_calls == [tmp_path / "out"]
    assert results["qa_summary_pdf"] == str(tmp_path / "out" / "qa_summary.pdf")
    assert results["qa_summary"]["qa_summary_pdf"] == str(
        tmp_path / "out" / "qa_summary.pdf"
    )
    assert results["qa_summary"]["qa_summary_pdf_filename"] == "qa_summary.pdf"


def test_run_drone_pipeline_writes_audit_json_when_correction_unavailable(
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

    _patch_basic_drone_runtime(monkeypatch)
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._has_required_ancillary",
        lambda cube, names: False,
    )

    results = run_drone_pipeline(
        h5_path.parent,
        output_dir=tmp_path / "out",
        apply_topo=True,
        apply_brdf=True,
    )

    assert results["processed"] == []
    assert len(results["failed"]) == 1
    file_summary = results["qa_summary"]["files"][0]
    assert file_summary["status"] == "failed_other"
    assert file_summary["flags"]["correction_failed"] is True
    assert file_summary["flags"]["topo_ready"] is False
    assert file_summary["flags"]["brdf_ready"] is False
    assert "required ancillary geometry was unavailable" in str(
        file_summary["correction_failure_reason"]
    )
    assert not Path(file_summary["corrected_raster_path"]).exists()
    qa_json_path = Path(file_summary["qa_json_path"])
    assert qa_json_path.exists()
    qa_payload = json.loads(qa_json_path.read_text(encoding="utf-8"))
    assert qa_payload["qa_rendered"] is False
    assert qa_payload["status"] == "failed_other"
    assert "required ancillary geometry was unavailable" in str(qa_payload["error"])
    assert qa_payload["audit"]["flags"]["correction_failed"] is True


def test_run_drone_pipeline_classifies_no_overlap_and_other_errors_and_continues(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    package_names = (
        "SPR1-06-28-23-ExportPackage",
        "SPR2-06-28-23-ExportPackage",
        "SPR3-06-28-23-ExportPackage",
    )
    for package in package_names:
        h5_path = input_dir / package / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
        h5_path.parent.mkdir(parents=True, exist_ok=True)
        h5_path.write_bytes(package.encode("utf-8"))
    polygon_path = tmp_path / "plots.geojson"
    polygon_path.write_text("{}", encoding="utf-8")

    _patch_basic_drone_runtime(monkeypatch)
    diagnostics_by_flight = {
        "SPR1_20230628__corrected": {
            "raster_crs": "EPSG:32613",
            "polygon_crs": "EPSG:4326",
            "polygon_reprojected": True,
            "bounds_overlap_after_reproject": True,
            "intersecting_polygon_count": 1,
            "raster_bounds": [0.0, 0.0, 10.0, 10.0],
        },
        "SPR2_20230628__corrected": {
            "raster_crs": "EPSG:32613",
            "polygon_crs": "EPSG:4326",
            "polygon_reprojected": True,
            "bounds_overlap_after_reproject": False,
            "intersecting_polygon_count": 0,
            "raster_bounds": [0.0, 0.0, 10.0, 10.0],
        },
        "SPR3_20230628__corrected": {
            "raster_crs": "EPSG:32613",
            "polygon_crs": "EPSG:4326",
            "polygon_reprojected": True,
            "bounds_overlap_after_reproject": True,
            "intersecting_polygon_count": 1,
            "raster_bounds": [0.0, 0.0, 10.0, 10.0],
        },
    }

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.collect_drone_spatial_diagnostics",
        lambda *, raster_img, polygons_path: diagnostics_by_flight[Path(raster_img).stem],
    )

    def _fake_overlay_plot(**kwargs):
        output_path = Path(kwargs["output_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"png")
        return output_path

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.save_drone_overlay_debug_plot",
        _fake_overlay_plot,
    )

    def _fake_build_index(**kwargs):
        output_path = kwargs["output_path"]
        flight_id = kwargs["flight_id"]
        if flight_id == "SPR2_20230628":
            raise ValueError("No pixels intersected the supplied polygons")
        if flight_id == "SPR3_20230628":
            raise RuntimeError("unexpected correction issue")
        output_path.write_text("index", encoding="utf-8")
        return output_path

    def _fake_extract(
        envi_img, envi_hdr, polygon_index_path, output_parquet_path, overwrite=False
    ):
        output_parquet_path.write_text("ok", encoding="utf-8")
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
        "spectralbridge.pipelines.drone._enrich_drone_polygon_parquet_with_index",
        _fake_polygon_enrichment,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._export_csv_copy_from_parquet",
        _fake_csv_export,
    )

    results = run_drone_pipeline(
        input_dir,
        polygon_path=polygon_path,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    captured = capsys.readouterr()
    assert "SPR2_20230628 -> success_qa_only_no_polygon_overlap" in captured.err
    assert "SPR3_20230628 -> failed_other: unexpected correction issue" in captured.err
    assert "Complete: 3 total | 2 success_total | 1 success_extracted | 1 success_qa_only_no_polygon_overlap | 0 success_qa_only_no_polygons | 1 failed_other" in captured.err

    statuses = {
        entry["flight_stem"]: entry["status"]
        for entry in results["qa_summary"]["files"]
    }
    assert statuses == {
        "SPR1_20230628": "success_extracted",
        "SPR2_20230628": "success_qa_only_no_polygon_overlap",
        "SPR3_20230628": "failed_other",
    }
    assert len(results["processed"]) == 2
    assert len(results["failed"]) == 1
    assert len(results["outputs"]) == 1
    assert results["merged"] == str(tmp_path / "out" / "drone_merged.parquet")
    assert results["merged_csv"] == str(tmp_path / "out" / "drone_merged.csv")
    assert results["qa_summary"]["success_count"] == 2
    assert results["qa_summary"]["success_extracted_count"] == 1
    assert results["qa_summary"]["success_qa_only_no_polygon_overlap_count"] == 1
    assert results["qa_summary"]["success_qa_only_no_polygons_count"] == 0
    assert results["qa_summary"]["skipped_no_polygon_overlap_count"] == 1
    assert results["qa_summary"]["failed_other_count"] == 1
    assert results["qa_summary"]["status_counts"] == {
        "success_extracted": 1,
        "success_qa_only_no_polygon_overlap": 1,
        "success_qa_only_no_polygons": 0,
        "failed_other": 1,
    }
    file_entries = {
        entry["flight_stem"]: entry for entry in results["qa_summary"]["files"]
    }
    assert file_entries["SPR2_20230628"]["spatial_diagnostics"] == diagnostics_by_flight[
        "SPR2_20230628__corrected"
    ]
    assert file_entries["SPR2_20230628"]["polygon_extraction_attempted"] is True
    assert file_entries["SPR2_20230628"]["polygon_extraction_ran"] is False
    assert "No pixels intersected" in str(
        file_entries["SPR2_20230628"]["polygon_extraction_skipped_reason"]
    )
    assert file_entries["SPR2_20230628"]["spatial_diagnostics"][
        "bounds_overlap_after_reproject"
    ] is False
    assert file_entries["SPR2_20230628"]["overlay_debug_filename"] == (
        "SPR2_20230628__overlay_debug.png"
    )
    assert Path(file_entries["SPR2_20230628"]["qa_plot_path"]).exists()
    assert Path(file_entries["SPR3_20230628"]["qa_plot_path"]).exists()
    assert file_entries["SPR2_20230628"]["qa_preview"]["polygon"]["path"] == str(
        polygon_path
    )
    assert file_entries["SPR3_20230628"]["qa_preview"]["polygon"]["path"] == str(
        polygon_path
    )
    assert file_entries["SPR1_20230628"]["polygon_csv_filename"] == (
        "SPR1_20230628__polygons.csv"
    )
    assert file_entries["SPR1_20230628"]["merged_csv_filename"] == "drone_merged.csv"
