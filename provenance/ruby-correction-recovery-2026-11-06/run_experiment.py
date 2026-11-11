"""Restart-safe stage runner for the frozen P184 Ruby research experiment."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1];parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--retrieve',action='store_true');args=parser.parse_args();env=dict(os.environ,PYTHONPATH='/private/tmp/spectralbridge-metashape-api/module',OPENBLAS_NUM_THREADS='1',MPLCONFIGDIR='/private/tmp/spectralbridge-mpl');state_path=P/'run_state.json';state=json.loads(state_path.read_text()) if state_path.exists() else {};helpers=[R/'src/spectralbridge/drone_original.py',R/'src/spectralbridge/corrections.py',R/'src/spectralbridge/topographic.py']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def stage(name,script,outputs,inputs=()):
 source=P/script;signature=hashlib.sha256(json.dumps({str(f):sha(f) for f in [source,*helpers,*[P/x for x in inputs]]},sort_keys=True).encode()).hexdigest();old=state.get(name,{})
 if old.get('signature')==signature and old.get('status')=='COMPLETE' and all((P/f).exists() and sha(P/f)==h for f,h in old.get('outputs',{}).items()):print('REUSE',name,flush=True);return
 if old.get('status')=='COMPLETE':raise RuntimeError('Completed stage changed; use a new experiment directory: '+name)
 state[name]=dict(status='RUNNING',signature=signature);state_path.write_text(json.dumps(state,indent=2)+'\n');start=time.monotonic();print('START',name,flush=True)
 with (P/(name+'.log')).open('w') as log:
  result=subprocess.run([sys.executable,str(source)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:
  state[name]['status']='FAILED';state_path.write_text(json.dumps(state,indent=2)+'\n');raise RuntimeError('Stage failed; see '+str(P/(name+'.log')))
 state[name].update(status='COMPLETE',elapsed_seconds=time.monotonic()-start,outputs={f:sha(P/f) for f in outputs});state_path.write_text(json.dumps(state,indent=2)+'\n');print('COMPLETE',name,flush=True)
if args.retrieve:stage('retrieve','retrieve_batches.py',['retrieval_manifest.json'],['photo_selection.json'])
# Revalidate source bytes before any checkpoint reuse, not only manifest text.
manifest_path=P/'retrieval_manifest.json'
if manifest_path.exists():
 records=json.loads(manifest_path.read_text());expected=set(json.loads((P/'photo_selection.json').read_text()))
 if {r['remote_path'] for r in records}!=expected:raise RuntimeError('Incomplete source-photo manifest')
 for index,row in enumerate(records,1):
  path=Path(row['local_path'])
  if path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:raise RuntimeError('Source-photo identity changed: '+str(path))
  if index%500==0:print('SOURCE VERIFY',index,'/',len(records),flush=True)
 if (P/'baseline.json').exists():
  baseline=json.loads((P/'baseline.json').read_text())
  if sha(Path(baseline['source']))!=baseline['radiometric_product']['configuration']['source_sha256']:raise RuntimeError('Original mosaic source changed')
  project=Path(baseline['project_path']);files=project.with_suffix('.files');paths=[project,files/'project.zip']+sorted(files.rglob('chunk.zip'))+sorted(files.rglob('frame.zip'))
  identity=[(str(f.relative_to(project.parent)),sha(f)) for f in paths]
  if hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()!=baseline['project_fingerprint']:raise RuntimeError('Source reconstruction changed')
 (P/'source_verification.json').write_text(json.dumps(dict(files=len(records),bytes=sum(r['bytes'] for r in records),all_sha256_verified=True),indent=2)+'\n')
stage('verify_sources','verify_sources.py',['baseline.json'])
stage('exact_rays','validate_exact_rays.py',['exact_ray_validation.json'],['observations_geometry.json'])
stage('calibration_replacement','calibrated_photo_roundtrip.py',['calibrated_photo_roundtrip.json'])
stage('sample','sample_photos.py',['expanded_observations.csv','expanded_photo_radiometry.json'],['observations_geometry.json','retrieval_manifest.json'])
stage('analyze','analyze.py',['observations_enriched.csv','heldout_validation.csv','topographic_models.json','brdf_models.json'],['expanded_observations.csv'])
stage('matched','matched_workflow.py',['correction_status.json','combined_heldout_validation.csv','bootstrap_uncertainty.json'],['observations_enriched.csv'])
print('Experiment complete; consult correction_status.json before any corrected-source export',flush=True)
