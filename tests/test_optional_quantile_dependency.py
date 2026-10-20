"""Cohort tests remain active without the optional quantile fitting dependency."""

from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.lite
def test_year_cohorts_run_without_xgboost_and_only_fitting_skips():
    script = """
import importlib.abc
import sys
class MissingQuantiles(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "xgboost" or fullname.startswith("xgboost."):
            raise ModuleNotFoundError("No module named 'xgboost'", name="xgboost")
sys.meta_path.insert(0, MissingQuantiles())
import pytest
class Outcomes:
    def __init__(self):
        self.passed = 0
        self.skipped = []
    def pytest_runtest_logreport(self, report):
        if report.when == "call" and report.passed:
            self.passed += 1
        if report.skipped:
            self.skipped.append(report.nodeid)
outcomes = Outcomes()
result = pytest.main(["-q", "-o", "addopts=", "tests/test_plant_spectral_years.py"], plugins=[outcomes])
print("COHORT_TESTS_PASSED=" + str(outcomes.passed))
print("QUANTILE_TESTS_SKIPPED=" + str(len(outcomes.skipped)))
for nodeid in outcomes.skipped:
    print("SKIPPED_FIT=" + nodeid)
raise SystemExit(result)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "COHORT_TESTS_PASSED=3" in output
    assert "QUANTILE_TESTS_SKIPPED=1" in output
    assert (
        "SKIPPED_FIT=tests/test_plant_spectral_years.py::test_year_site_panels_refit_correct_cohorts_and_mark_missing_acquisitions"
        in output
    )
