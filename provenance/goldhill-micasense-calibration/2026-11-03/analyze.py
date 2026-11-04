"""Bounded numerical hypothesis checks, not a physical calibration assignment."""

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from PIL import Image, ExifTags
import rasterio
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/goldhill-micasense-calibration-20261103")
ORIGINAL = Path("/private/tmp/spectralbridge-scale-confirmation/goldhill-original.tif")
NEW = Path(
    "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
)
SAMPLE = WORK / "representative_camera/IMG_0000_6.tif"
WAVES = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def safe(v):
    if isinstance(v, dict):
        return {str(k): safe(x) for k, x in v.items()}
    if isinstance(v, (tuple, list, np.ndarray)):
        return [safe(x) for x in v]
    if isinstance(v, np.generic):
        return safe(v.item())
    if isinstance(v, bytes):
        return v.decode(errors="replace")
    if isinstance(v, float) and not np.isfinite(v):
        return None
    if (
        hasattr(v, "numerator")
        and hasattr(v, "denominator")
        and not isinstance(v, (int, float))
    ):
        return float(v)
    return v


def main():
    protected = [
        ORIGINAL,
        NEW,
        Path("/private/tmp/photogrammetry-metadata-20261102/goldhill_report.pdf"),
        SAMPLE,
        ROOT / "src/spectralbridge/radiometry.py",
        ROOT / "src/spectralbridge/pipelines/drone.py",
        ROOT / "src/spectralbridge/corrections.py",
    ]
    protected += sorted(
        Path("/private/tmp/goldhill-end-to-end-20261103/source_metadata").glob(
            "SD*_image_metadata.csv"
        )
    )
    before = {str(p): sha(p) for p in protected}
    rows = []
    sample_values = []
    hists = []
    quantiles = [0, 0.01, 0.25, 0.5, 0.75, 0.99, 1]
    with rasterio.open(ORIGINAL) as src:
        assert (
            src.dtypes[0] == "uint16"
            and src.count == 11
            and src.colorinterp[-1].name == "alpha"
        )
        alpha = src.read(11) > 0
        indices = np.flatnonzero(alpha)[:: max(1, int(alpha.sum()) // 50000)]
        spectra = []
        coords = [(457750.0, 4432750.0), (457800.0, 4432700.0), (457850.0, 4432780.0)]
        for x, y in coords:
            row, col = src.index(x, y)
            assert alpha[row, col]
            v = (
                src.read(
                    list(range(1, 11)), window=rasterio.windows.Window(col, row, 1, 1)
                )
                .reshape(10)
                .astype(float)
            )
            spectra.append(
                dict(
                    easting=x,
                    northing=y,
                    row=row,
                    column=col,
                    DN=v.tolist(),
                    hypothesis_A_DN_div_32768=(v / 32768).tolist(),
                    numeric_fraction_DN_div_65535=(v / 65535).tolist(),
                    status="CANDIDATE_CONVERSION_ONLY",
                )
            )
        for band, wave in enumerate(WAVES, 1):
            a = src.read(band)
            v = a[alpha].astype(float)
            rho = v / 32768
            rows.append(
                dict(
                    band=band,
                    wavelength_nm=int(wave),
                    valid_source_alpha_pixels=int(v.size),
                    DN_min=int(v.min()),
                    DN_max=int(v.max()),
                    DN_mean=float(v.mean()),
                    DN_quantiles=np.quantile(v, quantiles).tolist(),
                    candidate_R_min=float(rho.min()),
                    candidate_R_max=float(rho.max()),
                    candidate_R_mean=float(rho.mean()),
                    candidate_R_quantiles=np.quantile(rho, quantiles).tolist(),
                    above_one_count=int((rho > 1).sum()),
                    above_one_fraction=float(np.mean(rho > 1)),
                    zeros=int((v == 0).sum()),
                    transparent_65535_excluded=int(((a == 65535) & ~alpha).sum()),
                    status="HYPOTHESIS_A_NOT_VERIFIED_PHYSICAL_REFLECTANCE",
                )
            )
            sample_values.append(a.ravel()[indices])
            hists.append(np.histogram(rho, np.linspace(0, 0.7, 141))[0])
        display = dict(
            red_A=np.where(alpha[::6, ::6], src.read(5)[::6, ::6] / 32768, np.nan),
            nir_A=np.where(alpha[::6, ::6], src.read(10)[::6, ::6] / 32768, np.nan),
            alpha=alpha[::6, ::6],
            histograms=np.asarray(hists),
            edges=np.linspace(0, 0.7, 141),
        )
    matrix = np.array(sample_values).T.astype(float)
    red, nir = matrix[:, 4], matrix[:, 9]
    den = nir + red
    ndvi = np.divide(nir - red, den, out=np.full(len(matrix), np.nan), where=den != 0)
    a = matrix / 32768
    fraction = matrix / 65535
    corr_a = np.corrcoef(a, rowvar=False)
    corr_b = np.corrcoef(fraction, rowvar=False)
    ndvi_b = np.divide(
        fraction[:, 9] - fraction[:, 4],
        fraction[:, 9] + fraction[:, 4],
        out=np.full(len(matrix), np.nan),
        where=(fraction[:, 9] + fraction[:, 4]) != 0,
    )
    shape_checks = dict(
        deterministic_sample_pixels=len(matrix),
        sample_rule="Evenly spaced indices from full positive original alpha footprint, no class-based selection",
        red_edge_step_717_minus_650_quantiles=np.quantile(
            a[:, 7] - a[:, 4], quantiles
        ).tolist(),
        nir_minus_red_quantiles=np.quantile(a[:, 9] - a[:, 4], quantiles).tolist(),
        nir_over_red_quantiles=np.quantile(
            nir[red > 0] / red[red > 0], quantiles
        ).tolist(),
        NDVI_quantiles=np.nanquantile(ndvi, quantiles).tolist(),
        pearson_correlations=corr_a.tolist(),
        spearman_correlations=spearmanr(a).statistic.tolist(),
        max_correlation_difference_vs_DN_div_65535=float(abs(corr_a - corr_b).max()),
        max_NDVI_difference_vs_DN_div_65535=float(np.nanmax(abs(ndvi - ndvi_b))),
        interpretation="Shape/red-edge/NDVI checks are invariant to a common positive scale and cannot identify the absolute reflectance divisor or prove applied calibration.",
    )
    codes = np.arange(65536, dtype=np.float32)
    stored = codes * np.float32(10000 / 65535)
    multiplier = Fraction(65535, 32768 * 10000)
    candidate = stored * np.float32(float(multiplier))
    reference = codes / np.float32(32768)
    inverse = stored * np.float32(65535 / 10000)
    precision = dict(
        exact_candidate_multiplier=str(multiplier),
        candidate_multiplier_float=float(multiplier),
        offset=0,
        factor_relative_to_naive_S_div_10000=65535 / 32768,
        code_count=len(codes),
        max_float32_composed_reflectance_error=float(abs(candidate - reference).max()),
        max_stored_inverse_DN_error=float(abs(inverse - codes).max()),
        all_integer_codes_recovered_after_rounding=bool(
            np.array_equal(np.rint(inverse), codes)
        ),
        reference="Direct DN/32768 exactly representable for UInt16 in float32; composition adds only encoding rounding",
        examples=[
            dict(
                DN=int(x),
                fixed_S=float(np.float32(x) * np.float32(10000 / 65535)),
                candidate_R=float(np.float32(x) / np.float32(32768)),
            )
            for x in [0, 16384, 32768, 65535]
        ],
        scope="Exhaustive numerical encoding test, not 65,536 physical observations or a calibration certificate",
    )
    # An accessible camera TIFF is inspected, but dated 2021 and rejected as Goldhill evidence.
    with Image.open(SAMPLE) as image:
        tags = {
            ExifTags.TAGS.get(k, str(k)): safe(v)
            for k, v in image.tag_v2.items()
            if k in [271, 272, 305, 306, 50714]
        }
        exif = {
            ExifTags.TAGS.get(k, str(k)): safe(v)
            for k, v in image.getexif().get_ifd(34665).items()
        }
        xmp = image.tag_v2[700]
        xmp = xmp[0] if isinstance(xmp, tuple) else xmp
        xmp = xmp.decode() if isinstance(xmp, bytes) else str(xmp)
        tree = ET.fromstring(xmp)
        fields = {}
        for node in tree.iter():
            key = node.tag.split("}")[-1]
            if key in [
                "RadiometricCalibration",
                "VignettingCenter",
                "VignettingPolynomial",
                "BandSensitivity",
                "Irradiance",
                "Serial",
                "SpectralIrradiance",
                "HorizontalIrradiance",
                "DirectIrradiance",
                "ScatteredIrradiance",
                "BandName",
                "CentralWavelength",
            ]:
                values = [n.text for n in node.iter() if n.tag.endswith("}li")]
                fields[key] = values or (node.text or "").strip()
        control = dict(
            path=str(SAMPLE),
            remote_origin="/iplant/home/shared/earthlab/macrosystems/calibration/blue/SYNC0034SET/000/IMG_0000_6.tif",
            sha256=before[str(SAMPLE)],
            tiff=tags,
            exif=exif,
            xmp_fields=fields,
            identity_status="NOT_GOLDHILL: capture 2021-09-15; Goldhill source tags are 2023-08-15",
            meaning="Shows the accessible 2021 camera has factory radiance/DLS metadata; none of its coefficients/panel information is transferred to Goldhill",
        )
        (HERE / "non_goldhill_control_xmp.xml").write_text(xmp)
    (HERE / "representative_camera_control.json").write_text(
        json.dumps(safe(control), indent=2) + "\n"
    )
    after = {p: sha(Path(p)) for p in before}
    assert before == after
    result = dict(
        outcome="SUPPORTED_BUT_UNVERIFIED",
        production_physical_units="UNSUPPORTED_UNTIL_DIRECT_APPLIED_CALIBRATION_EVIDENCE",
        alpha_valid_pixels=rows[0]["valid_source_alpha_pixels"],
        band_statistics=rows,
        representative_native_spectra=spectra,
        shape_checks=shape_checks,
        precision=precision,
        independent_panel_or_reference_measurements="NOT_AVAILABLE",
        original_Goldhill_raw_photograph_status="NOT_LOCATED; relative filenames/timestamp-only CSV exports available, not original XMP/EXIF",
        protected_hashes=before,
        protected_files_unchanged=True,
        production_changes=0,
        hypothesis_A="Officially documented for calibrated Metashape output; source-specific application not established",
        hypothesis_B="No alternative documented Goldhill physical encoding found; DN/65535 is only a numerical contrast",
        hypothesis_C="Uncalibrated export remains possible; not demonstrated by missing provenance alone",
    )
    (HERE / "results.json").write_text(json.dumps(safe(result), indent=2) + "\n")
    pd.DataFrame(rows).to_csv(HERE / "per_band_candidate_statistics.csv", index=False)
    np.savez_compressed(HERE / "display_arrays.npz", **display)
    print(
        json.dumps(
            dict(
                outcome=result["outcome"],
                physical_status=result["production_physical_units"],
                valid_pixels=result["alpha_valid_pixels"],
                precision=precision,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
