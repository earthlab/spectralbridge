"""Agreement statistics and true Landsat-footprint aggregation, without fitting calibration."""

from contextlib import ExitStack
from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.stats import spearmanr

from .io.neon import reflectance_to_unitless_multiplier
from .landsat_validation import (
    _clear_landsat_mask,
    LANDSAT_SURFACE_REFLECTANCE_SCALE,
    LANDSAT_SURFACE_REFLECTANCE_OFFSET,
)

OLI_CHANNELS = ("coastal", "blue", "green", "red", "nir08", "swir16", "swir22")
OLI_CENTERS = np.array([443, 482, 561.4, 654.6, 864.7, 1608.9, 2200.7])


@dataclass(frozen=True)
class ReferenceGrid:
    crs: str
    transform: tuple
    width: int
    height: int
    row_offset: int = 0
    col_offset: int = 0

    @property
    def affine(self):
        from affine import Affine

        return Affine(*self.transform[:6])


def mask_landsat_qa(qa_pixel, qa_radsat):
    """L8/9: reject flags 0-5, B1-B7 saturation and terrain occlusion."""
    q = np.asarray(qa_pixel, np.uint16)
    r = np.asarray(qa_radsat, np.uint16)
    if q.shape != r.shape:
        raise ValueError("QA_PIXEL and QA_RADSAT must share a grid")
    valid = _clear_landsat_mask(q) & ((r & np.uint16(127 | (1 << 11))) == 0)
    category = np.zeros(q.shape, np.uint8)
    category[(q & (1 << 5)) != 0] = 3
    category[(q & (1 << 4)) != 0] = 2
    category[(q & ((1 << 1) | (1 << 2) | (1 << 3))) != 0] = 1
    category[(r & np.uint16(127 | (1 << 11))) != 0] = 5
    category[(q & 1) != 0] = 4
    return valid, category


def scale_landsat_sr(dn):
    """Official Collection 2 Level-2 DN contract; never guess from magnitudes."""
    a = np.asarray(dn)
    valid = np.isfinite(a) & (a >= 1) & (a <= 65455)
    return np.where(
        valid,
        a.astype(np.float64) * LANDSAT_SURFACE_REFLECTANCE_SCALE
        + LANDSAT_SURFACE_REFLECTANCE_OFFSET,
        np.nan,
    )


def spectral_angle(real, synthetic):
    x = np.asarray(real, float)
    y = np.asarray(synthetic, float)
    if x.shape != y.shape or x.shape[-1] != 7:
        raise ValueError("Need matching seven-channel vectors on the last axis")
    norms = np.linalg.norm(x, axis=-1) * np.linalg.norm(y, axis=-1)
    cosine = np.divide(
        np.sum(x * y, axis=-1),
        norms,
        out=np.full(norms.shape, np.nan),
        where=norms > 1e-12,
    )
    return np.degrees(np.arccos(np.clip(cosine, -1, 1)))


def deming_regression(x, y, error_variance_ratio=1.0):
    """y versus x, lambda=variance(y measurement error)/variance(x error)."""
    if error_variance_ratio <= 0:
        raise ValueError("Deming variance ratio must be positive")
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    if len(x) < 3:
        return np.nan, np.nan
    xx = x - x.mean()
    yy = y - y.mean()
    vx = np.mean(xx * xx)
    vy = np.mean(yy * yy)
    cov = np.mean(xx * yy)
    if vx <= 0 or vy <= 0 or abs(cov) < 1e-15:
        return np.nan, np.nan
    a = vy - error_variance_ratio * vx
    d = np.sqrt(a * a + 4 * error_variance_ratio * cov * cov)
    slope = (a + d) / (2 * cov) if a >= 0 else 2 * error_variance_ratio * cov / (d - a)
    return float(slope), float(y.mean() - slope * x.mean())


