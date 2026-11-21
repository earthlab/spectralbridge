"""Offline datastore transfers and completion publication order."""
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from spectralbridge.remote import RemoteEntry, remote_join


@pytest.fixture
def vm(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'scripts'))
    return importlib.import_module('drone_vm_campaign')


class Backend:
    executable = 'fake-gocmd'

    def __init__(self):
        self.objects = {}
        self.downloads = []
        self.corrupt = None

    def list_directory(self, path):
        prefix = path.rstrip('/') + '/'
        return [RemoteEntry(key, key[len(prefix):], False, len(value))
                for key, value in self.objects.items() if key.startswith(prefix) and '/' not in key[len(prefix):]]

    def download_file(self, remote, local):
        self.downloads.append(remote)
        Path(local).write_bytes(b'corrupt' if remote == self.corrupt else self.objects[remote])


def test_auxiliary_restart_and_changed_remote_identity(tmp_path, vm):
    backend = Backend()
    backend.objects['i:/source/surface.tif'] = b'first'
    path = tmp_path / 'surface.tif'
    vm.stage_auxiliary(backend, 'i:/source/surface.tif', path)
    stamp = path.stat().st_mtime_ns
    vm.stage_auxiliary(backend, 'i:/source/surface.tif', path)
    assert len(backend.downloads) == 1 and path.stat().st_mtime_ns == stamp
    path.write_bytes(b'damage')
    vm.stage_auxiliary(backend, 'i:/source/surface.tif', path)
    assert path.read_bytes() == b'first'
    backend.objects['i:/source/surface.tif'] = b'new-data'
    vm.stage_auxiliary(backend, 'i:/source/surface.tif', path)
    assert path.read_bytes() == b'new-data'


def delivery(tmp_path):
    root = tmp_path / 'run1' / 'signature'
    products = root / 'flight_products' / 'flight'
    products.mkdir(parents=True)
    (products / 'product.img').write_bytes(b'synthetic processed bytes')
    report = dict(status='complete', signature='a' * 64, scope='pilot', run_root=str(root),
                  flight_products=str(root / 'flight_products'), flights={'one': dict(status='complete')})
    (root / 'run_configuration.json').write_text('{}')
    (root / 'campaign_result.json').write_text(json.dumps(report))
    return report


def test_upload_receipt_is_last_and_requires_full_readback(tmp_path, vm, monkeypatch):
    backend = Backend()
    uploads = []

    def put(folder, parent, executable):
        assert executable == backend.executable
        remote = remote_join(parent, folder.name)
        uploads.append(folder.name)
        for path in folder.rglob('*'):
            if path.is_file():
                backend.objects[remote_join(remote, str(path.relative_to(folder)))] = path.read_bytes()
        return remote

    monkeypatch.setattr(vm, 'upload_tree', put)
    report = delivery(tmp_path)
    receipt = vm.upload_verified_campaign(report, backend=backend, remote_results_parent='i:/processed')
    assert uploads == ['flight_products', 'delivery_metadata', 'completion']
    assert backend.downloads[-1] == receipt['completion_receipt']
    saved = json.loads(backend.objects[receipt['completion_receipt']])
    assert saved['verification'] == 'full remote SHA256 readback'
    assert len(saved['objects']) == receipt['verified_objects'] == 3
    original = receipt['destination']
    (Path(report['flight_products']) / 'flight/product.img').write_bytes(b'changed QA or data')
    changed = vm.upload_verified_campaign(report, backend=backend, remote_results_parent='i:/processed')
    assert changed['destination'] != original
    assert receipt['completion_receipt'] in backend.objects


def test_corrupt_readback_and_incomplete_runs_never_publish_completion(tmp_path, vm, monkeypatch):
    backend = Backend()
    uploads = []

    def put(folder, parent, executable):
        remote = remote_join(parent, folder.name)
        uploads.append(folder.name)
        for path in folder.rglob('*'):
            if path.is_file():
                target = remote_join(remote, str(path.relative_to(folder)))
                backend.objects[target] = path.read_bytes()
                if path.suffix == '.img':
                    backend.corrupt = target
        return remote

    monkeypatch.setattr(vm, 'upload_tree', put)
    report = delivery(tmp_path)
    with pytest.raises(RuntimeError, match='Remote readback mismatch'):
        vm.upload_verified_campaign(report, backend=backend, remote_results_parent='i:/processed')
    assert uploads == ['flight_products']
    assert not any('campaign_complete.json' in key for key in backend.objects)
    report['status'] = 'incomplete'
    with pytest.raises(ValueError, match='Incomplete'):
        vm.upload_verified_campaign(report, backend=backend, remote_results_parent='i:/processed')


def test_no_large_transfers_without_complete_reviewed_contracts(tmp_path, vm):
    backend = Backend()
    inventory = SimpleNamespace(discovery_complete=True,
                                eligible_packages=[SimpleNamespace(remote_package_path='i:/missing', package_name='missing')])
    with pytest.raises(KeyError):
        vm.run_vm_campaign(inventory, {}, work=tmp_path, run_id='test', backend=backend,
                           manifest=tmp_path / 'manifest.csv', polygons=None,
                           translation_registry=tmp_path / 'registry.json')
    assert backend.downloads == []


