"""Contracts for user-facing example scripts and notebook vignettes."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "docs" / "vignettes" / "notebooks"
GITHUB_NOTEBOOK_BASE = (
    "https://github.com/earthlab/spectralbridge/blob/main/"
    "docs/vignettes/notebooks/"
)
EXPECTED_NOTEBOOKS = [
    "00_full_neon_pipeline.ipynb",
    "01_acquire_neon.ipynb",
    "02_correct_neon.ipynb",
    "03_harmonize_to_landsat.ipynb",
    "04_analysis_tables.ipynb",
    "05_qa_and_validation.ipynb",
    "06_drone_pipeline.ipynb",
    "07_polygon_extraction.ipynb",
    "08_custom_correction_hook.ipynb",
    "09_bulk_analysis.ipynb",
]


def test_example_scripts_support_no_work_check_mode() -> None:
    for script in ("run_neon_pipeline.py", "run_drone_pipeline.py"):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "examples" / script), "--check"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "Configuration is valid" in result.stdout


def test_vignette_notebooks_are_clean_and_code_compiles() -> None:
    notebooks = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
    assert [path.name for path in notebooks] == EXPECTED_NOTEBOOKS

    for path in notebooks:
        notebook = json.loads(path.read_text(encoding="utf-8"))
        assert notebook["nbformat"] == 4
        assert notebook["metadata"]["kernelspec"]["name"] == "python3"
        code_cells = [
            cell for cell in notebook["cells"] if cell["cell_type"] == "code"
        ]
        assert code_cells
        source = "\n\n".join("".join(cell["source"]) for cell in code_cells)
        compiled = compile(source, str(path), "exec")
        assert "RUN = False" in source
        for cell in code_cells:
            assert cell["id"]
            assert cell["execution_count"] is None
            assert cell["outputs"] == []
        exec(compiled, {"__name__": "__notebook_contract_test__"})


def test_documentation_links_to_tracked_notebooks_on_github() -> None:
    """Keep GitHub Pages from treating notebooks as opaque static assets."""
    catalog = (
        REPO_ROOT / "docs" / "vignettes" / "notebook-vignettes.md"
    ).read_text(encoding="utf-8")
    for notebook_name in EXPECTED_NOTEBOOKS:
        assert f"{GITHUB_NOTEBOOK_BASE}{notebook_name}" in catalog

    notebook_link_patterns = (
        re.compile(r"\]\(([^)\s]+\.ipynb)\)"),
        re.compile(r"^\[[^\]]+\]:\s+(\S+\.ipynb)\s*$", re.MULTILINE),
    )
    unexpected_links: list[str] = []
    for path in (REPO_ROOT / "docs").rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for pattern in notebook_link_patterns:
            for target in pattern.findall(text):
                if not target.startswith(GITHUB_NOTEBOOK_BASE):
                    unexpected_links.append(f"{path.relative_to(REPO_ROOT)}: {target}")

    assert unexpected_links == []


def test_vignettes_mirror_active_research_notebook_workflows() -> None:
    def notebook_source(path: Path) -> str:
        notebook = json.loads(path.read_text(encoding="utf-8"))
        return "\n".join(
            "".join(cell["source"])
            for cell in notebook["cells"]
        )

    raster_reference = notebook_source(REPO_ROOT / "Raster_processing.ipynb")
    raster_vignette = notebook_source(
        NOTEBOOK_DIR / "00_full_neon_pipeline.ipynb"
    )
    for snippet in (
        "from spectralbridge import go_forth_and_multiply",
        "go_forth_and_multiply(",
    ):
        assert snippet in raster_reference
        assert snippet in raster_vignette

    drone_reference = notebook_source(REPO_ROOT / "Drone_processing.ipynb")
    drone_vignette = notebook_source(NOTEBOOK_DIR / "06_drone_pipeline.ipynb")
    for snippet in (
        "from spectralbridge import run_drone_pipeline",
        "results = run_drone_pipeline(",
        "pd.read_parquet",
    ):
        assert snippet in drone_reference
        assert snippet in drone_vignette
    assert "pprint(results[" in drone_reference
    assert "pprint(results[" in drone_vignette

    table_vignette = notebook_source(NOTEBOOK_DIR / "04_analysis_tables.ipynb")
    assert "duckdb.connect()" in raster_reference
    assert "duckdb.connect()" in table_vignette

    qa_vignette = notebook_source(NOTEBOOK_DIR / "05_qa_and_validation.ipynb")
    for snippet in ("def plot_envi_band", "def plot_envi_rgb"):
        assert snippet in raster_reference
        assert snippet in qa_vignette

    for notebook_name in EXPECTED_NOTEBOOKS:
        notebook = json.loads(
            (NOTEBOOK_DIR / notebook_name).read_text(encoding="utf-8")
        )
        markdown_cells = [
            "".join(cell["source"])
            for cell in notebook["cells"]
            if cell["cell_type"] == "markdown"
        ]
        assert len(markdown_cells) >= 3
        assert any("## 1." in source for source in markdown_cells)

    bulk_vignette = notebook_source(NOTEBOOK_DIR / "09_bulk_analysis.ipynb")
    assert "from spectralbridge import run_bulk_pipeline" in bulk_vignette
    assert "result = run_bulk_pipeline(" in bulk_vignette
    assert "bulk_observations" in bulk_vignette
