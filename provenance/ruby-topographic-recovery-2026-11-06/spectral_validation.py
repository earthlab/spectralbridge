"""Complete-spectrum and proxy-boundary controls; missing bands are not filled."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from spectralbridge.drone_topography import topographic_factors
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';d=pd.read_csv(P/'matched_spectral_stages.csv');rows=[]
for key,g in d.groupby(['sigma','population','method','target_id','master_key']):
 if g.wavelength_nm.nunique()!=10:continue
 a=g.sort_values('wavelength_nm');raw=a.raw.to_numpy();corrected=a.combined.to_numpy();cos=np.dot(raw,corrected)/(np.linalg.norm(raw)*np.linalg.norm(corrected));angle=float(np.rad2deg(np.arccos(np.clip(cos,-1,1))));get=lambda column,nm:float(a[a.wavelength_nm==nm][column].iloc[0]);ndvi=lambda col:(get(col,842)-get(col,668))/(get(col,842)+get(col,668));rows.append(dict(sigma=key[0],population=key[1],method=key[2],target_id=key[3],master_key=key[4],spectral_angle_degrees=angle,raw_ndvi=ndvi('raw'),corrected_ndvi=ndvi('combined'),negative=int((corrected<0).sum()),above_one=int((corrected>1).sum()),maximum_fraction=float(corrected.max())))
pd.DataFrame(rows).to_csv(P/'complete_spectral_validation.csv',index=False)
g=np.load(OUT/'common_grid.npz');models=json.loads((P/'models.json').read_text());factor=np.full(g['valid'].shape,np.nan)
for label,pop in [(1,'canopy_proxy'),(2,'herbaceous_proxy'),(3,'exposed_proxy'),(4,'mixed_proxy')]:
 m=next(v for v in models if v['surface']=='ground_dtm_chunk' and v['sigma']==3 and v['wavelength_nm']==650 and v['strategy']=='ols' and v['method']=='scsc' and v['population']==pop);app=topographic_factors(g['ground_dtm_chunk_sigma3_incidence'],g['ground_dtm_chunk_sigma3_slope_deg'],float(g['solar_zenith_deg']),m);u=(g['stratum']==label)&app['supported']&g['valid'];factor[u]=app['factor'][u]
differences=[];inside=[]
for axis in [0,1]:
 a=np.take(factor,range(factor.shape[axis]-1),axis=axis);b=np.take(factor,range(1,factor.shape[axis]),axis=axis);c=np.take(g['stratum'],range(factor.shape[axis]-1),axis=axis);e=np.take(g['stratum'],range(1,factor.shape[axis]),axis=axis);ok=np.isfinite(a)&np.isfinite(b);differences.extend(abs(a-b)[ok&(c!=e)].tolist());inside.extend(abs(a-b)[ok&(c==e)].tolist())
(P/'class_boundary_control.json').write_text(json.dumps(dict(role='Proxy-specific model assignment diagnostic only; not applied to imagery',supported=int(np.isfinite(factor).sum()),valid=int(g['valid'].sum()),boundary_gain_difference_quantiles=np.quantile(differences,[.5,.95,.99,1]).tolist() if differences else [],within_class_gain_difference_quantiles=np.quantile(inside,[.5,.95,.99,1]).tolist() if inside else [],complete_spectra=len(rows)),indent=2)+'\n');print('Complete held-out spectra',len(rows))
