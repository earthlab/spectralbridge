"""Human-readable stage reports and cross-stage synthesis."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from .paths import CombinedQAPaths
from .plots import (
    STANDARD_NEGATIVE_FRACTION_RANGE,
    STANDARD_REFLECTANCE_RANGE,
    STANDARD_VALID_FRACTION_RANGE,
    format_location_label,
    qa_plot_contract,
)
from .schema import SCHEMA_VERSION, QAStatus, StageQAReport


_STATUS_COLOR = {
    QAStatus.PASS.value: "#2f6b3c",
    QAStatus.WARN.value: "#a65f00",
    QAStatus.FAIL.value: "#a12b2b",
    QAStatus.NOT_EVALUATED.value: "#5c6670",
}


def _value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return html.escape(str(value))


def render_stage_html(report: StageQAReport, output_path: Path) -> Path:
    """Write a standalone deterministic HTML report for one stage."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    checks = "\n".join(
        "<tr>"
        f"<td>{html.escape(check.check_id)}</td>"
        f"<td class='status' style='color:{_STATUS_COLOR[check.status.value]}'>"
        f"{check.status.value}</td>"
        f"<td>{_value(check.value)} {html.escape(check.units or '')}</td>"
        f"<td>{_value(check.warn_threshold)} / {_value(check.fail_threshold)}</td>"
        f"<td>{html.escape(check.interpretation)}</td>"
        f"<td>{html.escape(check.reason or '')}</td>"
        "</tr>"
        for check in report.checks
    )
    interpretations = (
        "".join(f"<li>{html.escape(item)}</li>" for item in report.interpretation)
        or "<li>No automated interpretation was available.</li>"
    )
    unavailable = "".join(
        "<li><strong>NOT EVALUATED — "
        f"{html.escape(item['diagnostic'])}:</strong> {html.escape(item['reason'])}</li>"
        for item in report.unavailable_diagnostics
    )
    plots = "".join(
        f"<figure><img src='{html.escape(path)}' alt='Stage QA diagnostic'>"
        f"<figcaption>{html.escape(path)}</figcaption></figure>"
        for path in report.plots
    )
    footprint = report.metrics.get("spatial_footprint", {})
    footprint_section = ""
    if footprint:
        footprint_section = (
            "<h2>Spatial footprint interpretation</h2>"
            "<p>The observed flight footprint occupies "
            f"<strong>{_value(footprint.get('bounding_box_footprint_fraction'))}</strong> "
            "of the rectangular raster extent. Valid spectral support within that "
            "footprint is "
            f"<strong>{_value(footprint.get('within_footprint_valid_fraction'))}</strong>. "
            "Structural background remains recorded as no-data; QA did not crop, "
            "mask, or rewrite it.</p>"
        )
    spectral_quality = report.metrics.get("spectral_quality", {})
    spectral_section = ""
    if spectral_quality:
        bad_count = spectral_quality.get("known_bad_band_count")
        if bad_count is None:
            spectral_summary = (
                "A complete wavelength vector was unavailable, so retained bands "
                "could not be classified. No data were changed."
            )
        else:
            spectral_summary = (
                f"<strong>{_value(bad_count)}</strong> known poor-quality wavelength "
                "bands are retained and labeled. No values were masked, filtered, "
                "replaced, or removed. The all-band fraction above 1.2 is "
                f"<strong>{_value(spectral_quality.get('all_band_overbright_fraction'))}</strong>; "
                "the fraction over wavelengths labeled usable is "
                f"<strong>{_value(spectral_quality.get('usable_band_overbright_fraction'))}</strong>."
            )
        spectral_section = (
            f"<h2>Retained spectral-quality labels</h2><p>{spectral_summary}</p>"
        )
    content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(report.stage_name)} QA</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#182433}}
