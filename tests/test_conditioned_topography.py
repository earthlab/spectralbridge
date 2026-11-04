"""Synthetic physical tests of opt-in resolved SCS+C and spatial BRDF controls."""

import json
from types import SimpleNamespace
import numpy as np
import pytest

from spectralbridge import corrections as c
from spectralbridge.topographic import (
    SCSCPolicy,
    fit_conditioned_scs_c,
    apply_conditioned_scs_c,
    fieller_interval,
    cluster_covariance,
    CORRECTED,
    UNSUPPORTED,
)
from spectralbridge.radiometry import Radiometry, require_library_header


def cube(scale=1, offset=0):
    y, x = np.mgrid[:20, :24]
    g = dict(
        slope=np.deg2rad(8 + x * 1.5),
        aspect=y / 20 * 2 * np.pi,
        solar_zn=np.full(x.shape, 0.6),
        solar_az=np.full(x.shape, 1.2),
        sensor_zn=0.03 + x * 0.025 + y * 0.007,
        sensor_az=x * 0.24 + y * 0.09,
    )
    ci = c.calc_cosine_i(g["solar_zn"], g["solar_az"], g["aspect"], g["slope"])
    physical = np.stack([0.15 * ci + 0.07, 0.4 * ci + 0.1], axis=-1).astype("float32")
    obj = SimpleNamespace(
        data=((physical - offset) / scale).astype("float32"),
        lines=20,
        columns=24,
        bands=2,
        no_data=np.nan,
        wavelengths=np.array([650.0, 862.0]),
        mask_no_data=np.ones(x.shape, bool),
        source_valid_mask=np.ones(x.shape, bool),
        radiometry=Radiometry(
            scale, offset, "VALID", "independent synthetic physical control"
        ),
    )
    obj.get_ancillary = lambda name, radians=True: (
        g[name] if radians else np.rad2deg(g[name])
    )
    return obj, g, (y // 5) * 10 + x // 6


def test_exact_scsc_recovery_scale_offset_and_chunk_equivalence():
    a, g, groups = cube()
    b, _, _ = cube(0.0001, 0.005)
    ma = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    mb = fit_conditioned_scs_c(b, policy=SCSCPolicy(), uncertainty_groups=groups)
    np.testing.assert_allclose(
        [r["C"] for r in ma["fits"]], [0.07 / 0.15, 0.1 / 0.4], rtol=1e-6
    )
    np.testing.assert_allclose(
        [r["C"] for r in ma["fits"]], [r["C"] for r in mb["fits"]], rtol=1e-6
    )
    qa = apply_conditioned_scs_c(a, a.data, 0, 20, 0, 24, model=ma)
    qb = apply_conditioned_scs_c(b, b.data, 0, 20, 0, 24, model=mb)
    np.testing.assert_allclose(
        qa.values,
        b.radiometry.to_physical(qb.values),
        rtol=1e-6,
        atol=1e-7,
        equal_nan=True,
    )
    parts = np.concatenate(
        [
            apply_conditioned_scs_c(
                a, a.data[y : y + 5], y, y + 5, 0, 24, model=ma
            ).values
            for y in range(0, 20, 5)
        ]
    )
    np.testing.assert_array_equal(parts, qa.values)
    supported = qa.status[..., 0] == CORRECTED
    expected = 0.15 * np.cos(g["solar_zn"]) * np.cos(g["slope"]) + 0.07
    np.testing.assert_allclose(
        qa.values[..., 0][supported], expected[supported], rtol=1e-6
    )


def test_no_identity_on_unresolved_or_backfacing_geometry():
    a, g, groups = cube()
    m = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    # A broad supported C interval excludes a denominator that crosses its pole.
    m["fits"][0].update(C=-0.3, C_interval=[-0.7, 0.1], fitted_incidence_range=[0, 1])
    result = apply_conditioned_scs_c(a, a.data, 0, 20, 0, 24, model=m)
    ci = c.calc_cosine_i(g["solar_zn"], g["solar_az"], g["aspect"], g["slope"])
    rejected = ci < 0.7
    assert np.isnan(result.values[..., 0][rejected]).all()
    assert (result.status[..., 0][rejected] == UNSUPPORTED).all()


def test_unbounded_fieller_and_degenerate_groups_are_unsupported():
    assert fieller_interval(0.001, 0.2, np.eye(2), 1.96) is None
    a, g, groups = cube()
    m = fit_conditioned_scs_c(
        a, policy=SCSCPolicy(), uncertainty_groups=np.zeros(groups.shape, int)
    )
    assert m["validation_status"] == "UNSUPPORTED"
    out = apply_conditioned_scs_c(a, a.data, 0, 20, 0, 24, model=m)
    assert np.isnan(out.values).all() and (out.status == UNSUPPORTED).all()


def test_source_alpha_and_band_nodata_preserved():
    a, g, groups = cube()
    a.source_valid_mask[0, 0] = False
    a.data[0, 0] = 65535
    a.data[1, 1, 0] = np.nan
    m = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    out = apply_conditioned_scs_c(a, a.data, 0, 20, 0, 24, model=m)
    assert (out.status[0, 0] == 0).all() and np.isnan(out.values[0, 0]).all()
    assert out.status[1, 1, 0] == 0 and out.status[1, 1, 1] == CORRECTED


def test_topographic_models_bind_units_wavelengths_and_policy():
    a, g, groups = cube()
    m = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    m["wavelengths_nm"] = [444, 862]
    with pytest.raises(ValueError, match="wavelength"):
        apply_conditioned_scs_c(a, a.data, 0, 20, 0, 24, model=m)


def test_cluster_covariance_uses_groups_not_pixel_count():
    rng = np.random.default_rng(42)
    X = np.c_[np.tile(np.linspace(0.2, 1, 20), 8), np.ones(160)]
    groups = np.repeat(np.arange(8), 20)
    residual = np.repeat(rng.normal(0, 0.1, 8), 20)
    cov, n = cluster_covariance(X, residual, groups)
    assert n == 8 and cov[1, 1] > 0.0001


def test_brdf_training_mask_does_not_fit_heldout_values(tmp_path):
    a, g, groups = cube()
    config = c.HYTOOLS_BRDF_KERNEL_CONFIG
    X, _, _ = c._brdf_design(a, config)
    signal = X @ np.array([0.4, 0.03, 0.02])
    a.data = np.repeat(signal[..., None], 2, axis=-1).astype("float32")
    mask = np.indices(a.data.shape[:2])[1] < 12
    a.data[~mask] = 1.5
    path = c.fit_and_save_brdf_model(
        a,
        tmp_path,
        brdf_kernel_config=config,
        fitting_mask=mask,
        fitting_provenance={"strategy": "spatial training-only fixture"},
    )
    m = json.loads(path.read_text())
    assert m["validation"]["status"] == "VALID"
    assert all(r["eligible"] == 240 for r in m["validation"]["fits"])
    np.testing.assert_allclose(
        [m[k][0][0] for k in ["iso", "vol", "geo"]], [0.4, 0.03, 0.02], rtol=1e-5
    )
    with pytest.raises(ValueError, match="stale"):
        c.fit_and_save_brdf_model(
            a, tmp_path, brdf_kernel_config=config, fitting_mask=~mask
        )


def test_new_sampling_and_topography_do_not_accept_hypothetical_radiometry(tmp_path):
    a, g, groups = cube()
    a.radiometry = Radiometry(
        1, 0, "HYPOTHETICAL_UNVERIFIED", "synthetic unverified source"
    )
    with pytest.raises(ValueError, match="HYPOTHETICAL_UNVERIFIED"):
        fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    p = c.fit_and_save_brdf_model(a, tmp_path, fitting_mask=np.ones(groups.shape, bool))
    assert json.loads(p.read_text())["validation"]["status"] == "UNSUPPORTED"


def test_experimental_headers_never_enter_approved_library():
    with pytest.raises(ValueError, match="Experimental"):
        require_library_header({"scientific validation status": "EXPERIMENTAL"})


def test_actual_drone_writer_retains_experimental_acceptance_status(tmp_path):
    from spectralbridge.pipelines.drone import apply_drone_corrections
    from spectralbridge.envi_writer import EnviWriter
    from spectralbridge.envi import hdr_to_dict

    a, g, groups = cube()
    a.scale_factor = 1
    a.projection_wkt = "EPSG:26913"
    a.transform = (0, 1, 0, 20, 0, -1)
    header = dict(
        samples=24,
        lines=20,
        bands=2,
        interleave="bsq",
        **{
            "data type": 4,
            "byte order": 0,
            "wavelength": [650, 862],
            "fwhm": [10, 10],
            "wavelength units": "Nanometers",
            "projection": "EPSG:26913",
            "data ignore value": np.nan,
            "map info": ["UTM", 1, 1, 0, 20, 1, 1, 13, "North"],
            "brdf status": "NOT_REQUESTED",
        },
        **a.radiometry.header(),
    )
    a.build_envi_header = lambda: dict(header)
    a.chunk_count = lambda **kwargs: 1

    def chunks(chunk_y=128, chunk_x=None):
        for y in range(0, 20, chunk_y):
            yield y, min(y + chunk_y, 20), 0, 24, a.data[y : y + chunk_y]

    a.iter_chunks = chunks
    stem = tmp_path / "raw"
    writer = EnviWriter(stem, header)
    writer.write_chunk(a.data, 0, 0)
    writer.close()
    model = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    img, hdr, audit = apply_drone_corrections(
        cube=a,
        envi_img=stem.with_suffix(".img"),
        envi_hdr=stem.with_suffix(".hdr"),
        corrected_stem=tmp_path / "corrected",
        apply_topo=True,
        apply_brdf=False,
        topographic_model=model,
    )
    saved = hdr_to_dict(hdr)
    assert saved["scientific validation status"] == "EXPERIMENTAL"
    assert saved["topographic validation policy"] == "scsc-fieller-spatial-v1"
    assert audit["topo_applied"] and not audit["topo_fallback_due_to_nodata"]
    with pytest.raises(ValueError, match="Experimental"):
        require_library_header(saved)


def test_resolved_large_gain_is_retained_without_clipping():
    a, g, groups = cube()
    g["slope"][0, 0] = np.arccos(0.002) - 0.6
    g["aspect"][0, 0] = 1.2 + np.pi
    ci = c.calc_cosine_i(g["solar_zn"], g["solar_az"], g["aspect"], g["slope"])
    a.data[..., 0] = (0.15 * ci).astype("float32")
    model = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    result = apply_conditioned_scs_c(a, a.data, 0, 20, 0, 24, model=model)
    assert result.status[0, 0, 0] == CORRECTED
    assert result.factors[0, 0, 0] > 100
    np.testing.assert_allclose(
        result.values[0, 0, 0], 0.15 * np.cos(0.6) * np.cos(g["slope"][0, 0]), rtol=1e-4
    )


def test_per_band_affine_radiometry_is_decoded_once():
    a, g, groups = cube()
    physical = a.data.copy()
    scale = np.array([0.0001, 0.0002])
    offset = np.array([0.003, -0.007])
    a.data = ((physical - offset) / scale).astype("float32")
    a.radiometry = Radiometry(
        scale, offset, "VALID", "independent per-band synthetic calibration"
    )
    model = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    np.testing.assert_allclose(
        [r["C"] for r in model["fits"]], [0.07 / 0.15, 0.1 / 0.4], rtol=1e-5
    )
    result = apply_conditioned_scs_c(a, a.data, 0, 20, 0, 24, model=model)
    decoded = a.radiometry.to_physical(result.values)
    assert np.isfinite(decoded[result.status == CORRECTED]).all()


@pytest.mark.parametrize("fault", ["schema", "band_order", "interval", "window"])
def test_conditioned_application_rejects_corrupt_contracts(fault):
    a, _, groups = cube()
    model = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    chunk = a.data
    if fault == "schema":
        model["schema_version"] = 2
    elif fault == "band_order":
        model["fits"] = model["fits"][::-1]
    elif fault == "interval":
        model["fits"][0]["C_interval"] = [1.0, -1.0]
    else:
        chunk = chunk[:-1]
    with pytest.raises(ValueError):
        apply_conditioned_scs_c(a, chunk, 0, 20, 0, 24, model=model)


def test_conditioned_group_provenance_is_canonical_and_sensitive():
    a, _, groups = cube()
    first = fit_conditioned_scs_c(a, policy=SCSCPolicy(), uncertainty_groups=groups)
    same = fit_conditioned_scs_c(
        a, policy=SCSCPolicy(), uncertainty_groups=groups.astype(np.int32)
    )
    changed = fit_conditioned_scs_c(
        a, policy=SCSCPolicy(), uncertainty_groups=groups + 1
    )
    assert first["uncertainty_groups_sha256"] == same["uncertainty_groups_sha256"]
    assert first["uncertainty_groups_sha256"] != changed["uncertainty_groups_sha256"]
