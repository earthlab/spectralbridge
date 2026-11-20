"""Apply the user-selected conservative mask and retry existing translation QA.

No correction model is refitted: this tests shade exclusion from the requested
already-corrected translation inputs. BRDF/radiometry statuses are preserved.
Missing/rejected combined products are not replaced with another branch.
Original rasters and the packaged coefficient registry remain immutable.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

from drone_shade_mask_preview import ROOT, SOURCE, MASKS, file_sha256
from spectralbridge.bulk.provenance import write_json_atomic
from spectralbridge.drone_translation import (
    apply_drone_translation,
    load_drone_translation_plans,
    translated_output_stem,
)
from spectralbridge.drone_translation_registry import (
    packaged_drone_translation_coefficients_path,
)
from spectralbridge.envi import hdr_to_dict, memmap_bsq
from spectralbridge.envi_writer import EnviWriter
from spectralbridge.utils_checks import is_valid_envi_pair

EVIDENCE = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/conservative-trial"
)
OUTPUT = (
    ROOT / "archive/local/drone-calibration-translation/2026-11-19/conservative-trial"
)
REVIEW = ROOT / "provenance/drone-calibration-translation/2026-11-19/shade-review"


def mask_chunk(cube, mask, nodata):
    """Drop the same pixel from every band; retained stored values stay exact."""
    if cube.shape[:2] != mask.shape or cube.ndim != 3:
        raise ValueError("Mask and source chunk dimensions differ")
    if not np.isin(mask, [0, 1, 255]).all():
        raise ValueError("Unknown mask code")
    result = cube.copy()
    result[mask != 0] = nodata
    return result


def run():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((REVIEW / "source_provenance.json").read_text())
    registry = packaged_drone_translation_coefficients_path()
    reports, gains = [], []
    for site, stem in [
        ("gordon", "AOP_GORDON_20230814"),
        ("goldhill", "AOP_GOLDHILL_20230814"),
        ("ruby", "AOP_Ruby_20230814"),
    ]:
        source = SOURCE / site / "combined" / f"{stem}__combined_EXPERIMENTAL.img"
        mask_path = MASKS / f"{stem}__shade_candidate_relative_visible_10pct.tif"
        identity = dict(
            source=str(source),
            mask_sha256=file_sha256(mask_path),
            coefficient_sha256=file_sha256(registry),
            threshold=0.10,
            correction_refitted=False,
            criteria_changed=False,
        )
        if identity["mask_sha256"] != provenance["mask_sha256"][mask_path.name]:
            raise ValueError("Reviewed conservative mask has changed")
        record = dict(site=site, identity=identity, translations=[], uploaded=False)
        if site == "ruby" or not is_valid_envi_pair(source, source.with_suffix(".hdr")):
            record.update(
                status="NO_ACCEPTED_COMBINED_CORRECTION",
                reason="Ruby combined BRDF rejected in the selected run; no usable corrected input exists. A shade mask does not create that input.",
            )
            reports.append(record)
            print(site, record["status"], flush=True)
            continue
        identity["source_sha256"] = file_sha256(source)
        identity["header_sha256"] = file_sha256(source.with_suffix(".hdr"))
        header = hdr_to_dict(source.with_suffix(".hdr"))
        nodata = float(header.get("data ignore value", np.nan))
        folder = OUTPUT / site
        folder.mkdir(exist_ok=True)
        masked_stem = (
            folder / f"{stem}__combined_conservative_shade_masked_EXPERIMENTAL"
        )
        checkpoint = folder / "mask_application.json"
        saved = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}
        reuse = saved.get("identity") == identity and is_valid_envi_pair(
            masked_stem.with_suffix(".img"), masked_stem.with_suffix(".hdr")
        )
        if reuse:
            for suffix in [".img", ".hdr"]:
                if (
                    file_sha256(masked_stem.with_suffix(suffix))
                    != saved["output_sha256"][suffix]
                ):
                    raise ValueError("Changed masked-copy checkpoint")
        else:
            header["description"] = (
                str(header.get("description", ""))
                + "; user-selected conservative source-visible brightness exclusion; experimental status retained"
            )
            with rasterio.open(source) as src, rasterio.open(mask_path) as mask:
                if (src.crs, src.transform, src.shape) != (
                    mask.crs,
                    mask.transform,
                    mask.shape,
                ):
                    raise ValueError("Source/mask grids differ")
                writer = EnviWriter(masked_stem, header)
                try:
                    for start in range(0, src.height, 256):
                        window = Window(
                            0, start, src.width, min(256, src.height - start)
                        )
                        cube = np.moveaxis(src.read(window=window), 0, -1)
                        result = mask_chunk(cube, mask.read(1, window=window), nodata)
                        writer.write_chunk(result, start, 0)
                finally:
                    writer.close()
            saved = dict(
                identity=identity,
                output_sha256={
                    suffix: file_sha256(masked_stem.with_suffix(suffix))
                    for suffix in [".img", ".hdr"]
                },
            )
            write_json_atomic(checkpoint, saved)
        # Verify every retained value and all masked values in bounded chunks.
        corrected = memmap_bsq(source, hdr_to_dict(source.with_suffix(".hdr")))
        output = memmap_bsq(
            masked_stem.with_suffix(".img"),
            hdr_to_dict(masked_stem.with_suffix(".hdr")),
        )
        native = SOURCE / site / f"{stem}__experimental_candidate.img"
        raw = memmap_bsq(native, hdr_to_dict(native.with_suffix(".hdr")))
        ratio_before = [[] for _ in range(10)]
        ratio_after = [[] for _ in range(10)]
        with rasterio.open(mask_path) as mask:
            for start in range(0, int(header["lines"]), 256):
                stop = min(start + 256, int(header["lines"]))
                screen = mask.read(
                    1, window=Window(0, start, int(header["samples"]), stop - start)
                )
                a, b = (
                    np.asarray(corrected[:, start:stop]),
                    np.asarray(output[:, start:stop]),
                )
                np.testing.assert_array_equal(a[:, screen == 0], b[:, screen == 0])
                assert (
                    np.isnan(b[:, screen != 0]).all()
                    if np.isnan(nodata)
                    else (b[:, screen != 0] == nodata).all()
                )
                # Store compact deterministic samples for quantiles; exact maxima
                # are evaluated separately over all finite positive-source cells.
                for band in range(10):
                    source_values = np.asarray(raw[band, start:stop], dtype=float)
                    valid = (
                        np.isfinite(a[band])
                        & np.isfinite(source_values)
                        & (source_values > 0)
                    )
                    factor = np.divide(
                        a[band],
                        source_values,
                        out=np.full(source_values.shape, np.nan),
                        where=valid,
                    )
                    for collection, subset in [
                        (ratio_before, valid),
                        (ratio_after, valid & (screen == 0)),
                    ]:
                        values = factor[subset]
                        if len(values):
                            collection[band].append(
                                (float(values.max()), values[::100].copy())
                            )
        for band in range(10):
            row = dict(
                site=site,
                native_band=band + 1,
                wavelength_nm=header["wavelength"][band],
            )
            for label, groups in [
                ("before", ratio_before[band]),
                ("after", ratio_after[band]),
            ]:
                row[f"{label}_maximum_gain"] = max(
                    (g[0] for g in groups), default=np.nan
                )
                sample = (
                    np.concatenate([g[1] for g in groups]) if groups else np.array([])
                )
                row[f"{label}_sample_p99_gain"] = (
                    float(np.percentile(sample, 99)) if len(sample) else np.nan
                )
            gains.append(row)
        record.update(
            masked_input=str(masked_stem.with_suffix(".img")),
            all_retained_values_exact=True,
            source_unchanged=file_sha256(source) == identity["source_sha256"],
            correction_refitted=False,
        )
        plans = load_drone_translation_plans(
            registry,
            source_wavelengths_nm=header["wavelength"],
            target_sensors=["Landsat_8_OLI", "Landsat_9_OLI-2"],
        )
        for plan in plans:
            entry = dict(
                target=plan.target_sensor, coefficient_units=plan.reflectance_units
            )
            translated = translated_output_stem(
                folder, stem + "__conservative_shade_masked", plan.target_sensor
            )
            try:
                result = apply_drone_translation(
                    masked_stem.with_suffix(".img"),
                    masked_stem.with_suffix(".hdr"),
                    output_stem=translated,
                    plan=plan,
                )
                entry.update(status=result["status"], output=result["output_img"])
            except ValueError as exc:
                entry.update(status="UNSUPPORTED", reason=str(exc))
            record["translations"].append(entry)
        record["status"] = (
            "UNSUPPORTED"
            if all(x["status"] == "UNSUPPORTED" for x in record["translations"])
            else "created"
        )
        reports.append(record)
        print(
            site,
            record["status"],
            [x.get("reason") for x in record["translations"]],
            flush=True,
        )
    pd.DataFrame(gains).to_csv(
        EVIDENCE / "correction_gain_before_after.csv", index=False
    )
    write_json_atomic(
        EVIDENCE / "translation_trial.json",
        dict(
            sites=reports,
            mask="user-selected conservative <10% of pre-correction visible-brightness p95",
            correction_model_refitted=False,
            code_sha256=file_sha256(Path(__file__)),
            upload_performed=False,
            thresholds_or_scientific_statuses_changed=False,
        ),
    )


if __name__ == "__main__":
    run()
