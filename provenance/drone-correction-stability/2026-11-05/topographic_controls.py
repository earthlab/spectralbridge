"""Cross-site terrain/radiometric controls on the frozen 1 m training sample."""
import sys,json
from pathlib import Path
import numpy as np,pandas as pd,rasterio
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';sys.path.insert(0,str(PRIOR))
import correct_sites as old
from spectralbridge import corrections as c,topographic as topo
rows=[];poses=[]
for cfg in json.loads((PRIOR/'site_inputs.json').read_text()):
 cube,design,maps,profile=old.load_cube(cfg);folder=old.WORK/cfg['site'].lower();train=np.load(folder/'training_mask.npy');g=np.load(folder/'spatial_groups.npy');rr,cc=np.indices(train.shape);choose=train&(rr%10==0)&(cc%10==0);ij=np.nonzero(choose);raw=np.asarray(cube.data[ij],float)*old.SCALE;ci,reference,slope,valid=topo._geometry(cube);x=ci[ij];groups=g[ij];ndvi=(raw[:,9]-raw[:,5])/(raw[:,9]+raw[:,5])
 with rasterio.open(cfg['terrain']) as src:dem=src.read(1)
 dy,dx=np.gradient(dem,.1,.1);sl=np.arctan(np.hypot(dx,dy));asp=np.arctan2(-dx,dy)%(2*np.pi);sunz=cube.get_ancillary('solar_zn',radians=True);suna=cube.get_ancillary('solar_az',radians=True);newci=c.calc_cosine_i(sunz,suna,asp,sl)[ij]
 for b in range(10):
  y=raw[:,b]
  for label,xx,yy,sub in [('baseline',x,y,np.ones(len(x),bool)),('response_scale_half',x,y*.5,np.ones(len(x),bool)),('response_offset_plus_0.005_HYPOTHETICAL',x,y+.005,np.ones(len(x),bool)),('independent_DEM_gradient_DIAGNOSTIC',newci,y,np.ones(len(x),bool)),('NDVI_below_0.3',x,y,ndvi<.3),('NDVI_0.3_0.6',x,y,(ndvi>=.3)&(ndvi<.6)),('NDVI_above_0.6',x,y,ndvi>=.6)]:
   good=sub&np.isfinite(xx)&np.isfinite(yy)&(xx>0)&(slope[ij]>=np.deg2rad(5));a=np.c_[xx[good],np.ones(good.sum())];beta=np.linalg.lstsq(a,yy[good],rcond=None)[0];e=yy[good]-a@beta;cov,n=topo.cluster_covariance(a,e,groups[good]);interval=topo.fieller_interval(*beta,cov,1.96)
   rows.append(dict(site=cfg['site'],band_nm=cube.wavelengths[b],control=label,n=int(good.sum()),C=float(beta[1]/beta[0]),slope=float(beta[0]),intercept=float(beta[1]),C_interval=interval,clusters=n,rmse=float(np.sqrt(np.mean(e**2)))))
 p=pd.read_csv(cfg['camera_positions']);R=p[[f'r{i}{j}' for i in range(1,4) for j in range(1,4)]].to_numpy().reshape(-1,3,3)
 poses.append(dict(site=cfg['site'],positions=len(p),max_orthogonal_error=float(abs(R@R.transpose(0,2,1)-np.eye(3)).max()),determinant_quantiles=np.quantile(np.linalg.det(R),[0,.5,1]).tolist(),third_column_z=np.quantile(R[:,2,2],[0,.5,1]).tolist(),orientation_status='Valid rotation matrices; camera/world direction and image-axis binding not independently verified'))
 print(cfg['site'],'topographic controls complete',flush=True)
pd.DataFrame(rows).to_csv(HERE/'topographic_controls.csv',index=False);(HERE/'rotation_contract.json').write_text(json.dumps(poses,indent=2)+'\n')
