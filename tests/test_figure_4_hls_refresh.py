"""A stale source or analysis must fail before mutating publisher inputs."""

import importlib.util
import json
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    "figure4_refresh",
    Path(__file__).resolve().parents[1]
    / "examples/publication_figures/refresh_figure_4_hls_expansion.py",
)
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


@pytest.mark.parametrize("changed", ["source", "analysis"])
def test_stale_evidence_refused_before_any_bundle_mutation(
    tmp_path, monkeypatch, changed
):
    source = tmp_path / "source"
    analysis = tmp_path / "analysis"
    bundle = tmp_path / "bundle"
    for p in [source, analysis, bundle]:
        p.mkdir()
    src = source / "observations.csv"
    src.write_text("source data\n")
    result = analysis / "results.csv"
    result.write_text("analysis data\n")
    sentinel = bundle / "publisher.csv"
    sentinel.write_text("preserve me\n")
    manifest = {
        "input_sha256": {src.name: refresh.sha(src)},
        "output_sha256": {result.name: refresh.sha(result)},
    }
    (analysis / "manifest.json").write_text(json.dumps(manifest))
    (src if changed == "source" else result).write_text("changed\n")
    monkeypatch.setattr(refresh, "SOURCE", source)
    monkeypatch.setattr(refresh, "ANALYSIS", analysis)
    monkeypatch.setattr(refresh, "FIG", bundle)
    with pytest.raises(ValueError, match="Changed reference|Changed analysis"):
        refresh.run()
    assert sentinel.read_text() == "preserve me\n"
    assert list(bundle.iterdir()) == [sentinel]
