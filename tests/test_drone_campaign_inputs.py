"""Bounded camera/calibration inputs preserve source bytes and restart identities."""
import json

import h5py
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from spectralbridge.drone_campaign_inputs import file_sha256, bind_campaign_cube
from spectralbridge.pipelines.drone import _prepare_drone_source_working_h5, derive_drone_flight_stem
from spectralbridge.neon_cube import NeonCube

WAVES = [444, 475, 531, 560, 650, 668, 705, 717, 740, 842]


def inputs(tmp_path):
    folder = tmp_path / 'TEST-08-14-23-ExportPackage'
    folder.mkdir()
    source = folder / 'reflectance.tif'
    transform = from_origin(450000, 4430000, 1, 1)
    profile = dict(driver='GTiff', height=12, width=15, count=10, dtype='float32',
                   crs='EPSG:26913', transform=transform, nodata=-9999)
    with rasterio.open(source, 'w', **profile) as out:
        out.write(np.full((10, 12, 15), 2000, np.float32))
    profile.update(count=1)
    for name, value in [('surface', 2700), ('index', 0), ('mask', 0)]:
        with rasterio.open(folder / f'{name}.tif', 'w', **profile) as out:
            data = np.full((1, 12, 15), value, np.float32)
            if name == 'mask':
                data[:, 0, 0] = 1
            out.write(data)
    fields = 'PhotoID,X,Y,Z,Omega,Phi,Kappa,' + ','.join(f'r{i}{j}' for i in range(1, 4) for j in range(1, 4))
    camera = folder / 'camera.csv'
    camera.write_text(f'CRS,26913\n# Cameras (1)\n# {fields}\nphoto,450007,4429994,2800,0,0,0,1,0,0,0,1,0,0,0,1\n')
    geometry = dict(camera_locations=str(camera), surface=str(folder / 'surface.tif'),
                    camera_index=str(folder / 'index.tif'), assignment_policy='reviewed_index',
                    height_datum_provenance='Synthetic shared height datum', max_view_zenith_deg=70,
                    provenance='Synthetic known camera assignment')
    mask = dict(path=str(folder / 'mask.tif'), keep_value=0, allowed_values=[0, 1, 255], provenance='Synthetic exclusion')
    calibration = dict(schema_version=1, status='REVIEWED', calibration_id='fixture',
                       flight_id=derive_drone_flight_stem(source), source_sha256=file_sha256(source),
                       equation='calibrated_reflectance = gain * decoded_reflectance + offset',
                       provenance='Synthetic independent affine',
                       bands=[dict(wavelength_nm=w, gain=1 + i / 100, offset=-i / 1000) for i, w in enumerate(WAVES)])
    return source, geometry, mask, calibration


def prepare(source, working, geometry, mask, calibration):
    return _prepare_drone_source_working_h5(
        source, source_type='tiff', working_path=working,
        radiometry=dict(scale=0.0001, offset=0, status='VALID', provenance='Synthetic source decoding'),
        tiff_wavelengths_nm=WAVES, tiff_fwhm_nm=[10] * 10,
        tiff_solar_zenith_deg=35, tiff_solar_azimuth_deg=145,
        brightness_calibration=calibration, camera_geometry=geometry, processing_mask=mask)


