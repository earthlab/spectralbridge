"""Fresh full reprocessing of the three explicitly requested drone packages.

Run from the repository root. Uses the tested notebook's actual producer/bulk/
upload cells, original sources, and a new dedicated output collection. Never
rewrites authoritative sources, earlier Ruby tests or historical products.
"""
from dataclasses import replace
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
WORK = Path('/private/tmp/spectralbridge-three-flight-reprocess/gordon_goldhill_ruby_20261029_v1')
SOURCE = 'i:/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023-10cm-10k'
PACKAGES = (
    'AOP-GORDON-08-14-23-ExportPackage',
    'AOP-GOLDHILL-08-14-23-ExportPackage',
    'AOP-Ruby-08-14-23-ExportPackage',
)
GOCMD = '/private/tmp/spectralbridge-gocmd/gocmd'
REMOTE = 'i:/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/' + WORK.name


def validate_flights(namespace):
    reports = {}
    for package in namespace['inventory'].eligible_packages:
        label = f'{package.year}_{package.package_name}'
        output = namespace['FLIGHTS'] / label
        result_path = output / 'pipeline_result.json'
        result = json.loads(result_path.read_text())
        audit = result['qa_summary']['files'][0]
        flight = Path(audit['flight_dir'])
        stem = flight.name
        source = WORK / 'staged_sources' / label / 'aligned_orthomosaic.tif'
        evidence = EVIDENCE / package.package_name
        evidence.mkdir(exist_ok=True)
        print('INDEPENDENT VALIDATION:', label, flush=True)
        command = [sys.executable, str(REPO / 'scripts/diagnose_drone_spatial_integrity.py')]
        for key, path in {
            'source-tiff': source,
            'h5': flight / (stem + '__working.h5'),
            'native': flight / (stem + '__envi.img'),
            'corrected': flight / (stem + '__corrected.img'),
            'final': flight / (stem + '__landsat_like_landsat_oli_translated_envi.img'),
            'polygons': namespace['POLYGONS'],
            'parquet': flight / (stem + '__polygons.parquet'),
            'parquet-value-raster': flight / (stem + '__corrected.img'),
            'output': evidence / 'spatial_check',
        }.items():
            command.extend(['--' + key, str(path)])
        command.extend(['--source-bands', '1,2,3,4,5,6,7,8,9,10', '--id-column', 'GlobalID',
                        '--label', f'{stem}: full source-grid reprocessing'])
        subprocess.run(command, check=True)
        subprocess.run([
            sys.executable,
            str(REPO / 'provenance/drone-spatial-integrity/2026-10-29/validate_ruby_outputs.py'),
            '--source', str(source), '--result', str(result_path),
            '--output', str(evidence / 'full_pixel_checks.json'),
        ], check=True)
        checks = json.loads((evidence / 'full_pixel_checks.json').read_text())
        checks['scope'] = 'Spatial/arithmetic conformance with the declared retained bands and existing correction/translation; physical radiometry is not independently validated.'
        checks['manifest_acquisition_datetime'] = package.acquisition_datetime
        checks['package_date'] = package.flight_stem.rsplit('_', 1)[-1]
        checks['validation_implementation'] = 'provenance/drone-spatial-integrity/2026-10-29/validate_ruby_outputs.py'
        namespace['write_json'](evidence / 'full_pixel_checks.json', checks)
        assert checks['corrected_crs_matches_source'] and checks['corrected_affine_matches_source']
        assert checks['correction_mask_mismatches_against_source_and_terrain_policy'] == 0
        assert checks['correction_filled_source_nodata_values'] == 0
        for product in checks['translations']:
            assert not product['finite_value_mismatches'] and not product['mask_mismatches']
            assert product['crs_matches_source'] and product['affine_matches_source']
        spatial = json.loads((evidence / 'spatial_check/discrepancies.json').read_text())
        reports[package.package_name] = {
            'flight_dir': str(flight), 'records': spatial['parquet']['records'],
            'values_checked': spatial['parquet']['raw_values_checked'],
            'maximum_displacement_pixels': max(v['maximum_pixels'] for v in spatial['comparisons'].values()),
            'translation_values_checked': sum(v['values_checked'] for v in checks['translations']),
            'scientific_qa_status': checks['qa_scientific_status'],
        }
        shutil.copy2(result_path, evidence / 'pipeline_result.json')
        namespace['write_json'](EVIDENCE / 'validation_summary.json', reports)
    assert len(reports) == 3
    namespace['write_json'](namespace['STATE'] / 'independent_validation.json', reports)
    shutil.copytree(EVIDENCE, namespace['STATE'] / 'validation_evidence', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__'))
    return reports


def main():
    notebook_path = REPO / 'Drone_2023_2024_Cloud_Production.ipynb'
    notebook = json.loads(notebook_path.read_text())
    namespace = {'__name__': '__main__'}
    timings = []

    def cell(index):
        started = time.monotonic()
        print(f'NOTEBOOK CELL {index} starting', flush=True)
        exec(compile(''.join(notebook['cells'][index]['source']), f'notebook_cell_{index}', 'exec'), namespace)
        timings.append({'cell': index, 'seconds': round(time.monotonic() - started, 3), 'status': 'passed'})
        print('NOTEBOOK CELL', index, 'passed', flush=True)
        (EVIDENCE / 'cell_execution.json').write_text(json.dumps(timings, indent=2) + '\n')

    cell(1)
    namespace.update(REPO=REPO, WORK_PARENT=WORK.parent, RUN_ID=WORK.name, WORK=WORK,
                     SOURCES={2023: SOURCE}, GOCMD=GOCMD, RUN=True, UPLOAD=True,
                     INSTALL_PACKAGE=False, CLEANUP_STAGED_INPUTS=False,
                     TEST_PACKAGE=None, REMOTE_RESULTS=REMOTE)
    cell(3)
    cell(4)
    write_json = namespace['write_json']
    selected = []
    sources = []
    for name in PACKAGES:
        raw = namespace['inspect_drone_collection'](
            {2023: SOURCE + '/' + name}, years=[2023], manifest=namespace['MANIFEST'],
            backend=namespace['backend'], inventory_output_dir=namespace['STATE'] / 'inventory' / name,
        )
        individual = namespace['select_inventory'](raw, name)
        assert individual.discovery_complete and len(individual.eligible_packages) == 1
        selected.append(individual.eligible_packages[0])
        sources.append(individual.year_sources[0])
    assert {p.package_name for p in selected} == set(PACKAGES)
    year = replace(sources[0], requested_source=SOURCE,
                   resolved_sources=tuple(p.remote_package_path for p in selected),
                   expected_manifest_flights=tuple(p.manifest_id for p in selected))
    inventory = replace(individual, source=SOURCE, packages=tuple(selected), year_sources=(year,))
    inventory.write(namespace['STATE'] / 'requested_three_flight_inventory')
    namespace['inventory'] = inventory
    config = {'scope': 'complete_requested_three_flight_reprocess', 'requested_packages': PACKAGES,
              'work': WORK, 'source': SOURCE, 'remote_results': REMOTE,
              'bands': list(namespace['REFLECTANCE_BANDS']), 'cautions': namespace['CAUTIONS'],
              'manifest': str(namespace['MANIFEST']), 'polygons': str(namespace['POLYGONS']),
              'software_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()}
    write_json(namespace['STATE'] / 'run_configuration.json', config)
    write_json(EVIDENCE / 'run_configuration.json', config)
    prior = REPO / 'provenance/drone-cloud-integration/2026-10-29'
    snapshot = json.loads((prior / 'validated_code_snapshot.json').read_text())
    snapshot['base_commit'] = config['software_head']
    snapshot['files']['src/spectralbridge/qa_plots.py'] = {}
    snapshot['files'] = {name: {'bytes': (REPO / name).stat().st_size,
                                'sha256': hashlib.sha256((REPO / name).read_bytes()).hexdigest()}
                         for name in snapshot['files']}
    snapshot['revision_note'] = 'Coordinate-roundoff validation plus exact bounded QA quantiles; no resampling, correction formula, raster or extraction value changes.'
    snapshot.pop('clean_base_patch_application_verified', None)
    snapshot.pop('verified_reconstruction_files', None)
    patch = subprocess.check_output(['git', 'diff', '--binary', 'HEAD', '--', 'src/spectralbridge'], cwd=REPO)
    for name in ['scripts/drone_cloud_workflow.py', 'Drone_2023_2024_Cloud_Production.ipynb']:
        diff = subprocess.run(['git', 'diff', '--no-index', '--binary', '--', '/dev/null', name], cwd=REPO, capture_output=True)
        assert diff.returncode == 1
        patch += diff.stdout
    for folder in [EVIDENCE, namespace['STATE']]:
        (folder / 'validated_workflow.patch').write_bytes(patch)
        write_json(folder / 'validated_code_snapshot.json', snapshot)
    cell(8)  # All products are freshly computed in this new workspace.
    namespace['require_complete'](inventory, namespace['statuses'])
    validate_flights(namespace)
    cell(10)  # Exactly three completed, independently validated flights.
    assert namespace['preflight']['accepted_flightline_count'] == 3
    cell(12)
    for name in ['bulk_result.json', 'bulk_preflight_result.json', 'summary_result.json', 'status.json']:
        shutil.copy2(namespace['STATE'] / name, EVIDENCE / name)
    write_json(EVIDENCE / 'completed_run.json', {'status': 'processed_and_uploaded', 'work': WORK,
               'remote_results': REMOTE, 'packages': PACKAGES, 'cells': timings,
               'scientific_status': 'review_required; existing source provenance cautions preserved'})
    print('THREE-FLIGHT REPROCESS COMPLETE:', WORK, REMOTE, flush=True)


if __name__ == '__main__':
    main()
