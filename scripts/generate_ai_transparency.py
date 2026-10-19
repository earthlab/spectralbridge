#!/usr/bin/env python3
"""Generate deterministic AI-transparency summaries from PROMPT_LOG.md."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import statistics
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path


ENTRY_RE = re.compile(r"^## (?P<date>\d{4}-\d{2}-\d{2}) - (?P<label>.+?)\s*$")
WORD_RE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
DEFAULT_RE = re.compile(
    r"^Default (?P<field>AI system|model):\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)
META_RE = re.compile(
    r"^(?P<field>Branch|AI system|Model):\s*(?P<value>.*?)\s*$",
    re.IGNORECASE,
)

TOPICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Testing and CI",
        ("test", "pytest", "coverage", "ci", "ruff", "lint", "playwright", "regression"),
    ),
    (
        "Publication, packaging, release, and governance",
        (
            "publication",
            "publish",
            "release",
            "citation",
            "zenodo",
            "doi",
            "license",
            "governance",
            "contributor",
            "prompt log",
            "package",
            "dependency",
            "feature request",
            "backlog",
            "queue",
        ),
    ),
    (
        "Documentation and website",
        ("documentation", "docs", "website", "readme", "mkdocs", "homepage", "tutorial", "html", "logo", "favicon", "footer"),
    ),
    (
        "QA and visualization",
        ("qa", "plot", "figure", "visual", "dashboard", "pdf", "png", "panel", "aop"),
    ),
    (
        "Drone and UAS workflow",
        ("drone", "uas", "micasense", "tiff", "manifest"),
    ),
    (
        "Scientific pipeline and corrections",
        (
            "pipeline",
            "brdf",
            "topographic",
            "topo",
            "reflectance",
            "neon",
            "envi",
            "parquet",
            "hdf5",
            "convolution",
            "coefficient",
            "hytools",
            "kernel",
            "chunk",
        ),
    ),
    (
        "Data and metadata handling",
        ("metadata", "schema", "filename", "path", "polygon", "csv", "json", "data"),
    ),
)

INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Implementation or modification", ("add", "fix", "update", "change", "implement", "create", "make", "refactor", "remove")),
    ("Audit or investigation", ("audit", "review", "analyze", "investigate", "find", "explain", "why", "check")),
    ("Execution or verification", ("run", "test", "verify", "validate", "render", "build")),
)


@dataclass(frozen=True)
class PromptEntry:
    date: date
    label: str
    branch: str
    ai_system: str
    model: str
    prompt: str

    @property
    def word_count(self) -> int:
        return len(WORD_RE.findall(self.prompt))


def _field(metadata: dict[str, str], key: str, default: str) -> str:
    return metadata.get(key.casefold(), default).strip() or default


def parse_prompt_log(path: Path) -> tuple[list[PromptEntry], dict[str, str]]:
    """Parse entries while tolerating Markdown headings and fences inside prompts."""

    lines = path.read_text(encoding="utf-8").splitlines()
    starts: list[int] = []
    for index, line in enumerate(lines[:-1]):
        if ENTRY_RE.match(line) and lines[index + 1].startswith("Branch:"):
            starts.append(index)

    defaults = {"ai system": "OpenAI Codex", "model": "Not recorded"}
    boundary = starts[0] if starts else len(lines)
    for line in lines[:boundary]:
        match = DEFAULT_RE.match(line)
        if match:
            defaults[match.group("field").casefold()] = match.group("value").strip()

    entries: list[PromptEntry] = []
    for position, start in enumerate(starts):
        stop = starts[position + 1] if position + 1 < len(starts) else len(lines)
        header = ENTRY_RE.match(lines[start])
        if header is None:  # pragma: no cover - protected by starts construction
            continue
        block = lines[start + 1 : stop]
        open_index = next((i for i, line in enumerate(block) if line.strip() == "```text"), None)
        if open_index is None:
            continue

        metadata: dict[str, str] = {}
        for line in block[:open_index]:
            match = META_RE.match(line)
            if match:
                metadata[match.group("field").casefold()] = match.group("value").strip()

        closing_candidates = [
            i for i, line in enumerate(block[open_index + 1 :], start=open_index + 1)
            if line.strip() == "```"
        ]
        close_index = closing_candidates[-1] if closing_candidates else len(block)
        prompt = "\n".join(block[open_index + 1 : close_index]).strip()
        entries.append(
            PromptEntry(
                date=date.fromisoformat(header.group("date")),
                label=header.group("label").strip(),
                branch=_field(metadata, "branch", "Not recorded"),
                ai_system=_field(metadata, "ai system", defaults["ai system"]),
                model=_field(metadata, "model", defaults["model"]),
                prompt=prompt,
            )
        )

    if not entries:
        raise ValueError(f"No prompt entries found in {path}")
    return entries, defaults


def _keyword_score(text: str, keywords: Iterable[str]) -> int:
    lowered = text.casefold()
    return sum(1 for keyword in keywords if keyword in lowered)


def classify(text: str, rules: Sequence[tuple[str, Sequence[str]]], fallback: str) -> str:
    scored = [(name, _keyword_score(text, keywords)) for name, keywords in rules]
    best_name, best_score = max(scored, key=lambda item: item[1])
    return best_name if best_score else fallback


# Multi-label literal phrase matches describe mentions, including negations and pasted text.
MENTION_RULES = {
    "workflow_mentions": {
        "Implementation / refactoring": ("implement", "refactor", "modify", "fix"),
        "Audit / investigation": ("audit", "investigate", "inspect", "review"),
        "Documentation / reporting": ("documentation", "report", "manuscript", "website"),
        "Reproducibility / provenance": ("reproducib", "provenance", "checkpoint", "restart"),
        "Scientific analysis / figures": ("regression", "spectra", "statistical", "figure", "plot"),
    },
    "tool_mentions": {
        "Python": ("python",), "pytest": ("pytest",), "Ruff": ("ruff",),
        "Git / GitHub": ("github", "git ", "git\n"),
        "MkDocs": ("mkdocs",), "Notebooks / Jupyter": ("notebook", "jupyter", ".ipynb"),
        "Docker / containers": ("docker", "container"),
        "Browser / Playwright": ("browser", "playwright"),
        "Lean / Lake": ("lean 4", "lean4", "lake build",),
    },
    "validation_mentions": {
        "Tests / regression checks": ("pytest", "regression test", "unit test", "smoke", "test suite"),
        "Lint / static checks": ("ruff", "lint", "type check"),
        "Documentation / link builds": ("mkdocs", "check_docs_links", "link check", "strict build"),
        "Visual inspection": ("screenshot", "visual inspection", "render", "visually"),
        "Artifact / installation checks": ("wheel", "sdist", "installed artifact", "installation"),
        "Scientific / numerical checks": ("statistical", "confidence interval", "permutation", "numerical", "cross-validation"),
        "Formal verification": ("lean 4", "lean4", "lake build", "formal verification"),
        "Human review / approval": ("human review", "maintainer", "approval", "author input"),
    },
}


def mention_counts(texts: Sequence[str], rules: dict[str, Sequence[str]]) -> dict[str, int]:
    """Count each prompt once per category; mentions do not establish execution."""
    lowered = [text.casefold() for text in texts]
    return {name: sum(any(term in text for term in terms) for text in lowered)
            for name, terms in rules.items()}


def summarize(entries: Sequence[PromptEntry], source_sha256: str) -> dict[str, object]:
    word_counts = [entry.word_count for entry in entries]
    labeled_text = [(entry, f"{entry.label}\n{entry.prompt}") for entry in entries]
    topics = Counter(classify(text, TOPICS, "Other") for _, text in labeled_text)
    intents = Counter(classify(text, INTENTS, "Other or mixed") for _, text in labeled_text)
    months = Counter(entry.date.strftime("%Y-%m") for entry in entries)
    systems = Counter(entry.ai_system for entry in entries)
    models = Counter(entry.model for entry in entries)
    branches = Counter(entry.branch for entry in entries)
    known_models = sum(count for model, count in models.items() if model.casefold() != "not recorded")
    return {
        "schema_version": 2,
        "historical_context": {
            "statement": "Maintainers report using LLM assistance since GPT-3.5 and continuing thereafter; a prompt log was introduced when agentic assistants were adopted.",
            "basis": "Maintainer statement, 2026-10-19; early usage is not reconstructed from the log.",
        },
        "mention_analysis": {
            name: mention_counts([text for _, text in labeled_text], rules)
            for name, rules in MENTION_RULES.items()
        },
        "source": {
            "path": "PROMPT_LOG.md",
            "sha256": source_sha256,
            "data_through": max(entry.date for entry in entries).isoformat(),
        },
        "summary": {
            "prompt_count": len(entries),
            "first_prompt_date": min(entry.date for entry in entries).isoformat(),
            "last_prompt_date": max(entry.date for entry in entries).isoformat(),
            "total_prompt_words": sum(word_counts),
            "mean_prompt_words": round(statistics.fmean(word_counts), 1),
            "median_prompt_words": round(float(statistics.median(word_counts)), 1),
            "minimum_prompt_words": min(word_counts),
            "maximum_prompt_words": max(word_counts),
            "entries_with_recorded_model": known_models,
            "model_metadata_coverage_pct": round(known_models / len(entries) * 100.0, 1),
        },
        "prompts_by_month": dict(sorted(months.items())),
        "primary_topics": dict(topics.most_common()),
        "primary_intents": dict(intents.most_common()),
        "ai_systems": dict(systems.most_common()),
        "models": dict(models.most_common()),
        "branches": dict(branches.most_common()),
        "method": {
            "topic_classification": "Deterministic keyword scoring over each prompt and its logged task label; one primary topic per entry; ties follow documented rule order.",
            "intent_classification": "Deterministic keyword scoring over each prompt and its logged task label; one primary intent per entry; ties follow documented rule order.",
            "mention_classification": "Case-insensitive literal phrase matching over prompt and task label; each prompt counted once per category; categories overlap. Negated instructions and pasted text also count. No execution or success inferred.",
            "mention_rules": MENTION_RULES,
            "word_count": "Unicode word-like tokens matched by the generator's WORD_RE expression.",
            "ai_identity": "Entry metadata when present; otherwise the prompt log's declared defaults.",
        },
    }


def _svg_bar_chart(title: str, values: dict[str, int], subtitle: str) -> str:
    items = list(values.items())
    width = 1000
    left = 330
    right = 70
    top = 105
    row_height = 42
    height = top + max(len(items), 1) * row_height + 70
    plot_width = width - left - right
    maximum = max(values.values(), default=1)
    colors = ("#2563eb", "#0891b2", "#059669", "#65a30d", "#ca8a04", "#ea580c", "#dc2626", "#7c3aed")
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(subtitle)}</desc>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="36" y="42" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#172554">{html.escape(title)}</text>',
        f'<text x="36" y="70" font-family="Arial, sans-serif" font-size="14" fill="#475569">{html.escape(subtitle)}</text>',
    ]
    for index, (label, value) in enumerate(items):
        y = top + index * row_height
        bar_width = 0 if maximum == 0 else value / maximum * plot_width
        parts.extend(
            [
                f'<text x="{left - 14}" y="{y + 23}" text-anchor="end" font-family="Arial, sans-serif" font-size="14" fill="#334155">{html.escape(label)}</text>',
                f'<rect x="{left}" y="{y + 5}" width="{plot_width}" height="25" rx="4" fill="#e2e8f0"/>',
                f'<rect x="{left}" y="{y + 5}" width="{bar_width:.1f}" height="25" rx="4" fill="{colors[index % len(colors)]}"/>',
                f'<text x="{min(left + bar_width + 9, width - 34):.1f}" y="{y + 23}" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#0f172a">{value}</text>',
            ]
        )
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def _prompt_length_buckets(entries: Sequence[PromptEntry]) -> dict[str, int]:
    buckets = {"1–25 words": 0, "26–100 words": 0, "101–250 words": 0, "251–500 words": 0, ">500 words": 0}
    for entry in entries:
        count = entry.word_count
        if count <= 25:
            buckets["1–25 words"] += 1
        elif count <= 100:
            buckets["26–100 words"] += 1
        elif count <= 250:
            buckets["101–250 words"] += 1
        elif count <= 500:
            buckets["251–500 words"] += 1
        else:
            buckets[">500 words"] += 1
    return buckets


def render_markdown(summary: dict[str, object]) -> str:
    stats = summary["summary"]
    topics = summary["primary_topics"]
    intents = summary["primary_intents"]
    systems = summary["ai_systems"]
    models = summary["models"]
    assert isinstance(stats, dict) and isinstance(topics, dict) and isinstance(intents, dict)
    assert isinstance(systems, dict) and isinstance(models, dict)
    leading_topic = next(iter(topics), "Not available")
    leading_intent = next(iter(intents), "Not available")
    system_rows = "\n".join(f"| {name} | {count} |" for name, count in systems.items())
    model_rows = "\n".join(f"| {name} | {count} |" for name, count in models.items())
    return f"""# AI Transparency Statement

