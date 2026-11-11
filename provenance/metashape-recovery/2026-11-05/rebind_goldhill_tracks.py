"""Bind the same physical feature tracks to the export-matching Goldhill solution."""
import json,shutil
from pathlib import Path
import numpy as np,Metashape
from geometry import ground_to_photo,photo_ray,viewing_angles,point_ray_distance
HERE=Path(__file__).resolve().parent;SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources');folder=SRC/'AOP-GOLDHILL-08-14-23';p=next(p for p in folder.rglob('*.psx') if 'NOGCPS' not in p.name);d=Metashape.Document();d.open(str(p),read_only=True,ignore_lock=True);c=d.chunks[0];camera_by_label={cam.label:cam for cam in c.cameras};rows=json.loads((HERE/'tie_observations_geometry.json').read_text());needed={r['track_id'] for r in rows if r['site']=='Goldhill'};points={point.track_id:point.coord for point in c.tie_points.points if point.valid and point.track_id in needed};old_path=next(p for p in folder.rglob('*.psx') if 'NOGCPS' in p.name);od=Metashape.Document();od.open(str(old_path),read_only=True,ignore_lock=True);oc=od.chunks[0];checks=[];new=[]
# Verify identity by the observed source-image feature coordinates, not numeric ID alone.
old_features={};new_features={}
for chunk,table in [(oc,old_features),(c,new_features)]:
 for cam in chunk.cameras:
  if cam.transform is None or cam.master!=cam:continue
  for projection in chunk.tie_points.projections[cam]:
   if projection.track_id in needed:table[(projection.track_id,cam.label)]=np.array(list(projection.coord))
common=set(old_features)&set(new_features);deltas=[float(np.linalg.norm(old_features[k]-new_features[k])) for k in common];assert common and max(deltas)<1e-6
for r in rows:
 if r['site']!='Goldhill':new.append(r);continue
 cam=camera_by_label[r['label']];homogeneous=points[r['track_id']];pt=Metashape.Vector([homogeneous[i]/homogeneous[3] for i in range(3)]);ec=c.transform.matrix.mulp(pt);world=c.crs.project(ec);pixel=cam.project(pt);origin,ray=photo_ray(c,cam,pixel);local=c.crs.localframe(ec);R=np.array([[local[i,j] for j in range(3)] for i in range(3)]);z,a=viewing_angles(origin,np.array(list(ec)),R);dist,forward=point_ray_distance(np.array(list(ec)),origin,ray);master=cam.master if cam.master else cam;obs=new_features[(r['track_id'],master.label)];pred=master.project(pt);record=dict(r);record.update(previous_project_path=r['project_path'],previous_project_xyz=[r['x'],r['y'],r['z']],project_path=str(p),x=world.x,y=world.y,z=world.z,u=pixel.x,v=pixel.y,view_zenith_deg=float(z),view_azimuth_deg=float(a),ray_target_distance_m=float(dist),master_track_reprojection_error_px=float(np.linalg.norm(np.array(list(pred))-obs)),photo_path=str(Path(cam.photo.path).resolve()),camera_meta=dict(cam.meta),photo_meta=dict(cam.photo.meta));new.append(record)
control=HERE/'nogcps_overlap_control';control.mkdir(exist_ok=True)
for name in ['tie_observations_geometry.json','tie_targets.json','tie_observations.csv','repeated_target_fits.json']:
 if (HERE/name).exists() and not (control/name).exists():shutil.copy2(HERE/name,control/name)
(HERE/'tie_observations_geometry.json').write_text(json.dumps(new,indent=2)+'\n');targets={r['target_id']:{k:r[k] for k in ['site','target_id','x','y','z','track_id','matched_master_observations','lattice_displacement_m','project_path','target_registration']} for r in new};(HERE/'tie_targets.json').write_text(json.dumps(list(targets.values()),indent=2)+'\n');(HERE/'track_rebinding.json').write_text(json.dumps(dict(source='NOGCPS control',target='WORKING export-matching solution',same_observed_feature_pairs=len(common),max_source_pixel_coordinate_difference=max(deltas),original_photographs_unchanged=True,track_ids_verified_by_source_measurements=True),indent=2)+'\n');print('Rebound Goldhill tracks using',len(common),'identical source-image measurements',flush=True)
