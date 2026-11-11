"""Actual-geometry identifiability controls and explicit P184 guard audit."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from scipy.ndimage import gaussian_filter
from spectralbridge.drone_topography import fit_topographic_model,topographic_factors,solar_incidence
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';g=np.load(OUT/'common_grid.npz');b=json.loads((P/'baseline.json').read_text());sz=b['solar_zenith_deg'];sa=b['solar_azimuth_deg'];ci=g['ground_dtm_chunk_sigma0_incidence'];slope=g['ground_dtm_chunk_sigma0_slope_deg'];valid=g['valid']&(ci>0)&(slope>=5);groups=g['groups'];rng=np.random.default_rng(185);rows=[]
scenarios=['homogeneous_positive_C','known_negative_C','ecological_gradient_0.5','ecological_gradient_1.0','spatial_heterogeneity','shadow_contamination','incidence_error','radiometric_noise','narrow_illumination','sparse_sample','forward_SCSC_flat_surface']
for scenario in scenarios:
 for rep in range(60):
  x=ci.copy();C=-.1 if scenario=='known_negative_C' else .2;a=np.full(ci.shape,.08);u=(ci-np.nanmean(ci[valid]))/np.nanstd(ci[valid]);noise=gaussian_filter(rng.normal(size=ci.shape),4);noise/=np.std(noise[valid]);use=valid.copy()
  if scenario.startswith('ecological_gradient'):a*=np.exp(float(scenario.rsplit('_',1)[1])*u)
  if scenario=='spatial_heterogeneity':a*=np.exp(.6*noise)
  y=a*(ci+C)
  if scenario=='forward_SCSC_flat_surface':y=.08*(ci+C)/(np.cos(np.deg2rad(sz))*np.cos(np.deg2rad(slope))+C)
  if scenario=='shadow_contamination':y=np.where(g['viewing_absolute_shadow'],y*.2,y)
  if scenario=='incidence_error':x=ci+.05*noise
  y*=np.exp(rng.normal(0,.05 if scenario=='radiometric_noise' else .01,size=ci.shape))
  if scenario=='narrow_illumination':use &= abs(ci-np.median(ci[valid]))<.025
  if scenario=='sparse_sample':use &= np.indices(ci.shape)[0]%4==0;use &= np.indices(ci.shape)[1]%4==0
  m=fit_topographic_model(x[use],y[use],groups[use]);record=dict(scenario=scenario,replicate=rep,true_C=C,n=int(use.sum()),status=m['status'],C=m.get('C'),C_interval=m.get('C_interval'))
  if m.get('C_interval'):lo,hi=m['C_interval'];record['interval_covers_true_C']=lo<=C<=hi
  app=topographic_factors(x,slope,sz,m);record['supported_fraction']=float((app['supported']&valid).sum()/valid.sum());rows.append(record)
 print('Synthetic',scenario,flush=True)
pd.DataFrame(rows).to_csv(P/'synthetic_recovery.csv',index=False)
# Independent vector-dot formula audit on actual terrain.
s=np.deg2rad(slope);az=np.deg2rad(g['ground_dtm_chunk_sigma0_aspect_deg']);sun=np.array([np.sin(np.deg2rad(sz))*np.sin(np.deg2rad(sa)),np.sin(np.deg2rad(sz))*np.cos(np.deg2rad(sa)),np.cos(np.deg2rad(sz))]);normal=np.stack([np.sin(s)*np.sin(az),np.sin(s)*np.cos(az),np.cos(s)],axis=-1);dot=normal@sun
# Reproduce exactly the prior fitting population before new field/policy controls.
y=g['raw'][4];use=valid&np.isfinite(y)&(y>=0)&(y<=2);prior=fit_topographic_model(ci[use],y[use],groups[use]);expected=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/dense_terrain_control.json').read_text());expected=next(v for v in expected['records'] if v['surface']=='ground_dtm_chunk' and v['stratum']=='all' and v['wavelength_nm']==650)
# Quantify the previous experiment's negative-branch ambiguity without editing its files.
df=pd.read_csv(R/'provenance/ruby-correction-recovery-2026-11-06/observations_enriched.csv');models=json.loads((R/'provenance/ruby-correction-recovery-2026-11-06/topographic_models.json').read_text());ambiguity=[]
for model in models:
 if model.get('C_interval') is None:continue
 sample=df[(df.wavelength_nm==model['wavelength_nm'])&df.quality_supported];lo,hi=model['C_interval'];x=sample[model['surface']+'_incidence'].to_numpy();ref=sample[model['surface']+'_reference'].to_numpy();C=model['C'];gain=(ref+C)/(x+C);old=(x>0)&((x+lo)*(x+hi)>0)&(np.minimum(abs(x+lo),abs(x+hi))>.001)&(gain>0);strict=(x+lo>.001)&(ref+lo>0);ambiguity.append(dict(wavelength_nm=model['wavelength_nm'],surface=model['surface'],stratum=model['stratum'],old_negative_branch_passes=int((old&~strict).sum())))
(P/'numerical_audit.json').write_text(json.dumps(dict(max_incidence_dot_error=float(np.nanmax(abs(dot-ci))),red_C=prior.get('C'),red_C_interval=prior.get('C_interval'),P184_red_C=expected['C'],C_difference=prior.get('C')-expected['C'],P184_unsupported=expected['unsupported_application'],negative_branch_audit=ambiguity,production_change=False),indent=2)+'\n')
