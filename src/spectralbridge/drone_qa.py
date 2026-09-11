"""Standalone translation and optional common-support QA for drone runs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from spectralbridge.drone_translation import DroneTranslationPlan
from spectralbridge.envi import hdr_to_dict, memmap_bsq
from spectralbridge.qa_style import (
    DEFAULT_QA_STYLE,
    SENSOR_COLORS,
    STATUS_COLORS,
    apply_qa_axis_style,
    sensor_display_label,
)


DRONE_TRANSLATION_PUBLICATION_PANEL_COUNT = 3


def _finite_without_nodata(values: np.ndarray, nodata: float) -> np.ndarray:
    valid = np.isfinite(values)
    if math.isnan(nodata):
        valid &= ~np.isnan(values)
    else:
        valid &= ~np.isclose(values, nodata, atol=1e-6)
    return valid


def _bounded_pair_sample(
    source: np.ndarray,
    target: np.ndarray,
    valid: np.ndarray,
    *,
    maximum: int = 50_000,
) -> tuple[np.ndarray, np.ndarray]:
    indices = np.flatnonzero(valid.reshape(-1))
    if indices.size > maximum:
        positions = np.linspace(0, indices.size - 1, maximum, dtype=np.int64)
        indices = indices[positions]
    return source.reshape(-1)[indices], target.reshape(-1)[indices]


def render_drone_translation_qa(
    *,
    corrected_img: str | Path,
    translated_img: str | Path,
    plan: DroneTranslationPlan,
    translation_result: dict[str, Any],
    output_png: str | Path,
) -> tuple[Path, Path, dict[str, Any]]:
    """Render native-corrected versus Landsat-like translated band QA."""

    corrected_img = Path(corrected_img)
    translated_img = Path(translated_img)
    output_png = Path(output_png)
    output_json = output_png.with_suffix(".json")
    corrected_header = hdr_to_dict(corrected_img.with_suffix(".hdr"))
    translated_header = hdr_to_dict(translated_img.with_suffix(".hdr"))
    corrected = memmap_bsq(corrected_img, corrected_header)
    translated = memmap_bsq(translated_img, translated_header)
    nodata = float(corrected_header.get("data ignore value", -9999.0))
    scale = float(corrected_header.get("reflectance scale factor", 1.0) or 1.0)
    if scale <= 0:
        scale = 1.0

    band_records: list[dict[str, Any]] = []
    samples: list[tuple[np.ndarray, np.ndarray]] = []
    for output_index, band in enumerate(plan.bands):
        source_values = np.asarray(
            corrected[band.native_source_band_index - 1], dtype=np.float32
        )
        target_values = np.asarray(translated[output_index], dtype=np.float32)
        valid = _finite_without_nodata(source_values, nodata) & _finite_without_nodata(
            target_values, nodata
        )
        source_sample, target_sample = _bounded_pair_sample(
            source_values, target_values, valid
        )
        samples.append((source_sample, target_sample))
        difference = target_sample - source_sample
        denominator = np.abs(source_sample) > 1e-8
        relative = (
            100.0 * difference[denominator] / source_sample[denominator]
            if np.any(denominator)
            else np.array([], dtype=np.float32)
        )
        physical_target = target_sample * np.float32(scale)
        band_records.append(
            {
                "source_band_index": band.native_source_band_index,
                "target_band_index": band.target_band_index,
                "source_wavelength_nm": band.native_source_wavelength_nm,
                "target_wavelength_nm": band.target_wavelength_nm,
                "slope": band.slope,
                "intercept": band.intercept,
                "r2_bulk": band.r2,
                "valid_pixel_count": int(valid.sum()),
                "valid_translated_fraction": float(valid.mean()),
                "source_median": float(np.median(source_sample))
                if source_sample.size
                else None,
                "translated_median": float(np.median(target_sample))
                if target_sample.size
                else None,
                "median_absolute_shift": float(np.median(np.abs(difference)))
                if difference.size
                else None,
                "median_relative_shift_percent": float(np.median(relative))
                if relative.size
                else None,
                "translated_below_zero_fraction": float(np.mean(physical_target < 0))
                if physical_target.size
                else None,
                "translated_above_one_fraction": float(np.mean(physical_target > 1))
                if physical_target.size
                else None,
            }
        )

    columns = min(3, len(plan.bands))
    rows = int(math.ceil(len(plan.bands) / columns)) + 1
    fig, axes = plt.subplots(rows, columns, figsize=(5 * columns, 4 * rows))
    axes_array = np.atleast_1d(axes).reshape(rows, columns)
    for index, (band, (source_sample, target_sample)) in enumerate(
        zip(plan.bands, samples)
    ):
        ax = axes_array[index // columns, index % columns]
        if source_sample.size:
            ax.hexbin(source_sample, target_sample, gridsize=45, mincnt=1, cmap="viridis")
            low = float(min(source_sample.min(), target_sample.min()))
            high = float(max(source_sample.max(), target_sample.max()))
            ax.plot([low, high], [low, high], linestyle="--", color="black", linewidth=1)
        ax.set_title(
            f"{band.native_source_wavelength_nm:g} → {band.target_wavelength_nm:g} nm"
        )
        ax.set_xlabel("Corrected native MicaSense")
        ax.set_ylabel("Landsat-like translated")
        ax.grid(alpha=0.2)
    for index in range(len(plan.bands), (rows - 1) * columns):
        axes_array[index // columns, index % columns].axis("off")
    summary_ax = axes_array[-1, 0]
    summary_ax.axis("off")
    summary_ax.text(
        0,
        1,
        "\n".join(
            [
                f"Target: {plan.target_sensor}",
                f"Weighting: {plan.analysis_level}",
                f"Bulk run: {plan.analysis_run_id}",
                f"Coefficient SHA-256: {plan.coefficient_sha256[:16]}…",
                "Equation: target = slope × source + intercept",
                "Product semantics: Landsat-like translated (not actual Landsat)",
            ]
        ),
        va="top",
        fontsize=10,
    )
    if columns > 1:
        table_ax = axes_array[-1, 1]
        table_ax.axis("off")
        table_ax.table(
            cellText=[
                [
                    record["target_band_index"],
                    f"{record['slope']:.4g}",
                    f"{record['intercept']:.4g}",
                    f"{record['valid_translated_fraction']:.1%}",
                ]
                for record in band_records
            ],
            colLabels=["Band", "Slope", "Intercept", "Valid"],
            loc="center",
        )
    for index in range(2, columns):
        axes_array[-1, index].axis("off")
    fig.suptitle(f"Drone translation QA — {translated_img.stem}")
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=150)
    plt.close(fig)

    payload = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "product_semantics": "landsat_like_translated",
        "corrected_micasense_product": str(corrected_img),
        "translated_product": str(translated_img),
        "translation_provenance": translation_result,
        "bands": band_records,
        "warnings": list(translation_result.get("warnings", [])),
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_png, output_json, payload


def render_common_support_comparison(
    comparison: dict[str, Any],
    *,
    output_png: str | Path,
) -> tuple[Path, Path]:
    """Render compact actual-Landsat and optional three-way metric summaries."""

    output_png = Path(output_png)
    output_json = output_png.with_suffix(".json")
    bands = comparison.get("bands", [])
    has_neon = comparison.get("comparison_neon_product") is not None
    pair_names = ["drone_vs_actual"]
    if has_neon:
        pair_names.extend(["neon_vs_actual", "drone_vs_neon"])
    x = np.arange(len(bands))
    width = 0.8 / max(1, len(pair_names))
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    metric_axes = zip(
        axes.flat,
        ("mean_bias", "mae", "rmse", "correlation"),
        strict=True,
    )
    for panel, (ax, metric) in zip("ABCD", metric_axes, strict=True):
        for pair_index, pair_name in enumerate(pair_names):
            values = []
            for band in bands:
                value = (band.get(pair_name) or {}).get(metric)
                values.append(float(value) if value is not None else np.nan)
            ax.bar(
                x + (pair_index - (len(pair_names) - 1) / 2) * width,
                values,
                width=width,
                label=pair_name.replace("_", " "),
            )
        ax.set_title(metric.replace("_", " ").title())
        ax.set_xticks(x)
        ax.set_xticklabels(
            [
                f"B{band.get('target_band_index')}\n"
                f"{float(band.get('target_wavelength_nm')):g} nm"
                if band.get("target_wavelength_nm") is not None
                else f"B{band.get('target_band_index')}"
                for band in bands
            ]
        )
        ax.set_xlabel("Target band and center wavelength")
        ax.grid(axis="y", alpha=0.2)
        ax.text(-0.08, 1.04, panel, transform=ax.transAxes, fontsize=12, weight="bold")
    axes[0, 0].legend(fontsize=8)
    actual = comparison.get("actual_landsat", {})
    fig.suptitle(
        "Common-support validation — "
        f"{actual.get('product_id', 'actual Landsat')}"
    )
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=150)
    fig.savefig(output_png.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    output_json.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    return output_png, output_json


def render_drone_translation_publication(
    translation_qa: dict[str, Any],
    *,
    output_stem: str | Path,
) -> dict[str, str]:
    """Render a compact three-panel translation figure from QA JSON values."""

    output_stem = Path(output_stem)
    bands = translation_qa.get("bands", [])
    figure, axes = plt.subplots(
        1,
        3,
        figsize=(DEFAULT_QA_STYLE.manuscript_width_inches, 3.4),
        constrained_layout=True,
    )
    if not bands:
        for panel, axis in zip("ABC", axes, strict=True):
            axis.text(0.5, 0.5, "Unavailable\nNo translated bands", ha="center", va="center")
            axis.text(-0.12, 1.03, panel, transform=axis.transAxes, fontsize=12, weight="bold")
            axis.axis("off")
    else:
        x = np.arange(len(bands))
        labels = [
            f"MS {float(row['source_wavelength_nm']):g} →\n"
            f"B{int(row['target_band_index'])} · {float(row['target_wavelength_nm']):g} nm"
            for row in bands
        ]
        axes[0].plot(
            x,
            [row.get("source_median", np.nan) for row in bands],
            marker="o",
            color=SENSOR_COLORS["micasense"],
            label="Corrected MicaSense",
        )
        axes[0].plot(
            x,
            [row.get("translated_median", np.nan) for row in bands],
            marker="s",
            color=SENSOR_COLORS["drone_landsat_like"],
            label="Translated Landsat-like",
        )
        axes[0].set_title("Band medians", fontsize=10, loc="left")
        axes[0].set_ylabel("Reflectance value")
        axes[0].legend(frameon=False, fontsize=7, loc="best")
        shifts = [
            float(row["median_relative_shift_percent"])
            if row.get("median_relative_shift_percent") is not None
            else np.nan
            for row in bands
        ]
        axes[1].bar(
            x,
            shifts,
            color=[
                STATUS_COLORS["attention"]
                if np.isfinite(value) and abs(value) > 20
                else SENSOR_COLORS["drone_landsat_like"]
                for value in shifts
            ],
        )
        axes[1].axhline(0.0, color="#333333", linewidth=0.8)
        axes[1].set_title("Median translation shift", fontsize=10, loc="left")
        axes[1].set_ylabel("Change from source (%)")
        axes[2].scatter(
            [row.get("slope", np.nan) for row in bands],
            x,
            color=SENSOR_COLORS["drone_landsat_like"],
            marker="D",
            s=30,
        )
        axes[2].axvline(1.0, color="#333333", linestyle="--", linewidth=0.9)
        axes[2].set_title("Coefficient and range", fontsize=10, loc="left")
        axes[2].set_xlabel("Slope (identity = 1)")
        for index, row in enumerate(bands):
            axes[2].text(
                axes[2].get_xlim()[1],
                index,
                f"R² {float(row['r2_bulk']):.3f}" if row.get("r2_bulk") is not None else "R² n/a",
                fontsize=7,
                va="center",
                ha="right",
            )
        for panel, axis in zip("ABC", axes, strict=True):
            axis.text(-0.12, 1.03, panel, transform=axis.transAxes, fontsize=12, weight="bold")
            apply_qa_axis_style(axis)
        for axis in axes[:2]:
            axis.set_xticks(x, labels, rotation=35, ha="right", fontsize=7)
        axes[2].set_yticks(x, labels, fontsize=7)
        axes[2].invert_yaxis()
    target = sensor_display_label(
        str((translation_qa.get("translation_provenance") or {}).get("target_sensor", "Landsat target"))
    )
    figure.suptitle(
        f"Drone cross-sensor translation quality · {target}",
        fontsize=DEFAULT_QA_STYLE.title_font_size,
        weight="bold",
    )
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    png = output_stem.with_suffix(".png")
    pdf = output_stem.with_suffix(".pdf")
    figure.savefig(png, dpi=DEFAULT_QA_STYLE.figure_dpi, bbox_inches="tight", facecolor="white")
    figure.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return {"png": str(png), "pdf": str(pdf)}


__all__ = [
    "DRONE_TRANSLATION_PUBLICATION_PANEL_COUNT",
    "render_common_support_comparison",
    "render_drone_translation_publication",
    "render_drone_translation_qa",
]
