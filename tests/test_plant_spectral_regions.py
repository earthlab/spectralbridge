"""Source-table site contracts and independent within-region replication."""

import numpy as np
import pandas as pd
import pytest

from spectralbridge.plant_spectral_atlas import _file_hash, run_plant_spectral_atlas
from spectralbridge.plant_spectral_regions import (
    _regional_counts,
    _regional_provenance,
    _site_from_table,
    _verified_products,
    run_regional_plant_atlas,
)


def regional_library(tmp_path):
    rows = []
    for plant, region, flight, n, base in [
        ("A", "NIWO", "001", 9, 2.0),
        ("A", "NIWO", "002", 1, 8.0),
        ("B", "NIWO", "002", 1, 10.0),
        ("C", "WREF", "001", 1, 20.0),
    ]:
        flight_id = (
            f"NEON_D13_{region}_DP1_L{flight}-1_20230815_directional_reflectance"
        )
        for _ in range(n):
            row = {
                "GlobalID": plant,
                "species": "Test species",
                "polygon_id": ord(plant),
                "flight_id": flight_id,
                "source_image": flight_id + ".img",
                "source_parquet": f"/old-archive/wrong_YELL_folder/{flight_id}_polygons_merged_pixel_extraction.parquet",
                "aop_site": region,
                "ecoregion": f"{region} ecoregion",
            }
            for stage, factor in [
                ("raw", 2),
                ("corr", 1),
                ("olioli", 0.5),
                ("micasense", 0.25),
            ]:
                for band, wl in enumerate(
                    [400, 405, 410] if stage in ["raw", "corr"] else [475, 865], 1
                ):
                    row[f"{stage}_b{band:03}_wl{wl:04}nm"] = base * factor
            rows.append(row)
    source = tmp_path / "source.parquet"
    pd.DataFrame(rows).to_parquet(source)
    return source


def test_site_extraction_uses_table_basename():
    assert (
        _site_from_table("/YELL_archive/NEON_D13_NIWO_DP1_L001_test.parquet") == "NIWO"
    )
    assert _site_from_table(r"C:\NIWO\NEON_D16_WREF_DP1_L001_test.parquet") == "WREF"
    with pytest.raises(ValueError, match="Cannot resolve"):
        _site_from_table("/NIWO/archive/unidentified_table.parquet")


def test_provenance_crosschecks_and_independent_plant_counts(tmp_path):
    source = regional_library(tmp_path)
    plants, sources, names = _regional_provenance(source)
    assert len(plants) == 3 and plants.GlobalID.is_unique
    assert sources.groupby("region").pixel_rows.sum().to_dict() == {
        "NIWO": 11,
        "WREF": 1,
    }
    assert names == {"NIWO": "NIWO ecoregion", "WREF": "WREF ecoregion"}
    counts = _regional_counts(plants, 2).set_index("region")
    assert counts.plants.to_dict() == {"NIWO": 2, "WREF": 1}
    assert counts.eligible.to_dict() == {"NIWO": True, "WREF": False}


@pytest.mark.parametrize("field", ["aop_site", "flight_id"])
def test_metadata_site_disagreement_fails(tmp_path, field):
    source = regional_library(tmp_path)
    data = pd.read_parquet(source)
    data.loc[0, field] = (
        "YELL" if field == "aop_site" else "NEON_D12_YELL_DP1_L001_test"
    )
    data.to_parquet(source)
    with pytest.raises(ValueError, match="disagree"):
        _regional_provenance(source)


def test_plant_identity_spanning_regions_fails(tmp_path):
    source = regional_library(tmp_path)
    data = pd.read_parquet(source)
    data.loc[data.GlobalID == "C", "GlobalID"] = "A"
    data.to_parquet(source)
    with pytest.raises(ValueError, match="spans multiple regions"):
        _regional_provenance(source)


def test_region_defaults_do_not_depend_on_optional_site_metadata(tmp_path):
    source = regional_library(tmp_path)
    data = pd.read_parquet(source).drop(columns=["aop_site", "ecoregion"])
    data.to_parquet(source)
    _, _, names = _regional_provenance(source)
    assert names == {"NIWO": "NIWO", "WREF": "WREF"}


def test_regional_figures_reuse_compact_spectra_and_within_site_threshold(tmp_path):
    source = regional_library(tmp_path)
    original = source.read_bytes()
    comparisons = tmp_path / "comparisons"
    for stage in ["raw", "corr", "olioli", "micasense"]:
        run_plant_spectral_atlas(
            source,
            comparisons / "products" / stage,
            spectral_stage=stage,
            make_figures=False,
            grid_step_nm=5 if stage in ["raw", "corr"] else None,
            excluded=((1340, 1450), (1790, 2000)) if stage in ["raw", "corr"] else (),
        )
    out = tmp_path / "regional"
    audit = run_regional_plant_atlas(
        source, comparisons, out, min_plants_per_species=2, dpi=300
    )
    assert audit["matched_labelled_plants"] == 3
    assert audit["spectral_pixel_reads"] == 0
    summary = pd.read_csv(out / "region_summary.csv").set_index("region")
    assert summary.eligible_species.to_dict() == {"NIWO": 1, "WREF": 0}
    medians = pd.read_parquet(out / "regional_corrected_medians.parquet")
    np.testing.assert_allclose(
        medians["median"], 7.5
    )  # across two plants, not ten + one pixels
    assert medians.region.unique().tolist() == ["NIWO"]
    assert (out / "NIWO" / "three_panel_atlas.pdf").is_file()
    assert not (out / "WREF" / "three_panel_atlas.pdf").exists()
    assert (out / "WREF" / "species_sample_sizes.csv").is_file()
    svg = (out / "corrected_by_region_rows.svg").read_text()
    assert "below minimum 2" in svg and "<image" not in svg
    assert source.read_bytes() == original
    manifest = (out / "regional_manifest.json").read_bytes()
    assert (
        run_regional_plant_atlas(
            source, comparisons, out, min_plants_per_species=2, dpi=300
        )
        == audit
    )
    assert (out / "regional_manifest.json").read_bytes() == manifest
    path = comparisons / "products" / "corr" / "plant_harmonized_spectra.parquet"
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Invalid corr compact checkpoint"):
        _verified_products(_file_hash(source), comparisons / "products")


def test_no_within_region_qualifying_species_fails(tmp_path):
    counts = _regional_counts(
        pd.DataFrame(
            {
                "GlobalID": ["A", "B"],
                "species": ["Test species"] * 2,
                "region": ["NIWO", "WREF"],
            }
        ),
        2,
    )
    assert not counts.eligible.any()  # global n=2 cannot override within-site n=1


def test_region_species_order_is_alphabetical_rather_than_sample_size():
    plants = pd.DataFrame(
        {
            "GlobalID": list("ABCDE"),
            "species": ["Zulu species"] * 3 + ["Abies species", "Betula species"],
            "region": ["NIWO"] * 4 + ["WREF"],
        }
    )
    counts = _regional_counts(plants, 1)
    assert list(zip(counts.region, counts.species)) == [
        ("NIWO", "Abies species"),
        ("NIWO", "Zulu species"),
        ("WREF", "Betula species"),
    ]
