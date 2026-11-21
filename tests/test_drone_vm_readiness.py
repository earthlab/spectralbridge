"""VM preparation checks do not claim a completed camera-aware production run."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from spectralbridge.radiometry import Radiometry
from spectralbridge.remote import RemoteEntry

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('drone_vm_readiness', ROOT / 'scripts/drone_vm_readiness.py')
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)


def calibration():
    return dict(schema_version=1, status='REVIEWED', calibration_id='synthetic-v1',
                provenance='Synthetic calibration fixture, not field coefficients',
                flight_id='flight', source_sha256='a' * 64, equation=vm.BRIGHTNESS_EQUATION,
                bands=[dict(wavelength_nm=650, gain=1.2, offset=-0.02),
                       dict(wavelength_nm=842, gain=0.8, offset=0.01)])


def compose(record=None, **kwargs):
    args = dict(flight_id='flight', source_sha256='a' * 64, wavelengths_nm=[650, 842],
                source_radiometry=Radiometry(0.0001, -0.1, 'VALID', 'Synthetic source affine').record())
    args.update(kwargs)
    return vm.compose_brightness_calibration(record or calibration(), **args)


def test_per_band_calibration_composes_decoding_once_and_rejects_second_application():
    record = compose()
    result = Radiometry.from_record(record)
    stored = np.array([[2000, 4000], [5000, 8000]], dtype=np.float32)
    expected = (stored * 0.0001 - 0.1) * [1.2, 0.8] + [-0.02, 0.01]
    np.testing.assert_allclose(result.to_physical(stored), expected, atol=1e-7)
    np.testing.assert_allclose(result.to_stored(result.to_physical(stored)), stored, atol=0.002)
    with pytest.raises(ValueError, match='double calibration'):
        compose(source_radiometry=record)
    changed = calibration()
    changed['bands'][0]['gain'] = 1.3
    assert compose(changed)['encoding']['brightness_calibration_sha256'] != record['encoding']['brightness_calibration_sha256']


@pytest.mark.parametrize('damage', ['source', 'flight', 'order', 'missing', 'negative', 'nan', 'equation', 'pending'])
def test_calibration_rejects_ambiguous_or_incompatible_inputs(damage):
    record = calibration()
    if damage == 'source':
        record['source_sha256'] = 'b' * 64
    elif damage == 'flight':
        record['flight_id'] = 'other'
    elif damage == 'order':
        record['bands'].reverse()
    elif damage == 'missing':
        record['bands'].pop()
    elif damage == 'negative':
        record['bands'][0]['gain'] = -1
    elif damage == 'nan':
        record['bands'][0]['offset'] = float('nan')
    elif damage == 'equation':
        record['equation'] = 'stored = gain * physical + offset'
    else:
        record['status'] = 'PENDING'
    with pytest.raises(ValueError):
        compose(record)


def camera_bytes():
    fields = 'PhotoID,X,Y,Z,Omega,Phi,Kappa,' + ','.join(f'r{i}{j}' for i in range(1, 4) for j in range(1, 4))
    return (f'CRS,26913\n# Cameras (1)\n# {fields}\nphoto,450000,4430000,2800,0,0,0,1,0,0,0,1,0,0,0,1\n').encode()


class Backend:
    def __init__(self):
        self.data = camera_bytes()
        self.downloads = 0
        self.entries = [RemoteEntry('i:/original/package/AOP-RUBY-camera-locations.csv',
                                    'AOP-RUBY-camera-locations.csv', False, len(self.data))]

    def list_directory(self, path):
        assert path == 'i:/original/package'
        return self.entries

    def download_file(self, path, target):
        self.downloads += 1
        Path(target).write_bytes(self.data)


def test_camera_exact_package_selection_hash_restart_and_corruption(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    backend = Backend()
    entry = vm.camera_entry(backend, 'i:/original/package')
    first = vm.stage_camera(backend, entry, tmp_path)
    second = vm.stage_camera(backend, entry, tmp_path)
    assert first['source_sha256'] == second['source_sha256']
    assert first['declared_crs'] == first['adopted_crs'] == 'EPSG:26913'
    assert backend.downloads == 1
    (tmp_path / entry.name).write_bytes(b'corrupt')
    vm.stage_camera(backend, entry, tmp_path)
    assert backend.downloads == 2
    backend.entries *= 2
    with pytest.raises(ValueError, match='exactly one'):
        vm.camera_entry(backend, 'i:/original/package')


def test_bad_camera_transfer_does_not_replace_valid_file(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / 'scripts'))
    backend = Backend()
    entry = backend.entries[0]
    vm.stage_camera(backend, entry, tmp_path)
    original = (tmp_path / entry.name).read_bytes()
    (tmp_path / (entry.name + '.transfer.json')).unlink()
    backend.data = b'truncated'
    with pytest.raises(ValueError, match='Incomplete camera transfer'):
        vm.stage_camera(backend, entry, tmp_path)
    assert (tmp_path / entry.name).read_bytes() == original
    assert not list(tmp_path.glob('*.part'))


def test_report_cannot_promote_camera_presence_to_production_readiness():
    package = SimpleNamespace(remote_package_path='i:/raster/package', package_name='package')
    inventory = SimpleNamespace(discovery_complete=True, eligible_packages=[package])
    report = vm.readiness_report(inventory, cameras={package.remote_package_path: {}},
                                 calibrations={package.remote_package_path: compose()},
                                 translation_coefficients=None, wavelengths_by_flight={})
    assert not report['production_ready']
    assert not report['raster_downloads_started'] and not report['uploads_started']
    assert not report['ready_for_pilot']
    assert any('execution contracts' in reason for reason in report['blockers'])
    assert report['flights'][0]['blockers'] == ['Authoritative flight wavelengths not supplied']


def test_vm_notebook_is_clean_compilable_and_has_no_processing_or_upload_escape_hatch():
    notebook = json.loads((ROOT / 'examples/drone_cyverse_readiness.ipynb').read_text())
    code = []
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            compile(source, '<VM readiness cell>', 'exec')
            assert cell['execution_count'] is None and cell['outputs'] == []
            code.append(source)
    source = '\n'.join(code)
    assert '/Users/' not in source
    assert 'REMOTE_READS = False' in source
    assert 'run_drone_pipeline(' not in source and 'upload_tree(' not in source
