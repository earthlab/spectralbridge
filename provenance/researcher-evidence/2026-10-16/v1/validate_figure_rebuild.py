"""Require exact figure rebuilding while rejecting raw-data and cache reads."""

from pathlib import Path
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def guard(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        name = str(args[0])
        if (
            "/artifacts/plant_spectral_atlas/" in name
            or "Aug_2026_all_polygons_merged_pixel_extraction.parquet" in name
        ):
            raise RuntimeError(
                "Raw data/cache access denied during figure rebuild: " + name
            )


def hashes():
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((BASE / "figures").iterdir())
        if p.suffix in [".png", ".pdf", ".svg"]
    }


def main():
    before = hashes()
    assert len(before) == 30
    code = "import sys,runpy;sys.path.insert(0," + repr(str(BASE)) + ");"
    code += "from validate_figure_rebuild import guard;sys.addaudithook(guard);"
    code += (
        "runpy.run_path("
        + repr(str(BASE / "build_figures.py"))
        + ',run_name="__main__")'
    )
    subprocess.run([sys.executable, "-c", code], check=True)
    assert before == hashes()
    result = {
        "status": "passed",
        "figure_files": len(before),
        "byte_identical": True,
        "original_data_and_analysis_caches_access_denied": True,
        "sha256": before,
    }
    (BASE / "figure_rebuild_validation.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("All 30 figure exports reproduce byte-identically from compact saved tables.")


if __name__ == "__main__":
    main()
