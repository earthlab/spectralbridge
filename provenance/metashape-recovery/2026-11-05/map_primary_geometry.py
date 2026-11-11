"""Official retained-source API at 1 m; primary assignment is not a blend weight."""
import json
from pathlib import Path
import numpy as np,rasterio,Metashape
from affine import Affine
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=ROOT/'archive/local/metashape-recovery/2026-11-05/sources';WORK=ROOT/'archive/local/metashape-recovery/2026-11-05/geometry';WORK.mkdir(exist_ok=True);FIG=HERE/'figures';FIG.mkdir(exist_ok=True);results=[]
for site,variant in [('Ruby','WORKING'),('Goldhill','WORKING'),('Goldhill','NOGCPS-WORKING')]:
 tag=site.lower()+'_'+variant.lower().replace('-','_')
 cfg=next(r for r in json.loads((ROOT/'provenance/drone-camera-rerun/2026-11-05/site_inputs.json').read_text()) if r['site']==site);path=next(p for p in (SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('*.psx') if ('NOGCPS' in p.name)==variant.startswith('NOGCPS'));doc=Metashape.Document();doc.open(str(path),read_only=True,ignore_lock=True);chunk=doc.chunks[0];T=chunk.transform.matrix
 with rasterio.open(cfg['prepared']) as src:
  shape=(src.height//10,src.width//10);transform=src.transform*Affine.scale(10,10);mask=src.dataset_mask()[5:shape[0]*10:10,5:shape[1]*10:10]>0;profile=src.profile.copy()
 with rasterio.open(path.with_suffix('.files')/'0/0/elevation/tile-0-0.tif') as dem:
  rows,cols=np.nonzero(mask);xx,yy=rasterio.transform.xy(transform,rows,cols);z=np.array([r[0] for r in dem.sample(zip(xx,yy))]);ground=np.c_[xx,yy,z]
 cameras={};positions={}
 for camera in chunk.cameras:
  if camera.transform is not None and camera.photo and float(dict(camera.photo.meta).get('Pix4D/CentralWavelength','nan'))==650:
   master=camera.master if camera.master else camera;cameras[master.key]=camera;positions[camera.key]=T.mulp(camera.center)
 maps=np.full((*shape,6),np.nan,np.float32);seen={};valid=0
 for k,(row,col,p) in enumerate(zip(rows,cols,ground)):
  primary=chunk.orthomosaic.camera(Metashape.Vector(p[:2]));camera=cameras.get(primary.key) if primary else None
  if camera is None:continue
  ecef=chunk.crs.unproject(Metashape.Vector(p));internal=T.inv().mulp(ecef);uv=camera.project(internal)
  if uv is None:continue
  delta=positions[camera.key]-ecef;local=chunk.crs.localframe(ecef).mulv(delta);zen=np.rad2deg(np.arctan2(np.hypot(local.x,local.y),local.z));az=np.rad2deg(np.arctan2(local.x,local.y))%360;inside=0<=uv.x<camera.sensor.width and 0<=uv.y<camera.sensor.height;maps[row,col]=[primary.key,camera.key,zen,az,float(inside),p[2]];valid+=1;seen[primary.key]=seen.get(primary.key,0)+1
  if k%20000==0:print(site,'primary geometry',k,'/',len(rows),flush=True)
 out=WORK/(tag+'_primary_geometry_1m.tif');profile.update(height=shape[0],width=shape[1],transform=transform,count=6,dtype='float32',nodata=np.nan,compress='deflate');profile.pop('photometric',None)
 with rasterio.open(out,'w',**profile) as dst:
  dst.write(np.moveaxis(maps,2,0));dst.update_tags(STATUS='EXPERIMENTAL_READ_ONLY_METASHAPE_PRIMARY_ASSIGNMENT',BLEND_WEIGHTS='NOT_RECOVERED',SURFACE='Stored DEM id0; active canopy-height surface explicitly not used')
 fig,axs=plt.subplots(1,3,figsize=(13,4),layout='constrained')
 for ax,a,title,cmap in zip(axs,[maps[...,0],maps[...,2],maps[...,3]],['Retained primary exposure key','650 nm actual primary view zenith','650 nm actual primary azimuth'],['tab20','magma','twilight']):
  im=ax.imshow(a,cmap=cmap);fig.colorbar(im,ax=ax,shrink=.7);ax.set_title(title);ax.set_axis_off()
 fig.suptitle(site+': official camera assignment + estimated calibrated pose; no recovered blend weights');fig.savefig(FIG/(tag+'_primary_geometry.png'),dpi=160);plt.close(fig)
 rec=dict(site=site,variant=variant,project_path=str(path),output=str(out),valid=valid,requested=int(mask.sum()),source_exposures=len(seen),view_zenith_quantiles=np.nanquantile(maps[...,2],[0,.01,.5,.99,1]).tolist(),view_azimuth_quantiles=np.nanquantile(maps[...,3],[0,.01,.5,.99,1]).tolist(),projected_inside_image=int(np.nansum(maps[...,4])),method='Official orthomosaic.camera at 1m crop centers; calibrated band-specific projection and true ENU angles; primary assignment does not recover blend weights');results.append(rec);(HERE/'primary_geometry_summary.json').write_text(json.dumps(results,indent=2)+'\n');print(site,'complete',valid,flush=True)
