"""Unselected camera/world and footprint-axis alternatives; no invented pose binding."""
import sys,json
from pathlib import Path
import numpy as np,pandas as pd,rasterio
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';sys.path.insert(0,str(PRIOR))
import correct_sites as old
from spectralbridge.drone_view_geometry import NadirFootprint,camera_rays,footprint_candidates,aggregate_kernels
from spectralbridge import corrections as c,topographic as topo
rows=[]
for cfg in json.loads((PRIOR/'site_inputs.json').read_text()):
 folder=old.WORK/cfg['site'].lower();train=np.load(folder/'training_mask.npy');rr,cc=np.nonzero(train);take=np.arange(0,len(rr),max(1,len(rr)//2500));rr,cc=rr[take],cc[take];groups=np.load(folder/'spatial_groups.npy')[rr,cc]
 with rasterio.open(cfg['prepared']) as src:transform=src.transform;y=src.read(5)[rr,cc]*old.SCALE
 with rasterio.open(cfg['terrain']) as src:dem=src.read(1)[rr,cc]
 ground=np.c_[transform.c+(cc+.5)*transform.a,transform.f+(rr+.5)*transform.e,dem];p=pd.read_csv(cfg['camera_positions']);cam=p[['X','Y','Z']].to_numpy();R=p[[f'r{i}{j}' for i in range(1,4) for j in range(1,4)]].to_numpy().reshape(-1,3,3);foot=NadirFootprint(**{k:cfg['intrinsics'][k] for k in ['width_px','height_px','focal_mm','pixel_um']});rotation=json.loads((PRIOR/f"{cfg['site'].lower()}_geometry.json").read_text())['grid_to_true_north_rotation_deg'];zen,az,delta=camera_rays(ground,cam,grid_to_true_deg=rotation);solar=np.load(cfg['solar_arrays'],mmap_mode='r');sun=np.deg2rad(solar[rr,cc,1]);sunz=float(np.mean(np.deg2rad(solar[rr,cc,0])));reference=c._reference_design(c.ReferenceGeometry(),c.HYTOOLS_BRDF_KERNEL_CONFIG)
 for method in ['heading_baseline','heading_plus90','R_camera_to_world_negativeZ','R_world_to_camera_negativeZ']:
  if method.startswith('heading'):
   good,central=footprint_candidates(delta,p.heading_grid_rad.to_numpy()+(np.pi/2 if method.endswith('plus90') else 0),foot)
  else:
   local=np.einsum('nci,cij->ncj',-delta,R if 'camera_to_world' in method else R.transpose(0,2,1));height=-local[...,2]
   with np.errstate(divide='ignore',invalid='ignore'):central=np.maximum(abs(local[...,0])/(height*foot.half_tangents[0]),abs(local[...,1])/(height*foot.half_tangents[1]))
   good=np.isfinite(central)&(height>0)&(central<=1);central=np.where(good,central,np.inf)
  ii,jj=np.nonzero(good);kv=np.full(good.shape,np.nan);kg=kv.copy();kv[ii,jj]=c.calc_volume_kernel(sun[ii],sunz,az[ii,jj],zen[ii,jj],'RossThick');kg[ii,jj]=c.calc_geom_kernel(sun[ii],sunz,az[ii,jj],zen[ii,jj],'LiDenseR',b_r=10,h_b=2);D=aggregate_kernels(kv,kg,good,centrality=central);use=np.isfinite(D).all(1)&np.isfinite(y);A=D[use];target=y[use];beta,_,rank,s=np.linalg.lstsq(A,target,rcond=None);e=target-A@beta;cov,n=topo.cluster_covariance(A,e,groups[use]);pred,ref,se,rse,resolved=c._brdf_predictions(A,reference,beta,cov)
  rows.append(dict(site=cfg['site'],method=method,status='UNSELECTED_GEOMETRY_SENSITIVITY',n=int(use.sum()),rank=int(rank),condition=float(s[0]/s[-1]),reference=ref,reference_se=rse,reference_z=ref/rse,valid=bool(resolved.all()),candidate_count_quantiles=np.quantile(good.sum(1),[0,.5,1]).tolist(),median_optical_axis_tilt_deg=float(np.rad2deg(np.arccos(np.clip(R[:,2,2],-1,1))).mean())))
 print(cfg['site'],'pose alternatives evaluated without selecting a convention',flush=True)
(HERE/'pose_sensitivity.json').write_text(json.dumps(rows,indent=2)+'\n')
