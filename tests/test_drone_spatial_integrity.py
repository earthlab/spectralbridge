"""Independent rasterio/shapely checks of drone pixel geographic identity."""

from pathlib import Path

import geopandas as gpd
import h5py
import numpy as np
import pandas as pd
import pytest
import rasterio
from affine import Affine
from shapely.geometry import Point, box

from spectralbridge.neon_cube import NeonCube
from spectralbridge.pipelines.drone import (
    _build_polygon_pixel_index_for_raster,
    _prepare_drone_source_working_h5,
    apply_drone_corrections,
    convert_drone_tiff_to_h5,
    export_h5_to_envi,
)
from spectralbridge.polygons import extract_polygon_parquet_from_envi


def source(tmp_path, transform=None, epsg=32613):
    transform = transform or Affine(
        0.123456789, 0, 457624.1234567, 0, -0.234567891, 4432830.9876543
    )
    data = np.arange(3 * 5 * 7, dtype="float32").reshape(3, 5, 7) + 100
    data[:, 0, 0] = -9999
    path = tmp_path / "reflectance.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=7,
        height=5,
        count=3,
        dtype="float32",
        crs=f"EPSG:{epsg}",
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(data)
    return path, data, transform


def convert(path, out, **kwargs):
    return convert_drone_tiff_to_h5(
        path,
        output_h5_path=out,
        radiometry={"scale":1., "offset":0., "status":"VALID", "provenance":"Synthetic pixel-identity fixture"},
        wavelengths_nm=[500, 650, 860],
        fwhm_nm=[10, 10, 10],
        **kwargs,
    )


@pytest.mark.parametrize("epsg", [32613, 32719, 5070, 26913])
def test_tiff_h5_envi_pixel_identity(tmp_path, epsg):
    path, data, transform = source(tmp_path, epsg=epsg)
    h5 = convert(path, tmp_path / "working.h5")
    cube = NeonCube(h5)
    np.testing.assert_array_equal(cube.data, np.moveaxis(data, 0, 2))
    np.testing.assert_allclose(cube.transform, transform.to_gdal(), atol=1e-9, rtol=0)
    img, _ = export_h5_to_envi(h5, output_stem=tmp_path / "native")
    with rasterio.open(img) as ds:
        assert ds.crs == rasterio.crs.CRS.from_epsg(epsg)
        np.testing.assert_allclose(
            tuple(ds.transform), tuple(transform), atol=1e-9, rtol=0
        )
        np.testing.assert_array_equal(ds.read(), data)
        np.testing.assert_array_equal(
            ds.read_masks(), (data != -9999).astype("uint8") * 255
        )
    window = NeonCube(h5, sample_slice=(2, 6), line_slice=(1, 4))
    expected = transform * Affine.translation(2, 1)
    np.testing.assert_allclose(window.transform, expected.to_gdal(), atol=1e-9, rtol=0)
    np.testing.assert_array_equal(window.data, np.moveaxis(data[:, 1:4, 2:6], 0, 2))


@pytest.mark.parametrize(
    "transform",
    [
        Affine(1, 0, 1, 0, 1, 2),
        Affine(-1, 0, 1, 0, -1, 2),
        Affine(1, 0.1, 1, 0, -1, 2),
        Affine(1, 0, 1, 0.1, -1, 2),
    ],
)
def test_unsupported_geometry_rejected_before_output(tmp_path, transform):
    path, _, _ = source(tmp_path, transform)
    out = tmp_path / "working.h5"
    with pytest.raises(ValueError, match="north-up|rotation|shear"):
        convert(path, out)
    assert not out.exists()


def test_ancillary_alignment_and_values(tmp_path):
    path, _, transform = source(tmp_path)
    ancillary = tmp_path / "slope.tif"
    values = np.arange(35, dtype="float32").reshape(5, 7)
    with rasterio.open(path) as src:
        profile = src.profile.copy()
    profile.update(count=1)
    with rasterio.open(ancillary, "w", **profile) as dst:
        dst.write(values, 1)
    cube = NeonCube(convert(path, tmp_path / "working.h5", slope_tiff=ancillary))
    np.testing.assert_array_equal(cube.get_ancillary("slope", radians=False), values)
    profile.update(transform=transform * Affine.translation(0, 1))
    with rasterio.open(ancillary, "w", **profile) as dst:
        dst.write(values, 1)
    with pytest.raises(ValueError, match="transform does not match"):
        convert(path, tmp_path / "other.h5", slope_tiff=ancillary)