> This page is generated from `PROMPT_LOG.md` by `scripts/generate_ai_transparency.py`. It reports the development requests recorded in the repository; it does not measure scientific validity or assign code authorship.

## History and responsibility

Maintainers report that SpectralBridge development began using LLM assistance with **GPT-3.5** and has continued using LLMs since then. When agentic assistants were adopted, the project introduced the repository prompt log. This historical account was supplied by maintainers on 2026-10-19; the log does not establish an early start date, every model used, or complete coverage of subsequent work.

AI assistance is part of the development process. Scientific interpretation and release decisions remain human responsibilities. This statement does not certify that every suggestion received human review; recorded requests for review are not evidence of approval.

## Summary

From {stats['first_prompt_date']} through {stats['last_prompt_date']}, the log contains **{stats['prompt_count']} prompts** totaling **{stats['total_prompt_words']:,} words**. The median prompt contains **{stats['median_prompt_words']:g} words** and the mean contains **{stats['mean_prompt_words']:g} words**. Under the published keyword rules, the most common primary topic is **{leading_topic}**, and the most common request intent is **{leading_intent}**.

![Logged prompts by month](images/ai-transparency/prompts-by-month.svg)

![Primary prompt topics](images/ai-transparency/prompts-by-topic.svg)

![Primary prompt intents](images/ai-transparency/prompts-by-intent.svg)

