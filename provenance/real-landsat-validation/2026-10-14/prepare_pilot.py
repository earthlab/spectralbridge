"""Prepare exactly one existing real NEON flight through canonical stages."""

from pathlib import Path
from dataclasses import asdict
from spectralbridge.landsat_flight_validation import FlightValidationInput
import json
import logging
import os

# Bound BLAS; no scientific coefficients or correction formulas are changed.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
from spectralbridge.pipelines import pipeline as p
from spectralbridge import brdf_topo
from spectralbridge.utils.naming import get_flightline_products
from spectralbridge.utils_checks import is_valid_envi_pair
from spectralbridge.bulk.provenance import write_json_atomic

ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    ROOT
    / "archive/local/validation-input/NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5"
)
BASE = ROOT / "artifacts/real_landsat_validation/neon"
FLIGHT = SOURCE.stem
logging.basicConfig(level=logging.INFO)
args = dict(
    base_folder=BASE,
    product_code="DP1.30006.001",
    flight_stem=FLIGHT,
    parallel_mode=True,
)
# Processing strip size only: scene-wide fits and scientific defaults unchanged.
brdf_topo._SCENE_APPLY_CHUNK_Y = 32
raw, hdr = p.stage_export_envi_from_h5(**args, source_h5=SOURCE)
params = p.stage_build_and_write_correction_json(
    **args, source_h5=SOURCE, raw_img_path=raw, raw_hdr_path=hdr
)
corr, chdr = p.stage_apply_brdf_topo_correction(
    **args,
    raw_img_path=raw,
    raw_hdr_path=hdr,
    correction_json_path=params,
    topo_fit_mode="scene",
)
products = get_flightline_products(BASE, "DP1.30006.001", FLIGHT)
pair = products["sensor_products"]["landsat_oli"]
output = Path(pair["img"])
ohdr = Path(pair["hdr"])
if not is_valid_envi_pair(output, ohdr):
    header = p._parse_envi_header(chdr)
    parameters = json.loads(
        (ROOT / "src/spectralbridge/data/landsat_band_parameters.json").read_text()
    )["Landsat 8 OLI"]
    import numpy as np

    srfs = p._build_sensor_srfs(
        np.array(header["wavelength"]),
        parameters["wavelengths"],
        parameters["fwhms"],
        "convolution",
    )
    numeric_srfs = {
        str(center): weight
        for center, weight in zip(parameters["wavelengths"], srfs.values())
    }
    p.convolve_resample_product(
        corrected_hdr_path=chdr,
        sensor_srf=numeric_srfs,
        out_stem_resampled=output.with_suffix(""),
        sensor_name="Landsat 8 OLI",
        interactive_mode=False,
        log_every=5,
    )
write_json_atomic(
    ROOT / "artifacts/real_landsat_validation/pilot_products.json",
    dict(
        flight_id=FLIGHT,
        site="R10C",
        source_h5=str(SOURCE),
        corrected_raster=str(corr),
        adjusted_raster=str(output),
        undarkened_raster=str(
            p._with_undarkened_suffix(output.with_suffix("")).with_suffix(".img")
        ),
        synthetic_scale_factor=10000,
        scale_provenance="NEON H5 Scale_Factor and inherited ENVI reflectance scale factor",
        acquisition_datetime_local_metadata="2021-09-15 19:15:30",
        acquisition_timezone_status="H5 computer time; UTC not yet independently verified",
        topo_fit_mode="scene",
        apply_strip_rows=32,
    ),
)

# Explicit source-specific interpretation: never silently infer UTC from a naive field.

flight = FlightValidationInput(
    flight_id=FLIGHT,
    site="R10C",
    acquisition_datetime="2021-09-15T19:15:30+00:00",
    corrected_raster=str(corr),
    undarkened_raster=str(
        p._with_undarkened_suffix(output.with_suffix("")).with_suffix(".img")
    ),
    adjusted_raster=str(output),
    synthetic_scale_factor=10000,
    time_provenance="H5 Acquisition_Time 2021-09-15, 191530 [Computer Time in sec]; interpreted under NEON general UTC convention; legacy timezone not independently verified",
    source_h5=str(SOURCE),
    timezone_verified=False,
)
write_json_atomic(
    ROOT / "artifacts/real_landsat_validation/flight_input.json", asdict(flight)
)
