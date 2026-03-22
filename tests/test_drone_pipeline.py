from __future__ import annotations

from pathlib import Path

import json

import pytest
import numpy as np

from spectralbridge.pipelines import run_drone_pipeline
from spectralbridge.pipelines.drone import (
    DRONE_TARGET_BANDS,
    build_drone_output_paths,
    collect_drone_spatial_diagnostics,
    _prepare_drone_h5_working_copy,
    clean_name,
    derive_drone_flight_stem,
    resolve_band_map,
    save_drone_overlay_debug_plot,
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
        "spectralbridge.pipelines.drone.is_valid_envi_pair",
        lambda img, hdr: img.exists() and hdr.exists(),
    )
    monkeypatch.setattr(
        "spectralbridge.qa_plots.render_drone_panel",
        _fake_render_drone_panel,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._extract_drone_parquet_from_envi",
        _fake_extract_drone_parquet,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._merge_drone_parquet_outputs",
        _fake_merge_drone_parquets,
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


def _fake_extract_drone_parquet(
    envi_img,
    envi_hdr,
    output_parquet_path,
    *,
    pixel_index_path=None,
    overwrite=False,
    chunk_size=50_000,
):
    output_parquet_path = Path(output_parquet_path)
    output_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": Path(envi_img).name,
        "index": str(pixel_index_path) if pixel_index_path is not None else None,
    }
    output_parquet_path.write_text(json.dumps(payload), encoding="utf-8")
    return output_parquet_path


def _fake_merge_drone_parquets(outputs, output_path, overwrite=False):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(outputs), encoding="utf-8")
    return output_path


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
    assert results["outputs"] == [
        str(tmp_path / "out" / "SPR1_20230628" / "SPR1_20230628__extracted.parquet")
    ]
    assert results["merged"] == str(tmp_path / "out" / "drone_merged.parquet")
    qa_summary = results["qa_summary"]
    assert qa_summary["platform"] == "drone"
    assert qa_summary["convolution"] == "skipped"
    assert qa_summary["merged_path"] == str(tmp_path / "out" / "drone_merged.parquet")
    assert qa_summary["merged_preview"]["path"] == str(tmp_path / "out" / "drone_merged.parquet")
    file_summary = qa_summary["files"][0]
    assert file_summary["flight_stem"] == "SPR1_20230628"
    assert file_summary["status"] == "success"
    assert file_summary["resolved_band_map"]["nir"]["index"] == 3
    assert file_summary["working_h5_filename"] == "SPR1_20230628__working.h5"
    assert file_summary["working_raster"] == "SPR1_20230628__envi.img"
    assert file_summary["corrected_raster"] == "SPR1_20230628__corrected.img"
    assert file_summary["extracted_parquet_filename"] == "SPR1_20230628__extracted.parquet"
    assert file_summary["extracted_parquet_path"] == str(
        tmp_path / "out" / "SPR1_20230628" / "SPR1_20230628__extracted.parquet"
    )
    assert file_summary["polygon_filename"] is None
    assert file_summary["merged_path"] == str(tmp_path / "out" / "drone_merged.parquet")
    assert file_summary["qa_plot_filename"] == "SPR1_20230628__qa.png"
    assert file_summary["qa_json_filename"] == "SPR1_20230628__qa.json"
    assert Path(file_summary["flight_dir"]) == tmp_path / "out" / "SPR1_20230628"
    assert Path(results["qa_summary_path"]).exists()


