"""Gated copied-project reconstruction in a separately licensed Metashape runtime.

This interface is prepared and read-only preflight tested. Licensed build/export
is NOT validated locally. It never opens the source for writing. Corrected images
must already have accepted matched SCS+C+BRDF evidence; no raw calibration is
reapplied. The current P184 status intentionally fails this gate.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import Metashape
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--check-only',action='store_true');a=p.parse_args();m=json.loads(a.manifest.read_text())
if m.get('status')!='VALIDATED_MATCHED_SOURCE_IMAGES':raise SystemExit('UNSUPPORTED: accepted matched source-image products are required; no project changed')
if not m.get('both_corrections_required') or not m.get('independent_or_heldout_validation_passed'):raise SystemExit('UNSUPPORTED: both correction stages and validation evidence required')
if not m.get('calibrated_replacement_max_error',1)<=1e-7:raise SystemExit('UNSUPPORTED: source replacement roundtrip failed')
source=Path(m['source_project']).resolve();destination=Path(m['copied_project']).resolve();export=Path(m['output_orthomosaic']).resolve()
if source==destination or destination.exists() or export.exists():raise SystemExit('Refuse source modification or existing-output overwrite')
files=source.with_suffix('.files');descriptors=[source,files/'project.zip']+sorted(files.rglob('chunk.zip'))+sorted(files.rglob('frame.zip'))
identity=[(str(p.relative_to(source.parent)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in descriptors]
fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
if fingerprint!=m['project_fingerprint']:raise SystemExit('Source project/chunk fingerprint mismatch')
d=Metashape.Document();d.open(str(source),read_only=True,ignore_lock=True);chunk=next(c for c in d.chunks if c.key==m['chunk_key']);cameras={c.key:c for c in chunk.cameras};items=m['corrected_photos']
expected={c.key for c in chunk.cameras if c.enabled and c.transform is not None}
if {r['camera_key'] for r in items}!=expected:raise SystemExit('UNSUPPORTED: complete enabled-camera replacement manifest required')
for row in items:
 path=Path(row['path'])
 if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise SystemExit('Corrected photo checksum mismatch')
 if row['units']!='reflectance_fraction' or not row['both_stages_supported']:raise SystemExit('Unsupported units or correction stages')
 cam=cameras[row['camera_key']]
 if [cam.sensor.width,cam.sensor.height]!=row['dimensions']:raise SystemExit('Source geometry dimensions changed')
if a.check_only:print('Gated manifest checks passed; no source modified; license active:',Metashape.app.activated);raise SystemExit(0)
if not Metashape.app.activated:raise SystemExit('Licensed build/export unavailable; no source modified')
# Only the new project is writable. No align/optimize/DEM recomputation occurs.
destination.parent.mkdir(parents=True,exist_ok=True);d.save(str(destination));d.open(str(destination));chunk=next(c for c in d.chunks if c.key==m['chunk_key']);cameras={c.key:c for c in chunk.cameras}
for row in items:
 cam=cameras[row['camera_key']];before=np.array([[cam.transform[i,j] for j in range(4)] for i in range(4)]);photo=Metashape.Photo();photo.path=row['path'];cam.photo=photo;cam.sensor.normalize_sensitivity=False;cam.sensor.normalize_to_float=True;cam.sensor.black_level=[0.];cam.sensor.sensitivity=[1.];cam.sensor.vignetting=[];cam.vignetting=None
 for key in list(cam.meta.keys()):
  if key.startswith('Reflectance'):del cam.meta[key]
 if row.get('mask_path'):
  mask=Metashape.Mask();mask.load(row['mask_path']);cam.mask=mask
 assert np.array_equal(before,[[cam.transform[i,j] for j in range(4)] for i in range(4)])
# Caller must explicitly recover/review the original mosaic settings; no guessed defaults.
settings=m['orthomosaic_settings'];required={'resolution','fill_holes','ghosting_filter','color_enhancement','refine_seamlines','blending_mode'}
if not required.issubset(settings) or settings['blending_mode']!='MosaicBlending':raise SystemExit('Explicit reviewed original mosaic settings required')
if settings['color_enhancement']:raise SystemExit('Radiometric comparison forbids automatic color enhancement')
chunk.elevation=next(e for e in chunk.elevations if e.key==m['viewing_surface_key'])
chunk.buildOrthomosaic(surface_data=Metashape.ElevationData,blending_mode=Metashape.MosaicBlending,fill_holes=settings['fill_holes'],ghosting_filter=settings['ghosting_filter'],color_enhancement=False,refine_seamlines=settings['refine_seamlines'],resolution=settings['resolution'],replace_asset=False)
chunk.exportRaster(str(export),source_data=Metashape.OrthomosaicData,image_format=Metashape.ImageFormatTIFF,raster_transform=Metashape.RasterTransformNone,resolution=.1,save_alpha=True)
d.save();print('Licensed reconstruction completed:',export)
