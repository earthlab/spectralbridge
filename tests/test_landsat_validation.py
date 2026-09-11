from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from spectralbridge.drone_translation import DroneTranslationBand, DroneTranslationPlan
from spectralbridge.landsat_validation import (
    LandsatObservation,
    _clear_landsat_mask,
    _landsat_cache_signature,
    _load_cached_stac_observation,
    acquire_landsat_observation,
    compare_landsat_common_support,
    load_supplied_landsat_observation,
)

rasterio = pytest.importorskip("rasterio")
from_origin = rasterio.transform.from_origin


def _plan() -> DroneTranslationPlan:
    bands = tuple(
        DroneTranslationBand(
            translation_pair=(
                "MicaSense_to-match_OLI_and_OLI-2__to__Landsat_8_OLI"
            ),
            source_sensor="MicaSense_to-match_OLI_and_OLI-2",
            target_sensor="Landsat_8_OLI",
            coefficient_band_index=index,
            coefficient_source_band_index=index,
            native_source_band_index=index,
            target_band_index=index,
            source_wavelength_nm=wavelength,
            native_source_wavelength_nm=wavelength,
            target_wavelength_nm=target,
            target_fwhm_nm=20.0,
            slope=1.0,
            intercept=0.0,
            x_min=0.0,
            x_max=1.0,
            x_mean=0.3,
            r2=0.99,
        )
        for index, (wavelength, target) in enumerate(
            zip(
                [444.0, 475.0, 560.0, 668.0, 862.0],
                [443.0, 482.0, 561.4, 654.6, 864.7],
            ),
            start=1,
        )
    )
    return DroneTranslationPlan(
        analysis_run_id="run-1",
        analysis_level="site_balanced",
        weighting_description="each site has equal total weight",
        source_sensor="MicaSense_to-match_OLI_and_OLI-2",
        target_sensor="Landsat_8_OLI",
        translation_pair=(
            "MicaSense_to-match_OLI_and_OLI-2__to__Landsat_8_OLI"
        ),
        coefficient_path="coefficients.parquet",
        coefficient_sha256="abc",
        evidence_boundary="synthetic evidence",
        candidate_status="review_required",
        bands=bands,
    )


def _write_tif(
    path: Path,
    data: np.ndarray,
    *,
    pixel_size: float,
    tags: dict[str, str] | None = None,
) -> Path:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[2],
        height=data.shape[1],
        count=data.shape[0],
        dtype="float32",
        crs="EPSG:32613",
        transform=from_origin(500000, 4400000, pixel_size, pixel_size),
        nodata=-9999.0,
    ) as destination:
        destination.write(data.astype(np.float32))
        if tags:
            destination.update_tags(**tags)
    return path


def test_collection_2_clear_mask_rejects_cloud_shadow_snow_and_fill() -> None:
    qa = np.array([0, 1, 1 << 3, 1 << 4, 1 << 5, 1 << 6], dtype=np.uint16)
    assert _clear_landsat_mask(qa).tolist() == [True, False, False, False, False, True]


