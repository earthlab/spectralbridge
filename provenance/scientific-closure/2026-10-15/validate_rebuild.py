"""Verify byte-identical reconstruction of the final publication artifacts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
PDF = REPO / 'output/pdf/scientific_closure/What_Can_We_Reliably_Learn_from_the_SpectralBridge_Spectral_Library.pdf'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    files = sorted(p for p in (BASE / 'figures').iterdir() if p.suffix in {'.png', '.pdf', '.svg'}) + [PDF]
    assert len(files) == 16
    before = {str(p.relative_to(REPO)): digest(p) for p in files}
    env = dict(os.environ, MPLCONFIGDIR='/tmp/spectralbridge-mpl', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    subprocess.run([str(REPO / '.venv/bin/python'), str(BASE / 'build_figures.py')], cwd=REPO, env=env, check=True)
    subprocess.run([sys.executable, str(BASE / 'build_report.py')], cwd=REPO, env=env, check=True)
    after = {str(p.relative_to(REPO)): digest(p) for p in files}
    assert before == after, 'Publication artifacts changed on reconstruction'
    result = {'passed': True, 'byte_identical_files': len(files), 'sha256': after}
    (BASE / 'manifests/rebuild_validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Verified byte-identical reconstruction of 15 figure files and the report.')


if __name__ == '__main__':
    main()
