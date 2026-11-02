"""Bounded, read-only comparison of three downloaded authoritative TIFF/H5 pairs."""

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import h5py
import numpy as np
import rasterio
from pyproj import Transformer
from affine import Affine
from rasterio.features import rasterize
from rasterio.windows import Window


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--saved-qa", type=Path, required=True)
    parser.add_argument("--polygons", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    qa = json.loads(args.saved_qa.read_text())
    polygons = gpd.read_file(args.polygons).reset_index(drop=True)
    polygons["polygon_id"] = np.arange(1, len(polygons) + 1)
    results = []
    for package in sorted(args.sources.glob("AOP-*-08-14-23-ExportPackage")):
        if not any(n in package.name.lower() for n in ["gordon", "goldhill", "ruby"]):
            continue
        tiff = package / "aligned_orthomosaic.tif"
        h5 = package / "NEON_D13_NIWO_test_aligned_orthomosaic.h5"
        if not (tiff.exists() and h5.exists()):
            continue
        record = next(
            f
            for f in qa["files"]
            if package.name.split("-08-")[0].replace("-", "_").lower()
            == f["flight_stem"].rsplit("_", 1)[0].lower()
        )
        d = record["spatial_diagnostics"]
        old_transform = Affine(*d["raster_transform"])
        print("Comparing", package.name, flush=True)
        with rasterio.open(tiff) as src, h5py.File(h5) as h:
            base = next(iter(h.values()))["Reflectance"]
            ds = base["Reflectance_Data"]
            coord = base["Metadata/Coordinate_System"]
            count = ds.shape[-1]
            ids = list(range(1, count + 1))
            original_polys = polygons.to_crs(src.crs)
            legacy_polys = polygons.to_crs(d["raster_crs"])
            source_shapes = [
                (g, i)
                for g, i in zip(original_polys.geometry, original_polys.polygon_id)
                if g is not None and not g.is_empty
            ]
            legacy_shapes = [
                (g, i)
                for g, i in zip(legacy_polys.geometry, legacy_polys.polygon_id)
                if g is not None and not g.is_empty
            ]
            warp = Transformer.from_crs(d["raster_crs"], src.crs, always_xy=True)
            mismatches = 0
            values = 0
            source_count = 0
            legacy_count = 0
            selected_wrong = 0
            agreement = 0
            source_valid_count = 0
            legacy_valid_count = 0
            source_per = np.zeros(len(polygons) + 1, dtype="int64")
            legacy_per = source_per.copy()
            controls = []
            for start in range(0, src.height, 128):
                stop = min(src.height, start + 128)
                window = Window(0, start, src.width, stop - start)
                a = src.read(ids, window=window)
                b = np.moveaxis(ds[start:stop, :, :], 2, 0)
                mismatches += int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
                values += a.size
                valid = np.isfinite(a).all(axis=0)
                original = rasterize(
                    source_shapes,
                    out_shape=(stop - start, src.width),
                    transform=src.window_transform(window),
                    fill=0,
                    dtype="int32",
                )
                legacy = rasterize(
                    legacy_shapes,
                    out_shape=original.shape,
                    transform=old_transform * Affine.translation(0, start),
                    fill=0,
                    dtype="int32",
                )
                source_count += int((original > 0).sum())
                legacy_count += int((legacy > 0).sum())
                source_valid_count += int(((original > 0) & valid).sum())
                legacy_valid_count += int(((legacy > 0) & valid).sum())
                selected_wrong += int(((legacy > 0) & (legacy != original)).sum())
                agreement += int(((legacy > 0) & (legacy == original)).sum())
                source_per += np.bincount(original.ravel(), minlength=len(source_per))
                legacy_per += np.bincount(legacy.ravel(), minlength=len(legacy_per))
            for row, col in [
                (0, 0),
                (0, src.width - 1),
                (src.height - 1, 0),
                (src.height - 1, src.width - 1),
                (src.height // 2, src.width // 2),
            ]:
                x, y = src.transform * (col + 0.5, row + 0.5)
                xx, yy = old_transform * (col + 0.5, row + 0.5)
                wx, wy = warp.transform(xx, yy)
                controls.append(
                    dict(
                        row=row,
                        col=col,
                        source_x=x,
                        source_y=y,
                        legacy_x=xx,
                        legacy_y=yy,
                        legacy_x_in_source_crs=wx,
                        legacy_y_in_source_crs=wy,
                        displacement_m=float(np.hypot(wx - x, wy - y)),
                        numeric_displacement_source_units=float(
                            np.hypot(xx - x, yy - y)
                        ),
                        source_values=src.read(ids, window=Window(col, row, 1, 1))[
                            :, 0, 0
                        ].tolist(),
                    )
                )

            def safe(value):
                return (
                    None
                    if isinstance(value, float) and not np.isfinite(value)
                    else value
                )

            controls = [
                {
                    k: [safe(v) for v in value]
                    if isinstance(value, list)
                    else safe(value)
                    for k, value in c.items()
                }
                for c in controls
            ]
            results.append(
                dict(
                    flight=record["flight_stem"],
                    source_tiff=str(tiff),
                    source_h5=str(h5),
                    source_tiff_sha256=sha(tiff),
                    source_h5_sha256=sha(h5),
                    dimensions=[src.height, src.width],
                    source_band_count=src.count,
                    h5_band_count=count,
                    explicit_verified_source_bands=ids,
                    unmapped_source_bands=list(range(count + 1, src.count + 1)),
                    source_crs=src.crs.to_string(),
                    h5_crs=coord["Coordinate_System_String"][()].decode(),
                    source_affine=list(src.transform)[:6],
                    source_bounds=list(src.bounds),
                    source_nodata="NaN"
                    if src.nodata is not None and np.isnan(src.nodata)
                    else src.nodata,
                    h5_map_info=coord["Map_Info"][()].decode(),
                    h5_attribute_names=list(ds.attrs),
                    values_compared=values,
                    exact_value_mismatches=mismatches,
                    legacy_recorded_crs=d["raster_crs"],
                    legacy_recorded_affine=d["raster_transform"],
                    control_points=controls,
                    maximum_control_displacement_m=max(
                        c["displacement_m"] for c in controls
                    ),
                    empty_reference_geometries=int(polygons.geometry.is_empty.sum()),
                    source_index_pixels=source_count,
                    legacy_replayed_index_pixels=legacy_count,
                    source_valid_selected_pixels=source_valid_count,
                    legacy_valid_selected_pixels=legacy_valid_count,
                    legacy_selected_wrong_polygon_pixels=selected_wrong,
                    same_pixel_same_polygon=agreement,
                    scientific_scope="Source grid versus replay of saved production affine/CRS; not an actual downloaded historical Parquet. All 10 mapped bands compared exactly, with NaN equality. Eleventh band remains unclassified.",
                    per_polygon=[
                        dict(
                            polygon_id=i,
                            GlobalID=str(polygons.iloc[i - 1]["GlobalID"]),
                            cover_category=str(polygons.iloc[i - 1]["cover_category"]),
                            source_pixels=int(source_per[i]),
                            legacy_pixels=int(legacy_per[i]),
                        )
                        for i in range(1, len(polygons) + 1)
                        if source_per[i] or legacy_per[i]
                    ],
                )
            )
    (args.output / "production_source_comparison.json").write_text(
        json.dumps(results, indent=2, allow_nan=False) + "\n"
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from shapely.geometry import Polygon
    from shapely.ops import transform as map_geometry

    fig, axes = plt.subplots(1, 3, figsize=(15, 6), layout="constrained")
    reference_polygons = polygons.to_crs(26913)
    for ax, result in zip(axes, results):
        height, width = result["dimensions"]
        original = Affine(*result["source_affine"])
        legacy = Affine(*result["legacy_recorded_affine"])
        warp = Transformer.from_crs(
            result["legacy_recorded_crs"], result["source_crs"], always_xy=True
        )
        true_footprint = Polygon(
            [original * p for p in [(0, 0), (width, 0), (width, height), (0, height)]]
        )
        wrong_footprint = map_geometry(
            warp.transform,
            Polygon(
                [legacy * p for p in [(0, 0), (width, 0), (width, height), (0, height)]]
            ),
        )
        extent = np.array([true_footprint.bounds, wrong_footprint.bounds])
        x0, y0 = extent[:, :2].min(axis=0)
        x1, y1 = extent[:, 2:].max(axis=0)
        nearby = reference_polygons.cx[x0 - 20 : x1 + 20, y0 - 20 : y1 + 20]
        if not nearby.empty:
            nearby.boundary.plot(ax=ax, color="black", linewidth=0.5)
        with rasterio.open(result["source_tiff"]) as image:
            stride = max(1, int(np.ceil(max(height, width) / 450)))
            values = np.vstack(
                [
                    image.read(1, window=Window(0, row, width, 1))[0, ::stride]
                    for row in range(0, height, stride)
                ]
            )
            finite = values[np.isfinite(values)]
            vmin, vmax = np.quantile(finite, [0.02, 0.98])
            xx, yy = np.meshgrid(
                np.r_[np.arange(0, width, stride), width],
                np.r_[np.arange(0, height, stride), height],
            )
            ax.pcolormesh(
                original.a * xx + original.c,
                original.e * yy + original.f,
                values,
                cmap="viridis",
                vmin=vmin,
                vmax=vmax,
                rasterized=True,
            )
        for geom, label, color in [
            (true_footprint, "Authoritative TIFF", "#176b2f"),
            (wrong_footprint, "Recorded wrong geometry", "#d34339"),
        ]:
            x, y = geom.exterior.xy
            ax.plot(x, y, label=label, color=color, linewidth=2)
        ax.set_xlim(x0 - 15, x1 + 15)
        ax.set_ylim(y0 - 15, y1 + 15)
        ax.set_aspect("equal")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.ticklabel_format(useOffset=False, style="plain")
        ax.tick_params(labelsize=8)
        ax.set_title(
            result["flight"]
            + f"\nMaximum control displacement {result['maximum_control_displacement_m']:.1f} m"
        )
        ax.set_xlabel("NAD83 / UTM 13N easting (m)")
        ax.set_ylabel("Northing (m)")
    axes[0].legend(fontsize=7, loc="upper left")
    fig.suptitle(
        "Authoritative drone TIFFs versus saved production placement\nBlack: researcher polygons; sampled source band 1 with per-flight display stretch; wrong CRS corners explicitly mapped to EPSG:26913",
        fontsize=12,
    )
    fig.savefig(args.output / "production_verified_footprints.png", dpi=250)
    fig.savefig(args.output / "production_verified_footprints.svg")
    plt.close(fig)
    print(
        [
            (
                r["flight"],
                r["exact_value_mismatches"],
                r["source_index_pixels"],
                r["legacy_replayed_index_pixels"],
                r["same_pixel_same_polygon"],
            )
            for r in results
        ],
        flush=True,
    )


if __name__ == "__main__":
    main()
