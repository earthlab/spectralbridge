"""Deterministic, legible plots used by stage QA reports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import SymLogNorm


PLOT_CONTRACT_VERSION = "1.1"
STANDARD_WAVELENGTH_RANGE_NM = (350.0, 2600.0)
STANDARD_REFLECTANCE_RANGE = (-0.1, 1.6)
STANDARD_REFLECTANCE_MAP_RANGE = (0.0, 1.2)
STANDARD_RGB_REFLECTANCE_RANGE = (0.0, 0.6)
STANDARD_CORRECTION_DIFFERENCE_RANGE = (-0.2, 0.2)
STANDARD_VALID_MAP_RANGE = (0.0, 1.0)
STANDARD_VALID_FRACTION_RANGE = (0.0, 1.02)
STANDARD_NEGATIVE_FRACTION_RANGE = (0.0, 0.055)
STANDARD_SEAM_SCORE_RANGE = (0.0, 3.0)
STANDARD_CORRECTION_LINTHRESH = 0.005
STANDARD_BRIGHTNESS_PERCENT_RANGE = (-15.0, 5.0)
STANDARD_GEOMETRY_RANGE_RADIANS = (-0.1, 2.0 * np.pi + 0.1)
STANDARD_BRDF_COEFFICIENT_RANGE = (-1.5, 1.5)


def qa_plot_contract() -> dict[str, Any]:
    """Return the machine-readable fixed display contract for QA figures."""

    return {
        "version": PLOT_CONTRACT_VERSION,
        "display_only": True,
        "values_outside_limits_retained_in_metrics": True,
        "wavelength_nm": list(STANDARD_WAVELENGTH_RANGE_NM),
        "reflectance": list(STANDARD_REFLECTANCE_RANGE),
        "reflectance_map": list(STANDARD_REFLECTANCE_MAP_RANGE),
        "rgb_reflectance": list(STANDARD_RGB_REFLECTANCE_RANGE),
        "correction_difference": list(STANDARD_CORRECTION_DIFFERENCE_RANGE),
        "correction_difference_norm": (
            f"symmetric_log_linthresh_{STANDARD_CORRECTION_LINTHRESH:g}"
        ),
        "valid_map": list(STANDARD_VALID_MAP_RANGE),
        "valid_fraction": list(STANDARD_VALID_FRACTION_RANGE),
        "negative_fraction": list(STANDARD_NEGATIVE_FRACTION_RANGE),
        "seam_score": list(STANDARD_SEAM_SCORE_RANGE),
        "brightness_adjustment_percent": list(STANDARD_BRIGHTNESS_PERCENT_RANGE),
        "geometry_radians": list(STANDARD_GEOMETRY_RANGE_RADIANS),
        "brdf_coefficient": list(STANDARD_BRDF_COEFFICIENT_RANGE),
    }


def format_location_label(flightline_id: str) -> str:
    """Return a compact location/date label while preserving fallback identity."""

    match = re.search(
        r"NEON_D(?P<domain>\d+)_(?P<site>[^_]+)_DP\d+_"
        r"(?P<line>L\d+)(?:-\d+)?_(?P<date>\d{8})",
        flightline_id,
    )
    if not match:
        return flightline_id
    date = match.group("date")
    formatted_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    return (
        f"{match.group('site')} · D{match.group('domain')} · "
        f"{match.group('line')} · {formatted_date}"
    )


def spatial_plot_context(
    header: dict[str, Any],
    source_shape: tuple[int, int, int],
) -> dict[str, Any]:
    """Derive a projected plotting extent from standard ENVI map metadata."""

    map_info = header.get("map info")
    if not isinstance(map_info, (list, tuple)) or len(map_info) < 7:
        return {
            "mode": "sampled_pixel_coordinates",
            "extent": None,
            "x_label": "Sampled column",
            "y_label": "Sampled row",
            "coordinate_system": None,
        }
    try:
        reference_x = float(map_info[1])
        reference_y = float(map_info[2])
        map_x = float(map_info[3])
        map_y = float(map_info[4])
        pixel_x = abs(float(map_info[5]))
        pixel_y = abs(float(map_info[6]))
    except (TypeError, ValueError):
        return {
            "mode": "sampled_pixel_coordinates",
            "extent": None,
            "x_label": "Sampled column",
            "y_label": "Sampled row",
            "coordinate_system": None,
        }
    _, rows, cols = source_shape
    left = map_x - (reference_x - 0.5) * pixel_x
    top = map_y + (reference_y - 0.5) * pixel_y
    right = left + cols * pixel_x
    bottom = top - rows * pixel_y
    projection = str(map_info[0])
    zone = str(map_info[7]) if len(map_info) > 7 else None
    hemisphere = str(map_info[8]) if len(map_info) > 8 else None
    coordinate_system = " ".join(
        value
        for value in (projection, f"zone {zone}" if zone else None, hemisphere)
        if value
    )
    return {
        "mode": "projected_map_coordinates",
        "extent": [left, right, bottom, top],
        "x_label": "Easting (m)",
        "y_label": "Northing (m)",
        "coordinate_system": coordinate_system,
    }


def _apply_spatial_axes(axis: Any, spatial_context: dict[str, Any]) -> None:
    axis.set_xlabel(spatial_context["x_label"])
    axis.set_ylabel(spatial_context["y_label"])
    if spatial_context.get("extent") is not None:
        axis.ticklabel_format(style="plain", useOffset=False)
        axis.tick_params(axis="x", rotation=20)


def _clipping_note(
    axis: Any,
    values: np.ndarray,
    limits: tuple[float, float],
) -> None:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        return
    clipped = float(np.mean((finite < limits[0]) | (finite > limits[1])))
    if clipped <= 0:
        return
    axis.text(
        0.01,
        0.01,
        (
            "<0.01% outside display range; retained in metrics"
            if clipped < 0.0001
            else f"{clipped:.2%} outside display range; retained in metrics"
        ),
        transform=axis.transAxes,
        fontsize=7,
        color="#7a2e20",
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
    )


def _rgb(cube: np.ndarray, wavelengths: np.ndarray) -> tuple[np.ndarray, str]:
    targets = (660.0, 560.0, 490.0)
    if wavelengths.size == cube.shape[0] and np.isfinite(wavelengths).any():
        indices = [
            int(np.nanargmin(np.abs(wavelengths - target))) for target in targets
        ]
        label = "RGB approximation (660/560/490 nm; fixed 0–0.6 stretch)"
    else:
        indices = [0, min(1, cube.shape[0] - 1), min(2, cube.shape[0] - 1)]
        label = (
            f"False color (bands {indices[0]}/{indices[1]}/{indices[2]}; "
            "fixed 0–0.6 stretch)"
        )
    channels = []
    for index in indices:
        channel = np.asarray(cube[index], dtype=np.float64)
        low, high = STANDARD_RGB_REFLECTANCE_RANGE
        channel = np.clip((channel - low) / (high - low), 0, 1)
        channel[~np.isfinite(channel)] = 0
        channels.append(channel)
    return np.stack(channels, axis=-1), label


def render_envi_overview(
    cube: np.ndarray,
    wavelengths: np.ndarray,
    output_path: Path,
    *,
    title: str,
    location_label: str,
    spatial_context: dict[str, Any],
) -> Path:
    """Render spatial support and spectral distribution from an actual ENVI cube."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rgb, rgb_label = _rgb(cube, wavelengths)
    valid = np.isfinite(cube) & (cube > -9990)
    valid_map = np.mean(valid, axis=0)
    spectra = np.where(valid, cube, np.nan).reshape(cube.shape[0], -1)
    median = np.nanmedian(spectra, axis=1)
    q05 = np.nanquantile(spectra, 0.05, axis=1)
    q95 = np.nanquantile(spectra, 0.95, axis=1)
    valid_by_band = np.mean(valid, axis=(1, 2))
    x = wavelengths if wavelengths.size == cube.shape[0] else np.arange(cube.shape[0])
    x_label = "Wavelength (nm)" if wavelengths.size == cube.shape[0] else "Band index"

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    extent = spatial_context.get("extent")
    fig.suptitle(f"{title}\nLocation: {location_label}")
    axes[0, 0].imshow(rgb, extent=extent, origin="upper")
    axes[0, 0].set_title(f"{rgb_label}\n{location_label}")
    _apply_spatial_axes(axes[0, 0], spatial_context)
    valid_image = axes[0, 1].imshow(
        valid_map,
        cmap="viridis",
        vmin=STANDARD_VALID_MAP_RANGE[0],
        vmax=STANDARD_VALID_MAP_RANGE[1],
        extent=extent,
        origin="upper",
    )
    axes[0, 1].set_title(f"Fraction valid across bands\n{location_label}")
    _apply_spatial_axes(axes[0, 1], spatial_context)
    fig.colorbar(valid_image, ax=axes[0, 1], label="Valid fraction")
    axes[1, 0].fill_between(x, q05, q95, color="0.75", label="5th–95th percentile")
    axes[1, 0].plot(x, median, color="#163b65", label="Median")
    axes[1, 0].set(xlabel=x_label, ylabel="Reflectance", title="Spectral distribution")
    axes[1, 0].set_ylim(*STANDARD_REFLECTANCE_RANGE)
    _clipping_note(axes[1, 0], spectra, STANDARD_REFLECTANCE_RANGE)
    axes[1, 0].legend()
    axes[1, 1].plot(x, valid_by_band, color="#2f6b3c")
    axes[1, 1].set(
        xlabel=x_label,
        ylabel="Valid fraction",
        title="Bounding-box valid fraction by wavelength",
        ylim=STANDARD_VALID_FRACTION_RANGE,
    )
    if wavelengths.size == cube.shape[0]:
        for axis in axes[1]:
            axis.set_xlim(*STANDARD_WAVELENGTH_RANGE_NM)
    for axis in axes[1]:
        axis.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_correction_overview(
    raw_cube: np.ndarray,
    corrected_cube: np.ndarray,
    wavelengths: np.ndarray,
    seam_before: dict[str, Any] | None,
    seam_after: dict[str, Any] | None,
    output_path: Path,
    *,
    location_label: str,
    spatial_context: dict[str, Any],
) -> Path:
    """Render before/after/difference maps with matched and zero-centered scales."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    band_index = (
        int(np.nanargmin(np.abs(wavelengths - 660.0)))
        if wavelengths.size == raw_cube.shape[0]
        else int(raw_cube.shape[0] // 2)
    )
    raw = np.asarray(raw_cube[band_index], dtype=np.float64)
    corrected = np.asarray(corrected_cube[band_index], dtype=np.float64)
    diff = corrected - raw
    x = (
        wavelengths
        if wavelengths.size == raw_cube.shape[0]
        else np.arange(raw_cube.shape[0])
    )
    spectral_axis = (1, 2)
    raw_median = np.nanmedian(raw_cube, axis=spectral_axis)
    corrected_median = np.nanmedian(corrected_cube, axis=spectral_axis)

    fig, axes = plt.subplots(2, 3, figsize=(16, 9), layout="constrained")
    fig.suptitle(f"BRDF and topographic correction\nLocation: {location_label}")
    extent = spatial_context.get("extent")
    wavelength_label = (
        f"{float(wavelengths[band_index]):.1f} nm (band {band_index})"
        if wavelengths.size == raw_cube.shape[0]
        else f"band {band_index}"
    )
    axes[0, 0].imshow(
        raw,
        cmap="viridis",
        vmin=STANDARD_REFLECTANCE_MAP_RANGE[0],
        vmax=STANDARD_REFLECTANCE_MAP_RANGE[1],
        extent=extent,
        origin="upper",
    )
    axes[0, 0].set_title(f"Before: {wavelength_label}\n{location_label}")
    _apply_spatial_axes(axes[0, 0], spatial_context)
    _clipping_note(axes[0, 0], raw, STANDARD_REFLECTANCE_MAP_RANGE)
    after_image = axes[0, 1].imshow(
        corrected,
        cmap="viridis",
        vmin=STANDARD_REFLECTANCE_MAP_RANGE[0],
        vmax=STANDARD_REFLECTANCE_MAP_RANGE[1],
        extent=extent,
        origin="upper",
    )
    axes[0, 1].set_title(f"After: {wavelength_label}\n{location_label}")
    _apply_spatial_axes(axes[0, 1], spatial_context)
    _clipping_note(axes[0, 1], corrected, STANDARD_REFLECTANCE_MAP_RANGE)
    fig.colorbar(after_image, ax=axes[0, :2], label="Reflectance", shrink=0.8)
    delta_image = axes[0, 2].imshow(
        diff,
        cmap="RdBu_r",
        norm=SymLogNorm(
            linthresh=STANDARD_CORRECTION_LINTHRESH,
            vmin=STANDARD_CORRECTION_DIFFERENCE_RANGE[0],
            vmax=STANDARD_CORRECTION_DIFFERENCE_RANGE[1],
            base=10,
        ),
        extent=extent,
        origin="upper",
    )
    axes[0, 2].set_title(f"After − before\n{location_label}")
    _apply_spatial_axes(axes[0, 2], spatial_context)
    _clipping_note(axes[0, 2], diff, STANDARD_CORRECTION_DIFFERENCE_RANGE)
    fig.colorbar(delta_image, ax=axes[0, 2], label="Reflectance difference")
    axes[1, 0].plot(x, raw_median, label="Before", color="0.35")
    axes[1, 0].plot(x, corrected_median, label="After", color="#163b65")
    axes[1, 0].set_title("Median spectrum preservation")
    axes[1, 0].set_ylabel("Reflectance")
    axes[1, 0].set_ylim(*STANDARD_REFLECTANCE_RANGE)
    _clipping_note(
        axes[1, 0],
        np.concatenate([raw_median, corrected_median]),
        STANDARD_REFLECTANCE_RANGE,
    )
    axes[1, 0].legend()
    axes[1, 1].plot(x, corrected_median - raw_median, color="#8b3f30")
    axes[1, 1].axhline(0, color="black", linewidth=0.8)
    axes[1, 1].set_title("Median correction by wavelength")
    axes[1, 1].set_ylabel("After − before")
    axes[1, 1].set_ylim(*STANDARD_CORRECTION_DIFFERENCE_RANGE)
    _clipping_note(
        axes[1, 1],
        corrected_median - raw_median,
        STANDARD_CORRECTION_DIFFERENCE_RANGE,
    )
    axes[1, 2].set_ylim(*STANDARD_SEAM_SCORE_RANGE)
    if seam_before and seam_after:
        before_values = [item["seam_score"] for item in seam_before["bands"]]
        after_values = [item["seam_score"] for item in seam_after["bands"]]
        seam_x = np.arange(len(before_values))
        axes[1, 2].plot(seam_x, before_values, label="Before", color="0.35")
        axes[1, 2].plot(seam_x, after_values, label="After", color="#8b3f30")
        axes[1, 2].axhline(1, color="black", linestyle="--", linewidth=0.8)
        axes[1, 2].legend()
        axes[1, 2].set_title("Chunk seam score")
        axes[1, 2].set_xlabel("Sampled band")
        _clipping_note(
            axes[1, 2],
            np.concatenate([before_values, after_values]),
            STANDARD_SEAM_SCORE_RANGE,
        )
    else:
        axes[1, 2].text(
            0.5,
            0.5,
            "NOT EVALUATED\nNo internal chunk boundaries",
            ha="center",
            va="center",
            transform=axes[1, 2].transAxes,
        )
        axes[1, 2].set_title("Chunk seam score")
    for axis in axes[1, :2]:
        axis.set_xlabel("Wavelength (nm) or band index")
        axis.grid(alpha=0.2)
        if wavelengths.size == raw_cube.shape[0]:
            axis.set_xlim(*STANDARD_WAVELENGTH_RANGE_NM)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_artifact_inventory(
    artifacts: list[dict[str, Any]],
    output_path: Path,
    *,
    title: str,
    location_label: str,
) -> Path:
    """Render a compact inventory of the files produced by a stage."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = [record for record in artifacts if record.get("exists")]
    labels = [str(record.get("name", "artifact")) for record in records]
    sizes_mb = [
        max(float(record.get("size_bytes") or 0) / 1_000_000, 1e-6)
        for record in records
    ]
    fig_height = max(4.0, min(9.0, 2.5 + 0.45 * max(1, len(records))))
    fig, axis = plt.subplots(figsize=(12, fig_height), layout="constrained")
    fig.suptitle(f"{title}\nLocation: {location_label}")
    if records:
        positions = np.arange(len(records))
        axis.barh(positions, sizes_mb, color="#315f76")
        axis.set_yticks(
            positions,
            labels=[
                label if len(label) <= 72 else f"…{label[-71:]}" for label in labels
            ],
        )
        axis.invert_yaxis()
        axis.set_xscale("log")
        axis.set_xlabel("File size (MB; logarithmic)")
        for position, size in zip(positions, sizes_mb, strict=True):
            axis.text(size, position, f"  {size:,.2f} MB", va="center", fontsize=8)
        axis.grid(axis="x", alpha=0.2)
    else:
        axis.text(0.5, 0.5, "No existing output artifacts", ha="center", va="center")
        axis.set_axis_off()
    axis.set_title("Persisted output inventory")
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_correction_parameters(
    model: dict[str, Any],
    geometry: dict[str, Any],
    wavelengths: np.ndarray,
    output_path: Path,
    *,
    location_label: str,
) -> Path:
    """Plot persisted BRDF coefficients and geometry without changing them."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), layout="constrained")
    fig.suptitle(f"Correction parameters\nLocation: {location_label}")

    plotted = False
    for key, color in (("iso", "#163b65"), ("vol", "#2f6b3c"), ("geo", "#9a4f1c")):
        try:
            values = np.asarray(model.get(key), dtype=np.float64)
        except (TypeError, ValueError):
            continue
        if not values.size:
            continue
        profile = np.nanmedian(values.reshape(-1, values.shape[-1]), axis=0)
        x = (
            wavelengths
            if wavelengths.size == profile.size
            else np.arange(1, profile.size + 1)
        )
        axes[0].plot(x, profile, label=key, color=color, linewidth=1.1)
        plotted = True
    axes[0].set_title("Persisted BRDF coefficient profiles")
    axes[0].set_ylabel("Coefficient")
    axes[0].set_ylim(*STANDARD_BRDF_COEFFICIENT_RANGE)
    axes[0].set_xlabel("Wavelength (nm)" if wavelengths.size else "Band index")
    if wavelengths.size:
        axes[0].set_xlim(*STANDARD_WAVELENGTH_RANGE_NM)
    axes[0].axhline(0, color="black", linewidth=0.7)
    axes[0].grid(alpha=0.2)
    if plotted:
        axes[0].legend()
    else:
        axes[0].text(
            0.5,
            0.5,
            "BRDF model coefficients unavailable",
            ha="center",
            va="center",
            transform=axes[0].transAxes,
        )

    fields = [
        name
        for name in (
            "solar_zn",
            "solar_az",
            "sensor_zn",
            "sensor_az",
            "slope",
            "aspect",
        )
        if isinstance(geometry.get(name), dict)
    ]
    means = [float(geometry[name].get("mean", np.nan)) for name in fields]
    lower = [float(geometry[name].get("min", np.nan)) for name in fields]
    upper = [float(geometry[name].get("max", np.nan)) for name in fields]
    positions = np.arange(len(fields))
    if fields:
        axes[1].scatter(positions, means, color="#163b65", label="Mean", zorder=3)
        for position, low, high in zip(positions, lower, upper, strict=True):
            axes[1].plot([position, position], [low, high], color="0.45", linewidth=2)
        axes[1].set_xticks(positions, labels=fields, rotation=30, ha="right")
        axes[1].legend()
    else:
        axes[1].text(
            0.5,
            0.5,
            "Geometry summaries unavailable",
            ha="center",
            va="center",
            transform=axes[1].transAxes,
        )
    axes[1].set_title("Persisted geometry summaries (unfiltered)")
    axes[1].set_ylabel("Radians")
    axes[1].set_ylim(*STANDARD_GEOMETRY_RANGE_RADIANS)
    axes[1].axhline(0, color="black", linewidth=0.7)
    axes[1].grid(axis="y", alpha=0.2)
    _clipping_note(
        axes[1], np.asarray([*means, *lower, *upper]), STANDARD_GEOMETRY_RANGE_RADIANS
    )
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_brightness_diagnostics(
    before: np.ndarray,
    after: np.ndarray,
    metrics: dict[str, Any],
    output_path: Path,
    *,
    product_label: str,
    location_label: str,
) -> Path:
    """Render the Python equivalent of the historical coefficient QMD plots."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    x_values = np.asarray(before, dtype=np.float64).reshape(-1)
    y_values = np.asarray(after, dtype=np.float64).reshape(-1)
    valid = np.isfinite(x_values) & np.isfinite(y_values)
    x_values, y_values = x_values[valid], y_values[valid]
    stride = max(1, int(np.ceil(x_values.size / 5000)))
    x_sample, y_sample = x_values[::stride], y_values[::stride]
    bands = metrics.get("bands", [])
    indices = np.array([row["band_index"] for row in bands], dtype=float)
    expected = np.array(
        [row.get("expected_percent", np.nan) for row in bands], dtype=float
    )
    inferred = np.array(
        [
            (row["fitted_gain"] - 1.0) * 100.0
            if row.get("fitted_gain") is not None
            else np.nan
            for row in bands
        ]
    )
    before_median = np.array(
        [row.get("before_median", np.nan) for row in bands], dtype=float
    )
    after_median = np.array(
        [row.get("after_median", np.nan) for row in bands], dtype=float
    )

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.4), layout="constrained")
    fig.suptitle(
        f"Brightness correction audit · {product_label}\nLocation: {location_label}"
    )
    axes[0].scatter(
        x_sample, y_sample, s=5, alpha=0.18, color="#315f76", rasterized=True
    )
    axes[0].plot(
        STANDARD_REFLECTANCE_RANGE,
        STANDARD_REFLECTANCE_RANGE,
        linestyle="--",
        color="black",
        linewidth=0.9,
        label="1:1",
    )
    axes[0].set(
        xlabel="Before brightness correction",
        ylabel="After brightness correction",
        title="Paired reflectance",
    )
    axes[0].set_xlim(*STANDARD_REFLECTANCE_RANGE)
    axes[0].set_ylim(*STANDARD_REFLECTANCE_RANGE)
    axes[0].set_aspect("equal", adjustable="box")
    axes[0].legend()
    _clipping_note(
        axes[0], np.concatenate([x_values, y_values]), STANDARD_REFLECTANCE_RANGE
    )

    axes[1].plot(indices, expected, marker="o", label="Configured", color="#163b65")
    axes[1].plot(
        indices,
        inferred,
        marker="x",
        linestyle="--",
        label="Fitted from products",
        color="#9a4f1c",
    )
    axes[1].axhline(0, color="black", linewidth=0.7)
    axes[1].set(
        xlabel="One-based band index",
        ylabel="Brightness adjustment (%)",
        title="Coefficient profile",
    )
    axes[1].set_ylim(*STANDARD_BRIGHTNESS_PERCENT_RANGE)
    axes[1].legend()
    _clipping_note(
        axes[1], np.concatenate([expected, inferred]), STANDARD_BRIGHTNESS_PERCENT_RANGE
    )

    axes[2].plot(indices, before_median, marker="o", label="Before", color="0.4")
    axes[2].plot(indices, after_median, marker="o", label="After", color="#163b65")
    axes[2].set(
        xlabel="One-based band index", ylabel="Median reflectance", title="Band medians"
    )
    axes[2].set_ylim(*STANDARD_REFLECTANCE_RANGE)
    axes[2].legend()
    _clipping_note(
        axes[2],
        np.concatenate([before_median, after_median]),
        STANDARD_REFLECTANCE_RANGE,
    )
    for axis in axes:
        axis.grid(alpha=0.2)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_parquet_overview(
    parquet_metrics: dict[str, Any],
    output_path: Path,
    *,
    location_label: str,
) -> Path:
    """Render extraction and merge structure from Parquet metadata."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tables = [table for table in parquet_metrics.get("tables", []) if "rows" in table]
    labels = []
    for table in tables:
        name = Path(str(table["path"])).stem
        kind = "merged" if "merged" in name.lower() else "extracted"
        short = name if len(name) <= 46 else f"…{name[-45:]}"
        labels.append((short, kind))
    positions = np.arange(len(tables))
    colors = ["#9a4f1c" if kind == "merged" else "#315f76" for _, kind in labels]
    rows = [max(int(table["rows"]), 1) for table in tables]
    columns = [int(table["columns"]) for table in tables]
    sizes = [
        max(float(table.get("size_bytes") or 0) / 1_000_000, 1e-6) for table in tables
    ]
    fig_height = max(6.0, min(13.0, 3.5 + 0.32 * max(1, len(tables))))
    fig, axes = plt.subplots(1, 3, figsize=(18, fig_height), layout="constrained")
    fig.suptitle(f"Parquet extraction and merge\nLocation: {location_label}")
    if tables:
        ylabels = [label for label, _ in labels]
        axes[0].barh(positions, rows, color=colors)
        axes[0].set_yticks(positions, labels=ylabels)
        axes[0].invert_yaxis()
        axes[0].set_xscale("log")
        axes[0].set_xlabel("Rows (logarithmic)")
        axes[0].set_title("Rows carried into analysis")
        axes[1].barh(positions, columns, color=colors)
        axes[1].set_yticks(positions, labels=[])
        axes[1].invert_yaxis()
        axes[1].set_xlabel("Columns")
        axes[1].set_title("Schema width")
        axes[2].barh(positions, sizes, color=colors)
        axes[2].set_yticks(positions, labels=[])
        axes[2].invert_yaxis()
        axes[2].set_xscale("log")
        axes[2].set_xlabel("File size (MB; logarithmic)")
        axes[2].set_title("Persisted table size")
        for axis in axes:
            axis.grid(axis="x", alpha=0.2)
        axes[2].text(
            0.98,
            0.02,
            "blue = extracted · orange = merged",
            transform=axes[2].transAxes,
            ha="right",
            va="bottom",
            fontsize=8,
        )
    else:
        for axis in axes:
            axis.text(
                0.5,
                0.5,
                "No readable Parquet tables",
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
            axis.set_axis_off()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


__all__ = [
    "format_location_label",
    "qa_plot_contract",
    "render_artifact_inventory",
    "render_brightness_diagnostics",
    "render_correction_parameters",
    "render_correction_overview",
    "render_envi_overview",
    "render_parquet_overview",
    "spatial_plot_context",
]
