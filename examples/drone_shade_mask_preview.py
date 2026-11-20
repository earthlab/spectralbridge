"""Preview source-image brightness exclusions before drone translation.

Run from the repository root. These are candidate dark-pixel masks, not verified
shade classifications. Thresholds are fixed before inspecting translated values.
The source of brightness is the pre-correction orthomosaic on the same grid as
the camera-position correction experiment, never its BRDF-amplified output.

Each pixel receives 0=retain candidate, 1=exclude candidate, 255=source NoData.
All three variants use a single all-native-band validity domain. Dark valid
pixels remain eligible for review; no pixel is labelled shade by this script.
"""

from contextlib import ExitStack
from pathlib import Path
import json
import hashlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.envi import hdr_to_dict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "archive/local/drone-correction-stability/2026-11-05/stable_qr_v1"
REVIEW = ROOT / "provenance/drone-calibration-translation/2026-11-19/shade-review"
MASKS = (
    ROOT
    / "archive/local/drone-calibration-translation/2026-11-19/shade-mask-candidates"
)
THRESHOLDS = (0.10, 0.20, 0.30)
NAMES = ("Conservative", "Moderate", "Stronger")
POLICY = dict(
    status="CANDIDATE_FOR_VISUAL_REVIEW_NOT_VALIDATED_SHADE",
    source_stage="pre-correction camera-position experiment input",
    visible_wavelengths_nm=[475, 560, 668],
    brightness="arithmetic mean of three native visible bands / scene positive-visible-mean p95",
    normalization="deterministic systematic spatial sample; same scalar for three visible bands",
    threshold_fractions=THRESHOLDS,
    invalid="any native band nonfinite or source NoData; excluded from normalization and denominator",
    encoding={
        "0": "retain_candidate",
        "1": "exclude_candidate",
        "255": "source_nodata",
    },
    classification="brightness proxy only; dark vegetation/soil may be excluded and shade may be missed",
    corrections_refitted=False,
    translation_performed=False,
)


