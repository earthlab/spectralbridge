"""Compare official DEM hits to bracketed bilinear-DEM intersections on calibrated rays."""
from pathlib import Path
import json
import numpy as np,Metashape
from pyproj import Transformer
from affine import Affine
from scipy.ndimage import map_coordinates
from spectralbridge.drone_original import intersect_ecef_ray
P=Path(__file__).resolve().parent;R=P.parents[1];rows=json.loads((P/'observations_geometry.json').read_text());doc=Metashape.Document();doc.open(rows[0]['project_path'],read_only=True,ignore_lock=True);c=doc.chunks[0];cams={x.key:x for x in c.cameras};to=Transformer.from_crs(c.crs.geoccs.wkt,c.crs.wkt,always_xy=True);to_project=lambda a:np.column_stack(to.transform(*a.T));OUT=R/'archive/local/ruby-correction-recovery-2026-11-06';surfaces={}
for name in ['viewing_absolute','ground_dtm_chunk']:
 z=np.load(OUT/(name+'_terrain.npz'));tr=Affine(*z['transform'][:6]);elev=z['elevation']
 def sampler(xy,elev=elev,tr=tr):
  col,row=(~tr)*(xy[:,0],xy[:,1]);return map_coordinates(elev,[row-.5,col-.5],order=1,mode='constant',cval=np.nan)
 surfaces[name]=sampler
out=[]
for target in sorted(set(r['target_id'] for r in rows)):
 r=next(r for r in rows if r['target_id']==target and r['wavelength_nm']==650);cam=cams[r['camera_key']];uv=Metashape.Vector([r['u'],r['v']]);o=c.transform.matrix.mulp(cam.center);direction=c.transform.matrix.mulv(cam.transform.mulv(cam.calibration.unproject(uv)));origin=np.array(list(o));ray=np.array(list(direction));ray/=np.linalg.norm(ray)
 rec=dict(target_id=target,camera_key=cam.key)
 for name,sampler in surfaces.items():
  hit=intersect_ecef_ray(origin,ray,to_project=to_project,sample_height=sampler,maximum_distance=400,step_metres=.1);rr={k:v for k,v in hit.items() if k!='ecef'}
  if 'ecef' in hit:
   ecef=hit['ecef'];internal=c.transform.matrix.inv().mulp(Metashape.Vector(ecef.tolist()));pixel=cam.project(internal);point=to_project(ecef[None,:])[0];local=c.crs.localframe(Metashape.Vector(ecef.tolist())).mulv(o-Metashape.Vector(ecef.tolist()));rr.update(ground_project=point.tolist(),pixel_roundtrip_error=float((pixel-uv).norm()),feature_distance_m=float(np.linalg.norm(point-[r['x'],r['y'],r['z']])),view_zenith_deg=float(np.rad2deg(np.arctan2(np.hypot(local.x,local.y),local.z))))
  rec[name]=rr
 out.append(rec)
(P/'exact_ray_validation.json').write_text(json.dumps(out,indent=2)+'\n');print('Exact ray checks',len(out),'maxpx',max(v['viewing_absolute'].get('pixel_roundtrip_error',0) for v in out),flush=True)
