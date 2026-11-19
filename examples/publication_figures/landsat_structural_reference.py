"""Inspect public lidar height at frozen Cascades candidate patches.

This is a structural diagnostic, not a PFT classifier or a canopy-cover truth
product. The public HAG raster interpolates normalized point heights, including
ground returns. Acquisition intervals and missing coverage remain explicit.
Only compact 240 m windows are read; successful hashed windows are reused.
Run from the repository: .venv/bin/python examples/publication_figures/landsat_structural_reference.py
"""

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from shapely.geometry import Point, shape

from landsat_regional_candidates import open_asset
from landsat_spatial_expansion import CACHE, OUTPUT, sha
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

DEST = OUTPUT / "public-lidar"


def covering_items(items, longitude, latitude):
    """Return covering items in stable order; do not rank by measured heights."""
    point = Point(longitude, latitude)
    return sorted(
        [x for x in items if shape(x["geometry"]).covers(point)], key=lambda x: x["id"]
    )


def run():
    catalogue = DEST / "cascades-height-above-ground-catalogue.json"
    items = json.loads(catalogue.read_text())["features"]
    patches = pd.read_csv(OUTPUT / "patch_proposals.csv")
    patches = patches.loc[
        patches.region.eq("cascades") & patches.target_hypothesis.eq("Evergreen")
    ]
    records = []
    for _, patch in patches.iterrows():
        for item in covering_items(items, patch.longitude, patch.latitude):
            key = f"{patch.context_patch_id}-{item['id']}"
            path = DEST / f"{key}.npy"
            meta = DEST / f"{key}.json"
            identity = dict(
                catalogue_sha256=sha(catalogue),
                item_id=item["id"],
                easting=float(patch.easting),
                northing=float(patch.northing),
                epsg=int(patch.landsat_epsg),
                pixels=120,
                resolution_m=2,
            )
            saved = json.loads(meta.read_text()) if meta.exists() else {}
            if saved.get("identity") == identity and path.exists():
                if saved["array_sha256"] != sha(path):
                    raise ValueError("Lidar checkpoint changed")
                height = np.load(path)
            else:
                print(
                    patch.context_patch_id,
                    item["id"],
                    "reading 240 m lidar window",
                    flush=True,
                )
                with open_asset(item, "data") as src:
                    native_resolution = list(src.res)
                    with WarpedVRT(
                        src,
                        crs=f"EPSG:{patch.landsat_epsg}",
                        transform=from_origin(
                            patch.easting - 120, patch.northing + 120, 2, 2
                        ),
                        width=120,
                        height=120,
                        resampling=Resampling.nearest,
                        nodata=float("nan"),
                    ) as vrt:
                        height = vrt.read(1, masked=True).filled(np.nan)
                np.save(path, height)
                saved = dict(
                    identity=identity,
                    array_sha256=sha(path),
                    source_href=item["assets"]["data"]["href"],
                    native_resolution_m=native_resolution,
                    start_datetime=item["properties"].get("start_datetime"),
                    end_datetime=item["properties"].get("end_datetime"),
                    reference_status="structural_diagnostic_only",
                    pft_purity_verified=False,
                )
                write_json_atomic(meta, saved)
            finite = np.isfinite(height)
            records.append(
                dict(
                    context_patch_id=patch.context_patch_id,
                    item_id=item["id"],
                    valid_fraction=float(finite.mean()),
                    start_datetime=saved["start_datetime"],
                    end_datetime=saved["end_datetime"],
                    pft_purity_verified=False,
                    array_sha256=sha(path),
                )
            )
            rgb = np.load(CACHE / f"{patch.context_patch_id}.npy")
            fig, axes = plt.subplots(1, 2, figsize=(10, 5))
            axes[0].imshow(np.moveaxis(rgb, 0, -1), extent=(-120, 120, -120, 120))
            axes[0].set_title("Dated aerial reference (separate epoch)")
            im = axes[1].imshow(
                height, extent=(-120, 120, -120, 120), vmin=0, vmax=50, cmap="viridis"
            )
            axes[1].set_title(
                f"Lidar interval: {saved['start_datetime'][:10]} to {saved['end_datetime'][:10]}"
            )
            fig.colorbar(
                im, ax=axes[1], label="Interpolated height above ground (m)", shrink=0.7
            )
            for ax in axes:
                for edge in np.arange(-105, 106, 30):
                    ax.axvline(edge, color="cyan", lw=0.35)
                    ax.axhline(edge, color="cyan", lw=0.35)
            fig.suptitle(
                f"{patch.context_patch_id}\nStructural diagnostic; does not verify evergreen cover",
                fontsize=11,
            )
            fig.tight_layout()
            fig.savefig(DEST / f"{key}.png", dpi=150)
            plt.close(fig)
    write_text_atomic(
        DEST / "cascades-structural-reference-audit.csv",
        pd.DataFrame(records).to_csv(index=False),
    )


if __name__ == "__main__":
    run()
