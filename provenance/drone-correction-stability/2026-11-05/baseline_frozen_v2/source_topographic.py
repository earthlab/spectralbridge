"""Opt-in, uncertainty-resolved SCS+C models using the shared correction ratio.

This adds an explicit experimental acceptance policy. It does not replace the
legacy/default NEON path. Unsupported observations become NoData with a status,
never an identity substitute or a capped gain. Physical validation remains separate
from numerical support. See Soenen et al., DOI10.1109/TGRS.2005.852480.
"""

from dataclasses import asdict, dataclass
import hashlib

import numpy as np

from .radiometry import require_radiometry

POLICY_VERSION = "scsc-fieller-spatial-v1"
MISSING, UNSUPPORTED, CORRECTED = 0, 1, 2


@dataclass(frozen=True)
class SCSCPolicy:
    """Explicit experimental choices; the confidence rule is not field approval."""

    minimum_slope_degrees: float = 5.0
    rho_min: float = 0.0
    rho_max: float | None = 2.0
    confidence_z: float = 1.96
    min_denominator: float = 1e-3
    minimum_clusters: int = 4

    def __post_init__(self):
        if (
            not (0 <= self.minimum_slope_degrees < 90)
            or not np.isfinite(self.confidence_z)
            or self.confidence_z <= 0
        ):
            raise ValueError("Invalid slope or uncertainty policy")
        if (
            not np.isfinite(self.min_denominator)
            or self.min_denominator <= 0
            or self.minimum_clusters < 3
        ):
            raise ValueError(
                "Positive denominator tolerance and at least3clusters required"
            )
        if not np.isfinite(self.rho_min) or (
            self.rho_max is not None
            and (not np.isfinite(self.rho_max) or self.rho_max <= self.rho_min)
        ):
            raise ValueError("Invalid physical fitting interval")


def cluster_covariance(design, residual, groups):
    """Finite-cluster sandwich covariance, conditional on supplied cluster units."""
    X = np.asarray(design, float)
    e = np.asarray(residual, float)
    labels = np.asarray(groups)
    unique, index = np.unique(labels, return_inverse=True)
    if len(unique) <= X.shape[1] or len(X) <= X.shape[1]:
        raise ValueError("Insufficient independent uncertainty groups")
    scores = np.stack(
        [
            np.bincount(index, weights=X[:, j] * e, minlength=len(unique))
            for j in range(X.shape[1])
        ],
        axis=-1,
    )
    bread = np.linalg.inv(X.T @ X)
    correction = len(unique) / (len(unique) - 1) * (len(X) - 1) / (len(X) - X.shape[1])
    result = correction * (bread @ scores.T @ scores @ bread)
    return (result + result.T) / 2, len(unique)


def fieller_interval(slope, intercept, covariance, z):
    """Bounded Fieller interval for C=intercept/slope; no delta-method pole fix."""
    v = np.asarray(covariance, float)
    if v.shape != (2, 2) or not np.isfinite(v).all():
        return None
    a = float(slope)
    b = float(intercept)
    A = a * a - z * z * v[0, 0]
    B = -2 * (a * b - z * z * v[0, 1])
    D = b * b - z * z * v[1, 1]
    disc = B * B - 4 * A * D
    if not np.isfinite(A + disc) or A <= 0 or disc < 0 or a == 0:
        return None
    roots = np.sort(np.array([-B - np.sqrt(disc), -B + np.sqrt(disc)]) / (2 * A))
    return roots.tolist() if np.isfinite(roots).all() else None


def _geometry(cube, window=None):
    from .corrections import calc_cosine_i, _brdf_spatial_mask

    names = ["slope", "aspect", "solar_zn", "solar_az"]
    if window is None:
        angles = [
            np.asarray(cube.get_ancillary(n, radians=True), np.float32) for n in names
        ]
    else:
        y, z, x, w = window
        angles = [
            np.deg2rad(
                np.asarray(cube.get_ancillary(n, radians=False)[y:z, x:w], np.float32)
            )
            for n in names
        ]
    slope, aspect, sz, sa = angles
    valid = _brdf_spatial_mask(cube, window=window)
    valid &= (
        np.isfinite(slope) & np.isfinite(aspect) & np.isfinite(sz) & np.isfinite(sa)
    )
    valid &= (slope >= 0) & (slope < np.pi / 2) & (sz >= 0) & (sz < np.pi / 2)
    ci = calc_cosine_i(sz, sa, aspect, slope)
    reference = np.cos(sz) * np.cos(slope)
    return ci, reference, slope, valid


