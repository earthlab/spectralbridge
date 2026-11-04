"""Read-only full-band native statistics and explicit grid/encoding comparisons."""

import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TEMP = Path("/private/tmp/p168-goldhill-sources")
BASE = "/iplant/home/shared/earthlab/macrosystems/field-data/"
PACKAGE = "AOP-GOLDHILL-08-14-23-ExportPackage/"
WAVES = [444, 475, 531, 560, 650, 668, 705, 717, 740, 862]
CANDIDATES = {
    "original": (
        Path("/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif"),
        BASE + "uas-packages/" + PACKAGE + "AOP-GOLDHILL-08-14-23_ORTHO.tif",
    ),
    "upstream_uint16_25cm": (
        TEMP / "upstream_aligned/aligned_orthomosaic.tif",
        BASE + "To_Correct/macrosystems/" + PACKAGE + "aligned_orthomosaic.tif",
    ),
    "root_float_25cm": (
        TEMP / "root_aligned/aligned_orthomosaic.tif",
        BASE + "output/" + PACKAGE + "aligned_orthomosaic.tif",
    ),
    "summer_float_25cm": (
        Path("/private/tmp/spectralbridge-scale-confirmation/base/goldhill.tif"),
        BASE + "output/summer-2023/" + PACKAGE + "aligned_orthomosaic.tif",
    ),
    "normalized_25cm": (
        Path("/private/tmp/spectralbridge-scale-confirmation/rescale/goldhill.tif"),
        BASE + "output/summer-2023-rescale/" + PACKAGE + "aligned_orthomosaic.tif",
    ),
    "normalized_10cm": (
        TEMP / "ten_cm/aligned_orthomosaic.tif",
        BASE + "output/summer-2023-10cm-10k/" + PACKAGE + "aligned_orthomosaic.tif",
    ),
    "georef_rgb_10cm": (
        TEMP / "georef_rgb/goldhill_aop_underflight_georef_to_rgb.tif",
        BASE
        + "output/summer-2023_aop_underflight_georef_to_rgb/goldhill_aop_underflight_georef_to_rgb.tif",
    ),
    "new_fixed_10cm": (TEMP / "derived_10cm_10k/goldhill_10cm_fixed_10k.tif", None),
}


def sha(path):
    d = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024**2), b""):
            d.update(block)
    return d.hexdigest()


def valid(a, nodata):
    m = np.isfinite(a)
    if nodata is not None:
        m &= a != nodata
    return m


def pairs(x, y, m):
    x = x[m].astype(float)
    y = y[m].astype(float)
    xm = x.mean()
    ym = y.mean()
    dx = x - xm
    dy = y - ym
    slope = float(dx @ dy / (dx @ dx))
    offset = float(ym - slope * xm)
    error = y - (slope * x + offset)
    delta = y - x
    nonzero = x != 0
    ratio = y[nonzero] / x[nonzero]
    return dict(
        valid_pairs=int(x.size),
        slope=slope,
        offset=offset,
        r_squared=float(1 - error @ error / (dy @ dy)),
        rmse=float(np.sqrt(error @ error / x.size)),
        max_abs_residual=float(abs(error).max()),
        difference_mean=float(delta.mean()),
        difference_quantiles=np.quantile(delta, [0, 0.01, 0.5, 0.99, 1]).tolist(),
        ratio_quantiles_nonzero_source=np.quantile(
            ratio, [0, 0.01, 0.5, 0.99, 1]
        ).tolist(),
        ratio_excluded_zero_source=int((~nonzero).sum()),
        rmse_if_y_equals_x_times_10000=float(np.sqrt(np.mean((y - x * 10000) ** 2))),
    )


