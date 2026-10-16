"""Rebuild all figure exports with original data and analysis caches inaccessible."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent


def hashes():
    return {
        str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((BASE / "figures").iterdir())
        if p.suffix in {".png", ".pdf", ".svg"}
    }


def guard(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        name = str(args[0])
        if (
            "artifacts/plant_spectral_atlas/" in name
            or "Aug_2026_all_polygons_merged_pixel_extraction.parquet" in name
        ):
            raise RuntimeError(
                "Figure rebuild attempted to open original data/cache: " + name
            )


def main():
    before = hashes()
    sys.addaudithook(guard)
    for script in ["build_figures.py", "build_confusions.py"]:
        code = "import runpy, sys; sys.path.insert(0, " + repr(str(BASE)) + "); "
        code += "from validate_rebuild import guard; sys.addaudithook(guard); "
        code += "runpy.run_path(" + repr(str(BASE / script)) + ", run_name='__main__')"
        subprocess.run([sys.executable, "-c", code], check=True)
    after = hashes()
    assert before == after, [name for name in before if before[name] != after.get(name)]
    result = {
        "status": "passed",
        "figure_files": len(after),
        "byte_identical": True,
        "source_and_analysis_cache_access_denied": True,
        "sha256": after,
    }
    (BASE / "rebuild_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "All",
        len(after),
        "figure exports rebuilt byte-identically from compact numerical products.",
    )


if __name__ == "__main__":
    main()
