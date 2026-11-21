"""Restart-safe VM orchestration using existing drone processing and transfer APIs.

One ExportPackage is staged/processed at a time; raw sources are never uploaded
as processed results. Output roots are immutable configuration identities. Actual
camera/clock/calibration declarations belong to each flight, not global guesses.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.drone_campaign_inputs import (
    brightness_record, compose_brightness_calibration, file_sha256,
)
from spectralbridge.remote import remote_join, remote_parent

from drone_cloud_workflow import download_sources, prepare_reference, upload_tree
from drone_vm_readiness import camera_entry, stage_camera


def _identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def stage_auxiliary(backend, remote, destination):
    """Resume one auxiliary transfer against remote identity and local SHA-256."""
    parent, name = remote_parent(remote), remote.rsplit('/', 1)[-1]
    if name in {'', '.', '..'}:
        raise ValueError('Auxiliary source must name a remote file')
    entries = [e for e in backend.list_directory(parent) if not e.is_collection and e.name == name]
    if len(entries) != 1 or not entries[0].size_bytes:
        raise ValueError(f'Expected one sized auxiliary: {remote}')
    entry = entries[0]
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    receipt = destination.with_name(destination.name + '.transfer.json')
    previous = json.loads(receipt.read_text()) if receipt.exists() else {}
    if destination.is_file() and previous.get('remote') == entry.to_dict() and previous.get('sha256') == file_sha256(destination):
        return destination
    temporary = destination.with_name(destination.name + '.part')
    try:
        backend.download_file(entry.path, temporary)
        if temporary.stat().st_size != entry.size_bytes:
            raise ValueError(f'Incomplete auxiliary transfer: {remote}')
        digest = file_sha256(temporary)
        if destination.is_file() and file_sha256(destination) == digest:
            temporary.unlink()
        else:
            temporary.replace(destination)
        write_json_atomic(receipt, dict(remote=entry.to_dict(), sha256=digest))
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def verify_flight(result, targets, output_scale_factor):
    """Require produced rasters and QA, not a successful function return alone."""
    from spectralbridge.envi import hdr_to_dict
    from spectralbridge.radiometry import library_radiometry
    from spectralbridge.utils_checks import is_valid_envi_pair

    if result.get('failed') or result.get('blocked') or result.get('status') != 'complete':
        raise RuntimeError('Flight has failed or scientifically blocked stages')
    files = result['qa_summary']['files']
    if len(files) != 1 or result['qa_summary'].get('qa_render_error'):
        raise RuntimeError('Expected one flight with completed QA rendering')
    audit = files[0]
    products = audit['translation_products']
    if sorted(p['target_sensor'] for p in products) != sorted(targets):
        raise RuntimeError('Missing, duplicate or unexpected translation targets')
    required = [audit['qa_plot_path'], audit['qa_json_path'], result['qa_summary_path']]
    required += audit.get('translation_qa_paths', [])
    if len(audit.get('translation_qa_paths', [])) != 2 * len(products):
        raise RuntimeError('Every translation requires PNG and JSON QA')
    for product in products:
        image, header = Path(product['output_img']), Path(product['output_hdr'])
        if not is_valid_envi_pair(image, header):
            raise RuntimeError(f'Invalid translation pair: {image}')
        radiometry = library_radiometry(image)
        if radiometry.scale != 1.0 / output_scale_factor or radiometry.offset != 0.0:
            raise RuntimeError('Translation storage/physical unit contract differs from request')
        metadata = hdr_to_dict(header)
        if float(metadata['reflectance scale factor']) != output_scale_factor:
            raise RuntimeError('Translation divisor metadata differs from request')
        required.extend([str(image), str(header), product['provenance_json']])
    for path in required:
        path = Path(path)
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f'Missing required product/QA artifact: {path}')
    return Path(audit['flight_dir'])


def require_current_pilot(pilot, contracts, *, manifest, polygons, translation_registry,
                          targets, naming_style, output_scale_factor):
    """Reject a prior pilot when reviewed inputs, delivery or implementation change."""
    if pilot is None or pilot.get('scope') != 'pilot' or pilot.get('status') != 'complete' or len(pilot.get('flights', {})) != 1:
        raise ValueError('A completed one-flight VM pilot is required before campaign execution')
    root = Path(pilot['run_root'])
    configuration = json.loads((root / 'run_configuration.json').read_text())
    if _identity(configuration) != pilot['signature']:
        raise ValueError('Pilot configuration integrity mismatch')
    for key, previous in configuration['contracts'].items():
        contract = contracts.get(key)
        if contract is None or dict(contract, brightness_record=brightness_record(contract['brightness_json'])) != previous:
            raise ValueError('Pilot is stale: source/calibration/geometry contract changed')
    expected = dict(manifest_sha256=file_sha256(manifest),
                    polygon_sha256=file_sha256(polygons) if polygons is not None else None,
                    registry_sha256=file_sha256(translation_registry), targets=list(targets),
                    naming_style=naming_style, output_scale_factor=output_scale_factor)
    if any(configuration.get(key) != value for key, value in expected.items()):
        raise ValueError('Pilot is stale: manifest, registry or delivery contract changed')
    repo = Path(__file__).resolve().parents[1]
    for path, digest in configuration['implementation'].items():
        if file_sha256(repo / path) != digest:
            raise ValueError('Pilot is stale: processing implementation changed')
    for status in pilot['flights'].values():
        result = json.loads((Path(status['flight_dir']).parent / 'pipeline_result.json').read_text())
        verify_flight(result, targets, output_scale_factor)


def run_vm_campaign(inventory, contracts, *, work, run_id, backend, manifest, polygons,
                    translation_registry, targets=('Landsat_8_OLI', 'Landsat_9_OLI-2'),
                    naming_style='micasense', output_scale_factor=1000.0, scope='campaign', pilot=None):
    """Execute explicit per-flight contracts, recording failures while others continue.

    Contracts supply source SHA256, source radiometry, provider brightness JSON,
    camera collection/geometry/auxiliary paths and explicit topo/BRDF choices.
    A missing contract fails before any large raster transfer. Changed provider
    JSON/registry/policies create a fresh output identity; prior results survive.
    """
    from spectralbridge.pipelines.drone import run_drone_pipeline, derive_drone_flight_stem
    from spectralbridge.drone_radiometry import radiometry_from_source_encoding
    from spectralbridge.radiometry import Radiometry
    from spectralbridge.drone_translation import load_drone_translation_plans

    if scope not in {'campaign', 'pilot'} or (scope == 'pilot' and len(inventory.eligible_packages) != 1):
        raise ValueError('Scope must be full campaign or exactly one explicit pilot flight')
    if not inventory.discovery_complete or not inventory.eligible_packages:
        raise ValueError('Manifest inventory is incomplete or empty')
    if not targets or len(set(targets)) != len(targets):
        raise ValueError('Explicit unique translation targets required')
    # Validate the entire selected population before committing raster bandwidth.
    identity_contracts = {}
    for package in inventory.eligible_packages:
        key = package.remote_package_path
        contract = contracts[key]
        for required in ['source_sha256', 'source_radiometry', 'brightness_json', 'camera_collection', 'camera_geometry', 'pipeline']:
            if required not in contract:
                raise ValueError(f'{key} lacks {required}')
        for flag in ['apply_topo', 'apply_brdf']:
            if not isinstance(contract['pipeline'].get(flag), bool):
                raise ValueError(f'{key} requires explicit {flag}')
        allowed = {'apply_topo', 'apply_brdf', 'extraction_mode', 'parquet_chunk_size', 'drone_manifest_timezone'}
        if set(contract['pipeline']) - allowed:
            raise ValueError('Unsupported campaign pipeline options; never override source/QA gates')
        geometry = contract['camera_geometry']
        auxiliary = contract.get('auxiliary_sources', {})
        for field in ['assignment_policy', 'height_datum_provenance', 'max_view_zenith_deg', 'provenance']:
            if geometry.get(field) is None or not str(geometry[field]).strip():
                raise ValueError(f'{key}: missing camera policy {field}')
        roles = ['surface'] + (['camera_index'] if geometry['assignment_policy'] == 'reviewed_index' else [])
        for role in roles:
            if not auxiliary.get(role) and not geometry.get(role):
                raise ValueError(f'{key}: missing explicit {role} backing source')
        if geometry['assignment_policy'] == 'nearest_camera_scenario' and not geometry.get('assumption_acknowledgement'):
            raise ValueError(f'{key}: nearest-camera scenario acknowledgement required')
        record = brightness_record(contract['brightness_json'])
        if record.get('source_sha256') != contract['source_sha256']:
            raise ValueError(f'{key}: coefficient/source identity conflict')
        if record.get('status') != 'REVIEWED':
            raise ValueError(f'{key}: incoming brightness coefficients are not reviewed')
        declared_waves = contract['wavelengths_nm']
        base = contract['source_radiometry']
        base = radiometry_from_source_encoding(base).record() if 'input_encoding' in base else base
        compose_brightness_calibration(record, flight_id=package.flight_stem,
                                       source_sha256=contract['source_sha256'],
                                       wavelengths_nm=declared_waves, source_radiometry=base)
        load_drone_translation_plans(translation_registry, source_wavelengths_nm=declared_waves, target_sensors=targets)
        identity_contracts[key] = dict(contract, brightness_record=record)
    configuration = dict(schema_version=1, run_id=run_id, scope=scope,
                         contracts=identity_contracts, manifest_sha256=file_sha256(manifest),
                         polygon_sha256=file_sha256(polygons) if polygons is not None else None,
                         registry_sha256=file_sha256(translation_registry), targets=list(targets),
                         naming_style=naming_style, output_scale_factor=output_scale_factor,
                         # Never reuse checkpoints from a different implementation.
                         implementation={str(p.relative_to(Path(__file__).resolve().parents[1])): file_sha256(p)
                                         for p in [Path(__file__), Path(__file__).parent / 'drone_cloud_workflow.py',
                                                   Path(run_drone_pipeline.__code__.co_filename),
                                                   *[Path(__file__).resolve().parents[1] / 'src/spectralbridge' / name
                                                     for name in ['drone_campaign_inputs.py', 'corrections.py', 'topographic.py',
                                                                  'drone_translation.py', 'drone_view_geometry.py', 'radiometry.py',
                                                                  'drone_radiometry.py', 'neon_cube.py', 'io/neon.py',
                                                                  'envi_writer.py', 'qa_plots.py', 'drone_qa.py']]]})
    if scope == 'campaign':
        require_current_pilot(pilot, contracts, manifest=manifest, polygons=polygons,
                              translation_registry=translation_registry, targets=targets,
                              naming_style=naming_style, output_scale_factor=output_scale_factor)
    signature = _identity(configuration)
    work = Path(work)
    root = work / run_id / signature[:16]
    root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(root / 'run_configuration.json', configuration)
    statuses = {}
    report = dict(status='incomplete', scope=scope, signature=signature, run_root=str(root),
                  flight_products=str(root / 'flight_products'), flights=statuses,
                  targets=list(targets), output_scale_factor=output_scale_factor)
    for index, package in enumerate(inventory.eligible_packages, 1):
        key = package.remote_package_path
        contract = contracts[key]
        label = f'{package.year}_{package.package_name}'
        print(f'[VM drone] {index}/{len(inventory.eligible_packages)} {label}', flush=True)
        staging = work / 'staged_sources' / label
        prepared = work / 'prepared_sources' / str(package.year) / package.package_name
        output = root / 'flight_products' / label
        try:
            camera = camera_entry(backend, contract['camera_collection'], explicit_name=contract.get('camera_filename'))
            camera_meta = stage_camera(backend, camera, staging / 'camera',
                                       crs_override=contract['camera_geometry'].get('crs_override'),
                                       crs_override_provenance=contract['camera_geometry'].get('crs_override_provenance'))
            download_sources(package, staging, backend)
            actual_source = staging / package.h5_name
            if file_sha256(actual_source) != contract['source_sha256']:
                raise ValueError('Actual downloaded source does not match reviewed calibration SHA256')
            reference, tiff_options = prepare_reference(staging, package.h5_name, prepared, use_legacy_view=False)
            flight_id = derive_drone_flight_stem(reference)
            record = brightness_record(contract['brightness_json'])
            base = contract['source_radiometry']
            if 'input_encoding' in base:
                base = radiometry_from_source_encoding(base).record()
            else:
                base = Radiometry.from_record(base).require_valid().record()
            compose_brightness_calibration(record, flight_id=flight_id, source_sha256=contract['source_sha256'],
                                           wavelengths_nm=tiff_options['tiff_wavelengths_nm'], source_radiometry=base)
            # The derived TIFF has exactly the source H5's retained numeric values.
            # Bind the execution copy to those bytes while preserving the original
            # provider declaration and its source derivation in provenance.
            adapted = dict(record, source_sha256=file_sha256(reference),
                           source_derivation=dict(original_source_sha256=contract['source_sha256'],
                                                  provider_declaration_sha256=_identity(record),
                                                  recipe_sha256=file_sha256(prepared / 'source_recipe.json')))
            geometry = dict(contract['camera_geometry'], camera_locations=camera_meta['path'])
            mask = dict(contract['processing_mask']) if contract.get('processing_mask') else None
            for field, remote in contract.get('auxiliary_sources', {}).items():
                path = stage_auxiliary(backend, remote, staging / 'auxiliary' / field / remote.rsplit('/', 1)[-1])
                if field == 'processing_mask':
                    if mask is None:
                        raise ValueError('Mask auxiliary supplied without an explicit mask policy')
                    mask['path'] = str(path)
                elif field in {'surface', 'camera_index'}:
                    geometry[field] = str(path)
                else:
                    raise ValueError(f'Unknown auxiliary role: {field}')
            result = run_drone_pipeline(
                reference, polygon_path=polygons, output_dir=output, radiometry=base,
                brightness_calibration=adapted, camera_geometry=geometry, processing_mask=mask,
                drone_manifest_path=manifest, require_solar_geometry=True,
                apply_translation=True, translation_coefficients=translation_registry,
                translation_target_sensors=targets, translation_naming_style=naming_style,
                translation_output_scale_factor=output_scale_factor,
                merge_extractions=False, overwrite=False, raise_on_incomplete=False,
                **contract['pipeline'], **tiff_options)
            write_json_atomic(output / 'pipeline_result.json', result)
            flight_dir = verify_flight(result, targets, output_scale_factor)
            provenance = flight_dir / 'campaign_provenance'
            provenance.mkdir(exist_ok=True)
            shutil.copy2(camera_meta['path'], provenance / Path(camera_meta['path']).name)
            shutil.copy2(prepared / 'source_recipe.json', provenance / 'source_recipe.json')
            write_json_atomic(provenance / 'provider_brightness.json', record)
            write_json_atomic(provenance / 'execution_brightness.json', adapted)
            write_json_atomic(provenance / 'flight_contract.json', contract)
            write_json_atomic(provenance / 'camera_audit.json', camera_meta)
            for receipt in staging.rglob('*.transfer.json'):
                destination = provenance / 'transfers' / receipt.relative_to(staging)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(receipt, destination)
            statuses[key] = dict(status='complete', flight_dir=str(flight_dir))
        except Exception as exc:
            statuses[key] = dict(status='blocked_or_failed', error=f'{type(exc).__name__}: {exc}')
            print(f'[VM drone] {label}: {statuses[key]["error"]}', flush=True)
        write_json_atomic(root / 'campaign_result.json', report)
    if all(s['status'] == 'complete' for s in statuses.values()) and len(statuses) == len(inventory.eligible_packages):
        report['status'] = 'complete'
    write_json_atomic(root / 'campaign_result.json', report)
    return report


def upload_verified_campaign(report, *, backend, remote_results_parent):
    """Publish a complete run, read back SHA256 per object, then publish its receipt.

    Readback uses one temporary file at a time. Original/raw staging directories
    are outside this root. Changed configurations receive distinct destinations.
    """
    if report.get('status') != 'complete' or not report.get('flights') or any(s.get('status') != 'complete' for s in report['flights'].values()):
        raise ValueError('Incomplete/empty campaign cannot be uploaded as complete')
    root = Path(report['run_root'])
    products = Path(report['flight_products'])
    if not products.is_relative_to(root) or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Delivery must contain only durable run-owned files')
    # Upload only the configuration/result evidence and processed subtree.
    metadata = root / 'delivery_metadata'
    metadata.mkdir(exist_ok=True)
    for name in ['run_configuration.json', 'campaign_result.json']:
        shutil.copy2(root / name, metadata / name)
    payload = {str(path.relative_to(root)): dict(bytes=path.stat().st_size, sha256=file_sha256(path))
               for folder in [products, metadata] for path in sorted(folder.rglob('*'))
               if path.is_file() and path.name != 'upload_manifest.json'}
    delivery_identity = _identity(dict(signature=report['signature'], payload=payload))
    destination = remote_join(remote_results_parent, f'{root.parent.name}_{report["scope"]}_{delivery_identity[:16]}')
    largest_object = max((item['bytes'] for item in payload.values()), default=0)
    if shutil.disk_usage(root).free < largest_object:
        raise OSError('Persistent VM disk needs room for one largest-object verification readback')
    verified = []
    for folder in [products, metadata]:
        remote = upload_tree(folder, destination, backend.executable)
        with tempfile.TemporaryDirectory(prefix='drone-upload-readback-', dir=root) as scratch:
            for path in sorted(folder.rglob('*')):
                if not path.is_file():
                    continue
                key = str(path.relative_to(folder))
                remote_path = remote_join(remote, key)
                print(f"[VM drone] verify readback {remote_path} ({path.stat().st_size:,} bytes)", flush=True)
                snapshot = payload.get(str(path.relative_to(root)))
                local_hash = snapshot['sha256'] if snapshot else file_sha256(path)
                expected_bytes = snapshot['bytes'] if snapshot else path.stat().st_size
                copy = Path(scratch) / 'object'
                backend.download_file(remote_path, copy)
                if copy.stat().st_size != expected_bytes or file_sha256(copy) != local_hash:
                    raise RuntimeError(f'Remote readback mismatch: {remote_path}')
                copy.unlink()
                verified.append(dict(path=remote_path, bytes=path.stat().st_size, sha256=local_hash))
    receipt = dict(status='complete', scope=report['scope'], signature=report['signature'],
                   verification='full remote SHA256 readback', objects=verified)
    receipt_dir = root / 'completion'
    receipt_dir.mkdir(exist_ok=True)
    write_json_atomic(receipt_dir / 'campaign_complete.json', receipt)
    # Last object group is the completion marker, only after all payload reads.
    final_remote = upload_tree(receipt_dir, destination, backend.executable)
    with tempfile.TemporaryDirectory(prefix='drone-receipt-readback-', dir=root) as scratch:
        copy = Path(scratch) / 'receipt.json'
        backend.download_file(remote_join(final_remote, 'campaign_complete.json'), copy)
        if file_sha256(copy) != file_sha256(receipt_dir / 'campaign_complete.json'):
            raise RuntimeError('Completion receipt readback mismatch')
    return dict(destination=destination, completion_receipt=remote_join(final_remote, 'campaign_complete.json'),
                verified_objects=len(verified), signature=report['signature'])