def test_camera_calibration_mask_restart_and_changed_coefficient(tmp_path):
    source, geometry, mask, calibration = inputs(tmp_path)
    digest = file_sha256(source)
    working = tmp_path / 'output' / 'TEST_20230814__working.h5'
    working.parent.mkdir()
    prepare(source, working, geometry, mask, calibration)
    before = working.stat().st_mtime_ns
    cube = NeonCube(working)
    audit = bind_campaign_cube(cube)
    assert audit['actual_mosaic_contributors'] == 'REVIEWED_INDEX'
    assert not cube.mask_no_data[0, 0] and cube.mask_no_data[1:, 1:].all()
    expected = np.array([0.2 * (1 + i / 100) - i / 1000 for i in range(10)])
    np.testing.assert_allclose(cube.radiometry.to_physical(cube.data[2, 2]), expected, atol=1e-7)
    # Independent geometry calculation at an off-axis pixel.
    dx, dy, dz = 450007 - 450002.5, 4429994 - 4429997.5, 100
    expected_zenith = np.rad2deg(np.arctan2(np.hypot(dx, dy), dz))
    assert cube.get_ancillary('sensor_zn', radians=False)[2, 2] == pytest.approx(expected_zenith, abs=1e-6)
    prepare(source, working, geometry, mask, calibration)
    assert working.stat().st_mtime_ns == before
    changed = json.loads(json.dumps(calibration))
    changed['bands'][0]['gain'] = 1.5
    prepare(source, working, geometry, mask, changed)
    assert working.stat().st_mtime_ns != before
    assert NeonCube(working).radiometry.to_physical(np.full(10, 2000))[0] == pytest.approx(0.3)
    assert file_sha256(source) == digest
    with h5py.File(working) as h:
        from spectralbridge.pipelines.drone import _find_drone_reflectance_dataset
        assert 'spectralbridge_campaign_inputs' in _find_drone_reflectance_dataset(h).attrs


def test_mismatched_source_and_spatial_grid_block_before_completion(tmp_path):
    source, geometry, mask, calibration = inputs(tmp_path)
    calibration['source_sha256'] = '0' * 64
    working = tmp_path / 'out.h5'
    with pytest.raises(ValueError, match='source SHA-256 mismatch'):
        prepare(source, working, geometry, mask, calibration)
    assert not working.with_suffix('.stage.json').exists()
    calibration['source_sha256'] = file_sha256(source)
    with rasterio.open(geometry['surface'], 'r+') as out:
        out.transform = from_origin(450001, 4430000, 1, 1)
    with pytest.raises(ValueError, match='source grid exactly'):
        prepare(source, working, geometry, mask, calibration)
    assert not working.with_suffix('.stage.json').exists()


def test_nearest_geometry_requires_acknowledged_scenario(tmp_path):
    source, geometry, mask, calibration = inputs(tmp_path)
    geometry.pop('camera_index')
    geometry['assignment_policy'] = 'nearest_camera_scenario'
    with pytest.raises(ValueError, match='assumption acknowledgement'):
        prepare(source, tmp_path / 'working.h5', geometry, mask, calibration)
    geometry['assumption_acknowledgement'] = 'Synthetic scenario only; contributors unknown'
    path, _ = prepare(source, tmp_path / 'working.h5', geometry, mask, calibration)
    cube = NeonCube(path)
    assert bind_campaign_cube(cube)['actual_mosaic_contributors'] == 'UNKNOWN'


