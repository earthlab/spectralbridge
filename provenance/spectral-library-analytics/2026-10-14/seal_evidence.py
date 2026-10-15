"""Refresh the source-specific evidence ledger after validated report rebuilding."""

from pathlib import Path
import hashlib
import json

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal():
    path = BASE / "evidence_manifest.json"
    evidence = json.loads(path.read_text())
    evidence["implementation_hashes"]["pyproject.toml"] = sha(REPO / "pyproject.toml")
    evidence["implementation_hashes"].update(
        {str(p.relative_to(REPO)): sha(p) for p in BASE.glob("*.py")}
    )
    for name in list(evidence["implementation_hashes"]):
        evidence["implementation_hashes"][name] = sha(REPO / name)
    for name, expected in evidence["canonical_reference_manifest_hashes"].items():
        if sha(REPO / name) != expected:
            raise ValueError("Changed canonical reference ledger: " + name)
    evidence["outputs"] = {
        str(p.relative_to(BASE)): sha(p)
        for p in sorted(BASE.rglob("*"))
        if p.is_file()
        and p.name != "evidence_manifest.json"
        and "__pycache__" not in str(p)
    }
    evidence["pdf_sha256"] = sha(REPO / evidence["pdf"])
    path.write_text(json.dumps(evidence, indent=2) + "\n")
    for name, expected in evidence["outputs"].items():
        if sha(BASE / name) != expected:
            raise ValueError("Evidence drift: " + name)
    report = json.loads((BASE / "manifests/report_manifest.json").read_text())
    for section in report["sections"]:
        for name in section.get("result_files", []) + section.get("figure_files", []):
            if not (REPO / name).is_file():
                raise ValueError("Missing report evidence: " + name)
    print("Verified", len(evidence["outputs"]), "evidence files and all report links")


if __name__ == "__main__":
    seal()