def test_boundary_polygon_extraction_matches_source_centers(tmp_path):
    path, data, transform = source(tmp_path)
    h5 = convert(path, tmp_path / "working.h5")
    img, hdr = export_h5_to_envi(h5, output_stem=tmp_path / "native")
    corrected, corrected_hdr, audit = apply_drone_corrections(
        cube=NeonCube(h5),
        envi_img=img,
        envi_hdr=hdr,
        corrected_stem=tmp_path / "corrected",
        apply_topo=False,
        apply_brdf=False,
    )
    assert not audit["brdf_applied"]
    # Deliberately close to top/left edge: a half-pixel shift changes membership.
    x0, y0 = transform * (0.51, 0.51)
    x1, y1 = transform * (2.49, 2.49)
    polygon = box(x0, y1, x1, y0)
    polygons = tmp_path / "plots.geojson"
    gpd.GeoDataFrame(
        {"polygon_id": [19], "cover_category": ["Evergreen"]},
        geometry=[polygon],
        crs=32613,
    ).to_file(polygons)
    index_path = _build_polygon_pixel_index_for_raster(
        raster_img=corrected,
        raster_hdr=corrected_hdr,
        polygons_path=polygons,
        output_path=tmp_path / "index.parquet",
        flight_id="fixture",
    )
    index = pd.read_parquet(index_path)
    expected = {
        (r, c)
        for r in range(5)
        for c in range(7)
        if polygon.contains(Point(*(transform * (c + 0.5, r + 0.5))))
    }
    assert set(zip(index.row, index.col)) == expected
    assert set(index.polygon_id) == {19}
    assert set(index.cover_category) == {"Evergreen"}
    for row in index.itertuples():
        np.testing.assert_allclose(
            [row.x, row.y],
            transform * (row.col + 0.5, row.row + 0.5),
            atol=1e-9,
            rtol=0,
        )
    pq = extract_polygon_parquet_from_envi(
        corrected, corrected_hdr, index_path, tmp_path / "spectra.parquet"
    )
    df = pd.read_parquet(pq)
    assert set(zip(df.row, df.col)) == expected
    with rasterio.open(corrected) as ds:
        np.testing.assert_array_equal(ds.read(), data)
        for row in df.itertuples():
            np.testing.assert_array_equal(
                ds.read()[:, row.row, row.col], data[:, row.row, row.col]
            )


def test_conflicting_h5_y_convention_rejected_even_with_cached_export(tmp_path):
    path, _, _ = source(tmp_path)
    h5 = convert(path, tmp_path / "working.h5")
    export_h5_to_envi(h5, output_stem=tmp_path / "native")
    with h5py.File(h5, "r+") as f:
        coord = next(iter(f.values()))["Reflectance/Metadata/Coordinate_System"]
        info = coord["Map_Info"][()].decode().split(",")
        info[6] = "-0.234567891"
        coord["Map_Info"][()] = ",".join(info)
    with pytest.raises(ValueError, match="spatial|north-up|Map_Info"):
        export_h5_to_envi(h5, output_stem=tmp_path / "native")


def test_working_h5_spatial_cache_revision(tmp_path):
    path, _, _ = source(tmp_path)
    out = tmp_path / "working.h5"
    kwargs = dict(
        source_type="tiff",
        working_path=out,
        tiff_wavelengths_nm=[500, 650, 860],
        tiff_fwhm_nm=[10] * 3,
    )
    _prepare_drone_source_working_h5(path, **kwargs)
    mtime = out.stat().st_mtime_ns
    _prepare_drone_source_working_h5(path, **kwargs)
    assert out.stat().st_mtime_ns == mtime
    import json

    marker = out.with_suffix(".stage.json")
    record = json.loads(marker.read_text())
    assert record["configuration"]["algorithm_version"] >= 3


