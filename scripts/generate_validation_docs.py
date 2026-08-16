#!/usr/bin/env python3
"""Generate publication-facing validation pages from campaign JSON records."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from spectralbridge.validation import load_campaign

if __package__:
    from .validation_docs_content import (
        MODULE_GUIDES,
        STAGE_CHECK_GUIDES,
        STAGE_GUIDES,
        CheckGuide,
        FieldGuide,
        ImageGuide,
        stage_check_guide_key,
    )
else:
    from validation_docs_content import (
        MODULE_GUIDES,
        STAGE_CHECK_GUIDES,
        STAGE_GUIDES,
        CheckGuide,
        FieldGuide,
        ImageGuide,
        stage_check_guide_key,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "validation" / "results"
DOCS_DIR = REPO_ROOT / "docs" / "validation"
REAL_STAGE_ROOT = DOCS_DIR / "artifacts" / "r10c-l002-20210915" / "qa" / "stages"
MODULES = (
    ("neon_download", "NEON HDF5 download"),
    ("h5_to_envi", "HDF5 to raw ENVI"),
    ("topographic_correction", "Topographic correction"),
    ("brdf_correction", "BRDF correction"),
    ("sensor_convolution", "Sensor convolution"),
    ("parquet_csv", "Parquet extraction and CSV conversion"),
    ("save_restart", "Save and restart behavior"),
    ("qa_plots", "QA plots and diagnostics"),
)


def _inline(value: Any, *, limit: int = 110) -> str:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif value is None:
        text = "null"
    elif isinstance(value, float):
        text = f"{value:.6g}"
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    else:
        text = str(value)
    text = text.replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _mapping(mapping: dict[str, Any]) -> str:
    return "; ".join(
        f"`{key}`={_inline(value, limit=55)}" for key, value in mapping.items()
    )


def _campaigns() -> list[dict[str, Any]]:
    paths = sorted(RESULTS_DIR.glob("*.json"))
    if not paths:
        raise FileNotFoundError(
            f"No validation campaign JSON files found in {RESULTS_DIR}"
        )
    return [load_campaign(path) for path in paths]


def _group_results(campaigns: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for campaign in campaigns:
        for result in campaign["results"]:
            enriched = dict(result)
            enriched["campaign_id"] = campaign["campaign_id"]
            enriched["mode"] = campaign["mode"]
            grouped[result["module"]].append(enriched)
    return grouped


def _summary(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(results),
        "passed": sum(result["status"] == "passed" for result in results),
        "failed": sum(result["status"] == "failed" for result in results),
        "skipped": sum(result["status"] == "skipped" for result in results),
    }


def _field_table(fields: tuple[FieldGuide, ...]) -> list[str]:
    lines = ["| Field | Why it is recorded |", "| --- | --- |"]
    lines.extend(f"| `{field.name}` | {field.meaning} |" for field in fields)
    return lines


def _check_table(checks: tuple[CheckGuide, ...]) -> list[str]:
    lines = [
        "| Check | Question | PASS means | If it does not pass |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| `{check.name}` | {check.question} | {check.pass_condition} | "
        f"{check.review_if_not_pass} |"
        for check in checks
    )
    return lines


def _image_blocks(
    images: tuple[ImageGuide, ...], *, path_prefix: str = ""
) -> list[str]:
    """Render linked figure cards with paths relative to the generated page."""

    lines = ['<div class="sb-validation-grid">']
    for image in images:
        image_path = f"{path_prefix}{image.path}"
        lines.extend(
            [
                '  <figure class="sb-validation-figure">',
                f'    <a href="{image_path}"><img src="{image_path}" alt="{image.alt}" loading="lazy"></a>',
                f"    <figcaption>{image.caption}</figcaption>",
                "  </figure>",
            ]
        )
    lines.extend(["</div>", ""])
    return lines


def _module_page(
    slug: str,
    label: str,
    results: list[dict[str, Any]],
    *,
    last_updated: str,
) -> str:
    summary = _summary(results)
    guide = MODULE_GUIDES[slug]
    pass_rate = (
        100.0 * summary["passed"] / summary["total"] if summary["total"] else 0.0
    )
    lines = [
        "---",
        f"title: Validation — {label}",
        "---",
        "",
        f"# Validation: {label}",
        "",
        (
            f"**Recorded evidence:** {summary['total']} variations; {summary['passed']} passed, "
            f"{summary['failed']} failed, and {summary['skipped']} skipped "
            f"({pass_rate:.1f}% pass rate over all recorded variations)."
        ),
        "",
        '!!! info "Evidence boundary"',
        "    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. "
        "It validates software contracts and diagnostics, not real-flightline scientific accuracy.",
        "",
        "## What this module test exercises",
        "",
        guide.purpose,
        "",
        f"**Implementation exercised:** {guide.implementation}",
        "",
        "### Inputs varied",
        "",
        *_field_table(guide.inputs),
        "",
        "### Checks and how to interpret them",
        "",
        *_check_table(guide.checks),
        "",
        "### Diagnostics recorded for every variation",
        "",
        *_field_table(guide.diagnostics),
        "",
        "## Input variations and results",
        "",
        "On narrow screens, scroll the table horizontally to see every diagnostic and check.",
        "",
        "| Variation | Input variation | Result | Diagnostics | Explicit checks |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        status = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}[
            result["status"]
        ]
        checks = "; ".join(
            f"{name}={'✓' if value else '✗'}"
            for name, value in result.get("checks", {}).items()
        )
        diagnostics = _mapping(result.get("diagnostics", {})) or "—"
        if result.get("error"):
            diagnostics += f"; error={_inline(result['error'])}"
        if result.get("skip_reason"):
            diagnostics += f"; skip={_inline(result['skip_reason'])}"
        lines.append(
            f"| `{result['variation_id']}`<br>{_inline(result['description'])} "
            f"| {_mapping(result.get('inputs', {})) or '—'} | **{status}** "
            f"| {diagnostics} | {checks or '—'} |"
        )

    lines.extend(
        [
            "",
            "## What a passing result establishes",
            "",
            guide.establishes,
            "",
            '!!! warning "What it does not establish"',
            f"    {guide.does_not_establish}",
            "",
            f"The matching real stage checks are explained in the [stage QA test guide]({guide.stage_qa_link}).",
            "",
            "## Example from the real R10C test run",
            "",
            *_image_blocks(guide.images, path_prefix="../"),
            "The figure is evidence from one completed flightline, not a replacement for the variation table above. "
            "Open the [real flightline walkthrough](real-data-example.md) for exact values and limitations.",
            "",
            "## Expansion to 100 real variations",
            "",
            "The repository includes a [live 100-flightline campaign specification](https://github.com/earthlab/spectralbridge/blob/main/validation/campaigns/neon-live-100.example.json). "
            "It requires a pinned inventory of real flightline IDs plus an explicit compute, storage, and network allocation. "
            "Live results must be stored as a new campaign record; they must not overwrite this offline baseline.",
            "",
            "## Reproduce or expand this module",
            "",
            "```bash",
            "# Fast local evidence matrix (five variations per module)",
            "python scripts/run_validation_campaign.py --iterations-per-module 5",
            "",
            "# Exercise 100 deterministic small-data variations per module",
            "python scripts/run_validation_campaign.py --iterations-per-module 100 \\",
            "  --output validation/results/offline-contract-100.json",
            "",
            "python scripts/generate_validation_docs.py",
            "```",
            "",
            "The 100-case offline command scales contract variation and randomized synthetic inputs. It does **not** substitute for 100 distinct NEON downloads.",
            "",
            f"Last updated: {last_updated}",
            "",
        ]
    )
    return "\n".join(lines)


def _index_page(
    campaigns: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
    *,
    last_updated: str,
) -> str:
    lines = [
        "---",
        "title: Validation evidence",
        "---",
        "",
        "# Validation evidence",
        "",
        "This section records how SpectralBridge functions behave across explicit input variations. "
        "Each row comes from a machine-readable campaign result rather than a hand-written success claim.",
        "",
        "## How to use this section",
        "",
        "Validation is presented in three connected layers:",
        "",
        "1. **Module contract pages** explain the inputs varied, every Boolean check, every recorded diagnostic, and the limits of the evidence.",
        "2. **[Stage QA test guide](stage-qa-guide.md)** explains the checks emitted by a completed pipeline in acquisition-to-table order.",
        "3. **[Real flightline walkthrough](real-data-example.md)** interprets one 2.4 GB R10C run and links its complete HTML and JSON reports.",
        "",
        "A green offline contract does not imply scientific validation. A real stage `WARN` does not imply a crash. Read the stated evidence boundary on each page before comparing statuses.",
        "",
        "## Current evidence",
        "",
        "| Module | Variations | Passed | Failed | Skipped | Detailed test guide | Real stage QA |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for slug, label in MODULES:
        summary = _summary(grouped.get(slug, []))
        guide = MODULE_GUIDES[slug]
        lines.append(
            f"| {label} | {summary['total']} | {summary['passed']} | {summary['failed']} "
            f"| {summary['skipped']} | [Inputs, checks, and results]({slug}.md) "
            f"| [Matching stage]({guide.stage_qa_link}) |"
        )
    lines.extend(
        [
            "",
            "## Two validation tiers",
            "",
            "1. **Offline contract campaign:** small deterministic inputs, safe for local or CI execution. It checks dimensions, numerical invariants, schemas, restart behavior, and diagnostic generation.",
            "2. **Live NEON campaign:** opt-in real data selected from a pinned inventory. It measures download reliability, full-stage behavior, correction support, performance, and QA usefulness across sites and acquisition conditions.",
            "",
            "These tiers must remain separate. Repeating synthetic inputs 100 times can expose numerical and state bugs, but it cannot establish network reliability or scientific validity across 100 real flightlines.",
            "",
            "## Example figures from the real test run",
            "",
            "The figures below are generated artifacts from R10C · D10 · L002 · 2021-09-15. Their axes and map scales follow plot-contract version 1.1 so later runs can be compared directly.",
            "",
            *_image_blocks(
                (
                    MODULE_GUIDES["h5_to_envi"].images[0],
                    MODULE_GUIDES["topographic_correction"].images[0],
                    MODULE_GUIDES["sensor_convolution"].images[1],
                    MODULE_GUIDES["parquet_csv"].images[0],
                )
            ),
            "",
            "## Recorded campaigns",
            "",
            "| Campaign | Mode | Revision | Dirty tree | Generated (UTC) | Total | Passed | Failed |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for campaign in campaigns:
        summary = campaign["summary"]
        lines.append(
            f"| `{campaign['campaign_id']}` | {campaign['mode']} | `{campaign.get('git_revision', 'unknown')}` "
            f"| {_inline(campaign.get('git_dirty'))} | {campaign.get('generated_utc', 'unknown')} "
            f"| {summary['total']} | {summary['passed']} | {summary['failed']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation rules",
            "",
            "- A **pass** means every explicit software-contract check for that variation passed.",
            "- A **failure** remains visible and includes its diagnostics or exception.",
            "- A **skip** must state why evidence was not collected.",
            "- Synthetic checks must not be described as external scientific validation.",
            "- QA thresholds should be changed only after a representative real-data campaign and scientific review.",
            "",
            "The underlying JSON records live in `validation/results/` and are the source of truth for these pages.",
            "",
            f"Last updated: {last_updated}",
            "",
        ]
    )
    return "\n".join(lines)


def _real_stage_reports() -> dict[str, tuple[Path, dict[str, Any]]]:
    reports: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(REAL_STAGE_ROOT.glob("*/stage_qa.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        reports[str(report["stage_id"])] = (path, report)
    return reports


def _observed_values(checks: list[dict[str, Any]]) -> str:
    values = [check.get("value") for check in checks]
    if values and all(value is True for value in values):
        return f"{len(values)}/{len(values)} present"
    rendered = [_inline(value, limit=28) for value in values]
    return ", ".join(rendered[:6]) + ("…" if len(rendered) > 6 else "")


def _thresholds(check: dict[str, Any]) -> str:
    warn = check.get("warn_threshold")
    fail = check.get("fail_threshold")
    if warn is None and fail is None:
        return "Categorical contract"
    return f"warn `{_inline(warn)}`; fail `{_inline(fail)}`"


def _stage_qa_page(*, last_updated: str) -> str:
    reports = _real_stage_reports()
    lines = [
        "---",
        "title: Stage QA test guide",
        "---",
        "",
        "# Stage QA test guide",
        "",
        "This page explains every check family in the automatic stage reports, in pipeline order. "
        "Observed values and figures come from the completed R10C · D10 · L002 · 2021-09-15 run. "
        "The explanations are the reusable contract; the observed values are one example.",
        "",
        '!!! info "Three different questions"',
        "    `output_exists` asks whether software produced an artifact. Numerical checks ask whether the artifact obeys an implementation or provisional QA contract. Scientific validation asks whether the result is accurate across representative real conditions. A `PASS` in one category does not answer the other two.",
        "",
        "## Status language",
        "",
        "| Status | Meaning | Required response |",
        "| --- | --- | --- |",
        "| `PASS` | Evaluated value meets its current contract. | Continue, while retaining provenance and limitations. |",
        "| `WARN` | Pipeline completed, but evidence needs interpretation. | Review the named metric and figure; do not hide or automatically delete the value. |",
        "| `FAIL` | A required artifact is missing or an evaluated metric crosses its fail rule. | Stop scientific interpretation until the cause is understood. |",
        "| `NOT EVALUATED` | Available artifacts cannot support the requested diagnostic. | Read the recorded reason; do not reinterpret absence as a pass. |",
        "",
        "## Real-run stage summary",
        "",
        "| Stage | Status | Checks | Full report |",
        "| --- | --- | ---: | --- |",
    ]
    for stage in STAGE_GUIDES:
        path, report = reports[stage["stage_id"]]
        html_path = path.with_name("stage_qa.html").relative_to(DOCS_DIR).as_posix()
        anchor = str(stage["heading"]).lower().replace(" ", "-")
        lines.append(
            f"| [{stage['heading']}](#{anchor}) "
            f"| **{report['status']}** | {len(report['checks'])} "
            f"| [HTML]({html_path}) |"
        )

    for stage in STAGE_GUIDES:
        path, report = reports[stage["stage_id"]]
        html_path = path.with_name("stage_qa.html").relative_to(DOCS_DIR).as_posix()
        json_path = path.relative_to(DOCS_DIR).as_posix()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for check in report["checks"]:
            grouped[stage_check_guide_key(str(check["check_id"]))].append(check)
        lines.extend(
            [
                "",
                f"## {stage['heading']}",
                "",
                f"**Observed status: {report['status']}** · [open HTML]({html_path}) · [open JSON]({json_path})",
                "",
                str(stage["purpose"]),
                "",
                "### Checks in this stage",
                "",
                "| Check family | Count | Observed | Value(s) | Rule | What it asks | What to review |",
                "| --- | ---: | --- | --- | --- | --- | --- |",
            ]
        )
        for key, checks in grouped.items():
            guide = STAGE_CHECK_GUIDES[key]
            statuses = ", ".join(sorted({str(check["status"]) for check in checks}))
            lines.append(
                f"| `{guide.name}` | {len(checks)} | **{statuses}** | "
                f"{_observed_values(checks)} | {_thresholds(checks[0])} | "
                f"{guide.question} {guide.pass_condition} | {guide.review_if_not_pass} |"
            )
        lines.extend(
            [
                "",
                "### Example figure from R10C",
                "",
                *_image_blocks(stage["images"], path_prefix="../"),
                "### Explicitly unavailable diagnostics",
                "",
            ]
        )
        unavailable = report.get("unavailable_diagnostics", [])
        if unavailable:
            lines.extend(
                f"- **`{item['diagnostic']}` — NOT EVALUATED:** {item['reason']}"
                for item in unavailable
            )
        else:
            lines.append("- None for this stage in the real run.")

    lines.extend(
        [
            "",
            "## Reproduce the stage reports",
            "",
            "```bash",
            "spectralbridge-stage-qa \\",
            "  --flightline-dir outputs/<flightline_id> \\",
            "  --mode deep --force",
            "```",
            "",
            "`deep` changes deterministic sampling depth, not the scientific correction. "
            "See [Stage-by-stage scientific QA](../pipeline/stage-qa.md) for schemas, fixed plot ranges, and implementation details.",
            "",
            f"Last updated: {last_updated}",
            "",
        ]
    )
    return "\n".join(lines)


def generated_files() -> dict[Path, str]:
    campaigns = _campaigns()
    grouped = _group_results(campaigns)
    last_updated = max(
        str(campaign.get("generated_utc", "unknown"))[:10] for campaign in campaigns
    )
    files = {
        DOCS_DIR / "index.md": _index_page(
            campaigns, grouped, last_updated=last_updated
        ),
        DOCS_DIR / "stage-qa-guide.md": _stage_qa_page(last_updated=last_updated),
    }
    for slug, label in MODULES:
        files[DOCS_DIR / f"{slug}.md"] = _module_page(
            slug,
            label,
            grouped.get(slug, []),
            last_updated=last_updated,
        )
    return files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail if generated pages are stale."
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stale = []
    for path, content in generated_files().items():
        expected = content.rstrip() + "\n"
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                stale.append(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8")
        print(path.relative_to(REPO_ROOT))
    if stale:
        print("Stale validation pages:")
        for path in stale:
            print(f"  {path.relative_to(REPO_ROOT)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
