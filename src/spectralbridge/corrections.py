"""BRDF and topographic correction helpers.

Portions of this module are adapted from HyTools. The incidence-angle, Ross/Li
kernel, and BRDF fitting/application lineage is detailed in
``HYTOOLS_PROVENANCE.md``. The SCS+C implementation follows the published method
of Soenen et al. (2005), DOI 10.1109/TGRS.2005.852480; it is classified
separately from the adapted incidence helper.

HyTools: Hyperspectral image processing library
Copyright (C) 2021 University of Wisconsin
Authors named in the relevant source notices: Adam Chlus, Zhiwei Ye, Philip Townsend.
License: GNU General Public License, version 3
Upstream: https://github.com/EnSpec/hytools
Audited revision: 31286d64541791a9815d29443a33726fa4d54031

Modified and extended for SpectralBridge. See ``LICENSE``, ``NOTICE``, and
``HYTOOLS_PROVENANCE.md``. The Ross/Li kernel equations are described by Wanner
et al. (1995), DOI 10.1029/95JD02371, and Lucht et al. (2000), DOI
10.1109/36.841980.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, TYPE_CHECKING

import numpy as np

from .radiometry import require_radiometry
from spectralbridge.paths import normalize_brdf_model_path, scene_prefix_from_dir

__all__ = [
    "calc_cosine_i",
    "calc_volume_kernel",
    "calc_geom_kernel",
    "load_brdf_model",
    "fit_and_save_brdf_model",
    "fit_scs_c_coefficients",
    "apply_topo_correct",
    "apply_brdf_correct",
]

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from .neon_cube import NeonCube


_BRDF_COEFF_CACHE: dict[Path, dict[str, np.ndarray | str]] = {}
MAX_UNITLESS_REFLECTANCE = 1.2
MIN_SCS_C_DENOM = 1e-3
logger = logging.getLogger(__name__)


@dataclass
class NDVIBinningConfig:
    """Configuration for NDVI binning used during BRDF fitting and application."""

    enabled: bool = False
    ndvi_min: float = 0.05
    ndvi_max: float = 1.0
    n_bins: int = 25
    perc_min: float | None = 10.0
    perc_max: float | None = 95.0


@dataclass
class ReferenceGeometry:
    """Reference geometry (degrees) for BRDF normalization."""

    solar_zenith_deg: float = 45.0
    view_zenith_deg: float = 0.0
    relative_azimuth_deg: float = 0.0


@dataclass
class BRDFKernelConfig:
    """Kernel and geometry settings for BRDF fitting/application.

    Defaults preserve the streamlined implementation's historical behaviour.
    Pipelines that want closer HyTools-style kernel parity should pass an
    explicit config.
    """

    volume_kernel: str = "RossThick"
    geom_kernel: str = "LiSparseReciprocal"
    b_r: float = 1.0
    h_b: float = 2.0
    solar_zn_type: str = "pixel"


HYTOOLS_BRDF_KERNEL_CONFIG = BRDFKernelConfig(
    volume_kernel="RossThick",
    geom_kernel="LiDenseR",
    b_r=10.0,
    h_b=2.0,
    solar_zn_type="scene",
)


def log_stats(name: str, arr: np.ndarray, mask: np.ndarray | None = None) -> None:
    """Log min/max and validity fractions for quick debugging."""

    if mask is None:
        mask = np.ones_like(arr, dtype=bool)
    finite = np.isfinite(arr) & mask
    if finite.size == 0:
        logger.debug("%s: empty array", name)
        return
    fraction_valid = np.count_nonzero(finite) / finite.size
    if np.count_nonzero(finite) == 0:
        logger.debug("%s: all non-finite (mask fraction=%.5f)", name, fraction_valid)
        return
    subset = arr[finite]
    logger.debug(
        "%s: min=%.6f max=%.6f valid_fraction=%.5f",
        name,
        float(np.nanmin(subset)),
        float(np.nanmax(subset)),
        fraction_valid,
    )


def _scs_c_ratio(
    numerator: np.ndarray,
    denominator: np.ndarray,
    min_denom: float = MIN_SCS_C_DENOM,
) -> np.ndarray:
    """Internal helper applying the SCS+C denominator guard.

    Denominators below ``min_denom`` are forced to a neutral ratio of 1.0 to
    avoid exploding corrections. Non-finite or non-positive ratios are also
    forced to 1.0 so topographic correction cannot invent negative reflectance
    that BRDF later collapses to no-data. Caller is responsible for any logging.
    """

    ratio = np.ones_like(numerator, dtype=np.float32)
    valid = denominator > min_denom
    candidate = np.full_like(numerator, np.nan, dtype=np.float32)
    candidate[valid] = (numerator[valid] / denominator[valid]).astype(np.float32)
    keep = valid & np.isfinite(candidate) & (candidate > 0.0)
    ratio[keep] = candidate[keep]
    return ratio


def load_brdf_model(flightline_dir: Path) -> dict:
    """Load the BRDF model JSON for ``flightline_dir`` after normalizing its name."""

    flightline_dir = Path(flightline_dir)
    prefix = scene_prefix_from_dir(flightline_dir)
    preferred = flightline_dir / f"{prefix}_brdf_model.json"
    actual = normalize_brdf_model_path(flightline_dir) or preferred
    if not actual.exists():
        raise FileNotFoundError(
            f"BRDF model not found for {prefix}: expected {preferred.name}"
        )
    return json.loads(actual.read_text(encoding="utf-8"))


def _validate_angles(*arrays: np.ndarray) -> Tuple[np.ndarray, ...]:
    """Ensure all angle arrays are float32 with matching shapes."""

    cast_arrays: list[np.ndarray] = []
    reference_shape: Tuple[int, ...] | None = None
    for array in arrays:
        if array.ndim != 2:
            raise ValueError(
                "Angle ancillary rasters must be 2-D arrays with shape (Y, X)."
            )
        if reference_shape is None:
            reference_shape = array.shape
        elif array.shape != reference_shape:
            raise ValueError(
                "All ancillary rasters must share the same shape."
            )
        cast_arrays.append(array.astype(np.float32, copy=False))
    return tuple(cast_arrays)  # type: ignore[return-value]


def _select_band_for_wavelength(cube: "NeonCube", target_nm: float) -> int:
    """Return the band index closest to ``target_nm``."""

    diffs = np.abs(np.asarray(cube.wavelengths, dtype=np.float32) - np.float32(target_nm))
    return int(np.argmin(diffs))


def _normalize_volume_kernel_name(kernel_type: str) -> str:
    kernel_lower = str(kernel_type).lower().replace("-", "_")
    if kernel_lower in {"rossthick", "ross_thick"}:
        return "RossThick"
    raise NotImplementedError(
        f"Volume kernel '{kernel_type}' is not implemented in cross-sensor-cal."
    )


def _normalize_geom_kernel_name(kernel_type: str) -> str:
    kernel_lower = str(kernel_type).lower().replace("-", "_")
    if kernel_lower in {
        "lisparsereciprocal",
        "li_sparse_reciprocal",
        "li_sparse",
    }:
        return "LiSparseReciprocal"
    if kernel_lower in {
        "lidenser",
        "li_dense_r",
        "li_dense",
    }:
        return "LiDenseR"
    raise NotImplementedError(
        f"Geometric kernel '{kernel_type}' is not implemented in cross-sensor-cal."
    )


def _default_geom_params(kernel_type: str) -> tuple[float, float]:
    normalized = _normalize_geom_kernel_name(kernel_type)
    if normalized == "LiDenseR":
        return 10.0, 2.0
    return 1.0, 2.0


def _resolve_scene_solar_zenith(
    solar_zn: np.ndarray,
    valid_mask: np.ndarray | None = None,
) -> np.ndarray:
    finite = np.isfinite(solar_zn)
    if valid_mask is not None:
        finite &= valid_mask
    if not np.any(finite):
        return solar_zn.astype(np.float32, copy=False)
    scene_mean = np.float32(np.nanmean(solar_zn[finite], dtype=np.float64))
    return np.full_like(solar_zn, scene_mean, dtype=np.float32)


def compute_ndvi(
    cube: "NeonCube",
    data_unitless: np.ndarray,
    red_target_nm: float = 665.0,
    nir_target_nm: float = 865.0,
) -> np.ndarray:
    """Compute NDVI from unitless reflectance data."""

    red_idx = _select_band_for_wavelength(cube, red_target_nm)
    nir_idx = _select_band_for_wavelength(cube, nir_target_nm)
    red = data_unitless[..., red_idx]
    nir = data_unitless[..., nir_idx]
    denom = nir + red
    ndvi = (nir - red) / np.where(np.abs(denom) > 1e-6, denom, np.nan)
    return ndvi.astype(np.float32)


def compute_ndvi_bins(ndvi: np.ndarray, config: NDVIBinningConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return NDVI bin edges and bin indices.

    The returned ``edges`` are the realized NDVI bin boundaries after applying
    the configured clipping rules. They are written to the BRDF model JSON as
    ``ndvi_edges`` so each coefficient row can be traced back to the NDVI
    stratum it was fit from. This is BRDF model metadata, not a standalone NDVI
    science product.
    """

    ndvi_clean = ndvi[np.isfinite(ndvi)]
    ndvi_min = config.ndvi_min
    ndvi_max = config.ndvi_max
    if ndvi_clean.size > 0:
        if config.perc_min is not None:
            ndvi_min = max(ndvi_min, float(np.nanpercentile(ndvi_clean, config.perc_min)))
        if config.perc_max is not None:
            ndvi_max = min(ndvi_max, float(np.nanpercentile(ndvi_clean, config.perc_max)))
    edges = np.linspace(ndvi_min, ndvi_max, config.n_bins + 1, dtype=np.float32)
    bins = np.digitize(ndvi, edges, right=False) - 1
    bins = np.clip(bins, 0, config.n_bins - 1)
    bins[(ndvi < ndvi_min) | (ndvi > ndvi_max)] = -1
    return edges, bins.astype(np.int32)


