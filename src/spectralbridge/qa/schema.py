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
    """Machine-readable report emitted for one canonical pipeline stage.

    Attributes
    ----------
    stage_id : str
        Canonical processing-stage identifier used for deterministic QA paths and stage-specific diagnostics.
    stage_name : str
        Human-readable canonical processing-stage label.
    mode : str
        Diagnostic coverage level, normally 'standard' or 'deep'; existing artifacts are inspected without rerunning correction.
    status : QAStatus
        Recorded stage-specific outcome or eligibility state; inspect reason/detail and the relevant workflow before interpreting it scientifically.
    inputs : list[dict[str, Any]]
        Paths to the stage input/output artifacts; their availability and provenance are recorded in the QA payload.
    outputs : list[dict[str, Any]]
        Paths to the stage input/output artifacts; their availability and provenance are recorded in the QA payload.
    parameters : dict[str, Any]
        Optional serializable stage configuration recorded for reproducibility; does not modify the stage products.
    sample : dict[str, Any]
        Sampling metadata describing the bounded diagnostic support; not the entire raster population.
    metrics : dict[str, Any]
        Numerical diagnostic results with explicit missing/unavailable values.
    checks : list[QACheck]
        Structured QA checks and statuses evaluated against the configured review thresholds.
    warnings : list[str]
        Human-readable diagnostic warnings requiring interpretation.
    plots : list[str]
        Recorded rendered QA artifact paths/metadata.
    interpretation : list[str]
        Human-readable explanation of the stage diagnostics and their limitations.
    provenance : dict[str, Any]
        Source/configuration/version evidence accompanying this diagnostic report.
    schema_version : str, default=SCHEMA_VERSION
        Serialized payload schema version; preserve it when storing or exchanging this record.
    unavailable_diagnostics : list[dict[str, str]], default=field(default_factory=list)
        Explicit list of checks that could not be evaluated; these must not be treated as passing.
    """

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
        """Serialize this record to its established machine-readable mapping.

        Returns
        -------
        dict[str, Any]
            Mapping of record fields and workflow-derived summary entries in the established serialization schema.
        """

        payload = asdict(self)
        payload["status"] = self.status.value
        for check in payload["checks"]:
            status = check.get("status")
            if isinstance(status, QAStatus):
                check["status"] = status.value
        return payload

    def to_json(self) -> str:
        """Serialize the stage report to JSON.

        Returns
        -------
        str
            JSON representation of the stage report.
        """

        return json.dumps(self.to_dict(), indent=2, sort_keys=True, allow_nan=False)

    def write_json(self, path: Path) -> Path:
        """Write the stage report JSON to the requested path.

        Parameters
        ----------
        path : Path
            Destination JSON file path.

        Returns
        -------
        Path
            Destination path after writing this report as JSON.
        """

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
