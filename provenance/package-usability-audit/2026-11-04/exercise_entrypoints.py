"""Record documented entry-point execution; no imagery download or publication."""
import json,os,subprocess,time
from pathlib import Path
import tomllib
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
PYTHON=Path('/private/tmp/spectralbridge-usability-20261104/venv/bin/python')
ENV={**os.environ,'MPLCONFIGDIR':'/private/tmp/spectralbridge-mpl','OPENBLAS_NUM_THREADS':'1'}

def main():
    records=[]
    commands=tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['scripts']
    jobs=[(name,[str(PYTHON.parent/name),'--help']) for name in commands]
    jobs += [('drone-'+s,[str(PYTHON.parent/'spectralbridge-drone-production'),s,'--help']) for s in ['inventory','campaign','bulk']]
    jobs += [(name,[str(PYTHON),str(ROOT/'examples'/name),*args]) for name,args in [('first_example.py',[]),('scientific_workflows_offline.py',[]),('run_neon_pipeline.py',['--check']),('run_drone_pipeline.py',['--check'])]]
    for name,cmd in jobs:
        before=time.monotonic();p=subprocess.run(cmd,cwd='/private/tmp',env=ENV,text=True,capture_output=True,timeout=90)
        (HERE/(name+'.stdout.txt')).write_text(p.stdout)
        (HERE/(name+'.stderr.txt')).write_text(p.stderr)
        records.append(dict(name=name,command=cmd,returncode=p.returncode,seconds=round(time.monotonic()-before,3)))
        print(name,p.returncode,flush=True)
    (HERE/'entrypoint_execution.json').write_text(json.dumps(records,indent=2)+'\n')
if __name__=='__main__':main()
