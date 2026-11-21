"""Explicit drone campaign inputs at the existing radiometry/geometry boundaries.

Camera assignments are operational declarations, never inferred mosaic contributors.
Only derived working H5 files are edited. Geometry/masks are written by bounded rows.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np

from .radiometry import Radiometry

BRIGHTNESS_EQUATION = "calibrated_reflectance = gain * decoded_reflectance + offset"


def compose_brightness_calibration(record, *, flight_id, source_sha256, wavelengths_nm, source_radiometry):
    """Compose reviewed per-band calibration with source decoding, exactly once.

    Gain/offset operate in fractional reflectance, not stored TIFF/DN units.
    This returns an existing Radiometry record; it does not change source pixels
    or claim that the public pipeline's historical brightness flag applies it.
    """
    if record.get("schema_version") != 1 or record.get("status") != "REVIEWED":
        raise ValueError("Brightness JSON requires schema_version=1 and status=REVIEWED")
    if record.get("equation") != BRIGHTNESS_EQUATION:
        raise ValueError("Declare gain direction and fractional-reflectance offset units explicitly")
    if record.get("flight_id") != flight_id or record.get("source_sha256") != source_sha256:
        raise ValueError("Brightness calibration flight/source SHA-256 mismatch")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64:
        raise ValueError("Expected full source SHA-256")
    try:
        int(source_sha256, 16)
    except ValueError as exc:
        raise ValueError("Expected hexadecimal source SHA-256") from exc
    if not record.get("calibration_id") or not str(record.get("provenance", "")).strip():
        raise ValueError("Brightness calibration requires identity and provenance")
    base = Radiometry.from_record(source_radiometry).require_valid()
    if (base.encoding or {}).get("brightness_calibration_id"):
        raise ValueError("Brightness calibration already applied; double calibration rejected")
    bands = record.get("bands", [])
    waves = np.asarray(wavelengths_nm, dtype=float)
    if waves.ndim != 1 or not len(waves) or not np.isfinite(waves).all():
        raise ValueError("Expected finite one-dimensional source wavelengths")
    if len(bands) != len(waves):
        raise ValueError("Brightness JSON must cover every source wavelength exactly once")
    declared = np.asarray([row["wavelength_nm"] for row in bands], dtype=float)
    if len(np.unique(declared)) != len(declared) or not np.allclose(declared, waves, rtol=0, atol=1e-6):
        raise ValueError("Brightness wavelength identities/order differ from source")
    gain = np.asarray([row["gain"] for row in bands], dtype=float)
    offset = np.asarray([row["offset"] for row in bands], dtype=float)
    if not np.isfinite(gain).all() or not np.isfinite(offset).all() or np.any(gain <= 0):
        raise ValueError("Brightness gains must be finite and positive; offsets finite")
    try:
        scale = np.broadcast_to(np.asarray(base.scale), waves.shape) * gain
        intercept = np.broadcast_to(np.asarray(base.offset), waves.shape) * gain + offset
    except ValueError as exc:
        raise ValueError("Source decoding coefficient count differs from wavelengths") from exc
    encoding = dict(base.encoding or {"kind": "scaled_physical_reflectance"})
    encoding.update(
        brightness_calibration_id=record["calibration_id"],
        brightness_calibration_sha256=hashlib.sha256(
            json.dumps(record, sort_keys=True, allow_nan=False).encode()
        ).hexdigest(),
        brightness_source_sha256=source_sha256,
        brightness_equation=BRIGHTNESS_EQUATION,
        brightness_wavelengths_nm=waves.tolist(),
    )
    return Radiometry(
        tuple(scale), tuple(intercept), "VALID",
        f"{base.provenance}; brightness {record['calibration_id']}: {record['provenance']}",
        encoding=encoding,
    ).require_valid().record()



def file_sha256(path):
    digest = hashlib.sha256()
    processed = 0
    next_progress = 1024**3
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            digest.update(block)
            processed += len(block)
            if processed >= next_progress:
                logging.getLogger(__name__).info('SHA256 %s: %.1f GiB read', Path(path).name, processed / 1024**3)
                next_progress += 1024**3
    return digest.hexdigest()


def campaign_input_identity(camera_geometry=None, processing_mask=None):
    """Validate explicit policies and fingerprint their backing files for restarts."""
    result = {}
    for name, config, paths in [('camera_geometry', camera_geometry, ('camera_locations', 'surface', 'camera_index')),
                                ('processing_mask', processing_mask, ('path',))]:
        if config is None:
            continue
        if not str(config.get('provenance', '')).strip():
            raise ValueError(f'{name} requires explicit provenance')
        record = dict(config)
        for field in paths:
            if config.get(field) is not None:
                path = Path(config[field]).resolve()
                stat = path.stat()
                record[field] = str(path)
                record[field + '_identity'] = dict(size_bytes=stat.st_size, modified_time_ns=stat.st_mtime_ns)
        if name == 'camera_geometry':
            for required in ['camera_locations', 'surface', 'height_datum_provenance', 'max_view_zenith_deg']:
                if config.get(required) is None or not str(config[required]).strip():
                    raise ValueError(f'Camera geometry requires {required}')
            policy = config.get('assignment_policy')
            if policy not in {'reviewed_index', 'nearest_camera_scenario'}:
                raise ValueError('Explicit camera assignment_policy required')
            if policy == 'reviewed_index' and not config.get('camera_index'):
                raise ValueError('reviewed_index requires a zero-based camera-row index raster (-1 unknown)')
            if policy == 'nearest_camera_scenario' and not str(config.get('assumption_acknowledgement', '')).strip():
                raise ValueError('Nearest-camera scenario requires an explicit assumption acknowledgement; actual contributors are unknown')
            if not 0 < float(config['max_view_zenith_deg']) < 90:
                raise ValueError('max_view_zenith_deg must be strictly between 0 and 90')
            record['camera_sha256'] = file_sha256(config['camera_locations'])
        else:
            if 'keep_value' not in config or 'allowed_values' not in config:
                raise ValueError('Processing mask requires explicit keep_value and allowed_values')
            if config['keep_value'] not in config['allowed_values']:
                raise ValueError('keep_value must belong to allowed_values')
        result[name] = record
    return result


def apply_campaign_inputs(working_h5, *, camera_geometry=None, processing_mask=None):
    """Persist declared per-pixel views/exclusions on a derived H5, without pixel repairs.

    Surface and camera heights must share the caller-declared vertical datum.
    A reviewed index addresses original CSV row numbers. The optional nearest
    scenario uses positions only and is labelled as an assumption in every audit.
    """
    if camera_geometry is None and processing_mask is None:
        return
    import h5py
    import rasterio
    from affine import Affine
    from contextlib import ExitStack
    from pyproj import CRS, Transformer
    from scipy.spatial import cKDTree
    from .drone_view_geometry import read_metashape_camera_locations
    from .pipelines.drone import _find_drone_reflectance_dataset, _drone_grid_transforms_match
    from .io.neon import _prepare_map_info, _shift_map_info_for_window

    identity = campaign_input_identity(camera_geometry, processing_mask)
    with h5py.File(working_h5, 'r') as h:
        source = _find_drone_reflectance_dataset(h)
        coord = source.parent['Metadata/Coordinate_System']
        info = _prepare_map_info(coord['Map_Info'][()])
        _, spatial, _, _ = _shift_map_info_for_window(
            info, corner_reference=coord.attrs.get('spatial_reference_convention') == 'envi_corner_v1')
        projection = coord['Coordinate_System_String'][()]
        projection = projection.decode() if isinstance(projection, bytes) else str(projection)
        # The working-copy converter's established contract is lines/samples/bands.
        if source.ndim != 3 or source.shape[-1] != len(source.parent['Metadata/Spectral_Data/Wavelength']):
            raise ValueError('Camera integration requires the declared lines/samples/bands working-H5 layout')
        shape = source.shape[:2]
    transform = Affine.from_gdal(*spatial)
    crs = CRS.from_user_input(projection)
    if not crs.is_projected or any(axis.unit_name.lower() not in {'metre', 'meter'} for axis in crs.axis_info[:2]):
        raise ValueError('Camera geometry requires a projected metre source grid')
    with ExitStack() as stack:
        rasters = {}
        if camera_geometry is not None:
            for field in ['surface', 'camera_index']:
                if camera_geometry.get(field):
                    rasters[field] = stack.enter_context(rasterio.open(camera_geometry[field]))
        if processing_mask is not None:
            rasters['mask'] = stack.enter_context(rasterio.open(processing_mask['path']))
        for name, raster in rasters.items():
            if raster.count != 1 or raster.shape != shape or CRS.from_user_input(raster.crs) != crs or not _drone_grid_transforms_match(transform, raster.transform, shape):
                raise ValueError(f'{name} must match the source grid exactly; no implicit resampling')
        if camera_geometry is not None:
            photos, camera_meta = read_metashape_camera_locations(
                camera_geometry['camera_locations'], crs_override=camera_geometry.get('crs_override'),
                crs_override_provenance=camera_geometry.get('crs_override_provenance'))
            converter = Transformer.from_crs(camera_meta['adopted_crs'], crs, always_xy=True)
            cx, cy = converter.transform(photos.X.to_numpy(), photos.Y.to_numpy())
            positions = np.c_[cx, cy, photos.Z.to_numpy()]
            tree = cKDTree(positions[:, :2])
            to_geo = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True)
            geod = crs.get_geod()
        with h5py.File(working_h5, 'r+') as h:
            ds = _find_drone_reflectance_dataset(h)
            group = ds.parent.require_group('Metadata')
            name = 'Campaign_Keep_Mask'
            if name in group:
                del group[name]
            keep = group.create_dataset(name, shape=shape, dtype='uint8', chunks=True, compression='gzip')
            angles = {}
            if camera_geometry is not None:
                # Replace every recognized legacy alias so reader ordering cannot
                # accidentally select inherited constant placeholders.
                aliases = {'to_sensor_zenith_angle': 'zn', 'sensor_zenith_angle': 'zn', 'sensor_zn': 'zn',
                           'to_sensor_azimuth_angle': 'az', 'sensor_azimuth_angle': 'az', 'sensor_az': 'az'}
                delete = []
                group.visititems(lambda key, obj: delete.append(key) if isinstance(obj, h5py.Dataset) and key.split('/')[-1].lower().replace('-', '_') in aliases else None)
                for key in delete:
                    del group[key]
                for key, name in [('zn', 'to-sensor_Zenith_Angle'), ('az', 'to-sensor_Azimuth_Angle')]:
                    angles[key] = group.create_dataset(name, shape=shape, dtype='float32', chunks=True, compression='gzip')
                    angles[key].attrs['Units'] = 'degrees'
            valid_count = 0
            rows = max(1, min(128, 262144 // max(1, shape[1])))
            for start in range(0, shape[0], rows):
                end = min(shape[0], start + rows)
                window = rasterio.windows.Window(0, start, shape[1], end - start)
                retained = np.ones((end - start, shape[1]), bool)
                if processing_mask is not None:
                    mask = rasters['mask'].read(1, window=window, masked=True)
                    raw = np.asarray(mask.data)
                    if not np.isin(raw[~np.ma.getmaskarray(mask)], processing_mask['allowed_values']).all():
                        raise ValueError('Processing mask contains undeclared codes')
                    retained &= ~np.ma.getmaskarray(mask) & (raw == processing_mask['keep_value'])
                if camera_geometry is not None:
                    surface = rasters['surface'].read(1, window=window, masked=True)
                    rr, cc = np.mgrid[start:end, :shape[1]]
                    x, y = transform * (cc + 0.5, rr + 0.5)
                    if 'camera_index' in rasters:
                        index_data = rasters['camera_index'].read(1, window=window, masked=True).astype('float64')
                        values = np.asarray(index_data.filled(-1))
                        if not np.isfinite(values).all() or np.any(values != np.floor(values)) or np.any((values < -1) | (values >= len(positions))):
                            raise ValueError('Camera index must contain original zero-based CSV rows or -1')
                        indices = values.astype(int)
                    else:
                        indices = tree.query(np.c_[x.ravel(), y.ravel()], k=1, workers=1)[1].reshape(x.shape)
                    chosen = positions[np.maximum(indices, 0)]
                    dx, dy = chosen[..., 0] - x, chosen[..., 1] - y
                    dz = chosen[..., 2] - np.asarray(surface.data)
                    zenith = np.rad2deg(np.arctan2(np.hypot(dx, dy), dz))
                    lon, lat = to_geo.transform(x, y)
                    north_lon, north_lat = to_geo.transform(x, y + 10.0)
                    rotation = np.asarray(geod.inv(lon, lat, north_lon, north_lat)[0])
                    azimuth = (np.rad2deg(np.arctan2(dx, dy)) + rotation) % 360
                    good = (indices >= 0) & ~np.ma.getmaskarray(surface) & np.isfinite(dz) & (dz > 0)
                    good &= np.isfinite(zenith) & np.isfinite(azimuth) & (zenith <= float(camera_geometry['max_view_zenith_deg']))
                    retained &= good
                    angles['zn'][start:end] = np.where(good, zenith, np.nan).astype('float32')
                    angles['az'][start:end] = np.where(good, azimuth, np.nan).astype('float32')
                keep[start:end] = retained
                valid_count += int(retained.sum())
                print(f'[drone] camera/mask rows {end}/{shape[0]}', flush=True)
            if not valid_count:
                raise ValueError('Camera/processing mask leaves no eligible pixels')
            audit = dict(schema_version=1, inputs=identity, keep_mask_path=keep.name,
                         retained_pixels=valid_count, total_pixels=int(np.prod(shape)),
                         actual_mosaic_contributors='REVIEWED_INDEX' if camera_geometry and camera_geometry['assignment_policy'] == 'reviewed_index' else 'UNKNOWN',
                         interpretation='Declared operational geometry; not independent reflectance validation')
            if camera_geometry is not None:
                audit['camera_metadata'] = camera_meta
            ds.attrs['spectralbridge_campaign_inputs'] = json.dumps(audit, sort_keys=True)


def bind_campaign_cube(cube):
    """Attach persisted exclusion policy to the existing cube's chunk validity."""
    import h5py
    from .pipelines.drone import _find_drone_reflectance_dataset
    with h5py.File(cube.h5_path, 'r') as h:
        ds = _find_drone_reflectance_dataset(h)
        value = ds.attrs.get('spectralbridge_campaign_inputs')
        if value is None:
            return None
        audit = json.loads(value)
        keep = h[audit['keep_mask_path']][:].astype(bool)
    cube.mask_no_data &= keep
    original = getattr(cube, 'source_valid_mask', None)
    cube.source_valid_mask = keep if original is None else original & keep
    cube.campaign_inputs = audit
    return audit

