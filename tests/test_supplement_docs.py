"""Contracts preventing silent omissions from the published supplement."""

import importlib.util
import io
import json
from pathlib import Path
import re
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_supplement_docs", ROOT / "scripts/generate_supplement_docs.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_complete_supplement_and_download_bundle():
    generated = MODULE.outputs()
    for name, data in generated.items():
        assert (ROOT / name).read_bytes() == data, name
    manifest = json.loads(generated["docs/validation/supplement-coverage.json"])
    page = generated["docs/validation/supplement.md"].decode()
    assert manifest["reference_provenance_notes"] == 23
    assert page.count('class="si-reference-note"') == 23
    assert "ty.tuff@colorado.edu" in page
    for heading in manifest["section_headings"]:
        # Pandoc wraps heading text at line boundaries.
        assert heading in re.sub(r"\s+", " ", page)
    with zipfile.ZipFile(io.BytesIO(generated[
        "docs/validation/supplement-assets/supplement-source.zip"
    ])) as archive:
        assert archive.read("supplement.md") == (ROOT / "paper/supplement.md").read_bytes()
        assert archive.read("supplement.bib") == (ROOT / "paper/supplement.bib").read_bytes()
        assert len([x for x in archive.namelist() if x.startswith("figures/")]) == 23
    assert "0.6938–0.8317" in page
    assert "0.5529" in page


def test_missing_table_is_rejected(tmp_path):
    draft = tmp_path / "paper"
    (draft / "generated").mkdir(parents=True)
    original = (ROOT / "paper/generated/supplement.html").read_text()
    (draft / "generated/supplement.html").write_text(original.replace("<table>", "<missing-table>", 1))
    with pytest.raises(AssertionError, match="23 editable SI tables"):
        MODULE.outputs(tmp_path)


def test_missing_reference_is_rejected(tmp_path):
    draft = tmp_path / "paper"
    (draft / "generated").mkdir(parents=True)
    original = (ROOT / "paper/generated/supplement.html").read_text()
    (draft / "generated/supplement.html").write_text(original.replace('id="ref-', 'id="missing-ref-', 1))
    with pytest.raises(AssertionError, match="all SI references"):
        MODULE.outputs(tmp_path)


def test_editing_si_requires_fresh_html_render(tmp_path):
    draft = tmp_path / "paper"
    (draft / "generated").mkdir(parents=True)
    for name in ("generated/supplement.html", "supplement.md", "supplement.bib"):
        (draft / name).write_bytes((ROOT / "paper" / name).read_bytes())
    source = draft / "supplement.md"
    source.write_text(source.read_text() + "\nA new author edit.\n")
    with pytest.raises(AssertionError, match="SI HTML is stale"):
        MODULE.outputs(tmp_path)