def test_corrected_and_translated_grid_and_nodata(tmp_path, monkeypatch):
    """Real writers and translation; controlled radiometry separates pixel identity."""
    from spectralbridge.drone_translation import (
        DroneTranslationBand,
        DroneTranslationPlan,
        apply_drone_translation,
    )

    path, data, transform = source(tmp_path, epsg=5070)
    h5 = convert(path, tmp_path / "working.h5", slope_tiff=None)
    cube = NeonCube(h5)
    img, hdr = export_h5_to_envi(h5, output_stem=tmp_path / "native")
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone._has_required_ancillary", lambda *a: True
    )
    monkeypatch.setattr(
        "spectralbridge.pipelines.drone.apply_topo_correct",
        lambda cube, chunk, *a: np.where(chunk == -9999, chunk, chunk * 2),
    )
    corrected, corrected_hdr, _ = apply_drone_corrections(
        cube=cube,
        envi_img=img,
        envi_hdr=hdr,
        corrected_stem=tmp_path / "corrected",
        apply_topo=True,
        apply_brdf=False,
    )
    bands = tuple(
        DroneTranslationBand(
            translation_pair="fixture",
            source_sensor="MicaSense_to-match_OLI_and_OLI-2",
            target_sensor="Landsat_8_OLI",
            coefficient_band_index=i,
            coefficient_source_band_index=i,
            native_source_band_index=i,
            target_band_index=i,
            source_spectral_identity=f"band{i}",
            target_spectral_identity=f"band{i}",
            source_wavelength_nm=wl,
            native_source_wavelength_nm=wl,
            target_wavelength_nm=wl,
            target_fwhm_nm=10,
            slope=0.5,
            intercept=1,
            x_min=0,
            x_max=1000,
            x_mean=200,
            r2=1,
        )
        for i, wl in enumerate([500, 650, 860], 1)
    )
    plan = DroneTranslationPlan(
        analysis_run_id="fixture",
        analysis_level="site_balanced",
        weighting_description="fixture",
        source_sensor="MicaSense_to-match_OLI_and_OLI-2",
        target_sensor="Landsat_8_OLI",
        translation_pair="fixture",
        coefficient_path="synthetic",
        coefficient_sha256="fixture",
        evidence_boundary="synthetic test only",
        candidate_status="test",
        reflectance_units="physical_reflectance_v1",
        bands=bands,
    )
    result = apply_drone_translation(
        corrected, corrected_hdr, output_stem=tmp_path / "translated", plan=plan
    )
    for stage in [corrected, result["output_img"]]:
        with rasterio.open(stage) as ds:
            assert ds.crs == rasterio.crs.CRS.from_epsg(5070)
            np.testing.assert_allclose(
                tuple(ds.transform), tuple(transform), atol=1e-9, rtol=0
            )
            values = ds.read()
            np.testing.assert_array_equal(values[:, 0, 0], data[:, 0, 0])
            expected = data * 2 if stage == corrected else data + 1
            np.testing.assert_array_equal(values[:, 1:, :], expected[:, 1:, :])


def test_campaign_resume_rejects_conflicting_working_geometry(tmp_path, monkeypatch):
    from spectralbridge.drone_production import validate_bulk_ready_flightline

    path, _, _ = source(tmp_path)
    h5 = convert(path, tmp_path / "flight__working.h5")
    with h5py.File(h5, "r+") as f:
        coord = next(iter(f.values()))["Reflectance/Metadata/Coordinate_System"]
        info = coord["Map_Info"][()].decode().split(",")
        info[6] = "-0.1"
        coord["Map_Info"][()] = ",".join(info)
    validation = validate_bulk_ready_flightline(tmp_path)
    assert not validation.bulk_ready
    assert "spatial metadata conflict" in validation.error


