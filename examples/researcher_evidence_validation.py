"""Reproduce the three-question researcher-category evidence report in stages."""

from pathlib import Path
import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    stages = {
        "controls": ["run_controls.py"],
        "candidate": ["run_candidate_control.py"],
        "summary": [
            "synthesize.py",
            "audit_source_identities.py",
            "build_evidence.py",
            "prepare_figure_sources.py",
            "prepare_calibration.py",
            "audit_presence.py",
        ],
        "figures": ["build_figures.py"],
        "report": ["write_report_source.py", "build_report.py"],
        "validate": [
            "validate_controls.py",
            "validate_candidates.py",
            "validate_figure_rebuild.py",
            "validate_artifacts.py",
            "validate_restart.py",
        ],
    }
    parser.add_argument("--stage", choices=[*stages, "all"], default="all")
    parser.add_argument("--report-python", default=sys.executable)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    base = root / "provenance/researcher-evidence/2026-10-16/v1"
    if args.stage in ["all", "report", "validate"]:
        check = subprocess.run(
            [args.report_python, "-c", "import reportlab, pypdf, pandas, PIL"],
            capture_output=True,
        )
        if check.returncode:
            parser.error(
                "Set --report-python to a runtime with ReportLab, pypdf, pandas and Pillow."
            )
    for stage, scripts in stages.items():
        if args.stage not in [stage, "all"]:
            continue
        for script in scripts:
            interpreter = (
                args.report_python
                if script in ["build_report.py", "validate_artifacts.py"]
                else sys.executable
            )
            subprocess.run([interpreter, str(base / script)], cwd=root, check=True)


if __name__ == "__main__":
    main()
