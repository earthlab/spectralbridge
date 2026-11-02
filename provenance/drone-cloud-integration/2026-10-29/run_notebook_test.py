"""Execute the real notebook code cells with an explicitly isolated Ruby test scope.

Run from the repo root. This performs authenticated downloads and, unless
--no-upload is supplied, writes only to the dedicated integration collection.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import traceback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restart', action='store_true')
    parser.add_argument('--no-upload', action='store_true')
    args = parser.parse_args()
    repo = Path.cwd()
    sys.path.insert(0, str(repo / 'scripts'))
    from drone_cloud_workflow import sha256

    notebook = json.loads((repo / 'Drone_2023_2024_Cloud_Production.ipynb').read_text())
    work = Path('/private/tmp/spectralbridge-one-flight-e2e/ruby_integration_20261029_v1')
    evidence = Path(__file__).resolve().parent
    prefix = 'restart_' if args.restart else ''
    namespace = {'__name__': '__main__'}
    results = []

    def science_snapshot():
        return {str(p.relative_to(work)): {'sha256': sha256(p), 'mtime_ns': p.stat().st_mtime_ns}
                for p in sorted((work / 'flight_products').rglob('*'))
                if p.is_file() and (p.suffix in {'.img', '.hdr', '.h5', '.parquet'}
                                    or p.name.endswith('.stage.json'))}

    before = science_snapshot() if args.restart else {}
    for index, cell in enumerate(notebook['cells']):
        if cell['cell_type'] != 'code':
            continue
        print(f'\n>>> NOTEBOOK CELL {index} starting', flush=True)
        started = time.monotonic()
        try:
            exec(compile(''.join(cell['source']), f'notebook_cell_{index}', 'exec'), namespace)
            if index == 1:
                namespace.update(
                    WORK_PARENT=work.parent, RUN_ID=work.name,
                    TEST_PACKAGE='AOP-Ruby-08-14-23-ExportPackage',
                    SOURCES={2023: 'i:/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023-10cm-10k/AOP-Ruby-08-14-23-ExportPackage'},
                    GOCMD='/private/tmp/spectralbridge-gocmd/gocmd',
                    RUN=True, UPLOAD=not args.no_upload, INSTALL_PACKAGE=False, WORK=work,
                )
                namespace['REMOTE_RESULTS'] = namespace['REMOTE_PARENT'] + '/spectralbridge_processed/' + work.name
            results.append({'cell': index, 'status': 'passed', 'seconds': round(time.monotonic() - started, 3)})
            print(f'>>> NOTEBOOK CELL {index} passed ({results[-1]["seconds"]} s)', flush=True)
        except Exception as exc:
            traceback.print_exc()
            results.append({'cell': index, 'status': 'failed', 'error': str(exc), 'seconds': round(time.monotonic() - started, 3)})
            (evidence / (prefix + 'cell_execution.json')).write_text(json.dumps(results, indent=2) + '\n')
            raise
        (evidence / (prefix + 'cell_execution.json')).write_text(json.dumps(results, indent=2) + '\n')
    scope = {'notebook': str(repo / 'Drone_2023_2024_Cloud_Production.ipynb'), 'work': str(work),
             'remote_results': namespace['REMOTE_RESULTS'], 'scope': 'one_flight_integration_test',
             'installation_tested': False, 'uploaded': not args.no_upload,
             'environment': 'local macOS Python; Linux cloud container not exercised', 'results': results}
    (evidence / (prefix + 'test_scope.json')).write_text(json.dumps(scope, indent=2) + '\n')
    if args.restart:
        after = science_snapshot()
        changes = [p for p in set(before) | set(after) if before.get(p) != after.get(p)]
        # These are regenerated run audits, not persisted raster/table products.
        refreshed_audits = [p for p in changes if p.endswith('/qa/report.stage.json')
                            or p.endswith('/spatial_dependencies.stage.json')]
        product_changes = sorted(set(changes) - set(refreshed_audits))
        record = {'tracked_scientific_products': len(before), 'changed_products': product_changes, 'refreshed_run_audits': refreshed_audits,
                  'before': before, 'after': after}
        (evidence / 'restart_products.json').write_text(json.dumps(record, indent=2) + '\n')
        assert before and not product_changes, f'Unexpected scientific product rewrite: {product_changes}'
        print('Restart preserved', len(before) - len(refreshed_audits), 'scientific products/checkpoints and timestamps;', len(refreshed_audits), 'run audits refreshed', flush=True)


if __name__ == '__main__':
    main()
