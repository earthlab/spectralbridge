"""Contracts connecting generic methods, runnable lessons and current science pages."""

from pathlib import Path
import json
import re
import numpy as np
import pytest

pytest.importorskip("sklearn")
from spectralbridge import library_analysis  # noqa: E402
from scripts.validate_library_analysis_integration import verify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def test_current_scientific_numbers_assets_and_prior_packets():
    result = verify()
    assert result["status"] == "passed"
    assert result["prior_owned_files_verified"] >= 1053
    assert result["figure_assets_verified"] == 11


def test_all_public_contracts_document_scientific_scope():
    for name in library_analysis.__all__:
        doc = getattr(library_analysis, name).__doc__
        assert all(
            word in doc
            for word in [
                "Inputs:",
                "Sampling unit:",
                "Outputs:",
                "Assumptions:",
                "Does not",
            ]
        ), name
    assert len(library_analysis.__all__) == 12


def test_science_navigation_and_four_part_figure_captions():
    nav = (ROOT / "mkdocs.yml").read_text()
    for name in [
        "scientific-synthesis",
        "separability",
        "identifiability",
        "mathematical-guarantees",
    ]:
        assert f"spectral-library/{name}.md" in nav
    for name in [
        "scientific-synthesis",
        "separability",
        "identifiability",
        "mathematical-guarantees",
        "mesma-readiness",
        "sensor-transfer",
    ]:
        text = (ROOT / f"docs/spectral-library/{name}.md").read_text()
        new_figures = len(
            re.findall(r"!\[[^\]]+\]\([^)]*(?:current-|formal-)[^)]*\)", text)
        )
        for phrase in [
            "What you see:",
            "What to notice:",
            "What it means:",
            "What it does not mean:",
        ]:
            assert text.count(phrase) >= new_figures, (name, phrase)


def test_offline_notebook_cells_execute_in_order(capsys):
    notebook = json.loads(
        (ROOT / "examples/spectral_library_methods.ipynb").read_text()
    )
    scope = {}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            code = cell["source"]
            code = "".join(code) if isinstance(code, list) else code
            exec(compile(code, "spectral_library_methods.ipynb", "exec"), scope)
    assert "field cover" in capsys.readouterr().out
    np.testing.assert_allclose(scope["target"]["truth"].sum(1), 1)
    assert scope["recognition"]["overall"]["balanced_accuracy"] > 0.9
