"""Versioned schemas for stage and combined QA artifacts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.3"


class QAStatus(str, Enum):
    """Four-state QA classification used throughout SpectralBridge."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT EVALUATED"


@dataclass(frozen=True)
class QACheck:
    """One explicit check, including thresholds and interpretation."""

    check_id: str
    status: QAStatus
    value: Any = None
    units: str | None = None
    warn_threshold: Any = None
    fail_threshold: Any = None
    provisional: bool = True
    interpretation: str = ""
    reason: str | None = None


@dataclass
class StageQAReport:
    """Machine-readable report emitted for one canonical pipeline stage."""

    stage_id: str
    stage_name: str
    mode: str
    status: QAStatus
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    parameters: dict[str, Any]
    sample: dict[str, Any]
    metrics: dict[str, Any]
    checks: list[QACheck]
    warnings: list[str]
    plots: list[str]
    interpretation: list[str]
    provenance: dict[str, Any]
    schema_version: str = SCHEMA_VERSION
    unavailable_diagnostics: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        for check in payload["checks"]:
            status = check.get("status")
            if isinstance(status, QAStatus):
                check["status"] = status.value
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, allow_nan=False)

    def write_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json() + "\n", encoding="utf-8")
        return path


def overall_status(checks: list[QACheck]) -> QAStatus:
    """Return the most severe evaluated status, or ``NOT EVALUATED``."""

    statuses = {check.status for check in checks}
    if QAStatus.FAIL in statuses:
        return QAStatus.FAIL
    if QAStatus.WARN in statuses:
        return QAStatus.WARN
    if QAStatus.PASS in statuses:
        return QAStatus.PASS
    return QAStatus.NOT_EVALUATED


__all__ = [
    "QACheck",
    "QAStatus",
    "SCHEMA_VERSION",
    "StageQAReport",
    "overall_status",
]
