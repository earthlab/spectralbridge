"""Actual adjusted-calibration rays, independently typed surfaces and internal checks."""
from pathlib import Path
import json
import numpy as np,Metashape
from spectralbridge.drone_original import reconstruct_pixel_geometry
P=Path(__file__).resolve().parent;R=P.parents[1];rows=json.loads((P/'observations_geometry.json').read_text());doc=Metashape.Document();doc.open(rows[0]['project_path'],read_only=True,ignore_lock=True);chunk=doc.chunks[0];ground=doc.chunks[1];cameras={c.key:c for c in chunk.cameras};records=[]
for row in [next(r for r in rows if r['target_id']==t and r['wavelength_nm']==650) for t in sorted(set(r['target_id'] for r in rows))]:
 camera=cameras[row['camera_key']];out=reconstruct_pixel_geometry(chunk,camera,[row['u'],row['v']],chunk.elevations[0],api=Metashape)
 if 'ground_project' in out:
  target=np.array([row['x'],row['y'],row['z']]);hit=np.array(out['ground_project']);out.update(target_id=row['target_id'],feature_minus_first_surface_hit_m=(target-hit).tolist(),feature_to_surface_distance_m=float(np.linalg.norm(target-hit)),feature_view_zenith_deg=row['view_zenith_deg'])
 records.append(out)
mat=lambda c:np.array([[c.transform.matrix[i,j] for j in range(4)] for i in range(4)])
summary=dict(records=records,view_chunk=chunk.key,ground_chunk=ground.key,chunk_transform_max_difference=float(np.max(abs(mat(chunk)-mat(ground)))),surface_roles='Rays: absolute chunk0 DEM0; ground SCS+C candidate: chunk3 DTM; active canopy-height surface excluded',independent_geolocation_accuracy='UNVERIFIED',internal_roundtrip_max_px=max(v['pixel_roundtrip_error'] for v in records if 'pixel_roundtrip_error' in v))
(P/'geometry_validation.json').write_text(json.dumps(summary,indent=2)+'\n');print('Ray checks',len(records),summary['internal_roundtrip_max_px'],summary['chunk_transform_max_difference'])
