"""Exercise real AOP parameter/correction and drone TIFF/correction entry points."""

import json
from pathlib import Path

import h5py
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from spectralbridge.brdf_topo import (
    build_correction_parameters_dict,
    apply_brdf_topo_core,
)
from spectralbridge.corrections import (
    HYTOOLS_BRDF_KERNEL_CONFIG,
    calc_geom_kernel,
    calc_volume_kernel,
)
from spectralbridge.envi import hdr_to_dict, memmap_bsq
from spectralbridge.neon_cube import NeonCube
from spectralbridge.pipelines.drone import (
    convert_drone_tiff_to_h5,
    export_h5_to_envi,
    apply_drone_corrections,
    DroneCorrectionUnavailableError,
)
from spectralbridge.radiometry import Radiometry, library_radiometry


def scene(tmp_path, name, scale, offset, nadir=False, terrain=False):
    d = tmp_path / name
    d.mkdir()
    y, x = np.mgrid[:12, :14]
    solar_zn = np.full(y.shape, 45.0, np.float32)
    solar_az = np.full(y.shape, 120.0, np.float32)
    view = (
        np.zeros(y.shape, np.float32) if nadir else (x * 2 + y * 0.2).astype(np.float32)
    )
    az = (y * 25 + x * 8).astype(np.float32)
    rad = [np.deg2rad(a) for a in [solar_az, solar_zn, az, view]]
    cfg = HYTOOLS_BRDF_KERNEL_CONFIG
    kv = calc_volume_kernel(*rad, kernel_type=cfg.volume_kernel)
    kg = calc_geom_kernel(*rad, kernel_type=cfg.geom_kernel, b_r=cfg.b_r, h_b=cfg.h_b)
    physical = np.stack([0.3 + 0.02 * kv + 0.01 * kg, 0.5 + 0.03 * kv + 0.015 * kg])
    stored = (physical - offset) / scale
    transform = from_origin(450000, 4430000, 0.1, 0.1)

    def write(path, data):
        if data.ndim == 2:
            data = data[None]
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=14,
            height=12,
            count=len(data),
            dtype="float32",
            transform=transform,
            crs="EPSG:26913",
            nodata=-9999.0,
        ) as dst:
            dst.write(data.astype("float32"))

    source = d / "source.tif"
    write(source, stored)
    for k, a in [
        ("view", view),
        ("az", az),
        (
            "slope",
            (5.0 + 0.3 * x + 0.2 * y).astype(np.float32)
            if terrain
            else np.zeros_like(view),
        ),
        ("aspect", np.zeros_like(view)),
    ]:
        write(d / f"{k}.tif", a)
    h5 = convert_drone_tiff_to_h5(
        source,
        output_h5_path=d / f"{name}.h5",
        wavelengths_nm=[650.0, 860.0],
        fwhm_nm=[10.0, 10.0],
        sensor_zenith_tiff=d / "view.tif",
        sensor_azimuth_tiff=d / "az.tif",
        slope_tiff=d / "slope.tif",
        aspect_tiff=d / "aspect.tif",
        solar_zenith_deg=45.0,
        solar_azimuth_deg=120.0,
        radiometry=Radiometry(
            scale, offset, "VALID", "synthetic independently specified calibration"
        ).record(),
    )
    if name.startswith("NEON_"):
        with h5py.File(h5, "r+") as h:
            ds = next(iter(h.values()))["Reflectance/Reflectance_Data"]
            del ds.attrs["spectralbridge_radiometry"]
            ds.attrs["Scale_Factor"] = 1 / scale
            ds.attrs["Add_Offset"] = offset
    img, hdr = export_h5_to_envi(h5, output_stem=d / "raw")
    return h5, img, hdr, physical


