"""Seal the final closure packet and explicit analytical dependencies."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
DEST = BASE / 'manifests/final_evidence.json'


def sha(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def main():
    files = {p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p != DEST}
    files.update((REPO / 'output/pdf/scientific_closure').glob('*.pdf'))
    for pattern in ('src/spectralbridge/data/*', 'src/spectralbridge/spectral_closure.py',
                    'tests/test_spectral_closure.py', 'tests/test_scientific_docs_integration.py',
                    'scripts/generate_scientific_docs.py', 'docs/spectral-library/_closure.md',
                    'docs/images/spectral-library/closure-temporal.png'):
        files.update(p for p in REPO.glob(pattern) if p.is_file())
    # Refer to existing compact evidence in place; do not copy inputs or old outputs.
    for folder in ('spectral-library-analytics/2026-10-14', 'mesma-readiness',
                   'real-landsat-validation', 'sensor-pft-transfer'):
        root = REPO / 'provenance' / folder
        files.update(p for p in root.rglob('*.json') if 'manifest' in p.name and p.is_file())
    files.update((REPO / 'provenance/spectral-library-analytics/2026-10-14/tables').glob('*.csv'))
    hashes = {str(p.relative_to(REPO)): sha(p) for p in sorted(files)}
    result = {'status': 'sealed', 'date': '2026-10-15',
              'source_parquet_sha256': 'cd3a8afd2697f09d1f4749f92df8a5e2cc71ee12490d38de12f21f90b2a75978',
              'source_identity_note': 'Original source verified by the closure run; read in place, not copied.',
              'files': hashes}
    DEST.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    for name, expected in hashes.items():
        assert sha(REPO / name) == expected, name
    print(f'Sealed and verified {len(hashes)} files.')


if __name__ == '__main__':
    main()
