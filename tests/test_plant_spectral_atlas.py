"""Independent replication and gap-preserving union-schema contracts."""

import json

import numpy as np
import pandas as pd
import pytest

from spectralbridge.plant_spectral_atlas import (
    harmonize_spectrum,
    run_plant_spectral_atlas,
)


def test_interpolation_preserves_missing_and_excluded_gaps():
    w = [1340, 1345, 1350, 1450, 1455, 1460, 1465]
    v = [1, 2, 99, 99, 3, np.nan, 4]
    t = [1340, 1342, 1345, 1350, 1400, 1450, 1455, 1457, 1460, 1463, 1465]
    result = harmonize_spectrum(w, v, t, excluded=((1350, 1450), (1800, 2000)))
    np.testing.assert_allclose(result[:3], [1, 1.4, 2])
    assert np.isnan(result[[3, 4, 5, 7, 8, 9]]).all()
    np.testing.assert_allclose(result[[6, 10]], [3, 4])


def test_no_extrapolation_or_large_gap_interpolation():
    assert np.isnan(harmonize_spectrum([400, 420], [1, 2], [395, 410, 425])).all()
    with pytest.raises(ValueError, match="increasing"):
        harmonize_spectrum([400, 400], [1, 2], [400])


def library(tmp_path):
    rows = []
    # Plant A: median 2 in first flight despite nine pixels, then 8 in second.
    # Equal observation weighting gives 5; a pooled-pixel median would give 2.
    for plant, flight, base, n in [
        ("A", "one", 2.0, 9),
        ("A", "two", 8.0, 1),
        ("B", "two", 10.0, 1),
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
                    row[f"corr_b{band:03}_wl{wavelength + offset:04}nm"] = (
                        base if offset == (flight == "two") else np.nan
                    )
            rows.append(row)
    source = tmp_path / "source.parquet"
    pd.DataFrame(rows).to_parquet(source)
    return source


def test_union_grids_and_equal_independent_plants(tmp_path):
    source = library(tmp_path)
    original = source.read_bytes()
    out = tmp_path / "atlas"
    audit = run_plant_spectral_atlas(
        source, out, min_plants_per_species=1, supplementary=False
    )
    table = pd.read_parquet(out / "plant_harmonized_spectra.parquet").set_index(
        "GlobalID"
    )
    assert len(table) == 2
    assert table.loc["A", "corr_wl405nm"] == 5
    assert table.loc["B", "corr_wl405nm"] == 10
    species = pd.read_parquet(out / "species_median_spectra.parquet")
    assert species.loc[0, "corr_wl405nm"] == 7.5
    manifest = (out / "manifest.json").read_bytes()
    assert (
        run_plant_spectral_atlas(
            source, out, min_plants_per_species=1, supplementary=False
        )
        == audit
    )
    assert (out / "manifest.json").read_bytes() == manifest
    assert audit["native_grids"] == 2
    assert audit["plant_flight_observations"] == 3
    assert audit["merged_finite_fraction"] == 0.5
    assert source.read_bytes() == original
    assert all(
        (out / f"species_atlas.{ext}").is_file() for ext in ["png", "pdf", "svg"]
    )
    grids = pd.read_csv(out / "flight_source_grids.csv")
    assert grids["columns"].map(lambda v: len(json.loads(v))).tolist() == [3, 3]


def test_species_identity_conflicts_fail(tmp_path):
    source = library(tmp_path)
    df = pd.read_parquet(source)
    df.loc[0, "species"] = "Another species"
    df.to_parquet(source)
    with pytest.raises(ValueError, match="Conflicting"):
        run_plant_spectral_atlas(source, tmp_path / "out")


def test_same_source_with_ambiguous_duplicate_wavelength_fails(tmp_path):
    source = library(tmp_path)
    df = pd.read_parquet(source)
    df["corr_b999_wl0400nm"] = 3.0
    df.to_parquet(source)
    with pytest.raises(ValueError, match="Ambiguous"):
        run_plant_spectral_atlas(source, tmp_path / "out")


def test_failed_rerun_preserves_completed_products(tmp_path):
    source = library(tmp_path)
    out = tmp_path / "atlas"
    run_plant_spectral_atlas(source, out, min_plants_per_species=1, supplementary=False)
    manifest = (out / "manifest.json").read_bytes()
    png = (out / "species_atlas.png").read_bytes()
    with pytest.raises(ValueError, match="No taxa"):
        run_plant_spectral_atlas(
            source, out, min_plants_per_species=3, supplementary=False
        )
    assert (out / "manifest.json").read_bytes() == manifest
    assert (out / "species_atlas.png").read_bytes() == png


def test_undeclared_nodata_is_not_a_real_negative_spectrum(tmp_path):
    source = library(tmp_path)
    df = pd.read_parquet(source)
    df.loc[0, "corr_b001_wl0400nm"] = -9999
    df.to_parquet(source)
    with pytest.raises(ValueError, match="nodata sentinel"):
        run_plant_spectral_atlas(source, tmp_path / "out")
