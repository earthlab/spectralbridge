"""Official API, read-only project extraction; runnable in a licensed Metashape Python environment."""
import argparse,json,csv
from pathlib import Path
try:
 import pandas as pd
except ImportError:
 pd=None
import Metashape
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,default=ROOT/'archive/local/metashape-recovery/2026-11-05/sources');parser.add_argument('--output-root',type=Path,default=HERE/'extracted');args=parser.parse_args();SOURCE=args.source_root.resolve();OUT=args.output_root.resolve();OUT.mkdir(parents=True,exist_ok=True)
def vec(x):return list(x) if x is not None else None
def matrix(m):return [[m[i,j] for j in range(m.size[1])] for i in range(m.size[0])] if m is not None else None
def text_crs(x):return x.wkt if x is not None else None
def get(obj,attr):
 try:return getattr(obj,attr)
 except (AttributeError,RuntimeError,OSError):return None
def calibration(cal):
 if cal is None:return None
 return {k:get(cal,k) for k in ['type','width','height','f','cx','cy','b1','b2','k1','k2','k3','k4','p1','p2','p3','p4']}
def clean(o):
 if isinstance(o,dict):return {str(k):clean(v) for k,v in o.items()}
 if isinstance(o,(list,tuple)):return [clean(v) for v in o]
 if isinstance(o,(str,int,float,bool)) or o is None:return o
 return str(o)
records=[]
for path in sorted(SOURCE.rglob('*.psx'),key=lambda p:'RUBY' not in str(p)):
 doc=Metashape.Document();doc.open(str(path),read_only=True,ignore_lock=True);project=dict(project_path=str(path),api_version=Metashape.app.version,license_activated=Metashape.app.activated,read_only=True,chunks=[])
 for chunk in doc.chunks:
  identity=path.stem+'_chunk_'+str(chunk.key);folder=OUT/identity;folder.mkdir(exist_ok=True);T=chunk.transform.matrix;rows=[];sensors=[]
  for s in chunk.sensors:
   sensors.append(dict(key=s.key,label=s.label,type=str(s.type),width=s.width,height=s.height,pixel_width=s.pixel_width,pixel_height=s.pixel_height,focal_length=s.focal_length,master_key=s.master.key if get(s,'master') is not None else None,layer_index=get(s,'layer_index'),bands=clean(get(s,'bands')),adjusted=calibration(s.calibration),initial=calibration(get(s,'user_calib')),normalize_sensitivity=s.normalize_sensitivity,normalize_to_float=s.normalize_to_float,black_level=list(s.black_level),sensitivity=list(s.sensitivity),axes=str(s.axes),relative_location=vec(s.location),relative_rotation=matrix(s.rotation),sensor_meta=dict(s.meta)))
  for camera in chunk.cameras:
   estimated_ecef=T.mulp(camera.center) if camera.transform is not None and T is not None else None
   estimated_project=chunk.crs.project(estimated_ecef) if estimated_ecef is not None and chunk.crs is not None else None
   photo=camera.photo;row=dict(camera_key=camera.key,label=camera.label,sensor_key=camera.sensor.key if camera.sensor else None,enabled=camera.enabled,aligned=camera.transform is not None,master_camera_key=camera.master.key if get(camera,'master') is not None else None,photo_path=photo.path if photo else None,transform_chunk=matrix(camera.transform),center_chunk=vec(camera.center),center_ecef=vec(estimated_ecef),center_project=vec(estimated_project),reference_location=vec(camera.reference.location),reference_rotation=vec(camera.reference.rotation),reference_location_accuracy=vec(camera.reference.location_accuracy),reference_rotation_accuracy=vec(camera.reference.rotation_accuracy),location_covariance=matrix(get(camera,'location_covariance')),rotation_covariance=matrix(get(camera,'rotation_covariance')),photo_metadata=dict(photo.meta) if photo else {},camera_metadata=dict(camera.meta))
   row['photo_physically_present']=bool(photo and Path(photo.path).is_file())
   row['photo_recovery_status']='LOCAL_PATH_PRESENT_CHECK_MANIFEST_FOR_HASH' if row['photo_physically_present'] else 'REFERENCED_NOT_RECOVERED_AT_PATH'
   rows.append(clean(row))
  # Nested information is explicit JSON text in a portable flat table.
  flat=[{k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows]
  with (folder/'cameras.csv').open('w',newline='') as stream:
   writer=csv.DictWriter(stream,fieldnames=list(flat[0]) if flat else ['camera_key']);writer.writeheader();writer.writerows(flat)
  if pd is not None:pd.DataFrame(flat).to_parquet(folder/'cameras.parquet',index=False)
  (folder/'sensors.json').write_text(json.dumps(clean(sensors),indent=2)+'\n')
  assets={}
  for name in ['elevation','orthomosaic','model','point_cloud','tie_points','shapes']:
   obj=get(chunk,name);rec=dict(present=obj is not None,type=type(obj).__name__)
   if obj is not None:
    for attr in ['key','label','width','height','resolution','point_count','face_count','tile_width','tile_height','blending_mode','meta']:
     value=get(obj,attr)
     if value is not None:rec[attr]=dict(value) if attr=='meta' else clean(value)
   assets[name]=rec
  item=dict(key=chunk.key,label=chunk.label,cameras=len(rows),aligned=sum(r['aligned'] for r in rows),sensors=len(sensors),chunk_transform=matrix(T),crs=text_crs(chunk.crs),camera_reference_crs=text_crs(get(chunk,'camera_crs')),marker_crs=text_crs(get(chunk,'marker_crs')),meta=dict(chunk.meta),assets=assets,portable_camera_table=str(folder/('cameras.parquet' if pd is not None else 'cameras.csv')),portable_sensors=str(folder/'sensors.json'))
  (folder/'chunk.json').write_text(json.dumps(clean(item),indent=2)+'\n');project['chunks'].append(item);print(path.stem,chunk.key,chunk.label,'cameras',len(rows),'aligned',item['aligned'],flush=True)
 (OUT/(path.stem+'_project.json')).write_text(json.dumps(clean(project),indent=2)+'\n');records.append(project)
(HERE/'project_extraction.json').write_text(json.dumps(clean(records),indent=2)+'\n')
