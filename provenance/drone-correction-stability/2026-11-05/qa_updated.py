"""Reuse the established QA implementation against the new isolated namespace."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';sys.path.insert(0,str(PRIOR))
import build_qa as qa
WORK=ROOT/'archive/local/drone-correction-stability/2026-11-05/stable_qr_v1';qa.WORK=WORK;qa.HERE=HERE;qa.FIG=HERE/'figures';(HERE/'site_inputs.json').write_text((PRIOR/'site_inputs.json').read_text());qa.main()
# The supplementary script is top-level code with dependencies supplied by prepare_rerun.
source=(PRIOR/'compare_support.py').read_text().replace('from prepare_rerun import HERE,WORK','from prepare_rerun import HERE,WORK\nHERE=Path('+repr(str(HERE))+')\nWORK=Path('+repr(str(WORK))+')')
exec(compile(source,str(PRIOR/'compare_support.py'),'exec'),{'__name__':'__main__'})