def _single_brdf_bin(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Return a single BRDF bin spanning the full NDVI domain."""

    edges = np.array([-1.0, 1.0], dtype=np.float32)
    bins = np.zeros(shape, dtype=np.int32)
    return edges, bins


def calc_cosine_i(
    solar_zn: np.ndarray,
    solar_az: np.ndarray,
    aspect: np.ndarray,
    slope: np.ndarray,
) -> np.ndarray:
    """Adapted from hytools.topo.calc_cosine_i (GPLv3; HyTools Authors:
    Adam Chlus, Zhiwei Ye, Philip Townsend). Simplified for NEON use.

    Compute the cosine of the solar incidence angle on a sloped surface.

    Parameters
    ----------
    solar_zn : np.ndarray
        Solar zenith angle [radians], shape (Y,X)
    solar_az : np.ndarray
        Solar azimuth angle [radians], shape (Y,X)
    aspect : np.ndarray
        Surface aspect [radians], shape (Y,X)
        Aspect is typically clockwise from North.
    slope : np.ndarray
        Surface slope [radians], shape (Y,X)

    Returns
    -------
    np.ndarray
        cos(i), shape (Y,X), float32

    Notes
    -----
    HyTools uses this quantity in topographic correction.
    This is basically:
        cos_i = cos(solar_zn)*cos(slope)
                + sin(solar_zn)*sin(slope)*cos(solar_az - aspect)
    """

    solar_zn, solar_az, aspect, slope = _validate_angles(
        solar_zn, solar_az, aspect, slope
    )

    cos_solar_zn = np.cos(solar_zn)
    sin_solar_zn = np.sin(solar_zn)
    cos_slope = np.cos(slope)
    sin_slope = np.sin(slope)
    cos_relative_az = np.cos(solar_az - aspect)

    cos_i = cos_solar_zn * cos_slope + sin_solar_zn * sin_slope * cos_relative_az
    return cos_i.astype(np.float32, copy=False)


def calc_volume_kernel(
    solar_az: np.ndarray,
    solar_zn: np.ndarray,
    sensor_az: np.ndarray,
    sensor_zn: np.ndarray,
    kernel_type: str,
) -> np.ndarray:
    """Adapted from hytools.brdf.kernels.calc_volume_kernel (GPLv3; HyTools Authors:
    Adam Chlus, Zhiwei Ye, Philip Townsend). Simplified for NEON use.

    Compute the BRDF volume scattering kernel for each pixel.
    """

    _normalize_volume_kernel_name(kernel_type)

    solar_az, solar_zn, sensor_az, sensor_zn = _validate_angles(
        solar_az, solar_zn, sensor_az, sensor_zn
    )

    cos_solar = np.cos(solar_zn)
    sin_solar = np.sin(solar_zn)
    cos_sensor = np.cos(sensor_zn)
    sin_sensor = np.sin(sensor_zn)
    cos_rel_az = np.cos(solar_az - sensor_az)

    cos_phase = cos_solar * cos_sensor + sin_solar * sin_sensor * cos_rel_az
    cos_phase = np.clip(cos_phase, -1.0, 1.0)
    phase_angle = np.arccos(cos_phase)

    denom = cos_solar + cos_sensor
    denom = np.where(np.abs(denom) < 1e-6, np.nan, denom)

    kernel = (
        ((np.pi / 2.0 - phase_angle) * cos_phase + np.sin(phase_angle)) / denom
        - np.pi / 4.0
    )

    kernel = np.where(np.isfinite(kernel), kernel, 0.0)
    return kernel.astype(np.float32)


def calc_geom_kernel(
    solar_az: np.ndarray,
    solar_zn: np.ndarray,
    sensor_az: np.ndarray,
    sensor_zn: np.ndarray,
    kernel_type: str,
    b_r: float = 1.0,
    h_b: float = 2.0,
) -> np.ndarray:
    """Adapted from hytools.brdf.kernels.calc_geom_kernel (GPLv3; HyTools Authors:
    Adam Chlus, Zhiwei Ye, Philip Townsend). Simplified for NEON use.

    Compute the BRDF geometric scattering kernel for each pixel.
    """

    normalized_kernel = _normalize_geom_kernel_name(kernel_type)

    solar_az, solar_zn, sensor_az, sensor_zn = _validate_angles(
        solar_az, solar_zn, sensor_az, sensor_zn
    )

    # HyTools pinned 31286d64: Wanner 1995 / Lucht 2000 / Zhang 2018.
    # b/r transforms zenith angles; it is not an output multiplier.
    solar_p = np.arctan(float(b_r) * np.tan(solar_zn.astype(np.float64)))
    sensor_p = np.arctan(float(b_r) * np.tan(sensor_zn.astype(np.float64)))
    relative = sensor_az.astype(np.float64) - solar_az
    ts, tv = np.tan(solar_p), np.tan(sensor_p)
    ss, sv = 1 / np.cos(solar_p), 1 / np.cos(sensor_p)
    distance2 = np.maximum(ts**2 + tv**2 - 2 * ts * tv * np.cos(relative), 0.)
    cos_t = np.clip(float(h_b) * np.sqrt(distance2 + (ts * tv * np.sin(relative))**2) / (ss + sv), -1., 1.)
    t = np.arccos(cos_t)
    overlap = (t - np.sin(t) * np.cos(t)) * (ss + sv) / np.pi
    phase = np.cos(solar_p) * np.cos(sensor_p) + np.sin(solar_p) * np.sin(sensor_p) * np.cos(relative)
    if normalized_kernel == "LiDenseR":
        kernel = (1 + phase) * ss * sv / (ss + sv - overlap) - 2
    else:
        kernel = overlap - ss - sv + .5 * (1 + phase) * ss * sv
    return kernel.astype(np.float32)


# Per-tile topographic correction used by the streamlined NEON and drone workflows.
#
# Big picture:
# - ``chunk_array`` is a hyperspectral tile with shape ``(rows, cols, bands)``.
# - ``ys:ye`` and ``xs:xe`` tell us where that tile sits inside the full scene.
# - The function slices slope/aspect/solar geometry from the full-scene ancillary
#   rasters using those same bounds so every reflectance pixel lines up with its
#   corresponding terrain and illumination geometry.
#
# Math summary:
# - ``cos_i`` is the cosine of the solar incidence angle on the sloped surface.
# - In SCS+C mode, the code fits a linear model for each band on valid pixels:
#     rho = a * cos(i) + b
# - The fitted ``C`` parameter is defined as ``C = b / a``.
# - The correction factor is then:
#     (cos(theta_s) * cos(beta) + C) / (cos(i) + C)
#   where ``theta_s`` is solar zenith and ``beta`` is slope.
# - This is the standard SCS+C adjustment: it reduces terrain-driven brightness
#   differences while damping the instability that a pure cosine ratio can create.
#
# Chunking consequence:
# - Because the regression is fit inside this function on the current tile's valid
#   pixels, the fitted ``C`` value can vary from tile to tile when the caller uses
#   non-overlapping chunks.
def fit_scs_c_coefficients(
    cube,
    *,
    chunk_y: int = 500,
    chunk_x: int | None = None,
) -> np.ndarray:
    """Fit per-band SCS+C ``C`` parameters over a full NeonCube footprint.

    Implements the method of Soenen et al. (2005), DOI
    10.1109/TGRS.2005.852480. The audit found no material source match between
    this fitting/application code and HyTools' SCS+C implementation.

    Streams reflectance tiles and accumulates ordinary-least-squares sufficient
    statistics so scene-wide topographic fits do not require holding a second
    full corrected cube in memory.
    """

    lines = int(getattr(cube, "lines"))
    columns = int(getattr(cube, "columns"))
    bands = int(getattr(cube, "bands"))
    chunk_x = int(chunk_x) if chunk_x is not None else columns
    if chunk_y <= 0 or chunk_x <= 0:
        raise ValueError("chunk dimensions must be positive")

    slope = cube.get_ancillary("slope", radians=True)
    aspect = cube.get_ancillary("aspect", radians=True)
    solar_zn = cube.get_ancillary("solar_zn", radians=True)
    solar_az = cube.get_ancillary("solar_az", radians=True)
    cos_i = calc_cosine_i(solar_zn, solar_az, aspect, slope)

    if hasattr(cube, "mask_no_data"):
        base_mask = cube.mask_no_data.astype(bool)
    else:
        base_mask = np.ones((lines, columns), dtype=bool)
    base_mask &= np.isfinite(cos_i)

    n = np.zeros(bands, dtype=np.float64)
    sum_x = np.zeros(bands, dtype=np.float64)
    sum_y = np.zeros(bands, dtype=np.float64)
    sum_xx = np.zeros(bands, dtype=np.float64)
    sum_xy = np.zeros(bands, dtype=np.float64)

    for ys, ye, xs, xe, raw_chunk in cube.iter_chunks(chunk_y=chunk_y, chunk_x=chunk_x):
        chunk = np.asarray(raw_chunk, dtype=np.float32)
        data_unitless = require_radiometry(cube).to_physical(chunk)
        tile_mask = base_mask[ys:ye, xs:xe] & np.isfinite(data_unitless).all(axis=-1)
        if not np.any(tile_mask):
            continue
        x = cos_i[ys:ye, xs:xe][tile_mask].astype(np.float64, copy=False)
        for band in range(bands):
            y = data_unitless[..., band][tile_mask].astype(np.float64, copy=False)
            finite = np.isfinite(y) & np.isfinite(x)
            if not np.any(finite):
                continue
            x_f = x[finite]
            y_f = y[finite]
            n[band] += x_f.size
            sum_x[band] += x_f.sum()
            sum_y[band] += y_f.sum()
            sum_xx[band] += np.dot(x_f, x_f)
            sum_xy[band] += np.dot(x_f, y_f)

    c_values = np.zeros(bands, dtype=np.float32)
    for band in range(bands):
        if n[band] < 2:
            logger.debug("Band %d: insufficient samples for scene SCS+C; C=0", band)
            continue
        denom = n[band] * sum_xx[band] - sum_x[band] * sum_x[band]
        if abs(denom) < 1e-12:
            logger.debug("Band %d: singular scene SCS+C matrix; C=0", band)
            continue
        a = (n[band] * sum_xy[band] - sum_x[band] * sum_y[band]) / denom
        b = (sum_y[band] - a * sum_x[band]) / n[band]
        if np.isclose(a, 0.0):
            c_values[band] = 0.0
        else:
            c_values[band] = np.float32(b / a)

    logger.info(
        "Scene SCS+C fit complete: C finite bands=%d/%d (min=%.4g max=%.4g)",
        int(np.isfinite(c_values).sum()),
        bands,
        float(np.nanmin(c_values)) if bands else float("nan"),
        float(np.nanmax(c_values)) if bands else float("nan"),
    )
    return c_values


def apply_topo_correct(
    cube,
    chunk_array: np.ndarray,
    ys: int,
    ye: int,
    xs: int,
    xe: int,
    use_scs_c: bool = True,
    scs_c: np.ndarray | None = None,
) -> np.ndarray:
    """Topographic (illumination) correction on a hyperspectral chunk.

    The SCS+C branch implements Soenen et al. (2005), DOI
    10.1109/TGRS.2005.852480. ``calc_cosine_i``, used here, has separately
    documented HyTools implementation lineage.

    Parameters
    ----------
    scs_c :
        Optional per-band SCS+C ``C`` values (length ``bands``). When provided,
        the tile uses these coefficients instead of fitting locally. Pass scene
        fits from :func:`fit_scs_c_coefficients` for HyTools-style behaviour
        without loading the full flightline as one correction chunk.
    """

    if chunk_array.dtype != np.float32:
        raise ValueError("Chunks passed to apply_topo_correct must be float32 arrays.")

    # Pull the ancillary rasters for exactly the same spatial footprint as the
    # reflectance tile we are correcting.
    slope = cube.get_ancillary("slope", radians=True)[ys:ye, xs:xe]
    aspect = cube.get_ancillary("aspect", radians=True)[ys:ye, xs:xe]
    solar_zn = cube.get_ancillary("solar_zn", radians=True)[ys:ye, xs:xe]
    solar_az = cube.get_ancillary("solar_az", radians=True)[ys:ye, xs:xe]

    cos_i = calc_cosine_i(solar_zn, solar_az, aspect, slope)
    cos_solar = np.cos(solar_zn)
    cos_beta = np.cos(slope)

    # Internally we work in unitless reflectance. ``scale_factor`` converts from
    # the cube's stored values to physical reflectance before the correction math.
    data_unitless = require_radiometry(cube).to_physical(chunk_array)

    # ``valid_mask`` is spatial, not spectral: a pixel is valid only if the
    # reflectance tile and illumination geometry are finite at that location.
    if hasattr(cube, "mask_no_data"):
        valid_mask = cube.mask_no_data[ys:ye, xs:xe].astype(bool)
    else:
        valid_mask = np.ones_like(cos_i, dtype=bool)

    valid_mask &= np.isfinite(data_unitless).all(axis=-1)
    valid_mask &= np.isfinite(cos_i)

    corrected_unitless = data_unitless.copy()

    if use_scs_c:
        cos_i_valid = cos_i[valid_mask]
        cos_solar_valid = cos_solar[valid_mask]
        cos_beta_valid = cos_beta[valid_mask]
        precomputed = None
        if scs_c is not None:
            precomputed = np.asarray(scs_c, dtype=np.float64).reshape(-1)
            if precomputed.size != data_unitless.shape[-1]:
                raise ValueError(
                    f"scs_c length {precomputed.size} does not match "
                    f"chunk bands {data_unitless.shape[-1]}"
                )
        for band in range(data_unitless.shape[-1]):
            rho_band = data_unitless[..., band]
            if precomputed is not None:
                C_val = float(precomputed[band])
            else:
                # Solve the SCS+C regression independently for each spectral band
                # using only the valid pixels from this chunk.
                y = rho_band[valid_mask].astype(np.float64, copy=False)
                x = cos_i_valid.astype(np.float64, copy=False)
                finite = np.isfinite(y) & np.isfinite(x)
                if np.count_nonzero(finite) < 2:
                    logger.debug("Band %d: insufficient samples for SCS+C; using neutral", band)
                    continue

                # ``X = [cos(i), 1]`` means least squares is fitting:
                #   rho = a * cos(i) + b
                # where ``a`` is the slope and ``b`` is the intercept.
                X = np.stack([x[finite], np.ones_like(x[finite])], axis=1)
                try:
                    coeffs, *_ = np.linalg.lstsq(X, y[finite], rcond=None)
                    a, b = coeffs
                except np.linalg.LinAlgError:
                    logger.debug("Band %d: regression failed; using neutral", band)
                    continue
                if np.isclose(a, 0.0):
                    C_val = 0.0
                    logger.debug("Band %d: regression slope near zero; C set to 0", band)
                else:
                    # ``C = b / a`` is the classic SCS+C parameter. It shifts both
                    # the numerator and denominator so the correction is less
                    # extreme than a raw cosine ratio when terrain geometry is
                    # unfavorable.
                    C_val = float(b / a)
            num = cos_solar_valid * cos_beta_valid + C_val
            den = cos_i_valid + C_val
            min_denom = MIN_SCS_C_DENOM
            tiny = den > 0

            # Apply the multiplicative SCS+C factor. ``_scs_c_ratio`` forces a
            # neutral ratio of 1.0 when the denominator becomes too small or the
            # ratio is non-positive, which prevents NaN/-9999 cascades in BRDF.
            ratio_valid = _scs_c_ratio(num, den, min_denom=min_denom)
            if np.any(tiny & (den <= min_denom)):
                logger.debug(
                    "Band %d: %.5f fraction of pixels hit denom<=%.1e guard",
                    band,
                    np.count_nonzero(tiny & (den <= min_denom)) / tiny.size,
                    min_denom,
                )
            ratios_band = np.ones_like(cos_i, dtype=np.float32)
            ratios_band[valid_mask] = ratio_valid.astype(np.float32)
            log_stats(
                f"topo_ratio_band{band}",
                ratios_band,
                mask=valid_mask,
            )
            corrected_unitless[..., band] = rho_band * ratios_band
    else:
        # Legacy cosine-ratio fallback. This uses only cos(theta_s) / cos(i) and
        # therefore lacks the stabilizing ``C`` term from SCS+C.
        normalization = np.ones_like(cos_i, dtype=np.float32)
        valid_cos = cos_i > 0
        normalization[valid_cos] = cos_solar[valid_cos] / cos_i[valid_cos]
        corrected_unitless = data_unitless * normalization[..., np.newaxis]

    # Convert back to the cube's stored scale and restore the configured no-data value.
    no_data_value = np.float32(getattr(cube, "no_data", np.nan))
    corrected_scaled = require_radiometry(cube).to_stored(corrected_unitless)
    corrected_scaled = np.where(valid_mask[..., np.newaxis], corrected_scaled, no_data_value)

    return corrected_scaled.astype(np.float32, copy=False)


def apply_brdf_correct(
    cube: "NeonCube",
    chunk_array: np.ndarray,
    ys: int,
    ye: int,
    xs: int,
    xe: int,
    coeff_path: Path | None = None,
    ndvi_config: NDVIBinningConfig | None = None,
    reference_geometry: ReferenceGeometry | None = None,
    brdf_kernel_config: BRDFKernelConfig | None = None,
    input_stage: str = "uncorrected",
) -> np.ndarray:
    """Perform BRDF normalization on a hyperspectral chunk using FlexBRDF ratio."""

    if chunk_array.dtype != np.float32:
        raise ValueError("Chunks passed to apply_brdf_correct must be float32 arrays.")
    radiometry = require_radiometry(cube)
    if coeff_path is None:
        raise ValueError("BRDF UNSUPPORTED: a validated saved model is required.")
    # Read the small record on each call: a path-only cache can conceal edits.
    model = json.loads(Path(coeff_path).read_text())
    validation = model.get("validation", {})
    if model.get("schema_version") != 2 or validation.get("status") != "VALID":
        raise ValueError(f"BRDF {validation.get('status', 'UNSUPPORTED')}: model is not a validated shared-contract fit.")
    if model.get("fit_input_stage") != input_stage:
        raise ValueError("BRDF UNSUPPORTED: fitting and application correction stages differ")
    if brdf_kernel_config is not None:
        from dataclasses import asdict
        if asdict(brdf_kernel_config) != model["kernel_config"]:
            raise ValueError("BRDF INVALID: application kernels differ from validated model")
    if model["radiometry"] != radiometry.record():
        raise ValueError("BRDF INVALID: model radiometry differs from application cube.")
    if model.get("source_identity") != _brdf_source_identity(cube):
        raise ValueError("BRDF INVALID: model source/window differs from application cube.")
    stored_reference = ReferenceGeometry(**model["reference_geometry"])
    if reference_geometry is not None and reference_geometry != stored_reference:
        raise ValueError("BRDF INVALID: application reference differs from validated reference.")
    X, valid, _ = _brdf_design(cube, BRDFKernelConfig(**model["kernel_config"]),
                               scene_solar=model.get("scene_solar_zenith_rad"), window=(ys, ye, xs, xe))
    physical = radiometry.to_physical(chunk_array)
    edges = np.asarray(model["ndvi_edges"], dtype=np.float32)
    if model["ndvi_binning_enabled"]:
        ndvi = compute_ndvi(cube, physical)
        bins = np.digitize(ndvi, edges) - 1
        bins[ndvi == edges[-1]] = len(edges) - 2
        outside = ~np.isfinite(ndvi) | (bins < 0) | (bins >= len(edges)-1)
        if np.any(outside & valid):
            raise ValueError("BRDF UNSUPPORTED: application pixels outside validated NDVI strata.")
    else:
        bins = np.zeros(physical.shape[:2], dtype=int)
    reference = np.asarray(model["reference_design"], dtype=np.float64)
    corrected = physical.copy()
    for band in range(cube.bands):
        for bin_id in range(len(edges)-1):
            selected = valid & (bins == bin_id) & np.isfinite(physical[..., band])
            selected &= chunk_array[..., band] != getattr(cube, "no_data", np.nan)
            if not np.any(selected):
                continue
            values = [model[k][bin_id][band] for k in ("iso", "vol", "geo")]
            if any(value is None for value in values):
                raise ValueError("BRDF UNSUPPORTED: no fitted support for this band/stratum")
            beta = np.asarray(values, dtype=np.float64)
            pred = X @ beta
            ref = float(reference @ beta)
            if np.any(selected & (~np.isfinite(pred) | (pred <= 0))) or not np.isfinite(ref) or ref <= 0:
                raise ValueError("BRDF INVALID: nonpositive/nonfinite prediction; no identity fallback is allowed.")
            factor = np.divide(ref, pred, out=np.ones_like(pred), where=selected)
            if not np.isfinite(factor[selected]).all():
                raise ValueError("BRDF INVALID: nonfinite correction factor.")
            corrected[..., band][selected] *= factor[selected]
    output = radiometry.to_stored(corrected)
    input_valid = valid[..., None] & np.isfinite(chunk_array)
    input_valid &= chunk_array != getattr(cube, "no_data", np.nan)
    return np.where(input_valid, output, getattr(cube, "no_data", np.nan)).astype(np.float32)


def _brdf_source_identity(cube):
    """Bound cached fits to source bytes and spatial window without a pixel cache."""
    import hashlib
    if hasattr(cube, "_brdf_source_digest"):
        return cube._brdf_source_digest
    h = hashlib.sha256()
    # Loaded cubes already hold the source data. Hash bounded row views, never
    # create another full-scene byte string or reread the archive.
    for row in cube.data:
        h.update(np.ascontiguousarray(row).tobytes())
    for name in ("solar_zn", "solar_az", "sensor_zn", "sensor_az"):
        for row in cube.get_ancillary(name, radians=True):
            h.update(np.ascontiguousarray(row).tobytes())
    h.update(str((getattr(cube, "sample_start", 0), getattr(cube, "line_start", 0), cube.data.shape, getattr(cube,"no_data",None))).encode())
    for row in cube.mask_no_data:
        h.update(np.ascontiguousarray(row).tobytes())
    cube._brdf_source_digest = h.hexdigest()
    return cube._brdf_source_digest


def _brdf_design(cube, config, scene_solar=None, window=None):
    names = ("solar_az", "solar_zn", "sensor_az", "sensor_zn")
    valid = np.asarray(cube.mask_no_data, dtype=bool).copy()
    if window is None:
        angles = [np.asarray(cube.get_ancillary(k, radians=True), dtype=np.float32) for k in names]
    else:
        ys, ye, xs, xe = window
        # Slice in native degree units before conversion, avoiding four full
        # angular conversions on every application strip.
        angles = [np.deg2rad(np.asarray(cube.get_ancillary(k, radians=False)[ys:ye, xs:xe], np.float32)) for k in names]
        valid = valid[ys:ye, xs:xe]
    for a in angles:
        valid &= np.isfinite(a)
    valid &= (angles[1] >= 0) & (angles[1] < np.pi/2) & (np.abs(angles[3]) < np.pi/2)
    if str(config.solar_zn_type).lower() == "scene":
        if scene_solar is None:
            scene_solar = float(np.mean(angles[1][valid], dtype=np.float64)) if valid.any() else None
        if scene_solar is not None:
            angles[1] = np.full_like(angles[1], scene_solar)
    kv = calc_volume_kernel(*angles, kernel_type=config.volume_kernel)
    kg = calc_geom_kernel(*angles, kernel_type=config.geom_kernel, b_r=config.b_r, h_b=config.h_b)
    X = np.stack([np.ones_like(kv), kv, kg], axis=-1)
    valid &= np.isfinite(X).all(axis=-1)
    return X, valid, scene_solar


def _reference_design(reference, config):
    a = [np.full((1, 1), np.deg2rad(x), dtype=np.float32) for x in
         (reference.relative_azimuth_deg, reference.solar_zenith_deg, 0., reference.view_zenith_deg)]
    return np.array([1., calc_volume_kernel(*a, kernel_type=config.volume_kernel).item(),
                     calc_geom_kernel(*a, kernel_type=config.geom_kernel, b_r=config.b_r, h_b=config.h_b).item()])


def fit_and_save_brdf_model(
    cube: "NeonCube",
    out_dir: Path,
    ndvi_config: NDVIBinningConfig | None = None,
    brdf_kernel_config: BRDFKernelConfig | None = None,
    rho_min: float = 0.0,
    rho_max: float | None = 2.0,
    apply_topography: bool = False,
) -> Path:
    """Estimate and persist BRDF coefficients for a NEON flightline.

    Parameters
    ----------
    cube : NeonCube
        Loaded NEON hyperspectral cube providing reflectance and ancillary angles.
    out_dir : Path
        Directory where the fitted BRDF coefficient JSON should be stored.

    Returns
    -------
    Path
        Path to the JSON file containing the BRDF model coefficients.
    """

    from dataclasses import asdict
    from .radiometry import Radiometry
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = scene_prefix_from_dir(out_dir)
    # Discovery must be read-only: the legacy normalizer renames old models.
    existing = sorted(out_dir.glob("*_brdf_model.json"))
    if len(existing) > 1:
        raise ValueError("BRDF UNSUPPORTED: multiple existing models; use a fresh output directory")
    coeff_path = existing[0] if existing else out_dir / f"{prefix}_brdf_model.json"
    config = brdf_kernel_config or BRDFKernelConfig()
    ndvi_config = ndvi_config or NDVIBinningConfig()
    reference = ReferenceGeometry()
    radiometry = getattr(cube, "radiometry", Radiometry(None, None, "UNSUPPORTED", "No authoritative calibration"))
    identity = _brdf_source_identity(cube)
    signature = {"source_identity": identity, "radiometry": radiometry.record(),
                 "kernel_config": asdict(config), "ndvi_config": asdict(ndvi_config),
                 "rho_min": rho_min, "rho_max": rho_max, "schema_version": 2,
                 "apply_topography": bool(apply_topography)}
    if coeff_path.exists():
        old = json.loads(coeff_path.read_text())
        if all(old.get(k) == v for k, v in signature.items()):
            return coeff_path
        raise ValueError("BRDF UNSUPPORTED: cached model is stale or unvalidated; use a fresh output directory. Historical models are not overwritten.")
    payload = {**signature, "source_path": str(getattr(cube,"h5_path","in-memory fixture")),
               "source_shape": list(cube.data.shape), "reference_geometry": asdict(reference),
               "coefficient_provenance": "scene ordinary least squares; shared Ross-Li v2; coefficients absent unless VALID",
               "fitting_population": {"available_spatial": int(np.count_nonzero(cube.mask_no_data)), "eligible": None, "status": "NOT_EVALUATED"},
               "angular_support": {"status": "NOT_EVALUATED"},
               "rank_conditioning_status": "NOT_EVALUATED",
               "correction_factor_diagnostics_status": "NOT_EVALUATED",
               "validation": {"status": "UNSUPPORTED", "fits": [], "reasons": []}}
    validation = payload["validation"]
    try:
        radiometry.require_valid()
    except ValueError as exc:
        validation["reasons"].append(str(exc))
        coeff_path.write_text(json.dumps(payload, indent=2, allow_nan=False))
        return coeff_path
    physical = radiometry.to_physical(cube.data)
    if apply_topography:
        # Fit the BRDF on the same topographically corrected measurements to
        # which its ratio will be applied. Fit C once; keep raw cube immutable.
        c = fit_scs_c_coefficients(cube)
        payload["topographic_c"] = c.astype(float).tolist()
        for ys, ye, xs, xe, chunk in cube.iter_chunks(chunk_y=500, chunk_x=cube.columns):
            corrected = apply_topo_correct(cube, np.asarray(chunk, np.float32), ys, ye, xs, xe, scs_c=c)
            physical[ys:ye, xs:xe] = radiometry.to_physical(corrected)
    payload["fit_input_stage"] = "topographic_only" if apply_topography else "uncorrected"
    X, valid, scene_solar = _brdf_design(cube, config)
    payload["fitting_population"]["status"] = "EVALUATED_PER_BAND_STRATUM"
    payload["rank_conditioning_status"] = "EVALUATED_PER_BAND_STRATUM"
    payload["scene_solar_zenith_rad"] = scene_solar
    payload["angular_support"] = {}
    for name in ("solar_zn", "solar_az", "sensor_zn", "sensor_az"):
        a = cube.get_ancillary(name, radians=True)[valid]
        payload["angular_support"][name] = {"count": int(a.size),
            "min_rad": float(a.min()) if a.size else None,
            "max_rad": float(a.max()) if a.size else None,
            "std_rad": float(a.std(dtype=np.float64)) if a.size else None}
    ref = _reference_design(reference, config)
    payload["reference_design"] = ref.tolist()
    if ndvi_config.enabled and ndvi_config.n_bins > 1:
        edges, bins = compute_ndvi_bins(compute_ndvi(cube, physical), ndvi_config)
    else:
        edges, bins = _single_brdf_bin(physical.shape[:2])
    n_bins = len(edges)-1
    if np.any(valid & (bins < 0)):
        validation["reasons"].append("Application pixels outside fitted NDVI strata; partial-scene BRDF is unsupported")
    coefficients = np.full((n_bins, cube.bands, 3), np.nan, np.float64)
    unsupported = bool(validation["reasons"])
    invalid = False
    # Float32 input kernels cannot support a solution whose conditioning loses
    # more than half their significant digits. This is a precision requirement,
    # not an empirical approval threshold or a correction-factor cap.
    condition_limit = 1 / np.sqrt(np.finfo(np.float32).eps)
    validation["condition_limit"] = float(condition_limit)
    for band in range(cube.bands):
        if band % 10 == 0 or band == cube.bands - 1:
            logger.info("BRDF validation: band %d/%d; %d strata; physical rho eligibility [%s, %s]", band+1, cube.bands, n_bins, rho_min, rho_max)
        for bin_id in range(n_bins):
            population = valid & (bins == bin_id)
            y = physical[..., band]
            finite = population & np.isfinite(y) & (cube.data[..., band] != getattr(cube, "no_data", np.nan))
            eligible = finite & (y >= rho_min)
            if rho_max is not None:
                eligible &= y <= rho_max
            count = int(eligible.sum())
            record = {"band": band, "bin": bin_id, "available": int(population.sum()),
                      "eligible": count, "excluded_nonfinite_or_nodata": int((population & ~finite).sum()),
                      "excluded_below_min": int((finite & (y < rho_min)).sum()),
                      "excluded_above_max": int((finite & (y > rho_max)).sum()) if rho_max is not None else 0,
                      "rank": 0, "status": "UNSUPPORTED"}
            validation["fits"].append(record)
            if not np.any(finite):
                record.update(status="NOT_APPLICABLE", reason="No finite source observations in this band/stratum; nodata is preserved, no coefficients estimated")
                continue
            if count < 4:
                record["reason"] = "Fewer than four eligible observations for three coefficients and residual assessment"
                unsupported = True
                continue
            A = X[eligible].astype(np.float64)
            target = y[eligible].astype(np.float64)
            beta, _, rank, singular = np.linalg.lstsq(A, target, rcond=None)
            condition = float(singular[0] / singular[-1]) if singular[-1] > 0 else None
            if condition is not None and not np.isfinite(condition):
                condition = None
            record.update(rank=int(rank), singular_values=singular.tolist(), condition_number=condition)
            if rank != 3 or condition is None or condition > condition_limit:
                record["reason"] = "Rank-deficient or insufficiently conditioned angular design"
                unsupported = True
                continue
            # Check the whole application domain, not only the few eligible pixels.
            domain = X[population].astype(np.float64)
            prediction = domain @ beta
            reference_prediction = float(ref @ beta)
            roundoff = 8 * np.finfo(np.float32).eps * (np.abs(domain) @ np.abs(beta))
            reference_roundoff = float(8 * np.finfo(np.float32).eps * (np.abs(ref) @ np.abs(beta)))
            residual = target - A @ beta
            variance = float(residual @ residual / (count - 3))
            covariance = variance * np.linalg.inv(A.T @ A)
            reference_se = float(np.sqrt(max(0., ref @ covariance @ ref)))
            prediction_se = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", domain, covariance, domain), 0.))
            record.update(reference_prediction=reference_prediction, reference_standard_error=reference_se,
                          predicted_standard_error_quantiles=np.quantile(prediction_se,[0,.5,1]).tolist(),
                          coefficient_standard_errors=np.sqrt(np.maximum(np.diag(covariance),0)).tolist(),
                          reference_leverage=float(ref @ np.linalg.solve(A.T @ A, ref)),
                          reference_outside_kernel_bounds=bool(np.any((ref < A.min(axis=0)) | (ref > A.max(axis=0)))))
            if (not np.isfinite(beta).all() or not np.isfinite(prediction).all() or
                    np.any(prediction <= roundoff + 1.96 * prediction_se) or reference_prediction <= reference_roundoff + 1.96 * reference_se):
                record.update(status="INVALID", reason="Nonpositive or cancellation/uncertainty-dominated model prediction")
                invalid = True
                continue
            factors = reference_prediction / prediction
            record.update(status="VALID", predicted_quantiles=np.quantile(prediction,[0,.01,.5,.99,1]).tolist(),
                          factor_quantiles=np.quantile(factors,[0,.01,.5,.99,1]).tolist())
            coefficients[bin_id, band] = beta
    validation["status"] = "INVALID" if invalid else "UNSUPPORTED" if unsupported else "VALID"
    if not valid.any() or all(r["status"] == "NOT_APPLICABLE" for r in validation["fits"]):
        validation["status"] = "UNSUPPORTED"
        validation["reasons"].append("No supported angular observations")
    payload["correction_factor_diagnostics_status"] = "EVALUATED_PER_SUPPORTED_FIT"
    if validation["status"] == "VALID":
        for i, key in enumerate(("iso", "vol", "geo")):
            payload[key] = [[float(v) if np.isfinite(v) else None for v in row] for row in coefficients[...,i]]
    payload.update(ndvi_edges=edges.astype(float).tolist(), ndvi_binning_enabled=bool(ndvi_config.enabled and n_bins > 1),
                   volume_kernel=config.volume_kernel, geom_kernel=config.geom_kernel,
                   b_r=config.b_r, h_b=config.h_b, solar_zn_type=config.solar_zn_type)
    coeff_path.write_text(json.dumps(payload, indent=2, allow_nan=False))
    return coeff_path