def test_old_tiff_checkpoint_rebuilt_and_new_checkpoint_reused(tmp_path):
    import hashlib
    import json

    path, _, transform = source(tmp_path)
    out = tmp_path / "working.h5"
    kwargs = dict(
        source_type="tiff",
        working_path=out,
        tiff_wavelengths_nm=[500, 650, 860],
        tiff_fwhm_nm=[10] * 3,
    )
    _prepare_drone_source_working_h5(path, **kwargs)
    marker = out.with_suffix(".stage.json")
    record = json.loads(marker.read_text())
    record["configuration"]["algorithm_version"] = 2
    payload = {
        k: record[k] for k in ["schema_version", "stage", "inputs", "configuration"]
    }
    record["stage_signature_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    marker.write_text(json.dumps(record))
    with h5py.File(out, "r+") as f:
        coord = next(iter(f.values()))["Reflectance/Metadata/Coordinate_System"]
        del coord.attrs["spatial_reference_convention"]
    _prepare_drone_source_working_h5(path, **kwargs)
    np.testing.assert_allclose(
        NeonCube(out).transform, transform.to_gdal(), rtol=0, atol=1e-9
    )
    assert json.loads(marker.read_text())["configuration"]["algorithm_version"] == 3
    mtime = out.stat().st_mtime_ns
    _prepare_drone_source_working_h5(path, **kwargs)
    assert out.stat().st_mtime_ns == mtime


def test_legacy_center_reference_keeps_h5_identity_in_drone_export(tmp_path):
    path, _, transform = source(tmp_path)
    h5 = convert(path, tmp_path / "working.h5")
    with h5py.File(h5, "r+") as f:
        coord = next(iter(f.values()))["Reflectance/Metadata/Coordinate_System"]
        del coord.attrs["spatial_reference_convention"]
    # Independent legacy center-coordinate contract, unchanged in NEON reader.
    expected = Affine(
        transform.a,
        0,
        transform.c - transform.a / 2,
        0,
        transform.e,
        transform.f - transform.e / 2,
    )
    cube = NeonCube(h5)
    np.testing.assert_allclose(cube.transform, expected.to_gdal(), atol=1e-9, rtol=0)
    img, _ = export_h5_to_envi(h5, output_stem=tmp_path / "native")
    with rasterio.open(img) as ds:
        np.testing.assert_allclose(
            tuple(ds.transform), tuple(expected), atol=1e-9, rtol=0
        )


def test_pipeline_refreshes_polygon_and_merged_cache_after_grid_change(tmp_path, monkeypatch):
    from spectralbridge.pipelines.drone import run_drone_pipeline

    package = tmp_path / "inputs" / "fixture-08-14-23-ExportPackage"
    package.mkdir(parents=True)
    path = package / "reflectance.tif"
    transform = Affine(1, 0, 500000, 0, -1, 4100000)
    data = np.arange(10 * 5 * 7, dtype="float32").reshape(10, 5, 7) + 300
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=7,
        height=5,
        count=10,
        dtype="float32",
        crs=32613,
        transform=transform,
        nodata=-9999,
    ) as dst:
        dst.write(data)
    polygons = tmp_path / "polygons.geojson"
    gpd.GeoDataFrame(
        {"polygon_id": [8], "cover_category": ["Evergreen"]},
        geometry=[box(500000.1, 4099995.1, 500002.9, 4099999.9)],
        crs=32613,
    ).to_file(polygons)
    # Spatial regression uses explicitly synthetic physical-unit coefficients;
    # the historical count-trained registry is no longer scientific approval.
    from dataclasses import replace
    from spectralbridge.drone_translation import load_drone_translation_plans
    def synthetic_plans(*args, **kwargs):
        return [replace(plan, reflectance_units="physical_reflectance_v1", coefficient_set_version=None,
                        bands=tuple(replace(b, slope=1., intercept=0., x_mean=None, coefficient_set_version=None) for b in plan.bands))
                for plan in load_drone_translation_plans(*args, **kwargs)]
    monkeypatch.setattr("spectralbridge.pipelines.drone.load_drone_translation_plans", synthetic_plans)
    options = dict(
        radiometry={"scale":1., "offset":0., "status":"VALID", "provenance":"Synthetic pixel-identity fixture"},
        polygon_path=polygons,
        output_dir=tmp_path / "out",
        apply_topo=False,
        apply_brdf=False,
        require_solar_geometry=False,
        merge_extractions=True,
        apply_translation=True,
    )
    first = run_drone_pipeline(package, **options)
    audit = first["qa_summary"]["files"][0]
    index = Path(audit["polygon_index_path"])
    original = pd.read_parquet(index)
    # Only change the authoritative grid; pixel arrays stay identical.
    with rasterio.open(path, "r+") as dst:
        dst.transform = transform * Affine.translation(1, 0)
    second = run_drone_pipeline(package, **options)
    assert second["qa_summary"]["files"][0]["spatial_dependencies_refreshed"]
    changed = pd.read_parquet(index)
    assert set(zip(original.row, original.col)) != set(zip(changed.row, changed.col))
    assert set(
        zip(
            pd.read_parquet(second["merged"]).row, pd.read_parquet(second["merged"]).col
        )
    ) == set(zip(changed.row, changed.col))
    tables = [Path(p) for p in second["translated_libraries"]] + [
        Path(second["qa_summary"]["files"][0]["polygon_path"])
    ]
    for table in tables:
        frame = pd.read_parquet(table)
        assert set(zip(frame.row, frame.col)) == set(zip(changed.row, changed.col))
    table_mtimes = {str(p): p.stat().st_mtime_ns for p in tables}
    mtime = index.stat().st_mtime_ns
    third = run_drone_pipeline(package, **options)
    assert not third["qa_summary"]["files"][0]["spatial_dependencies_refreshed"]
    assert index.stat().st_mtime_ns == mtime
    assert table_mtimes == {str(p): p.stat().st_mtime_ns for p in tables}