def _identity(cube):
    cache = getattr(cube, "_conditioned_scsc_identity", None)
    if cache is not None:
        return cache
    h = hashlib.sha256()
    for row in cube.data:
        h.update(np.ascontiguousarray(row).tobytes())
    for name in ["slope", "aspect", "solar_zn", "solar_az"]:
        for row in cube.get_ancillary(name, radians=True):
            h.update(np.ascontiguousarray(row).tobytes())
    from .corrections import _brdf_spatial_mask

    h.update(np.ascontiguousarray(_brdf_spatial_mask(cube)).tobytes())
    h.update(str((cube.data.shape, getattr(cube, "no_data", None))).encode())
    cube._conditioned_scsc_identity = h.hexdigest()
    return cube._conditioned_scsc_identity


def fit_conditioned_scs_c(
    cube, *, policy, uncertainty_groups, fitting_mask=None, provenance=None
):
    """Fit physical per-band SCS+C with explicit source and spatial uncertainty.

    Per-band OLS uses a bounded two-column design. Arrays for one band are live
    at a time; the already-loaded source cube is not duplicated as a full product.
    Uncertainty groups are caller-defined spatial/observational units, not inferred
    independent pixels. The spatial covariance/Fieller interval is a diagnostic
    acceptance rule, not independent calibration or a universal physical criterion.
    """
    from .corrections import _brdf_spatial_mask

    r = require_radiometry(cube)
    if not isinstance(policy, SCSCPolicy):
        raise TypeError("Explicit SCSCPolicy required")
    groups = np.asarray(uncertainty_groups)
    shape = cube.data.shape[:2]
    if groups.shape != shape or not np.issubdtype(groups.dtype, np.integer):
        raise ValueError("Integer uncertainty groups must match the source grid")
    if fitting_mask is None:
        fitmask = np.ones(shape, bool)
    else:
        fitmask = np.asarray(fitting_mask)
        if fitmask.shape != shape or fitmask.dtype != bool:
            raise ValueError("Boolean fitting_mask must match the source grid")
    ci, ref, slope, valid = _geometry(cube)
    eligible = (
        valid
        & fitmask
        & (ci > 0)
        & (slope >= np.deg2rad(policy.minimum_slope_degrees))
        & (groups >= 0)
    )
    model = dict(
        schema_version=1,
        policy_version=POLICY_VERSION,
        policy=asdict(policy),
        source_identity=_identity(cube),
        radiometry=r.record(),
        wavelengths_nm=np.asarray(cube.wavelengths, float).tolist(),
        scientific_validation_status="EXPERIMENTAL",
        fit_provenance=provenance or {},
        uncertainty_method="spatial_cluster_sandwich_and_Fieller",
        source_pixels=int(_brdf_spatial_mask(cube).sum()),
        geometry_eligible=int(eligible.sum()),
        fitting_mask_sha256=hashlib.sha256(
            np.ascontiguousarray(fitmask).tobytes()
        ).hexdigest(),
        uncertainty_groups_sha256=hashlib.sha256(
            np.ascontiguousarray(groups, dtype=np.int64).tobytes()
        ).hexdigest(),
        sampling_grid_shape=list(shape),
        fits=[],
    )
    for band in range(cube.bands):
        stored = cube.data[..., band]
        physical = r.to_physical(stored, band_index=band)
        choose = (
            eligible
            & r.valid_stored(
                stored, band_index=band, nodata=getattr(cube, "no_data", None)
            )
            & np.isfinite(physical)
            & (physical >= policy.rho_min)
        )
        if policy.rho_max is not None:
            choose &= physical <= policy.rho_max
        record = dict(
            band=band,
            n=int(choose.sum()),
            status="UNSUPPORTED",
            C=None,
            C_interval=None,
        )
        model["fits"].append(record)
        if record["n"] < 4:
            record["reason"] = "Insufficient source/illumination support"
            continue
        x = ci[choose].astype(float)
        y = physical[choose].astype(float)
        X = np.c_[x, np.ones(len(x))]
        beta, _, rank, s = np.linalg.lstsq(X, y, rcond=None)
        condition = float(s[0] / s[-1]) if s[-1] > 0 else None
        record.update(
            rank=int(rank),
            condition=condition,
            slope=float(beta[0]),
            intercept=float(beta[1]),
            negative_illumination_slope=bool(beta[0] < 0),
        )
        if (
            rank != 2
            or condition is None
            or condition > 1 / np.sqrt(np.finfo(np.float32).eps)
        ):
            record["reason"] = "Illumination regression rank/conditioning unsupported"
            continue
        try:
            cov, nclusters = cluster_covariance(X, y - X @ beta, groups[choose])
        except (ValueError, np.linalg.LinAlgError) as exc:
            record["reason"] = str(exc)
            continue
        interval = fieller_interval(*beta, cov, policy.confidence_z)
        record.update(
            clusters=nclusters,
            coefficient_covariance=cov.tolist(),
            residual_rmse=float(np.sqrt(np.mean((y - X @ beta) ** 2))),
            fitted_incidence_range=[float(x.min()), float(x.max())],
        )
        if nclusters < policy.minimum_clusters or interval is None:
            record["reason"] = "C ratio has unbounded/unsupported spatial uncertainty"
            continue
        record.update(status="VALID", C=float(beta[1] / beta[0]), C_interval=interval)
    model["validation_status"] = (
        "VALID"
        if all(f["status"] == "VALID" for f in model["fits"])
        else "PARTIAL"
        if any(f["status"] == "VALID" for f in model["fits"])
        else "UNSUPPORTED"
    )
    return model


