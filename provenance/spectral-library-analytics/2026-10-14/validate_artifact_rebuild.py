from pathlib import Path
import subprocess
import json
import hashlib
import os

b = Path("provenance/spectral-library-analytics/2026-10-14")
pdf = Path(
    "output/pdf/spectral_library_analytics/SpectralBridge_Spectral_Library_Analytics_Report.pdf"
)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


before = {str(p): sha(p) for p in (b / "figures").glob("*") if p.is_file()}
before[str(pdf)] = sha(pdf)
env = dict(os.environ, MPLCONFIGDIR="/tmp/spectralbridge-mpl", OPENBLAS_NUM_THREADS="1")
subprocess.run(
    [
        ".venv/bin/python",
        "-c",
        "import importlib.util;p='examples/spectral_library_analytics_results.py';s=importlib.util.spec_from_file_location('figures',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.draw_figures()",
    ],
    check=True,
    env=env,
)
subprocess.run(
    [".venv/bin/python", str(b / "build_explanatory_figures.py")], check=True, env=env
)
subprocess.run(
    [
        "/Users/tuff/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
        str(b / "build_report.py"),
    ],
    check=True,
    env=env,
)
changed = [p for p, h in before.items() if sha(Path(p)) != h]
result = dict(
    status="passed" if not changed else "failed",
    artifacts=len(before),
    changed=changed,
    figures_and_PDF_byte_identical=not changed,
)
(b / "manifests/rebuild_validation.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(result)
