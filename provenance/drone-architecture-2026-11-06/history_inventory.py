"""Read-only history, actual H5 metadata and costs; no historical reprocessing."""
from pathlib import Path
import json,hashlib,subprocess,re
import h5py,numpy as np
P=Path(__file__).resolve().parent;R=P.parents[1];references=[
('H5/spatial','provenance/drone-spatial-integrity/2026-10-29/README.md'),('Original radiometric maps','provenance/drone-scale-confirmation/2026-10-30/README.md'),('Shared radiometry/BRDF audit','provenance/radiometry-brdf/2026-10-30/README.md'),('Red artifact','provenance/brdf-artifact-anatomy/2026-11-03/report.md'),('Clean source','provenance/goldhill-clean-source-brdf/2026-11-03/report.md'),('Pose artifact','provenance/brdf-artifact-anatomy-part-ii/2026-11-04/report.md'),('Camera rerun','DRONE_CAMERA_RERUN_REPORT.md'),('Stability','DRONE_CORRECTION_STABILITY_REPORT.md'),('Metashape','METASHAPE_RECOVERY_REPORT.md'),('Original-photo Ruby','provenance/ruby-correction-recovery-2026-11-06/REPORT.md'),('Ruby topography','provenance/ruby-topographic-recovery-2026-11-06/REPORT.md')]
summary=[]
for label,path in references:
 f=R/path;s=f.read_text();summary.append(dict(topic=label,path=path,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),headings=[x for x in s.splitlines() if x.startswith('#')],review_excerpt='\n'.join(s.splitlines()[:22])))
(P/'history_sources.json').write_text(json.dumps(summary,indent=2)+'\n')
log=subprocess.run(['git','log','--reverse','--format=%h %as %s','--','src/spectralbridge/pipelines/drone.py'],capture_output=True,text=True,check=True);(P/'git_drone_history.txt').write_text(log.stdout)
scan=[]
for f in (R/'src/spectralbridge').rglob('*.py'):
 for n,line in enumerate(f.read_text().splitlines(),1):
  if re.search(r'32768|65535|10000|min.?max|reflectance.*scale',line,re.I):scan.append(dict(file=str(f.relative_to(R)),line=n,text=line.strip()))
(P/'radiometry_code_inventory.json').write_text(json.dumps(scan,indent=2)+'\n')
from spectralbridge.radiometry import dataset_radiometry
legacy=json.loads((R/'provenance/drone-spatial-integrity/2026-10-29/production_source_comparison.json').read_text());h5=[]
for row in legacy:
 path=Path(row['source_h5']);rec=dict(flight=row['flight'],path=str(path),exists=path.exists())
 if path.exists():
  with h5py.File(path,'r') as h:
   items=[];h.visititems(lambda name,obj:items.append((name,obj)) if isinstance(obj,h5py.Dataset) else None);reflect=next(o for n,o in items if n.endswith('Reflectance_Data'));rec.update(bytes=path.stat().st_size,shape=list(reflect.shape),dtype=str(reflect.dtype),attrs={k:np.asarray(v).tolist() if not isinstance(v,bytes) else v.decode(errors='replace') for k,v in reflect.attrs.items()},datasets=[dict(path=n,shape=list(o.shape),attrs={k:str(v) for k,v in o.attrs.items()}) for n,o in items]);rec['wavelengths_nm']=next(o[:].tolist() for n,o in items if n.endswith('/Wavelength'))
  from spectralbridge.radiometry import dataset_radiometry
  with h5py.File(path,'r') as h:
   objects=[];h.visititems(lambda name,obj:objects.append(obj) if isinstance(obj,h5py.Dataset) and name.endswith('Reflectance_Data') else None);rec['current_radiometry']=dataset_radiometry(objects[0]).record()
 h5.append(rec)
# Inspect available derived H5s too, explicitly separated from absent originals.
for item in json.loads((R/'provenance/drone-correction-stability/2026-11-05/site_inputs.json').read_text()):
 path=Path(item['solar_h5']);rec=dict(flight=item['flight_stem'],path=str(path),exists=path.exists(),role='Nov4 TIFF-derived preparation H5; not the original legacy H5')
 if path.exists():
  with h5py.File(path,'r') as h:
   items=[];h.visititems(lambda n,o:items.append((n,o)) if isinstance(o,h5py.Dataset) else None);ds=next(o for n,o in items if n.endswith('Reflectance_Data'));rec.update(bytes=path.stat().st_size,shape=list(ds.shape),attrs={k:str(v) for k,v in ds.attrs.items()},datasets=[dict(path=n,shape=list(o.shape),attrs={k:str(v) for k,v in o.attrs.items()}) for n,o in items],wavelengths_nm=next(o[:].tolist() for n,o in items if n.endswith('/Wavelength')),current_radiometry=dataset_radiometry(ds).record())
 h5.append(rec)
(P/'actual_h5_inventory.json').write_text(json.dumps(h5,indent=2,default=str)+'\n')
cost=[]
for name in ['ruby-correction-recovery-2026-11-06','ruby-topographic-recovery-2026-11-06']:
 state=json.loads((R/'provenance'/name/'run_state.json').read_text());cost.append(dict(investigation=name,measured_stage_seconds={k:v.get('seconds',v.get('elapsed_seconds')) for k,v in state.items()},scope='Measured completed research stages on this Mac, excludes earlier transfers and manual investigation'))
packet=R/'provenance/metashape-recovery/2026-11-05';inventory=json.loads((packet/'remote_inventory.json').read_text());cost.append(dict(investigation='Metashape remote inventory',bytes=inventory['total_bytes'],objects=inventory['unique_objects'],scope='Ruby+Goldhill only; Gordon new project not located'));cost.append(dict(investigation='Portable Ruby adjusted geometry',bytes=sum(f.stat().st_size for f in (packet/'extracted').glob('*RUBY*chunk_0/*') if f.suffix in ['.parquet','.json']),scope='Camera table and sensor/chunk metadata; excludes surfaces/primary assignment archive'))
(P/'measured_costs.json').write_text(json.dumps(cost,indent=2)+'\n');print('Reviewed reports',len(summary),'actual H5 files',sum(r['exists'] for r in h5),'scaling code references',len(scan))