def file_sha256(path):
    """Hash source rasters in bounded buffers without materializing a full cube."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def visible_indices(wavelengths):
    """Physical wavelength matching, with no positional-band assumptions."""
    waves = np.asarray(wavelengths, float)
    result = []
    for target in POLICY["visible_wavelengths_nm"]:
        matches = np.flatnonzero(np.abs(waves - target) <= 1)
        if len(matches) != 1:
            raise ValueError(f"Need one unambiguous visible band at {target} nm")
        result.append(int(matches[0]))
    return result


def classify(cube, indices, denominator, threshold, nodata=np.nan):
    """Uniform mask for every translated band, preserving unknown input support."""
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError("Positive finite scene brightness normalizer required")
    valid = np.isfinite(cube).all(axis=0)
    if nodata is not None and np.isfinite(nodata):
        valid &= ~(cube == nodata).any(axis=0)
    brightness = np.mean(cube[indices].astype(np.float64), axis=0) / denominator
    result = np.full(valid.shape, 255, dtype=np.uint8)
    result[valid] = (brightness[valid] < threshold).astype(np.uint8)
    return result, brightness


def run():
    REVIEW.mkdir(parents=True, exist_ok=True)
    MASKS.mkdir(parents=True, exist_ok=True)
    # JSON canonicalization makes the frozen policy identical after serialization.
    policy = json.loads(json.dumps(POLICY))
    path = REVIEW / "candidate_mask_policy.json"
    if path.exists() and json.loads(path.read_text()) != policy:
        raise ValueError("Review policy changed: create a new version")
    write_json_atomic(path, policy)
    rows, provenance = [], []
    board, axes = plt.subplots(3, 4, figsize=(19, 14), facecolor="white")
    for site_index, (site, stem) in enumerate(
        [
            ("gordon", "AOP_GORDON_20230814"),
            ("goldhill", "AOP_GOLDHILL_20230814"),
            ("ruby", "AOP_Ruby_20230814"),
        ]
    ):
        source = SOURCE / site / f"{stem}__experimental_candidate.img"
        header = hdr_to_dict(source.with_suffix(".hdr"))
        indices = visible_indices(header["wavelength"])
        with rasterio.open(source) as src:
            if src.crs is None:
                raise ValueError("Missing source projection")
            # Native-grid systematic sampling, no averaging across sun/shade edges.
            stride = max(1, int(np.ceil(np.sqrt(src.width * src.height / 200000))))
            from spectralbridge.envi import memmap_bsq

            native = memmap_bsq(source, header)
            small = np.asarray(native[:, ::stride, ::stride], dtype=np.float32)
            valid = np.isfinite(small).all(axis=0)
            if src.nodata is not None and np.isfinite(src.nodata):
                valid &= ~(small == src.nodata).any(axis=0)
            mean = np.mean(small[indices].astype(np.float64), axis=0)
            positive = mean[valid & (mean > 0)]
            if not len(positive):
                raise ValueError("No positive valid visible brightness")
            normalizer = float(np.percentile(positive, 95))
            rgb = np.moveaxis(small[[indices[2], indices[1], indices[0]]], 0, -1)
            stretch = np.percentile(rgb[valid], [2, 98], axis=0)
            display = np.clip(
                (rgb - stretch[0]) / np.maximum(stretch[1] - stretch[0], 1e-12), 0, 1
            )
            display[~valid] = 0.94
            profile = dict(
                driver="GTiff",
                width=src.width,
                height=src.height,
                count=1,
                dtype="uint8",
                crs=src.crs,
                transform=src.transform,
                nodata=255,
                compress="deflate",
                tiled=True,
                blockxsize=256,
                blockysize=256,
            )
            counts = [dict(valid=0, excluded=0) for _ in THRESHOLDS]
            with ExitStack() as stack:
                writers = []
                for threshold in THRESHOLDS:
                    dest = (
                        MASKS
                        / f"{stem}__shade_candidate_relative_visible_{int(threshold * 100):02d}pct.tif"
                    )
                    writer = stack.enter_context(rasterio.open(dest, "w", **profile))
                    writer.update_tags(
                        status=POLICY["status"],
                        source=str(source),
                        relative_visible_threshold=str(threshold),
                        normalization_p95=str(normalizer),
                        mask_codes="0=retain,1=exclude,255=source_nodata",
                    )
                    writers.append(writer)
                for start in range(0, src.height, 256):
                    window = Window(0, start, src.width, min(256, src.height - start))
                    cube = src.read(window=window)
                    for i, threshold in enumerate(THRESHOLDS):
                        mask, _ = classify(
                            cube, indices, normalizer, threshold, src.nodata
                        )
                        writers[i].write(mask, 1, window=window)
                        counts[i]["valid"] += int((mask != 255).sum())
                        counts[i]["excluded"] += int((mask == 1).sum())
            axes[site_index, 0].imshow(display)
            axes[site_index, 0].set_title(f"{site.title()} — source RGB", fontsize=13)
            fig, detail = plt.subplots(1, 4, figsize=(18, 6), facecolor="white")
            detail[0].imshow(display)
            detail[0].set_title("Source RGB")
            for i, threshold in enumerate(THRESHOLDS):
                mask, _ = classify(small, indices, normalizer, threshold, src.nodata)
                fraction = counts[i]["excluded"] / counts[i]["valid"]
                overlay = np.zeros((*mask.shape, 4))
                overlay[mask == 1] = [1, 0.38, 0.05, 0.75]
                title = f"{NAMES[i]}: <{threshold:.0%} of p95\n{fraction:.1%} of valid pixels excluded"
                for ax in [axes[site_index, i + 1], detail[i + 1]]:
                    ax.imshow(display)
                    ax.imshow(overlay)
                    ax.set_title(title, fontsize=12)
                rows.append(
                    dict(
                        site=site,
                        variant=NAMES[i],
                        threshold=threshold,
                        normalization_p95_native_units=normalizer,
                        sampling_stride=stride,
                        valid_source_pixels=counts[i]["valid"],
                        excluded_candidate_pixels=counts[i]["excluded"],
                        excluded_fraction=fraction,
                        mask=str(Path(writers[i].name).relative_to(ROOT)),
                        candidate_only=True,
                    )
                )
            for ax in detail:
                ax.axis("off")
            fig.suptitle(
                f"{site.title()}: orange = candidate dark-pixel exclusion; shade identity requires review",
                fontsize=14,
            )
            fig.tight_layout()
            fig.savefig(REVIEW / f"{site}_shade_mask_candidates.png", dpi=180)
            plt.close(fig)
            provenance.append(
                dict(
                    site=site,
                    source=str(source.relative_to(ROOT)),
                    source_bytes=source.stat().st_size,
                    source_mtime_ns=source.stat().st_mtime_ns,
                    header_sha256=file_sha256(source.with_suffix(".hdr")),
                    visible_native_band_indices_1based=[index + 1 for index in indices],
                    source_sha256=file_sha256(source),
                )
            )
        print(site, [f"{c['excluded'] / c['valid']:.1%}" for c in counts], flush=True)
    for ax in axes.flat:
        ax.axis("off")
    board.suptitle(
        "Drone shade-mask candidates for review\nOrange = dark pixels proposed for exclusion; no translation or upload yet",
        fontsize=18,
    )
    board.subplots_adjust(
        left=0.015, right=0.985, bottom=0.03, top=0.88, hspace=0.38, wspace=0.035
    )
    board.savefig(REVIEW / "three_site_shade_mask_comparison.png", dpi=150)
    board.savefig(REVIEW / "three_site_shade_mask_overview.png", dpi=65)
    plt.close(board)
    pd.DataFrame(rows).to_csv(REVIEW / "candidate_exclusion_counts.csv", index=False)
    write_json_atomic(
        REVIEW / "source_provenance.json",
        dict(
            sources=provenance,
            code_sha256=file_sha256(Path(__file__)),
            policy=policy,
            mask_sha256={p.name: file_sha256(p) for p in sorted(MASKS.glob("*.tif"))},
            chosen_mask=None,
            translated_products_created=False,
            uploaded=False,
        ),
    )


if __name__ == "__main__":
    run()