@pytest.mark.parametrize("scale,offset", [(1.0, 0.0), (0.001, -0.05)])
def test_actual_entry_points_equivalent(tmp_path, scale, offset):
    ah, ai, ar, expected = scene(
        tmp_path, "NEON_D13_NIWO_DP1_fixture", 0.0001, 0.0, terrain=True
    )
    dh, di, dr, _ = scene(tmp_path, "drone", scale, offset, terrain=True)
    a_cube, d_cube = NeonCube(ah), NeonCube(dh)
    np.testing.assert_allclose(
        a_cube.radiometry.to_physical(a_cube.data),
        d_cube.radiometry.to_physical(d_cube.data),
        atol=6e-8,
    )
    params = build_correction_parameters_dict(
        h5_path=ah, raw_img_path=ai, raw_hdr_path=ar, base_folder=ah.parent
    )
    ao = ah.parent / "aop_corrected.img"
    apply_brdf_topo_core(
        raw_img_path=ai,
        raw_hdr_path=ar,
        params=params,
        out_img_path=ao,
        out_hdr_path=ao.with_suffix(".hdr"),
    )
    do, do_hdr, audit = apply_drone_corrections(
        cube=d_cube,
        envi_img=di,
        envi_hdr=dr,
        corrected_stem=dh.parent / "drone_corrected",
        apply_topo=True,
        apply_brdf=True,
    )
    assert audit["brdf_status"] == "VALID"
    a_model = json.loads(Path(params["coefficients_path"]).read_text())
    d_model = json.loads(next(dh.parent.glob("*brdf_model.json")).read_text())
    assert a_model["validation"]["status"] == d_model["validation"]["status"] == "VALID"
    assert [r["eligible"] for r in a_model["validation"]["fits"]] == [
        r["eligible"] for r in d_model["validation"]["fits"]
    ]
    for key in ["iso", "vol", "geo", "reference_design"]:
        np.testing.assert_allclose(a_model[key], d_model[key], atol=3e-6)
    for a, d in zip(a_model["validation"]["fits"], d_model["validation"]["fits"]):
        np.testing.assert_allclose(
            a["factor_quantiles"], d["factor_quantiles"], atol=3e-6
        )
    a_values = library_radiometry(ao).to_physical(
        memmap_bsq(ao, hdr_to_dict(ao.with_suffix(".hdr")))
    )
    d_values = library_radiometry(do).to_physical(memmap_bsq(do, hdr_to_dict(do_hdr)))
    np.testing.assert_allclose(a_values, d_values, atol=2e-7)
    with rasterio.open(ao) as a, rasterio.open(do) as d:
        assert a.transform == d.transform
        assert a.crs == d.crs


def test_both_entry_points_reject_goldhill_geometry(tmp_path):
    for name, scale in [("NEON_D13_NIWO_DP1_nadir", 0.0001), ("drone", 1.0)]:
        h, img, hdr, _ = scene(tmp_path, name, scale, 0.0, nadir=True)
        if name.startswith("NEON"):
            params = build_correction_parameters_dict(
                h5_path=h, raw_img_path=img, raw_hdr_path=hdr, base_folder=h.parent
            )
            out = h.parent / "blocked.img"
            with pytest.raises(ValueError, match="UNSUPPORTED"):
                apply_brdf_topo_core(
                    raw_img_path=img,
                    raw_hdr_path=hdr,
                    params=params,
                    out_img_path=out,
                    out_hdr_path=out.with_suffix(".hdr"),
                )
            assert not out.exists()
        else:
            with pytest.raises(DroneCorrectionUnavailableError):
                apply_drone_corrections(
                    cube=NeonCube(h),
                    envi_img=img,
                    envi_hdr=hdr,
                    corrected_stem=h.parent / "topo_only",
                    apply_topo=True,
                    apply_brdf=True,
                )
            assert (
                hdr_to_dict(h.parent / "topo_only.hdr")["brdf status"] == "UNSUPPORTED"
            )
            with pytest.raises(ValueError, match="UNSUPPORTED"):
                library_radiometry(h.parent / "topo_only.img")


