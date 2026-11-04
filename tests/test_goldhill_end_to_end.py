"""Synthetic integration contracts for uncalibrated masked drone ingestion."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from spectralbridge.pipelines.drone import (
    convert_drone_tiff_to_h5,
    export_h5_to_envi,
    apply_drone_corrections,
    DroneCorrectionUnavailableError,
)
from spectralbridge.neon_cube import NeonCube
from spectralbridge.radiometry import Radiometry


def test_uncalibrated_fixed_encoding_preserves_grid_mask_zero_and_blocks_physical_stages(
    tmp_path,
):
    source = tmp_path / "source.tif"
    transform = from_origin(500000, 4400000, 0.1, 0.1)
    values = np.broadcast_to(
        np.arange(12, dtype=np.float32).reshape(1, 3, 4), (10, 3, 4)
    ).copy()
    values[:, 1, 2] = np.nan
    mask = np.ones((3, 4), np.uint8) * 255
    mask[1, 2] = 0
    with (
        rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True),
        rasterio.open(
            source,
            "w",
            driver="GTiff",
            height=3,
            width=4,
            count=10,
            dtype="float32",
            crs="EPSG:26913",
            transform=transform,
            nodata=np.nan,
        ) as out,
    ):
        out.write(values)
        out.write_mask(mask)
    declaration = Radiometry(
        None,
        None,
        "UNSUPPORTED",
        "Synthetic fixed numerical encoding; no physical calibration",
        encoding={
            "kind": "range_normalized_dn",
            "physical_calibration_status": "UNVERIFIED",
            "normalization": {"stored_min": 0, "stored_max": 10000},
        },
    )
    h5 = convert_drone_tiff_to_h5(
        source,
        output_h5_path=tmp_path / "work.h5",
        wavelengths_nm=[444, 475, 531, 560, 650, 668, 705, 717, 740, 862],
        fwhm_nm=[28, 32, 14, 27, 16, 14, 10, 12, 18, 57],
        radiometry=declaration.record(),
    )
    cube = NeonCube(h5)
    assert cube.bands == 10
    np.testing.assert_array_equal(cube.mask_no_data, mask > 0)
    assert cube.mask_no_data[0, 0] and cube.data[0, 0, 0] == 0
    img, hdr = export_h5_to_envi(h5, output_stem=tmp_path / "raw", cube=cube)
    with rasterio.open(img) as src:
        assert src.crs.to_epsg() == 26913
        np.testing.assert_allclose(
            tuple(src.transform), tuple(transform), atol=1e-6, rtol=0
        )
        np.testing.assert_array_equal(src.read(), values)
    for topo, brdf in [(True, False), (False, True), (True, True)]:
        stem = tmp_path / f"correction_{topo}_{brdf}"
        with pytest.raises(
            DroneCorrectionUnavailableError, match="Radiometry UNSUPPORTED"
        ):
            apply_drone_corrections(
                cube=cube,
                envi_img=img,
                envi_hdr=hdr,
                corrected_stem=stem,
                apply_topo=topo,
                apply_brdf=brdf,
            )
        assert not stem.with_suffix(".img").exists()
    # Unknown sensor views remain absent; ingestion must not invent nadir.
    with pytest.raises(ValueError, match="sensor_zn"):
        cube.get_ancillary("sensor_zn")
