from __future__ import annotations

import json
from pathlib import Path

from scripts.run_validation_campaign import MODULE_LABELS, build_offline_cases
from spectralbridge.validation import (
    ValidationCase,
    ValidationObservation,
    load_campaign,
    run_campaign,
    run_case,
    write_campaign,
)


def test_validation_case_records_pass_failure_and_skip() -> None:
    passed = run_case(
        ValidationCase(
            module="demo",
            variation_id="pass",
            description="passing case",
            inputs={"value": 1},
            expected={"positive": True},
            runner=lambda: ValidationObservation(
                diagnostics={"observed": 1}, checks={"positive": True}
            ),
        )
    )
    failed = run_case(
        ValidationCase(
            module="demo",
            variation_id="fail",
            description="failing case",
            inputs={"value": -1},
            expected={"positive": True},
            runner=lambda: ValidationObservation(
                diagnostics={"observed": -1}, checks={"positive": False}
            ),
        )
    )
    errored = run_case(
        ValidationCase(
            module="demo",
            variation_id="error",
            description="error case",
            inputs={},
            expected={},
            runner=lambda: (_ for _ in ()).throw(ValueError("diagnostic failure")),
        )
    )
    skipped = run_case(
        ValidationCase(
            module="demo",
            variation_id="skip",
            description="skipped case",
            inputs={},
            expected={},
            runner=None,
            skip_reason="live data not approved",
        )
    )

    assert passed.status == "passed"
    assert failed.status == "failed"
    assert errored.status == "failed"
    assert "ValueError: diagnostic failure" == errored.error
    assert skipped.status == "skipped"
    assert skipped.skip_reason == "live data not approved"


def test_campaign_round_trip_preserves_summary(tmp_path: Path) -> None:
    cases = [
        ValidationCase(
            module="demo",
            variation_id=f"case-{index}",
            description="round trip",
            inputs={"index": index},
            expected={"even": index % 2 == 0},
            runner=lambda index=index: ValidationObservation(
                diagnostics={"remainder": index % 2},
                checks={"recorded": True},
            ),
        )
        for index in range(3)
    ]
    campaign = run_campaign(
        cases,
        campaign_id="round-trip",
        mode="offline",
        repo_root=tmp_path,
    )
    output = write_campaign(campaign, tmp_path / "campaign.json")
    loaded = load_campaign(output)

    assert loaded["summary"] == {
        "failed": 0,
        "passed": 3,
        "skipped": 0,
        "total": 3,
    }
    assert len(loaded["results"]) == 3
    assert json.loads(output.read_text()) == loaded


def test_offline_validation_smoke_exercises_every_module(tmp_path: Path) -> None:
    cases = build_offline_cases(tmp_path, count=1)
    campaign = run_campaign(
        cases,
        campaign_id="pytest-offline-smoke",
        mode="offline",
        repo_root=tmp_path,
    )

    observed_modules = {result["module"] for result in campaign["results"]}
    assert observed_modules == set(MODULE_LABELS)
    assert campaign["summary"] == {
        "total": len(MODULE_LABELS),
        "passed": len(MODULE_LABELS),
        "failed": 0,
        "skipped": 0,
    }
