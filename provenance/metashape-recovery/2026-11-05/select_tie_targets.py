"""Refine the fixed target lattice to tracked 3-D features, before radiometric fitting."""
import json
from pathlib import Path
import numpy as np,pandas as pd,Metashape,rasterio
from scipy.spatial import cKDTree
from pyproj import Transformer
from geometry import ground_to_photo,photo_ray,viewing_angles,point_ray_distance
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SRC=ROOT/'archive/local/metashape-recovery/2026-11-05/sources';inventory=json.loads((HERE/'remote_inventory.json').read_text());remote={r['relative_path']:r for r in inventory['objects']};lattice=json.loads((HERE/'ground_targets.json').read_text());observations=[];targets=[];selection=set()
for site in ['Ruby','Goldhill']:
 project=next(p for p in (SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('*.psx') if ('NOGCPS' in p.name)==(site=='Goldhill'));doc=Metashape.Document();doc.open(str(project),read_only=True,ignore_lock=True);chunk=doc.chunks[0];tp=chunk.tie_points;T=chunk.transform.matrix;mat=np.array([[T[i,j] for j in range(4)] for i in range(4)])
 items=[(p.track_id,list(p.coord)) for j in range(0,len(tp.points),10) if (p:=tp.points[j]).valid];ids=np.array([p[0] for p in items]);xyz=np.array([p[1] for p in items]);finite=np.isfinite(xyz).all(1)&(abs(xyz[:,3])>1e-12) if xyz.shape[1]==4 else np.isfinite(xyz).all(1);ids=ids[finite];xyz=xyz[finite];xyz=xyz[:,:3]/xyz[:,3,None] if xyz.shape[1]==4 else xyz;ecef=xyz@mat[:3,:3].T+mat[:3,3];trans=Transformer.from_crs(chunk.crs.geoccs.wkt,chunk.crs.wkt,always_xy=True);world=np.stack(trans.transform(*ecef.T),axis=1);tree=cKDTree(world);plans=[dict(p) for p in lattice if p['site']==site]
 with rasterio.open(project.with_suffix('.files')/'0/0/elevation/tile-0-0.tif') as dem:
  for plan in plans:plan['z']=float(next(dem.sample([(plan['x'],plan['y'])]))[0])
 queries={};needed=set()
 for target in plans:
  distance,index=tree.query([target['x'],target['y'],target['z']],k=256);queries[target['target_id']]=[(float(d),int(i)) for d,i in zip(distance,index) if d<20];needed.update(int(ids[i]) for d,i in queries[target['target_id']])
 # Actual aligned feature observations, not just geometrically possible footprints.
 tracks={k:{} for k in needed};masters=[c for c in chunk.cameras if c.transform is not None and c.master==c]
 for n,cam in enumerate(masters):
  for projection in tp.projections[cam]:
   if projection.track_id in tracks:tracks[projection.track_id][cam.key]=list(projection.coord)
  if n%100==0:print(site,'track observation scan',n,'/',len(masters),flush=True)
 red={};siblings={}
 for cam in chunk.cameras:
  if cam.transform is not None and cam.photo:
   master=cam.master if cam.master else cam;siblings.setdefault(master.key,[]).append(cam)
   if float(dict(cam.photo.meta).get('Pix4D/CentralWavelength','nan'))==650:red[master.key]=cam
 for target in plans:
  candidates=queries[target['target_id']];supported=[(d,i) for d,i in candidates if len(tracks[int(ids[i])])>=6]
  if not supported:print(site,target['target_id'],'no six-view tracked point within20m',flush=True);continue
  distance,index=min(supported);track=int(ids[index]);P=world[index];ec=Metashape.Vector(ecef[index].tolist());local=chunk.crs.localframe(ec);R=np.array([[local[i,j] for j in range(3)] for i in range(3)]);g=dict(site=site,target_id=target['target_id'],x=float(P[0]),y=float(P[1]),z=float(P[2]),track_id=track,matched_master_observations=len(tracks[track]),lattice_displacement_m=distance,project_path=str(project),coordinate_system=chunk.crs.wkt,target_registration='Aligned tie-point track; internally validated, not independent field truth');targets.append(g);angles=[]
  for master_key in tracks[track]:
   cam=red.get(master_key)
   if cam is None:continue
   uv,internal,_=ground_to_photo(chunk,cam,P.tolist(),Metashape)
   if uv is None or not (20<=uv.x<cam.sensor.width-20 and 20<=uv.y<cam.sensor.height-20):continue
   origin,ray=photo_ray(chunk,cam,uv);zen,az=viewing_angles(origin,ecef[index],R);angles.append((float(az),float(zen),cam))
  picked=[]
  for sector in range(8):
   group=[r for r in angles if int(r[0]//45)==sector]
   if group:picked.append(max(group,key=lambda r:r[1]))
  # Include a second distinct angle in occupied sectors until >=6 observations, if available.
  selected_keys={v[2].key for v in picked}
  for item in sorted(angles,key=lambda r:r[1]):
   if len(picked)>=max(6,min(12,len(angles))):break
   if item[2].key not in selected_keys:picked.append(item);selected_keys.add(item[2].key)
  for az,zen,cam in picked:
   master=cam.master if cam.master else cam;selected=siblings[master.key] if site=='Ruby' and target['target_id'] in ['ruby_1','ruby_5','ruby_9'] else [cam]
   for camera in selected:
    uv,internal,_=ground_to_photo(chunk,camera,P.tolist(),Metashape)
    if uv is None or not (5<=uv.x<camera.sensor.width-5 and 5<=uv.y<camera.sensor.height-5):continue
    photo=Path(camera.photo.path).resolve();relative=photo.relative_to(SRC).as_posix();assert relative in remote;selection.add(remote[relative]['remote_path']);origin,ray=photo_ray(chunk,camera,uv);z,a=viewing_angles(origin,ecef[index],R);dist,forward=point_ray_distance(ecef[index],origin,ray);master_obs=np.array(tracks[track][master.key]);master_pred=master.project(Metashape.Vector(xyz[index].tolist()));error=float(np.linalg.norm(np.array(list(master_pred))-master_obs))
    observations.append(dict(**g,camera_key=camera.key,master_key=master.key,label=camera.label,wavelength_nm=float(camera.photo.meta['Pix4D/CentralWavelength']),photo_path=str(photo),remote_path=remote[relative]['remote_path'],u=uv.x,v=uv.y,view_zenith_deg=float(z),view_azimuth_deg=float(a),ray_target_distance_m=float(dist),master_track_reprojection_error_px=error,camera_meta=dict(camera.meta),photo_meta=dict(camera.photo.meta)))
  print(site,target['target_id'],'track',track,'available',len(tracks[track]),'selected',len(picked),flush=True)
 (HERE/'tie_targets.json').write_text(json.dumps(targets,indent=2)+'\n');(HERE/'tie_observations_geometry.json').write_text(json.dumps(observations,indent=2)+'\n');(HERE/'tie_photo_selection.json').write_text(json.dumps(sorted(selection),indent=2)+'\n')
print('Unique needed photos',len(selection),'GB',sum(r['bytes'] for r in inventory['objects'] if r['remote_path'] in selection)/1e9,flush=True)
