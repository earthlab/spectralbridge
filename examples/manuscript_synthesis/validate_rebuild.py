"""Require exact export reconstruction with original spectra/analysis caches denied."""

import json
import subprocess
import sys
from .figure_data import BASE, REPO, sha


def guard(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        name = str(args[0])
        if (
            "/artifacts/plant_spectral_atlas/" in name
            or "Aug_2026_all_polygons_merged_pixel_extraction.parquet" in name
        ):
            raise RuntimeError("Source spectral/cache access denied: " + name)


def main():
    out = REPO / "output/figures/manuscript_synthesis"
    files = [out / ("figure_main_synthesis." + ext) for ext in ["pdf", "svg", "png"]]
    before = {p.name: sha(p) for p in files}
    code = "import sys,runpy;from examples.manuscript_synthesis.validate_rebuild import guard;sys.addaudithook(guard);"
    code += 'sys.argv=["build_figure","--reuse-data"];runpy.run_module("examples.manuscript_synthesis.build_figure",run_name="__main__")'
    subprocess.run([sys.executable, "-c", code], cwd=REPO, check=True)
    assert before == {p.name: sha(p) for p in files}
    result = {
        "status": "passed",
        "original_spectra_and_analysis_cache_access_denied": True,
        "all_three_exports_byte_identical": True,
        "sha256": before,
    }
    (BASE / "rebuild_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
