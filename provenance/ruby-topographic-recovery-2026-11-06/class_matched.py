"""Train-only original-photo topo fits and matched target-amplitude BRDF controls."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from affine import Affine
from scipy.ndimage import map_coordinates
from spectralbridge.drone_topography import solar_incidence,fit_topographic_model,topographic_factors
from spectralbridge.drone_original import fit_target_amplitudes,reference_design,reference_in_hull
HERE=Path(__file__).resolve().parent;R=HERE.parents[1];P=HERE/'class_specific';P.mkdir(exist_ok=True);OUT=R/'archive/local/ruby-topographic-recovery-2026-11-06';g=np.load(OUT/'common_grid.npz');df=pd.read_csv(R/'provenance/ruby-correction-recovery-2026-11-06/observations_enriched.csv');tr=Affine(*g['transform'][:6]);cc,rr=(~tr)*(df.x.to_numpy(),df.y.to_numpy());coords=[rr-.5,cc-.5];rng=np.random.default_rng(1850);reference=reference_design()
def sample(a,order=1):return map_coordinates(a.astype(float),coords,order=order,mode='constant',cval=np.nan)
for name in ['viewing_absolute_shadow','viewing_absolute_covered','texture_cv','stratum','groups','fold']:
 df['new_'+name]=sample(g[name],order=0)
records=[];scores=[];spectra=[]
for sigma in [0,3]:
 key='ground_dtm_chunk_sigma'+str(sigma);slope=sample(g[key+'_slope_deg']);a=np.deg2rad(g[key+'_aspect_deg']);aspect=np.rad2deg(np.arctan2(sample(np.sin(a)),sample(np.cos(a))))%360;df['new_slope']=slope;df['new_ci']=solar_incidence(slope,aspect,df.solar_zenith_deg.to_numpy(),df.solar_azimuth_deg.to_numpy())
 for population in ['canopy_proxy','herbaceous_proxy','exposed_proxy']:
  mask=df.quality_supported.to_numpy(copy=True);mask &= (df.new_stratum=={'canopy_proxy':1,'herbaceous_proxy':2,'exposed_proxy':3}[population]).to_numpy();sun=(df.new_viewing_absolute_shadow==0)&(df.new_viewing_absolute_covered==1)
  if population!='existing':mask &= sun.to_numpy()&~df.possible_shadow_or_dark.to_numpy()
  if population=='homogeneous_sunlit':mask &= (df.patch_cv<=.25).to_numpy()
  for nm,band in df[mask].groupby('wavelength_nm'):
   counts=band.groupby('target_id').size();b=band[band.target_id.isin(counts[counts>=3].index)].copy()
   if len(b)<8:continue
   X=np.c_[np.ones(len(b)),b.ross,b.li];y=b.observed_fraction.to_numpy();targets=b.target_id.to_numpy()
   for method in ['scsc','c_correction','minnaert']:
    for fold in range(4):
     train=b.new_fold.to_numpy()!=fold;test=~train
     if test.sum()<3:continue
     means=b[train].groupby('target_id').agg(ci=('new_ci','mean'),rho=('observed_fraction','mean'),slope=('new_slope','mean'),group=('new_groups','first'));eligible=(means.slope>=5)&(means.ci>0);means=means[eligible]
     m=fit_topographic_model(means.ci.to_numpy(),means.rho.to_numpy(),means.group.to_numpy(),method=method);record=dict(sigma=sigma,population=population,wavelength_nm=float(nm),method=method,fold=fold,train_targets=len(means),test_observations=int(test.sum()),topographic_model=m,status='UNSUPPORTED_TOPO')
     app=topographic_factors(b.new_ci.to_numpy(),b.new_slope.to_numpy(),b.solar_zenith_deg.to_numpy(),m);top=y*app['factor'];supported=app['supported'];trainok=train&supported;testok=test&supported
     counts=b[trainok].groupby('target_id').size();trainok &= b.target_id.isin(counts[counts>=3].index).to_numpy()
     if trainok.sum()<8 or testok.sum()<3:records.append(record);continue
     try:
      f=fit_target_amplitudes(X[trainok],top[trainok],targets[trainok]);pred=X@f['beta'];ref=float(reference@f['beta']);boots=[];ts=np.unique(targets[trainok])
      for _ in range(40):
       inds=np.concatenate([np.flatnonzero(trainok&(targets==t)) for t in rng.choice(ts,len(ts),replace=True)])
       try:boots.append(fit_target_amplitudes(X[inds],top[inds],targets[inds])['beta'])
       except (ValueError,np.linalg.LinAlgError):pass
      if len(boots)<30:raise ValueError('Insufficient successful BRDF target bootstrap replicates')
      boots=np.array(boots);predlo=np.quantile(X@boots.T,.025,axis=1);reflo=float(np.quantile(boots@reference,.025));refsupport=reference_in_hull(X[trainok],reference);brdfok=(pred>0)&(predlo>0)&(ref>0)&(reflo>0)&refsupport
      # Raw BRDF-only comparison independently fitted in the raw space.
      rawfit=fit_target_amplitudes(X[train],y[train],targets[train]);rawpred=X@rawfit['beta'];rawref=float(reference@rawfit['beta']);brdfonly=np.where((rawpred>0)&(rawref>0),y*rawref/rawpred,np.nan)
      joint=top*np.where(brdfok,ref/pred,np.nan);factorboots=(boots@reference)[None,:]/(X@boots.T);blo,bhi=np.quantile(factorboots,[.025,.975],axis=1);lower=y*app['low']*blo;upper=y*app['high']*bhi
      record.update(status='CONDITIONAL_MATCHED_CANDIDATE' if (testok&brdfok).any() else 'UNSUPPORTED_BRDF',topo_supported_test=int(testok.sum()),combined_supported_test=int((testok&brdfok).sum()),brdf_reference_joint_support=refsupport,brdf_beta=f['beta'].tolist(),brdf_reference_lower=reflo,combined_interval='Conservative endpoint product envelope; not independent physical truth')
      for t in np.unique(targets[test]):
       u=testok&brdfok&(targets==t)
       if u.sum()<2:continue
       cv=lambda a:float(np.std(a)/abs(np.mean(a))) if np.mean(a)!=0 else None;rawcv=cv(y[u]);row=dict(sigma=sigma,population=population,wavelength_nm=float(nm),method=method,fold=fold,target_id=t,n=int(u.sum()),raw_cv=rawcv,topo_cv=cv(top[u]),brdf_cv=cv(brdfonly[u]),combined_cv=cv(joint[u]),combined_variance_ratio=(cv(joint[u])/rawcv)**2 if rawcv else None,topographic_variance_ratio=(cv(top[u])/rawcv)**2 if rawcv else None,interval_relative_width=float(np.nanmedian((upper[u]-lower[u])/abs(joint[u]))));scores.append(row)
       for index in np.flatnonzero(u):spectra.append(dict(sigma=sigma,population=population,method=method,target_id=t,master_key=int(b.iloc[index].master_key),wavelength_nm=float(nm),raw=float(y[index]),topographic=float(top[index]),brdf=float(brdfonly[index]),combined=float(joint[index])))
     except (ValueError,np.linalg.LinAlgError) as exc:record.update(status='UNSUPPORTED_BRDF',reason=str(exc))
     records.append(record)
  print('Matched',sigma,population,'fits',len(records),flush=True)
(P/'matched_models.json').write_text(json.dumps(records,indent=2)+'\n');pd.DataFrame(scores).to_csv(P/'matched_holdouts.csv',index=False);pd.DataFrame(spectra).to_csv(P/'matched_spectral_stages.csv',index=False)
