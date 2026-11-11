"""Repeated-feature Ross/Li feasibility, unchanged reference and prediction guards."""
import json
from pathlib import Path
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from spectralbridge import corrections as c
from spectralbridge.topographic import cluster_covariance
HERE=Path(__file__).resolve().parent;data=pd.read_csv(HERE/'tie_observations.csv');ref=c._reference_design(c.ReferenceGeometry(),c.HYTOOLS_BRDF_KERNEL_CONFIG);rows=[];points=[]
for (site,target,nm),group in data.groupby(['site','target_id','wavelength_nm']):
 for selection in ['all_tracked','reprojection_le_1px','reprojection_le_0.5px']:
  df=group if selection=='all_tracked' else group[group.master_track_reprojection_error_px<=(1 if selection.endswith('1px') else .5)]
  if len(df)<4:rows.append(dict(site=site,target_id=target,wavelength_nm=nm,selection=selection,n=len(df),status='UNSUPPORTED',reason='Fewer than four registered observations'));continue
  args=[np.deg2rad(df[name].to_numpy()) for name in ['solar_azimuth_deg','solar_zenith_deg','view_azimuth_deg','view_zenith_deg']];kv=c.calc_volume_kernel(*args,'RossThick');kg=c.calc_geom_kernel(*args,'LiDenseR',b_r=10,h_b=2);X=np.c_[np.ones(len(df)),kv,kg];y=df.vendor_fraction_median.to_numpy();beta,_,rank,s=np.linalg.lstsq(X,y,rcond=None);condition=s[0]/s[-1] if s[-1]>0 else float('inf');record=dict(site=site,target_id=target,wavelength_nm=nm,selection=selection,n=len(df),rank=int(rank),condition=float(condition),view_zenith_range=[df.view_zenith_deg.min(),df.view_zenith_deg.max()],relative_azimuth_range=[float(((df.view_azimuth_deg-df.solar_azimuth_deg)%360).min()),float(((df.view_azimuth_deg-df.solar_azimuth_deg)%360).max())],volume_range=[float(kv.min()),float(kv.max())],geometry_range=[float(kg.min()),float(kg.max())],reference_outside_bounds=bool(np.any((ref<X.min(0))|(ref>X.max(0)))),beta=beta.tolist(),reference_design=ref.tolist(),registration_max_px=df.master_track_reprojection_error_px.max(),radiometry='Vendor project calibration; independent accuracy pending',status='UNSUPPORTED')
  if rank!=3 or condition>1/np.sqrt(np.finfo(np.float32).eps):record['reason']='Rank/conditioning fails unchanged precision guard';rows.append(record);continue
  residual=y-X@beta;cov,n=cluster_covariance(X,residual,df.master_key.to_numpy());pred,r,se,rse,ok=c._brdf_predictions(X,ref,beta,cov);record.update(reference=float(r),reference_se=float(rse),reference_z=float(r/rse) if rse else None,unresolved=int((~ok).sum()),status='NUMERICALLY_SUPPORTED' if ok.all() else 'INVALID',uncertainty='Individual exposure clusters; shared calibration/time errors not independent',rmse=float(np.sqrt(np.mean(residual**2))))
  # Additional temporal grouping is a sensitivity, not replaced by an easier estimator.
  minutes=pd.to_datetime(df.timestamp_utc_scenario).astype('int64').to_numpy()//60_000_000_000
  try:
   tc,ng=cluster_covariance(X,residual,minutes);pp,rr,ss,rss,resolved=c._brdf_predictions(X,ref,beta,tc);record.update(temporal_minute_groups=int(ng),temporal_reference_se=float(rss),temporal_prediction_status='NUMERICALLY_SUPPORTED' if resolved.all() else 'INVALID')
  except ValueError:record.update(temporal_minute_groups=int(len(np.unique(minutes))),temporal_prediction_status='INSUFFICIENT_INDEPENDENT_TIME_GROUPS')
  loo=[]
  if len(y)>4:
   for i in range(len(y)):
    use=np.arange(len(y))!=i;b=np.linalg.lstsq(X[use],y[use],rcond=None)[0];loo.append(float(X[i]@b-y[i]))
  record['leave_one_exposure_out_rmse']=float(np.sqrt(np.mean(np.array(loo)**2))) if loo else None;rows.append(record)
  if selection=='all_tracked':
   for i,(_,obs) in enumerate(df.iterrows()):points.append(dict(site=site,target_id=target,wavelength_nm=nm,view_zenith_deg=obs.view_zenith_deg,volume=float(kv[i]),geometry=float(kg[i]),value=float(y[i]),fitted=float(pred[i]),photo=obs.photo_path,registration_error_px=obs.master_track_reprojection_error_px))
(HERE/'repeated_target_fits.json').write_text(json.dumps(rows,indent=2)+'\n');pd.DataFrame(points).to_csv(HERE/'repeated_target_kernel_observations.csv',index=False)
fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for col,site in enumerate(['Ruby','Goldhill']):
 p=pd.DataFrame([r for r in points if r['site']==site and r['wavelength_nm']==650])
 for target,group in p.groupby('target_id'):
  axs[0,col].plot(group.view_zenith_deg,group.value,'o',ms=3,alpha=.75,label=target);axs[1,col].scatter(group.volume,group.geometry,s=12,alpha=.7)
 axs[0,col].set(title=site+': same tracked feature, repeated red signal',xlabel='View zenith (deg)',ylabel='Vendor-calibrated fraction (accuracy unverified)');axs[1,col].scatter(ref[1],ref[2],marker='*',s=150,color='red',label='45 deg / nadir reference');axs[1,col].set(xlabel='RossThick',ylabel='LiDenseR');axs[1,col].legend()
fig.suptitle('Original images add angular diversity; registration and uncertainty remain explicit');fig.savefig(HERE/'figures/repeated_targets.png',dpi=160);plt.close(fig)
# Genuine repeated spectra: each curve is one observed exposure at the same tracked target.
full=data[data.site=='Ruby'];targets=[t for t,g in full.groupby('target_id') if g.wavelength_nm.nunique()==10];fig,axs=plt.subplots(1,max(1,len(targets)),figsize=(12,4),squeeze=False,layout='constrained')
for ax,target in zip(axs.flat,targets):
 for master,g in full[full.target_id==target].groupby('master_key'):
  g=g.sort_values('wavelength_nm');ax.plot(g.wavelength_nm,g.vendor_fraction_median,alpha=.7,lw=1)
 ax.set(title=target+' | same registered track',xlabel='Source wavelength (nm)',ylabel='Vendor-calibrated fraction')
fig.suptitle('Repeated spectra use the source 842 nm NIR label; prior input metadata said 862 nm');fig.savefig(HERE/'figures/repeated_spectra.png',dpi=160);plt.close(fig)
print(pd.DataFrame(rows).groupby(['site','selection','status']).size().to_string(),flush=True)
