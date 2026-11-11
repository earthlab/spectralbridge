"""Inspect the explicit Metashape camera CSV contract without rewriting sources."""
import csv,hashlib,json,re
from pathlib import Path
import numpy as np
import pandas as pd
from affine import Affine
from pyproj import Transformer
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
source=json.loads((HERE/'camera_table_inventory.json').read_text())
footprints=json.loads((ROOT/'provenance/drone-spatial-integrity/2026-10-29/production_source_comparison.json').read_text())
results=[]
for item in source:
    path=Path(item['local_path'])
    records=list(csv.reader(path.open(newline='')))
    index=next(i for i,row in enumerate(records) if row and row[0].strip()=='# PhotoID')
    declared_crs=records[0][1].strip() if records[0][0].strip()=='CRS' else None
    frame=pd.read_csv(path,skiprows=index,skipinitialspace=True)
    frame.columns=frame.columns.str.lstrip('#').str.strip()
    numeric=frame.drop(columns='PhotoID').apply(pd.to_numeric,errors='coerce')
    coordinates=numeric[['X','Y','Z']].to_numpy()
    rotation=numeric[[f'r{i}{j}' for i in range(1,4) for j in range(1,4)]].to_numpy().reshape(-1,3,3)
    result=dict(package=item['package'],remote_path=item['remote_path'],remote_md5=item['remote_md5'],sha256=item['sha256'],
        rows=len(frame),declared_camera_rows=int(re.search(r'\((\d+)\)',records[1][0]).group(1)),
        declared_epsg=declared_crs,columns=list(frame.columns),unique_photo_ids=int(frame.PhotoID.nunique()),
        duplicated_photo_ids=int(frame.PhotoID.duplicated().sum()),missing_values=int(frame.isna().sum().sum()),
        numeric_values_finite=bool(np.isfinite(numeric.to_numpy()).all()),unique_xyz_positions=int(frame[['X','Y','Z']].drop_duplicates().shape[0]),
        xyz_min=coordinates.min(axis=0).tolist(),xyz_max=coordinates.max(axis=0).tolist(),
        max_rotation_orthogonality_error=float(np.max(np.abs(rotation@rotation.transpose(0,2,1)-np.eye(3)))),
        rotation_determinant_range=[float(np.linalg.det(rotation).min()),float(np.linalg.det(rotation).max())],
        timestamps_in_table=False,source_immutable=hashlib.md5(path.read_bytes()).hexdigest()==item['remote_md5'],
        geometry_status='SOURCE_CAMERA_METADATA; actual mosaic contributors, clock, vertical datum and physical radiometry not certified')
    match=next((r for r in footprints if r['flight'].split('_')[1].lower() in item['package'].lower()),None)
    if match:
        rows,cols=match['dimensions'];affine=Affine(*match['source_affine'][:6]);corners=np.array([affine*(x,y) for x,y in [(0,0),(cols,0),(0,rows),(cols,rows)]])
        left,bottom=corners.min(axis=0);right,top=corners.max(axis=0)
        def inside(x,y):return int(((x>=left)&(x<=right)&(y>=bottom)&(y<=top)).sum())
        x,y=Transformer.from_crs('EPSG:'+declared_crs,match['source_crs'],always_xy=True).transform(coordinates[:,0],coordinates[:,1])
        result['historical_footprint_check']=dict(reference='provenance/drone-spatial-integrity/2026-10-29/production_source_comparison.json',
            raster_crs=match['source_crs'],inside_using_declared_crs=inside(np.asarray(x),np.asarray(y)),
            inside_if_xy_already_in_raster_crs=inside(coordinates[:,0],coordinates[:,1]),
            qualification='Historical processing footprint, not a new survey validation. Alternate interpretation is diagnostic only; source CRS not relabeled.')
    results.append(result)
    print(item['package'],len(frame),result['unique_xyz_positions'],'positions; declared EPSG',declared_crs,flush=True)
(HERE/'camera_table_validation.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
# Inventory holds integrity/paths only; parsed summaries replace the initial generic CSV preview.
for row in source:
    for key in ['columns','missing_by_column','sample_rows','rows']:row.pop(key,None)
(HERE/'camera_table_inventory.json').write_text(json.dumps(source,indent=2,allow_nan=False)+'\n')
