from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, List, Dict
import json


@dataclass
class HeaderReport:
    """Store legacy ENVI header QA findings and metadata."""

    keys_present: List[str]
    keys_missing: List[str]
    wavelength_unit: Optional[str]
    n_bands: int
    n_wavelengths_finite: int
    first_nm: Optional[float]
    last_nm: Optional[float]
    wavelengths_monotonic: Optional[bool]
    wavelength_source: str  # "header" | "sensor_default" | "absent"


@dataclass
class MaskReport:
    """Store legacy validity-mask QA findings."""

    n_total: int
    n_valid: int
    valid_pct: float


@dataclass
class CorrectionReport:
    """Store legacy correction QA diagnostics."""

    delta_median: List[float]
    delta_iqr: List[float]
    delta_q10: List[float]
    delta_q25: List[float]
    delta_q75: List[float]
    delta_q90: List[float]
    delta_abs_median: List[float]
    largest_delta_indices: List[int]


@dataclass
class ConvolutionReport:
    """Store legacy target-sensor convolution QA diagnostics."""

    sensor: str
    rmse: List[float]
    sam: Optional[float]


@dataclass
class Provenance:
    """Store source and execution metadata accompanying a legacy QA report."""

    flightline_id: str
    created_utc: str
    package_version: str
    git_sha: str
    input_hashes: Dict[str, str]


@dataclass
class QAMetrics:
    """Group legacy header, mask, correction, convolution and provenance QA records."""

    provenance: Provenance
    header: HeaderReport
    mask: MaskReport
    correction: Optional[CorrectionReport]
    convolution: List[ConvolutionReport]
    negatives_pct: float
    overbright_pct: float
    issues: List[str]
    brightness_coefficients: Dict[str, Dict[int, float]] = field(default_factory=dict)
    brightness_summary: Dict[str, List[Dict[str, float]]] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def write_json(metrics: QAMetrics, out_path: Path) -> Path:
    """Serialize legacy QAMetrics to JSON, creating the destination parent directory."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(metrics.to_json())
    return out_path


__all__ = [
    "HeaderReport",
    "MaskReport",
    "CorrectionReport",
    "ConvolutionReport",
    "Provenance",
    "QAMetrics",
    "write_json",
]
