"""Verify prior immutability and seal new reproducible scientific evidence."""

from pathlib import Path
import hashlib
import json
import pandas as pd

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
PRIOR = REPO / "provenance/researcher-pft-information/2026-10-15/v1"


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    for name in [
        "control_validation.json",
        "candidate_validation.json",
        "source_identity_validation.json",
        "presence_validation.json",
        "restart_validation.json",
        "synthesis_validation.json",
        "artifact_validation.json",
        "figure_rebuild_validation.json",
    ]:
        assert json.loads((BASE / name).read_text())["status"] == "passed", name
    previous = json.loads((PRIOR / "final_manifest.json").read_text())
    for name, h in previous["sha256"].items():
        assert sha(REPO / name) == h, name
    foundation = json.loads((BASE / "foundation.json").read_text())
    source = REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    assert sha(source) == foundation["source_sha256"]
    report = json.loads((BASE / "report_manifest.json").read_text())
    assert sha(REPO / report["pdf"]) == report["pdf_sha256"]
    for name, h in report["table_hashes"].items():
        assert sha(BASE / name) == h, name
    for name, h in report["figure_hashes"].items():
        assert sha(BASE / name) == h, name
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
            "src/spectralbridge/researcher_validation.py",
            "tests/test_researcher_validation.py",
            "tests/test_fraction_grid_calibration.py",
            "examples/researcher_evidence_validation.py",
            report["pdf"],
        ]
    ]
    upstream = {
        str(source.relative_to(REPO)): foundation["source_sha256"],
        str((PRIOR / "final_manifest.json").relative_to(REPO)): sha(
            PRIOR / "final_manifest.json"
        ),
    }
    upstream.update(report["numerical_source_hashes"])
    for name in [
        "provenance/scientific-closure/2026-10-15/manifests/metadata_audit.json",
        "provenance/scientific-closure/2026-10-15/tables/annotation_year_audit.csv",
        "artifacts/plant_spectral_atlas/researcher_pft_statistics/method_comparison.csv",
        "artifacts/plant_spectral_atlas/sensor_pft_transfer/statistics_manifest.json",
    ]:
        upstream[name] = sha(REPO / name)
    index = pd.read_csv(PRIOR / "tables/abundance_case_index.csv")
    for name in sorted(set(index.predictions) | set(index.truth)):
        upstream[name] = sha(REPO / name)
    for p in (
        REPO / "artifacts/plant_spectral_atlas/researcher_pft_statistics/checkpoints"
    ).glob("*_flight_history.npz"):
        upstream[str(p.relative_to(REPO))] = sha(p)
    result = {
        "status": "sealed locally",
        "completed": "2026-10-16",
        "prior_sealed_files_verified_unchanged": len(previous["sha256"]),
        "scope": "Five researcher categories; separate difference, recognition, synthetic fractions and missing field cover",
        "sha256": {str(p.relative_to(REPO)): sha(p) for p in sorted(paths)},
        "upstream_references_sha256": upstream,
    }
    (BASE / "final_manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    for name, h in result["sha256"].items():
        assert sha(REPO / name) == h, name
    print(
        "Sealed",
        len(paths),
        "owned files;",
        len(upstream),
        "upstream references;",
        len(previous["sha256"]),
        "prior files unchanged.",
    )


if __name__ == "__main__":
    main()