def test_vm_pilot_from_datastore_through_real_producer_and_resume(tmp_path, vm):
    """No producer/QA doubles: only the remote service is replaced by a byte store."""
    from tests.test_drone_campaign_inputs import inputs, WAVES
    from spectralbridge.pipelines.drone import convert_drone_tiff_to_h5, derive_drone_flight_stem
    from spectralbridge.drone_campaign_inputs import file_sha256

    source, geometry, mask, calibration = inputs(tmp_path)
    original_h5 = tmp_path / 'original.h5'
    convert_drone_tiff_to_h5(
        source, output_h5_path=original_h5, wavelengths_nm=WAVES, fwhm_nm=[10] * 10,
        radiometry=dict(scale=.0001, offset=0, status='VALID', provenance='Synthetic source'),
        solar_zenith_deg=35, solar_azimuth_deg=145, sensor_zenith_deg=0, sensor_azimuth_deg=0)
    package_path = 'i:/rasters/TEST-08-14-23-ExportPackage'
    camera_collection = 'i:/original/TEST-08-14-23-ExportPackage'
    backend = Backend()
    backend.objects[package_path + '/original.h5'] = original_h5.read_bytes()
    backend.objects[package_path + '/aligned_orthomosaic.tif'] = source.read_bytes()
    for name in ['aligned_slope.tif', 'aligned_aspect.tif']:
        # The recipe validates grid placement; this pilot explicitly requests no
        # terrain/BRDF stage. Those stages are covered by the full science pilot.
        backend.objects[package_path + '/' + name] = Path(geometry['surface']).read_bytes()
    camera_name = 'TEST-camera-locations.csv'
    backend.objects[camera_collection + '/' + camera_name] = Path(geometry['camera_locations']).read_bytes()
    for role, path in [('surface', geometry['surface']), ('camera_index', geometry['camera_index']), ('processing_mask', mask['path'])]:
        backend.objects[f'i:/auxiliary/{role}.tif'] = Path(path).read_bytes()
    package = SimpleNamespace(remote_package_path=package_path, package_name='TEST-08-14-23-ExportPackage',
                              h5_name='original.h5', year=2023, flight_stem=derive_drone_flight_stem(source))
    inventory = SimpleNamespace(discovery_complete=True, eligible_packages=[package])
    calibration['source_sha256'] = file_sha256(original_h5)
    provider = tmp_path / 'brightness.json'
    provider.write_text(json.dumps(calibration))
    manifest = tmp_path / 'manifest.csv'
    manifest.write_text('Plot,Day of data collection,Mean Time of data collection (24 hr clock)\nTEST,2023-08-14,18:00:00\n')
    from tests.test_drone_translation import _write_coefficients
    registry = _write_coefficients(tmp_path / 'registry.parquet')
    contract = dict(source_sha256=file_sha256(original_h5), wavelengths_nm=WAVES,
                    source_radiometry=dict(scale=.0001, offset=0, status='VALID', provenance='Synthetic source'),
                    brightness_json=str(provider), camera_collection=camera_collection,
                    camera_geometry=geometry, processing_mask=mask,
                    auxiliary_sources={role: f'i:/auxiliary/{role}.tif' for role in ['surface', 'camera_index', 'processing_mask']},
                    pipeline=dict(apply_topo=False, apply_brdf=False, extraction_mode='full', parquet_chunk_size=32))
    options = dict(work=tmp_path / 'vm', run_id='pilot', backend=backend, manifest=manifest,
                   polygons=None, translation_registry=registry, targets=('Landsat_8_OLI',), scope='pilot')
    report = vm.run_vm_campaign(inventory, {package_path: contract}, **options)
    assert report['status'] == 'complete', report
    flight = Path(report['flights'][package_path]['flight_dir'])
    image = next(flight.glob('*micasense_translated_to_*.img'))
    stamp = image.stat().st_mtime_ns
    transfers = len(backend.downloads)
    repeated = vm.run_vm_campaign(inventory, {package_path: contract}, **options)
    assert repeated['status'] == 'complete', repeated
    assert repeated['run_root'] == report['run_root']
    assert image.stat().st_mtime_ns == stamp
    assert len(backend.downloads) == transfers
    assert (flight / 'campaign_provenance/provider_brightness.json').exists()
    original_receipt = json.loads((flight / 'campaign_provenance/provider_brightness.json').read_text())
    assert original_receipt['source_sha256'] == file_sha256(original_h5)
    pilot_options = dict(manifest=manifest, polygons=None, translation_registry=registry,
                         targets=('Landsat_8_OLI',), naming_style='micasense', output_scale_factor=1000.0)
    vm.require_current_pilot(report, {package_path: contract}, **pilot_options)
    calibration['bands'][0]['gain'] += .02
    provider.write_text(json.dumps(calibration))
    with pytest.raises(ValueError, match='Pilot is stale'):
        vm.require_current_pilot(report, {package_path: contract}, **pilot_options)
    changed = vm.run_vm_campaign(inventory, {package_path: contract}, **options)
    assert changed['status'] == 'complete', changed
    assert changed['run_root'] != report['run_root']
    assert image.exists()  # Previous calibrated products are preserved.


def test_production_notebook_is_portable_clean_and_requires_explicit_execution():
    root = Path(__file__).resolve().parents[1]
    notebook = json.loads((root / 'examples/drone_cyverse_production.ipynb').read_text())
    sources = []
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            compile(source, 'VM production cell', 'exec')
            assert cell['execution_count'] is None and cell['outputs'] == []
            sources.append(source)
    code = '\n'.join(sources)
    for flag in ['REMOTE_READS', 'STAGE_PILOT_INPUTS', 'RUN_PILOT', 'RUN_ALL', 'UPLOAD']:
        assert f'{flag} = False' in code
    assert '/Users/' not in code
    assert 'PILOT_QA_REVIEWED' in code and 'upload_verified_campaign' in code
    assert 'aop_derived_micasense_to_landsat_fractional_reflectance_registry.json' in code
