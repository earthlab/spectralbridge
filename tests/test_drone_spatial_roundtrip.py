"""Independent geometry checks for TIFF-backed drone products; NEON default stays center-based."""

import h5py
import numpy as np
import pytest
import rasterio
from affine import Affine

from spectralbridge.io.neon import _shift_map_info_for_window
from spectralbridge.neon_cube import NeonCube
from spectralbridge.pipelines.drone import convert_drone_tiff_to_h5, export_h5_to_envi


def test_tiff_cube_envi_roundtrip(tmp_path):
    transform = Affine(.123456789, 0, 450000.1234567, 0, -.234567891, 4430000.9876543)
    original = tmp_path / 'original.tif'
    data = np.arange(3 * 4 * 5, dtype='float32').reshape(3, 4, 5)
    with rasterio.open(original, 'w', driver='GTiff', height=4, width=5, count=3,
                       dtype='float32', transform=transform, crs='EPSG:26913') as dst:
        dst.write(data)
    h5 = convert_drone_tiff_to_h5(original, output_h5_path=tmp_path / 'working.h5',
                                wavelengths_nm=[450, 650, 850], fwhm_nm=[10, 10, 10])
    cube = NeonCube(h5)
    np.testing.assert_allclose(cube.transform, transform.to_gdal(), rtol=0, atol=1e-9)
    image, header = export_h5_to_envi(h5, output_stem=tmp_path / 'native')
    with rasterio.open(image) as dst:
        assert dst.crs == rasterio.crs.CRS.from_epsg(26913)
        np.testing.assert_allclose(tuple(dst.transform), tuple(transform), rtol=0, atol=1e-9)
        np.testing.assert_array_equal(dst.read(), data)
    assert 'coordinate system string = {' in header.read_text()
    with h5py.File(h5) as h:
        group = next(iter(h.values()))['Reflectance/Metadata/Coordinate_System']
        assert group.attrs['spatial_reference_convention'] == 'envi_corner_v1'


@pytest.mark.parametrize('transform', [Affine(.1, 0, 1, 0, .1, 2), Affine(-.1, 0, 1, 0, -.1, 2), Affine(.1, .01, 1, 0, -.1, 2)])
def test_unsupported_source_grid_rejected(tmp_path, transform):
    path = tmp_path / 'bad.tif'
    with rasterio.open(path, 'w', driver='GTiff', height=2, width=3, count=3,
                       dtype='float32', transform=transform, crs='EPSG:26913') as dst:
        dst.write(np.ones((3, 2, 3), dtype='float32'))
    with pytest.raises(ValueError):
        convert_drone_tiff_to_h5(path, output_h5_path=tmp_path / 'bad.h5',
                                wavelengths_nm=[450, 650, 850], fwhm_nm=[10, 10, 10])


def test_neon_default_is_unchanged():
    _, transform, _, _ = _shift_map_info_for_window(['UTM', '1', '1', '100', '200', '2', '2'])
    assert transform == (99., 2., 0., 201., 0., -2.)


def test_ancillary_coordinate_roundoff_is_allowed_but_real_shift_is_not(tmp_path):
    from spectralbridge.pipelines.drone import (
        _drone_grid_transforms_match,
        _validate_drone_tiff_ancillary_alignment,
    )

    reference = Affine(.0999999999999763, 0, 457268.25,
                       0, -.0999999999999108, 4429034.8)
    ancillary = Affine(.09999999999999605, 0, 457268.25,
                       0, -.0999999999999108, 4429034.8)
    shape = (2088, 2948)
    assert _drone_grid_transforms_match(reference, ancillary, shape)
    assert not _drone_grid_transforms_match(reference, Affine.translation(.00001, 0) * ancillary, shape)
    assert not _drone_grid_transforms_match(reference, Affine.translation(0, .00001) * ancillary, shape)
    assert not _drone_grid_transforms_match(reference, Affine(.10000001, 0, reference.c, 0, reference.e, reference.f), shape)
    path = tmp_path / 'slope.tif'
    values = np.full((1, *shape), 12.5, dtype='float32')
    with rasterio.open(path, 'w', driver='GTiff', height=shape[0], width=shape[1],
                       count=1, dtype='float32', transform=ancillary, crs='EPSG:26913') as dst:
        dst.write(values)
    loaded = _validate_drone_tiff_ancillary_alignment(
        tmp_path / 'source.tif', shape, reference,
        rasterio.crs.CRS.from_epsg(26913).to_wkt(), path,
    )
    np.testing.assert_array_equal(loaded, values[0])
