"""Opt-in original-photo research helpers; never called by production pipelines.

Vendor-calibrated values are distinct from raw sensor DN. Target-aware fits are
experimental diagnostics and do not constitute independent physical validation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from . import corrections as c
from .topographic import cluster_covariance


def calibrated_integer_to_fraction(values, *, scale=1 / 32768, offset=0.0):
    """Convert already vendor-calibrated DN, preserving negative and >1 values."""
    if not np.isfinite([scale, offset]).all() or scale <= 0:
        raise ValueError("Explicit finite positive calibrated scale required")
    return np.asarray(values, dtype=np.float64) * scale + offset


def ross_li_design(solar_azimuth, solar_zenith, view_azimuth, view_zenith):
    """Shared production RossThick/LiDenseR kernels; inputs are degrees."""
    args = [
        np.deg2rad(np.asarray(v, float)).reshape(-1, 1)
        for v in (solar_azimuth, solar_zenith, view_azimuth, view_zenith)
    ]
    kv = c.calc_volume_kernel(*args, "RossThick")
    kg = c.calc_geom_kernel(*args, "LiDenseR", b_r=10, h_b=2)
    return np.column_stack([np.ones(np.size(kv)), np.ravel(kv), np.ravel(kg)])


def reference_design():
    """Unchanged 45 degree solar zenith / nadir package reference."""
    return c._reference_design(c.ReferenceGeometry(), c.HYTOOLS_BRDF_KERNEL_CONFIG)


def reference_in_hull(design, reference):
    """Joint kernel-space support, stronger than separate marginal ranges."""
    from scipy.spatial import Delaunay, QhullError

    points = np.asarray(design, float)[:, 1:]
    ref = np.asarray(reference, float)[1:]
    try:
        return bool(Delaunay(points).find_simplex(ref) >= 0)
    except QhullError:
        return False


def fit_target_effects(design, response, target_ids, *, uncertainty_groups=None):
    """Additive target intercepts estimated by within-target residualization.

    Returned angular differences are additive. They must not be interpreted as
    multiplicative correction factors. Cluster covariance uses absorbed-target
    degrees of freedom. Group labels describe dependence, not independence proof.
    """
    X = np.asarray(design, float)
    y = np.asarray(response, float)
    labels, index = np.unique(target_ids, return_inverse=True)
    if (
        X.shape != (len(y), 3)
        or len(index) != len(y)
        or not np.isfinite(X).all()
        or not np.isfinite(y).all()
    ):
        raise ValueError("Finite three-column design and matched targets required")
    counts = np.bincount(index)
    if np.any(counts < 2) or len(y) <= len(labels) + 2:
        raise ValueError(
            "Repeated observations and residual degrees of freedom required"
        )
    means_x = np.stack(
        [np.bincount(index, weights=X[:, j]) / counts for j in (1, 2)], axis=1
    )
    means_y = np.bincount(index, weights=y) / counts
    within_x = X[:, 1:] - means_x[index]
    within_y = y - means_y[index]
    beta, _, rank, singular = np.linalg.lstsq(within_x, within_y, rcond=None)
    condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf")
    if rank != 2 or condition > 1 / np.sqrt(np.finfo(np.float32).eps):
        raise ValueError("Within-target angular design is unsupported")
    alpha = means_y - means_x @ beta
    residual = y - alpha[index] - X[:, 1:] @ beta
    groups = np.asarray(
        target_ids if uncertainty_groups is None else uncertainty_groups
    )
    covariance, n = cluster_covariance(within_x, residual, groups)
    covariance *= (len(y) - 2) / (len(y) - len(labels) - 2)
    return dict(
        angular_beta=beta,
        target_intercepts=alpha,
        target_labels=labels,
        covariance=covariance,
        residual=residual,
        condition=condition,
        groups=n,
        within_design=within_x,
    )


def fit_target_amplitudes(design, response, target_ids):
    """Exploratory shared Ross/Li shape times target-specific amplitude.

    Variable projection fits y_ij = a_i * (1 + b_vol*Kvol + b_geo*Kgeo).
    Fixing the isotropic shape coefficient to one identifies the scale. This is
    a candidate model, not accepted production normalization or uncertainty.
    """
    from scipy.optimize import least_squares

    X = np.asarray(design, float)
    y = np.asarray(response, float)
    labels, index = np.unique(target_ids, return_inverse=True)
    if (
        X.shape != (len(y), 3)
        or len(index) != len(y)
        or not np.isfinite(X).all()
        or not np.isfinite(y).all()
    ):
        raise ValueError("Finite matched design and targets required")
    if np.any(np.bincount(index) < 2):
        raise ValueError("Repeated target observations required")

    def evaluate(beta):
        shape = X @ np.r_[1.0, beta]
        denominator = np.bincount(index, weights=shape * shape)
        if np.any(denominator <= np.finfo(float).tiny):
            raise ValueError("Degenerate target amplitude")
        amplitudes = np.bincount(index, weights=shape * y) / denominator
        return y - amplitudes[index] * shape, amplitudes

    result = least_squares(lambda b: evaluate(b)[0], np.zeros(2), max_nfev=500)
    residual, amplitudes = evaluate(result.x)
    singular = np.linalg.svd(result.jac, compute_uv=False)
    condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf")
    if (
        not result.success
        or np.linalg.matrix_rank(result.jac) != 2
        or condition > 1 / np.sqrt(np.finfo(np.float32).eps)
    ):
        raise ValueError("Target-amplitude angular design is unsupported")
    return dict(
        beta=np.r_[1.0, result.x],
        amplitudes=amplitudes,
        target_labels=labels,
        residual=residual,
        condition=condition,
    )


def apply_supported_factors(
    values, topo_factor, brdf_factor, *, topo_supported, brdf_supported
):
    """Both stages must be supported; failed observations are NaN, never identity."""
    values, topo, brdf, ts, bs = np.broadcast_arrays(
        np.asarray(values, float),
        np.asarray(topo_factor, float),
        np.asarray(brdf_factor, float),
        np.asarray(topo_supported, bool),
        np.asarray(brdf_supported, bool),
    )
    valid = (
        ts
        & bs
        & np.isfinite(values)
        & np.isfinite(topo)
        & np.isfinite(brdf)
        & (topo > 0)
        & (brdf > 0)
    )
    output = np.full(values.shape, np.nan)
    output[valid] = values[valid] * topo[valid] * brdf[valid]
    return output, valid


def prepare_calibrated_orthomosaic(
    source,
    destination,
    *,
    wavelengths_nm,
    source_scale,
    source_offset,
    provenance,
    target_transform,
    target_shape,
):
    """Immutable explicit-scale 10-band+alpha export to float fraction*10000.

    Caller supplies the established processing grid and source calibration.
    Alpha is interpreted by the existing ten-spectral-plus-alpha contract.
    One band is warped at a time; source-invalid pixels cannot bleed into output.
    Restart requires matching input/configuration and output checksum.
    """
    import os
    import rasterio
    from rasterio.warp import reproject, Resampling
    from affine import Affine

    source, destination = Path(source), Path(destination)
    waves = list(map(float, wavelengths_nm))
    if len(waves) != 10 or len(set(waves)) != 10:
        raise ValueError("Ten explicit distinct source wavelengths required")
    if not np.isfinite([source_scale, source_offset]).all() or source_scale <= 0:
        raise ValueError("Explicit source encoding required")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    config = dict(
        source_sha256=digest.hexdigest(),
        wavelengths_nm=waves,
        source_scale=source_scale,
        source_offset=source_offset,
        output_scale=0.0001,
        output_offset=0.0,
        units="reflectance_fraction",
        transform=list(target_transform)[:6],
        shape=list(target_shape),
        resampling="bilinear",
        provenance=provenance,
        schema_version=1,
    )
    sidecar = destination.with_suffix(destination.suffix + ".json")
    if destination.exists() or sidecar.exists():
        if destination.exists() and sidecar.exists():
            saved = json.loads(sidecar.read_text())
            if (
                saved["configuration"] == config
                and hashlib.sha256(destination.read_bytes()).hexdigest()
                == saved["output_sha256"]
                and (
                    "mask_sha256" not in saved
                    or (
                        destination.with_suffix(".tif.msk").exists()
                        and hashlib.sha256(
                            destination.with_suffix(".tif.msk").read_bytes()
                        ).hexdigest()
                        == saved["mask_sha256"]
                    )
                )
            ):
                return saved
        raise FileExistsError(
            "Immutable output exists with incomplete/different provenance"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.tif")
    with rasterio.open(source) as src:
        if src.count != 11 or src.crs is None:
            raise ValueError("Require georeferenced ten-band plus alpha source")
        alpha = src.read(11) > 0
        profile = dict(
            driver="GTiff",
            width=target_shape[1],
            height=target_shape[0],
            count=10,
            dtype="float32",
            crs=src.crs,
            transform=Affine(*list(target_transform)[:6]),
            nodata=np.nan,
            tiled=True,
            compress="deflate",
            predictor=3,
        )
        with rasterio.open(temporary, "w", **profile) as dst:
            valid = np.ones(target_shape, bool)
            for i, nm in enumerate(waves, 1):
                raw = src.read(i).astype(np.float32)
                raw[~alpha] = np.nan
                physical = calibrated_integer_to_fraction(
                    raw, scale=source_scale, offset=source_offset
                )
                result = np.full(target_shape, np.nan, np.float32)
                reproject(
                    physical,
                    result,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=profile["transform"],
                    dst_crs=src.crs,
                    src_nodata=np.nan,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )
                valid &= np.isfinite(result)
                dst.write(result * 10000, i)
                dst.set_band_description(i, f"{nm:g} nm")
            dst.scales = (0.0001,) * 10
            dst.offsets = (0.0,) * 10
            dst.write_mask(valid.astype("uint8") * 255)
            dst.update_tags(
                units="reflectance_fraction",
                source_encoding="vendor_calibrated_integer",
                calibration_status="PROJECT_ENCODING_VERIFIED;INDEPENDENT_ACCURACY_PENDING",
                wavelengths=json.dumps(waves),
                provenance=json.dumps(provenance),
            )
    # Internal GDAL mask is required: a detached temporary .msk would be lost.
    if temporary.with_suffix(".tif.msk").exists():
        os.replace(
            temporary.with_suffix(".tif.msk"), destination.with_suffix(".tif.msk")
        )
    os.replace(temporary, destination)
    saved = dict(
        configuration=config,
        output_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    )
    if destination.with_suffix(".tif.msk").exists():
        saved["mask_sha256"] = hashlib.sha256(
            destination.with_suffix(".tif.msk").read_bytes()
        ).hexdigest()
    sidecar.write_text(json.dumps(saved, indent=2) + "\n")
    return saved


def reconstruct_pixel_geometry(chunk, camera, pixel, absolute_surface, *, api):
    """Adjusted-calibration ray and absolute-surface hit through official API.

    ``absolute_surface`` must be explicitly selected by the caller, never the
    project's active (possibly relative canopy-height) surface. ``api`` is the
    installed Metashape module; this helper does not import or activate it.
    Ground-terrain slope/aspect remains a separate input to correction.
    """
    if camera.transform is None or chunk.crs is None:
        raise ValueError("Aligned camera and project CRS required")
    calibration = camera.calibration
    uv = api.Vector(list(pixel))
    back = calibration.project(calibration.unproject(uv))
    if back is None or (back - uv).norm() > 1:
        raise ValueError("Adjusted calibration fails pixel round trip")
    origin = chunk.transform.matrix.mulp(camera.center)
    direction = chunk.transform.matrix.mulv(
        camera.transform.mulv(calibration.unproject(uv))
    )
    direction = direction / direction.norm()
    start = api.OrthoProjection.transform(
        origin, chunk.crs.geoccs, absolute_surface.projection
    )
    end = api.OrthoProjection.transform(
        origin + direction * 1000, chunk.crs.geoccs, absolute_surface.projection
    )
    hit = absolute_surface.pickPoint(start, end)
    if hit is None:
        return dict(status="NO_ABSOLUTE_SURFACE_INTERSECTION")
    ecef = api.OrthoProjection.transform(
        hit, absolute_surface.projection, chunk.crs.geoccs
    )
    local = chunk.crs.localframe(ecef).mulv(origin - ecef)
    if local.z <= 0:
        raise ValueError("Camera below ground tangent; check source/frame binding")
    zenith = float(np.rad2deg(np.arctan2(np.hypot(local.x, local.y), local.z)))
    azimuth = float(np.rad2deg(np.arctan2(local.x, local.y)) % 360)
    project = chunk.crs.project(ecef)
    internal = chunk.transform.matrix.inv().mulp(ecef)
    projected = camera.project(internal)
    return dict(
        status=(
            "RECONSTRUCTED_INTERNAL_VALIDATION_ONLY"
            if float((projected - uv).norm()) <= 1
            else "UNSUPPORTED_SURFACE_ROUNDTRIP"
        ),
        ground_project=list(project),
        ground_ecef=list(ecef),
        camera_ecef=list(origin),
        ray_ecef=list(direction),
        view_zenith_deg=zenith,
        view_azimuth_deg=azimuth,
        pixel_roundtrip_error=float((projected - uv).norm()),
    )


def intersect_ecef_ray(
    origin,
    direction,
    *,
    to_project,
    sample_height,
    maximum_distance=1000.0,
    step_metres=0.5,
):
    """First bracketed absolute DEM intersection on the actual ECEF ray.

    ``to_project`` maps Nx3 ECEF coordinates to the DEM CRS and ``sample_height``
    bilinearly samples absolute elevation at Nx2 coordinates. Missing surface
    samples before the crossing are unresolved, not treated as empty space.
    The finite step is an explicit surface-resolution/occlusion limitation.
    """
    from scipy.optimize import brentq

    origin = np.asarray(origin, float)
    direction = np.asarray(direction, float)
    if (
        origin.shape != (3,)
        or direction.shape != (3,)
        or not np.isfinite([origin, direction]).all()
        or np.linalg.norm(direction) == 0
    ):
        raise ValueError("Finite ECEF origin and nonzero direction required")
    if maximum_distance <= 0 or step_metres <= 0:
        raise ValueError("Positive intersection range and step required")
    direction = direction / np.linalg.norm(direction)
    distances = np.linspace(
        0, maximum_distance, int(np.ceil(maximum_distance / step_metres)) + 1
    )
    world = np.asarray(to_project(origin + distances[:, None] * direction), float)
    difference = world[:, 2] - np.asarray(sample_height(world[:, :2]), float)
    crossings = np.flatnonzero((difference[:-1] > 0) & (difference[1:] <= 0))
    if not len(crossings):
        return dict(status="NO_BRACKETED_SURFACE_INTERSECTION")
    index = crossings[0]
    if not np.isfinite(difference[: index + 2]).all() or difference[0] <= 0:
        return dict(status="UNSUPPORTED_SURFACE_GAP_OR_ORIGIN")

    def objective(distance):
        point = np.asarray(to_project((origin + distance * direction)[None, :]), float)
        return float(point[0, 2] - np.asarray(sample_height(point[:, :2]))[0])

    distance = brentq(objective, distances[index], distances[index + 1], xtol=1e-7)
    hit = origin + distance * direction
    return dict(
        status="BRACKETED_DEM_INTERSECTION",
        ecef=hit,
        distance_m=float(distance),
        elevation_residual_m=objective(distance),
        step_metres=step_metres,
    )


def write_corrected_photo(
    destination,
    values,
    topographic_factor,
    brdf_factor,
    *,
    topographic_supported,
    brdf_supported,
    provenance,
):
    """Export a new float source plane with both explicit stage masks.

    This low-level experimental writer does not approve a model. Caller must
    supply matched-stage, source-bound factors. No geometry/XMP calibration tags
    are copied: these values are already calibrated fractions. Invalid pixels
    remain NaN plus an explicit mask; the original source image is never opened
    for writing. A licensed mosaic consumer must disable prior calibration.
    """
    import os
    import rasterio

    destination = Path(destination)
    if destination.exists() or destination.with_suffix(".tif.json").exists():
        raise FileExistsError("Corrected source products are immutable")
    required = {
        "project_fingerprint",
        "camera_key",
        "wavelength_nm",
        "matched_processing_stage",
    }
    if not required.issubset(provenance):
        raise ValueError("Source identity and matched-stage provenance required")
    values = np.asarray(values, float)
    if values.ndim != 2:
        raise ValueError("One unwarped source-image plane required")
    output, valid = apply_supported_factors(
        values,
        topographic_factor,
        brdf_factor,
        topo_supported=topographic_supported,
        brdf_supported=brdf_supported,
    )
    if not valid.any():
        raise ValueError("No observations supported by both corrections")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.tif")
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(
            temporary,
            "w",
            driver="GTiff",
            width=values.shape[1],
            height=values.shape[0],
            count=1,
            dtype="float32",
            nodata=np.nan,
            compress="deflate",
        ) as dst:
            dst.write(output.astype("float32"), 1)
            dst.write_mask(valid.astype("uint8") * 255)
            dst.update_tags(
                units="reflectance_fraction",
                already_calibrated="true",
                both_corrections_applied="true",
                provenance=json.dumps(provenance),
            )
    os.replace(temporary, destination)
    record = dict(
        provenance=provenance,
        dimensions=[values.shape[1], values.shape[0]],
        units="reflectance_fraction",
        valid_pixels=int(valid.sum()),
        unsupported_pixels=int((~valid).sum()),
        sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
        calibration_reapplication="MUST_BE_DISABLED_BY_MOSAIC_CONSUMER",
    )
    destination.with_suffix(".tif.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def temporal_minute_groups(timestamps):
    """UTC minute labels without assuming pandas' integer datetime resolution.

    Pandas may parse timestamps as microseconds or nanoseconds. Dividing an
    unqualified integer timestamp by a nanosecond constant collapses real groups.
    """
    import pandas as pd

    return np.asarray(
        pd.DatetimeIndex(pd.to_datetime(timestamps, utc=True)).floor("min").astype(str)
    )