![Prompt length distribution](images/ai-transparency/prompt-lengths.svg)

## What assistance and methods were discussed

The following figures count **prompts mentioning** each activity, tool or validation method. Each prompt counts at most once within a category and may count in several categories. Bar lengths measure recorded attention, not effort, executed commands or successful checks. All figures use the {stats['prompt_count']} logged prompts as their denominator.

![Workflows mentioned in logged prompts](images/ai-transparency/workflow-mentions.svg)

**Read this as:** the kinds of work users asked assistants to undertake or discussed in their instructions. Implementation and audits can occur in the same prompt.

![Tools mentioned in logged prompts](images/ai-transparency/tool-mentions.svg)

**Read this as:** named tools in requests, specifications or pasted material. A mention of pytest, for example, does not establish that pytest ran. Tools absent from prompts can still have been used.

![Validation methods mentioned in logged prompts](images/ai-transparency/validation-mentions.svg)

**Read this as:** the review and checking methods discussed in the log. These counts do not estimate test pass rates, numerical correctness, successful formal proofs or human sign-off.

To establish what actually happened, inspect the corresponding Git changes, test/CI outputs and dated evidence packets in the [provenance directory](https://github.com/earthlab/spectralbridge/tree/main/provenance). Those records cover particular revisions and experiments; this generator does not treat them as evidence for every prompt. Complete tool-call traces and per-prompt execution outcomes are not recorded in this log.

## Which AI was used

The prompt log declares the AI system used for logged work. Model names are reported only when an entry records them; missing model metadata is not inferred.

| AI system | Logged prompts |
| --- | ---: |
{system_rows}

| Model metadata | Logged prompts |
| --- | ---: |
{model_rows}

Model metadata is recorded for **{stats['entries_with_recorded_model']} of {stats['prompt_count']} entries ({stats['model_metadata_coverage_pct']:g}%)**.

## How AI was used

The logged requests cover implementation and modification, audits and investigations, verification, documentation, QA, pipeline behavior, and publication maintenance. Each entry receives one primary topic and one primary intent through deterministic keyword scoring over the prompt and its logged task label. These labels summarize requests, not completed work; consult Git history, tests, and review records for evidence of outcomes.

## Scope and limitations

- The source log begins after repository development was already underway, so it is not a complete history of AI use.
- It records user prompts, not assistant responses, accepted/rejected suggestions, token usage, elapsed time, or line-level authorship.
- Long prompts may contain pasted logs or specifications; word counts measure prompt text, not effort.
- Mention matching includes negated instructions (for example, “do not run pytest”) and pasted examples. Counts are descriptive text indicators, not semantic judgments. The machine-readable output publishes every matching phrase and includes zero-count categories.
- Topic and intent labels are rule-based approximations based on prompt text and the logged task label. The rules are version-controlled in the generator.
- Legacy entries use the log-level AI-system default. Their model is `Not recorded` unless an entry explicitly provides model metadata.
- Prompts may contain sensitive material. The generated report includes aggregates only and does not reproduce prompt text.

## Reproduce this statement

```bash
python scripts/generate_ai_transparency.py
python scripts/generate_ai_transparency.py --check
```

Machine-readable statistics are available in [`ai-transparency.json`](ai-transparency.json). The source-log SHA-256 recorded there allows a reviewer to verify which prompt-log revision produced this page.
"""


def build_outputs(prompt_log: Path, figures_dir: Path) -> dict[Path, str]:
    entries, _ = parse_prompt_log(prompt_log)
    source_bytes = prompt_log.read_bytes()
    summary = summarize(entries, hashlib.sha256(source_bytes).hexdigest())
    figure_specs = {
        figures_dir / "prompts-by-month.svg": (
            "Logged prompts by month",
            summary["prompts_by_month"],
            "Counts reflect entries in PROMPT_LOG.md; missing historical work is not reconstructed.",
        ),
        figures_dir / "prompts-by-topic.svg": (
            "Primary prompt topics",
            summary["primary_topics"],
            "One deterministic keyword-based primary topic is assigned to each logged prompt.",
        ),
        figures_dir / "prompts-by-intent.svg": (
            "Primary prompt intents",
            summary["primary_intents"],
            "One deterministic keyword-based primary intent is assigned to each logged prompt.",
        ),
        figures_dir / "prompt-lengths.svg": (
            "Prompt length distribution",
            _prompt_length_buckets(entries),
            "Word-like tokens per logged prompt; pasted specifications and logs can increase counts.",
        ),
    }
    for key, title in (
        ("workflow_mentions", "Workflows mentioned in logged prompts"),
        ("tool_mentions", "Tools mentioned in logged prompts"),
        ("validation_mentions", "Validation methods mentioned in logged prompts"),
    ):
        figure_specs[figures_dir / (key.replace("_", "-") + ".svg")] = (
            title, summary["mention_analysis"][key],
            f"Prompts mentioning each category (N={len(entries)}); categories overlap; execution is not established.",
        )
    outputs = {
        Path("docs/ai-transparency.md"): render_markdown(summary),
        Path("docs/ai-transparency.json"): json.dumps(summary, indent=2, sort_keys=True) + "\n",
    }
    for path, (title, values, subtitle) in figure_specs.items():
        assert isinstance(values, dict)
        outputs[path] = _svg_bar_chart(title, values, subtitle)
    return outputs


def _resolve_outputs(root: Path, prompt_log: Path) -> dict[Path, str]:
    relative_outputs = build_outputs(prompt_log, Path("docs/images/ai-transparency"))
    return {root / path: content for path, content in relative_outputs.items()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated files are missing or stale.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    prompt_log = root / "PROMPT_LOG.md"
    outputs = _resolve_outputs(root, prompt_log)
    stale: list[Path] = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        for path in stale:
            print(f"stale: {path.relative_to(root)}", file=sys.stderr)
        print("Run: python scripts/generate_ai_transparency.py", file=sys.stderr)
        return 1
    action = "verified" if args.check else "generated"
    print(f"AI transparency artifacts {action}: {len(outputs)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
