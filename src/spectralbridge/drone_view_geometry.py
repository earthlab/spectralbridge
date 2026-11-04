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
