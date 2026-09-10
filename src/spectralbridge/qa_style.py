"""Shared presentation conventions for drone and bulk QA.

Machine-readable sensor identifiers remain unchanged.  These helpers are only
for human-facing labels and the drone/bulk plotting palette; the normal NEON
plotting stack intentionally does not import this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


SENSOR_COLORS = {
    "micasense": "#0072B2",
    "tm_etm": "#E69F00",
    "oli_oli2": "#009E73",
    "actual_landsat": "#222222",
    "neon_landsat_like": "#CC79A7",
    "drone_landsat_like": "#56B4E9",
}

WEIGHTING_COLORS = {
    "pixel_pooled": "#0072B2",
    "flightline_balanced": "#E69F00",
    "site_balanced": "#009E73",
}

WEIGHTING_MARKERS = {
    "pixel_pooled": "o",
    "flightline_balanced": "s",
    "site_balanced": "^",
}

STATUS_COLORS = {
    "normal": "#009E73",
    "attention": "#E69F00",
    "failure": "#D55E00",
    "unavailable": "#7A7A7A",
}


@dataclass(frozen=True)
class QAPlotStyle:
    """Typography and export defaults for drone/bulk QA figures."""

    minimum_font_size: float = 9.0
    title_font_size: float = 13.0
    panel_label_font_size: float = 12.0
    figure_dpi: int = 300
    manuscript_width_inches: float = 7.2


DEFAULT_QA_STYLE = QAPlotStyle()


_SENSOR_DISPLAY_LABELS = {
    "MicaSense_to-match_TM_and_ETM+": "MicaSense matched to TM/ETM+",
    "MicaSense_to-match_OLI_and_OLI-2": "MicaSense matched to OLI/OLI-2",
    "Landsat_5_TM": "Landsat 5 TM",
    "Landsat_7_ETM+": "Landsat 7 ETM+",
    "Landsat_8_OLI": "Landsat 8 OLI",
    "Landsat_9_OLI-2": "Landsat 9 OLI-2",
}

_SENSOR_SHORT_LABELS = {
    "MicaSense_to-match_TM_and_ETM+": "MS",
    "MicaSense_to-match_OLI_and_OLI-2": "MS",
    "Landsat_5_TM": "L5 TM",
    "Landsat_7_ETM+": "L7 ETM+",
    "Landsat_8_OLI": "L8 OLI",
    "Landsat_9_OLI-2": "L9 OLI-2",
}


def sensor_display_label(sensor: str, *, short: bool = False) -> str:
    """Return a stable human label without changing the underlying sensor ID."""

    labels = _SENSOR_SHORT_LABELS if short else _SENSOR_DISPLAY_LABELS
    if sensor in labels:
        return labels[sensor]
    return re.sub(r"_+", " ", str(sensor)).strip()


def wavelength_pair_label(row: dict[str, Any], *, include_source_band: bool = False) -> str:
    """Return a compact physical source-to-target band label.

    The separate source and target indices remain visible when requested, and
    wavelength—not equality of sensor-local band numbers—provides the compact
    visual identity.
    """

    source_wavelength = row.get("source_wavelength_nm")
    target_wavelength = row.get("target_wavelength_nm")
    source_band = row.get("source_band_index")
    target_band = row.get("target_band_index")
    source_sensor = sensor_display_label(str(row.get("source_sensor", "source")), short=True)
    target_sensor = sensor_display_label(str(row.get("target_sensor", "target")), short=True)
    if source_wavelength is not None and target_wavelength is not None:
        source = f"{source_sensor}{float(source_wavelength):g}"
        if include_source_band and source_band is not None:
            source = f"{source_sensor} B{int(source_band)} · {float(source_wavelength):g}"
        target = f"{target_sensor} B{int(target_band)} · {float(target_wavelength):g}"
        return f"{source} → {target}"
    return f"{source_sensor} B{source_band} → {target_sensor} B{target_band}"


def apply_qa_axis_style(axis: Any) -> None:
    """Apply the restrained drone/bulk axis treatment."""

    axis.grid(axis="x", color="#DCE3E8", linewidth=0.6, alpha=0.8)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)
    axis.tick_params(labelsize=DEFAULT_QA_STYLE.minimum_font_size)


__all__ = [
    "DEFAULT_QA_STYLE",
    "QAPlotStyle",
    "SENSOR_COLORS",
    "STATUS_COLORS",
    "WEIGHTING_COLORS",
    "WEIGHTING_MARKERS",
    "apply_qa_axis_style",
    "sensor_display_label",
    "wavelength_pair_label",
]
