"""Bounded, matched three-site diagnosis; does not alter source products or gates."""
import sys,json,csv,hashlib
from pathlib import Path
import numpy as np,pandas as pd,rasterio
from scipy.ndimage import distance_transform_edt
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import least_squares,lsq_linear
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';sys.path.insert(0,str(PRIOR))
import correct_sites as old
from spectralbridge import corrections as c,topographic as topo
from spectralbridge.drone_view_geometry import camera_rays,footprint_candidates,NadirFootprint,aggregate_kernels
from spectralbridge.pipelines.drone import _compute_solar_geometry_arrays
HERE.joinpath('figures').mkdir(exist_ok=True)
def safe(v):return old.clean(v)
def write(name,v):(HERE/name).write_text(json.dumps(safe(v),indent=2,allow_nan=False)+'\n')
def quant(a):
 a=np.asarray(a);a=a[np.isfinite(a)];return np.quantile(a,[0,.01,.1,.5,.9,.99,1]).tolist() if len(a) else []
def fit(A,y,g,ref):
 beta,_,rank,s=np.linalg.lstsq(A,y,rcond=None);e=y-A@beta;cov,n=topo.cluster_covariance(A,e,g);pred,r,se,rs,ok=c._brdf_predictions(A,ref,beta,cov)
 return dict(beta=beta,rank=int(rank),condition=s[0]/s[-1],reference=r,reference_se=rs,reference_z=r/rs if rs else None,groups=n,rmse=np.sqrt(np.mean(e**2)),r2=1-np.sum(e**2)/np.sum((y-y.mean())**2),reference_outside_bounds=bool(np.any((ref<A.min(0))|(ref>A.max(0)))),valid=bool(ok.all()),residual=e,cov=cov,pred=pred,reference_kernel=ref)
