"""Official calibrated red-plane footprints on the stored DEM, no guessed frusta."""
import json
from pathlib import Path
import numpy as np,Metashape
from pyproj import Transformer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from geometry import photo_ray
HERE=Path(__file__).resolve().parent;SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources');features=[];summary=[]
for site,variant in [('Ruby','WORKING'),('Goldhill','WORKING'),('Goldhill','NOGCPS')]:
 p=next(p for p in (SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('*.psx') if ('NOGCPS' in p.name)==(variant=='NOGCPS'));d=Metashape.Document();d.open(str(p),read_only=True,ignore_lock=True);c=d.chunks[0];dem=c.elevations[0];cameras=[cam for cam in c.cameras if cam.transform is not None and cam.photo and float(dict(cam.photo.meta).get('Pix4D/CentralWavelength','nan'))==650];centers=[];tilts=[];completed=0
 to_lonlat=Transformer.from_crs(c.crs.wkt,4326,always_xy=True)
 fig,ax=plt.subplots(figsize=(7,6),layout='constrained')
 for j,cam in enumerate(cameras):
  corners=[];cal=cam.calibration;center_ec=c.transform.matrix.mulp(cam.center);center=c.crs.project(center_ec);centers.append(list(center));axis=cal.project(Metashape.Vector([0,0,1]));origin,ray=photo_ray(c,cam,axis);local=c.crs.localframe(center_ec).mulv(Metashape.Vector(ray.tolist()));tilts.append(float(np.rad2deg(np.arccos(np.clip(-local.z,-1,1)))))
  for pixel in [[0,0],[cam.sensor.width-1,0],[cam.sensor.width-1,cam.sensor.height-1],[0,cam.sensor.height-1]]:
   uv=Metashape.Vector(pixel);back=cal.project(cal.unproject(uv))
   if back is None or (back-uv).norm()>1:break
   o,v=photo_ray(c,cam,uv);a=Metashape.OrthoProjection.transform(Metashape.Vector(o.tolist()),c.crs.geoccs,dem.projection);b=Metashape.OrthoProjection.transform(Metashape.Vector((o+v*500).tolist()),c.crs.geoccs,dem.projection);hit=dem.pickPoint(a,b)
   if hit is None:break
   corners.append(list(hit))
  if len(corners)==4:
   completed+=1;features.append(dict(type='Feature',geometry=dict(type='Polygon',coordinates=[[[*to_lonlat.transform(*r[:2])] for r in corners+[corners[0]]]]),properties=dict(site=site,variant=variant,camera_key=cam.key,label=cam.label,wavelength_nm=650,method='Adjusted camera calibration + estimated transform + stored DEM id0 ray intersection',crs=c.crs.wkt)))
   if j%15==0:a=np.array(corners+[corners[0]]);ax.plot(a[:,0],a[:,1],color='#6ca5a2',alpha=.35,lw=.7)
 centers=np.array(centers);sc=ax.scatter(centers[:,0],centers[:,1],c=tilts,s=8,cmap='magma');fig.colorbar(sc,ax=ax,label='Estimated optical-axis tilt from nadir (deg)');ax.set(aspect='equal',xlabel='UTM easting (m)',ylabel='UTM northing (m)',title=f'{site} {variant}: calibrated camera positions / sampled footprints');fig.savefig(HERE/'figures'/(site.lower()+'_'+variant.lower()+'_footprints.png'),dpi=160);plt.close(fig)
 summary.append(dict(site=site,variant=variant,aligned_red_planes=len(cameras),complete_four_corner_DEM_hits=completed,optical_axis_tilt_quantiles=np.quantile(tilts,[0,.01,.5,.99,1]).tolist(),limitation='Incomplete footprints are not extended beyond DEM coverage; ray-cast visibility does not prove unoccluded image contribution'))
 print(site,variant,'footprints',completed,'/',len(cameras),flush=True)
(HERE/'footprints.geojson').write_text(json.dumps(dict(type='FeatureCollection',features=features,coordinate_system='EPSG:4326; RFC7946'),indent=2)+'\n');(HERE/'footprint_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
