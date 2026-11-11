"""Independent field-label context and per-polygon red correction diagnostics."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from spectralbridge.drone_topography import topographic_factors
P=Path(__file__).resolve().parent;R=P.parents[1];g=np.load(R/'archive/local/ruby-topographic-recovery-2026-11-06/common_grid.npz');models=json.loads((P/'models.json').read_text());fields=json.loads((P/'field_polygon_context.json').read_text());rows=[]
for sigma in [0,3]:
 for pop in ['existing','combined_screened','homogeneous_sunlit','canopy_proxy','herbaceous_proxy','exposed_proxy']:
  for method in ['scsc','c_correction','minnaert']:
   m=next(v for v in models if v['surface']=='ground_dtm_chunk' and v['sigma']==sigma and v['population']==pop and v['method']==method and v['strategy']=='ols' and v['wavelength_nm']==650);key='ground_dtm_chunk_sigma'+str(sigma);domain=g['valid']&(g['viewing_absolute_covered'])&~g['viewing_absolute_shadow']
   if pop!='existing':domain &= ~g['spectral_dark']
   if pop=='homogeneous_sunlit':domain &= g['texture_cv']<=.25
   if pop in ['canopy_proxy','herbaceous_proxy','exposed_proxy']:domain &= g['stratum']=={'canopy_proxy':1,'herbaceous_proxy':2,'exposed_proxy':3}[pop]
   app=topographic_factors(g[key+'_incidence'],g[key+'_slope_deg'],float(g['solar_zenith_deg']),m,geometric_sunlit=domain)
   for f in fields:
    u=(g['field_polygon']==f['polygon_id'])&app['supported']&domain
    if not u.any():continue
    a=g['raw'][4][u];corrected=a*app['factor'][u];rows.append(dict(sigma=sigma,population=pop,method=method,polygon_id=f['polygon_id'],species=f['species'],cover_category=f['cover_category'],n=int(u.sum()),raw_median=float(np.median(a)),corrected_median=float(np.median(corrected)),incidence=float(np.median(g[key+'_incidence'][u])),note='All field polygons and a 2m buffer excluded from fitting; labels do not establish equal physical reflectance'))
d=pd.DataFrame(rows);d.to_csv(P/'field_holdout_predictions.csv',index=False);summaries=[]
for key,a in d.groupby(['sigma','population','method','cover_category','species']):
 if len(a)<4:continue
 cv=lambda s:float(np.std(s)/abs(np.mean(s))) if np.mean(s)!=0 else None;summaries.append(dict(sigma=key[0],population=key[1],method=key[2],cover_category=key[3],species=key[4],polygons=len(a),raw_cv=cv(a.raw_median),corrected_cv=cv(a.corrected_median),raw_incidence_correlation=float(np.corrcoef(a.raw_median,a.incidence)[0,1]),corrected_incidence_correlation=float(np.corrcoef(a.corrected_median,a.incidence)[0,1])))
pd.DataFrame(summaries).to_csv(P/'field_holdout_summary.csv',index=False);print('Field polygon diagnostic records',len(d))
