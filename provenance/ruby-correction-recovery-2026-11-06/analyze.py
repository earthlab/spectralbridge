"""Matched original-photo terrain/BRDF candidate evaluation, without production promotion."""
import json
from pathlib import Path
import numpy as np,pandas as pd
from affine import Affine
from scipy.ndimage import map_coordinates
from spectralbridge.drone_original import ross_li_design,reference_design,reference_in_hull,fit_target_effects,fit_target_amplitudes,temporal_minute_groups
from spectralbridge.topographic import cluster_covariance,fieller_interval,SCSCPolicy
from spectralbridge.corrections import calc_cosine_i
import argparse
SCRIPT=Path(__file__).resolve().parent;R=SCRIPT.parents[1];parser=argparse.ArgumentParser();parser.add_argument('--data-root',type=Path,default=SCRIPT);parser.add_argument('--input-file',type=Path);parser.add_argument('--response',choices=['center','median'],default='center');parser.add_argument('--homogeneous-only',action='store_true');args=parser.parse_args();P=args.data_root;P.mkdir(parents=True,exist_ok=True);OUT=R/'archive/local/ruby-correction-recovery-2026-11-06';df=pd.read_csv(args.input_file or P/'expanded_observations.csv');df['observed_fraction']=df['vendor_fraction_'+args.response];policy=SCSCPolicy();ref=reference_design()
for name in ['viewing_absolute','ground_dtm_chunk']:
 z=np.load(OUT/(name+'_terrain.npz'));tr=Affine(*z['transform'][:6]);cols,rows=(~tr)*(df.x.to_numpy(),df.y.to_numpy());coords=[rows-.5,cols-.5]
 for key in ['elevation','slope_deg','aspect_deg']:df[name+'_'+key]=map_coordinates(z[key],coords,order=1,mode='constant',cval=np.nan)
# Aspect is sampled as a vector across the north wrap rather than as 359->0 scalar.
 for key in ['aspect_deg']:
  radians=np.deg2rad(z[key]);ss=map_coordinates(np.sin(radians),coords,order=1,mode='constant',cval=np.nan);cc=map_coordinates(np.cos(radians),coords,order=1,mode='constant',cval=np.nan);df[name+'_'+key]=np.rad2deg(np.arctan2(ss,cc))%360
 slope=np.deg2rad(df[name+'_slope_deg']);aspect=np.deg2rad(df[name+'_aspect_deg']);sz=np.deg2rad(df.solar_zenith_deg);sa=np.deg2rad(df.solar_azimuth_deg);df[name+'_incidence']=calc_cosine_i(sz.to_numpy().reshape(-1,1),sa.to_numpy().reshape(-1,1),aspect.to_numpy().reshape(-1,1),slope.to_numpy().reshape(-1,1)).ravel();df[name+'_reference']=np.cos(sz)*np.cos(slope)