h1,h2{{color:#123565}} .badge{{display:inline-block;padding:.35rem .7rem;border:2px solid currentColor;border-radius:999px;font-weight:700}}
table{{border-collapse:collapse;width:100%;font-size:.94rem}} th,td{{border:1px solid #d7dee8;padding:.55rem;vertical-align:top}} th{{background:#eef3f8;text-align:left}}
.status{{font-weight:800}} figure{{margin:1.5rem 0}} img{{display:block;max-width:100%;height:auto}} code,pre{{background:#f4f6f8}} pre{{padding:1rem;overflow:auto}}
</style></head><body>
<p>Schema {html.escape(report.schema_version)} · Mode {html.escape(report.mode)}</p>
<h1>{html.escape(report.stage_name)}</h1>
<p class="badge" style="color:{_STATUS_COLOR[report.status.value]}">{report.status.value}</p>
<h2>Automated interpretation</h2><ul>{interpretations}</ul>
{footprint_section}{spectral_section}
<h2>Checks</h2><table><thead><tr><th>Check</th><th>Status</th><th>Value</th><th>Warn / fail</th><th>Meaning</th><th>Reason</th></tr></thead><tbody>{checks}</tbody></table>
<h2>Diagnostics</h2>{plots or "<p>No plot was applicable to this stage.</p>"}
<h2>Unavailable diagnostics</h2><ul>{unavailable or "<li>None.</li>"}</ul>
<h2>Machine-readable metrics</h2><pre>{html.escape(json.dumps(report.metrics, indent=2, sort_keys=True))}</pre>
<h2>Provenance</h2><pre>{html.escape(json.dumps(report.provenance, indent=2, sort_keys=True))}</pre>
</body></html>"""
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _cross_stage_findings(stage_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    failed = [item["stage_name"] for item in stage_payloads if item["status"] == "FAIL"]
    warned = [item["stage_name"] for item in stage_payloads if item["status"] == "WARN"]
    if failed:
        findings.append(
            {
                "status": "FAIL",
                "finding": "One or more stages failed QA.",
                "evidence": {"stages": failed},
            }
        )
    elif warned:
        findings.append(
            {
                "status": "WARN",
                "finding": "The pipeline completed with stage-level warnings.",
                "evidence": {"stages": warned},
            }
        )
    else:
        findings.append(
            {
                "status": "PASS",
                "finding": "No evaluated stage check failed or warned.",
                "evidence": {"evaluated_stages": len(stage_payloads)},
            }
        )

    retained_bad_bands = []
    for item in stage_payloads:
        spectral_quality = item.get("metrics", {}).get("spectral_quality", {})
        count = spectral_quality.get("known_bad_band_count")
        if count:
            retained_bad_bands.append(
                {
                    "stage": item["stage_name"],
                    "known_bad_band_count": count,
                    "classification_mode": spectral_quality.get("classification_mode"),
                    "data_modified": spectral_quality.get("data_modified"),
                }
            )
    if retained_bad_bands:
        findings.append(
            {
                "status": "WARN",
                "finding": "Known poor-quality wavelength bands were retained and explicitly labeled; no masking or replacement was applied.",
                "evidence": {"stages": retained_bad_bands},
            }
        )

    correction = next(
        (
            item
            for item in stage_payloads
            if item["stage_id"] == "brdf_topographic_correction"
        ),
        None,
    )
    if correction:
        metrics = correction.get("metrics", {})
        before = metrics.get("seam_before", {}).get("max_seam_score")
        after = metrics.get("seam_after", {}).get("max_seam_score")
        if before is not None and after is not None:
            change = float(after) - float(before)
            findings.append(
                {
                    "status": "WARN" if change > 0.5 else "PASS",
                    "finding": (
                        "Chunk-aligned discontinuity increased after correction."
                        if change > 0.5
                        else "No large increase in sampled chunk seam score after correction."
                    ),
                    "evidence": {
                        "max_seam_score_before": before,
                        "max_seam_score_after": after,
                        "change": change,
                    },
                }
            )
    return findings


def _render_pipeline_evolution(
    stage_payloads: list[dict[str, Any]],
    output_path: Path,
    *,
    location_label: str,
) -> Path | None:
    rows = []
    for item in stage_payloads:
        metrics = item.get("metrics", {})
        summary = metrics.get("reflectance")
        footprint = metrics.get("spatial_footprint", {})
        if summary and summary.get("q50") is not None:
            rows.append(
                (
                    item["stage_name"],
                    summary["q50"],
                    footprint.get(
                        "within_footprint_valid_fraction",
                        summary["valid_fraction"],
                    ),
                    summary["negative_fraction"],
                )
            )
    if not rows:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels = [row[0] for row in rows]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].plot(labels, [row[1] for row in rows], marker="o")
    axes[0].set_title("Median reflectance")
    axes[0].set_ylim(*STANDARD_REFLECTANCE_RANGE)
    axes[1].plot(labels, [row[2] for row in rows], marker="o")
    axes[1].set_title("Valid fraction within footprint")
    axes[1].set_ylim(*STANDARD_VALID_FRACTION_RANGE)
    axes[2].plot(labels, [row[3] for row in rows], marker="o")
    axes[2].set_title("Negative fraction")
    axes[2].set_ylim(*STANDARD_NEGATIVE_FRACTION_RANGE)
    axes[2].axhline(0.01, color="#a65f00", linestyle="--", linewidth=0.8)
    axes[2].axhline(0.05, color="#a12b2b", linestyle=":", linewidth=0.8)
    for axis in axes:
        axis.tick_params(axis="x", rotation=35)
        axis.grid(alpha=0.2)
    fig.suptitle(
        f"Pipeline evolution from available stage reports\nLocation: {location_label}"
    )
    fig.tight_layout()
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return output_path


def assemble_combined_report(flightline_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Assemble stage reports and derive cross-stage findings."""

    flightline_dir = Path(flightline_dir)
    paths = CombinedQAPaths(flightline_dir)
    stage_jsons = sorted((flightline_dir / "qa" / "stages").glob("*/stage_qa.json"))
    stage_payloads = [
        json.loads(path.read_text(encoding="utf-8")) for path in stage_jsons
    ]
    location_label = format_location_label(flightline_dir.name)
    findings = _cross_stage_findings(stage_payloads)
    statuses = [item["status"] for item in stage_payloads]
    overall = (
        "FAIL"
        if "FAIL" in statuses
        else "WARN"
        if "WARN" in statuses
        else "PASS"
        if "PASS" in statuses
        else "NOT EVALUATED"
    )
    evolution = _render_pipeline_evolution(
        stage_payloads,
        paths.evolution_png,
        location_label=location_label,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "flightline_id": flightline_dir.name,
        "status": overall,
        "plot_contract": {
            **qa_plot_contract(),
            "location_label": location_label,
        },
        "stage_reports": [
            str(path.relative_to(flightline_dir)) for path in stage_jsons
        ],
        "stages": [],
        "what_we_learn_from_the_full_pipeline": findings,
        "plots": [str(evolution.relative_to(paths.directory))] if evolution else [],
        "not_evaluated": [
            {
                "diagnostic": "sensor_triangle_path_and_cycle_consistency",
                "reason": "No fitted translation-edge artifacts are produced by the canonical NEON processing run.",
            },
            {
                "diagnostic": "landsat_direct_nbar_comparability",
                "reason": "Direct Landsat Collection 2 NBAR is acquired outside this NEON flightline pipeline.",
            },
        ],
    }
    for stage_json, item in zip(stage_jsons, stage_payloads, strict=True):
        metrics = item.get("metrics", {})
        reflectance = metrics.get("reflectance", {})
        footprint = metrics.get("spatial_footprint", {})
        spectral_quality = metrics.get("spectral_quality", {})
        paired = metrics.get("paired_change", {})
        parquet = metrics.get("parquet", {})
        payload["stages"].append(
            {
                "stage_id": item["stage_id"],
                "stage_name": item["stage_name"],
                "status": item["status"],
                "interpretation": item.get("interpretation", []),
                "report": str(
                    stage_json.with_suffix(".html").relative_to(flightline_dir)
                ),
                "highlights": {
                    # Compatibility fields retain the original all-band,
                    # bounding-box summaries. New report columns use the
                    # explicitly stratified metrics below.
                    "valid_fraction": reflectance.get("valid_fraction"),
                    "median_reflectance": reflectance.get("q50"),
                    "negative_fraction": reflectance.get("negative_fraction"),
                    "above_1_2_fraction": reflectance.get("overbright_fraction"),
                    "bounding_box_footprint_fraction": footprint.get(
                        "bounding_box_footprint_fraction"
                    ),
                    "within_footprint_valid_fraction": footprint.get(
                        "within_footprint_valid_fraction"
                    ),
                    "usable_band_above_1_2_fraction": spectral_quality.get(
                        "usable_band_overbright_fraction"
                    ),
                    "known_bad_band_count": spectral_quality.get(
                        "known_bad_band_count"
                    ),
                    "absolute_correction_q99": paired.get("absolute_difference_q99"),
                    "readable_parquet_outputs": (
                        len(
                            [
                                table
                                for table in parquet.get("tables", [])
                                if "rows" in table
                            ]
                        )
                        if parquet
                        else None
                    ),
                },
            }
        )
    paths.directory.mkdir(parents=True, exist_ok=True)
    paths.json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    stage_rows = "".join(
        "<tr>"
        f"<td><a href='../../{html.escape(item['report'])}'>{html.escape(item['stage_name'])}</a></td>"
        f"<td style='color:{_STATUS_COLOR[item['status']]};font-weight:800'>{item['status']}</td>"
        f"<td>{_value(item['highlights']['bounding_box_footprint_fraction'])}</td>"
        f"<td>{_value(item['highlights']['within_footprint_valid_fraction'])}</td>"
        f"<td>{_value(item['highlights']['median_reflectance'])}</td>"
        f"<td>{_value(item['highlights']['negative_fraction'])}</td>"
        f"<td>{_value(item['highlights']['above_1_2_fraction'])}</td>"
        f"<td>{_value(item['highlights']['usable_band_above_1_2_fraction'])}</td>"
        f"<td>{_value(item['highlights']['known_bad_band_count'])}</td>"
        f"<td>{_value(item['highlights']['absolute_correction_q99'])}</td>"
        f"<td>{_value(item['highlights']['readable_parquet_outputs'])}</td>"
        "</tr>"
        for item in payload["stages"]
    )
    finding_items = "".join(
        f"<li><strong>{html.escape(item['status'])}:</strong> "
        f"{html.escape(item['finding'])}<pre>{html.escape(json.dumps(item['evidence'], indent=2))}</pre></li>"
        for item in findings
    )
    image = (
        f"<img src='{html.escape(paths.evolution_png.name)}' alt='Pipeline evolution'>"
        if evolution
        else "<p>Pipeline evolution was not evaluable.</p>"
    )
    paths.html.write_text(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Combined SpectralBridge QA</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#182433}}h1,h2{{color:#123565}}table{{border-collapse:collapse;width:100%;display:block;overflow-x:auto}}td,th{{border:1px solid #d7dee8;padding:.6rem;white-space:nowrap}}img{{max-width:100%;height:auto}}pre{{background:#f4f6f8;padding:.8rem;overflow:auto}}</style></head><body>
<h1>Combined QA — {html.escape(flightline_dir.name)}</h1><p><strong>Overall status: {overall}</strong></p>
<h2>Stage summary</h2><table><tr><th>Stage</th><th>Status</th><th>Footprint / bounding box</th><th>Valid within footprint</th><th>Median reflectance</th><th>Negative fraction</th><th>All-band &gt;1.2</th><th>Usable-band &gt;1.2</th><th>Known bad bands retained</th><th>Correction |Δ| q99</th><th>Readable tables</th></tr>{stage_rows}</table>
<h2>Pipeline evolution</h2>{image}
<h2>What we learn from the full pipeline</h2><ul>{finding_items}</ul>
<h2>Not evaluated</h2><pre>{html.escape(json.dumps(payload["not_evaluated"], indent=2))}</pre>
</body></html>""",
        encoding="utf-8",
    )
    return paths.html, payload


__all__ = ["assemble_combined_report", "render_stage_html"]
