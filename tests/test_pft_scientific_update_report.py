"""Synthetic regression fixtures for the collaborator report's claim validator."""

from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "provenance/pft-scientific-update/2026-10-22/v1"
spec = importlib.util.spec_from_file_location(
    "pft_briefing_checks", PACKET / "validate_report.py"
)
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


@pytest.fixture
def synthetic_claims():
    # Deliberately fictional display values; production observations are checked
    # independently against saved tables by validate_report.py, not constants.
    values = {"fixture_recall": 0.6, "fixture_fraction_error": 0.2}
    claims = [
        dict(
            id=k,
            value=v,
            source=str(Path(__file__).relative_to(ROOT)),
            selection="Synthetic fixture",
            scope="Not scientific evidence",
        )
        for k, v in values.items()
    ]
    return claims, values


def test_matching_claims_are_accepted(synthetic_claims):
    claims, expected = synthetic_claims
    checks.validate_claims(claims, expected)


def test_changed_numeric_claim_is_rejected(synthetic_claims):
    claims, expected = synthetic_claims
    changed = deepcopy(claims)
    changed[0]["value"] = 0.95
    with pytest.raises(AssertionError, match="fixture_recall"):
        checks.validate_claims(changed, expected)


def test_untraceable_claim_is_rejected(synthetic_claims):
    claims, expected = synthetic_claims
    claims.append(
        dict(
            id="invented_field_accuracy", value=0.99, source="", selection="", scope=""
        )
    )
    with pytest.raises(AssertionError, match="Missing or unexpected"):
        checks.validate_claims(claims, expected)


def test_duplicate_claim_is_rejected(synthetic_claims):
    claims, expected = synthetic_claims
    claims.append(deepcopy(claims[0]))
    with pytest.raises(AssertionError, match="Duplicate numeric"):
        checks.validate_claims(claims, expected)