def test_projected_crs_required(tmp_path):
    path, _, _ = source(tmp_path, epsg=4326)
    with pytest.raises(ValueError, match="projected CRS"):
        convert(path, tmp_path / "working.h5")


def test_campaign_resume_rejects_old_export_revision(tmp_path):
    from spectralbridge.drone_production import validate_bulk_ready_flightline

    path, _, _ = source(tmp_path)
    convert(path, tmp_path / "flight__working.h5")
    validation = validate_bulk_ready_flightline(tmp_path)
    assert not validation.bulk_ready
    assert "export contract is stale" in validation.error


def diagnostic_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "drone_spatial_diagnostic",
        Path(__file__).parents[1] / "scripts/diagnose_drone_spatial_integrity.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_diagnostic_detects_array_flip_even_when_coordinates_match(tmp_path):
    diagnostic = diagnostic_module()
    path, data, _ = source(tmp_path)
    h5 = convert(path, tmp_path / "working.h5")
    img, _ = export_h5_to_envi(h5, output_stem=tmp_path / "native")
    reference, _ = diagnostic.inspect_stage(path, "raster", 1)
    stage, _ = diagnostic.inspect_stage(img, "raster", 1)
    assert diagnostic.compare_controls(reference, stage)["maximum_pixels"] == 0
    assert diagnostic.compare_lossless_pixels(path, stage)["mismatched_values"] == 0
    with rasterio.open(img, "r+") as ds:
        ds.write(data[:, ::-1, :])
    changed, _ = diagnostic.inspect_stage(img, "raster", 1)
    assert diagnostic.compare_controls(reference, changed)["maximum_pixels"] == 0
    assert diagnostic.compare_lossless_pixels(path, changed)["mismatched_values"] > 0


def test_diagnostic_validates_exact_index_and_detects_duplicates(tmp_path):
    diagnostic = diagnostic_module()
    path, _, transform = source(tmp_path)
    h5 = convert(path, tmp_path / "working.h5")
    img, hdr = export_h5_to_envi(h5, output_stem=tmp_path / "native")
    left, bottom = transform * (0, 5)
    right, top = transform * (7, 0)
    gdf = gpd.GeoDataFrame(
        {"polygon_id": [19], "cover_category": ["Evergreen"]},
        geometry=[box(left, bottom, right, top)],
        crs=32613,
    )
    polygons = tmp_path / "plots.geojson"
    gdf.to_file(polygons)
    index = _build_polygon_pixel_index_for_raster(
        raster_img=img,
        raster_hdr=hdr,
        polygons_path=polygons,
        output_path=tmp_path / "index.parquet",
        flight_id="fixture",
    )
    result = diagnostic.compare_parquet(
        index, path, gdf, "polygon_id", "cover_category"
    )
    assert result["complete_index_membership_match"]
    frame = pd.read_parquet(index)
    pd.concat([frame, frame.iloc[:1]], ignore_index=True).to_parquet(index)
    result = diagnostic.compare_parquet(
        index, path, gdf, "polygon_id", "cover_category"
    )
    assert not result["complete_index_membership_match"]
    assert result["duplicate_pixel_records"] == 1