def test_public_drone_pipeline_full_chain_delivery_and_restart(tmp_path, monkeypatch):
    """Real TIFF/H5/ENVI/correction/translation/Parquet/QA path, no science doubles."""
    import pandas as pd
    from spectralbridge import corrections as c
    from spectralbridge.pipelines.drone import run_drone_pipeline
    from spectralbridge.envi import hdr_to_dict, memmap_bsq
    from spectralbridge.radiometry import Radiometry

    source, geometry, mask, calibration = inputs(tmp_path)
    camera = geometry['camera_locations']
    from pathlib import Path
    Path(camera).write_text(Path(camera).read_text().replace('2800', '2710'))
    yy, xx = np.mgrid[:12, :15]
    dx, dy = 7 - (xx + .5), -6 + (yy + .5)
    zen = np.arctan2(np.hypot(dx, dy), 10)
    az = np.arctan2(dx, dy) % (2 * np.pi)
    slope = np.deg2rad(5 + xx * .6 + yy * .1)
    aspect = np.full(xx.shape, 1.0)
    cos_i = c.calc_cosine_i(np.full(xx.shape, np.deg2rad(35)), np.full(xx.shape, np.deg2rad(145)), aspect, slope)
    kv = c.calc_volume_kernel(np.deg2rad(145), np.deg2rad(35), az, zen, 'RossThick')
    kg = c.calc_geom_kernel(np.deg2rad(145), np.deg2rad(35), az, zen, 'LiDenseR', b_r=10, h_b=2)
    physical = (.3 + .02 * kv + .01 * kg) * (.4 + cos_i)
    with rasterio.open(source, 'r+') as out:
        out.write(np.stack([physical * 10000 * (1 + i / 50) for i in range(10)]).astype('float32'))
        profile = out.profile.copy()
    profile.update(count=1)
    for name, values in [('aligned_slope.tif', np.rad2deg(slope)), ('aligned_aspect.tif', np.rad2deg(aspect))]:
        with rasterio.open(source.parent / name, 'w', **profile) as out:
            out.write(values.astype('float32'), 1)
    calibration['source_sha256'] = file_sha256(source)
    rows = []
    for target in ['Landsat_8_OLI', 'Landsat_9_OLI-2']:
        for band in range(1, 6):
            rows.append(dict(reflectance_units='physical_reflectance_v1', analysis_run_id='synthetic-pilot',
                             analysis_level='site_balanced', weighting='synthetic sites',
                             translation_pair=f'MicaSense_to-match_OLI_and_OLI-2__to__{target}',
                             source_sensor='MicaSense_to-match_OLI_and_OLI-2', target_sensor=target,
                             source_band_index=band, target_band_index=band, band_index=band,
                             equation='target = slope * source + intercept', status='ok',
                             slope=1.1, intercept=.01, x_min=0., x_max=2., x_mean=.3, r2=.99))
    registry = tmp_path / 'coefficients.parquet'
    pd.DataFrame(rows).to_parquet(registry, index=False)
    options = dict(output_dir=tmp_path / 'products', apply_topo=True, apply_brdf=True,
                   radiometry=dict(scale=.0001, offset=0, status='VALID', provenance='Synthetic source'),
                   brightness_calibration=calibration, camera_geometry=geometry, processing_mask=mask,
                   tiff_wavelengths_nm=WAVES, tiff_fwhm_nm=[10] * 10,
                   tiff_solar_zenith_deg=35, tiff_solar_azimuth_deg=145,
                   extraction_mode='full', parquet_chunk_size=32,
                   apply_translation=True, translation_coefficients=registry,
                   translation_target_sensors=['Landsat_8_OLI', 'Landsat_9_OLI-2'],
                   translation_naming_style='micasense', translation_output_scale_factor=1000,
                   raise_on_incomplete=False)
    result = run_drone_pipeline(source, **options)
    assert result['status'] == 'complete', result
    audit = result['qa_summary']['files'][0]
    assert audit['flags']['topo_applied'] and audit['flags']['brdf_applied']
    assert audit['flags']['brightness_applied']
    assert result['qa_summary']['brightness_adjustment_applied']
    assert len(audit['translation_products']) == 2
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from drone_vm_campaign import verify_flight
    verify_flight(result, options['translation_target_sensors'], 1000)
    corrected = Path(audit['corrected_raster_path'])
    header = hdr_to_dict(corrected.with_suffix('.hdr'))
    cube = np.asarray(memmap_bsq(corrected, header))
    calibration_after = Radiometry.from_header(header)
    for product in audit['translation_products']:
        target = Path(product['output_img'])
        assert '_micasense_translated_to_' in target.name
        target_header = hdr_to_dict(target.with_suffix('.hdr'))
        translated = np.asarray(memmap_bsq(target, target_header))
        # Independently verify a retained pixel against the reviewed affine.
        for i, native in enumerate([0, 1, 3, 5, 9]):
            value = calibration_after.to_physical(cube[native, 3, 4], band_index=native)
            assert translated[i, 3, 4] == pytest.approx((1.1 * value + .01) * 1000, abs=.001)
        assert not np.isfinite(translated[:, 0, 0]).any() or np.all(translated[:, 0, 0] == float(target_header['data ignore value']))
    stamp = corrected.stat().st_mtime_ns
    repeat = run_drone_pipeline(source, **options)
    assert repeat['status'] == 'complete', repeat
    assert corrected.stat().st_mtime_ns == stamp
    assert repeat['qa_summary']['files'][0]['flags']['reused_existing_corrected']

    calibration['bands'][0]['gain'] += .02
    updated = run_drone_pipeline(source, **options)
    assert updated['status'] == 'complete', updated
    assert corrected.stat().st_mtime_ns != stamp
    verify_flight(updated, options['translation_target_sensors'], 1000)