def test_landsat_crop_cache_requires_matching_request_and_valid_raster(
    tmp_path: Path,
) -> None:
    product_id = "LC08_cache_fixture"
    target_sensor = "Landsat_8_OLI"
    raster_path = _write_tif(
        tmp_path / "crop.tif",
        np.ones((5, 2, 2), dtype=np.float32),
        pixel_size=30,
        tags={"target_sensor": target_sensor, "product_id": product_id},
    )
    with rasterio.open(raster_path, "r+") as destination:
        for index, name in enumerate(
            ("coastal", "blue", "green", "red", "nir08"), start=1
        ):
            destination.set_band_description(index, name)
    metadata_path = tmp_path / "observation.json"
    observation = LandsatObservation(
        product_id=product_id,
        target_sensor=target_sensor,
        acquisition_datetime="2026-06-10T00:00:00+00:00",
        cloud_cover=4.0,
        raster_path=str(raster_path),
        metadata_path=str(metadata_path),
        source="planetary_computer_stac",
        temporal_offset_days=1.0,
        band_common_names=("coastal", "blue", "green", "red", "nir08"),
        target_band_indices=(1, 2, 3, 4, 5),
        wavelengths_nm=(443.0, 482.0, 561.4, 654.6, 864.7),
        scene_selection="fixture",
    )
    signature, contract = _landsat_cache_signature(
        product_id=product_id,
        target_sensor=target_sensor,
        bounds_wgs84=(-105.5, 39.9, -105.4, 40.0),
        temporal_offset_days=1.0,
        cloud_cover=4.0,
    )
    metadata_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "cache_signature_sha256": signature,
                "cache_contract": contract,
                "observation": asdict(observation),
            }
        ),
        encoding="utf-8",
    )
    cached = _load_cached_stac_observation(
        raster_path=raster_path,
        metadata_path=metadata_path,
        expected_signature=signature,
        product_id=product_id,
        target_sensor=target_sensor,
    )
    assert cached == observation

    changed_signature, _ = _landsat_cache_signature(
        product_id=product_id,
        target_sensor=target_sensor,
        bounds_wgs84=(-105.6, 39.9, -105.4, 40.0),
        temporal_offset_days=1.0,
        cloud_cover=4.0,
    )
    assert changed_signature != signature
    assert (
        _load_cached_stac_observation(
            raster_path=raster_path,
            metadata_path=metadata_path,
            expected_signature=changed_signature,
            product_id=product_id,
            target_sensor=target_sensor,
        )
        is None
    )

    raster_path.write_bytes(b"corrupt")
    assert (
        _load_cached_stac_observation(
            raster_path=raster_path,
            metadata_path=metadata_path,
            expected_signature=signature,
            product_id=product_id,
            target_sensor=target_sensor,
        )
        is None
    )


