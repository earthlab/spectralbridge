"""Authoritative deterministic paths for stage QA artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_STAGE_ORDER = {
    "acquisition": 0,
    "input_data": 1,
    "correction_parameters": 2,
    "brdf_topographic_correction": 3,
    "spectral_convolution": 4,
    "analysis_tables": 5,
}


def normalize_stage_id(stage_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", stage_id.strip().lower()).strip("_")
    if not normalized:
        raise ValueError("stage_id must contain at least one letter or number")
    return normalized


@dataclass(frozen=True)
class StageQAPaths:
    """Canonical paths for one stage report."""

    flightline_dir: Path
    stage_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "flightline_dir", Path(self.flightline_dir))
        object.__setattr__(self, "stage_id", normalize_stage_id(self.stage_id))

    @property
    def stage_order(self) -> int:
        return _STAGE_ORDER.get(self.stage_id, 90)

    @property
    def directory(self) -> Path:
        return (
            self.flightline_dir
            / "qa"
            / "stages"
            / f"{self.stage_order:02d}_{self.stage_id}"
        )

    @property
    def json(self) -> Path:
        return self.directory / "stage_qa.json"

    @property
    def html(self) -> Path:
        return self.directory / "stage_qa.html"

    @property
    def overview_png(self) -> Path:
        return self.directory / "overview.png"

    @property
    def brightness_png(self) -> Path:
        """Additional before/after diagnostic for brightness-adjusted products."""

        return self.directory / "brightness.png"


@dataclass(frozen=True)
class CombinedQAPaths:
    """Canonical paths for the cross-stage report."""

    flightline_dir: Path

    @property
    def directory(self) -> Path:
        return Path(self.flightline_dir) / "qa" / "combined"

    @property
    def json(self) -> Path:
        return self.directory / "combined_qa.json"

    @property
    def html(self) -> Path:
        return self.directory / "combined_qa.html"

    @property
    def pdf(self) -> Path:
        return self.directory / "combined_qa.pdf"

    @property
    def evolution_png(self) -> Path:
        return self.directory / "pipeline_evolution.png"


__all__ = ["CombinedQAPaths", "StageQAPaths", "normalize_stage_id"]
