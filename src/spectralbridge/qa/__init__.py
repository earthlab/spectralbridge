"""Stage-level and cross-stage scientific quality assurance.

The legacy :mod:`spectralbridge.qa_plots` renderer remains supported.  This
package adds deterministic machine-readable stage reports, explicit status
classification, reusable diagnostics, and combined report assembly.
"""

from .metrics import (
    chunk_invariance_metrics,
    linear_diagnostic,
    reflectance_summary,
    residual_metrics,
    seam_score,
    spectral_response_support,
)
from .brightness import brightness_correction_metrics
from .network import (
    cycle_consistency_metrics,
    grouped_residual_metrics,
    path_consistency_metrics,
    translation_edge_metrics,
)
from .reporting import assemble_combined_report
from .runner import run_completed_flightline_qa
from .schema import QAStatus, StageQAReport
from .stages import emit_stage_qa
from .thresholds import QAThresholds

__all__ = [
    "QAStatus",
    "QAThresholds",
    "StageQAReport",
    "assemble_combined_report",
    "brightness_correction_metrics",
    "chunk_invariance_metrics",
    "cycle_consistency_metrics",
    "emit_stage_qa",
    "grouped_residual_metrics",
    "linear_diagnostic",
    "reflectance_summary",
    "residual_metrics",
    "run_completed_flightline_qa",
    "path_consistency_metrics",
    "seam_score",
    "spectral_response_support",
    "translation_edge_metrics",
]
