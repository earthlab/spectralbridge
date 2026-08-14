"""Contracts for user-facing example scripts and notebook vignettes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "docs" / "vignettes" / "notebooks"


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
    assert [path.name for path in notebooks] == [
        "00_full_neon_pipeline.ipynb",
        "01_acquire_neon.ipynb",
        "02_correct_neon.ipynb",
        "03_harmonize_to_landsat.ipynb",
        "04_analysis_tables.ipynb",
        "05_qa_and_validation.ipynb",
        "06_drone_pipeline.ipynb",
        "07_polygon_extraction.ipynb",
        "08_custom_correction_hook.ipynb",
    ]

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
