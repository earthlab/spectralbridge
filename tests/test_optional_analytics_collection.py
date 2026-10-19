"""Optional analytics tests must not break collection in the lite environment."""

from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.lite
def test_analytics_modules_skip_when_sklearn_is_unavailable():
    # Block discovery even when the developer environment has analytics installed.
    # Marker selection happens after collection, so -m lite cannot guard imports.
    script = """
import importlib.abc
import sys
class MissingAnalytics(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "sklearn" or fullname.startswith("sklearn."):
            raise ModuleNotFoundError("No module named 'sklearn'", name="sklearn")
sys.meta_path.insert(0, MissingAnalytics())
import pytest
class CollectionOutcomes:
    def __init__(self):
        self.skipped = []
    def pytest_collectreport(self, report):
        if report.skipped:
            self.skipped.append(report.nodeid)
outcomes = CollectionOutcomes()
result = pytest.main([
    "--collect-only", "-q", "-o", "addopts=",
    "tests/test_selected_endmember_quality.py",
    "tests/test_spectral_analytics_extensions.py",
    "tests/test_spectral_analytics_mixtures.py",
], plugins=[outcomes])
print("OPTIONAL_ANALYTICS_SKIPS=" + str(len(outcomes.skipped)))
for nodeid in sorted(outcomes.skipped):
    print("OPTIONAL_ANALYTICS_MODULE=" + nodeid)
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
    assert result.returncode == 5, output  # No collected tests: all three skipped.
    assert "OPTIONAL_ANALYTICS_SKIPS=3" in output
    for name in (
        "selected_endmember_quality",
        "spectral_analytics_extensions",
        "spectral_analytics_mixtures",
    ):
        assert "OPTIONAL_ANALYTICS_MODULE=tests/test_" + name + ".py" in output
    assert "ERROR" not in output
