"""Matched cohorts, stage isolation and discrete derived-band plotting."""

import numpy as np
import pandas as pd
import pytest

from spectralbridge.plant_spectral_atlas import run_plant_spectral_atlas
from spectralbridge.plant_spectral_comparison import (
    _draw_product,
    _matched_products,
    run_plant_comparison_atlas,
)


def source_library(tmp_path):
    rows = []
    for plant, flight, n, base in [
        ("A", "one", 9, 2.0),
        ("A", "two", 1, 8.0),
        ("B", "two", 1, 10.0),
    ]:
        for _ in range(n):
            row = {
                "GlobalID": plant,
                "flight_id": flight,
                "source_image": flight,
                "polygon_id": 1 if plant == "A" else 2,
                "species": "Test species",
            }
            for band, wavelength in enumerate([400, 405, 410], 1):
                for offset in [0, 1]:
                    for stage, factor in [("corr", 1), ("raw", 2)]:
                        row[f"{stage}_b{band:03}_wl{wavelength + offset:04}nm"] = (
                            base * factor if offset == (flight == "two") else np.nan
                        )
            for stage, factor in [("olioli", 0.5), ("micasense", 0.25)]:
                for band, wavelength in enumerate([475, 865], 1):
                    row[f"{stage}_b{band:03}_wl{wavelength:04}nm"] = base * factor
            rows.append(row)
    source = tmp_path / "source.parquet"
    pd.DataFrame(rows).to_parquet(source)
    return source


def test_raw_stage_isolation_and_discrete_native_bands(tmp_path):
    source = source_library(tmp_path)
    raw = tmp_path / "raw"
    audit = run_plant_spectral_atlas(
        source, raw, spectral_stage="raw", make_figures=False
    )
    table = pd.read_parquet(raw / "plant_harmonized_spectra.parquet").set_index(
        "GlobalID"
    )
    assert table.loc["A", "raw_wl405nm"] == 10
    assert audit["native_grids"] == 2
    assert not any(c.startswith("corr_wl") for c in table)
    broad = tmp_path / "broad"
    run_plant_spectral_atlas(
        source,
        broad,
        spectral_stage="olioli",
        grid_step_nm=None,
        excluded=(),
        make_figures=False,
    )
    table = pd.read_parquet(broad / "plant_harmonized_spectra.parquet").set_index(
        "GlobalID"
    )
    assert [c for c in table if c.startswith("olioli_wl")] == [
        "olioli_wl475nm",
        "olioli_wl865nm",
    ]
    assert table.loc["A", "olioli_wl475nm"] == 2.5


@pytest.mark.parametrize("stage, style", [("olioli", "-"), ("micasense", "--")])
def test_sensor_traces_retain_exact_band_samples_and_missing_breaks(stage, style):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    diagnostic = []
    wavelengths = np.array([475.0, 717.0, 865.0])
    values = np.array([[-1.0, np.nan, 2.0], [3.0, 5.0, 4.0]])
    _draw_product(
        ax, stage, wavelengths, values, excluded=(), band_diagnostics=diagnostic
    )
    traces = [line for line in ax.lines if line.get_linestyle() == style]
    assert (
        len(traces) == 3
    )  # exactly one trace per plant plus the plant-balanced median
    for line, expected in zip(traces, [values[0], values[1], [1.0, 5.0, 3.0]]):
        np.testing.assert_array_equal(line.get_xdata(), wavelengths)
        np.testing.assert_allclose(line.get_ydata(), expected, equal_nan=True)
        assert line.get_marker() == "None"
    assert [d["median"] for d in diagnostic] == [1.0, 5.0, 3.0]
    assert [d["plants"] for d in diagnostic] == [2, 1, 2]
    plt.close(fig)


