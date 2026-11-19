"""Inspect additional public aerial epochs at the existing evergreen patches.

This stage addresses illumination/reference uncertainty, not sample inflation.
The same 30 m lattice is retained and each image stays attached to its own year.
No forest-cover map or image-quality statistic is treated as a verified PFT label.
"""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely import Point
from shapely.geometry import shape

from landsat_regional_candidates import aerial_chip
from landsat_spatial_expansion import (
    CACHE as PATCH_CACHE,
    OUTPUT as ROUND2,
    SEASONAL,
    sha,
)
from spectralbridge.bulk.provenance import write_json_atomic, write_text_atomic

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROUND2 / "evergreen-epochs"
CACHE = ROOT / "archive/local/landsat-evergreen-epochs"
PATCHES = {
    "front_range": [
        "r2-front_range-evergreen-006",
        "r2-front_range-evergreen-007",
        "r2-front_range-evergreen-009",
    ],
    "gunnison_aspen": [
        "r2-gunnison_aspen-evergreen-005",
        "r2-gunnison_aspen-evergreen-008",
    ],
    "cascades": [
        "r2-cascades-evergreen-001",
        "r2-cascades-evergreen-005",
        "r2-cascades-evergreen-006",
        "r2-cascades-evergreen-007",
        "r2-cascades-evergreen-009",
        "r2-cascades-herbaceous-006",
    ],
    "yellowstone": ["r2-yellowstone-evergreen-008"],
}


def epoch_choices(metadata, items):
    """Choose other aerial years by date/coverage only, without Landsat spectra."""
    point = Point(metadata["longitude"], metadata["latitude"])
    available = []
    anchor = pd.Timestamp(metadata["scene_datetime"])
    for item in items:
        date = pd.Timestamp(item["properties"]["datetime"])
        target = pd.Timestamp(
            year=date.year, month=anchor.month, day=anchor.day, tz="UTC"
        )
        offset = abs((date.normalize() - target).days)
        if (
            date.year != int(metadata["naip_datetime"][:4])
            and offset <= 45
            and shape(item["geometry"]).covers(point)
        ):
            available.append((date.year, offset, item["id"], item, target))
    # Full 240 m context coverage is checked by aerial_chip, not just the center.
    years = sorted({row[0] for row in available})
    return [
        (
            year,
            sorted(
                [row for row in available if row[0] == year],
                key=lambda row: (row[1], row[2]),
            ),
        )
        for year in years
    ]


def run_region(region):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    source = SEASONAL / f"{region}-aerial-catalogue.json"
    items = json.loads(source.read_text())["features"]
    records = []
    for patch in PATCHES[region]:
        metadata = json.loads((PATCH_CACHE / f"{patch}.json").read_text())
        for year, choices in epoch_choices(metadata, items):
            key = f"{patch}-{year}"
            checkpoint = CACHE / f"{key}.json"
            image_path = CACHE / f"{key}.npy"
            identity = hashlib.sha256(
                json.dumps(
                    dict(
                        patch_sha256=sha(PATCH_CACHE / f"{patch}.json"),
                        catalogue_sha256=sha(source),
                        year=year,
                        context_m=240,
                        pixels=600,
                    ),
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            saved = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
            if (
                saved.get("identity") == identity
                and saved.get("status") == "context_ready"
            ):
                if sha(image_path) != saved["image_sha256"]:
                    raise ValueError("Aerial checkpoint changed")
                records.append(saved)
                continue
            print(region, patch, year, "retrieving alternate aerial epoch", flush=True)
            proposal = metadata.copy()
            proposal["scene_datetime"] = choices[0][4].isoformat()
            selected, image = aerial_chip(
                proposal, [row[3] for row in choices], context_m=240, pixels=600
            )
            saved = (
                metadata
                | selected
                | dict(
                    epoch_id=key,
                    identity=identity,
                    status="no_complete_context",
                    aerial_year=year,
                    original_reference_aerial_year=int(metadata["naip_datetime"][:4]),
                )
            )
            if image is not None:
                temp = image_path.with_suffix(".tmp")
                with temp.open("wb") as stream:
                    np.save(stream, image.astype(np.uint8))
                temp.replace(image_path)
                saved.update(
                    status="context_ready",
                    image_sha256=sha(image_path),
                    pixel_identity_unchanged=True,
                    reference_review="pending",
                    pft_purity_verified=False,
                )
            write_json_atomic(checkpoint, saved)
            records.append(saved)
            write_text_atomic(
                OUTPUT / f"{region}-alternate-aerial-epochs.csv",
                pd.DataFrame(records).to_csv(index=False),
            )
    write_text_atomic(
        OUTPUT / f"{region}-alternate-aerial-epochs.csv",
        pd.DataFrame(
            records,
            columns=list(records[0])
            if records
            else ["epoch_id", "status", "context_patch_id", "aerial_year"],
        ).to_csv(index=False),
    )
    sheets(region)


def sheets(region):
    frame = pd.read_csv(OUTPUT / f"{region}-alternate-aerial-epochs.csv")
    frame = frame.loc[frame.status.eq("context_ready")]
    for start in range(0, len(frame), 4):
        fig, axes = plt.subplots(2, 2, figsize=(12, 12))
        for ax in axes.flat:
            ax.axis("off")
        for ax, (_, row) in zip(axes.flat, frame.iloc[start : start + 4].iterrows()):
            image = np.load(CACHE / f"{row.epoch_id}.npy")
            ax.imshow(np.moveaxis(image, 0, -1), extent=(-120, 120, -120, 120))
            for edge in np.arange(-105, 106, 30):
                ax.axvline(edge, color="cyan", lw=0.4)
                ax.axhline(edge, color="cyan", lw=0.4)
            ax.axis("on")
            ax.tick_params(labelsize=7)
            ax.set_title(
                f"{row.context_patch_id}\nAerial: {str(row.naip_datetime)[:10]}; same native grid\nClass/purity unresolved until dated review",
                fontsize=9,
            )
        fig.suptitle(
            "Evergreen reference review: alternate aerial epochs\nRepeated years are not independent native pixels",
            fontsize=12,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        fig.savefig(
            OUTPUT / f"{region}-alternate-epoch-review-{start // 4 + 1:02d}.png",
            dpi=170,
        )
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", choices=list(PATCHES))
    parser.add_argument("--sheets", choices=list(PATCHES))
    args = parser.parse_args()
    if args.region:
        run_region(args.region)
    if args.sheets:
        sheets(args.sheets)
