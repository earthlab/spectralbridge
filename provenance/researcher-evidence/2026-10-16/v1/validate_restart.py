"""Exercise completed stages, require unchanged owned fits and numerical exports."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ledgers = sorted((BASE / "checkpoints").glob("*/complete.json"))
    assert len(ledgers) == 34
    before = {str(p): p.stat().st_mtime_ns for p in ledgers}
    files = [
        BASE / "tables" / name
        for name in [
            "metrics.csv",
            "rates.csv",
            "confusions.csv",
            "identity_correctness.parquet",
            "same_candidate_ridge.csv",
        ]
    ]
    hashes = {str(p): sha(p) for p in files}
    for stage in ["controls", "candidate"]:
        subprocess.run(
            [
                sys.executable,
                str(REPO / "examples/researcher_evidence_validation.py"),
                "--stage",
                stage,
            ],
            cwd=REPO,
            check=True,
        )
    assert before == {str(p): p.stat().st_mtime_ns for p in ledgers}
    assert hashes == {str(p): sha(p) for p in files}
    (BASE / "restart_validation.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "completed_training_cases_reused": 34,
                "fit_ledger_mtimes_unchanged": True,
                "aggregate_numerical_exports_byte_identical": True,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "Restart passed: 34 completed cases reused without refits or changed numerical exports."
    )


if __name__ == "__main__":
    main()
