"""Fresh native three-site execution with immutable P181 geometry/source backing."""
import sys,json,shutil,hashlib,argparse,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';sys.path.insert(0,str(PRIOR))
import correct_sites as driver
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--baseline',action='store_true');args=p.parse_args()
BASE=driver.WORK;WORK=ROOT/'archive/local/drone-correction-stability/2026-11-05'/args.label;WORK.mkdir(parents=True,exist_ok=True)
EVIDENCE=HERE/args.label;EVIDENCE.mkdir(exist_ok=True)
if args.baseline:
 saved=HERE/'reproduced_baseline'
 def load(name,path):
  spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
 t=load('spectralbridge._p182_baseline_topographic',saved/'source_topographic.py')
 c=load('spectralbridge._p182_baseline_corrections',saved/'source_corrections.py')
 c.cluster_covariance=t.cluster_covariance;c.apply_conditioned_scs_c=t.apply_conditioned_scs_c
 driver.support.c=c;driver.support.topo=t
for module in ['corrections.py','topographic.py']:
 src=(HERE/'reproduced_baseline'/('source_'+module)) if args.baseline else ROOT/'src/spectralbridge'/module;dst=EVIDENCE/('source_'+module)
 if dst.exists() and dst.read_bytes()!=src.read_bytes():raise ValueError('Preserve previous source snapshot: '+str(dst))
 if not dst.exists():shutil.copy2(src,dst)
driver.WORK=WORK;driver.HERE=EVIDENCE
for config in json.loads((PRIOR/'site_inputs.json').read_text()):
 site=config['site'].lower();folder=WORK/site;folder.mkdir(exist_ok=True)
 for name in ['geometry_complete.json','geometry.npy','center_design.npy','candidate_stored.npy','source_manifest.json']:
  dst=folder/name
  if not dst.exists():dst.symlink_to(BASE/site/name)
 driver.site(config)
(EVIDENCE/'run_complete.json').write_text(json.dumps(dict(label=args.label,work=str(WORK),sources={m:hashlib.sha256((EVIDENCE/('source_'+m)).read_bytes()).hexdigest() for m in ['corrections.py','topographic.py']}),indent=2)+'\n')
