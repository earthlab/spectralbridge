"""Audit the exact RC2 payload without rebuilding or changing its bytes."""

from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import tarfile
import zipfile
from email.parser import BytesParser

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DIST = ROOT / "archive/local/release-rc2/2026-11-04/dist"
EXPECTED = "2.3.0rc2"
results = []
payloads = {}
for path in sorted(DIST.iterdir()):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as z:
            files = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path) as t:
            files = {
                m.name: t.extractfile(m).read() for m in t.getmembers() if m.isfile()
            }
    else:
        continue
    payloads[path.suffix] = files
    problems = []
    for name, data in files.items():
        parts = PurePosixPath(name).parts
        if name.startswith("/") or ".." in parts:
            problems.append("unsafe archive path: " + name)
        if any(
            p in {".git", ".venv", "__pycache__", "archive", "provenance"}
            for p in parts
        ):
            if not name.endswith("/provenance/hytools.json"):
                problems.append("non-runtime research/private payload: " + name)
        if name.endswith(
            (".tif", ".tiff", ".h5", ".hdf5", ".parquet", ".gpkg", ".ipynb", ".pyc")
        ):
            problems.append("unexpected data/intermediate: " + name)
        if any(
            p in {".env", ".irods", ".aws", ".ssh", "PROMPT_LOG.md", "gocmd"}
            for p in parts
        ):
            problems.append("private or development file: " + name)
        if len(data) > 10 * 1024 * 1024:
            problems.append("unexpected large file: " + name)
        if name.endswith(
            (".py", ".toml", ".json", ".md", ".txt", ".cfg")
        ) and re.search(rb"/Users/tuff/|/home/ubuntu/|/mnt/data/", data):
            problems.append("machine-specific path: " + name)
    metadata = next(
        v
        for k, v in files.items()
        if k.endswith("/METADATA") or k.count("/") == 1 and k.endswith("/PKG-INFO")
    )
    parsed = BytesParser().parsebytes(metadata)
    assert parsed["Name"] == "earthlab-spectralbridge"
    assert parsed["Version"] == EXPECTED
    assert parsed["License-Expression"] == "GPL-3.0-or-later"
    for required in ["LICENSE", "NOTICE"]:
        assert any(k.endswith("/" + required) for k in files), required
    assert any(k.endswith("spectralbridge/topographic.py") for k in files)
    assert any(k.endswith("spectralbridge/drone_view_geometry.py") for k in files)
    assert any(
        k.endswith("spectralbridge/data/drone_field_manifest.csv") for k in files
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    results.append(
        dict(
            file=path.name,
            sha256=digest,
            size_bytes=path.stat().st_size,
            files=len(files),
            metadata=dict(
                name=parsed["Name"],
                version=parsed["Version"],
                license=parsed["License-Expression"],
                extras=parsed.get_all("Provides-Extra"),
                requirements=parsed.get_all("Requires-Dist"),
            ),
            problems=problems,
        )
    )
(HERE / "distribution-audit.json").write_text(json.dumps(results, indent=2) + "\n")
(HERE / "SHA256SUMS").write_text(
    "".join(r["sha256"] + "  " + r["file"] + "\n" for r in results)
)
for r in results:
    print(r["file"], r["size_bytes"], "bytes", len(r["problems"]), "payload issues")
    for issue in r["problems"]:
        print(issue)
assert not any(r["problems"] for r in results)
assert len(results) == 2

# The replacement sdist must contain byte-identical runtime files to the wheel.
wheel_files = payloads[".whl"]
source_files = {
    k.split("/src/", 1)[1]: v for k, v in payloads[".gz"].items() if "/src/" in k
}
shared = [
    k for k in wheel_files if k.startswith(("spectralbridge/", "cross_sensor_cal/"))
]
for name in shared:
    assert source_files.get(name) == wheel_files[name], name
(HERE / "runtime-payload-parity.json").write_text(
    json.dumps(dict(files=len(shared), wheel_sdist_runtime_identical=True), indent=2)
    + "\n"
)
print("Exact wheel/sdist runtime parity:", len(shared), "files")
