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
    """Provisional standard-mode thresholds expressed as fractions.

    Attributes
    ----------
    valid_fraction_warn : float, default=0.9
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    valid_fraction_fail : float, default=0.7
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    negative_fraction_warn : float, default=0.01
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    negative_fraction_fail : float, default=0.05
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    overbright_fraction_warn : float, default=0.01
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    overbright_fraction_fail : float, default=0.05
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    correction_abs_q99_warn : float, default=0.2
        Review threshold for the 99th percentile of absolute reflectance correction, in the diagnostic reflectance units.
    correction_abs_q99_fail : float, default=0.5
        Review threshold for the 99th percentile of absolute reflectance correction, in the diagnostic reflectance units.
    seam_score_warn : float, default=1.5
        Dimensionless seam/interior gradient-ratio review threshold; landscape structure can also exceed it.
    seam_score_fail : float, default=2.5
        Dimensionless seam/interior gradient-ratio review threshold; landscape structure can also exceed it.
    chunk_difference_tolerance : float, default=1e-06
        Absolute same-unit tolerance for chunk-invariance comparisons.
    srf_coverage_warn : float, default=0.98
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    srf_coverage_fail : float, default=0.9
        Fractional support/range review threshold in [0, 1]; warn/fail interpretation follows the corresponding metric, not a universal scientific validity rule.
    provisional : bool, default=True
        Whether these configured review bounds are explicitly provisional rather than empirically calibrated acceptance criteria.
    """

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
        """Serialize this record to its established machine-readable mapping.

        Returns
        -------
        dict[str, float | bool]
            Mapping of record fields and workflow-derived summary entries in the established serialization schema.
        """

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
    """Classify a metric against inclusive upper warn/fail bounds; None yields NOT EVALUATED."""

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
    """Classify a metric against inclusive lower warn/fail bounds; None yields NOT EVALUATED."""

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
