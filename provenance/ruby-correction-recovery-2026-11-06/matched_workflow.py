"""Cross-fitted matched SCS+C then original-photo Ross/Li candidates.

No full corrected images are emitted unless all numerical and scientific gates
are established. Held-out targets remain conditional on this shared flight.
"""
import json
from pathlib import Path
import numpy as np,pandas as pd
from spectralbridge.drone_original import fit_target_amplitudes,fit_target_effects,reference_design,reference_in_hull,temporal_minute_groups
from spectralbridge.topographic import cluster_covariance,fieller_interval,SCSCPolicy
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--data-root',type=Path,default=Path(__file__).resolve().parent);args=parser.parse_args();P=args.data_root;df=pd.read_csv(P/'observations_enriched.csv');ref=reference_design();policy=SCSCPolicy();outputs=[];fits=[];boot=[];rng=np.random.default_rng(184)

def topo_fit(b):
 a=b.groupby('target_id').agg(ci=('ground_dtm_chunk_incidence','mean'),value=('observed_fraction','mean'),slope=('ground_dtm_chunk_slope_deg','mean'),group=('spatial_group','first'))
 a=a[(a.slope>=policy.minimum_slope_degrees)&(a.ci>0)&(a.value>=policy.rho_min)&(a.value<=policy.rho_max)].dropna()
 if len(a)<5:raise ValueError('Insufficient independent ground-terrain targets')
 X=np.c_[a.ci,np.ones(len(a))];y=a.value.to_numpy();beta=np.linalg.lstsq(X,y,rcond=None)[0];cov,ng=cluster_covariance(X,y-X@beta,a.group);interval=fieller_interval(*beta,cov,policy.confidence_z)
 if interval is None or ng<policy.minimum_clusters:raise ValueError('Unbounded C or insufficient spatial groups')
 return dict(C=float(beta[1]/beta[0]),C_interval=interval,incidence_range=[float(a.ci.min()),float(a.ci.max())],groups=ng)

def topo_apply(b,fit):
 ci=b.ground_dtm_chunk_incidence.to_numpy();nr=b.ground_dtm_chunk_reference.to_numpy();lo,hi=fit['C_interval'];C=fit['C'];factor=(nr+C)/(ci+C)
 valid=np.isfinite(factor)&(factor>0)&(ci>0)&((ci+lo)*(ci+hi)>0)&(np.minimum(abs(ci+lo),abs(ci+hi))>policy.min_denominator)&(ci>=fit['incidence_range'][0])&(ci<=fit['incidence_range'][1])
 return b.observed_fraction.to_numpy()*np.where(valid,factor,np.nan),factor,valid