def test_mocked_scene_discovery_selects_nearest_acceptable_scene(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Item:
        def __init__(self, item_id: str, date: str, cloud: float):
            self.id = item_id
            self.properties = {
                "platform": "landsat-8",
                "datetime": date,
                "eo:cloud_cover": cloud,
            }

    far = Item("LC08_far", "2026-06-01T00:00:00Z", 2.0)
    near = Item("LC08_near", "2026-06-09T00:00:00Z", 20.0)

    class Search:
        def items(self):
            return [far, near]

    class ClientInstance:
        def search(self, **_kwargs):
            return Search()

    fake_client = SimpleNamespace(open=lambda *_args, **_kwargs: ClientInstance())
    monkeypatch.setitem(sys.modules, "pystac_client", SimpleNamespace(Client=fake_client))
    monkeypatch.setitem(
        sys.modules,
        "planetary_computer",
        SimpleNamespace(sign_inplace=lambda item: item),
    )
    chosen: list[str] = []

    def fake_crop(item, **kwargs):
        chosen.append(item.id)
        return LandsatObservation(
            product_id=item.id,
            target_sensor=kwargs["target_sensor"],
            acquisition_datetime=item.properties["datetime"],
            cloud_cover=item.properties["eo:cloud_cover"],
            raster_path=str(tmp_path / "crop.tif"),
            metadata_path=None,
            source="mock",
            temporal_offset_days=kwargs["temporal_offset_days"],
            band_common_names=("coastal", "blue", "green", "red", "nir08"),
            target_band_indices=(1, 2, 3, 4, 5),
            wavelengths_nm=(443.0, 482.0, 561.4, 654.6, 864.7),
            scene_selection="mock",
        )

    monkeypatch.setattr(
        "spectralbridge.landsat_validation._crop_stac_item", fake_crop
    )
    observation = acquire_landsat_observation(
        bounds_wgs84=(-105.5, 39.9, -105.4, 40.0),
        acquisition_datetime=datetime(2026, 6, 10, tzinfo=timezone.utc),
        search_days=15,
        target_sensors=["Landsat_8_OLI"],
        output_dir=tmp_path,
    )
    assert observation is not None
    assert observation.product_id == "LC08_near"
    assert chosen == ["LC08_near"]


def test_mocked_scene_discovery_returns_none_when_cloud_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = SimpleNamespace(
        id="LC08_cloudy",
        properties={
            "platform": "landsat-8",
            "datetime": "2026-06-10T00:00:00Z",
            "eo:cloud_cover": 90.0,
        },
    )
    search = SimpleNamespace(items=lambda: [item])
    client = SimpleNamespace(search=lambda **_kwargs: search)
    fake_client = SimpleNamespace(open=lambda *_args, **_kwargs: client)
    monkeypatch.setitem(sys.modules, "pystac_client", SimpleNamespace(Client=fake_client))
    monkeypatch.setitem(
        sys.modules,
        "planetary_computer",
        SimpleNamespace(sign_inplace=lambda value: value),
    )
    assert (
        acquire_landsat_observation(
            bounds_wgs84=(-105.5, 39.9, -105.4, 40.0),
            acquisition_datetime="2026-06-10T00:00:00Z",
            search_days=5,
            target_sensors=["Landsat_8_OLI"],
            output_dir=tmp_path,
            cloud_cover_max=50,
        )
        is None
    )


def test_supplied_landsat_raster_is_allowed_and_sensor_validated(tmp_path: Path) -> None:
    path = _write_tif(
        tmp_path / "actual.tif",
        np.ones((5, 2, 2), dtype=np.float32),
        pixel_size=30,
        tags={"target_sensor": "Landsat_8_OLI", "product_id": "LC08_fixture"},
    )
    observation = load_supplied_landsat_observation(
        path, target_sensors=["Landsat_8_OLI"]
    )
    assert observation.source == "user_supplied"
    assert observation.product_id == "LC08_fixture"
    assert observation.target_sensor == "Landsat_8_OLI"


def test_common_support_aggregates_drone_and_neon_to_landsat_grid(
    tmp_path: Path,
) -> None:
    plan = _plan()
    drone_data = np.stack(
        [np.full((4, 4), 0.10 * index, dtype=np.float32) for index in range(1, 6)]
    )
    actual_data = np.stack(
        [np.full((2, 2), 0.10 * index + 0.01, dtype=np.float32) for index in range(1, 6)]
    )
    neon_data = actual_data.repeat(2, axis=1).repeat(2, axis=2)
    drone = _write_tif(tmp_path / "drone.tif", drone_data, pixel_size=1)
    neon = _write_tif(tmp_path / "neon.tif", neon_data, pixel_size=1)
    actual = _write_tif(tmp_path / "actual.tif", actual_data, pixel_size=2)
    observation = LandsatObservation(
        product_id="LC08_fixture",
        target_sensor="Landsat_8_OLI",
        acquisition_datetime="2026-06-10T00:00:00+00:00",
        cloud_cover=0.0,
        raster_path=str(actual),
        metadata_path=None,
        source="fixture",
        temporal_offset_days=None,
        band_common_names=("coastal", "blue", "green", "red", "nir08"),
        target_band_indices=(1, 2, 3, 4, 5),
        wavelengths_nm=(443.0, 482.0, 561.4, 654.6, 864.7),
        scene_selection="fixture",
    )
    result = compare_landsat_common_support(
        translated_img=drone,
        plan=plan,
        observation=observation,
        output_dir=tmp_path / "qa",
        neon_product=neon,
        drone_acquisition_datetime="2026-06-09T00:00:00+00:00",
        neon_acquisition_datetime="2026-06-08T00:00:00+00:00",
    )
    assert result["common_grid"]["reference"] == "actual Landsat grid"
    assert Path(result["common_grid"]["common_support_product"]).exists()
    assert Path(result["common_grid"]["neon_common_support_product"]).exists()
    assert result["temporal_context"]["drone_to_landsat_offset_days"] == 1.0
    assert result["temporal_context"]["neon_to_landsat_offset_days"] == 2.0
    assert len(result["bands"]) == 5
    assert result["bands"][0]["drone_vs_actual"]["mean_bias"] == pytest.approx(-0.01)
    assert result["bands"][0]["neon_vs_actual"]["rmse"] == pytest.approx(0.0)
    assert result["bands"][0]["drone_vs_neon"]["mae"] == pytest.approx(0.01)
