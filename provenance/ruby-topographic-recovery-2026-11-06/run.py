"""Restart-safe runner for the source-preserving P185 Ruby experiment."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';prior=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/baseline.json').read_text());source=R/'archive/local/ruby-correction-recovery-2026-11-06/ruby_vendor_fraction_x10000_10cm_v1.tif';env=dict(os.environ,OPENBLAS_NUM_THREADS='1',MPLCONFIGDIR='/private/tmp/spectralbridge-mpl');statefile=P/'run_state.json';state=json.loads(statefile.read_text()) if statefile.exists() else {}
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
inputs=[source,Path(prior['terrain_assets']['viewing_absolute']['path']),Path(prior['terrain_assets']['ground_dtm_chunk']['path']),Path(prior['baseline_site']['polygons']),R/'provenance/ruby-correction-recovery-2026-11-06/observations_enriched.csv',R/'provenance/metashape-recovery/2026-11-05/tie_observations.csv']
helpers=[R/'src/spectralbridge'/f for f in ['drone_topography.py','drone_original.py','topographic.py','corrections.py']]
identity={str(f):sha(f) for f in inputs+helpers};(P/'source_manifest.json').write_text(json.dumps(identity,indent=2)+'\n')
for name,expected in prior['production_source_hashes'].items():
 if sha(name)!=expected:raise RuntimeError('Production baseline changed: '+name)
def stage(script,outputs):
 f=P/(script+'.py');signature=hashlib.sha256(json.dumps(dict(inputs=identity,script=sha(f)),sort_keys=True).encode()).hexdigest();files=[Path(o) if Path(o).is_absolute() else P/o for o in outputs];old=state.get(script,{})
 if old.get('signature')==signature and old.get('status')=='COMPLETE' and all(p.exists() and sha(p)==old['outputs'][str(p)] for p in files):print('REUSE',script,flush=True);return
 if old.get('status')=='COMPLETE':raise RuntimeError('Completed experiment changed; create a distinct investigation run: '+script)
 state[script]=dict(signature=signature,status='RUNNING');statefile.write_text(json.dumps(state,indent=2)+'\n');start=time.monotonic();print('START',script,flush=True)
 with (P/(script+'.log')).open('w') as log:result=subprocess.run([sys.executable,str(f)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT)
 if result.returncode:state[script]['status']='FAILED';statefile.write_text(json.dumps(state,indent=2)+'\n');raise RuntimeError('Stage failed: '+script)
 state[script].update(status='COMPLETE',seconds=time.monotonic()-start,outputs={str(p):sha(p) for p in files});statefile.write_text(json.dumps(state,indent=2)+'\n');print('COMPLETE',script,flush=True)
stage('characterize',['baseline.json','surface_provenance.json','field_polygon_context.json',OUT/'common_grid.npz'])
stage('evaluate',['models.json','spatial_holdouts.csv',OUT/'candidate_maps.npz'])
stage('synthetic_audit',['synthetic_recovery.csv','numerical_audit.json'])
stage('matched_originals',['matched_models.json','matched_holdouts.csv','matched_spectral_stages.csv'])
stage('class_matched',['class_specific/matched_models.json','class_specific/matched_holdouts.csv','class_specific/matched_spectral_stages.csv'])
stage('full_frame',['full_frame_support.csv','full_frame_products.json',*[OUT/(f'dtm_sigma{s}_{p}_{m}__red_support.tif') for s,p,m in [(0,'existing','scsc'),(3,'combined_screened','scsc'),(3,'combined_screened','c_correction'),(3,'combined_screened','minnaert')]]])
stage('sensitivity',['input_sensitivity.json','dependence_summary.json','matched_comparisons.csv','matched_common_support.csv','field_stratum_validation.csv'])
stage('spectral_validation',['complete_spectral_validation.csv','class_boundary_control.json'])
stage('field_holdouts',['field_holdout_predictions.csv','field_holdout_summary.csv'])
stage('figures',['figures/'+n+'.png' for n in ['01_terrain','02_illumination','03_negative_C','04_heterogeneity','05_shadows','06_sensitivity','07_identifiability','08_alternatives','09_holdouts','10_combined','11_full_support','12_workflow']])
stage('report',['REPORT.md','decision.json'])
print('Complete; scientific decision is in decision.json',flush=True)
