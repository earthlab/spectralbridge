from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_ai_transparency.py"
SPEC = importlib.util.spec_from_file_location("generate_ai_transparency", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_parse_prompt_log_ignores_headings_and_fences_inside_prompt(tmp_path: Path) -> None:
    prompt_log = tmp_path / "PROMPT_LOG.md"
    prompt_log.write_text(
        """# Log
Default AI system: Example AI
Default model: Not recorded

## 2026-01-02 - first task
Branch: main

```text
Please add this:
```python
print("hello")
```
## A heading inside the prompt
```

## 2026-01-03 - second task
Branch: work
AI system: Other AI
Model: Model X

```text
Run the tests.
```
""",
        encoding="utf-8",
    )

    entries, defaults = MODULE.parse_prompt_log(prompt_log)

    assert defaults == {"ai system": "Example AI", "model": "Not recorded"}
    assert len(entries) == 2
    assert "heading inside the prompt" in entries[0].prompt
    assert entries[0].ai_system == "Example AI"
    assert entries[0].model == "Not recorded"
    assert entries[1].ai_system == "Other AI"
    assert entries[1].model == "Model X"


def test_summary_reports_identity_coverage_and_deterministic_categories(tmp_path: Path) -> None:
    prompt_log = tmp_path / "PROMPT_LOG.md"
    prompt_log.write_text(
        """# Log
Default AI system: OpenAI Codex
Default model: Not recorded

## 2026-01-02 - tests
Branch: main

```text
Run pytest and audit test coverage.
```

## 2026-02-03 - docs
Branch: main
Model: GPT-5

```text
Update the publication documentation and citation.
```
""",
        encoding="utf-8",
    )

    entries, _ = MODULE.parse_prompt_log(prompt_log)
    summary = MODULE.summarize(entries, "abc123")

    assert summary["summary"]["prompt_count"] == 2
    assert summary["summary"]["entries_with_recorded_model"] == 1
    assert summary["summary"]["model_metadata_coverage_pct"] == 50.0
    assert summary["primary_topics"] == {
        "Testing and CI": 1,
        "Publication, packaging, release, and governance": 1,
    }
    assert summary["prompts_by_month"] == {"2026-01": 1, "2026-02": 1}


def test_generated_repository_artifacts_are_current() -> None:
    outputs = MODULE._resolve_outputs(ROOT, ROOT / "PROMPT_LOG.md")
    for path, expected in outputs.items():
        assert path.exists(), f"Missing generated artifact: {path.relative_to(ROOT)}"
        assert path.read_text(encoding="utf-8") == expected

    payload = json.loads((ROOT / "docs" / "ai-transparency.json").read_text())
    assert payload["source"]["path"] == "PROMPT_LOG.md"
    assert payload["summary"]["prompt_count"] > 0