df['relative_azimuth_deg']=(df.view_azimuth_deg-df.solar_azimuth_deg)%360
df['patch_cv']=df.vendor_fraction_std/df.vendor_fraction_median.abs();df['quality_supported']=(df.master_track_reprojection_error_px<=1)&(df.raw_DN_at_uint16_max_fraction==0)&(df.raw_DN_at_or_below_black_fraction<.05)&(df.observed_fraction>0)&np.isfinite(df.observed_fraction)
df['possible_shadow_or_dark']=df.vendor_fraction_median<.01;df['heterogeneous_patch']=df.patch_cv>.25
df['spatial_group']=(df.cell//8//2)*4+(df.cell%8//2);df['holdout_fold']=(df.cell//8//4)*2+(df.cell%8//4)
pivot=df.groupby(['target_id','wavelength_nm']).vendor_fraction_median.median().unstack();ndvi=(pivot[842]-pivot[668])/(pivot[842]+pivot[668]);df['ndvi_proxy']=df.target_id.map(ndvi);df['spectral_stratum']=np.where(df.ndvi_proxy>.5,'high_NDVI_proxy','low_NDVI_proxy');df['height_above_ground']=df.z-df.ground_dtm_chunk_elevation;df['height_stratum']=np.where(df.height_above_ground>2,'elevated_feature','near_ground_feature')
if args.homogeneous_only:df['quality_supported'] &= ~df.heterogeneous_patch
Xall=ross_li_design(df.solar_azimuth_deg,df.solar_zenith_deg,df.view_azimuth_deg,df.view_zenith_deg);df['ross']=Xall[:,1];df['li']=Xall[:,2]
results=[];validation=[];topo=[];details=[]
for nm,band in df.groupby('wavelength_nm'):
 b=band[band.quality_supported].copy();counts=b.groupby('target_id').size();b=b[b.target_id.isin(counts[counts>=3].index)].copy();X=np.c_[np.ones(len(b)),b.ross,b.li];y=b.observed_fraction.to_numpy();targets=b.target_id.to_numpy()
 base=dict(wavelength_nm=float(nm),observations=len(b),targets=b.target_id.nunique(),reference_joint_support=reference_in_hull(X,ref),view_range=[float(b.view_zenith_deg.min()),float(b.view_zenith_deg.max())],solar_range=[float(b.solar_zenith_deg.min()),float(b.solar_zenith_deg.max())])
 for model in ['additive_target_effects','multiplicative_target_amplitudes']:
  rec=dict(**base,model=model,status='EXPERIMENTAL_NOT_APPROVED')
  try:
   fit=fit_target_effects(X,y,targets,uncertainty_groups=b.spatial_group) if model.startswith('additive') else fit_target_amplitudes(X,y,targets)
   rec.update(condition=fit['condition'],residual_rmse=float(np.sqrt(np.mean(fit['residual']**2))),coefficients=fit['angular_beta'].tolist() if model.startswith('additive') else fit['beta'].tolist())
   if model.startswith('additive'):rec['spatial_covariance']=fit['covariance'].tolist()
   else:
    shape=X@fit['beta'];reference=float(ref@fit['beta']);rec.update(reference_shape=reference,nonpositive_application_predictions=int((shape<=0).sum()),factor_quantiles=np.quantile(reference/shape,[0,.01,.5,.99,1]).tolist())
   for fold in range(4):
    train=b.holdout_fold.to_numpy()!=fold;test=~train
    if test.sum()<4:continue
    try:
     f=fit_target_effects(X[train],y[train],targets[train],uncertainty_groups=b.spatial_group.to_numpy()[train]) if model.startswith('additive') else fit_target_amplitudes(X[train],y[train],targets[train]);v=y[test].copy();xt=X[test];tt=targets[test]
     if model.startswith('additive'):corrected=v+(ref[1:]-xt[:,1:])@f['angular_beta'];support=np.ones(len(v),bool)
     else:
      shape=xt@f['beta'];reference=float(ref@f['beta']);support=(shape>0)&(reference>0);corrected=np.where(support,v*reference/shape,np.nan)
     for t in np.unique(tt):
      use=tt==t
      if use.sum()<2:continue
      before=float(np.std(v[use]));after=float(np.std(corrected[use]));validation.append(dict(wavelength_nm=float(nm),model=model,fold=fold,target_id=t,n=int(use.sum()),before_sd=before,after_sd=after,variance_ratio=(after/before)**2 if before>0 else None,reference_supported=reference_in_hull(X[train],ref),heldout_kernel_support_fraction=float(np.mean([reference_in_hull(X[train],r) for r in xt[use]])),interpretation='Held-out spatial targets; shared photo/calibration/time dependence remains'))
    except (ValueError,np.linalg.LinAlgError) as exc:rec.setdefault('holdout_failures',[]).append(str(exc))
  except (ValueError,np.linalg.LinAlgError) as exc:rec['reason']=str(exc)
  results.append(rec)
 # SCS+C fitted across target means, never treating repeated images as independent terrain samples.
 for surface in ['viewing_absolute','ground_dtm_chunk']:
  for stratum in ['all','high_NDVI_proxy','low_NDVI_proxy']:
   subset=b if stratum=='all' else b[b.spectral_stratum==stratum];a=subset.groupby('target_id').agg(value=('observed_fraction','mean'),incidence=(surface+'_incidence','mean'),reference=(surface+'_reference','mean'),slope=(surface+'_slope_deg','mean'),group=('spatial_group','first'))
   a=a[(a.slope>=policy.minimum_slope_degrees)&(a.incidence>0)&(a.value>=policy.rho_min)&(a.value<=policy.rho_max)].dropna();rec=dict(wavelength_nm=float(nm),surface=surface,stratum=stratum,targets=len(a),status='UNSUPPORTED',C=None,C_interval=None)
   if len(a)>4:
    xx=np.c_[a.incidence,np.ones(len(a))];yy=a.value.to_numpy();beta,_,rank,sv=np.linalg.lstsq(xx,yy,rcond=None);rec.update(slope=float(beta[0]),intercept=float(beta[1]),condition=float(sv[0]/sv[-1]))
    try:
     cov,ng=cluster_covariance(xx,yy-xx@beta,a.group);interval=fieller_interval(*beta,cov,policy.confidence_z);rec.update(C=float(beta[1]/beta[0]),C_interval=interval,spatial_groups=ng)
     if interval is not None:
      ci=b[surface+'_incidence'].to_numpy();nr=b[surface+'_reference'].to_numpy();C=rec['C'];factors=(nr+C)/(ci+C);low,high=interval;den=np.minimum(abs(ci+low),abs(ci+high));pole=(ci+low)*(ci+high)<=0;valid=(ci>0)&~pole&(den>policy.min_denominator)&np.isfinite(factors)&(factors>0);rec.update(unsupported_application=int((~valid).sum()),factor_quantiles=np.quantile(factors[np.isfinite(factors)],[0,.01,.5,.99,1]).tolist(),status='NUMERICALLY_SUPPORTED' if valid.all() and ng>=policy.minimum_clusters else 'UNSUPPORTED_APPLICATION')
      # Matched topo stage persisted; only numerically admissible observations are finite.
      for j,(_,r) in enumerate(b.iterrows()):details.append(dict(target_id=r.target_id,master_key=int(r.master_key),wavelength_nm=float(nm),surface=surface,stratum=stratum,raw=float(r.observed_fraction),topographic=float(r.observed_fraction*factors[j]) if valid[j] else None,factor=float(factors[j]),numerically_supported=bool(valid[j]),fit_status=rec['status']))
    except (ValueError,np.linalg.LinAlgError) as exc:rec['reason']=str(exc)
   topo.append(rec)
 # Does illumination have independent within-target information alongside directional kernels?
 inc=b.ground_dtm_chunk_incidence.to_numpy();within=[]
 for t in np.unique(targets):
  u=targets==t;Z=np.c_[X[u,1:],inc[u]];within.append(Z-Z.mean(0))
 Z=np.concatenate(within);s=np.linalg.svd(Z,compute_uv=False);results.append(dict(**base,model='joint_within_target_illumination_design',rank=int(np.linalg.matrix_rank(Z)),condition=float(s[0]/s[-1]),within_incidence_sd=float(np.std(Z[:,2])),status='DIAGNOSTIC_ONLY_TARGET_INTERCEPTS_DO_NOT_IDENTIFY_SCSC_C'))
df.to_csv(P/'observations_enriched.csv',index=False);pd.DataFrame(validation).to_csv(P/'heldout_validation.csv',index=False);pd.DataFrame(details).to_csv(P/'topographic_stages.csv',index=False)
for name,value in [('brdf_models',results),('topographic_models',topo)]: (P/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
summary=dict(response=args.response,homogeneous_only=args.homogeneous_only,observations=len(df),unique_photos=df.photo_path.nunique(),targets=df.target_id.nunique(),quality_observations=int(df.quality_supported.sum()),heterogeneous_patches=int(df.heterogeneous_patch.sum()),possible_dark_observations=int(df.possible_shadow_or_dark.sum()),temporal_minutes=int(len(np.unique(temporal_minute_groups(df.timestamp_utc_scenario)))),correction_status='EXPERIMENTAL_EVALUATION_PENDING;NO_ORTHOMOSAIC_APPROVAL',surface_classes='NDVI/height proxies only; no independent forest/grass/soil truth')
(P/'analysis_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary,flush=True)
