"""Direct primary-photo radiometric lineage, including the fixed red crossing."""
import json
from pathlib import Path
import Metashape
from geometry import ground_to_photo,photo_ray,viewing_angles
import numpy as np
HERE=Path(__file__).resolve().parent;SRC=Path('/private/tmp/spectralbridge-metashape-recovery-20261105/sources');inventory=json.loads((HERE/'remote_inventory.json').read_text());remote={r['relative_path']:r for r in inventory['objects']};targets=json.loads((HERE/'ground_targets.json').read_text());rows=[];selection=set()
for site in ['Ruby','Goldhill']:
 p=next(p for p in (SRC/('AOP-'+site.upper()+'-08-14-23')).rglob('*.psx') if 'NOGCPS' not in p.name);d=Metashape.Document();d.open(str(p),read_only=True,ignore_lock=True);c=d.chunks[0];red={}
 for cam in c.cameras:
  if cam.transform is not None and cam.photo and float(dict(cam.photo.meta).get('Pix4D/CentralWavelength','nan'))==650:red[(cam.master if cam.master else cam).key]=cam
 pts=[dict(r) for r in targets if r['site']==site]
 if site=='Goldhill':pts.extend([dict(site=site,target_id='boundary_left',x=457722.55,y=4432738.4),dict(site=site,target_id='boundary_right',x=457722.65,y=4432738.4)])
 for target in pts:
  x,y=target['x'],target['y'];master=c.orthomosaic.camera(Metashape.Vector([x,y]));cam=red[master.key];z=c.elevations[0].altitude(Metashape.Vector([x,y]));uv,internal,ec=ground_to_photo(c,cam,[x,y,z],Metashape);origin,ray=photo_ray(c,cam,uv);local=c.crs.localframe(ec);R=np.array([[local[i,j] for j in range(3)] for i in range(3)]);zen,az=viewing_angles(origin,np.array(list(ec)),R);photo=Path(cam.photo.path).resolve();rel=photo.relative_to(SRC).as_posix();selection.add(remote[rel]['remote_path']);rows.append(dict(site=site,target_id=target['target_id'],x=x,y=y,z=z,project_path=str(p),camera_key=cam.key,master_key=master.key,label=cam.label,wavelength_nm=650,photo_path=str(photo),remote_path=remote[rel]['remote_path'],u=uv.x,v=uv.y,view_zenith_deg=float(zen),view_azimuth_deg=float(az)))
(HERE/'primary_photo_geometry.json').write_text(json.dumps(rows,indent=2)+'\n');(HERE/'primary_photo_selection.json').write_text(json.dumps(sorted(selection),indent=2)+'\n');print('primary red photos',len(selection))
