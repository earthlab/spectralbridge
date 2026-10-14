"""Pairing, discrete metrics and coupled cluster uncertainty contracts."""

import numpy as np
import pandas as pd
import pytest

from spectralbridge.sensor_pft_transfer import (
    paired_observations,
    validate_sensor_coordinates,
    joint_cluster_multiplicities,
    bootstrap_contrasts,
    project_neon_to_oli,
    OLI_CENTERS,
)


def observation(stage, ids, values):
    return pd.DataFrame(
        {
            "GlobalID": ids,
            "flight_id": ["flight"] * len(ids),
            "source_image": ["image"] * len(ids),
            "polygon_id": range(len(ids)),
            "cover_category": ["Evergreen"] * len(ids),
            stage + "_wl400nm": values,
            stage + "_wl405nm": values,
        }
    )


def test_intersection_before_medians_and_reject_metadata_conflict():
    a = observation("corr", ["a", "b", "c"], [1, 2, 3])
    b = observation("oli", ["a", "b", "c"], [1, np.nan, 3])
    paired = paired_observations({"corr": a, "oli": b})
    assert paired["corr"].GlobalID.tolist() == ["a", "c"]
    assert paired["oli"].GlobalID.tolist() == ["a", "c"]
    b.loc[0, "cover_category"] = "Herbaceous"
    with pytest.raises(ValueError, match="metadata"):
        paired_observations({"corr": a, "oli": b})
    with pytest.raises(ValueError, match="Duplicate"):
        paired_observations({"corr": pd.concat([a, a])})


def test_sensor_coordinate_gates():
    validate_sensor_coordinates(np.round(OLI_CENTERS), "OLI")
    with pytest.raises(ValueError, match="original headers"):
        validate_sensor_coordinates(
            [444, 475, 531, 560, 650, 668, 705, 717, 740, 842], "MicaSense"
        )
    with pytest.raises(ValueError, match="Invalid OLI"):
        validate_sensor_coordinates([443, 482, 561, 655, 865, 841, 842], "OLI")


def test_cluster_weights_couple_repeated_years_and_preserve_cells():
    table = pd.DataFrame(
        [
            {
                "GlobalID": str(i),
                "site": "NIWO",
                "year": year,
                "label": str(i // 3),
                "flight_history": str(year),
            }
            for year in [2020, 2023]
            for i in range(6)
        ]
    )
    m, report = joint_cluster_multiplicities(table, 39, 12)
    np.testing.assert_array_equal(m[:, :6], m[:, 6:])
    np.testing.assert_array_equal(m[:, :3].sum(1), np.repeat(3, 39))
    assert report["clusters"] == 6
    assert report["strata"] == 2
    assert np.any(m != 1)


def test_bootstrap_sufficient_moments_match_expanded_rows_and_gain_invariance():
    y = np.array([[1, 2], [3, 8], [5, 9], [7, 15]], float)
    z = np.array([1, 1, 0, 0])
    blocks = np.zeros(4)
    m = np.array([[1, 1, 1, 1], [2, 0, 0, 2]])
    effect, delta = bootstrap_contrasts(y, z, blocks, m, [1, 1])
    rows = np.repeat(np.arange(4), m[1])
    yy = y[rows]
    zz = z[rows]
    x = zz - zz.mean()
    yc = yy - yy.mean(0)
    expected = (x @ yc / (x @ x)) / np.sqrt((yc * yc).sum(0) / 3)
    np.testing.assert_allclose(delta[1], expected)
    changed, _ = bootstrap_contrasts(y * [0.95, 1.2], z, blocks, m, [1, 1])
    np.testing.assert_allclose(effect, changed)
    with pytest.raises(ValueError, match="counts"):
        bootstrap_contrasts(y, z, blocks, np.array([[3, 0, 0, 1]]), [1, 1])


def test_projection_requires_supported_response_and_keeps_constant_spectrum():
    w = np.arange(385, 2505, 5)
    keep = ~(((w >= 1340) & (w <= 1450)) | ((w >= 1790) & (w <= 2000)))
    y = np.ones((2, len(w)))
    y[:, ~keep] = np.nan
    result, mass = project_neon_to_oli(y, w)
    np.testing.assert_allclose(result, 1)
    assert np.all(mass > 0.99)


def test_end_to_end_paired_inference_and_restart(tmp_path):
    from spectralbridge.sensor_pft_transfer import run_sensor_pft_transfer, OLI_WIDTHS
    from spectralbridge.pft_method_audit import AuditConfig

    flight = "NEON_D13_NIWO_DP1_L001_20230701_directional_reflectance"
    w = np.arange(385, 2510, 5)
    response = np.exp(
        -0.5 * ((w[:, None] - OLI_CENTERS) / (OLI_WIDTHS / 2.354820045)) ** 2
    )
    response /= response.sum(0)
    rows = []
    for category, species, offset in [
        ("Evergreen", "Pinus contorta", 0),
        ("Deciduous", "Populus tremuloides", 1),
    ]:
        for i in range(4):
            values = (1 + np.sin(w / 400) * 0.2) * (1 + offset * 0.4) + i * 0.03
            oli = values @ response
            record = dict(
                GlobalID=f"{category}{i}",
                flight_id=flight,
                source_image=flight,
                source_parquet=flight + "_polygons.parquet",
                polygon_id=i,
                cover_category=category,
                species=species,
                aop_site="NIWO",
            )
            record.update(
                {
                    f"corr_b{j:03}_wl{wave:04}nm": v
                    for j, (wave, v) in enumerate(zip(w, values), 1)
                }
            )
            for stage, gain in [("olioli", 0.95), ("olioli_undarkened", 1.0)]:
                record.update(
                    {
                        f"{stage}_b{j:03}_wl{int(round(wave)):04}nm": v * gain
                        for j, (wave, v) in enumerate(zip(OLI_CENTERS, oli), 1)
                    }
                )
            rows.append(record)
    source = tmp_path / "source.parquet"
    pd.DataFrame(rows).to_parquet(source)
    out = tmp_path / "out"
    result = run_sensor_pft_transfer(
        source, out, config=AuditConfig(permutations=19), bootstraps=19, minimum=2
    )
    assert set(result.scheme) == {"inferred_pft", "researcher_category"}
    assert set(result.common_n) == {8}
    assert result.dark_invariance_error.max() < 1e-10
    mtimes = {p: p.stat().st_mtime_ns for p in out.rglob("*") if p.is_file()}
    again = run_sensor_pft_transfer(
        source, out, config=AuditConfig(permutations=19), bootstraps=19, minimum=2
    )
    np.testing.assert_allclose(result.OLI_effect, again.OLI_effect)
    assert all(p.stat().st_mtime_ns == v for p, v in mtimes.items())
