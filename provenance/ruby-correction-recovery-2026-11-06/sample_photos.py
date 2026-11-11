"""Original and vendor-processed pixels at registered targets, with raw XMP lineage."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np,pandas as pd,Metashape
from PIL import Image
from spectralbridge.pipelines.drone import _compute_solar_geometry_arrays
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
p=argparse.ArgumentParser();p.add_argument('--geometry',default='observations_geometry.json');p.add_argument('--prefix',default='expanded');p.add_argument('--source-root',type=Path);a=p.parse_args();rows=json.loads((HERE/a.geometry).read_text())
if a.source_root:
 old_root=str(ROOT/'archive/local/metashape-recovery/2026-11-05/sources')
 for row in rows:
  for key in ['photo_path','project_path']:
   if key in row and str(row[key]).startswith(old_root):
    row['previous_'+key]=row[key];row[key]=str(a.source_root)+str(row[key])[len(old_root):]
missing=[r['photo_path'] for r in rows if not Path(r['photo_path']).exists()]
if missing:raise FileNotFoundError(str(len(set(missing)))+' required original photos not retrieved')
docs={};images={};groups={};out=[];audit=[]
for row in rows:groups.setdefault((row.get('project_path',row['site']),row['camera_key']),[]).append(row)
for n,((project,key),items) in enumerate(groups.items(),1):
 first=items[0]
 if project in ['Ruby','Goldhill']:
  project=str(next(p for p in (ROOT/'archive/local/metashape-recovery/2026-11-05/sources'/('AOP-'+project.upper()+'-08-14-23')).rglob('*.psx') if 'NOGCPS' not in p.name))
 if str(project) not in docs:
  doc=Metashape.Document();doc.open(str(project),read_only=True,ignore_lock=True);chunk=doc.chunks[0];docs[str(project)]=(doc,{c.key:c for c in chunk.cameras})
 doc,cameras=docs[str(project)];cam=cameras[key];photo=Path(first['photo_path'])
 with Image.open(photo) as im:
  raw=np.asarray(im).copy();xmp=im.tag_v2.get(700,b'');xmp=xmp[0] if isinstance(xmp,tuple) else xmp;black=np.mean(im.tag_v2.get(50714,[np.nan]));xml=ET.fromstring(xmp.rstrip(b'\x00'));metadata={}
  for e in xml.iter():
   if e.tag.startswith('{http://pix4d.com/camera') or e.tag.startswith('{http://micasense.com/'):
    vals=[v.text for v in e.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')];metadata[e.tag]=(vals if vals else e.text.strip() if e.text else None)
 image=cam.image();dtype={'U16':np.uint16,'F32':np.float32,'F64':np.float64}[image.data_type];processed=np.frombuffer(image.tostring(),dtype=dtype).reshape(image.height,image.width,-1)
 if processed.shape[-1]!=1:raise ValueError('Require one physically identified spectral plane')
 processed=processed[...,0];factor=dict(cam.meta).get('ReflectanceFactor');assert cam.sensor.normalize_sensitivity and factor is not None
 normalized=processed.astype(float)/(1 if cam.sensor.normalize_to_float else 32768)
 photo_meta=dict(cam.photo.meta);when=datetime.strptime(photo_meta['Exif/DateTimeOriginal'],'%Y:%m:%d %H:%M:%S').replace(tzinfo=timezone.utc);lon=float(photo_meta['Exif/GPSLongitude']);lat=float(photo_meta['Exif/GPSLatitude']);sz,sa=_compute_solar_geometry_arrays(acquisition_datetime=when,longitude=np.array([lon]),latitude=np.array([lat]));dls_elevation=float(metadata.get('{http://micasense.com/DLS/1.0/}SolarElevation','nan'));dls_az=float(metadata.get('{http://micasense.com/DLS/1.0/}SolarAzimuth','nan'))
 audit.append(dict(project=str(project),camera_key=key,photo=str(photo),dtype=str(raw.dtype),stored_min=int(raw.min()),stored_max=int(raw.max()),black_level=float(black),normalize_sensitivity=cam.sensor.normalize_sensitivity,normalize_to_float=cam.sensor.normalize_to_float,reflectance_factor=float(factor),sensor_sensitivity=list(cam.sensor.sensitivity),xmp=metadata,solar_utc_zenith_deg=float(sz[0]),solar_utc_azimuth_deg=float(sa[0]),DLS_solar_zenith_deg=float(90-np.rad2deg(dls_elevation)),DLS_solar_azimuth_deg=float(np.rad2deg(dls_az)),solar_convention_status='DLS metadata comparison supports UTC; not a direct solar instrument validation'))
 for r in items:
  u,v=int(round(r['u'])),int(round(r['v']));sl=(slice(max(0,v-4),min(raw.shape[0],v+5)),slice(max(0,u-4),min(raw.shape[1],u+5)));rp=raw[sl].astype(float);vp=normalized[sl];record={k:v for k,v in r.items() if k not in ['camera_meta','photo_meta','coordinate_system']};record.update(raw_DN_median=float(np.median(rp)),raw_DN_min=float(rp.min()),raw_DN_max=float(rp.max()),raw_DN_at_or_below_black_fraction=float(np.mean(rp<=black)),raw_DN_at_uint16_max_fraction=float(np.mean(rp>=65535)),vendor_DN_median=float(np.median(processed[sl])),vendor_fraction_median=float(np.median(vp)),vendor_fraction_std=float(np.std(vp)),vendor_fraction_center=float(normalized[v,u]),vendor_fraction_mad=float(np.median(abs(vp-np.median(vp)))),patch_rows=rp.shape[0],patch_columns=rp.shape[1],exposure_seconds=float(photo_meta['Exif/ExposureTime']),ISO=float(photo_meta['Exif/ISOSpeedRatings']),DLS_horizontal_irradiance=float(photo_meta.get('DLS/HorizontalIrradiance','nan')),reflectance_factor=float(factor),solar_zenith_deg=float(sz[0]),solar_azimuth_deg=float(sa[0]),timestamp_utc_scenario=when.isoformat(),radiometric_status='VENDOR_PROJECT_CALIBRATED_UNITS;INDEPENDENT_PHYSICAL_VALIDATION_PENDING');out.append(record)
 if n%25==0 or n==len(groups):print('Original photos sampled',n,'/',len(groups),flush=True)
 if n%10!=0 and n!=len(groups):continue
 pd.DataFrame(out).to_csv(HERE/(a.prefix+'_observations.csv'),index=False);(HERE/(a.prefix+'_photo_radiometry.json')).write_text(json.dumps(audit,indent=2)+'\n')
