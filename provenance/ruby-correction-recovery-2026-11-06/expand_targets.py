"""Fixed spatial-grid Ruby repeated-track selection, independent of radiometric outcome."""
import importlib.util,json
from pathlib import Path
import numpy as np
import Metashape,rasterio
from scipy.spatial import cKDTree
from pyproj import Transformer
P=Path(__file__).resolve().parent;R=P.parents[1];OLD=R/'provenance/metashape-recovery/2026-11-05';SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources')
spec=importlib.util.spec_from_file_location('recovery_geometry',OLD/'geometry.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
project=next((SRC/'AOP-RUBY-08-14-23').rglob('*.psx'));doc=Metashape.Document();doc.open(str(project),read_only=True,ignore_lock=True);chunk=doc.chunks[0];tp=chunk.tie_points;T=chunk.transform.matrix;mat=np.array([[T[i,j] for j in range(4)] for i in range(4)]);fingerprint=g.project_descriptor_fingerprint(project)
items=[(pt.track_id,list(pt.coord)) for pt in tp.points if pt.valid];ids=np.array([v[0] for v in items]);xyz=np.array([v[1] for v in items]);xyz=xyz[:,:3]/xyz[:,3,None] if xyz.shape[1]==4 else xyz;ecef=xyz@mat[:3,:3].T+mat[:3,3];trans=Transformer.from_crs(chunk.crs.geoccs.wkt,chunk.crs.wkt,always_xy=True);world=np.stack(trans.transform(*ecef.T),axis=1);finite=np.isfinite(world).all(1);ids=ids[finite];xyz=xyz[finite];ecef=ecef[finite];world=world[finite];tree=cKDTree(world[:,:2]);queries=[];needed=set()
with rasterio.open('/private/tmp/spectralbridge-metashape-recovery-20261105/originals/ruby.tif') as src:
 bounds=src.bounds
 for iy,y in enumerate(np.linspace(bounds.bottom+6,bounds.top-6,8)):
  for ix,x in enumerate(np.linspace(bounds.left+6,bounds.right-6,8)):
   d,ind=tree.query([x,y],k=256);candidates=[(float(dd),int(ii)) for dd,ii in zip(d,ind) if dd<=10];queries.append((iy*8+ix,x,y,candidates));needed.update(int(ids[ii]) for _,ii in candidates)
tracks={k:{} for k in needed};masters=[c for c in chunk.cameras if c.transform is not None and c.master==c]
for n,c in enumerate(masters):
 for projection in tp.projections[c]:
  if projection.track_id in tracks:tracks[projection.track_id][c.key]=list(projection.coord)
 if n%100==0:print('Track scan',n,len(masters),flush=True)
siblings={}
for cam in chunk.cameras:
 if cam.transform is not None and cam.photo:
  master=cam.master or cam;siblings.setdefault(master.key,[]).append(cam)
remote={r['relative_path']:r for r in json.loads((OLD/'remote_inventory.json').read_text())['objects']};rows=[];targets=[];selection=set();used=set();coverage=[]
for cell,x,y,candidates in queries:
 eligible=[(d,i) for d,i in candidates if len(tracks[int(ids[i])])>=4 and int(ids[i]) not in used]
 if not eligible:coverage.append(dict(cell=cell,x=x,y=y,status='NO_FOUR_VIEW_TRACK_WITHIN_10M'));continue
 distance,i=min(eligible);track=int(ids[i]);used.add(track);point=world[i];ec=Metashape.Vector(ecef[i].tolist());local=chunk.crs.localframe(ec);rot=np.array([[local[a,b] for b in range(3)] for a in range(3)]);keys=sorted(tracks[track],key=lambda k:dict(chunk.cameras[[c.key for c in chunk.cameras].index(k)].photo.meta).get('Exif/DateTimeOriginal',''))
 # At most eight evenly spaced temporal observations, no angular or reflectance optimization.
 keys=[keys[j] for j in np.unique(np.linspace(0,len(keys)-1,min(8,len(keys))).round().astype(int))]
 target=dict(site='Ruby',target_id='ruby_grid_'+str(cell),cell=cell,x=float(point[0]),y=float(point[1]),z=float(point[2]),track_id=track,lattice_displacement_m=distance,matched_master_observations=len(tracks[track]),project_path=str(project),project_fingerprint=fingerprint,coordinate_system=chunk.crs.wkt,target_registration='Aligned tie-point feature; internal registration only');targets.append(target);coverage.append(dict(cell=cell,x=x,y=y,status='SELECTED',target_id=target['target_id']))
 for key in keys:
  for camera in siblings[key]:
   uv,internal,_=g.ground_to_photo(chunk,camera,point.tolist(),Metashape)
   if uv is None or not (6<=uv.x<camera.sensor.width-6 and 6<=uv.y<camera.sensor.height-6):continue
   master=camera.master or camera;pred=master.project(Metashape.Vector(xyz[i].tolist()));error=float(np.linalg.norm(np.array(list(pred))-tracks[track][key]));photo=Path(camera.photo.path).resolve();relative=photo.relative_to(SRC).as_posix()
   if relative not in remote:raise ValueError('Photo lacks remote identity '+relative)
   origin,ray=g.photo_ray(chunk,camera,uv);zen,az=g.viewing_angles(origin,ecef[i],rot);dist,forward=g.point_ray_distance(ecef[i],origin,ray)
   rows.append(dict(**target,camera_key=camera.key,master_key=key,label=camera.label,wavelength_nm=float(camera.photo.meta['Pix4D/CentralWavelength']),photo_path=str(photo),remote_path=remote[relative]['remote_path'],u=float(uv.x),v=float(uv.y),view_zenith_deg=float(zen),view_azimuth_deg=float(az),ray_target_distance_m=float(dist),master_track_reprojection_error_px=error));selection.add(remote[relative]['remote_path'])
 print('Grid',cell,'targets',len(targets),'rows',len(rows),'photos',len(selection),flush=True)
for name,value in [('targets',targets),('coverage',coverage),('observations_geometry',rows),('photo_selection',sorted(selection))]: (P/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
(P/'selection_policy.json').write_text(json.dumps(dict(grid=[8,8],maximum_displacement_m=10,minimum_master_views=4,maximum_selected_views=8,view_selection='evenly spaced chronological index; all ten source bands',surface_classes='Not independently labelled; spectral/height strata evaluated descriptively',project_fingerprint=fingerprint,photos=len(selection),bytes=sum(v['bytes'] for v in remote.values() if v['remote_path'] in selection)),indent=2)+'\n')