def compute_agreement_metrics(real, synthetic) -> dict:
    """Summarize paired scalar reflectance observations in their supplied units.

    Args:
        real (array-like): Reference reflectance values.
        synthetic (array-like): Same-shape modeled reflectance values.

    Returns:
        dict: Finite-pair N/status, bias (synthetic minus real), MAE, RMSE,
            IQR-normalized RMSE, correlations, identity/Deming fits and residual
            diagnostics. Undefined sparse/constant statistics are NaN. No clipping
            or unit conversion occurs; bias/MAE/RMSE retain reflectance units.

    Raises:
        ValueError: Inputs cannot be broadcast/aligned for pairwise evaluation.

    Correlation is not radiometric agreement. This function supplies no
    population uncertainty; spatial-block intervals are added by the workflow.
    """
    x = np.asarray(real, float)
    y = np.asarray(synthetic, float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    if not len(x):
        return dict(N=0, status="no_common_support")
    difference = y - x
    average = (x + y) / 2
    sd = float(np.std(difference, ddof=1)) if len(x) > 1 else np.nan
    rmse = float(np.sqrt(np.mean(difference * difference)))
    iqr = float(np.subtract(*np.quantile(x, [0.75, 0.25])))
    slope, intercept = deming_regression(x, y)
    variable = len(x) > 2 and np.ptp(x) > 1e-12 and np.ptp(y) > 1e-12
    corr = float(np.corrcoef(x, y)[0, 1]) if variable else np.nan
    identity_r2 = (
        1 - float(np.sum(difference**2) / np.sum((x - x.mean()) ** 2))
        if np.ptp(x) > 1e-12
        else np.nan
    )
    hetero = (
        float(spearmanr(average, np.abs(difference)).statistic)
        if np.ptp(average) > 1e-12 and np.ptp(np.abs(difference)) > 1e-12
        else np.nan
    )
    out = dict(
        N=len(x),
        status="ok",
        mean_bias=float(difference.mean()),
        median_bias=float(np.median(difference)),
        MAE=float(np.mean(np.abs(difference))),
        RMSE=rmse,
        nRMSE_IQR=rmse / iqr if iqr > 1e-8 else np.nan,
        normalization_IQR=iqr,
        Pearson_r=corr,
        Spearman_rho=float(spearmanr(x, y).statistic) if variable else np.nan,
        correlation_r2=corr * corr,
        identity_r2=identity_r2,
        deming_slope=slope,
        deming_intercept=intercept,
        loa_lower=float(difference.mean() - 1.96 * sd),
        loa_upper=float(difference.mean() + 1.96 * sd),
        residual_q025=float(np.quantile(difference, 0.025)),
        residual_q975=float(np.quantile(difference, 0.975)),
        absolute_error_brightness_rho=hetero,
    )
    for lam in [0.25, 4.0]:
        out[f"deming_slope_lambda_{lam:g}"], out[f"deming_intercept_lambda_{lam:g}"] = (
            deming_regression(x, y, lam)
        )
    return out


def spatial_bootstrap_indices(
    rows, cols, replicates=499, block_pixels=10, seed=20261014
):
    """Resample spatial blocks, never individual pixels as independent evidence."""
    if block_pixels < 1 or replicates < 1:
        raise ValueError("Positive spatial blocks and bootstrap count required")
    labels = np.column_stack(
        [np.asarray(rows) // block_pixels, np.asarray(cols) // block_pixels]
    )
    _, group = np.unique(labels, axis=0, return_inverse=True)
    members = [np.flatnonzero(group == k) for k in np.unique(group)]
    rng = np.random.default_rng(seed)
    draws = (
        [
            np.concatenate(
                [members[k] for k in rng.integers(0, len(members), len(members))]
            )
            for _ in range(replicates)
        ]
        if members
        else []
    )
    return draws, len(members)


def _axis_weights(destination_edges, source_edges):
    """Exact interval overlaps, including fractional source/destination edges."""
    sl = np.minimum(source_edges[:-1], source_edges[1:])
    sh = np.maximum(source_edges[:-1], source_edges[1:])
    rows = []
    cols = []
    values = []
    for j, (a, b) in enumerate(zip(destination_edges[:-1], destination_edges[1:])):
        lo, hi = min(a, b), max(a, b)
        ix = np.flatnonzero((sh > lo) & (sl < hi))
        rows.extend([j] * len(ix))
        cols.extend(ix)
        values.extend(np.minimum(sh[ix], hi) - np.maximum(sl[ix], lo))
    return csr_matrix(
        (values, (rows, cols)),
        shape=(len(destination_edges) - 1, len(source_edges) - 1),
    )


def _source_scale(source, explicit):
    tags = source.tags(ns="ENVI")
    value = tags.get("reflectance_scale_factor", tags.get("reflectance scale factor"))
    if explicit is None and value is None:
        raise ValueError("Explicit source reflectance scale metadata required")
    factor = float(explicit if explicit is not None else value)
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError("Invalid source reflectance scale factor")
    if (
        value is not None
        and explicit is not None
        and not np.isclose(float(value), factor)
    ):
        raise ValueError("Explicit and raster reflectance scale metadata disagree")
    return reflectance_to_unitless_multiplier(factor)


def aggregate_to_landsat_grid(
    products, grid, *, scale_factors=None, offset_m=(0.0, 0.0), strip_rows=8
) -> dict:
    """Aggregate joint seven-band products to actual projected Landsat footprints.

    Args:
        products (dict): Variant names mapped to seven-band raster paths.
        grid (ReferenceGrid): Actual north-up projected Landsat grid.
        scale_factors (dict, optional): Explicit divisor by variant. Otherwise
            verified raster metadata must declare scale; never infer visually.
        offset_m (tuple[float, float]): Declared source registration offset in
            projected meters; unsupported cross-CRS offsets raise ValueError.
        strip_rows (int): Positive destination strip size for bounded reads.

    Returns:
        dict: Variant means/variances in unitless reflectance, source geometry
            coverage, joint validity/full-footprint coverage, contributing counts,
            and aggregation method. Unsupported cells have NaN means.

    Raises:
        ValueError: Invalid grid, scale, dimensions, offsets or variant alignment.
        OSError: Rasters cannot be read.

    Same-CRS uses interval intersections; cross-CRS uses transformed source-cell
    polygons. Whole-footprint coverage is not normalized to contributing source
    overlap. Joint finite/nodata masks keep variants and seven channels paired.
    """
    import rasterio
    from rasterio.windows import from_bounds, Window
    from affine import Affine

    a = grid.affine
    if (
        a.b != 0
        or a.d != 0
        or a.a <= 0
        or a.e >= 0
        or not rasterio.crs.CRS.from_user_input(grid.crs).is_projected
    ):
        raise ValueError("Reference must be a north-up projected Landsat grid")
    if strip_rows < 1:
        raise ValueError("strip_rows must be positive")
    scale_factors = scale_factors or {}
    shape = (grid.height, grid.width)
    means = {k: np.full((7, *shape), np.nan) for k in products}
    variances = {k: np.full((7, *shape), np.nan) for k in products}
    area = np.zeros(shape)
    geometric = np.zeros(shape)
    counts = np.zeros(shape, np.int32)
    with ExitStack() as stack:
        sources = {
            k: stack.enter_context(rasterio.open(p)) for k, p in products.items()
        }
        first = next(iter(sources.values()))
        for k, src in sources.items():
            if (
                src.count != 7
                or src.crs is None
                or src.transform.b != 0
                or src.transform.d != 0
                or src.transform.a <= 0
                or src.transform.e >= 0
            ):
                raise ValueError(
                    "Source requires seven bands, CRS and rectilinear grid"
                )
            if (
                src.shape != first.shape
                or src.crs != first.crs
                or src.transform != first.transform
            ):
                raise ValueError(
                    "Synthetic variants must share the identical source pixel grid"
                )
        multipliers = {
            k: _source_scale(src, scale_factors.get(k)) for k, src in sources.items()
        }
        shifted = Affine(
            first.transform.a,
            0,
            first.transform.c + offset_m[0],
            0,
            first.transform.e,
            first.transform.f + offset_m[1],
        )
        if first.crs != rasterio.crs.CRS.from_user_input(grid.crs):
            if offset_m != (0.0, 0.0):
                raise ValueError(
                    "Registration offsets in destination meters require matching projected CRS"
                )
            return _aggregate_cross_crs(sources, grid, multipliers)
        for start in range(0, grid.height, strip_rows):
            stop = min(grid.height, start + strip_rows)
            left, top = a * (0, start)
            right, bottom = a * (grid.width, stop)
            ww = from_bounds(left, bottom, right, top, shifted)
            col0 = max(0, int(np.floor(ww.col_off)))
            row0 = max(0, int(np.floor(ww.row_off)))
            col1 = min(first.width, int(np.ceil(ww.col_off + ww.width)))
            row1 = min(first.height, int(np.ceil(ww.row_off + ww.height)))
            if col1 <= col0 or row1 <= row0:
                continue
            window = Window(col0, row0, col1 - col0, row1 - row0)
            data = {
                k: src.read(window=window, masked=True).astype(np.float64)
                for k, src in sources.items()
            }
            valid = np.ones((row1 - row0, col1 - col0), bool)
            for v in data.values():
                valid &= ~np.ma.getmaskarray(v).any(0) & np.isfinite(v.data).all(0)
            xx = shifted.c + np.arange(col0, col1 + 1) * shifted.a
            yy = shifted.f + np.arange(row0, row1 + 1) * shifted.e
            wx = _axis_weights(a.c + np.arange(grid.width + 1) * a.a, xx)
            wy = _axis_weights(a.f + np.arange(start, stop + 1) * a.e, yy)

            def reduce(v):
                return (wx @ (wy @ v).T).T

            denominator = reduce(valid.astype(float))
            area[start:stop] = denominator
            geometric[start:stop] = reduce(np.ones_like(valid, dtype=float))
            bx = wx.copy()
            bx.data[:] = 1
            by = wy.copy()
            by.data[:] = 1
            counts[start:stop] = (bx @ (by @ valid.astype(float)).T).T.astype(np.int32)
            for k, v in data.items():
                values = v.data * multipliers[k]
                for band in range(7):
                    anchor = float(np.mean(values[band][valid])) if valid.any() else 0.0
                    centered = np.where(valid, values[band] - anchor, 0.0)
                    mu = np.divide(
                        reduce(centered),
                        denominator,
                        out=np.full_like(denominator, np.nan),
                        where=denominator > 0,
                    )
                    means[k][band, start:stop] = mu + anchor
                    variances[k][band, start:stop] = np.maximum(
                        0,
                        np.divide(
                            reduce(centered * centered),
                            denominator,
                            out=np.full_like(denominator, np.nan),
                            where=denominator > 0,
                        )
                        - mu * mu,
                    )
    pixel_area = abs(a.a * a.e)
    return dict(
        means=means,
        variances=variances,
        contributing_pixels=counts,
        coverage_fraction=np.clip(geometric / pixel_area, 0, 1),
        valid_fraction=np.divide(
            area, geometric, out=np.zeros_like(area), where=geometric > 0
        ),
        valid_coverage_fraction=np.clip(area / pixel_area, 0, 1),
        method="exact_rectilinear_area_intersection",
    )


def _aggregate_cross_crs(sources, grid, multipliers):
    """Bounded destination-pixel polygon intersections; no implicit regridding."""
    from rasterio.windows import from_bounds, Window
    from rasterio.warp import transform_bounds
    from pyproj import Transformer
    import shapely

    a = grid.affine
    first = next(iter(sources.values()))
    s = first.transform
    transformer = Transformer.from_crs(first.crs, grid.crs, always_xy=True)
    shape = (grid.height, grid.width)
    means = {k: np.full((7, *shape), np.nan) for k in sources}
    variances = {k: np.full((7, *shape), np.nan) for k in sources}
    coverage = np.zeros(shape)
    valid_area = np.zeros(shape)
    counts = np.zeros(shape, np.int32)
    for row in range(grid.height):
        for col in range(grid.width):
            left, top = a * (col, row)
            right, bottom = a * (col + 1, row + 1)
            bounds = transform_bounds(
                grid.crs, first.crs, left, bottom, right, top, densify_pts=21
            )
            w = from_bounds(*bounds, s)
            c0 = max(0, int(np.floor(w.col_off)))
            r0 = max(0, int(np.floor(w.row_off)))
            c1 = min(first.width, int(np.ceil(w.col_off + w.width)))
            r1 = min(first.height, int(np.ceil(w.row_off + w.height)))
            if c1 <= c0 or r1 <= r0:
                continue
            cc, rr = np.meshgrid(np.arange(c0, c1), np.arange(r0, r1))
            polygons = []
            for dc, dr in [(0, 0), (1, 0), (1, 1), (0, 1)]:
                x, y = s * (cc + dc, rr + dr)
                x, y = transformer.transform(x, y)
                polygons.append(np.stack([x, y], axis=-1))
            cells = shapely.polygons(np.stack(polygons, axis=-2).reshape(-1, 4, 2))
            weights = shapely.area(
                shapely.intersection(cells, shapely.box(left, bottom, right, top))
            )
            data = {
                k: src.read(
                    window=Window(c0, r0, c1 - c0, r1 - r0), masked=True
                ).reshape(7, -1)
                for k, src in sources.items()
            }
            valid = np.ones(len(weights), bool)
            for v in data.values():
                valid &= ~np.ma.getmaskarray(v).any(0) & np.isfinite(v.data).all(0)
            weights_valid = weights * valid
            mass = weights_valid.sum()
            coverage[row, col] = weights.sum()
            valid_area[row, col] = mass
            counts[row, col] = int(((weights > 0) & valid).sum())
            if mass <= 0:
                continue
            for k, v in data.items():
                values = v.data * multipliers[k]
                mu = np.sum(np.where(valid, values, 0) * weights_valid, axis=1) / mass
                means[k][:, row, col] = mu
                variances[k][:, row, col] = (
                    np.sum(
                        np.where(valid, (values - mu[:, None]) ** 2, 0) * weights_valid,
                        axis=1,
                    )
                    / mass
                )
    cellarea = abs(a.a * a.e)
    return dict(
        means=means,
        variances=variances,
        contributing_pixels=counts,
        coverage_fraction=np.clip(coverage / cellarea, 0, 1),
        valid_fraction=np.divide(
            valid_area, coverage, out=np.zeros_like(coverage), where=coverage > 0
        ),
        valid_coverage_fraction=np.clip(valid_area / cellarea, 0, 1),
        method="transformed_source_cell_polygon_intersection",
    )