def brightness_record(value):
    """Load one compact calibration declaration; never modify the provider file."""
    return dict(value) if isinstance(value, dict) else json.loads(Path(value).read_text())


def apply_working_brightness(working_h5, source_path, *, flight_id, calibration):
    """Bind actual source bytes and compose calibration on a derived copy only."""
    import h5py
    from .radiometry import dataset_radiometry
    from .pipelines.drone import _find_drone_reflectance_dataset

    record = brightness_record(calibration)
    source_digest = file_sha256(source_path)
    with h5py.File(working_h5, 'r+') as h:
        ds = _find_drone_reflectance_dataset(h)
        original = dataset_radiometry(ds).record()
        waves = ds.parent['Metadata/Spectral_Data/Wavelength'][:]
        composed = compose_brightness_calibration(
            record, flight_id=flight_id, source_sha256=source_digest,
            wavelengths_nm=waves, source_radiometry=original)
        if 'spectralbridge_source_encoding' in ds.attrs:
            ds.attrs['spectralbridge_previous_source_encoding'] = ds.attrs['spectralbridge_source_encoding']
        ds.attrs['spectralbridge_previous_radiometry'] = json.dumps(original)
        # Declare the new composed affine explicitly, retaining the original
        # decoding in provenance instead of leaving contradictory active scales.
        declaration = dict(schema_version=1, input_encoding='explicit_calibrated_affine',
                           verification_status='VERIFIED_ENCODING', processing_state='calibrated_reflectance',
                           scale=composed['scale'], offset=composed['offset'],
                           provenance=composed['provenance'], wavelengths_nm=np.asarray(waves).tolist())
        ds.attrs['spectralbridge_source_encoding'] = json.dumps(declaration)
        ds.attrs['spectralbridge_radiometry'] = json.dumps(composed)
        ds.attrs['spectralbridge_brightness_calibration'] = json.dumps(record, sort_keys=True)