def compact(r):return {k:safe(v) for k,v in r.items() if k not in ['residual','cov','pred']}
allfits=[];alltrace=[];summaries=[];sensitivities=[]
extremes=pd.read_csv(PRIOR/'bounded_extreme_source_records.csv')
configs=json.loads((PRIOR/'site_inputs.json').read_text())
for config in configs:
 name=config['site'];print(name,'loading bounded diagnostics',flush=True);folder=old.WORK/name.lower();cube,design,maps,profile=old.load_cube(config);shape=cube.data.shape[:2]
 mask=cube.mask_no_data;train=np.load(folder/'training_mask.npy');groups=np.load(folder/'spatial_groups.npy');ys,xs=np.indices(shape);sample=train&(ys%10==0)&(xs%10==0);ij=np.nonzero(sample);A=np.asarray(design[ij]);g=groups[ij];raw=np.asarray(cube.data[ij],float)*old.SCALE
 geom={k:cube.get_ancillary(k,radians=False) for k in ['solar_zn','solar_az','slope','aspect']};ci,ref_s,slope,valid=topo._geometry(cube);positions=pd.read_csv(config['camera_positions']);cameras=positions[['X','Y','Z']].to_numpy()
 with rasterio.open(config['terrain']) as src:dem=src.read(1)
 dzdy,dzdx=np.gradient(dem,.1,.1);slope_dem=np.rad2deg(np.arctan(np.hypot(dzdx,dzdy)));aspect_dem=np.rad2deg(np.arctan2(-dzdx,dzdy))%360
 distance=distance_transform_edt(mask)*.1
 summary=dict(site=name,shape=shape,source_covered=int(mask.sum()),sample_n=len(A),camera_z=quant(cameras[:,2]),camera_xy_bounds=[cameras[:,:2].min(0),cameras[:,:2].max(0)],solar_zenith=quant(geom['solar_zn'][mask]),solar_azimuth=quant(geom['solar_az'][mask]),central_view_zenith=quant(maps[...,1][mask]),central_relative_azimuth=quant(((maps[...,2]-geom['solar_az']+180)%360-180)[mask]),candidate_counts=quant(maps[...,0][mask]),kernel_volume=quant(A[:,1]),kernel_geometry=quant(A[:,2]),kernel_correlation=np.corrcoef(A[:,1:3].T)[0,1],dem_slope_difference=quant((slope_dem-geom['slope'])[sample]),dem_aspect_circular_difference=quant(((aspect_dem-geom['aspect']+180)%360-180)[sample]))
 topo_model=json.loads((PRIOR/f'{name.lower()}_conditioned_scsc_model.json').read_text());products={}
 for r in json.loads((PRIOR/f'{name.lower()}_pipeline_results.json').read_text()):
  if r['status']=='EXECUTED_EXPERIMENTAL':
   with rasterio.open(r['geotiff']) as src:products[r['branch']]=np.moveaxis(src.read(out_shape=(10,shape[0],shape[1])),0,-1)
 # Specific original extreme locations: all stages, geometry and algebraic composition.
 for _,r in extremes[extremes.site==name].iterrows():
  y,x,b=int(r.row),int(r.col),int(np.argmin(abs(cube.wavelengths-r.wavelength_nm)));rawv=float(cube.data[y,x,b]*old.SCALE);v={s:float(a[y,x,b]*old.SCALE) for s,a in products.items()};f=topo_model['fits'][b];C=f['C'];low,high=f['C_interval'];K=np.asarray(design[y,x]);record=dict(site=name,band_nm=int(r.wavelength_nm),kind=r.kind,baseline_stage=r.stage,row=y,col=x,raw=rawv,**v,topographic_factor=v.get('topographic_only',np.nan)/rawv if rawv else np.nan,brdf_only_factor=v.get('brdf_only',np.nan)/rawv if rawv else np.nan,combined_factor=v.get('combined',np.nan)/rawv if rawv else np.nan,combined_brdf_factor=v.get('combined',np.nan)/v.get('topographic_only',np.nan) if v.get('topographic_only',0) else np.nan,slope_deg=float(geom['slope'][y,x]),aspect_deg=float(geom['aspect'][y,x]),incidence=float(ci[y,x]),topo_reference=float(ref_s[y,x]),C=C,C_low=low,C_high=high,denominator=float(ci[y,x]+C),denominator_interval_low=float(ci[y,x]+low),distance_to_boundary_m=float(distance[y,x]),candidate_count=float(maps[y,x,0]),central_zenith=float(maps[y,x,1]),central_azimuth=float(maps[y,x,2]))
  for stage in ['brdf_only','combined']:
   model=json.loads((PRIOR/f'{name.lower()}_{stage}_brdf_model.json').read_text());br=model['validation']['fits'][b];beta=np.array(br['diagnostic_coefficient_estimate']);cov=np.array(br['coefficient_covariance']);pred,reference,se,rse,ok=c._brdf_predictions(K[None,:],np.array(model['reference_design']),beta,cov);record.update({stage+'_prediction':float(pred[0]),stage+'_prediction_se':float(se[0]),stage+'_reference_prediction':reference,stage+'_reference_se':rse,stage+'_resolved':bool(ok[0])})
  alltrace.append(record)
 # identical 1 m systematic samples, all bands and both stages, saved baseline reference.
 fig,axs=plt.subplots(2,3,figsize=(13,7),layout='constrained');fig.suptitle(name+': shared 1 m diagnostic sample (not new independent observations)')
 for stage_i,stage in enumerate(['brdf_only','combined']):
  model=json.loads((PRIOR/f'{name.lower()}_{stage}_brdf_model.json').read_text());ref=np.array(model['reference_design']);Y=raw if stage=='brdf_only' else np.asarray(products['topographic_only'][ij],float)*old.SCALE
  for b in range(10):
   good=np.isfinite(Y[:,b])&(Y[:,b]>=0)&(Y[:,b]<=2)&np.isfinite(A).all(1);a=A[good];y=Y[good,b];gg=g[good];f=fit(a,y,gg,ref);allfits.append(dict(site=name,stage=stage,band_nm=int(cube.wavelengths[b]),**compact(f)))
   if b==4:
    ax=axs[stage_i,0];sc=ax.scatter(a[:,1],a[:,2],c=y,s=1,cmap='viridis',rasterized=True);ax.scatter(ref[1],ref[2],marker='*',c='red',s=130,label='45 deg / nadir reference');ax.legend(fontsize=7);ax.set(xlabel='RossThick mixture',ylabel='LiDenseR mixture',title=stage+' | 650 nm');fig.colorbar(sc,ax=ax,label='conditional fraction')
    ax=axs[stage_i,1];ax.hexbin(f['pred'],y,gridsize=45,mincnt=1,bins='log');ax.set(xlabel='Fitted conditional fraction',ylabel='Observed conditional fraction',title=f"R2={f['r2']:.3f}; ref z={f['reference_z']:.2f}")
    residual=np.full(shape,np.nan);idx=(ij[0][good],ij[1][good]);residual[idx]=f['residual'];axs[stage_i,2].scatter(idx[1],idx[0],c=f['residual'],s=1,cmap='coolwarm',vmin=-.03,vmax=.03,rasterized=True);axs[stage_i,2].invert_yaxis();axs[stage_i,2].set(title='Spatial residuals (fixed +/-0.03)',xlabel='Column',ylabel='Row')
    # Prespecified diagnostics: equal cluster weight, spatial trend nuisance controls, robust loss,
    # nonnegative coefficients, ridge, and within-scene reference. None used as accepted new products.
    counts=np.unique(gg,return_counts=True);weights=1/np.sqrt(counts[1][np.searchsorted(counts[0],gg)]);aw=a*weights[:,None];yw=y*weights;beta=np.linalg.lstsq(aw,yw,rcond=None)[0];sensitivities.append(dict(site=name,stage=stage,method='equal_spatial_group_weight',reference=float(ref@beta),beta=beta.tolist()))
    for label,fun in [('soft_l1',lambda:least_squares(lambda b:a@b-y,f['beta'],loss='soft_l1',f_scale=.01).x),('nonnegative_all_coefficients_NOT_physical_requirement',lambda:lsq_linear(a,y,bounds=(0,np.inf)).x)]:
     beta=fun();sensitivities.append(dict(site=name,stage=stage,method=label,reference=float(ref@beta),beta=beta.tolist(),rmse=float(np.sqrt(np.mean((y-a@beta)**2)))))
    # center/scale nonconstant kernels before ridge. penalty is diagnostic only, not selected by pass status.
    mu=a[:,1:].mean(0);sd=a[:,1:].std(0);z=np.c_[np.ones(len(a)),(a[:,1:]-mu)/sd];zr=np.r_[1,(ref[1:]-mu)/sd]
    for lam in [.001,.01,.1]:
     beta=np.linalg.solve(z.T@z+np.diag([0,lam*len(a),lam*len(a)]),z.T@y);sensitivities.append(dict(site=name,stage=stage,method='standardized_ridge_'+str(lam),reference=float(zr@beta),rmse=float(np.sqrt(np.mean((y-z@beta)**2)))))
    # Surface-coordinate nuisance terms expose confounding without being a physical correction.
    spatial=np.c_[np.ones(len(a)),idx[0]/shape[0],idx[1]/shape[1]];aug=np.c_[a,spatial[:,1:]];coef=np.linalg.lstsq(aug,y,rcond=None)[0];sensitivities.append(dict(site=name,stage=stage,method='spatial_linear_nuisance',beta=coef.tolist(),reference_at_center=float(np.r_[ref,.5,.5]@coef),rmse=float(np.sqrt(np.mean((y-aug@coef)**2)))))
    refmean=a.mean(0);fm=fit(a,y,gg,refmean);sensitivities.append(dict(site=name,stage=stage,method='mean_kernel_reference_DIAGNOSTIC',**compact(fm)))
    # Spatially held-out errors across five fixed group folds; no method selected by acceptance.
    methods=['OLS','Huber','ridge_0.01','nonnegative_coefficients']
    for fold in range(5):
     tr=gg%5!=fold;te=~tr
     aa,tt=a[tr],y[tr];truth=y[te];test=a[te]
     for method in methods:
      if method=='OLS':bb=np.linalg.lstsq(aa,tt,rcond=None)[0];prediction=test@bb
      elif method=='Huber':
       bb=least_squares(lambda b:aa@b-tt,np.linalg.lstsq(aa,tt,rcond=None)[0],loss='huber',f_scale=.01).x;prediction=test@bb
      elif method=='nonnegative_coefficients':bb=lsq_linear(aa,tt,bounds=(0,np.inf)).x;prediction=test@bb
      else:
       mean=aa[:,1:].mean(0);std=aa[:,1:].std(0);z=np.c_[np.ones(len(aa)),(aa[:,1:]-mean)/std];bb=np.linalg.solve(z.T@z+np.diag([0,.01*len(aa),.01*len(aa)]),z.T@tt);prediction=np.c_[np.ones(len(test)),(test[:,1:]-mean)/std]@bb
      sensitivities.append(dict(site=name,stage=stage,method='spatial_holdout_'+method,fold=fold,test_n=int(te.sum()),test_rmse=float(np.sqrt(np.mean((truth-prediction)**2)))))
    # Scene heterogeneity and displacement controls retain the raw-defined populations.
    nir=raw[good,9];red=raw[good,5];ndvi=(nir-red)/(nir+red)
    for lo,hi in [(-1,.3),(.3,.6),(.6,1.01)]:
     use=(ndvi>=lo)&(ndvi<hi)
     if use.sum()>20 and len(np.unique(gg[use]))>3:
      ff=fit(a[use],y[use],gg[use],ref);sensitivities.append(dict(site=name,stage=stage,method=f'raw_NDVI_{lo}_{hi}',n=int(use.sum()),**compact(ff)))
    if stage=='brdf_only':
     for pixels in [0,250,500]:
      displaced=np.roll(cube.data[...,4],pixels,axis=1)[ij]*old.SCALE;use=np.isfinite(displaced)&np.isfinite(A).all(1)&(displaced>=0)&(displaced<=2)
      ff=fit(A[use],displaced[use],g[use],ref);sensitivities.append(dict(site=name,stage=stage,method=f'spatial_displacement_{pixels/10}_m',**compact(ff)))
    # Common positive scaling leaves predictions and uncertainty proportional; fixed thresholds can differ.
    fs=fit(a,y*.5,gg,ref);sensitivities.append(dict(site=name,stage=stage,method='response_scale_half_same_population',reference_ratio=fs['reference']/f['reference'],se_ratio=fs['reference_se']/f['reference_se'],same_acceptance=fs['valid']==f['valid'],factor_max_difference=float(np.max(abs(fs['reference']/fs['pred']-f['reference']/f['pred'])))))
 fig.savefig(HERE/'figures'/f'{name.lower()}_fit.png',dpi=150);plt.close(fig)
 # Factor maps and topographic mechanism, consistent red band.
 b=4;rawband=np.asarray(cube.data[...,b],float)*old.SCALE;top=products['topographic_only'][...,b]*old.SCALE;factor=np.divide(top,rawband,out=np.full(shape,np.nan),where=rawband!=0);both=products.get('combined');summary['red_topographic_factor']=quant(factor[mask]);summary['red_topographic_above5_count']=int(np.sum(mask&(factor>5)));summary['red_topographic_above5_incidence']=quant(ci[mask&(factor>5)]);summary['red_topographic_above5_slope']=quant(geom['slope'][mask&(factor>5)]);summary['red_topographic_above5_boundary_distance']=quant(distance[mask&(factor>5)])
 fig,ax=plt.subplots(2,3,figsize=(13,7),layout='constrained');fig.suptitle(name+': 650 nm correction mechanisms; plot limits do not clip data')
 fields=[(geom['slope'],'Slope (degrees)',0,60),(ci,'Cosine solar incidence',0,1),(factor,'Topographic multiplier',0,10),(maps[...,0],'Potential camera count',0,230),(maps[...,5],'RossThick mixture',None,None),(None if both is None else np.divide(both[...,b],products['topographic_only'][...,b],out=np.full(shape,np.nan),where=products['topographic_only'][...,b]!=0),'Combined BRDF multiplier',0,3)]
 for a,(field,title,lo,hi) in zip(ax.flat,fields):
  a.set_title(title);a.set_axis_off()
  if field is None:a.text(.5,.5,'UNSUPPORTED',ha='center',transform=a.transAxes);continue
  im=a.imshow(np.where(mask,field,np.nan)[::3,::3],vmin=lo,vmax=hi);fig.colorbar(im,ax=a,shrink=.75)
 fig.savefig(HERE/'figures'/f'{name.lower()}_mechanisms.png',dpi=150);plt.close(fig)
 # Source based sampled ray tests: altitude perturbation and timezone, unchanged kernel equations.
 take=np.arange(0,len(A),max(1,len(A)//2500));yy=ij[0][take];xx=ij[1][take];ground=np.c_[profile['transform'].c+(xx+.5)*profile['transform'].a,profile['transform'].f+(yy+.5)*profile['transform'].e,dem[yy,xx]]
 heading=positions.heading_grid_rad.to_numpy();footprint=NadirFootprint(**{k:config['intrinsics'][k] for k in ['width_px','height_px','focal_mm','pixel_um']});rotation=json.loads((PRIOR/f'{name.lower()}_geometry.json').read_text())['grid_to_true_north_rotation_deg']
 from datetime import datetime,timedelta
 solar_time=datetime.fromisoformat(config['solar_datetime'].replace('Z','+00:00'))
 for shift_m,shift_h in [(0,0),(-30,0),(30,0),(0,6),(0,7)]:
  cam=cameras.copy();cam[:,2]+=shift_m;zen,az,delta=camera_rays(ground,cam,grid_to_true_deg=rotation);good,central=footprint_candidates(delta,heading,footprint);ii,jj=np.nonzero(good)
  # Existing NOAA implementation at scalar center; preserve geolocation input ordering.
  from pyproj import Transformer
  trans=Transformer.from_crs(config['crs'],4326,always_xy=True);lon,lat=trans.transform(ground[:,0],ground[:,1]);when=solar_time+timedelta(hours=shift_h)
  sz,sa=_compute_solar_geometry_arrays(latitude=lat,longitude=lon,acquisition_datetime=when)
  if np.mean(sz)>=90:
   sensitivities.append(dict(site=name,stage="brdf_only",method=f"geometry_altitude_{shift_m}_clock_hours_{shift_h}",status="SUN_BELOW_HORIZON",solar_zenith_deg=float(np.mean(sz))));continue
  kv=np.full(good.shape,np.nan);kg=kv.copy();sun=np.deg2rad(sa);sunz=float(np.mean(np.deg2rad(sz)));kv[ii,jj]=c.calc_volume_kernel(sun[ii],sunz,az[ii,jj],zen[ii,jj],'RossThick');kg[ii,jj]=c.calc_geom_kernel(sun[ii],sunz,az[ii,jj],zen[ii,jj],'LiDenseR',b_r=10,h_b=2);D=aggregate_kernels(kv,kg,good,centrality=central);target=raw[take,4];valid=np.isfinite(D).all(1)&np.isfinite(target);ff=fit(D[valid],target[valid],g[take][valid],c._reference_design(c.ReferenceGeometry(),c.HYTOOLS_BRDF_KERNEL_CONFIG))
  sensitivities.append(dict(site=name,stage='brdf_only',method=f'geometry_altitude_{shift_m}_clock_hours_{shift_h}',solar_zenith_deg=float(np.rad2deg(sunz)),solar_azimuth_deg=float(np.mean(sa)),height_above_ground=quant(delta[...,2]),all_candidate_zenith_deg=quant(np.rad2deg(zen[good])),camera_ground_distance=quant(np.linalg.norm(delta,axis=-1)[good]),**compact(ff)))
  if shift_m==0 and shift_h==0:summary['sampled_ray_distance']=quant(np.linalg.norm(delta,axis=-1)[good]);summary['sampled_agl']=quant(delta[...,2]);summary['all_candidate_zenith_deg']=quant(np.rad2deg(zen[good]))
 summaries.append(summary);write('geometry_and_factor_summary.json',summaries);write('sampled_model_fits.json',allfits);write('sensitivity_experiments.json',sensitivities);pd.DataFrame(alltrace).to_csv(HERE/'traced_extreme_pixels.csv',index=False)
 print(name,'diagnosis saved',flush=True)
write('diagnosis_complete.json',dict(sites=3,sample_grid='every 10th source row/column, training mask preserved',analytical_clipping=False))