def test_run_drone_pipeline_without_polygons_writes_per_flight_parquets(
    tmp_path: Path, monkeypatch
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    h5_paths = []
    for stem in ("SPR1-06-28-23-ExportPackage", "SPR2-06-28-23-ExportPackage"):
        h5_path = input_dir / stem / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
        h5_path.parent.mkdir(parents=True, exist_ok=True)
        h5_path.write_bytes(stem.encode("utf-8"))
        h5_paths.append(h5_path)

    _patch_basic_drone_runtime(monkeypatch)

    results = run_drone_pipeline(
        input_dir,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    expected_outputs = {
        str(tmp_path / "out" / "SPR1_20230628" / "SPR1_20230628__extracted.parquet"),
        str(tmp_path / "out" / "SPR2_20230628" / "SPR2_20230628__extracted.parquet"),
    }
    assert set(results["processed"]) == {str(path) for path in h5_paths}
    assert set(results["outputs"]) == expected_outputs
    for output in expected_outputs:
        assert Path(output).exists()
    qa_entries = {entry["flight_stem"]: entry for entry in results["qa_summary"]["files"]}
    assert qa_entries["SPR1_20230628"]["extracted_parquet_filename"] == (
        "SPR1_20230628__extracted.parquet"
    )
    assert qa_entries["SPR2_20230628"]["extracted_parquet_filename"] == (
        "SPR2_20230628__extracted.parquet"
    )
    assert all(entry["polygon_filename"] is None for entry in qa_entries.values())


def test_run_drone_pipeline_merges_from_written_per_flight_parquets(
    tmp_path: Path, monkeypatch
) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for stem in ("SPR1-06-28-23-ExportPackage", "SPR2-06-28-23-ExportPackage"):
        h5_path = input_dir / stem / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
        h5_path.parent.mkdir(parents=True, exist_ok=True)
        h5_path.write_bytes(stem.encode("utf-8"))

    _patch_basic_drone_runtime(monkeypatch)

    merge_calls: list[list[str]] = []

    def _recording_merge(outputs, output_path, overwrite=False):
        merge_calls.append(list(outputs))
        return _fake_merge_drone_parquets(outputs, output_path, overwrite=overwrite)

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._merge_drone_parquet_outputs",
        _recording_merge,
    )

    results = run_drone_pipeline(
        input_dir,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    assert results["merged"] == str(tmp_path / "out" / "drone_merged.parquet")
    assert merge_calls == [results["outputs"]]
    merged_text = Path(results["merged"]).read_text(encoding="utf-8").splitlines()
    assert merged_text == results["outputs"]
    assert all(Path(path).exists() for path in merged_text)


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
        envi_img,
        envi_hdr,
        output_parquet_path,
        *,
        pixel_index_path=None,
        overwrite=False,
        chunk_size=50_000,
    ):
        output_parquet_path.write_text(output_parquet_path.stem, encoding="utf-8")
        assert pixel_index_path is not None
        return output_parquet_path

    def _fake_merge(outputs, output_path, overwrite=False):
        output_path.write_text("\n".join(outputs), encoding="utf-8")
        return output_path

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._build_polygon_pixel_index_for_raster",
        _fake_build_index,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._extract_drone_parquet_from_envi",
        _fake_extract,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._merge_drone_parquet_outputs", _fake_merge
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
    assert Path(results["merged"]).exists()
    qa_files = results["qa_summary"]["files"]
    assert {entry["polygon_filename"] for entry in qa_files} == {
        "SPR1_20230628__polygons.parquet",
        "SPR2_20230628__polygons.parquet",
    }
    assert {entry["extracted_parquet_filename"] for entry in qa_files} == {
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
    assert {entry["status"] for entry in qa_files} == {"success"}


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
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._extract_drone_parquet_from_envi",
        _fake_extract_drone_parquet,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._merge_drone_parquet_outputs",
        _fake_merge_drone_parquets,
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
    assert "stage=preparing H5" in captured.err
    assert "[drone] [2/2] SPR2_20230628 -> success (" in captured.err
    assert "[drone] Complete: 2 total | 2 success | 0 skipped_no_polygon_overlap | 0 failed_other" in captured.err


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
        envi_img,
        envi_hdr,
        output_parquet_path,
        *,
        pixel_index_path=None,
        overwrite=False,
        chunk_size=50_000,
    ):
        output_parquet_path.write_text("ok", encoding="utf-8")
        assert pixel_index_path is not None
        return output_parquet_path

    def _fake_merge(outputs, output_path, overwrite=False):
        output_path.write_text("\n".join(outputs), encoding="utf-8")
        return output_path

    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._build_polygon_pixel_index_for_raster",
        _fake_build_index,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._extract_drone_parquet_from_envi",
        _fake_extract,
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._merge_drone_parquet_outputs", _fake_merge
    )

    results = run_drone_pipeline(
        input_dir,
        polygon_path=polygon_path,
        output_dir=tmp_path / "out",
        apply_topo=False,
    )

    captured = capsys.readouterr()
    assert "SPR2_20230628 -> skipped_no_polygon_overlap" in captured.err
    assert "SPR3_20230628 -> failed_other: unexpected correction issue" in captured.err
    assert "Complete: 3 total | 1 success | 1 skipped_no_polygon_overlap | 1 failed_other" in captured.err

    statuses = {
        entry["flight_stem"]: entry["status"]
        for entry in results["qa_summary"]["files"]
    }
    assert statuses == {
        "SPR1_20230628": "success",
        "SPR2_20230628": "skipped_no_polygon_overlap",
        "SPR3_20230628": "failed_other",
    }
    assert len(results["processed"]) == 2
    assert len(results["failed"]) == 1
    assert len(results["outputs"]) == 1
    assert results["merged"] == str(tmp_path / "out" / "drone_merged.parquet")
    assert results["qa_summary"]["success_count"] == 1
    assert results["qa_summary"]["skipped_no_polygon_overlap_count"] == 1
    assert results["qa_summary"]["failed_other_count"] == 1
    assert results["qa_summary"]["status_counts"] == {
        "success": 1,
        "skipped_no_polygon_overlap": 1,
        "failed_other": 1,
    }
    file_entries = {
        entry["flight_stem"]: entry for entry in results["qa_summary"]["files"]
    }
    assert file_entries["SPR2_20230628"]["spatial_diagnostics"] == diagnostics_by_flight[
        "SPR2_20230628__corrected"
    ]
    assert file_entries["SPR2_20230628"]["spatial_diagnostics"][
        "bounds_overlap_after_reproject"
    ] is False
    assert file_entries["SPR2_20230628"]["overlay_debug_filename"] == (
        "SPR2_20230628__overlay_debug.png"
    )
