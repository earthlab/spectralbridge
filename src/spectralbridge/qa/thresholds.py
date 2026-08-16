"""Configurable QA thresholds.

Defaults are intentionally conservative and provisional until they are tuned
against a pinned set of real NEON, MicaSense, and Landsat comparison data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .schema import QACheck, QAStatus


# These ranges mirror the long-standing HyTools configuration retained under
# ``spectralbridge.deprecated.hytools``. Stage QA uses them only to label and
# stratify diagnostics; it never masks or changes the underlying data.
KNOWN_BAD_WAVELENGTH_RANGES_NM: tuple[dict[str, float | str], ...] = (
    {
        "minimum_nm": 300.0,
        "maximum_nm": 400.0,
        "reason": "spectral edge / low-signal region",
    },
    {
        "minimum_nm": 1337.0,
        "maximum_nm": 1430.0,
        "reason": "strong atmospheric water-absorption region",
    },
    {
        "minimum_nm": 1800.0,
        "maximum_nm": 1960.0,
        "reason": "strong atmospheric water-absorption region",
    },
    {
        "minimum_nm": 2450.0,
        "maximum_nm": 2600.0,
        "reason": "spectral edge / low-signal region",
    },
)


@dataclass(frozen=True)
class QAThresholds:
    """Provisional standard-mode thresholds expressed as fractions."""

    valid_fraction_warn: float = 0.90
    valid_fraction_fail: float = 0.70
    negative_fraction_warn: float = 0.01
    negative_fraction_fail: float = 0.05
    overbright_fraction_warn: float = 0.01
    overbright_fraction_fail: float = 0.05
    correction_abs_q99_warn: float = 0.20
    correction_abs_q99_fail: float = 0.50
    seam_score_warn: float = 1.50
    seam_score_fail: float = 2.50
    chunk_difference_tolerance: float = 1e-6
    srf_coverage_warn: float = 0.98
    srf_coverage_fail: float = 0.90
    provisional: bool = True

    def to_dict(self) -> dict[str, float | bool]:
        return asdict(self)


def classify_high_bad(
    check_id: str,
    value: float | None,
    *,
    warn: float,
    fail: float,
    units: str | None = None,
    interpretation: str,
    provisional: bool = True,
    reason: str | None = None,
) -> QACheck:
    if value is None:
        return QACheck(
            check_id=check_id,
            status=QAStatus.NOT_EVALUATED,
            units=units,
            warn_threshold=warn,
            fail_threshold=fail,
            provisional=provisional,
            interpretation=interpretation,
            reason=reason or "Metric could not be computed.",
        )
    status = (
        QAStatus.FAIL
        if value >= fail
        else QAStatus.WARN
        if value >= warn
        else QAStatus.PASS
    )
    return QACheck(
        check_id=check_id,
        status=status,
        value=float(value),
        units=units,
        warn_threshold=float(warn),
        fail_threshold=float(fail),
        provisional=provisional,
        interpretation=interpretation,
    )


def classify_low_bad(
    check_id: str,
    value: float | None,
    *,
    warn: float,
    fail: float,
    units: str | None = None,
    interpretation: str,
    provisional: bool = True,
    reason: str | None = None,
) -> QACheck:
    if value is None:
        return QACheck(
            check_id=check_id,
            status=QAStatus.NOT_EVALUATED,
            units=units,
            warn_threshold=warn,
            fail_threshold=fail,
            provisional=provisional,
            interpretation=interpretation,
            reason=reason or "Metric could not be computed.",
        )
    status = (
        QAStatus.FAIL
        if value <= fail
        else QAStatus.WARN
        if value <= warn
        else QAStatus.PASS
    )
    return QACheck(
        check_id=check_id,
        status=status,
        value=float(value),
        units=units,
        warn_threshold=float(warn),
        fail_threshold=float(fail),
        provisional=provisional,
        interpretation=interpretation,
    )


__all__ = [
    "KNOWN_BAD_WAVELENGTH_RANGES_NM",
    "QAThresholds",
    "classify_high_bad",
    "classify_low_bad",
]
