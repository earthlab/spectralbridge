"""Exact bounded comparisons, immutable inputs, and experimental gate checks."""
import json,sys,hashlib
from pathlib import Path
import numpy as np,rasterio
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';sys.path.insert(0,str(PRIOR))
from prepare_rerun import sha
from spectralbridge.envi import hdr_to_dict
from spectralbridge.radiometry import require_library_header
rows=[];immutable=[];catalog=[];total=0
for cfg in json.loads((PRIOR/'site_inputs.json').read_text()):
 name=cfg['site'];site=name.lower();old=json.loads((PRIOR/f'{site}_correction_summary.json').read_text())
 for path,digest in cfg['input_sha256'].items():
  assert sha(path)==digest,path
  immutable.append(dict(path=path,sha256=digest,status='UNCHANGED'))
 for path,digest in old['output_sha256'].items():
  assert sha(path)==digest,path
  immutable.append(dict(path=path,sha256=digest,status='UNCHANGED'))
 original={r['branch']:r for r in old['branches']}
 baseline={r['branch']:r for r in json.loads((HERE/'baseline_frozen_v2'/f'{site}_pipeline_results.json').read_text())}
 after={r['branch']:r for r in json.loads((HERE/'stable_qr_v1'/f'{site}_pipeline_results.json').read_text())}
 for branch,r in original.items():
  before=baseline[branch];new=after[branch];assert r['status']==before['status']==new['status']
  rec=dict(site=name,branch=branch,status=r['status'])
  if r['status']!='EXECUTED_EXPERIMENTAL':rows.append(rec);continue
  source,rep,updated,envi=[rasterio.open(p) for p in [r['geotiff'],before['geotiff'],new['geotiff'],new['image']]]
  finite=0;changed=0;maxdelta=0;supportchanged=0
  for b in range(1,11):
   for y in range(0,source.height,128):
    win=rasterio.windows.Window(0,y,source.width,min(128,source.height-y));a,bb,d,e=[f.read(b,window=win) for f in [source,rep,updated,envi]]
    assert np.array_equal(a,bb,equal_nan=True),'Baseline was not reproduced'
    assert np.array_equal(d,e,equal_nan=True),'Native ENVI differs'
    supportchanged+=int(np.sum(np.isfinite(a)!=np.isfinite(d)));both=np.isfinite(a)&np.isfinite(d);changed+=int(np.sum(a[both]!=d[both]));maxdelta=max(maxdelta,float(np.max(np.abs(a[both]-d[both]))) if both.any() else 0);finite+=int(np.isfinite(d).sum())
  assert source.crs==updated.crs and source.transform==updated.transform
  hdr=hdr_to_dict(Path(new['header']));assert hdr['radiometry status']=='HYPOTHETICAL_UNVERIFIED' and hdr['scientific validation status']=='EXPERIMENTAL'
  try:require_library_header(hdr)
  except ValueError:pass
  else:raise AssertionError('Unapproved product accepted')
  total+=finite;rec.update(baseline_exact=True,new_native_envi_exact=True,finite_values=finite,changed_finite_values=changed,max_stored_delta=maxdelta,changed_support_cells=supportchanged,crs_affine_exact=True,approved_library_rejected=True);rows.append(rec)
  catalog.append(dict(site=name,branch=branch,geotiff=new['geotiff'],header=new['header'],sha256=sha(new['geotiff']),bytes=Path(new['geotiff']).stat().st_size,status='EXPERIMENTAL_NOT_PRODUCTION_APPROVED'))
  for f in [source,rep,updated,envi]:f.close()
 print(name,'verified baseline, updated outputs and unchanged products',flush=True)
(HERE/'verification.json').write_text(json.dumps(dict(finite_values_verified=total,comparisons=rows,immutable_artifacts=immutable),indent=2)+'\n');(HERE/'product_catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
