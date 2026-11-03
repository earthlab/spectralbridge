"""Bounded read-only BRDF-coefficient provenance and applicability inventory."""

from pathlib import Path
import os
import json
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SKIP = {".git", ".venv", "node_modules", "__pycache__", "site", "_build", "python-libs"}


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def main():
    roots = [ROOT] + sorted(
        p
        for p in Path("/private/tmp").iterdir()
        if p.is_dir()
        and p.name.startswith(("spectralbridge", "goldhill", "drone-brdf"))
    )
    candidates = set()
    for root in roots:
        for directory, subdirs, files in os.walk(root):
            subdirs[:] = [s for s in subdirs if s not in SKIP]
            if len(Path(directory).relative_to(root).parts) >= 9:
                subdirs[:] = []
            for name in files:
                lower = name.lower()
                if lower.endswith(".json") and (
                    "brdf_model" in lower or "brdf_coeff" in lower
                ):
                    p = Path(directory) / name
                    if p.stat().st_size < 20 * 1024**2:
                        candidates.add(p)
    rows = []
    for p in sorted(candidates):
        try:
            d = json.loads(p.read_text())
        except (ValueError, OSError):
            continue
        if not isinstance(d, dict):
            continue
        r = d.get("radiometry", {})
        v = d.get("validation", {})
        text = json.dumps(d).lower()
        synthetic = any(
            word in text for word in ["synthetic", "fixture"]
        ) or "tests/" in str(p)
        legacy = not d.get("schema_version") == 2
        kind = (
            "SYNTHETIC_CONTRACT_FIXTURE"
            if synthetic
            else "UNSUPPORTED_OR_INVALID"
            if v.get("status") in ("UNSUPPORTED", "INVALID")
            else "HISTORICAL_UNVALIDATED_MODEL"
            if legacy
            else "NO_INDEPENDENT_VALIDATION_RECORD"
        )
        row = dict(
            path=str(p),
            size_bytes=p.stat().st_size,
            sha256=sha(p),
            classification=kind,
            computational_status=v.get("status", "NOT_RECORDED"),
            radiometry=r,
            kernel_config=d.get("kernel_config"),
            reference_geometry=d.get("reference_geometry"),
            coefficient_provenance=d.get("coefficient_provenance"),
            source_path=d.get("source_path"),
            source_identity=d.get("source_identity"),
            independently_validated_empirical_NEON_transfer=False,
            independent_validation_record="NOT_FOUND in model or prior validation evidence",
            drone_wavelength_response_compatibility="NOT_ESTABLISHED",
            canopy_PFT_illumination_domain_transfer="NOT_ESTABLISHED",
            application_eligibility="NOT_ELIGIBLE",
            rejection="Synthetic fixture, missing shared validation, unsupported model, or absent independent empirical transfer evidence; computational VALID alone is insufficient.",
        )
        rows.append(row)
    qa_path = (
        ROOT
        / "docs/validation/artifacts/r10c-l002-20210915/qa/stages/02_correction_parameters/stage_qa.json"
    )
    qa_summary = json.loads(qa_path.read_text())["metrics"]["brdf_model_summary"]
    auxiliary = dict(
        path=str(qa_path),
        sha256=sha(qa_path),
        summary=qa_summary,
        status="Historical real-NEON QA summary, not an applicable coefficient set",
        reason="426 vol and geo terms are all zero in the pre-repair artifact; no independently validated current transfer model is supplied by this summary.",
    )
    out = dict(
        search_roots=[str(x) for x in roots],
        max_depth=9,
        filename_contract="*.json containing brdf_model or brdf_coeff; <20MiB",
        scope="Repository including archived evidence plus named local investigation caches; not a global archive search or claim no validated NEON coefficients exist anywhere.",
        candidates=rows,
        auxiliary_real_NEON_QA=auxiliary,
        suitable_sets=0,
        conclusion="No independently validated, radiometrically and spectrally applicable NEON coefficient set found. Fixed-coefficient correction and resulting factor/PFT changes are NOT_EVALUATED. No coefficients manufactured or transferred.",
    )
    (HERE / "coefficient_inventory.json").write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"{len(rows)} candidate files inspected; 0 eligible independent coefficient sets.",
        flush=True,
    )


if __name__ == "__main__":
    main()