def test_all_comparison_layouts_and_plant_medians(tmp_path):
    source = source_library(tmp_path)
    before = source.read_bytes()
    out = tmp_path / "comparison"
    audit = run_plant_comparison_atlas(source, out, min_plants_per_species=1, dpi=300)
    assert audit["matched_labelled_plants"] == audit["main_plants"] == 2
    assert audit["main_species_count"] == 1
    medians = pd.read_parquet(out / "plotted_species_medians.parquet")
    expected = {"raw": 15.0, "corr": 7.5, "olioli": 3.75, "micasense": 1.875}
    for stage, value in expected.items():
        np.testing.assert_allclose(medians.loc[medians.stage == stage, "median"], value)
    for name in audit["layouts"] + audit["standalone_atlases"]:
        for extension in ["pdf", "png", "svg"]:
            assert (out / f"{name}.{extension}").is_file()
        assert "<image" not in (out / f"{name}.svg").read_text()
    assert source.read_bytes() == before
    manifest = (out / "comparison_manifest.json").read_bytes()
    assert (
        run_plant_comparison_atlas(source, out, min_plants_per_species=1, dpi=300)
        == audit
    )
    assert (out / "comparison_manifest.json").read_bytes() == manifest
    # Join by GlobalID despite different stored order, and match only retained plants.
    p = out / "products" / "micasense" / "plant_harmonized_spectra.parquet"
    table = pd.read_parquet(p).iloc[::-1]
    table.loc[table.GlobalID == "A", "retained"] = False
    table.to_parquet(p)
    plants, _, labels, sample = _matched_products(out / "products", 1)
    assert plants.GlobalID.tolist() == ["B"]
    assert labels == ["Test species"]
    assert sample.loc[0, "plants"] == 1


def test_cross_product_species_conflict_fails(tmp_path):
    root = tmp_path / "products"
    for stage in ["raw", "corr", "olioli", "micasense"]:
        (root / stage).mkdir(parents=True)
        pd.DataFrame(
            {
                "GlobalID": ["A"],
                "species": ["Wrong species" if stage == "raw" else "Test species"],
                "retained": [True],
                "flight_observations": [1],
                "pixel_count": [1],
                f"{stage}_wl475nm": [1.0],
                f"{stage}_wl865nm": [2.0],
            }
        ).to_parquet(root / stage / "plant_harmonized_spectra.parquet")
    with pytest.raises(ValueError, match="Species conflict"):
        _matched_products(root, 1)


def test_sensor_products_reject_continuous_grid_defaults(tmp_path):
    source = source_library(tmp_path)
    with pytest.raises(ValueError, match="Discrete sensor products"):
        run_plant_spectral_atlas(source, tmp_path / "out", spectral_stage="olioli")


def test_alphabetical_species_have_one_aligned_row_in_every_layout(tmp_path):
    import re
    import xml.etree.ElementTree as ET

    source = source_library(tmp_path)
    data = pd.read_parquet(source)
    extra = data.iloc[[-1]].copy()
    extra["GlobalID"] = "C"
    extra["polygon_id"] = 3
    extra["species"] = "Abies testii"  # fewer plants, but alphabetically first
    pd.concat([data, extra], ignore_index=True).to_parquet(source)
    out = tmp_path / "alphabetical"
    audit = run_plant_comparison_atlas(source, out, min_plants_per_species=1, dpi=300)
    labels = ["Abies testii", "Test species"]
    assert audit["species"] == labels
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    for name in audit["layouts"] + audit["standalone_atlases"]:
        tree = ET.parse(out / f"{name}.svg")
        texts = list(tree.findall(".//svg:text", namespace))
        nodes = []
        for label in labels:
            matches = [t for t in texts if "".join(t.itertext()).strip() == label]
            assert len(matches) == 1  # no repeated species across separate atlas blocks
            nodes.append(matches[0])

        def text_y(node):
            if node.get("y") is not None:
                return float(node.get("y"))
            return float(
                re.search(r"translate\([^ ]+ ([^)]+)\)", node.get("transform"))[1]
            )

        assert text_y(nodes[0]) < text_y(nodes[1])
        rectangles = tree.findall(".//svg:clipPath/svg:rect", namespace)
        assert len({r.get("y") for r in rectangles}) == len(labels)
        expected_columns = 1 if name in audit["standalone_atlases"] else 3
        assert len({r.get("x") for r in rectangles}) == expected_columns
    for extension in ["pdf", "svg", "png"]:
        assert (out / f"three_panel_atlas.{extension}").read_bytes() == (
            out / f"raw_corrected_darkened_rows.{extension}"
        ).read_bytes()


def test_legacy_micasense_padding_is_flagged_without_remapping():
    from spectralbridge.plant_spectral_comparison import _micasense_labels_unverified

    padded = np.array([475, 560, 668, 717, 840, 841, 842, 843, 844, 845.0])
    original = padded.copy()
    assert _micasense_labels_unverified(padded)
    assert not _micasense_labels_unverified(
        [444, 475, 531, 560, 650, 668, 705, 717, 740, 842]
    )
    assert not _micasense_labels_unverified([475, 560, 668, 717, 840])
    np.testing.assert_array_equal(padded, original)
