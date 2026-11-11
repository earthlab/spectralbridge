"""Same-footprint 650 nm model with retained primary geometry (blend weights unknown)."""
import json
from pathlib import Path
import numpy as np,pandas as pd,rasterio
from spectralbridge import corrections as c
from spectralbridge.topographic import cluster_covariance
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PRIOR=ROOT/'provenance/drone-camera-rerun/2026-11-05';ref=c._reference_design(c.ReferenceGeometry(),c.HYTOOLS_BRDF_KERNEL_CONFIG);results=[]
for site in ['Ruby','Goldhill']:
 cfg=next(r for r in json.loads((PRIOR/'site_inputs.json').read_text()) if r['site']==site);path=ROOT/'archive/local/metashape-recovery/2026-11-05/geometry'/(site.lower()+'_working_primary_geometry_1m.tif')
 with rasterio.open(path) as maps:
  a=np.moveaxis(maps.read(),0,-1);shape=maps.shape;tr=maps.transform;rr,cc=np.indices(shape);x,y=rasterio.transform.xy(tr,rr.ravel(),cc.ravel());xy=list(zip(x,y))
 with rasterio.open(cfg['prepared']) as src:signal=np.array([v[0] for v in src.sample(xy,indexes=5)]).reshape(shape)*65535/(10000*32768)
 mask=np.load(ROOT/'archive/local/drone-camera-rerun/2026-11-05/photo_clock_v1'/site.lower()/'training_mask.npy');sample=mask[5:shape[0]*10:10,5:shape[1]*10:10];good=sample&np.isfinite(a).all(-1)&(a[...,4]>0)&np.isfinite(signal)&(signal>=0)&(signal<=2);g=(rr//20)*((shape[1]+19)//20)+cc//20
 solar=np.load(cfg['solar_arrays'],mmap_mode='r');sz=solar[5:shape[0]*10:10,5:shape[1]*10:10,0];sa=solar[5:shape[0]*10:10,5:shape[1]*10:10,1];v=np.deg2rad(a[...,2][good]);az=np.deg2rad(a[...,3][good]);sun=np.deg2rad(sa[good]);sunz=float(np.mean(np.deg2rad(sz[good])));kv=c.calc_volume_kernel(sun,sunz,az,v,'RossThick');kg=c.calc_geom_kernel(sun,sunz,az,v,'LiDenseR',b_r=10,h_b=2);X=np.c_[np.ones(len(kv)),kv,kg];y=signal[good];b,_,rank,s=np.linalg.lstsq(X,y,rcond=None);cond=float(s[0]/s[-1]);rec=dict(site=site,n=len(y),rank=int(rank),condition=cond,status='UNSUPPORTED',model='Raw 650nm, observed primary camera only; effective blended geometry not recovered',reference_design=ref.tolist(),volume_range=[float(kv.min()),float(kv.max())],geometry_range=[float(kg.min()),float(kg.max())],reference_outside_bounds=bool(np.any((ref<X.min(0))|(ref>X.max(0)))))
 if rank==3 and cond<=1/np.sqrt(np.finfo(np.float32).eps):
  residual=y-X@b;cov,ng=cluster_covariance(X,residual,g[good]);p,r,se,rse,res=c._brdf_predictions(X,ref,b,cov);rec.update(status='NUMERICALLY_SUPPORTED' if res.all() else 'INVALID',beta=b.tolist(),reference=r,reference_se=rse,reference_z=r/rse,unsupported_predictions=int((~res).sum()),spatial_groups=ng,rmse=float(np.sqrt(np.mean(residual**2))))
 else:rec['reason']='Unchanged rank/conditioning guard'
 results.append(rec);print(site,rec,flush=True)
(HERE/'primary_mosaic_fits.json').write_text(json.dumps(results,indent=2)+'\n')
