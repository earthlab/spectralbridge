"""Canonical recorded-category information atlas and synthetic abundance study.

Repository experiment on the supplied source; see the versioned METHODS first.
Older dual-label workflows are historical reproduction only.
"""

import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=[
            "atlas",
            "abundance",
            "summary",
            "figures",
            "report",
            "validate",
            "all",
        ],
        default="all",
    )
    parser.add_argument(
        "--report-python",
        default=sys.executable,
        help="Python with ReportLab and pypdf; defaults to this interpreter",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = root / "provenance/researcher-pft-information/2026-10-15/v1"
    if args.stage in ["all", "report"]:
        probe = subprocess.run(
            [args.report_python, "-c", "import reportlab, pypdf"], capture_output=True
        )
        if probe.returncode:
            parser.error(
                "Report dependencies unavailable; set --report-python to a ReportLab/pypdf runtime."
            )
    stages = {
        "atlas": ["run_atlas.py", "training_inference.py"],
        "abundance": ["run_abundance.py", "finalize_exports.py"],
        "summary": [
            "summarize.py",
            "add_diagnostics.py",
            "write_results.py",
            "prepare_compact_figure_sources.py",
        ],
        "figures": ["build_figures.py", "build_confusions.py"],
        "report": ["create_report_source.py", "build_report.py"],
        "validate": ["validate_analysis.py", "validate_model_replay.py"],
    }
    for stage, scripts in stages.items():
        if args.stage in [stage, "all"]:
            for script in scripts:
                interpreter = (
                    args.report_python
                    if script == "build_report.py"
                    else sys.executable
                )
                subprocess.run([interpreter, str(base / script)], cwd=root, check=True)


if __name__ == "__main__":
    main()