for nm,band in df.groupby('wavelength_nm'):
 b=band[band.quality_supported].copy();counts=b.groupby('target_id').size();b=b[b.target_id.isin(counts[counts>=3].index)].copy();X=np.c_[np.ones(len(b)),b.ross,b.li];y=b.observed_fraction.to_numpy();targets=b.target_id.to_numpy()
 # Parameter uncertainty from spatial blocks and time blocks; each is conditional on one shared calibration.
 for clustering in ['spatial_group','time_minute']:
  labels=b.spatial_group.to_numpy() if clustering=='spatial_group' else temporal_minute_groups(b.timestamp_utc_scenario)
  unique=np.unique(labels);betas=[]
  for _ in range(60):
   indices=np.concatenate([np.flatnonzero(labels==v) for v in rng.choice(unique,len(unique),replace=True)])
   try:betas.append(fit_target_amplitudes(X[indices],y[indices],targets[indices])['beta'])
   except (ValueError,np.linalg.LinAlgError):pass
  if len(betas)>=30:
   betas=np.array(betas);p=X@betas.T;r=betas@ref;low=np.quantile(p,.025,axis=1);rlo=float(np.quantile(r,.025));boot.append(dict(wavelength_nm=float(nm),groups=len(unique),clustering=clustering,successful_replicates=len(betas),coefficient_interval=np.quantile(betas,[.025,.975],axis=0).tolist(),reference_interval=np.quantile(r,[.025,.975]).tolist(),nonpositive_lower_application=int((low<=0).sum()),reference_joint_support=reference_in_hull(X,ref),normalization_supported=bool((low>0).all() and rlo>0 and reference_in_hull(X,ref)),status='CONDITIONAL_SINGLE_FLIGHT_BOOTSTRAP'))
 for fold in range(4):
  train=b.holdout_fold.to_numpy()!=fold;test=~train;tr=b.loc[train].copy();te=b.loc[test].copy();rec=dict(wavelength_nm=float(nm),fold=fold,train_targets=tr.target_id.nunique(),test_targets=te.target_id.nunique(),status='UNSUPPORTED')
  try:
   tf=topo_fit(tr);yt,_,tvalid=topo_apply(tr,tf);yv,_,vvalid=topo_apply(te,tf);tr['topo']=yt;counts=tr[tvalid].groupby('target_id').size();validtrain=tvalid&tr.target_id.isin(counts[counts>=3].index).to_numpy();validtest=vvalid
   if validtrain.sum()<8 or validtest.sum()<4:raise ValueError('Insufficient supported matched-stage observations')
   fit=fit_target_amplitudes(X[train][validtrain],yt[validtrain],tr.target_id.to_numpy()[validtrain]);shape=X[test]@fit['beta'];reference=float(ref@fit['beta']);local=(shape>0)&(reference>0);ref_support=reference_in_hull(X[train][validtrain],ref);combined=yv*np.where(local,reference/shape,np.nan)
   rec.update(status='NUMERICAL_CANDIDATE_ONLY',topographic=tf,brdf_beta=fit['beta'].tolist(),reference_joint_support=ref_support,unsupported_topographic_test=int((~vvalid).sum()),unsupported_brdf_test=int((~local).sum()))
   for t in te.target_id.unique():
    u=(te.target_id.to_numpy()==t)&validtest&local
    if u.sum()<2:continue
    raw=te.observed_fraction.to_numpy()[u];top=yv[u];final=combined[u];cv=lambda v:float(np.std(v)/abs(np.mean(v))) if np.mean(v)!=0 else None
    outputs.append(dict(wavelength_nm=float(nm),fold=fold,target_id=t,n=int(u.sum()),raw_cv=cv(raw),topographic_cv=cv(top),combined_cv=cv(final),raw_sd=float(np.std(raw)),topographic_sd=float(np.std(top)),combined_sd=float(np.std(final)),reference_joint_support=ref_support,stage='MATCHED_TRAIN_ONLY_TOPO_THEN_BRDF;CONDITIONAL_VALIDATION',scientific_approval=False))
  except (ValueError,np.linalg.LinAlgError) as exc:rec['reason']=str(exc)
  fits.append(rec)
pd.DataFrame(outputs).to_csv(P/'combined_heldout_validation.csv',index=False)
(P/'matched_models.json').write_text(json.dumps(fits,indent=2)+'\n');(P/'bootstrap_uncertainty.json').write_text(json.dumps(boot,indent=2)+'\n')
# This is a research-stage manifest: independent accuracy, full-frame support and
# licensed mosaicking are not inferred from local coefficient or bootstrap passes.
status=dict(schema_version=1,status='UNSUPPORTED_FOR_FULL_CORRECTED_ORTHOMOSAIC',radiometric_encoding='VERIFIED_VENDOR_PROJECT_ENCODING;INDEPENDENT_ACCURACY_PENDING',both_corrections_required=True,source_images_exported=False,orthomosaic_regenerated=False,blockers=['Independent reflectance/ground registration not established','Full-frame original-photo terrain/shadow/BRDF support not validated','Shared calibration/flight dependence remains in held-out evidence','Licensed Metashape build/export unavailable'],numerical_summary='See matched_models.json, bootstrap_uncertainty.json and combined_heldout_validation.csv')
(P/'correction_status.json').write_text(json.dumps(status,indent=2)+'\n');print('Matched evaluation complete; full output gate remains unsupported',flush=True)
