"""Compact, restart-safe drone QA dashboard and report assembly."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import textwrap
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from spectralbridge import __version__
from spectralbridge.qa_style import STATUS_COLORS


def _safe_read_qa_png(qa_png: Path):
    try:
        return plt.imread(qa_png), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _read_payload(base_dir: Path, qa_summary: dict[str, Any] | None) -> dict[str, Any]:
    if qa_summary is not None:
        return qa_summary
    path = base_dir / "drone_qa_summary.json"
    if not path.is_file():
        return {"platform": "drone", "files": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _metric_from_translation_qa(file_audit: dict[str, Any]) -> dict[str, Any]:
    band_rows: list[dict[str, Any]] = []
    for raw_path in file_audit.get("translation_qa_paths", []):
        path = Path(str(raw_path))
        if path.suffix.lower() != ".json" or not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        band_rows.extend(payload.get("bands", []))
    shifts = [
        abs(value)
        for row in band_rows
        if (value := _finite(row.get("median_relative_shift_percent"))) is not None
    ]
    valid = [
        value
        for row in band_rows
        if (value := _finite(row.get("valid_translated_fraction"))) is not None
    ]
    return {
        "largest_translation_shift_percent": max(shifts, default=None),
        "valid_pixel_fraction": min(valid, default=None),
    }


def _landsat_metrics(file_audit: dict[str, Any]) -> dict[str, Any]:
    comparison = file_audit.get("landsat_comparison")
    if not isinstance(comparison, dict):
        return {
            "status": "not_requested",
            "median_rmse": None,
            "median_correlation": None,
        }
    rows = comparison.get("bands", [])
    rmse: list[float] = []
    correlation: list[float] = []
    for row in rows:
        metrics = row.get("drone_vs_actual") or {}
        if (value := _finite(metrics.get("rmse"))) is not None:
            rmse.append(value)
        if (value := _finite(metrics.get("correlation"))) is not None:
            correlation.append(value)
    return {
        "status": comparison.get("status", "unavailable"),
        "reason": comparison.get("reason"),
        "median_rmse": float(sorted(rmse)[len(rmse) // 2]) if rmse else None,
        "median_correlation": (
            float(sorted(correlation)[len(correlation) // 2])
            if correlation
            else None
        ),
    }


def _dashboard_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    files = payload.get("files", []) if isinstance(payload.get("files"), list) else []
    file_metrics = []
    warning_count = 0
    for item in files:
        translation = _metric_from_translation_qa(item)
        landsat = _landsat_metrics(item)
        flags = item.get("flags") if isinstance(item.get("flags"), dict) else {}
        warning_count += len(item.get("qa_warnings", []))
        warning_count += int(str(item.get("status", "")).startswith("failed"))
        warning_count += sum(
            bool(flags.get(name))
            for name in (
                "topo_fallback_due_to_nodata",
                "brdf_fallback_due_to_nodata",
                "correction_failed",
            )
        )
        products = item.get("translation_products", [])
        range_statuses = [
            check.get("status")
            for product in products
            for check in (product.get("training_range_checks") or {}).values()
            if isinstance(check, dict)
        ]
        if any(
            status not in {"overlap", "no_valid_source_values"}
            for status in range_statuses
        ):
            warning_count += 1
        file_metrics.append(
            {
                "flight_stem": item.get("flight_stem"),
                "source_type": item.get("input_source_type") or "source",
                "source": item.get("input_source_path")
                or item.get("source_path")
                or item.get("input_path"),
                "ingest_status": (
                    "complete" if item.get("prepared_h5_path") else "unavailable"
                ),
                "acquisition_datetime": item.get("acquisition_datetime_used")
                or item.get("acquisition_datetime"),
                "topo_status": (
                    "applied" if flags.get("topo_applied") else "not applied"
                ),
                "brdf_status": (
                    "applied" if flags.get("brdf_applied") else "not applied"
                ),
                "translation_status": (
                    "complete" if products else "not requested or unavailable"
                ),
                "coefficient_weighting": next(
                    (product.get("analysis_level") for product in products if product),
                    None,
                ),
                "coefficient_run_id": next(
                    (product.get("analysis_run_id") for product in products if product),
                    None,
                ),
                "range_compatibility": (
                    "attention"
                    if any(status != "overlap" for status in range_statuses)
                    else "compatible"
                    if range_statuses
                    else "not evaluated"
                ),
                "landsat": landsat,
                "neon_status": (
                    "included"
                    if payload.get("comparison_neon_product")
                    else "not supplied"
                ),
                **translation,
            }
        )
    return {
        "run_id": payload.get("run_id"),
        "flight_count": len(files),
        "success_count": int(payload.get("success_count", 0)),
        "failure_count": int(payload.get("failed_other_count", 0)),
        "warning_count": warning_count,
        "files": file_metrics,
    }


def _fmt(value: Any, *, digits: int = 3, suffix: str = "") -> str:
    number = _finite(value)
    return "Unavailable" if number is None else f"{number:.{digits}f}{suffix}"


def _render_dashboard(metrics: dict[str, Any], output_png: Path) -> Path:
    output_png.parent.mkdir(parents=True, exist_ok=True)
    figure = plt.figure(figsize=(11, 8.5), facecolor="white")
    figure.text(0.055, 0.94, "Drone pipeline QA", fontsize=22, weight="bold")
    figure.text(
        0.055,
        0.905,
        "Did this run work, and what should I worry about?",
        fontsize=11,
        color="#4A5258",
    )
    warning_count = int(metrics["warning_count"])
    status_color = STATUS_COLORS["attention" if warning_count else "normal"]
    figure.text(
        0.94,
        0.94,
        "ATTENTION" if warning_count else "COMPLETE",
        ha="right",
        fontsize=14,
        weight="bold",
        color=status_color,
    )
    figure.text(
        0.055,
        0.85,
        f"{metrics['flight_count']} flights  •  {metrics['success_count']} successful  •  "
        f"{metrics['failure_count']} failed  •  {warning_count} warnings",
        fontsize=13,
        weight="bold",
    )
    headers = (
        "Flight / source",
        "Ingest & correction",
        "Translation",
        "External validation",
    )
    x_positions = (0.055, 0.30, 0.54, 0.77)
    for x, header in zip(x_positions, headers, strict=True):
        figure.text(x, 0.79, header, fontsize=10, weight="bold", color="#344149")
    y = 0.745
    for row in metrics["files"][:6]:
        source = Path(str(row.get("source") or "unknown")).name
        figure.text(
            0.055,
            y,
            str(row.get("flight_stem") or source),
            fontsize=9,
            weight="bold",
            va="top",
        )
        figure.text(
            0.055,
            y - 0.022,
            f"{source[:26]} · {row.get('source_type')}\n"
            f"{row.get('acquisition_datetime') or 'acquisition time unavailable'}",
            fontsize=7.5,
            color="#68747B",
            va="top",
        )
        figure.text(
            0.30,
            y,
            f"H5 {row['ingest_status']}\nTopo {row['topo_status']} · "
            f"BRDF {row['brdf_status']}",
            fontsize=8,
            va="top",
        )
        valid = row.get("valid_pixel_fraction")
        valid_label = _fmt(100.0 * float(valid), digits=1, suffix="%") if valid is not None else "Unavailable"
        figure.text(
            0.54,
            y,
            f"{row['translation_status']}\n"
            f"{row.get('coefficient_weighting') or 'weighting unavailable'}\n"
            f"valid {valid_label} · max shift "
            f"{_fmt(row.get('largest_translation_shift_percent'), digits=1, suffix='%')}\n"
            f"range {row.get('range_compatibility')} · run "
            f"{str(row.get('coefficient_run_id') or 'unavailable')[:12]}",
            fontsize=8,
            va="top",
        )
        landsat = row["landsat"]
        figure.text(
            0.77,
            y,
            f"Landsat {landsat.get('status')}\nRMSE "
            f"{_fmt(landsat.get('median_rmse'))} · r "
            f"{_fmt(landsat.get('median_correlation'))}\n"
            f"NEON {row.get('neon_status')}",
            fontsize=8,
            va="top",
        )
        y -= 0.105
    if len(metrics["files"]) > 6:
        figure.text(
            0.055,
            y,
            f"+ {len(metrics['files']) - 6} additional flights in machine-readable QA JSON",
            fontsize=8,
            color="#68747B",
        )
    figure.text(
        0.055,
        0.045,
        "Translated Landsat-like products are derived from corrected MicaSense and are not actual Landsat observations.\n"
        f"Run {metrics.get('run_id') or 'not recorded'}  •  SpectralBridge {__version__}",
        fontsize=8.5,
        color="#68747B",
    )
    temporary = output_png.with_suffix(".tmp.png")
    figure.savefig(temporary, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    temporary.replace(output_png)
    return output_png


def _signature(payload: dict[str, Any], qa_pngs: list[Path]) -> str:
    ignored = {
        "created_utc",
        "total_wall_time_seconds",
        "average_successful_flight_seconds",
        "qa_summary_pdf",
        "qa_summary_pdf_filename",
        "qa_summary_figure",
        "qa_report_stage",
        "qa_report_error",
    }
    stable = {key: value for key, value in payload.items() if key not in ignored}
    artifacts = [
        {
            "path": str(path.resolve()),
            "size": path.stat().st_size,
            "mtime_ns": path.stat().st_mtime_ns,
        }
        for path in qa_pngs
    ]
    encoded = json.dumps(
        {"schema_version": 2, "qa": stable, "artifacts": artifacts},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def render_drone_qa_report(
    base_dir: str | Path,
    *,
    qa_summary: dict[str, Any] | None = None,
    output_pdf: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Render/reuse the final dashboard and PDF using compact QA products only."""

    base_dir = Path(base_dir).expanduser().resolve()
    payload = _read_payload(base_dir, qa_summary)
    output_pdf = (
        Path(output_pdf).expanduser().resolve()
        if output_pdf
        else base_dir / "qa_summary.pdf"
    )
    summary_png = base_dir / "qa" / "summary" / "drone_qa_summary.png"
    summary_json = base_dir / "qa" / "summary" / "drone_qa_summary.json"
    stage_record = base_dir / "qa" / "report.stage.json"
    qa_pngs = sorted(
        path
        for path in base_dir.rglob("*.png")
        if path.is_file() and path.resolve() != summary_png.resolve()
    )
    signature = _signature(payload, qa_pngs)
    if (
        not force
        and stage_record.is_file()
        and summary_png.is_file()
        and output_pdf.is_file()
    ):
        try:
            previous = json.loads(stage_record.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            previous = {}
        if (
            previous.get("stage_signature_sha256") == signature
            and output_pdf.read_bytes()[:4] == b"%PDF"
        ):
            return {**previous, "status": "reused"}

    metrics = _dashboard_metrics(payload)
    _render_dashboard(metrics, summary_png)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(
        json.dumps(metrics, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_pdf.with_suffix(".tmp.pdf")
    with PdfPages(temporary) as pdf:
        for index, qa_png in enumerate([summary_png, *qa_pngs]):
            image, image_error = _safe_read_qa_png(qa_png)
            figure = plt.figure(
                figsize=(11, 8.5 if index == 0 else 14), facecolor="white"
            )
            axis = figure.add_axes([0.03, 0.03, 0.94, 0.94])
            if image is not None:
                axis.imshow(image)
            else:
                axis.text(
                    0.5,
                    0.55,
                    "QA image unavailable",
                    ha="center",
                    va="center",
                    fontsize=14,
                )
                axis.text(
                    0.5,
                    0.45,
                    "\n".join(textwrap.wrap(image_error or "Unknown error", 70)),
                    ha="center",
                    va="center",
                    fontsize=9,
                )
            axis.axis("off")
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)
    temporary.replace(output_pdf)
    result = {
        "schema_version": 2,
        "status": "complete",
        "stage": "final_drone_qa_report",
        "stage_signature_sha256": signature,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "spectralbridge_version": __version__,
        "source_policy": "compact_qa_json_and_existing_qa_figures_only",
        "source_rasters_opened": False,
        "summary_png": str(summary_png),
        "summary_json": str(summary_json),
        "report_pdf": str(output_pdf),
        "metrics": metrics,
    }
    stage_record.parent.mkdir(parents=True, exist_ok=True)
    stage_record.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return {**result, "status": "created"}


def build_drone_qa_summary(
    base_dir: Path,
    output_html: Path | None = None,
    pattern: str = "*__qa.png",
    *,
    qa_summary: dict[str, Any] | None = None,
    force: bool = False,
) -> Path:
    """Backward-compatible wrapper returning the final drone QA PDF path."""

    del pattern
    result = render_drone_qa_report(
        base_dir,
        qa_summary=qa_summary,
        output_pdf=output_html,
        force=force,
    )
    return Path(result["report_pdf"])


__all__ = ["build_drone_qa_summary", "render_drone_qa_report"]
