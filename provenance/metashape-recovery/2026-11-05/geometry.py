"""Experimental API-based rays; no assumed Euler or camera-axis convention.

The official Camera.project and Calibration.unproject models are authoritative.
Localframe rows are east/north/up at the ground point; angles describe the
surface-to-sensor direction, clockwise azimuth from true north.
"""
import numpy as np

def normalize(vector):
    value=np.asarray(vector,dtype=float)
    length=np.linalg.norm(value,axis=-1,keepdims=True)
    if not np.isfinite(value).all() or np.any(length<=0):
        raise ValueError('Finite nonzero direction required')
    return value/length

def viewing_angles(camera_ecef,ground_ecef,ecef_to_enu):
    delta=np.asarray(camera_ecef,float)-np.asarray(ground_ecef,float)
    rotation=np.asarray(ecef_to_enu,float)
    if rotation.shape!=(3,3) or not np.allclose(rotation@rotation.T,np.eye(3),atol=1e-7):
        raise ValueError('Orthonormal ECEF-to-ENU rotation required')
    enu=np.einsum('ij,...j->...i',rotation,delta)
    if np.any(enu[...,2]<=0):raise ValueError('Camera is not above the local ground tangent')
    zenith=np.rad2deg(np.arctan2(np.hypot(enu[...,0],enu[...,1]),enu[...,2]))
    azimuth=np.rad2deg(np.arctan2(enu[...,0],enu[...,1]))%360
    return zenith,azimuth

def ground_to_photo(chunk,camera,project_point,Metashape):
    if camera.transform is None:raise ValueError('Aligned camera transform required')
    ecef=chunk.crs.unproject(Metashape.Vector(project_point))
    internal=chunk.transform.matrix.inv().mulp(ecef)
    pixel=camera.project(internal)
    return pixel,internal,ecef

def photo_ray(chunk,camera,pixel):
    if camera.transform is None:raise ValueError('Aligned camera transform required')
    local=camera.calibration.unproject(pixel)
    origin=chunk.transform.matrix.mulp(camera.center)
    ray=chunk.transform.matrix.mulv(camera.transform.mulv(local))
    return np.asarray(list(origin)),normalize(np.asarray(list(ray)))

def point_ray_distance(point,origin,direction):
    delta=np.asarray(point,float)-np.asarray(origin,float)
    direction=normalize(direction)
    distance=np.linalg.norm(np.cross(delta,direction),axis=-1)
    forward=np.sum(delta*direction,axis=-1)>0
    return distance,forward

def require_asset_binding(camera_metadata,surface_metadata):
    """Reject mixed project/frame evidence before experimental ray construction.

    Fingerprints must cover the project/chunk/frame descriptors, not only the
    tiny PSX pointer (identical pointers can occur in different projects).
    An absolute camera frame cannot be paired with relative canopy heights.
    This explicit experiment contract does not modify production processing.
    """
    for field in ['project_fingerprint','chunk_key','crs','coordinate_frame']:
        if field not in camera_metadata or field not in surface_metadata:
            raise ValueError('Missing source binding: '+field)
        if camera_metadata[field]!=surface_metadata[field]:
            raise ValueError('Camera/surface source mismatch: '+field)
    if camera_metadata['coordinate_frame']!='project_absolute':
        raise ValueError('Absolute project coordinates required for viewing rays')
    return dict(camera_metadata)

def open_native_orthomosaic_tile(path,*,expected_shape,expected_bands=10):
    """Open the largest multispectral TIFF directory, not a stored thumbnail.

    Metashape's retained mosaic tiles can put a small image directory first.
    GDAL's documented GTIFF_DIR interface reads those directories without
    rewriting the source or changing production GeoTIFF readers.
    """
    import rasterio
    candidates=[]
    for directory in range(1,33):
        try:
            with rasterio.open('GTIFF_DIR:'+str(directory)+':'+str(path)) as src:
                if src.count==expected_bands and all(t=='uint16' for t in src.dtypes):
                    candidates.append((src.width*src.height,directory))
        except rasterio.errors.RasterioIOError:
            break
    if not candidates:raise ValueError('No supported native multispectral TIFF directory')
    _,directory=max(candidates,key=lambda r:(r[0],-r[1]))
    dataset=rasterio.open('GTIFF_DIR:'+str(directory)+':'+str(path))
    if dataset.shape!=tuple(expected_shape):
        dataset.close()
        raise ValueError('Native image does not match declared tile grid')
    return dataset

def project_descriptor_fingerprint(project_path):
    """Bind pointer, chunk transforms/calibrations and frame metadata together."""
    import hashlib,json
    from pathlib import Path
    project=Path(project_path);files=project.with_suffix('.files')
    paths=[project,files/'project.zip']+sorted(files.rglob('chunk.zip'))+sorted(files.rglob('frame.zip'))
    if not any(p.name=='chunk.zip' for p in paths) or not any(p.name=='frame.zip' for p in paths):
        raise ValueError('Complete project/chunk/frame descriptors required')
    records=[(str(p.relative_to(project.parent)),hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths]
    return hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest()
