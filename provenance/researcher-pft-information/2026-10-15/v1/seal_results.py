"""Seal the final versioned packet, helper contracts and standalone report."""

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for name in [
        "numerical_validation.json",
        "model_replay_validation.json",
        "rebuild_validation.json",
        "pdf_validation.json",
    ]:
        assert json.loads((BASE / name).read_text())["status"] == "passed", name
    paths = [
        p
        for p in BASE.rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.name != "final_manifest.json"
    ]
    paths += [
        REPO / name
        for name in [
            "src/spectralbridge/researcher_information.py",
            "src/spectralbridge/mesma_readiness.py",
            "tests/test_researcher_information.py",
            "tests/test_scientific_docs_integration.py",
            "examples/researcher_pft_information.py",
            "output/pdf/researcher_pft_information/Researcher_Categories_Spectral_Information_and_Abundance.pdf",
        ]
    ]
    result = {
        "status": "sealed locally",
        "completed": "2026-10-16",
        "scope": "Researcher cover_category only; synthetic abundance, not field validation",
        "sha256": {str(p.relative_to(REPO)): digest(p) for p in sorted(paths)},
    }
    dest = BASE / "final_manifest.json"
    dest.write_text(json.dumps(result, indent=2) + "\n")
    for name, expected in result["sha256"].items():
        assert digest(REPO / name) == expected, name
    print("Sealed and verified", len(paths), "files.")


if __name__ == "__main__":
    main()
