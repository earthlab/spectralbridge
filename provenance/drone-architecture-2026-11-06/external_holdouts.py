"""Matched spatial holdouts for the cheap-terrain sensitivity; no shadow approval."""
from pathlib import Path
import numpy as np,pandas as pd,json
from spectralbridge.drone_topography import fit_topographic_model,topographic_factors
P=Path(__file__).resolve().parent;R=P.parents[1]
g=np.load(R/'archive/local/ruby-topographic-recovery-2026-11-06/common_grid.npz');e=np.load(P/'external_dem_comparison_maps.npz');b=json.loads((R/'provenance/ruby-topographic-recovery-2026-11-06/baseline.json').read_text())
variants=[('USGS_3DEP_requested_10m',e['usgs_slope'],e['usgs_incidence']),('Metashape_DTM_native',g['ground_dtm_chunk_sigma0_slope_deg'],g['ground_dtm_chunk_sigma0_incidence']),('Metashape_DTM_sigma3m',g['ground_dtm_chunk_sigma3_slope_deg'],g['ground_dtm_chunk_sigma3_incidence'])]
valid=g['valid']&~g['spectral_dark']&~g['field_buffer']
for _,s,x in variants:valid &= np.isfinite(s+x)&(s>=5)&(x>0)
fold=(g['x']>np.median(g['x'][valid])).astype(int)+2*(g['y']>np.median(g['y'][valid])).astype(int)
rows=[]
for name,s,x in variants:
 for i,nm in enumerate([444,475,531,560,650,668,705,717,740,842]):
  for f in range(4):
   train=valid&(fold!=f);test=valid&(fold==f);m=fit_topographic_model(x[train],g['raw'][i][train],g['groups'][train]);app=topographic_factors(x,s,b['solar_zenith_deg'],m);use=test&app['supported'];raw=g['raw'][i][use];out=raw*app['factor'][use]
   rows.append(dict(source=name,wavelength_nm=nm,fold=f,train_n=int(train.sum()),test_n=int(test.sum()),supported_n=int(use.sum()),C=m.get('C'),status=m['status'],raw_cv=float(np.std(raw)/np.mean(raw)) if len(raw)>1 else None,corrected_cv=float(np.std(out)/np.mean(out)) if len(raw)>1 else None))
d=pd.DataFrame(rows);d['cv2_ratio']=(d.corrected_cv/d.raw_cv)**2;d.to_csv(P/'external_dem_spatial_holdouts.csv',index=False)
print(d.groupby('source')[['cv2_ratio','supported_n','test_n']].mean().to_string())
