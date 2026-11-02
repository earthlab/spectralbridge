#!/usr/bin/env python3
"""Read-only, bounded-memory spatial audit. Never flips or repairs an input.

Supply the original TIFF, available stages and original researcher polygons.
H5 is evaluated both as encoded ENVI map info and as the package reader sees it.
Missing stages remain explicitly missing. Coordinates are pixel centers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import h5py
import numpy as np
import rasterio
from affine import Affine
from pyproj import CRS, Transformer
from rasterio.windows import Window
from shapely.geometry import Polygon


def text(value):
    return value.decode() if isinstance(value, bytes) else str(value)


def controls(height, width):
    return [
        (0, 0),
        (0, width - 1),
        (height - 1, 0),
        (height - 1, width - 1),
        (height // 2, width // 2),
    ]


def footprint(transform, height, width):
    return Polygon(
        [transform * p for p in [(0, 0), (width, 0), (width, height), (0, height)]]
    )


def inspect_stage(path, kind, band):
    """Sample one band, scan NoData by bounded rows, retain exact control values."""
    path = Path(path)
    result = {
        "path": str(path.resolve()),
        "kind": kind,
        "size_bytes": path.stat().st_size,
        "mtime_ns": path.stat().st_mtime_ns,
    }
    if kind == "h5":
        handle = h5py.File(path, "r")
        matches = []
        handle.visititems(
            lambda n, o: (
                matches.append(n)
                if isinstance(o, h5py.Dataset) and n.endswith("Reflectance_Data")
                else None
            )
        )
        if len(matches) != 1:
            handle.close()
            raise ValueError("Expected one unambiguous H5 Reflectance_Data dataset")
        ds = handle[matches[0]]
        if ds.ndim != 3:
            raise ValueError("Expected H5 (rows, columns, bands) contract")
        height, width, bands = ds.shape
        coord = ds.parent["Metadata/Coordinate_System"]
        raw = coord["Map_Info"][()]
        parts = (
            [text(v).strip() for v in raw]
            if isinstance(raw, np.ndarray)
            else text(raw).strip("{}").split(",")
        )
        rx, ry, x, y, dx, dy = [float(v) for v in parts[1:7]]
        # GDAL's ENVI corner convention, independently of package helpers.
        encoded = Affine(dx, 0, x - (rx - 1) * dx, 0, -dy, y + (ry - 1) * dy)
        corner = coord.attrs.get("spatial_reference_convention") == "envi_corner_v1"
        ref = 1 if corner else 0.5
        transform = Affine(
            dx, 0, x - (rx - ref) * dx, 0, -abs(dy), y + (ry - ref) * abs(dy)
        )
        crs = CRS.from_user_input(text(coord["Coordinate_System_String"][()]))
        nodata = next(
            (
                float(ds.attrs[k])
                for k in ["Data_Ignore_Value", "_FillValue", "NoData", "no_data"]
                if k in ds.attrs
            ),
            None,
        )

        def read(r0, r1, c0, c1):
            return np.asarray(ds[r0:r1, c0:c1, band - 1])

        result.update(
            map_info=[str(v) for v in parts],
            encoded_envi_transform=list(encoded)[:6],
            spatial_reference_convention="envi_corner_v1"
            if corner
            else "legacy_center",
            encoded_orientation_conflict=bool(dy <= 0),
        )
    else:
        handle = rasterio.open(path)
        height, width, bands = handle.height, handle.width, handle.count
        transform, nodata = handle.transform, handle.nodata
        crs = CRS.from_user_input(handle.crs) if handle.crs else None

        def read(r0, r1, c0, c1):
            return handle.read(band, window=Window(c0, r0, c1 - c0, r1 - r0))

    try:
        if not 1 <= band <= bands:
            raise ValueError(f"Band {band} not available in {path}")
        step = max(1, int(np.ceil(max(height, width) / 400)))
        thumb = np.empty((len(range(0, height, step)), len(range(0, width, step))))
        # Read thumbnail in bounded row windows even for H5.
        invalid = 0
        mask_hash = hashlib.sha256()
        for row in range(0, height, 128):
            end = min(height, row + 128)
            values = read(row, end, 0, width)
            mask = ~np.isfinite(values)
            if nodata is not None:
                mask |= values == nodata
            invalid += int(mask.sum())
            mask_hash.update(mask.tobytes())
        for i, row in enumerate(range(0, height, step)):
            values = read(row, row + 1, 0, width)[0, ::step].astype(float)
            if nodata is not None:
                values[values == nodata] = np.nan
            thumb[i] = values
        cp = []
        for row, col in controls(height, width):
            x, y = transform * (col + 0.5, row + 0.5)
            value = float(read(row, row + 1, col, col + 1)[0, 0])
            cp.append(
                dict(
                    row=row,
                    col=col,
                    x=x,
                    y=y,
                    value=value if np.isfinite(value) else None,
                )
            )
        result.update(
            height=height,
            width=width,
            bands=bands,
            crs=crs.to_wkt() if crs else None,
            epsg=crs.to_epsg() if crs else None,
            affine=list(transform)[:6],
            bounds=list(footprint(transform, height, width).bounds),
            resolution=[
                float(np.hypot(transform.a, transform.d)),
                float(np.hypot(transform.b, transform.e)),
            ],
            orientation="north-up" if transform.e < 0 else "south-up",
            nodata="NaN" if nodata is not None and np.isnan(nodata) else nodata,
            invalid_band_pixels=invalid,
            mask_sha256=mask_hash.hexdigest(),
            control_points=cp,
            thumbnail_stride=step,
        )
        return result, thumb
    finally:
        handle.close()


def compare_controls(reference, stage):
    if reference["crs"] is None or stage["crs"] is None:
        return {"status": "missing_crs"}
    if (reference["height"], reference["width"]) != (stage["height"], stage["width"]):
        return {"status": "different_dimensions_no_assumed_correspondence"}
    warp = Transformer.from_crs(stage["crs"], reference["crs"], always_xy=True)
    ref_transform = Affine(*reference["affine"])
    inv = ~ref_transform
    rows = []
    for a, b in zip(reference["control_points"], stage["control_points"]):
        x, y = warp.transform(b["x"], b["y"])
        dc, dr = inv * (x, y)
        rows.append(
            {
                "row": a["row"],
                "col": a["col"],
                "dx": x - a["x"],
                "dy": y - a["y"],
                "displacement": float(np.hypot(x - a["x"], y - a["y"])),
                "displacement_pixels": float(
                    np.hypot(dc - a["col"] - 0.5, dr - a["row"] - 0.5)
                ),
                "reference_value": a["value"],
                "stage_value": b["value"],
            }
        )
    distances = [r["displacement"] for r in rows]
    return {
        "status": "five_control_points_only",
        "coordinate_units": CRS(reference["crs"]).axis_info[0].unit_name,
        "explicit_coordinate_conversion": not CRS(reference["crs"]).equals(
            CRS(stage["crs"])
        ),
        "maximum": max(distances),
        "mean": float(np.mean(distances)),
        "median": float(np.median(distances)),
        "maximum_pixels": max(r["displacement_pixels"] for r in rows),
        "controls": rows,
        "bounds_delta": (np.array(stage["bounds"]) - reference["bounds"]).tolist()
        if CRS(reference["crs"]).equals(CRS(stage["crs"]))
        else None,
    }


def compare_lossless_pixels(source, stage, chunk_rows=128, source_bands=None):
    """Exact all-band TIFF versus H5/native ENVI comparison, no full-scene load."""
    with rasterio.open(source) as src:
        if stage["kind"] == "h5":
            handle = h5py.File(stage["path"], "r")
            matches = []
            handle.visititems(
                lambda n, o: (
                    matches.append(n)
                    if isinstance(o, h5py.Dataset) and n.endswith("Reflectance_Data")
                    else None
                )
            )
            ds = handle[matches[0]]

            def read(start, stop):
                return np.moveaxis(ds[start:stop, :, :], 2, 0)
        else:
            handle = rasterio.open(stage["path"])

            def read(start, stop):
                return handle.read(window=Window(0, start, src.width, stop - start))

        try:
            bands = (
                list(source_bands) if source_bands is not None else list(src.indexes)
            )
            if (src.height, src.width, len(bands)) != (
                stage["height"],
                stage["width"],
                stage["bands"],
            ):
                return {"status": "different_dimensions"}
            mismatch = 0
            total = 0
            for start in range(0, src.height, chunk_rows):
                stop = min(src.height, start + chunk_rows)
                a = src.read(
                    indexes=bands, window=Window(0, start, src.width, stop - start)
                ).astype("float32")
                b = read(start, stop)
                mismatch += int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
                total += a.size
            return {
                "status": "exact_float32_comparison",
                "values": total,
                "mismatched_values": mismatch,
            }
        finally:
            handle.close()


def compare_parquet(path, source, polygons, id_column, label_column, value_raster=None):
    """Bounded record scan with source-center membership and source value checks.

    Pixel membership always uses the authoritative TIFF. Spectral values are
    compared only against an explicitly supplied value raster: legacy column
    prefixes can say raw even when the samples came from a corrected product.
    """
    import pyarrow.parquet as pq
    import re
    from collections import OrderedDict, Counter
    from contextlib import ExitStack
    from rasterio.features import rasterize
    import duckdb

    result = dict(
        path=str(Path(path).resolve()),
        records=0,
        coordinate_mismatches=0,
        membership_mismatches=0,
        label_mismatches=0,
        invalid_indices=0,
        raw_value_mismatches=0,
        raw_values_checked=0,
        value_reference_invalid_rows=0,
    )
    with rasterio.open(source) as src, ExitStack() as refs:
        values_src = (
            refs.enter_context(rasterio.open(value_raster)) if value_raster else None
        )
        result["explicit_value_reference"] = str(value_raster) if value_raster else None
        row_cache = OrderedDict()
        index_cache = OrderedDict()
        observed_counts = Counter()
        expected_counts = Counter()
        filtered_counts = Counter()
        if polygons is not None:
            polygons = polygons.to_crs(src.crs)
            if id_column not in polygons or polygons[id_column].duplicated().any():
                raise ValueError("Reference polygons need unique explicit identifiers")
            lookup = polygons.set_index(id_column)
            ids = list(lookup.index)
            shapes = [
                (geom, i + 1)
                for i, geom in enumerate(lookup.geometry)
                if geom is not None and not geom.is_empty
            ]
            # Independent source-grid extraction in bounded windows; retain
            # compact per-polygon counts, never a pixel-scale cache.
            for start in range(0, src.height, 128):
                stop = min(src.height, start + 128)
                window = Window(0, start, src.width, stop - start)
                grid = rasterize(
                    shapes,
                    out_shape=(stop - start, src.width),
                    transform=src.window_transform(window),
                    fill=0,
                    dtype="int32",
                )
                values, counts = np.unique(grid, return_counts=True)
                for code, count in zip(values, counts):
                    if code:
                        expected_counts[str(ids[code - 1])] += int(count)
                if values_src is not None:
                    data = values_src.read(window=window)
                    valid = np.isfinite(data).all(axis=0)
                    if values_src.nodata is not None and np.isfinite(values_src.nodata):
                        valid &= (data != values_src.nodata).all(axis=0)
                    codes, counts = np.unique(grid[valid], return_counts=True)
                    for code, count in zip(codes, counts):
                        if code:
                            filtered_counts[str(ids[code - 1])] += int(count)
        else:
            lookup = None
        for batch_number, batch in enumerate(
            pq.ParquetFile(path).iter_batches(batch_size=4096)
        ):
            if batch_number % 25 == 0:
                print(
                    f"Parquet spatial audit: {result['records']:,} records checked",
                    flush=True,
                )
            frame = batch.to_pandas()
            if not {"row", "col", "x", "y"} <= set(frame):
                return {"status": "missing_row_col_x_y", "path": str(path)}
            for record in frame.to_dict("records"):
                result["records"] += 1
                row, col = int(record["row"]), int(record["col"])
                if not (0 <= row < src.height and 0 <= col < src.width):
                    result["invalid_indices"] += 1
                    continue
                x, y = src.transform * (col + 0.5, row + 0.5)
                result["coordinate_mismatches"] += int(
                    not np.allclose(
                        [x, y], [record["x"], record["y"]], atol=1e-7, rtol=0
                    )
                )
                if lookup is not None and id_column in record:
                    identity = record[id_column]
                    observed_counts[str(identity)] += 1
                    block_start = (row // 128) * 128
                    if block_start not in index_cache:
                        height = min(128, src.height - block_start)
                        window = Window(0, block_start, src.width, height)
                        index_cache[block_start] = rasterize(
                            shapes,
                            out_shape=(height, src.width),
                            transform=src.window_transform(window),
                            fill=0,
                            dtype="int32",
                        )
                        if len(index_cache) > 2:
                            index_cache.popitem(last=False)
                    code = int(index_cache[block_start][row - block_start, col])
                    expected_identity = ids[code - 1] if code else None
                    if expected_identity != identity:
                        result["membership_mismatches"] += 1
                    elif label_column in record and label_column in lookup:
                        result["label_mismatches"] += int(
                            str(record[label_column])
                            != str(lookup.loc[identity, label_column])
                        )
                raw = [
                    (k, int(m.group(1)))
                    for k in record
                    if (m := re.match(r"^raw_b(\d+)_", k))
                ]
                if values_src is not None:
                    if row not in row_cache:
                        row_cache[row] = values_src.read(
                            window=Window(0, row, values_src.width, 1)
                        )[:, 0, :]
                        if len(row_cache) > 4:
                            row_cache.popitem(last=False)
                    values = row_cache[row][:, col]
                    valid_row = np.isfinite(values).all()
                    if values_src.nodata is not None and np.isfinite(values_src.nodata):
                        valid_row = valid_row and not np.any(
                            values == values_src.nodata
                        )
                    result["value_reference_invalid_rows"] += int(not valid_row)
                    for key, band in raw:
                        if 1 <= band <= len(values):
                            result["raw_values_checked"] += 1
                            result["raw_value_mismatches"] += int(
                                not np.isclose(
                                    record[key],
                                    values[band - 1],
                                    atol=0,
                                    rtol=0,
                                    equal_nan=True,
                                )
                            )
    result["expected_source_index_pixels_by_polygon"] = dict(expected_counts)
    result["observed_pixels_by_polygon"] = dict(observed_counts)
    result["source_index_counts_match"] = bool(
        lookup is not None and expected_counts == observed_counts
    )
    # Distinctness plus exact counts and valid membership can establish set
    # equality without storing millions of Python pixel identifiers.
    connection = duckdb.connect()
    try:
        connection.execute("SET memory_limit='256MB'")
        total, unique = connection.execute(
            'SELECT count(*), count(DISTINCT ("row", "col")) FROM read_parquet(?)',
            [str(path)],
        ).fetchone()
        result["duplicate_pixel_records"] = total - unique
    finally:
        connection.close()
    result["complete_index_membership_match"] = bool(
        result["source_index_counts_match"]
        and not result["duplicate_pixel_records"]
        and not result["membership_mismatches"]
        and not result["invalid_indices"]
    )
    result["expected_finite_value_reference_pixels_by_polygon"] = dict(filtered_counts)
    result["complete_retained_membership_match"] = bool(
        values_src is not None
        and filtered_counts == observed_counts
        and not result["duplicate_pixel_records"]
        and not result["membership_mismatches"]
        and not result["invalid_indices"]
        and not result["value_reference_invalid_rows"]
    )
    result["status"] = "source_index_and_record_comparison"
    result["membership_scope"] = (
        "center-based source-grid polygon index, including nodata; filtered spectral tables may legitimately contain fewer rows"
    )
    return result


def run(args):
    import geopandas as gpd
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.ticker import MaxNLocator

    args.output.mkdir(parents=True, exist_ok=True)
    stages, images = {}, {}
    paths = [
        ("source_tiff", "raster"),
        ("h5", "h5"),
        ("native", "raster"),
        ("corrected", "raster"),
        ("final", "raster"),
    ]
    for name, kind in paths:
        path = getattr(args, name)
        if path is not None:
            print(f"Inspecting {name}: {path}", flush=True)
            stages[name], images[name] = inspect_stage(path, kind, args.band)
    reference = stages.get("source_tiff")
    comparisons = (
        {k: compare_controls(reference, v) for k, v in stages.items()}
        if reference
        else {}
    )
    for k in ("h5", "native"):
        if reference and k in stages:
            comparisons[k]["lossless_values"] = compare_lossless_pixels(
                args.source_tiff, stages[k], source_bands=args.source_bands
            )
    polygons = gpd.read_file(args.polygons) if args.polygons else None
    packet = dict(
        stages=stages,
        comparisons=comparisons,
        authoritative_tiff_available=bool(reference),
        missing_stages=[k for k, _ in paths if k not in stages],
        scope="read-only; synthetic only when --synthetic is supplied",
        synthetic=args.synthetic,
        explicit_source_band_selection=args.source_bands,
    )
    if args.parquet and reference:
        packet["parquet"] = compare_parquet(
            args.parquet,
            args.source_tiff,
            polygons,
            args.id_column,
            args.label_column,
            value_raster=args.parquet_value_raster,
        )
    if args.parquet and not reference:
        packet["parquet"] = {"status": "not_evaluated_no_authoritative_tiff"}
    (args.output / "discrepancies.json").write_text(
        json.dumps(packet, indent=2, allow_nan=False) + "\n"
    )
    rows = [
        dict(stage=k, **r)
        for k, v in comparisons.items()
        for r in v.get("controls", [])
    ]
    if rows:
        with (args.output / "control_displacements.csv").open("w") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    fig, axes = plt.subplots(2, 3, figsize=(16, 7), layout="constrained")
    base = reference or next(iter(stages.values()), None)
    if base is None:
        raise ValueError("Supply at least one input stage")
    bounds = list(
        footprint(Affine(*base["affine"]), base["height"], base["width"]).bounds
    )
    mapped_footprints = {}
    coordinate_maps = {}
    from shapely.ops import transform as transform_geometry

    for name, stage in stages.items():
        mapper = Transformer.from_crs(stage["crs"], base["crs"], always_xy=True)
        coordinate_maps[name] = mapper
        geom = footprint(Affine(*stage["affine"]), stage["height"], stage["width"])
        mapped_footprints[name] = transform_geometry(mapper.transform, geom)
    extents = np.array([geom.bounds for geom in mapped_footprints.values()])
    bounds = [
        float(extents[:, 0].min()),
        float(extents[:, 1].min()),
        float(extents[:, 2].max()),
        float(extents[:, 3].max()),
    ]
    if polygons is not None and base["crs"]:
        poly = polygons.to_crs(base["crs"])
        # Common overview extent includes all supplied polygons explicitly.
    else:
        poly = None
    finite = images.get("source_tiff", next(iter(images.values())))
    valid = finite[np.isfinite(finite)]
    limits = np.quantile(valid, [0.02, 0.98]) if valid.size else (0, 1)
    labels = [
        "A — Original TIFF",
        "B — H5 reader geometry",
        "C — Native ENVI",
        "D — Corrected ENVI",
        "E — Final product",
    ]
    for ax, (name, _), label in zip(axes.flat, paths, labels):
        ax.set_title(label)
        if name not in stages:
            ax.text(
                0.5,
                0.5,
                "Unavailable"
                + ("\nFinal may be point-based" if name == "final" else ""),
                ha="center",
                transform=ax.transAxes,
            )
        else:
            s = stages[name]
            mapper = coordinate_maps[name]
            if not CRS(s["crs"]).equals(CRS(base["crs"])):
                ax.set_title(
                    label
                    + f"\nExplicit corner coordinates EPSG:{s['epsg']} → {base['epsg']}",
                    fontsize=10,
                )
            tr = Affine(*s["affine"])
            im = images[name]
            xx, yy = np.meshgrid(
                np.r_[np.arange(0, s["width"], s["thumbnail_stride"]), s["width"]],
                np.r_[np.arange(0, s["height"], s["thumbnail_stride"]), s["height"]],
            )
            x, y = mapper.transform(
                tr.a * xx + tr.b * yy + tr.c, tr.d * xx + tr.e * yy + tr.f
            )
            ax.pcolormesh(
                x,
                y,
                im,
                cmap="viridis",
                vmin=limits[0],
                vmax=limits[1],
                rasterized=True,
            )
            for i, c in enumerate(s["control_points"]):
                x, y = mapper.transform(c["x"], c["y"])
                ax.plot(x, y, "r+")
                ax.annotate(
                    str(i + 1),
                    (x, y),
                    xytext=(
                        -10 if x > (bounds[0] + bounds[2]) / 2 else 4,
                        -12 if y > (bounds[1] + bounds[3]) / 2 else 4,
                    ),
                    textcoords="offset points",
                    color="white",
                    fontsize=9,
                    path_effects=[pe.withStroke(linewidth=2, foreground="black")],
                )
        ax.set_xlim(bounds[0], bounds[2])
        ax.set_ylim(bounds[1], bounds[3])
        ax.set_aspect("equal")
        ax.ticklabel_format(useOffset=False, style="plain")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(4))
        ax.tick_params(labelsize=8)
    ax = axes.flat[5]
    ax.set_title("F — Footprints and researcher polygons")
    if poly is not None:
        poly.boundary.plot(ax=ax, color="gray", linewidth=0.6)
    for name, geom in mapped_footprints.items():
        x, y = geom.exterior.xy
        ax.plot(x, y, label=name)
    ax.legend(fontsize=8)
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_aspect("equal")
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.xaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.tick_params(labelsize=8)
    fig.suptitle(
        ("SYNTHETIC REGRESSION FIXTURE — " if args.synthetic else "")
        + args.label
        + "\nNative arrays unaltered; display sampled; any CRS corner mapping labeled; common geographic extent",
        fontsize=14,
    )
    fig.savefig(args.output / "spatial_diagnostic.png", dpi=250)
    fig.savefig(args.output / "spatial_diagnostic.svg")
    plt.close(fig)
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in [
        "source-tiff",
        "h5",
        "native",
        "corrected",
        "final",
        "polygons",
        "parquet",
    ]:
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--band", type=int, default=1)
    parser.add_argument(
        "--source-bands",
        type=lambda value: [int(v) for v in value.split(",")],
        help="Explicit TIFF band correspondence for lossless comparisons; never inferred or discarded automatically",
    )
    parser.add_argument("--label", default="Drone spatial integrity audit")
    parser.add_argument(
        "--parquet-value-raster",
        type=Path,
        help="Explicit radiometric reference for raw_bNNN table columns; never infer radiometry from column prefixes",
    )
    parser.add_argument("--id-column", default="polygon_id")
    parser.add_argument("--label-column", default="cover_category")
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()
    packet = run(args)
    failures = [
        v
        for k, v in packet["comparisons"].items()
        if k != "source_tiff"
        and (
            v.get("status") != "five_control_points_only"
            or v.get("maximum_pixels", 0) > 1e-5
            or v.get("lossless_values", {}).get("mismatched_values", 0)
        )
    ]
    parquet = packet.get("parquet", {})
    failures += [
        key
        for key in (
            "coordinate_mismatches",
            "membership_mismatches",
            "label_mismatches",
            "invalid_indices",
            "raw_value_mismatches",
            "duplicate_pixel_records",
        )
        if parquet.get(key, 0)
    ]
    failures += [
        key
        for key, value in packet["stages"].items()
        if value.get("encoded_orientation_conflict")
    ]
    # Missing source/required stages is an incomplete investigation, never a pass.
    incomplete = not packet["authoritative_tiff_available"] or any(
        name in packet["missing_stages"] for name in ("h5", "native", "corrected")
    )
    return 2 if incomplete else 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
