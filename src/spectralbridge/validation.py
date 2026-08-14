"""Structured evidence records for SpectralBridge validation campaigns.

Validation campaigns are distinct from ordinary unit tests.  A unit test protects
one contract; a campaign runs a named operation over a matrix of input variations
and preserves the diagnostics as publication-facing evidence.
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


ValidationRunner = Callable[[], "ValidationObservation"]


def _json_value(value: Any) -> Any:
    """Return a recursively JSON-compatible representation of ``value``."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _json_value(value.item())
        except (TypeError, ValueError):
            pass
    return str(value)


@dataclass(frozen=True)
class ValidationObservation:
    """Diagnostics and explicit checks returned by one validation variation."""

    diagnostics: Mapping[str, Any]
    checks: Mapping[str, bool]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationCase:
    """One operation/input combination in a validation campaign."""

    module: str
    variation_id: str
    description: str
    inputs: Mapping[str, Any]
    expected: Mapping[str, Any]
    runner: ValidationRunner | None = field(repr=False, compare=False)
    skip_reason: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Serializable result from one :class:`ValidationCase`."""

    module: str
    variation_id: str
    description: str
    inputs: Mapping[str, Any]
    expected: Mapping[str, Any]
    status: str
    diagnostics: Mapping[str, Any]
    checks: Mapping[str, bool]
    duration_seconds: float
    notes: tuple[str, ...] = ()
    error: str | None = None
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_value(asdict(self))


def run_case(case: ValidationCase) -> ValidationResult:
    """Run one case, converting failures and skips into structured evidence."""

    if case.runner is None or case.skip_reason:
        return ValidationResult(
            module=case.module,
            variation_id=case.variation_id,
            description=case.description,
            inputs=_json_value(case.inputs),
            expected=_json_value(case.expected),
            status="skipped",
            diagnostics={},
            checks={},
            duration_seconds=0.0,
            skip_reason=case.skip_reason or "No validation runner was provided.",
        )

    started = time.perf_counter()
    try:
        observation = case.runner()
        checks = {str(name): bool(value) for name, value in observation.checks.items()}
        status = "passed" if checks and all(checks.values()) else "failed"
        error = None if checks else "Validation case returned no explicit checks."
    except Exception as exc:
        observation = ValidationObservation(diagnostics={}, checks={})
        checks = {}
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"

    return ValidationResult(
        module=case.module,
        variation_id=case.variation_id,
        description=case.description,
        inputs=_json_value(case.inputs),
        expected=_json_value(case.expected),
        status=status,
        diagnostics=_json_value(observation.diagnostics),
        checks=checks,
        duration_seconds=round(time.perf_counter() - started, 6),
        notes=tuple(observation.notes),
        error=error,
    )


def _git_revision(repo_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _git_dirty(repo_root: Path) -> bool | None:
    try:
        output = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return bool(output.strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def run_campaign(
    cases: Iterable[ValidationCase],
    *,
    campaign_id: str,
    mode: str,
    repo_root: Path,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run ``cases`` and return a versioned, machine-readable campaign record."""

    results = [run_case(case) for case in cases]
    counts = {
        status: sum(result.status == status for result in results)
        for status in ("passed", "failed", "skipped")
    }
    return {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "mode": mode,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": _git_revision(Path(repo_root)),
        "git_dirty": _git_dirty(Path(repo_root)),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "metadata": _json_value(metadata or {}),
        "summary": {"total": len(results), **counts},
        "results": [result.to_dict() for result in results],
    }


def write_campaign(campaign: Mapping[str, Any], path: Path) -> Path:
    """Atomically write one campaign JSON file."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_json_value(campaign), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def load_campaign(path: Path) -> dict[str, Any]:
    """Load and minimally validate a campaign record."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema_version", "campaign_id", "mode", "summary", "results"}
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError(f"Validation campaign is missing keys: {missing}")
    if payload["schema_version"] != 1:
        raise ValueError(
            f"Unsupported validation schema version: {payload['schema_version']}"
        )
    if not isinstance(payload["results"], list):
        raise ValueError("Validation campaign 'results' must be a list")
    return payload


__all__ = [
    "ValidationCase",
    "ValidationObservation",
    "ValidationResult",
    "load_campaign",
    "run_campaign",
    "run_case",
    "write_campaign",
]