def main():
    protected = {str(p): sha(p) for p, _ in CANDIDATES.values()}
    for rel in [
        "src/spectralbridge/pipelines/drone.py",
        "src/spectralbridge/corrections.py",
        "src/spectralbridge/radiometry.py",
        "src/spectralbridge/neon_cube.py",
    ]:
        p = ROOT / rel
        protected[str(p)] = sha(p)
    inventory = {}
    display = {}
    for name, (path, remote) in CANDIDATES.items():
        with rasterio.open(path) as src:
            nodata = src.nodata
            alpha = [i for i, c in enumerate(src.colorinterp, 1) if c.name == "alpha"]
            mask = src.read(alpha[0]) > 0 if alpha else None
            metadata = dict(
                path=str(path),
                remote_origin=remote,
                bytes=path.stat().st_size,
                sha256=protected[str(path)],
                format=src.driver,
                shape=[src.height, src.width],
                total_bands=src.count,
                spectral_bands=10,
                extra_band_status="Declared alpha"
                if alpha
                else "Band 11 follows original auxiliary lineage, but alpha interpretation lost"
                if src.count == 11
                else "None",
                dtype=src.dtypes[0],
                crs=str(src.crs),
                transform=list(src.transform),
                resolution=list(src.res),
                bounds=list(src.bounds),
                nodata="NaN"
                if nodata is not None and not np.isfinite(nodata)
                else nodata,
                scales=list(src.scales),
                offsets=list(src.offsets),
                units=list(src.units),
                descriptions=list(src.descriptions),
                colorinterp=[c.name for c in src.colorinterp],
                tags={
                    ns or "default": src.tags(ns=ns)
                    for ns in [None, *src.tag_namespaces()]
                },
                band_tags=[src.tags(i) for i in range(1, src.count + 1)],
                mask_flags=[[f.name for f in flags] for flags in src.mask_flag_enums],
                declared_positive_alpha_pixels=int(mask.sum())
                if mask is not None
                else None,
                physical_calibration="UNVERIFIED; identity TIFF scales are not a calibration certificate",
            )
            stats = []
            for band in range(1, 11):
                a = src.read(band)
                v = valid(a, nodata)
                x = a[v]
                observed = v & (src.read_masks(band) > 0)
                if mask is not None:
                    observed &= mask
                ox = a[observed]
                stats.append(
                    dict(
                        band=band,
                        wavelength_nm=WAVES[band - 1],
                        finite_non_nodata=int(v.sum()),
                        nodata_pixels=int((~v).sum()),
                        minimum=float(x.min()),
                        maximum=float(x.max()),
                        mean=float(x.mean(dtype=float)),
                        quantiles=np.quantile(
                            x, [0, 0.01, 0.25, 0.5, 0.75, 0.99, 1]
                        ).tolist(),
                        valid_mask_pixels=int(observed.sum()),
                        observed_quantiles=np.quantile(
                            ox, [0, 0.01, 0.5, 0.99, 1]
                        ).tolist(),
                        exact_zero_count=int((x == 0).sum()),
                        exact_10000_count=int((x == 10000).sum()),
                        exact_65535_count=int((x == 65535).sum()),
                        saturation_status="No independent flag; endpoint counts are not proof of saturation/clipping",
                    )
                )
            metadata["bands"] = stats
            inventory[name] = metadata
            # Compact representative displays; same physical coordinates available in metadata.
            step = max(1, src.width // 750)
            rgb = src.read([5, 4, 2])[:, ::step, ::step].transpose(1, 2, 0)
            vm = valid(rgb, nodata).all(axis=-1)
            if mask is not None:
                vm &= mask[::step, ::step]
            else:
                vm &= src.read_masks(1)[::step, ::step] > 0
            rgb[~vm] = np.nan if rgb.dtype.kind == "f" else 0
            display[name + "_rgb"] = rgb
            display[name + "_mask"] = vm
            print("Inventoried", name, flush=True)
    # Same-grid comparisons distinguish rounding, encoding and metadata changes.
    comparisons = {}
    for label, left, right in [
        ("root_vs_summer", "root_float_25cm", "summer_float_25cm"),
        ("uint16_vs_float_25cm", "root_float_25cm", "upstream_uint16_25cm"),
        ("25cm_normalization", "summer_float_25cm", "normalized_25cm"),
        ("old_vs_new_10cm", "normalized_10cm", "new_fixed_10cm"),
    ]:
        out = []
        with (
            rasterio.open(CANDIDATES[left][0]) as a,
            rasterio.open(CANDIDATES[right][0]) as b,
        ):
            assert a.shape == b.shape and a.transform == b.transform and a.crs == b.crs
            for band in range(1, 11):
                x = a.read(band)
                y = b.read(band)
                va = valid(x, a.nodata)
                vb = valid(y, b.nodata)
                m = va & vb & (a.read_masks(band) > 0) & (b.read_masks(band) > 0)
                row = dict(
                    band=band,
                    wavelength_nm=WAVES[band - 1],
                    **pairs(x, y, m),
                    nodata_agreement_pixels=int((va == vb).sum()),
                    total_pixels=int(x.size),
                    only_left_valid=int((va & ~vb).sum()),
                    only_right_valid=int((vb & ~va).sum()),
                )
                if label == "25cm_normalization":
                    lo = inventory["original"]["bands"][band - 1]["minimum"]
                    hi = inventory["original"]["bands"][band - 1]["maximum"]
                    e = y[m].astype(float) - (x[m].astype(float) - lo) * 10000 / (
                        hi - lo
                    )
                    row.update(
                        expected_multiplier=10000 / (hi - lo),
                        expected_offset=-lo * 10000 / (hi - lo),
                        max_abs_error_vs_expected=float(abs(e).max()),
                    )
                if label == "uint16_vs_float_25cm":
                    row["fraction_matching_float_rounded_to_nearest_integer"] = float(
                        np.mean(y[m] == np.rint(x[m]))
                    )
                if label == "25cm_normalization":
                    display[f"pair25_b{band}"] = np.array(
                        [
                            x[m][:: max(1, int(m.sum()) // 4000)],
                            y[m][:: max(1, int(m.sum()) // 4000)],
                        ]
                    )
                out.append(row)
            comparisons[label] = dict(
                left=left, right=right, grid="IDENTICAL", bands=out
            )
    # Cross-grid hypothesis test: original native samples warped to each destination.
    for target in ["summer_float_25cm", "normalized_10cm", "georef_rgb_10cm"]:
        records = []
        with (
            rasterio.open(CANDIDATES["original"][0]) as src,
            rasterio.open(CANDIDATES[target][0]) as dst,
        ):
            for band in range(1, 11):
                data = src.read(band).astype(np.float32)
                warped = np.full(dst.shape, np.nan, np.float32)
                reproject(
                    data,
                    warped,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst.transform,
                    dst_crs=dst.crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.bilinear,
                )
                y = dst.read(band)
                m = np.isfinite(warped) & valid(y, dst.nodata)
                rec = dict(
                    band=band, wavelength_nm=WAVES[band - 1], **pairs(warped, y, m)
                )
                if target != "summer_float_25cm":
                    lo = inventory["original"]["bands"][band - 1]["minimum"]
                    hi = inventory["original"]["bands"][band - 1]["maximum"]
                    e = y[m].astype(float) - (warped[m].astype(float) - lo) * 10000 / (
                        hi - lo
                    )
                    rec.update(
                        rmse_vs_original_minmax_mapping=float(np.sqrt(e @ e / len(e))),
                        max_abs_error_vs_original_minmax_mapping=float(abs(e).max()),
                    )
                records.append(rec)
                print("Compared original ->", target, "band", band, flush=True)
            comparisons["original_to_" + target] = dict(
                grid="DIFFERENT: bilinear GDAL reprojection to exact destination grid",
                method_limit="Independent interpolation hypothesis, not exact replay of unavailable historical exporter. Original alpha not applied in this historical-lineage comparison; validity handled separately for new derivative.",
                bands=records,
            )
    # Native pixel spectra at fixed map coordinates, nearest center per source, not exact co-located footprint equivalence.
    spectra = {}
    coords = [(457750.0, 4432750.0), (457800.0, 4432700.0), (457850.0, 4432780.0)]
    for name, (path, _) in CANDIDATES.items():
        with rasterio.open(path) as src:
            samples = []
            for x, y in coords:
                row, col = src.index(x, y)
                v = (
                    src.read(
                        list(range(1, 11)),
                        window=rasterio.windows.Window(col, row, 1, 1),
                    )
                    .reshape(10)
                    .astype(float)
                )
                samples.append(
                    dict(easting=x, northing=y, row=row, column=col, values=v.tolist())
                )
            spectra[name] = samples
    np.savez_compressed(HERE / "display_arrays.npz", **display)
    # Restored working H5 is an actual 10-band input, distinct from the archived converter source.
    h5path = Path("/private/tmp/assumed-viewing-angles-20261103/goldhill_working.h5")
    with h5py.File(h5path, "r") as h:
        ds = h["AOP-GOLDHILL-08-14-23-ExportPackage/Reflectance/Reflectance_Data"]
        attrs = {k: np.asarray(v).tolist() for k, v in ds.attrs.items()}
        h5 = dict(
            path=str(h5path),
            bytes=h5path.stat().st_size,
            sha256=sha(h5path),
            shape=list(ds.shape),
            dtype=str(ds.dtype),
            attrs=attrs,
        )
        with rasterio.open(CANDIDATES["normalized_10cm"][0]) as src:
            exact = True
            for y in range(0, src.height, 128):
                tif = src.read(
                    list(range(1, 11)),
                    window=rasterio.windows.Window(
                        0, y, src.width, min(128, src.height - y)
                    ),
                ).transpose(1, 2, 0)
                stored = ds[y : y + 128]
                good = np.isfinite(tif)
                exact &= bool(
                    np.array_equal(tif[good], stored[good])
                    and np.all(~np.isfinite(stored[~good]) | (stored[~good] == -9999))
                )
            h5["ten_cm_tiff_to_working_h5_exact_finite_values_and_missingness"] = exact
            assert exact
    after = {path: sha(Path(path)) for path in protected}
    assert after == protected
    result = dict(
        candidate_inventory=inventory,
        comparisons=comparisons,
        representative_spectra=spectra,
        wavelengths_nm=WAVES,
        working_h5=h5,
        protected_hashes=protected,
        protected_files_unchanged=True,
        source_read_only=True,
        production_pipeline_changed=False,
        quantile_method="Exact NumPy quantiles of all finite non-NoData values; explicit alpha/mask subset separately recorded",
        normalization_status="Numeric mapping verified; physical calibration and exact historical export code unresolved",
    )

    def json_safe(value):
        if isinstance(value, dict):
            return {k: json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [json_safe(v) for v in value]
        if isinstance(value, float) and not np.isfinite(value):
            return None
        return value

    result = json_safe(result)
    result["json_nonfinite_policy"] = (
        "Nonfinite metadata/sample values stored as null; original source metadata retained unchanged"
    )
    (HERE / "results.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )
    print("All protected source and production-code hashes unchanged", flush=True)


if __name__ == "__main__":
    main()