@dataclass
class SCSCResult:
    values: np.ndarray
    status: np.ndarray
    factors: np.ndarray


def apply_conditioned_scs_c(cube, chunk, ys, ye, xs, xe, *, model):
    """Apply the unchanged shared SCS+C ratio on its resolved positive domain.

    Status0: missing/invalid source or geometry. Status1: valid source but
    unsupported illumination/model. Status2: successfully corrected. No identity
    substitute is returned for unsupported observations. A large but resolved
    positive ratio is retained; there is no gain cap.
    """
    from .corrections import _scs_c_ratio

    r = require_radiometry(cube)
    if np.shape(chunk) != (ye - ys, xe - xs, cube.bands):
        raise ValueError("SCS+C chunk shape does not match its declared source window")
    if model.get("schema_version") != 1 or len(model.get("fits", [])) != cube.bands:
        raise ValueError("Unsupported SCS+C schema or band records")
    for band, fit in enumerate(model["fits"]):
        if fit.get("band") != band:
            raise ValueError("SCS+C band records are reordered")
        if fit.get("status") == "VALID":
            low, high = fit["C_interval"]
            if (
                not np.isfinite([low, high, fit["C"]]).all()
                or not low <= fit["C"] <= high
            ):
                raise ValueError("Invalid SCS+C coefficient uncertainty interval")
    if model.get("policy_version") != POLICY_VERSION or model.get(
        "source_identity"
    ) != _identity(cube):
        raise ValueError("SCS+C model source/policy mismatch")
    if (
        model.get("radiometry") != r.record()
        or model.get("wavelengths_nm") != np.asarray(cube.wavelengths, float).tolist()
    ):
        raise ValueError("SCS+C radiometry or wavelength mismatch")
    policy = SCSCPolicy(**model["policy"])
    ci, ref, slope, valid = _geometry(cube, (ys, ye, xs, xe))
    physical = r.to_physical(chunk)
    quality = r.valid_stored(chunk, nodata=getattr(cube, "no_data", None))
    status = np.zeros(chunk.shape, np.uint8)
    factors = np.full(chunk.shape, np.nan, np.float32)
    corrected = np.full(chunk.shape, np.nan, np.float32)
    for band, fit in enumerate(model["fits"]):
        source = valid & quality[..., band] & np.isfinite(physical[..., band])
        status[..., band][source] = UNSUPPORTED
        if fit["status"] != "VALID":
            continue
        C = fit["C"]
        low, high = fit["C_interval"]
        xmin, xmax = fit["fitted_incidence_range"]
        flat = np.isclose(slope, 0, rtol=0, atol=np.finfo(np.float32).eps)
        # C interval endpoints give exact denominator/numerator extrema. Require
        # the complete interval to stay positive; this is not a gain threshold.
        resolved = (
            source
            & (ci > 0)
            & ((ci >= xmin) & (ci <= xmax) | flat)
            & (ci + low > policy.min_denominator)
            & (ref + low > 0)
        )
        resolved &= np.isfinite(high) & np.isfinite(C)
        ratio = _scs_c_ratio(
            ref[resolved] + C, ci[resolved] + C, min_denom=policy.min_denominator
        )
        corrected[..., band][resolved] = physical[..., band][resolved] * ratio
        factors[..., band][resolved] = ratio
        status[..., band][resolved] = CORRECTED
    output = r.to_stored(corrected)
    output = np.where(
        status == CORRECTED, output, getattr(cube, "no_data", np.nan)
    ).astype(np.float32)
    return SCSCResult(output, status, factors)
