"""Experimental nadir-camera geometry; never asserts mosaic contributors.

Coordinates must be in a common projected metre grid. The caller must explicitly
supply the grid-north to true-north rotation and declare the height datum scenario.
No pipeline defaults, calibration records, BRDF equations or acceptance gates are
changed by this opt-in module. Memory scales with ground chunk size times cameras.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class NadirFootprint:
    """Undistorted rectangular pinhole scenario, not a recovered visibility mask.

    The reported Goldhill dimensions are defaults only when supplied explicitly
    by the caller. ``heading_rad`` elsewhere is along image height; width lies
    across that heading. Terrain height is evaluated at each candidate target.
    """

    width_px: int
    height_px: int
    focal_mm: float
    pixel_um: float
    size_multiplier: float = 1.0

    def __post_init__(self):
        values = [
            self.width_px,
            self.height_px,
            self.focal_mm,
            self.pixel_um,
            self.size_multiplier,
        ]
        if not np.all(np.isfinite(values)) or np.any(np.asarray(values) <= 0):
            raise ValueError(
                "Footprint dimensions and scale must be finite and positive"
            )

    @property
    def half_tangents(self):
        return (
            np.asarray([self.width_px, self.height_px], float)
            * self.pixel_um
            * 0.001
            / (2 * self.focal_mm)
            * self.size_multiplier
        )


def camera_rays(ground_xyz, camera_xyz, *, grid_to_true_deg):
    """Return ground-to-sensor zenith and clockwise true-north azimuth radians.

    The camera-to-ground horizontal vector has the opposite azimuth. The shared
    BRDF contract uses *to sensor*, so that vector is reversed here. At nadir the
    azimuth is defined as zero (irrelevant to the validated nadir kernel).
    Invalid/at-or-below-surface cameras yield NaNs, never neutral-view repairs.
    """
    ground = np.asarray(ground_xyz, dtype=float)
    cameras = np.asarray(camera_xyz, dtype=float)
    if (
        ground.ndim != 2
        or cameras.ndim != 2
        or ground.shape[1] != 3
        or cameras.shape[1] != 3
    ):
        raise ValueError("Ground and cameras must have shape (n,3), projected metres")
    rotation = np.broadcast_to(np.asarray(grid_to_true_deg, float), (len(ground),))
    delta = cameras[None, :, :] - ground[:, None, :]
    distance = np.hypot(delta[..., 0], delta[..., 1])
    valid = (
        np.isfinite(delta).all(-1)
        & (delta[..., 2] > 0)
        & np.isfinite(rotation[:, None])
    )
    zenith = np.arctan2(distance, delta[..., 2])
    azimuth = (
        np.arctan2(delta[..., 0], delta[..., 1]) + np.deg2rad(rotation[:, None])
    ) % (2 * np.pi)
    azimuth = np.where(distance == 0, 0.0, azimuth)
    return np.where(valid, zenith, np.nan), np.where(valid, azimuth, np.nan), delta


def footprint_candidates(delta, heading_rad, footprint):
    """Return rectangular target visibility and normalized centrality scenario.

    No occlusion, distortion, recovered yaw, seamline or blending is asserted.
    Heading is clockwise from grid north and belongs to the camera's image-height
    axis. Rotating by ninety degrees is a separate footprint sensitivity case.
    """
    delta = np.asarray(delta, float)
    heading = np.asarray(heading_rad, float)
    across = delta[..., 0] * np.cos(heading) - delta[..., 1] * np.sin(heading)
    along = delta[..., 0] * np.sin(heading) + delta[..., 1] * np.cos(heading)
    half = footprint.half_tangents
    height = delta[..., 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        centrality = np.maximum(
            abs(across) / (height * half[0]), abs(along) / (height * half[1])
        )
    valid = (
        np.isfinite(delta).all(-1)
        & np.isfinite(centrality)
        & (height > 0)
        & (centrality <= 1)
    )
    return valid, np.where(valid, centrality, np.inf)


def assign_camera(delta, eligible, centrality, *, rule):
    """A nearest eligible or B most-central eligible; stable input-order ties.

    Returns -1 where unsupported. Camera order must already be deterministic.
    No reflectance is read when assigning cameras.
    """
    if rule == "nearest":
        score = np.hypot(delta[..., 0], delta[..., 1])
    elif rule == "central":
        score = centrality
    else:
        raise ValueError("rule must be nearest or central")
    score = np.where(eligible, score, np.inf)
    index = np.argmin(score, axis=1)
    return np.where(np.any(eligible, axis=1), index, -1)


def aggregate_kernels(volume, geometry, eligible, *, centrality=None):
    """One simulated blended design per ground observation, never duplicated rho.

    Uniform or Gaussian centrality weights are sensitivity assumptions, never
    recovered mosaic weights. Individual kernels must come from the shared
    validated BRDF implementation; this routine performs only linear reduction.
    """
    good = np.asarray(eligible, bool) & np.isfinite(volume) & np.isfinite(geometry)
    weights = good.astype(float)
    if centrality is not None:
        weights *= np.exp(-2 * np.minimum(np.asarray(centrality), 1e100) ** 2)
    total = weights.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        kv = np.where(
            total > 0,
            np.sum(np.where(good, volume, 0) * weights, axis=1) / total,
            np.nan,
        )
        kg = np.where(
            total > 0,
            np.sum(np.where(good, geometry, 0) * weights, axis=1) / total,
            np.nan,
        )
    return np.stack([np.ones_like(kv), kv, kg], axis=-1)


def read_metashape_camera_locations(
    path, *, crs_override=None, crs_override_provenance=None
):
    """Read an explicit Metashape camera export without relabeling its source.

    Parameters
    ----------
    path : str or Path
        CSV containing a ``CRS,<EPSG>`` preamble, a declared camera-row count,
        and ``# PhotoID,X,Y,Z,Omega,Phi,Kappa,r11,...,r33`` column names. Photo
        rows may share a position; they must have unique identifiers.
    crs_override : str or int, optional
        Explicit interpretation of the numeric XY columns, never a coordinate
        transformation or source edit. A different CRS requires evidence below.
    crs_override_provenance : str, optional
        Nonempty independent source/reason for an override, retained verbatim.

    Returns
    -------
    tuple
        Photo DataFrame and metadata with source hash, declared/adopted CRS,
        counts and rotation checks. Coordinates require a projected metre CRS.
        Orthogonal matrices do not establish their camera/world convention.
        Physical radiometry, timestamps, vertical datum and actual orthomosaic
        contributors are not certified by reading this file.
    """
    import csv
    import hashlib
    from pathlib import Path
    import re

    import pandas as pd
    from pyproj import CRS

    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.reader(source))
    if len(rows) < 4 or len(rows[0]) < 2 or rows[0][0].strip() != "CRS":
        raise ValueError("Expected Metashape CRS preamble before camera columns")
    declared = CRS.from_user_input(rows[0][1].strip())
    count = re.fullmatch(r"#\s*Cameras\s*\((\d+)\)", rows[1][0].strip())
    if count is None or rows[2][0].strip() != "# PhotoID":
        raise ValueError("Expected camera count followed by # PhotoID header")
    photos = pd.read_csv(path, skiprows=2, skipinitialspace=True, encoding="utf-8-sig")
    photos.columns = photos.columns.str.lstrip("#").str.strip()
    required = ["PhotoID", "X", "Y", "Z", "Omega", "Phi", "Kappa"] + [
        f"r{i}{j}" for i in range(1, 4) for j in range(1, 4)
    ]
    missing = sorted(set(required) - set(photos.columns))
    if missing:
        raise ValueError("Camera table missing columns: " + ", ".join(missing))
    if len(photos) != int(count[1]) or photos.empty:
        raise ValueError("Camera row count differs from declared count or is empty")
    if photos.PhotoID.isna().any():
        raise ValueError("Camera identifiers cannot be missing")
    photos["PhotoID"] = photos.PhotoID.astype(str).str.strip()
    if photos.PhotoID.eq("").any() or photos.PhotoID.duplicated().any():
        raise ValueError("Camera identifiers must be nonempty and unique")
    for name in required[1:]:
        photos[name] = pd.to_numeric(photos[name], errors="coerce")
    if not np.isfinite(photos[required[1:]].to_numpy()).all():
        raise ValueError("Camera positions, angles and rotations must all be finite")
    rotations = photos[required[7:]].to_numpy().reshape(-1, 3, 3)
    orthogonality = np.max(
        np.abs(rotations @ rotations.transpose(0, 2, 1) - np.eye(3))
    )
    determinants = np.linalg.det(rotations)
    # Text exports round individual matrix elements; tolerate serialization only.
    if orthogonality > 1e-6 or not np.allclose(determinants, 1, atol=1e-6, rtol=0):
        raise ValueError("Camera rotations are not proper orthogonal matrices")
    adopted = CRS.from_user_input(crs_override) if crs_override is not None else declared
    overridden = adopted != declared
    if overridden and (
        not isinstance(crs_override_provenance, str)
        or not crs_override_provenance.strip()
    ):
        raise ValueError("CRS override requires explicit independent evidence/provenance")
    if not adopted.is_projected or any(
        axis.unit_name.lower() not in {"metre", "meter"} for axis in adopted.axis_info[:2]
    ):
        raise ValueError("Camera coordinates require a projected metre CRS")
    metadata = dict(
        path=str(path),
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        declared_crs=declared.to_string(),
        adopted_crs=adopted.to_string(),
        crs_overridden=overridden,
        crs_override_provenance=crs_override_provenance if overridden else None,
        photo_rows=len(photos),
        distinct_positions=len(photos[["X", "Y", "Z"]].drop_duplicates()),
        maximum_rotation_orthogonality_error=float(orthogonality),
        rotation_determinant_range=[float(determinants.min()), float(determinants.max())],
        orientation_convention="UNVERIFIED",
        vertical_datum="UNVERIFIED",
        timestamps="NOT_PRESENT_IN_THIS_CONTRACT",
        actual_contributors="UNVERIFIED",
    )
    return photos, metadata