def test_diagnostic_serializes_nan_nodata_without_nonstandard_json(tmp_path):
    import json

    diagnostic = diagnostic_module()
    path, data, _ = source(tmp_path)
    data[data == -9999] = np.nan
    with rasterio.open(path, "r+") as ds:
        ds.nodata = float("nan")
        ds.write(data)
    record, _ = diagnostic.inspect_stage(path, "raster", 1)
    assert record["nodata"] == "NaN"
    assert record["control_points"][0]["value"] is None
    json.dumps(record, allow_nan=False)


def test_lossless_comparison_requires_explicit_band_correspondence(tmp_path):
    diagnostic = diagnostic_module()
    path, data, _ = source(tmp_path)
    selected = tmp_path / "selected.tif"
    with rasterio.open(path) as src:
        profile = src.profile.copy()
    profile.update(count=2)
    with rasterio.open(selected, "w", **profile) as ds:
        ds.write(data[:2])
    h5 = convert_drone_tiff_to_h5(
        selected,
        output_h5_path=tmp_path / "selected.h5",
        wavelengths_nm=[500, 650],
        fwhm_nm=[10, 10],
    )
    img, _ = export_h5_to_envi(h5, output_stem=tmp_path / "native")
    stage, _ = diagnostic.inspect_stage(img, "raster", 1)
    assert (
        diagnostic.compare_lossless_pixels(path, stage)["status"]
        == "different_dimensions"
    )
    assert (
        diagnostic.compare_lossless_pixels(path, stage, source_bands=[1, 2])[
            "mismatched_values"
        ]
        == 0
    )
    assert (
        diagnostic.compare_lossless_pixels(path, stage, source_bands=[2, 3])[
            "mismatched_values"
        ]
        > 0
    )


def test_parquet_value_comparison_uses_explicit_radiometric_reference(tmp_path):
    diagnostic = diagnostic_module()
    path, data, transform = source(tmp_path)
    corrected = tmp_path / "corrected.tif"
    with rasterio.open(path) as src:
        profile = src.profile.copy()
    values = np.where(data == -9999, data, data * 2)
    with rasterio.open(corrected, "w", **profile) as ds:
        ds.write(values)
    x, y = transform * (1.5, 1.5)
    polygon = box(
        x - transform.a * 0.4,
        y + transform.e * 0.4,
        x + transform.a * 0.4,
        y - transform.e * 0.4,
    )
    gdf = gpd.GeoDataFrame(
        {"polygon_id": [19], "cover_category": ["Evergreen"]},
        geometry=[polygon],
        crs=32613,
    )
    table = tmp_path / "pixels.parquet"
    pd.DataFrame(
        {
            "row": [1],
            "col": [1],
            "x": [x],
            "y": [y],
            "polygon_id": [19],
            "cover_category": ["Evergreen"],
            "raw_b001_wl0500nm": [values[0, 1, 1]],
        }
    ).to_parquet(table)
    report = diagnostic.compare_parquet(
        table, path, gdf, "polygon_id", "cover_category", value_raster=corrected
    )
    assert report["complete_retained_membership_match"]
    assert report["raw_value_mismatches"] == 0
    assert (
        diagnostic.compare_parquet(table, path, gdf, "polygon_id", "cover_category")[
            "raw_values_checked"
        ]
        == 0
    )
    assert (
        diagnostic.compare_parquet(
            table, path, gdf, "polygon_id", "cover_category", value_raster=path
        )["raw_value_mismatches"]
        == 1
    )
