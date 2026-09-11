from __future__ import annotations

from pathlib import Path

from matplotlib.image import imread

import spectralbridge.drone_qa as drone_qa
from spectralbridge.drone_qa import DRONE_TRANSLATION_PUBLICATION_PANEL_COUNT
from spectralbridge.qa_style import (
    DEFAULT_QA_STYLE,
    WEIGHTING_COLORS,
    sensor_display_label,
    wavelength_pair_label,
)


def test_display_labels_preserve_machine_ids_and_physical_band_identity() -> None:
    sensor_id = "MicaSense_to-match_OLI_and_OLI-2"
    assert sensor_display_label(sensor_id) == "MicaSense matched to OLI/OLI-2"
    assert sensor_display_label(sensor_id, short=True) == "MS"
    label = wavelength_pair_label(
        {
            "source_sensor": sensor_id,
            "target_sensor": "Landsat_8_OLI",
            "source_band_index": 2,
            "target_band_index": 2,
            "source_wavelength_nm": 475.0,
            "target_wavelength_nm": 482.0,
        }
    )
    assert label == "MS475 → L8 OLI B2 · 482"
    assert "B1" not in label


def test_drone_bulk_plot_style_has_accessible_stable_categories() -> None:
    assert set(WEIGHTING_COLORS) == {
        "pixel_pooled",
        "flightline_balanced",
        "site_balanced",
    }
    assert len(set(WEIGHTING_COLORS.values())) == 3
    assert DEFAULT_QA_STYLE.minimum_font_size >= 9
    assert DEFAULT_QA_STYLE.figure_dpi >= 300


def test_drone_publication_figure_has_three_readable_named_panels(
    tmp_path: Path, monkeypatch
) -> None:
    captured = {}
    original_subplots = drone_qa.plt.subplots
    original_close = drone_qa.plt.close

    def capture_subplots(*args, **kwargs):
        figure, axes = original_subplots(*args, **kwargs)
        captured["figure"] = figure
        captured["axes"] = axes
        return figure, axes

    monkeypatch.setattr(drone_qa.plt, "subplots", capture_subplots)
    monkeypatch.setattr(drone_qa.plt, "close", lambda _figure: None)
    outputs = drone_qa.render_drone_translation_publication(
        {
            "translation_provenance": {"target_sensor": "Landsat_8_OLI"},
            "bands": [
                {
                    "source_wavelength_nm": 475.0,
                    "target_wavelength_nm": 482.0,
                    "target_band_index": 2,
                    "source_median": 0.20,
                    "translated_median": 0.19,
                    "median_relative_shift_percent": -5.0,
                    "slope": 0.95,
                    "r2_bulk": 0.99,
                }
            ],
        },
        output_stem=tmp_path / "translation_quality",
    )

    assert DRONE_TRANSLATION_PUBLICATION_PANEL_COUNT == 3
    assert [axis.get_title(loc="left") for axis in captured["axes"]] == [
        "Band medians",
        "Median translation shift",
        "Coefficient and range",
    ]
    assert all(
        panel in {text.get_text() for text in axis.texts}
        for panel, axis in zip("ABC", captured["axes"], strict=True)
    )
    height, width = imread(outputs["png"]).shape[:2]
    assert width >= 1_800
    assert height >= 700
    assert Path(outputs["pdf"]).read_bytes().startswith(b"%PDF")
    original_close(captured["figure"])
