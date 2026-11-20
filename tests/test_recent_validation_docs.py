"""Keep current public scientific claims tied to the frozen evidence snapshot."""

import hashlib
import json
from pathlib import Path
import pytest
from scripts.generate_scientific_docs import recent_validation_generated_files

ROOT = Path(__file__).resolve().parents[1]


def test_recent_assets_match_their_verified_snapshot():
    for path, content in recent_validation_generated_files().items():
        assert path.read_bytes() == content, path


def test_tampered_evidence_is_rejected_before_publishing(tmp_path):
    base = tmp_path / "provenance/website-updates/2026-11-20"
    (base / "files").mkdir(parents=True)
    raw = b"original observations\n"
    (base / "files/results.csv").write_bytes(b"changed observations\n")
    (base / "manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "source": "files/results.csv",
                        "destination": "docs/validation/recent-evidence/results.csv",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="Changed recent validation evidence"):
        recent_validation_generated_files(tmp_path)
    assert not (tmp_path / "docs").exists()


def test_documented_hls_counts_and_recalls_match_current_figure_source():
    source = json.loads(
        (ROOT / "docs/validation/recent-evidence/figure-4-provenance.json").read_text()
    )
    page = (ROOT / "docs/validation/landsat-pilot.md").read_text()
    found = {}
    for line in page.splitlines():
        cells = [v.strip() for v in line.strip("|").split("|")]
        if len(cells) == 5 and cells[0] in source["panel_b_landsat"]["primary_classes"]:
            found[cells[0]] = cells[1:]
    assert len(found) == len(source["panel_b_landsat"]["primary_classes"])
    for category, r in source["panel_b_landsat"]["primary_classes"].items():
        assert found[category] == [
            str(r["cells"]),
            str(r["patches"]),
            r["supported_testable_pairs"],
            r["held_patch_recall"],
        ]
    assert str(source["panel_b_landsat"]["cohort_cells"]) in page.replace(",", "")
    assert "provisional" in page and "seven have no mixed-region support" in page


def test_published_drone_qa_table_distinguishes_processing_branches():
    import csv

    records = list(
        csv.DictReader(
            (ROOT / "docs/validation/recent-evidence/drone_model_support.csv").open()
        )
    )
    page = (ROOT / "docs/validation/drone-findings.md").read_text()
    for site in ["gordon", "goldhill", "ruby"]:
        support = []
        for variant, branch in [
            ("baseline", "combined"),
            ("conservative", "combined"),
            ("conservative", "brdf_only"),
        ]:
            r = next(
                r
                for r in records
                if r["site"] == site
                and r["variant"] == variant
                and r["branch"] == branch
            )
            support.append(r["valid_bands"] + "/10")
        expected = "| " + site.title() + " | " + " | ".join(support) + " |"
        assert expected in page
    assert "HYPOTHETICAL_UNVERIFIED" in page and "−7.42" in page


def test_recent_generated_paths_cannot_escape_docs(tmp_path):
    base = tmp_path / "provenance/website-updates/2026-11-20"
    base.mkdir(parents=True)
    raw = b"legitimate\n"
    (base / "evidence.csv").write_bytes(raw)
    (base / "manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "source": "evidence.csv",
                        "destination": "../escape.csv",
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="inside docs"):
        recent_validation_generated_files(tmp_path)
