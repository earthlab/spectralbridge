"""Read-only Data Store verification of the isolated integration upload."""
import json
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from drone_cloud_workflow import JsonGocmdBackend, sha256, write_json  # noqa: E402

WORK = Path('/private/tmp/spectralbridge-one-flight-e2e/ruby_integration_20261029_v1')
REMOTE = 'i:/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/' + WORK.name
EXE = '/private/tmp/spectralbridge-gocmd/gocmd'
EVIDENCE = Path(__file__).resolve().parent
READBACK = WORK / 'upload_readback'
READBACK.mkdir(exist_ok=True)
backend = JsonGocmdBackend(EXE)
records = []
for name in ['flight_products', 'bulk_preflight', 'bulk_analysis', 'campaign_state']:
    local = WORK / name
    manifest = local / 'upload_manifest.json'
    remote = REMOTE + '/' + name
    copy = READBACK / (name + '_upload_manifest.json')
    subprocess.run([EXE, 'get', '--diff', '--verify_checksum', remote + '/upload_manifest.json', str(copy)], check=True)
    assert sha256(copy) == sha256(manifest), f'Remote manifest differs: {name}'
    expected = json.loads(copy.read_text())['files']
    directories = ['']
    observed = {}
    while directories:
        parents = directories
        directories = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            entries = list(pool.map(backend.list_directory, [remote + ('/' + p if p else '') for p in parents]))
        for parent, children in zip(parents, entries):
            for child in children:
                relative = (parent + '/' if parent else '') + child.name
                if child.is_collection:
                    directories.append(relative)
                else:
                    observed[relative] = child.size_bytes
    differences = [path for path, info in expected.items() if observed.get(path) != info['bytes']]
    unexpected = sorted(set(observed) - set(expected) - {'upload_manifest.json'})
    assert not differences and not unexpected, (name, differences, unexpected)
    records.append({'directory': remote, 'manifest_sha256': sha256(copy),
                    'verified_files': len(expected), 'verified_bytes': sum(x['bytes'] for x in expected.values()),
                    'size_mismatches': differences, 'unexpected_files': unexpected})
    print('Verified', name, len(expected), 'remote file sizes and identical manifest', flush=True)
    write_json(EVIDENCE / 'remote_verification.json', {'directories': records, 'status': 'in_progress'})

relative = 'flight_products/2023_AOP-Ruby-08-14-23-ExportPackage/AOP_Ruby_20230814/AOP_Ruby_20230814__corrected.img'
copy = READBACK / 'corrected.img'
subprocess.run([EXE, 'get', '--diff', '--verify_checksum', REMOTE + '/' + relative, str(copy)], check=True)
assert sha256(copy) == sha256(WORK / relative), 'Corrected raster upload/readback differs'
write_json(EVIDENCE / 'remote_verification.json', {
    'status': 'passed', 'directories': records,
    'corrected_raster_roundtrip': {'remote': REMOTE + '/' + relative, 'bytes': copy.stat().st_size,
                                  'sha256': sha256(copy), 'matches_local': True},
    'verification_scope': 'Every remote file size and exact manifest; gocmd transfer checksum verification; full corrected raster SHA-256 readback',
})
print('Full corrected raster upload/download SHA-256 matches', flush=True)
