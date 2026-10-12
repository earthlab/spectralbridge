"""Bounded contracts for repository migrations, documentation and launchers."""

from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_built_site", ROOT / "scripts/check_built_site.py")
SITE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SITE)


def test_rendered_link_checker_finds_missing_anchor_and_asset(tmp_path):
    (tmp_path / "index.html").write_text('<a href="page/#gone">Go</a><img src="missing.png">')
    (tmp_path / "page").mkdir()
    (tmp_path / "page/index.html").write_text('<h1 id="present">Present</h1>')
    errors = SITE.check(tmp_path)
    assert len(errors) == 2
    assert any("missing anchor" in error for error in errors)
    assert any("missing target" in error for error in errors)
    (tmp_path / "page/index.html").write_text('<h1 id="gone">Present</h1>')
    (tmp_path / "missing.png").write_bytes(b"fixture")
    assert SITE.check(tmp_path) == []


def test_rendered_link_checker_never_requires_external_availability(tmp_path):
    (tmp_path / "index.html").write_text('<a href="https://example.invalid/missing#gone">External</a>')
    assert SITE.check(tmp_path) == []


def test_gocmd_launcher_forwards_args_cwd_and_explicit_client(tmp_path):
    client = tmp_path / "installed-gocmd"
    client.write_text('#!/bin/sh\npwd\nprintf "%s\\n" "$GOCMD_TEST_MARKER" "$@"\n')
    client.chmod(0o755)
    env = dict(os.environ, GOCMD_BINARY=str(client), GOCMD_TEST_MARKER="sentinel")
    result = subprocess.run([sys.executable, str(ROOT / "gocmd"), "ls", "i:/example/a b"],
                            cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [str(tmp_path), "sentinel", "ls", "i:/example/a b"]


def test_offline_first_example_runs_public_preflight():
    result = subprocess.run([sys.executable, str(ROOT / "examples/first_example.py")],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["counts"] == {"source_rows": 6, "valid_spectra": 6, "species": 2,
                                  "polygons": 2, "flightlines": 1, "sites": 1}
    assert not payload["pdfs_generated"]
    assert "invented" in payload["data_kind"]


def test_canonical_paper_sources_and_prompt_interface():
    for name in ("paper.md", "paper.bib", "supplement.md", "supplement.bib"):
        assert (ROOT / "paper" / name).is_file()
    assert (ROOT / "PROMPT_LOG.md").resolve() == ROOT / "provenance/prompts/PROMPT_LOG.md"
    assert (ROOT / "paper/archive/main-38.pdf").is_file()
    assert (ROOT / "paper/archive/supplement-10.pdf").is_file()
    assert not list((ROOT / "docs/literature").glob("*.pdf"))


def test_new_paper_build_manifest_does_not_inherit_a_review_claim(tmp_path):
    spec = importlib.util.spec_from_file_location("record_publication_build", ROOT / "scripts/record_publication_build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "generated").mkdir()
    (tmp_path / "paper.md").write_text("# Example\n")
    (tmp_path / "paper.bib").write_text("fixture bibliography")
    (tmp_path / "generated/paper.pdf").write_bytes(b"first fixture PDF")
    old = module.record(tmp_path, "pinned-fixture-renderer", review_note="Reviewed")
    (tmp_path / "generated/paper.pdf").write_bytes(b"changed fixture PDF")
    new = module.record(tmp_path, "pinned-fixture-renderer")
    assert new["pdf_sha256"] != old["pdf_sha256"]
    assert new["visual_review"] == "Pending visual review of this exact PDF"
    assert new["inputs"] == old["inputs"]
