from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_joss_submission", ROOT / "scripts/check_joss_submission.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_real_paper_contracts() -> None:
    report = MODULE.check_paper(ROOT / "paper/paper.md")
    assert not report["errors"]
    assert 750 <= report["word_count_including_captions"] <= 1750
    assert report["images"] == 3


def test_nested_bibliography_and_literal_author() -> None:
    entries = MODULE.bibliography_entries("@misc{key,\n author = {{Earth Lab}},\n title = {{NEON: {BRDF}}},\n year = {2026},\n}\n")
    assert entries["key"]["author"] == "{Earth Lab}"
    assert entries["key"]["title"] == "{NEON: {BRDF}}"


@pytest.mark.parametrize("text", [
    "@misc{key, title = {{broken},}",
    "@misc{key, title = {one},}\n@misc{key, title = {two},}",
])
def test_broken_bibliographies_are_rejected(text: str) -> None:
    with pytest.raises(ValueError):
        MODULE.bibliography_entries(text)


def test_bad_citation_and_internal_reference_are_reported(tmp_path: Path) -> None:
    source = ROOT / "paper/paper.md"
    target = tmp_path / "paper.md"
    target.write_text(source.read_text() + "\n[@missing_citation] \\autoref{missing-figure}\n")
    (tmp_path / "paper.bib").write_text((source.parent / "paper.bib").read_text())
    report = MODULE.check_paper(target)
    assert "Unresolved citation: missing_citation" in report["errors"]
    assert "Unresolved internal reference: missing-figure" in report["errors"]


def test_caption_words_count_and_citation_keys_do_not() -> None:
    body = "Four ordinary prose words.\n\n![Three caption words](figures/a.png){#fig:a}\n[@key; @other]\n"
    assert MODULE.word_count(body, captions=True) == 7
    assert MODULE.word_count(body, captions=False) == 4


def test_orcid_checksum() -> None:
    assert MODULE.valid_orcid("0000-0001-5249-5197")
    assert not MODULE.valid_orcid("0000-0001-5249-5198")


def test_author_requests_are_not_mistaken_for_readiness() -> None:
    source = ROOT / "paper/paper.md"
    report = MODULE.check_paper(source)
    expected = "AUTHOR INPUT REQUIRED:" in source.read_text()
    assert bool(report["author_actions"]) == expected
