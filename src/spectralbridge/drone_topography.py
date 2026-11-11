"""Experimental terrain/illumination research; production defaults are unchanged.

SCS+C/C-correction require a positive, uncertainty-resolved denominator. Minnaert
is a separately named model with different assumptions, never an identity fallback.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from .corrections import calc_cosine_i
from .topographic import cluster_covariance, fieller_interval, SCSCPolicy


def terrain_geometry(elevation, *, pixel_size, smoothing_sigma_m=0.0):
    """North-up metric DEM derivatives; aspect is downslope clockwise from north.

    Smoothing is normalized only over observed cells; original holes and a
    derivative edge around them remain unavailable rather than being infilled.
    Sigma is a declared physical scale, not a fitted model parameter.
    """
    z = np.asarray(elevation, float)
    if z.ndim != 2 or min(z.shape) < 3 or pixel_size <= 0 or smoothing_sigma_m < 0:
        raise ValueError(
            "North-up 2-D DEM, positive metric pixel size and nonnegative sigma required"
        )
    valid = np.isfinite(z)
    if smoothing_sigma_m:
        sigma = smoothing_sigma_m / pixel_size
        weights = gaussian_filter(valid.astype(float), sigma, mode="nearest")
        smoothed = gaussian_filter(
            np.where(valid, z, 0.0), sigma, mode="nearest"
        ) / np.maximum(weights, 1e-30)
        z = np.where(valid, smoothed, np.nan)
    south, east = np.gradient(z, pixel_size, pixel_size)
    slope = np.rad2deg(np.arctan(np.hypot(east, south)))
    aspect = np.rad2deg(np.arctan2(-east, south)) % 360
    curvature = sum(
        np.gradient(g, pixel_size, axis=axis) for axis, g in enumerate([south, east])
    )
    local_mean = gaussian_filter(
        np.where(valid, elevation, 0.0), max(1.0, 1 / pixel_size), mode="nearest"
    )
    local_weight = gaussian_filter(
        valid.astype(float), max(1.0, 1 / pixel_size), mode="nearest"
    )
    roughness = np.where(
        valid,
        np.asarray(elevation) - local_mean / np.maximum(local_weight, 1e-30),
        np.nan,
    )
    return dict(
        elevation=z,
        slope_deg=slope,
        aspect_deg=aspect,
        curvature=curvature,
        roughness=roughness,
        valid=valid & np.isfinite(slope),
    )


def solar_incidence(slope_deg, aspect_deg, solar_zenith_deg, solar_azimuth_deg):
    """Shared package incidence formula, explicit degree inputs and broadcast shape."""
    arrays = np.broadcast_arrays(
        slope_deg, aspect_deg, solar_zenith_deg, solar_azimuth_deg
    )
    shape = arrays[0].shape
    slope, aspect, sz, sa = [np.deg2rad(a).reshape(-1, 1) for a in arrays]
    if np.any((slope < 0) | (slope >= np.pi / 2)) or np.any(
        (sz < 0) | (sz >= np.pi / 2)
    ):
        raise ValueError("Slope and solar zenith must be in [0,90) degrees")
    return calc_cosine_i(sz, sa, aspect, slope).reshape(shape)


def solar_visibility(
    x,
    y,
    height,
    *,
    solar_zenith_deg,
    solar_azimuth_deg,
    sample_surface,
    maximum_distance=100.0,
    step_metres=1.0,
    height_tolerance=0.0,
):
    """Finite-radius geometric sun obstruction; darkness is not used.

    Returns shadow, covered and maximum obstruction. Covered means all sampled
    rays have terrain support inside the declared radius; it does not establish
    absence of obstruction outside that radius. NoData is unknown, not sunlight.
    """
    x, y, height, sz, sa = np.broadcast_arrays(
        x, y, height, solar_zenith_deg, solar_azimuth_deg
    )
    if maximum_distance <= 0 or step_metres <= 0 or np.any((sz <= 0) | (sz >= 90)):
        raise ValueError("Positive radius/step and sun above horizon required")
    az = np.deg2rad(sa)
    rise = 1 / np.tan(np.deg2rad(sz))
    covered = np.isfinite(x + y + height)
    obstruction = np.full(x.shape, -np.inf)
    for distance in np.arange(
        step_metres, maximum_distance + step_metres / 2, step_metres
    ):
        xx = x + np.sin(az) * distance
        yy = y + np.cos(az) * distance
        terrain = np.asarray(sample_surface(xx, yy), float)
        covered &= np.isfinite(terrain)
        obstruction = np.maximum(
            obstruction,
            np.where(np.isfinite(terrain), terrain - height - rise * distance, -np.inf),
        )
    shadow = obstruction > height_tolerance
    return dict(
        shadow=shadow,
        covered=covered,
        obstruction_m=obstruction,
        maximum_distance_m=maximum_distance,
        step_metres=step_metres,
    )


def weighted_cluster_fit(design, response, groups, *, balanced=False):
    """OLS or equal-spatial-block WLS with fixed-weight cluster covariance."""
    X, y, groups = (
        np.asarray(design, float),
        np.asarray(response, float),
        np.asarray(groups),
    )
    if (
        X.ndim != 2
        or y.shape != (len(X),)
        or groups.shape != y.shape
        or not np.isfinite(X).all()
        or not np.isfinite(y).all()
    ):
        raise ValueError("Finite matched design/response/spatial groups required")
    _, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    weights = 1 / counts[inverse] if balanced else np.ones(len(y))
    root = np.sqrt(weights)
    beta, _, rank, s = np.linalg.lstsq(X * root[:, None], y * root, rcond=None)
    if rank != X.shape[1] or s[0] / s[-1] > 1 / np.sqrt(np.finfo(np.float32).eps):
        raise ValueError("Regression rank/conditioning unsupported")
    residual = y - X @ beta
    covariance, n = cluster_covariance(X * root[:, None], residual * root, groups)
    return dict(
        beta=beta,
        covariance=covariance,
        residual=residual,
        groups=n,
        condition=float(s[0] / s[-1]),
        leverage=np.sum(
            np.linalg.qr(X * root[:, None], mode="reduced")[0] ** 2, axis=1
        ),
    )


def fit_topographic_model(
    incidence,
    response,
    groups,
    *,
    method="scsc",
    balanced=False,
    robust=False,
    policy=None,
):
    """Fit declared correction model with source-domain and uncertainty evidence.

    Robust Huber fits use a cluster-sandwich estimating-equation covariance;
    they are experimental sensitivities. No coefficient sign is constrained.
    """
    from scipy.optimize import least_squares

    policy = policy or SCSCPolicy()
    x, y, groups = (
        np.asarray(incidence, float),
        np.asarray(response, float),
        np.asarray(groups),
    )
    good = np.isfinite(x) & np.isfinite(y) & (x > 0) & (y >= policy.rho_min)
    if policy.rho_max is not None:
        good &= y <= policy.rho_max
    if method == "minnaert":
        good &= y > 0
    if good.sum() < 5:
        return dict(
            status="UNSUPPORTED",
            reason="Insufficient valid fitting observations",
            method=method,
        )
    xx, yy, gg = x[good], y[good], groups[good]
    X = np.c_[np.log(xx) if method == "minnaert" else xx, np.ones(len(xx))]
    Y = np.log(yy) if method == "minnaert" else yy
    if method not in {"scsc", "c_correction", "minnaert"}:
        raise ValueError("Unknown topographic model")
    try:
        fit = weighted_cluster_fit(X, Y, gg, balanced=balanced)
        beta, covariance = fit["beta"], fit["covariance"]
        if robust:
            scale = 1.4826 * np.median(
                abs(fit["residual"] - np.median(fit["residual"]))
            )
            if scale <= np.finfo(float).eps:
                scale = np.finfo(float).eps
            result = least_squares(
                lambda b: (X @ b - Y) / scale, beta, loss="huber", f_scale=1.0
            )
            beta = result.x
            u = (Y - X @ beta) / scale
            psi = np.clip(u, -1, 1)
            derivative = (abs(u) <= 1).astype(float)
            bread = X.T @ (X * derivative[:, None])
            if np.linalg.matrix_rank(bread) != 2:
                raise ValueError("Robust estimating equation rank unsupported")
            unique, inverse = np.unique(gg, return_inverse=True)
            scores = np.stack(
                [np.bincount(inverse, weights=X[:, j] * psi) for j in range(2)], axis=1
            )
            influence = np.linalg.solve(bread, scores.T)
            covariance = (
                scale**2
                * len(unique)
                / (len(unique) - 1)
                * (len(Y) - 1)
                / (len(Y) - 2)
                * (influence @ influence.T)
            )
        model = dict(
            status="NUMERICALLY_SUPPORTED",
            method=method,
            n=int(good.sum()),
            beta=beta.tolist(),
            covariance=covariance.tolist(),
            groups=int(fit["groups"]),
            condition=fit["condition"],
            balanced=balanced,
            robust=robust,
            incidence_range=[float(xx.min()), float(xx.max())],
            max_leverage=float(fit["leverage"].max()),
            rmse=float(np.sqrt(np.mean((Y - X @ beta) ** 2))),
            policy=dict(
                min_denominator=policy.min_denominator, confidence_z=policy.confidence_z
            ),
        )
        if fit["groups"] < policy.minimum_clusters:
            model.update(
                status="UNSUPPORTED", reason="Insufficient spatial uncertainty groups"
            )
        if method == "minnaert":
            se = float(np.sqrt(max(0.0, covariance[0, 0])))
            model.update(
                k=float(beta[0]),
                k_interval=[
                    float(beta[0] - policy.confidence_z * se),
                    float(beta[0] + policy.confidence_z * se),
                ],
            )
        else:
            interval = fieller_interval(*beta, covariance, policy.confidence_z)
            model.update(
                C=float(beta[1] / beta[0]) if beta[0] else None, C_interval=interval
            )
            if interval is None:
                model.update(
                    status="UNSUPPORTED",
                    reason="C ratio has unbounded spatial uncertainty",
                )
        return model
    except (ValueError, np.linalg.LinAlgError) as exc:
        return dict(
            status="UNSUPPORTED", reason=str(exc), method=method, n=int(good.sum())
        )


def topographic_factors(
    incidence,
    slope_deg,
    solar_zenith_deg,
    model,
    *,
    geometric_sunlit=None,
    restrict_domain=True,
):
    """Positive resolved domain and exact parameter-endpoint factor uncertainty.

    A finite positive quotient of two negative terms is NOT accepted. Unsupported
    factors remain NaN. Large supported values are preserved without clipping.
    Minnaert's log-power relation has different assumptions from SCS+C.
    """
    ci, slope, sz = np.broadcast_arrays(
        np.asarray(incidence, float),
        np.deg2rad(slope_deg),
        np.deg2rad(solar_zenith_deg),
    )
    shape = ci.shape
    factor = np.full(shape, np.nan)
    low_factor = factor.copy()
    high_factor = factor.copy()
    codes = np.full(shape, 1, np.uint8)
    if model.get("status") != "NUMERICALLY_SUPPORTED":
        return dict(
            factor=factor,
            low=low_factor,
            high=high_factor,
            supported=np.zeros(shape, bool),
            status=codes,
        )
    valid = (
        np.isfinite(ci + slope + sz)
        & (ci > 0)
        & (slope >= 0)
        & (slope < np.pi / 2)
        & (sz >= 0)
        & (sz < np.pi / 2)
    )
    if restrict_domain:
        lo, hi = model["incidence_range"]
        valid &= (ci >= lo) & (ci <= hi)
    if geometric_sunlit is not None:
        valid &= np.broadcast_to(geometric_sunlit, shape)
    method = model["method"]
    if method == "minnaert":
        k = model["k"]
        lo, hi = model["k_interval"]
        base = np.cos(sz) / ci
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            raw = base**k
            ends = np.stack([base**lo, base**hi])
        lower = np.min(ends, axis=0)
        upper = np.max(ends, axis=0)
    else:
        C = model["C"]
        lo, hi = model["C_interval"]
        reference = np.cos(sz) * (np.cos(slope) if method == "scsc" else 1.0)
        valid &= (ci + lo > model["policy"]["min_denominator"]) & (reference + lo > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            raw = (reference + C) / (ci + C)
            ends = np.stack(
                [(reference + lo) / (ci + lo), (reference + hi) / (ci + hi)]
            )
        lower = np.min(ends, axis=0)
        upper = np.max(ends, axis=0)
    valid &= np.isfinite(raw + lower + upper) & (raw > 0) & (lower > 0)
    factor[valid] = raw[valid]
    low_factor[valid] = lower[valid]
    high_factor[valid] = upper[valid]
    codes[valid] = 2
    return dict(
        factor=factor, low=low_factor, high=high_factor, supported=valid, status=codes
    )


def spatial_training_mask(folds, heldout_fold, *, buffer_cells=2):
    """Exclude a held-out spatial region and its declared pixel-cell buffer."""
    from scipy.ndimage import binary_dilation

    folds = np.asarray(folds)
    if folds.ndim != 2 or buffer_cells < 0 or int(buffer_cells) != buffer_cells:
        raise ValueError("2-D folds and a nonnegative integer buffer required")
    test = folds == heldout_fold
    if not test.any():
        raise ValueError("Held-out fold absent")
    return ~binary_dilation(test, iterations=buffer_cells) if buffer_cells else ~test
