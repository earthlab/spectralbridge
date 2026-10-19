"""Read-only source/evidence audit; write only this new packet's audit results.

This does not fit models, infer physical scales, call historical mutable loaders,
regenerate historical reports or alter their manifests. Run from any directory.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import pyarrow.parquet as pq

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def metadata(path):
    parquet = pq.ParquetFile(path)
    values = parquet.schema_arrow.metadata or {}
    return dict(path=str(path.relative_to(ROOT)), sha256=sha(path),
                rows=parquet.metadata.num_rows,
                metadata_keys=[key.decode(errors='replace') for key in values],
                non_pandas_metadata={key.decode(errors='replace'): value.decode(errors='replace')
                                     for key, value in values.items() if key != b'pandas'},
                scale_unit_columns=[name for name in parquet.schema_arrow.names
                                    if any(key in name.lower() for key in ('scale', 'unit', 'gain', 'offset'))])


def main():
    manifest_paths = [
        ROOT/'provenance/researcher-evidence/2026-10-16/v1/final_manifest.json',
        ROOT/'provenance/researcher-pft-information/2026-10-15/v1/final_manifest.json',
        ROOT/'provenance/endmember-quality/2026-10-19/v1/packet_manifest.json',
        ROOT/'provenance/endmember-quality/2026-10-19/exhaustive-v1/packet_manifest.json',
    ]
    owned = {}
    checks = []
    failures = []
    for manifest in manifest_paths:
        d = json.loads(manifest.read_text())
        files = d.get('sha256', d.get('files'))
        prefix = ROOT if 'sha256' in d else manifest.parent
        for name, expected in files.items():
            path = prefix/name
            key = str(path.relative_to(ROOT))
            if key in owned and owned[key] != expected:
                failures.append(dict(path=key, reason='conflicting manifest ownership'))
            owned[key] = expected
            actual = sha(path) if path.exists() else None
            if actual != expected:
                failures.append(dict(path=key, expected=expected, actual=actual))
        checks.append(dict(path=str(manifest.relative_to(ROOT)), entries=len(files), sha256=sha(manifest)))
    preservation = dict(manifests=checks, unique_owned_files=len(owned), failures=failures,
                        status='passed' if not failures else 'STOP: historical hashes differ')
    (OUT/'historical_preservation.json').write_text(json.dumps(preservation, indent=2)+'\n')
    (OUT/'historical_hashes.json').write_text(json.dumps(owned, indent=2)+'\n')
    if failures:
        raise RuntimeError('Stop-the-line historical hash mismatch; see historical_preservation.json')
    source = ROOT/'Aug_2026_all_polygons_merged_pixel_extraction.parquet'
    compact = ROOT/'artifacts/plant_spectral_atlas/sensor_pft_transfer/compact'
    source_files = [metadata(source)] + [metadata(compact/(stage+'_polygon_year.parquet'))
                                        for stage in ['corr', 'olioli_undarkened']]
    oldinput = ROOT/'provenance/researcher-pft-information/2026-10-15/v1/input_identity.json'
    foundation = ROOT/'provenance/researcher-evidence/2026-10-16/v1/foundation.json'
    old = json.loads(oldinput.read_text())
    found = json.loads(foundation.read_text())
    assert source_files[0]['sha256'] == old['source_sha256'] == found['source_sha256']
    ledger_path = compact.parent/'statistics_manifest.json'
    ledger = json.loads(ledger_path.read_text())
    assert sha(ledger_path) == old['canonical_manifest_sha256']
    for entry in source_files[1:]:
        relative = str(Path(entry['path']).relative_to(compact.parent.relative_to(ROOT)))
        assert entry['sha256'] == ledger['outputs'][relative]
    integration_path = ROOT/'docs/spectral-library/integration-validation.json'
    integration = json.loads(integration_path.read_text())
    for name, expected in integration['source_sha256'].items():
        assert sha(ROOT/name) == expected, name
    exhaustive_path = ROOT/'provenance/endmember-quality/2026-10-19/exhaustive-v1/comparison_summary.json'
    exhaustive = json.loads(exhaustive_path.read_text())
    result = dict(status='STOP: source scaling unclear', instruction='Attached request section 15: source scaling is unclear',
                  git_SHA=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
                  package_version='2.3.0rc1', source_files=source_files,
                  prior_units_statement=old['units'], prior_foundation_units_status=found['units_status'],
                  prior_input_record_sha256=sha(oldinput), prior_foundation_sha256=sha(foundation),
                  canonical_values=integration['scientific_values'],
                  integration_sources_verified=len(integration['source_sha256']),
                  exhaustive_evidence=dict(model_count=exhaustive['model_count'], targets=exhaustive['targets'],
                                            target_model_evaluations=exhaustive['target_model_evaluations'],
                                            metrics=exhaustive['method_metrics']),
                  new_empirical_models_fitted=0, historical_artifacts_regenerated=0,
                  source_scale_inferred=False, production_changes=0)
    (OUT/'source_scale_audit.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], unique_historical_files_verified=len(owned),
                         integration_source_hashes_verified=result['integration_sources_verified'],
                         source_sha256=source_files[0]['sha256']), indent=2))


if __name__ == '__main__':
    main()
