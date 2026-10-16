"""Build Lean proofs, evaluate rational bridge, audit axioms and preserve evidence.

Run with the repository Python environment: .venv/bin/python formal/check.py
A normal `lake build` is the authoritative Lean compilation step.
"""

from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess

FORMAL = Path(__file__).resolve().parent
REPO = FORMAL.parent
CHECKS = FORMAL / "checks"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, filename, env):
    result = subprocess.run(
        command,
        cwd=FORMAL,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (CHECKS / filename).write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"{command} failed; see {CHECKS / filename}")
    return result.stdout


def main():
    CHECKS.mkdir(exist_ok=True)
    env = os.environ.copy()
    local_elan = FORMAL / ".elan"
    if local_elan.is_dir():
        env["ELAN_HOME"] = str(local_elan)
    lake = shutil.which("lake")
    if not lake:
        raise RuntimeError("Install elan/Lean as documented in formal/README.md")
    sources = sorted((FORMAL / "SpectralBridge").glob("*.lean"))
    # Reject proof escape hatches in source code (strip comments before checking).
    for p in sources:
        code = re.sub(r"/-.*?-/", "", p.read_text(), flags=re.S)
        code = re.sub(r"--[^\n]*", "", code)
        if re.search(r"\b(sorry|admit|axiom|unsafe)\b", code):
            raise RuntimeError(f"Uncertified proof escape hatch in {p}")
    run([lake, "build"], "lean-build.log", env)
    axioms = run(
        [lake, "env", "lean", "SpectralBridge/AxiomAudit.lean"], "axioms.log", env
    )
    used = set()
    for group in re.findall(r"depends on axioms: \[([^\]]*)\]", axioms):
        used.update(x.strip() for x in group.split(",") if x.strip())
    if "sorryAx" in axioms or used - {"propext", "Classical.choice", "Quot.sound"}:
        raise RuntimeError(f"Axiom audit found unapproved dependencies: {used}")
    output = run(
        [lake, "env", "lean", "--run", "SpectralBridge/Bridge.lean"], "bridge.log", env
    )
    data = json.loads(output[output.rfind("\n{") + 1 :] if "\n{" in output else output)
    target = CHECKS / "rational_examples.json"
    target.write_text(json.dumps(data, indent=2) + "\n")
    (CHECKS / "bridge_execution.json").write_text(
        json.dumps(
            {
                "status": "Lean executed; exact rational output",
                "lean_source_sha256": sha(FORMAL / "SpectralBridge/Bridge.lean"),
                "output_sha256": sha(target),
            },
            indent=2,
        )
        + "\n"
    )
    snapshot = json.loads((FORMAL / "source_manifest.json").read_text())
    for name, digest in snapshot["sha256"].items():
        if sha(REPO / name) != digest:
            raise RuntimeError(f"Audited implementation/config/test changed: {name}")
    preserved = {}
    for manifest in [
        REPO
        / "provenance/researcher-pft-information/2026-10-15/v1/final_manifest.json",
        REPO / "provenance/researcher-evidence/2026-10-16/v1/final_manifest.json",
        REPO / "provenance/manuscript-synthesis/2026-10-16/v1/packet_manifest.json",
    ]:
        m = json.loads(manifest.read_text())
        for name, digest in m.get("sha256", m.get("files", {})).items():
            if sha(REPO / name) != digest:
                raise RuntimeError(f"Historical evidence changed: {name}")
            preserved[name] = digest
    (CHECKS / "preservation.json").write_text(
        json.dumps(
            {"status": "passed", "unique_previous_files_unchanged": len(preserved)},
            indent=2,
        )
        + "\n"
    )
    (CHECKS / "proof_build.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "toolchain": (FORMAL / "lean-toolchain").read_text().strip(),
                "lake_manifest_sha256": sha(FORMAL / "lake-manifest.json"),
                "foundation_axioms": sorted(used),
                "lean_sources": {str(p.relative_to(FORMAL)): sha(p) for p in sources},
                "axiom_audit_sha256": sha(CHECKS / "axioms.log"),
                "no_custom_axioms_or_proof_holes": True,
                "python_conformance": "Run pytest separately; see conformance.log",
            },
            indent=2,
        )
        + "\n"
    )
    print("Lean build, axiom audit, rational bridge and historical preservation passed")


if __name__ == "__main__":
    main()
