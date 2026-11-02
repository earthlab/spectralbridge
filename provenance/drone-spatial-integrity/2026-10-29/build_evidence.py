"""Reproduce saved-production-metadata evidence without inventing source TIFFs."""

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
from affine import Affine
from shapely.geometry import Polygon


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--polygons", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.summary.read_text())
    selected = [
        f
        for f in data["files"]
        if any(
            n in f.get("flight_stem", "").lower()
            for n in ["gordon", "goldhill", "ruby"]
        )
    ]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), layout="constrained")
    polygons = gpd.read_file(args.polygons).to_crs(32613)
    records = []
    for ax, f in zip(axes, selected):
        d = f["spatial_diagnostics"]
        t = Affine(*d["raster_transform"])
        w = d["raster_width"]
        h = d["raster_height"]
        # This alternate geometry illustrates the reader convention only.
        # It is NOT a proposed source placement or a repair.
        alternative = Affine(
            t.a, 0, t.c - t.a * 0.5, 0, -abs(t.e), t.f + abs(t.e) * 0.5
        )
        outlines = []
        for tr, label, color in [
            (t, "Recorded ENVI footprint", "#d34a40"),
            (alternative, "H5-reader convention hypothesis", "#17609a"),
        ]:
            footprint = Polygon([tr * p for p in [(0, 0), (w, 0), (w, h), (0, h)]])
            x, y = footprint.exterior.xy
            ax.plot(x, y, label=label, color=color, lw=2)
            outlines.append(footprint)
        bounds = np.array([p.bounds for p in outlines])
        minx, miny = bounds[:, :2].min(axis=0)
        maxx, maxy = bounds[:, 2:].max(axis=0)
        nearby = polygons.cx[minx - 100 : maxx + 100, miny - 100 : maxy + 100]
        if not nearby.empty:
            nearby.boundary.plot(ax=ax, color="#252525", lw=0.7)
        ax.set_xlim(minx - 40, maxx + 40)
        ax.set_ylim(miny - 40, maxy + 40)
        ax.set_title(f["flight_stem"] + "\nRecorded row step = +0.1 m north")
        ax.set_aspect("equal")
        ax.ticklabel_format(style="plain", useOffset=False)
        ax.tick_params(labelsize=8)
        ax.set_xlabel("UTM easting (m)")
        ax.set_ylabel("UTM northing (m)")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(5))
        rows = []
        for row, col in [
            (0, 0),
            (0, w - 1),
            (h - 1, 0),
            (h - 1, w - 1),
            (h // 2, w // 2),
        ]:
            x, y = t * (col + 0.5, row + 0.5)
            xx, yy = alternative * (col + 0.5, row + 0.5)
            rows.append(
                dict(
                    row=row,
                    col=col,
                    recorded_x=x,
                    recorded_y=y,
                    reader_hypothesis_x=xx,
                    reader_hypothesis_y=yy,
                    displacement_m=float(np.hypot(x - xx, y - yy)),
                )
            )
        records.append(
            dict(
                flight=f["flight_stem"],
                input_source_path=f["input_source_path"],
                corrected_raster_path=f["corrected_raster_path"],
                recorded=d,
                control_comparison=rows,
                maximum_hypothetical_displacement_m=max(
                    r["displacement_m"] for r in rows
                ),
            )
        )
    axes[0].legend(loc="lower left", fontsize=7)
    fig.suptitle(
        "Saved production QA: Gordon, Goldhill and Ruby\nBlack = researcher polygons; blue is an unverified reader-convention hypothesis, NOT authoritative TIFF placement",
        fontsize=13,
    )
    fig.savefig(args.output / "production_metadata_footprints.png", dpi=250)
    fig.savefig(args.output / "production_metadata_footprints.svg")
    plt.close(fig)
    output = dict(
        evidence_status="saved production metadata only; original named TIFF/H5/raster pairs unavailable",
        summary_path=str(args.summary),
        summary_sha256=hashlib.sha256(args.summary.read_bytes()).hexdigest(),
        polygons_path=str(args.polygons),
        polygons_sha256=hashlib.sha256(args.polygons.read_bytes()).hexdigest(),
        flights=records,
    )
    (args.output / "production_metadata_evidence.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
