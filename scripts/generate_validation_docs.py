#!/usr/bin/env python3
"""Generate publication-facing validation pages from campaign JSON records."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from spectralbridge.validation import load_campaign


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "validation" / "results"
DOCS_DIR = REPO_ROOT / "docs" / "validation"
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
QA_USE = {
    "neon_download": (
        "Track availability, artifact size, retry count, and failure category. A live campaign "
        "should expose site/month combinations that need clearer download diagnostics."
    ),
    "h5_to_envi": (
        "Compare source and output dimensions, value error, wavelength/header integrity, and "
        "NoData handling. These checks should become visible in ENVI/header QA summaries."
    ),
    "topographic_correction": (
        "Report finite support, correction magnitude, and terrain/illumination relationships before "
        "and after correction. Synthetic correlation reduction is a contract diagnostic, not proof "
        "of physical accuracy on real terrain."
    ),
    "brdf_correction": (
        "Use identity-model error to detect numerical drift, then add real-flightline diagnostics for "
        "view-angle support, coefficient stability, and correction magnitude by wavelength."
    ),
    "sensor_convolution": (
        "Surface numerical error against an independent weighted-average reference, output range, "
        "and target-band support. QA should flag missing or near-zero spectral-response support."
    ),
    "parquet_csv": (
        "Expose row preservation, spectral-column counts, coordinate fields, and CSV parity. These "
        "are direct candidates for the Parquet/merge page of the QA report."
    ),
    "save_restart": (
        "Use hashes, expected byte counts, and non-mutation checks to distinguish a valid reusable "
        "artifact from a merely present file."
    ),
    "qa_plots": (
        "Verify that injected correction deltas and NoData patterns appear in machine-readable QA. "
        "Visual legibility still requires image review or approved perceptual baselines."
    ),
}


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
    return "; ".join(f"`{key}`={_inline(value, limit=55)}" for key, value in mapping.items())


def _campaigns() -> list[dict[str, Any]]:
    paths = sorted(RESULTS_DIR.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"No validation campaign JSON files found in {RESULTS_DIR}")
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


def _module_page(
    slug: str,
    label: str,
    results: list[dict[str, Any]],
    *,
    last_updated: str,
) -> str:
    summary = _summary(results)
    pass_rate = 100.0 * summary["passed"] / summary["total"] if summary["total"] else 0.0
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
        "!!! info \"Evidence boundary\"",
        "    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. "
        "It validates software contracts and diagnostics, not real-flightline scientific accuracy.",
        "",
        "## Input variations and results",
        "",
        "On narrow screens, scroll the table horizontally to see every diagnostic and check.",
        "",
        "| Variation | Input variation | Result | Diagnostics | Explicit checks |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        status = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}[result["status"]]
        checks = "; ".join(
            f"{name}={'✓' if value else '✗'}" for name, value in result.get("checks", {}).items()
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
            "## What this tells us about QA",
            "",
            QA_USE[slug],
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
        "## Current evidence",
        "",
        "| Module | Variations | Passed | Failed | Skipped | Results |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for slug, label in MODULES:
        summary = _summary(grouped.get(slug, []))
        lines.append(
            f"| {label} | {summary['total']} | {summary['passed']} | {summary['failed']} "
            f"| {summary['skipped']} | [Open module evidence]({slug}.md) |"
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


def generated_files() -> dict[Path, str]:
    campaigns = _campaigns()
    grouped = _group_results(campaigns)
    last_updated = max(
        str(campaign.get("generated_utc", "unknown"))[:10] for campaign in campaigns
    )
    files = {
        DOCS_DIR / "index.md": _index_page(
            campaigns, grouped, last_updated=last_updated
        )
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
    parser.add_argument("--check", action="store_true", help="Fail if generated pages are stale.")
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