def test_extraction_and_bulk_apply_affine_once(tmp_path):
    from types import SimpleNamespace
    from spectralbridge.parquet_export import (
        read_envi_in_chunks,
        build_parquet_from_envi,
    )
    from spectralbridge.radiometry import require_physical_table
    from spectralbridge.bulk.registry import TranslationPair
    from spectralbridge.bulk.streaming import iter_aligned_pair_chunks

    h, img, hdr, expected = scene(tmp_path, "drone", 0.001, -0.05)
    frames = list(read_envi_in_chunks(img, hdr, "native.parquet", chunk_size=35))
    import pandas as pd

    frame = pd.concat(frames).sort_values("pixel_id")
    cols = [c for c in frame if "_wl" in c]
    assert len(cols) == 2
    np.testing.assert_allclose(
        frame[cols].to_numpy(), expected.reshape(2, -1).T, atol=2e-7
    )
    out = tmp_path / "physical.parquet"
    build_parquet_from_envi(img, hdr, out, chunk_size=35)
    require_physical_table(out)
    pair = TranslationPair(
        key="equivalent",
        source_sensor="a",
        target_sensor="b",
        matching_group="same",
        band_pairs=((1, 1),),
    )
    flight = SimpleNamespace(
        target_products_json=json.dumps(
            {"a": {"image": str(img)}, "b": {"image": str(img)}}
        ),
        analysis_eligibility_json=json.dumps({"equivalent": True}),
        canonical_flightline_id="synthetic",
    )
    chunks = list(
        iter_aligned_pair_chunks(flight, [pair], chunk_size=5, minimum_reflectance=0.0)
    )
    arrays = [list(v.values())[0] for _, v in chunks]
    ids = np.concatenate([v[0] for v in arrays])
    values = np.concatenate([v[1] for v in arrays])
    np.testing.assert_allclose(
        values[np.argsort(ids)], expected[0].reshape(-1), atol=2e-7
    )


def test_legacy_cached_model_is_not_reused_or_overwritten(tmp_path):
    from spectralbridge.corrections import fit_and_save_brdf_model

    h, _, _, _ = scene(tmp_path, "drone", 1.0, 0.0)
    old = tmp_path / "old"
    old.mkdir()
    model = old / "old_brdf_model.json"
    model.write_text('{"iso": [[1, 1]]}')
    before = model.read_bytes()
    with pytest.raises(ValueError, match="cached model"):
        fit_and_save_brdf_model(NeonCube(h), old)
    assert model.read_bytes() == before


def test_interrupted_raster_cannot_appear_brdf_valid(tmp_path, monkeypatch):
    from spectralbridge.envi_writer import EnviWriter

    h, img, hdr, _ = scene(tmp_path, "drone", 1.0, 0.0)

    def interrupted(*args, **kwargs):
        raise OSError("simulated write interruption")

    monkeypatch.setattr(EnviWriter, "write_chunk", interrupted)
    output = tmp_path / "interrupted"
    with pytest.raises(OSError, match="interruption"):
        apply_drone_corrections(
            cube=NeonCube(h),
            envi_img=img,
            envi_hdr=hdr,
            corrected_stem=output,
            apply_topo=True,
            apply_brdf=True,
        )
    assert hdr_to_dict(output.with_suffix(".hdr"))["brdf status"] == "INCOMPLETE"
    with pytest.raises(ValueError, match="INCOMPLETE"):
        library_radiometry(output.with_suffix(".img"))


def test_nodata_only_band_is_preserved_without_a_claimed_fit(tmp_path):
    h, img, hdr, _ = scene(tmp_path, "drone", 0.001, -0.05)
    with h5py.File(h, "r+") as f:
        data = next(iter(f.values()))["Reflectance/Reflectance_Data"]
        data[:, :, 1] = -9999.0
    # Re-export reflects the deliberately changed synthetic source.
    img, hdr = export_h5_to_envi(h, output_stem=h.parent / "nodata_raw")
    cube = NeonCube(h)
    out, out_hdr, audit = apply_drone_corrections(
        cube=cube,
        envi_img=img,
        envi_hdr=hdr,
        corrected_stem=h.parent / "corrected",
        apply_topo=True,
        apply_brdf=True,
    )
    model = json.loads(next(h.parent.glob("*brdf_model.json")).read_text())
    assert model["validation"]["status"] == "VALID"
    assert model["validation"]["fits"][1]["status"] == "NOT_APPLICABLE"
    assert model["iso"][0][1] is None
    values = memmap_bsq(out, hdr_to_dict(out_hdr))
    np.testing.assert_array_equal(values[1], -9999.0)
    assert np.isfinite(values[0]).all()
    assert audit["brdf_applied"]
