from __future__ import annotations

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

