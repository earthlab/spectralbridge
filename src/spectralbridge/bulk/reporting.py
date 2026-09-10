"""Publication and summary reporting from compact bulk result products."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np

from spectralbridge.qa_style import (
    DEFAULT_QA_STYLE,
    STATUS_COLORS,
    WEIGHTING_COLORS,
    WEIGHTING_MARKERS,
    apply_qa_axis_style,
    wavelength_pair_label,
)


def _number(value: Any, *, digits: int = 3, suffix: str = "") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unavailable"
    if not math.isfinite(number):
        return "Unavailable"
    return f"{number:.{digits}f}{suffix}"


def _save_pair(figure: Any, stem: Path, dpi: int) -> dict[str, str]:
    stem.parent.mkdir(parents=True, exist_ok=True)
    png = stem.with_suffix(".png")
    pdf = stem.with_suffix(".pdf")
    temporary_png = stem.with_suffix(".tmp.png")
    temporary_pdf = stem.with_suffix(".tmp.pdf")
    figure.savefig(temporary_png, dpi=dpi, bbox_inches="tight", facecolor="white")
    figure.savefig(temporary_pdf, bbox_inches="tight", facecolor="white")
    if temporary_png.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Invalid PNG output: {temporary_png}")
    if temporary_pdf.read_bytes()[:4] != b"%PDF":
        raise RuntimeError(f"Invalid PDF output: {temporary_pdf}")
    temporary_png.replace(png)
    temporary_pdf.replace(pdf)
    return {"png": png.as_posix(), "pdf": pdf.as_posix()}


def _metric_card(
    figure: Any,
    bounds: tuple[float, float, float, float],
    label: str,
    value: str,
    *,
    attention: bool = False,
) -> None:
    axis = figure.add_axes(bounds)
    axis.set_facecolor("#FFF8EB" if attention else "#F4F7F9")
    for spine in axis.spines.values():
        spine.set_color("#E69F00" if attention else "#D5DEE3")
    axis.set_xticks([])
    axis.set_yticks([])
    axis.text(0.06, 0.70, label, fontsize=9, color="#4A5258", va="center")
    axis.text(0.06, 0.28, value, fontsize=17, weight="bold", color="#17242C", va="center")


def render_bulk_summary_dashboard(
    overview: dict[str, Any],
    *,
    output_stem: str | Path,
    figure_dpi: int = DEFAULT_QA_STYLE.figure_dpi,
) -> dict[str, str]:
    """Render a one-page population QA dashboard from machine-readable metrics."""

    figure = plt.figure(figsize=(11, 8.5), facecolor="white")
    figure.text(0.055, 0.94, "Bulk translation QA", fontsize=22, weight="bold")
    figure.text(
        0.055,
        0.905,
        "Did the population analysis work, and what requires attention?",
        fontsize=11,
        color="#4A5258",
    )
    cards = [
        ("Accepted flightlines", f"{int(overview.get('accepted_flightlines', 0)):,}"),
        ("Sites", f"{int(overview.get('site_count', 0)):,}"),
        ("Observation rows", f"{int(overview.get('selected_observation_rows', 0)):,}"),
        ("Excluded candidates", f"{int(overview.get('excluded_candidate_count', 0)):,}"),
        ("Candidate coefficients", f"{int(overview.get('candidate_coefficient_count', 0)):,}"),
        ("Attention flags", f"{int(overview.get('attention_flag_count', 0)):,}"),
        ("Median R²", _number(overview.get("candidate_r2_median"))),
        ("Worst R²", _number(overview.get("candidate_r2_min"))),
        ("Median RMSE", _number(overview.get("candidate_rmse_median"))),
        ("Worst RMSE", _number(overview.get("candidate_rmse_max"))),
        (
            "Median |correction|",
            _number(overview.get("absolute_fitted_correction_percent_median"), digits=1, suffix="%"),
        ),
        (
            "Maximum |correction|",
            _number(overview.get("absolute_fitted_correction_percent_max"), digits=1, suffix="%"),
        ),
    ]
    left, top = 0.055, 0.72
    width, height = 0.14, 0.105
    gap_x, gap_y = 0.015, 0.025
    for index, (label, value) in enumerate(cards):
        row, column = divmod(index, 6)
        _metric_card(
            figure,
            (left + column * (width + gap_x), top - row * (height + gap_y), width, height),
            label,
            value,
            attention=(label == "Attention flags" and int(overview.get("attention_flag_count", 0)) > 0),
        )

    cases = [
        ("Most weighting-sensitive", overview.get("most_weighting_sensitive")),
        ("Most site-dependent", overview.get("most_site_dependent")),
        ("Weakest LOSO", overview.get("worst_loso")),
    ]
    y = 0.48
    figure.text(0.055, y + 0.055, "Priority review", fontsize=13, weight="bold")
    for label, case in cases:
        case = case if isinstance(case, dict) else {}
        figure.text(0.055, y, label, fontsize=9, color="#4A5258", va="top")
        figure.text(
            0.26,
            y,
            str(case.get("label") or "Unavailable"),
            fontsize=10,
            weight="bold",
            va="top",
        )
        figure.text(
            0.83,
            y,
            _number(case.get("value")),
            fontsize=10,
            ha="right",
            va="top",
        )
        y -= 0.065

    warning_count = int(overview.get("attention_flag_count", 0))
    status = "ATTENTION REQUIRED" if warning_count else "NO CONFIGURED WARNING TRIGGERED"
    color = STATUS_COLORS["attention" if warning_count else "normal"]
    figure.text(0.055, 0.21, status, fontsize=14, weight="bold", color=color)
    figure.text(
        0.055,
        0.165,
        "High R² alone does not establish sensor interchangeability. Review weighting, "
        "site dependence, correction magnitude, and held-out-site performance.",
        fontsize=10,
        color="#3F494F",
        wrap=True,
    )
    figure.text(
        0.055,
        0.075,
        f"Run {overview.get('analysis_run_id') or 'not recorded'}  •  "
        f"Sites: {', '.join(overview.get('sites', [])) or 'unavailable'}",
        fontsize=8.5,
        color="#68747B",
    )
    outputs = _save_pair(figure, Path(output_stem), figure_dpi)
    plt.close(figure)
    return outputs


def _publication_axes(title: str, row_count: int):
    height = max(5.8, min(10.5, 2.8 + row_count * 0.34))
    figure, axes = plt.subplots(
        1,
        3,
        figsize=(DEFAULT_QA_STYLE.manuscript_width_inches, height),
        sharey=True,
        constrained_layout=True,
    )
    figure.suptitle(title, fontsize=DEFAULT_QA_STYLE.title_font_size, weight="bold")
    return figure, axes


def _set_pair_axis(axis: Any, labels: Sequence[str], panel: str, title: str) -> None:
    y = np.arange(len(labels))
    axis.set_yticks(y, labels)
    axis.invert_yaxis()
    axis.set_title(f"{panel}  {title}", fontsize=10, loc="left", weight="bold")
    apply_qa_axis_style(axis)


def render_bulk_publication_figures(
    *,
    weighting: Sequence[dict[str, Any]],
    pair_summaries: Sequence[dict[str, Any]],
    flightline: Sequence[dict[str, Any]],
    site: Sequence[dict[str, Any]],
    loso: Sequence[dict[str, Any]],
    output_dir: str | Path,
    figure_dpi: int = DEFAULT_QA_STYLE.figure_dpi,
) -> dict[str, dict[str, str]]:
    """Render three manuscript-width figures from compact result tables only."""

    output_dir = Path(output_dir)
    labels = [wavelength_pair_label(row) for row in pair_summaries]
    keys = [(str(row["translation_pair"]), int(row["band_index"])) for row in pair_summaries]
    y = np.arange(len(keys), dtype=float)
    by_key: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in weighting:
        by_key.setdefault((str(row["translation_pair"]), int(row["band_index"])), []).append(row)

    figure, axes = _publication_axes("Translation performance", len(labels))
    for level in WEIGHTING_COLORS:
        values = []
        r2 = []
        correction = []
        for key in keys:
            row = next((item for item in by_key.get(key, []) if item.get("analysis_level") == level), {})
            values.append(row.get("slope", np.nan))
            r2.append(row.get("r2", np.nan))
            correction.append(abs(float(row["fitted_correction_percent"])) if row.get("fitted_correction_percent") is not None else np.nan)
        axes[0].scatter(values, y, s=24, color=WEIGHTING_COLORS[level], marker=WEIGHTING_MARKERS[level], label=level.replace("_", " "))
        axes[1].scatter(r2, y, s=24, color=WEIGHTING_COLORS[level], marker=WEIGHTING_MARKERS[level])
        axes[2].scatter(correction, y, s=24, color=WEIGHTING_COLORS[level], marker=WEIGHTING_MARKERS[level])
    _set_pair_axis(axes[0], labels, "A", "Slope")
    _set_pair_axis(axes[1], labels, "B", "R²")
    _set_pair_axis(axes[2], labels, "C", "|Correction| (%)")
    axes[0].axvline(1.0, color="#333333", linestyle="--", linewidth=1)
    axes[0].legend(loc="lower center", bbox_to_anchor=(1.62, -0.12), ncol=3, frameon=False, fontsize=8)
    performance = _save_pair(figure, output_dir / "translation_performance", figure_dpi)
    plt.close(figure)

    flight_by = {(str(row["translation_pair"]), int(row["band_index"])): row for row in flightline}
    site_by = {(str(row["translation_pair"]), int(row["band_index"])): row for row in site}
    figure, axes = _publication_axes("Translation stability", len(labels))
    metrics = (
        ([row.get("candidate_slope_spread") for row in pair_summaries], "Weighting slope spread"),
        ([flight_by.get(key, {}).get("slope_iqr") for key in keys], "Flightline slope IQR"),
        ([site_by.get(key, {}).get("slope_range") for key in keys], "Site slope range"),
    )
    for axis, (values, title), panel, color in zip(
        axes,
        metrics,
        ("A", "B", "C"),
        (WEIGHTING_COLORS["pixel_pooled"], WEIGHTING_COLORS["flightline_balanced"], WEIGHTING_COLORS["site_balanced"]),
        strict=True,
    ):
        axis.barh(y, [np.nan if value is None else float(value) for value in values], color=color, alpha=0.85)
        _set_pair_axis(axis, labels, panel, title)
    stability = _save_pair(figure, output_dir / "translation_stability", figure_dpi)
    plt.close(figure)

    loso_by = {(str(row["translation_pair"]), int(row["band_index"])): row for row in loso}
    figure, axes = _publication_axes("Generalization and failure cases", len(labels))
    metrics = (
        ([loso_by.get(key, {}).get("held_out_r2_min") for key in keys], "Worst held-out R²"),
        ([loso_by.get(key, {}).get("held_out_rmse_max") for key in keys], "Worst held-out RMSE"),
        ([row.get("warning_count") for row in pair_summaries], "Attention flags"),
    )
    colors = ("#0072B2", "#D55E00", STATUS_COLORS["attention"])
    for axis, (values, title), panel, color in zip(axes, metrics, ("A", "B", "C"), colors, strict=True):
        axis.barh(y, [np.nan if value is None else float(value) for value in values], color=color, alpha=0.85)
        _set_pair_axis(axis, labels, panel, title)
    generalization = _save_pair(figure, output_dir / "generalization_and_failures", figure_dpi)
    plt.close(figure)
    return {
        "translation_performance": performance,
        "translation_stability": stability,
        "generalization_and_failures": generalization,
    }


def render_bulk_pdf_report(
    *,
    summary_png: str | Path,
    publication_figures: dict[str, dict[str, str]],
    diagnostic_figures: Sequence[str],
    overview: dict[str, Any],
    flags: Sequence[dict[str, Any]],
    output_pdf: str | Path,
) -> Path:
    """Assemble a self-contained PDF from already-computed compact QA outputs."""

    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_pdf.with_suffix(".tmp.pdf")
    page_paths = [Path(summary_png)]
    page_paths.extend(Path(value["png"]) for value in publication_figures.values())
    page_paths.extend(Path(path) for path in diagnostic_figures)
    with PdfPages(temporary) as pdf:
        for page_path in page_paths:
            figure = plt.figure(figsize=(11, 8.5), facecolor="white")
            axis = figure.add_axes([0.02, 0.02, 0.96, 0.96])
            axis.imshow(plt.imread(page_path))
            axis.axis("off")
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)
        figure = plt.figure(figsize=(8.5, 11), facecolor="white")
        figure.text(0.07, 0.95, "Ranked attention and provenance", fontsize=18, weight="bold")
        y = 0.90
        for row in list(flags)[:18]:
            label = wavelength_pair_label(row)
            detail = f"{label}: {row.get('flag_code')} ({row.get('analysis_scope')})"
            figure.text(0.07, y, detail, fontsize=8.5, va="top")
            y -= 0.038
        if not flags:
            figure.text(0.07, y, "No configured warning triggered.", fontsize=10)
        figure.text(
            0.07,
            0.08,
            "Machine-readable overview:\n" + json.dumps(overview, indent=2, sort_keys=True)[:3500],
            fontsize=6.5,
            family="monospace",
            va="bottom",
        )
        pdf.savefig(figure, bbox_inches="tight")
        plt.close(figure)
    if temporary.read_bytes()[:4] != b"%PDF":
        raise RuntimeError(f"Invalid PDF output: {temporary}")
    temporary.replace(output_pdf)
    return output_pdf


__all__ = [
    "render_bulk_pdf_report",
    "render_bulk_publication_figures",
    "render_bulk_summary_dashboard",
]
