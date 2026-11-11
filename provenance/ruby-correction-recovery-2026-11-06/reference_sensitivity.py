"""Explicit reference sensitivity; no production reference changes."""
import json
from pathlib import Path
import numpy as np,pandas as pd
from spectralbridge.drone_original import ross_li_design,reference_in_hull,reference_design
P=Path(__file__).resolve().parent;d=pd.read_csv(P/'observations_enriched.csv');models=json.loads((P/'brdf_models.json').read_text());out=[]
for nm,b in d[d.quality_supported].groupby('wavelength_nm'):
 X=np.c_[np.ones(len(b)),b.ross,b.li];median_solar=float(b.solar_zenith_deg.median());medoid=int(np.argmin(np.linalg.norm((X[:,1:]-X[:,1:].mean(0))/np.std(X[:,1:],axis=0),axis=1)))
 refs=[('unchanged_45deg_nadir',reference_design(),dict(solar_zenith=45,view_zenith=0)),('diagnostic_actual_sun_nadir',ross_li_design([0],[median_solar],[0],[0])[0],dict(solar_zenith=median_solar,view_zenith=0)),('diagnostic_observed_medoid',X[medoid],dict(solar_zenith=float(b.iloc[medoid].solar_zenith_deg),view_zenith=float(b.iloc[medoid].view_zenith_deg),relative_azimuth=float(b.iloc[medoid].relative_azimuth_deg)))]
 fit=next((v for v in models if v['wavelength_nm']==nm and v['model']=='multiplicative_target_amplitudes' and 'coefficients' in v),None)
 for label,ref,angles in refs:
  rec=dict(wavelength_nm=float(nm),reference=label,angles=angles,reference_design=ref.tolist(),joint_support=reference_in_hull(X,ref),production_reference_changed=False)
  if fit:rec['shared_shape_prediction']=float(ref@np.array(fit['coefficients']))
  out.append(rec)
(P/'reference_sensitivity.json').write_text(json.dumps(out,indent=2)+'\n')
