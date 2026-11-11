"""Common-grid dense mosaic SCS+C surface control; not original-photo coefficients."""
from pathlib import Path
import json
import numpy as np,pandas as pd,rasterio
from affine import Affine
from scipy.ndimage import map_coordinates
from spectralbridge.topographic import cluster_covariance,fieller_interval,SCSCPolicy
from spectralbridge.corrections import calc_cosine_i
P=Path(__file__).resolve().parent;R=P.parents[1];OUT=R/'archive/local/ruby-correction-recovery-2026-11-06';policy=SCSCPolicy();base=json.loads((P/'baseline.json').read_text());old=base['baseline_site'];solar=np.load(old['solar_arrays']);print('solar',solar.shape,flush=True)
with rasterio.open(OUT/'ruby_vendor_fraction_x10000_10cm_v1.tif') as ds:
 # Identical center sample for every candidate; 1m support is not a spatial average.
 data=ds.read()[:,::10,::10].astype(float)*.0001;rr,cc=np.indices(data.shape[1:]);xx,yy=ds.transform*(cc*10+.5,rr*10+.5)
if solar.ndim==1:sz,sa=solar[:2]
else:sz,sa=solar[0].mean(),solar[1].mean()
# Use recovered original-photo midpoint geometry, explicitly rather than guessing array layout.
sz=old.get('solar_zenith_deg',26.0);sa=old.get('solar_azimuth_deg')
# Source existing P183 observations carry per-photo physical solar definitions.
pdobs=pd.read_csv(R/'provenance/metashape-recovery/2026-11-05/tie_observations.csv');pdobs=pdobs[pdobs.site=='Ruby'];sz=float(pdobs.solar_zenith_deg.median());sa=float(pdobs.solar_azimuth_deg.median())
groups=(rr//20)*100+(cc//20);ndvi=(data[9]-data[5])/(data[9]+data[5]);records=[];maps={}
for surface in ['viewing_absolute','ground_dtm_chunk']:
 z=np.load(OUT/(surface+'_terrain.npz'));tr=Affine(*z['transform'][:6]);col,row=(~tr)*(xx,yy);coords=[row-.5,col-.5];slope=map_coordinates(z['slope_deg'],coords,order=1,mode='constant',cval=np.nan);a=np.deg2rad(z['aspect_deg']);ss=map_coordinates(np.sin(a),coords,order=1,mode='constant',cval=np.nan);co=map_coordinates(np.cos(a),coords,order=1,mode='constant',cval=np.nan);aspect=np.arctan2(ss,co);ci=calc_cosine_i(np.full(slope.shape,np.deg2rad(sz)),np.full(slope.shape,np.deg2rad(sa)),aspect,np.deg2rad(slope));nr=np.cos(np.deg2rad(sz))*np.cos(np.deg2rad(slope));maps[surface+'_incidence']=ci;maps[surface+'_slope']=slope
 for band,nm in enumerate([444,475,531,560,650,668,705,717,740,842]):
  for label,selection in [('all',np.ones(slope.shape,bool)),('high_NDVI',ndvi>.5),('low_NDVI',ndvi<=.5)]:
   valid=selection&np.isfinite(data[band])&np.isfinite(ci)&(ci>0)&(slope>=policy.minimum_slope_degrees)&(data[band]>=policy.rho_min)&(data[band]<=policy.rho_max);X=np.c_[ci[valid],np.ones(valid.sum())];y=data[band][valid];rec=dict(surface=surface,wavelength_nm=nm,stratum=label,n=len(y),status='UNSUPPORTED',processing_space='Raw calibrated orthomosaic; dense terrain diagnostic only')
   if len(y)>4:
    beta=np.linalg.lstsq(X,y,rcond=None)[0]
    try:
     cov,ng=cluster_covariance(X,y-X@beta,groups[valid]);interval=fieller_interval(*beta,cov,policy.confidence_z);C=float(beta[1]/beta[0]);rec.update(C=C,C_interval=interval,groups=ng)
     if interval is not None:
      low,high=interval;gain=(nr+C)/(ci+C);pole=(ci+low)*(ci+high)<=0;good=np.isfinite(ci)&np.isfinite(data[band]);bad=good&((ci<=0)|pole|(np.minimum(abs(ci+low),abs(ci+high))<=policy.min_denominator)|~np.isfinite(gain)|(gain<=0));rec.update(unsupported_application=int(bad.sum()),application_pixels=int(good.sum()),gain_quantiles=np.quantile(gain[good&np.isfinite(gain)],[0,.01,.5,.99,1]).tolist(),status='NUMERICALLY_SUPPORTED' if not bad.any() else 'UNSUPPORTED_APPLICATION')
      if nm==650 and label=='all':maps[surface+'_red_gain']=np.where(good,gain,np.nan);maps[surface+'_unsupported']=bad
    except (ValueError,np.linalg.LinAlgError) as exc:rec['reason']=str(exc)
   records.append(rec)
(P/'dense_terrain_control.json').write_text(json.dumps(dict(solar_zenith_deg=sz,solar_azimuth_deg=sa,records=records),indent=2)+'\n');np.savez_compressed(OUT/'dense_terrain_control.npz',**maps);print('Dense control complete',flush=True)
