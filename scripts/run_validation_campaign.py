#!/usr/bin/env python3
"""Run a deterministic, small-data SpectralBridge validation campaign.

The default campaign exercises real functions with synthetic or already-present
inputs.  It never contacts NEON.  Increase ``--iterations-per-module`` to expand
the variation matrix; use the separate live manifest documented under
``validation/campaigns`` before collecting network/full-flightline evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Callable

import h5py
import numpy as np

from spectralbridge.corrections import (
    apply_brdf_correct,
    apply_topo_correct,
    calc_cosine_i,
)
from spectralbridge.envi_writer import EnviWriter
from spectralbridge.neon_to_envi import neon_to_envi_no_hytools
from spectralbridge.parquet_export import build_parquet_from_envi
from spectralbridge.pipelines.drone import _export_csv_copy_from_parquet
from spectralbridge.pipelines.pipeline import stage_download_h5
from spectralbridge.qa_plots import render_flightline_panel
from spectralbridge.resample import resample_chunk_to_sensor
from spectralbridge.validation import (
    ValidationCase,
    ValidationObservation,
    run_campaign,
    write_campaign,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_VARIATIONS = (
    ("D01", "HARV"),
    ("D03", "OSBS"),
    ("D13", "NIWO"),
    ("D14", "JORN"),
    ("D17", "SJER"),
    ("D19", "BONA"),
)
MODULE_LABELS = {
    "neon_download": "NEON HDF5 download",
    "h5_to_envi": "HDF5 to raw ENVI",
    "topographic_correction": "Topographic correction",
    "brdf_correction": "BRDF correction",
    "sensor_convolution": "Sensor convolution",
    "parquet_csv": "Parquet extraction and CSV conversion",
    "save_restart": "Save and restart behavior",
    "qa_plots": "QA plots and diagnostics",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _map_info() -> list[str]:
    return [
        "UTM",
        "1.0",
        "1.0",
        "500000.0",
        "4420000.0",
        "1.0",
        "-1.0",
        "13",
        "North",
        "WGS-84",
    ]


def _write_synthetic_neon_h5(
    path: Path,
    *,
    lines: int,
    samples: int,
    bands: int,
    seed: int,
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    data = (0.05 + rng.random((lines, samples, bands)) * 0.55).astype(np.float32)
    wavelengths = np.linspace(430.0, 900.0, bands, dtype=np.float32)
    with h5py.File(path, "w") as h5_file:
        root = h5_file.create_group("VALIDATION")
        reflectance = root.create_group("Reflectance")
        dataset = reflectance.create_dataset("Reflectance_Data", data=data)
        dataset.attrs["Data_Ignore_Value"] = np.float32(-9999.0)
        metadata = reflectance.create_group("Metadata")
        spectral = metadata.create_group("Spectral_Data")
        wavelength_dataset = spectral.create_dataset("Wavelength", data=wavelengths)
        wavelength_dataset.attrs["Units"] = "Nanometers"
        spectral.create_dataset("FWHM", data=np.full(bands, 10.0, dtype=np.float32))
        coordinate = metadata.create_group("Coordinate_System")
        coordinate.create_dataset("Map_Info", data=np.array(_map_info(), dtype="S"))
        coordinate.create_dataset(
            "Coordinate_System_String",
            data=np.array("VALIDATION PROJECTION", dtype="S"),
        )
    return data


class _SyntheticCorrectionCube:
    def __init__(
        self,
        data: np.ndarray,
        *,
        scale_factor: float,
        slope_max_deg: float,
        view_zenith_deg: float,
    ) -> None:
        self.data = np.asarray(data, dtype=np.float32)
        self.scale_factor = float(scale_factor)
        self.lines, self.columns, self.bands = self.data.shape
        self.wavelengths = np.linspace(620.0, 880.0, self.bands, dtype=np.float32)
        self.mask_no_data = np.ones((self.lines, self.columns), dtype=bool)
        self.no_data = -9999.0
        self.base_key = "validation"
        y = np.linspace(0.0, 1.0, self.lines, dtype=np.float32)[:, None]
        x = np.linspace(0.0, 1.0, self.columns, dtype=np.float32)[None, :]
        self._ancillary = {
            "slope": np.deg2rad(slope_max_deg * (0.25 + 0.75 * y + 0.0 * x)).astype(np.float32),
            "aspect": (np.pi * (x + 0.0 * y)).astype(np.float32),
            "solar_zn": np.full((self.lines, self.columns), np.deg2rad(35.0), dtype=np.float32),
            "solar_az": np.full((self.lines, self.columns), np.deg2rad(145.0), dtype=np.float32),
            "sensor_zn": np.full(
                (self.lines, self.columns), np.deg2rad(view_zenith_deg), dtype=np.float32
            ),
            "sensor_az": np.full((self.lines, self.columns), np.deg2rad(20.0), dtype=np.float32),
        }

    def get_ancillary(self, name: str, radians: bool = True) -> np.ndarray:
        values = self._ancillary[name]
        return values if radians else np.rad2deg(values).astype(np.float32)


def _case(
    module: str,
    index: int,
    description: str,
    inputs: dict[str, Any],
    expected: dict[str, Any],
    runner: Callable[[], ValidationObservation],
) -> ValidationCase:
    return ValidationCase(
        module=module,
        variation_id=f"{module}-{index + 1:03d}",
        description=description,
        inputs=inputs,
        expected=expected,
        runner=runner,
    )


def _download_cases(root: Path, count: int) -> list[ValidationCase]:
    cases = []
    for index in range(count):
        domain, site = SITE_VARIATIONS[index % len(SITE_VARIATIONS)]
        date = f"2023{(index % 12) + 1:02d}15"
        stem = f"NEON_{domain}_{site}_DP1_L{index + 1:03d}-1_{date}_directional_reflectance"
        case_root = root / "neon_download" / f"case-{index:03d}"

        def runner(case_root=case_root, stem=stem, site=site, index=index):
            case_root.mkdir(parents=True, exist_ok=True)
            existing = case_root / f"{stem}.h5"
            existing.write_bytes(f"validation-{site}-{index}".encode())
            before = (existing.stat().st_mtime_ns, _sha256(existing))
            output = stage_download_h5(
                case_root,
                site,
                f"2023-{(index % 12) + 1:02d}",
                "DP1.30006.001",
                stem,
            )
            after = (output.stat().st_mtime_ns, _sha256(output))
            return ValidationObservation(
                diagnostics={
                    "output_bytes": output.stat().st_size,
                    "sha256": after[1],
                    "network_contacted": False,
                    "artifact_reused_unchanged": before == after,
                },
                checks={
                    "canonical_path_returned": output == existing,
                    "nonempty_h5_reused": before == after,
                },
                notes=("Offline restart contract; this does not validate NEON availability.",),
            )

        cases.append(
            _case(
                "neon_download",
                index,
                f"Reuse a non-empty HDF5 artifact for site {site}.",
                {"domain": domain, "site_code": site, "year_month": f"2023-{(index % 12) + 1:02d}"},
                {"network_contacted": False, "artifact_reused_unchanged": True},
                runner,
            )
        )
    return cases


def _h5_to_envi_cases(root: Path, count: int) -> list[ValidationCase]:
    cases = []
    for index in range(count):
        domain, site = SITE_VARIATIONS[index % len(SITE_VARIATIONS)]
        lines = 3 + index % 5
        samples = 4 + (index * 2) % 5
        bands = 2 + index % 6
        offset = (index % 3) * 0.01
        case_root = root / "h5_to_envi" / f"case-{index:03d}"
        stem = f"NEON_{domain}_{site}_DP1_L{index + 1:03d}-1_20230815_directional_reflectance"

        def runner(
            case_root=case_root,
            stem=stem,
            lines=lines,
            samples=samples,
            bands=bands,
            offset=offset,
            index=index,
        ):
            case_root.mkdir(parents=True, exist_ok=True)
            source = case_root / f"{stem}.h5"
            original = _write_synthetic_neon_h5(
                source, lines=lines, samples=samples, bands=bands, seed=1000 + index
            )
            metadata = neon_to_envi_no_hytools(
                [str(source)], str(case_root / "envi"), brightness_offset=offset, interactive_mode=False
            )[0]
            img = Path(metadata["img"])
            hdr = Path(metadata["hdr"])
            observed = np.fromfile(img, dtype=np.float32).reshape(bands, lines, samples).transpose(1, 2, 0)
            expected_data = original + np.float32(offset)
            max_error = float(np.max(np.abs(observed - expected_data)))
            return ValidationObservation(
                diagnostics={
                    "shape": list(observed.shape),
                    "output_bytes": img.stat().st_size,
                    "max_absolute_error": max_error,
                    "header_bytes": hdr.stat().st_size,
                },
                checks={
                    "shape_preserved": observed.shape == original.shape,
                    "float32_bsq_values_preserved": max_error <= 1e-7,
                    "header_written": hdr.exists() and hdr.stat().st_size > 0,
                },
            )

        cases.append(
            _case(
                "h5_to_envi",
                index,
                f"Convert a {lines}×{samples}×{bands} synthetic NEON-layout cube.",
                {"site_code": site, "shape_y_x_b": [lines, samples, bands], "brightness_offset": offset},
                {"shape_preserved": True, "max_absolute_error_lte": 1e-7},
                runner,
            )
        )
    return cases


def _topographic_cases(root: Path, count: int) -> list[ValidationCase]:
    del root
    cases = []
    for index in range(count):
        slope_max = 5.0 + 5.0 * (index % 6)
        scale_factor = 1e-4 if index % 2 else 1.0
        lines, samples, bands = 8 + index % 3, 9 + index % 4, 3 + index % 3

        def runner(
            slope_max=slope_max,
            scale_factor=scale_factor,
            lines=lines,
            samples=samples,
            bands=bands,
        ):
            base = np.ones((lines, samples, bands), dtype=np.float32)
            cube = _SyntheticCorrectionCube(
                base, scale_factor=scale_factor, slope_max_deg=slope_max, view_zenith_deg=5.0
            )
            cos_i = calc_cosine_i(
                cube.get_ancillary("solar_zn"),
                cube.get_ancillary("solar_az"),
                cube.get_ancillary("aspect"),
                cube.get_ancillary("slope"),
            )
            unitless = np.stack(
                [0.08 + (0.06 + band * 0.015) * cos_i for band in range(bands)], axis=-1
            ).astype(np.float32)
            stored = unitless / np.float32(scale_factor)
            cube.data = stored
            corrected = apply_topo_correct(cube, stored, 0, lines, 0, samples, use_scs_c=True)
            before = unitless[..., 0].reshape(-1)
            after = (corrected * np.float32(scale_factor))[..., 0].reshape(-1)
            geometry = cos_i.reshape(-1)
            before_corr = float(abs(np.corrcoef(before, geometry)[0, 1]))
            after_corr = float(abs(np.corrcoef(after, geometry)[0, 1]))
            finite_pct = float(np.isfinite(corrected).mean() * 100.0)
            return ValidationObservation(
                diagnostics={
                    "incidence_correlation_before": before_corr,
                    "incidence_correlation_after": after_corr,
                    "correlation_reduction": before_corr - after_corr,
                    "finite_percent": finite_pct,
                    "mean_absolute_change": float(np.mean(np.abs(corrected - stored)) * scale_factor),
                },
                checks={
                    "shape_preserved": corrected.shape == stored.shape,
                    "all_values_finite": finite_pct == 100.0,
                    "terrain_correlation_reduced": after_corr < before_corr,
                },
            )

        cases.append(
            _case(
                "topographic_correction",
                index,
                f"SCS+C correction over terrain slopes up to {slope_max:.0f}°.",
                {"slope_max_degrees": slope_max, "scale_factor": scale_factor, "shape_y_x_b": [lines, samples, bands]},
                {"finite_percent": 100.0, "terrain_correlation_reduced": True},
                runner,
            )
        )
    return cases


def _brdf_cases(root: Path, count: int) -> list[ValidationCase]:
    del root
    cases = []
    for index in range(count):
        scale_factor = 1e-4 if index % 2 else 1.0
        view_zenith = float((index % 5) * 7)
        rng = np.random.default_rng(2000 + index)
        unitless = (0.05 + rng.random((5 + index % 4, 6 + index % 3, 2 + index % 4)) * 0.6).astype(np.float32)

        def runner(unitless=unitless, scale_factor=scale_factor, view_zenith=view_zenith):
            stored = unitless / np.float32(scale_factor)
            cube = _SyntheticCorrectionCube(
                stored, scale_factor=scale_factor, slope_max_deg=10.0, view_zenith_deg=view_zenith
            )
            cube.brdf_coefficients = {
                "iso": np.ones((1, cube.bands), dtype=np.float32),
                "vol": np.zeros((1, cube.bands), dtype=np.float32),
                "geo": np.zeros((1, cube.bands), dtype=np.float32),
            }
            corrected = apply_brdf_correct(cube, stored, 0, cube.lines, 0, cube.columns)
            max_error = float(np.max(np.abs(corrected - stored)))
            return ValidationObservation(
                diagnostics={
                    "max_absolute_error_stored_units": max_error,
                    "finite_percent": float(np.isfinite(corrected).mean() * 100.0),
                    "output_min_unitless": float(np.min(corrected) * scale_factor),
                    "output_max_unitless": float(np.max(corrected) * scale_factor),
                },
                checks={
                    "shape_preserved": corrected.shape == stored.shape,
                    "neutral_model_is_identity": np.allclose(corrected, stored, atol=1e-5),
                    "dtype_preserved": corrected.dtype == np.float32,
                },
            )

        cases.append(
            _case(
                "brdf_correction",
                index,
                f"Neutral BRDF model at {view_zenith:.0f}° view zenith.",
                {"scale_factor": scale_factor, "view_zenith_degrees": view_zenith, "shape_y_x_b": list(unitless.shape)},
                {"neutral_model_is_identity": True, "dtype": "float32"},
                runner,
            )
        )
    return cases


def _convolution_cases(root: Path, count: int) -> list[ValidationCase]:
    del root
    cases = []
    for index in range(count):
        input_bands = 4 + index % 8
        output_bands = 1 + index % 5
        rng = np.random.default_rng(3000 + index)
        chunk = rng.random((3 + index % 3, 4 + index % 2, input_bands), dtype=np.float32)
        wavelengths = np.linspace(420.0, 950.0, input_bands, dtype=np.float32)
        responses = {
            f"band_{band + 1}": rng.random(input_bands, dtype=np.float32) + 0.01
            for band in range(output_bands)
        }

        def runner(chunk=chunk, wavelengths=wavelengths, responses=responses):
            observed = resample_chunk_to_sensor(chunk, wavelengths, responses)
            expected = np.stack(
                [
                    np.sum(chunk * (response / np.sum(response))[None, None, :], axis=-1)
                    for response in responses.values()
                ],
                axis=-1,
            ).astype(np.float32)
            max_error = float(np.max(np.abs(observed - expected)))
            return ValidationObservation(
                diagnostics={
                    "output_shape": list(observed.shape),
                    "max_absolute_error": max_error,
                    "output_min": float(np.min(observed)),
                    "output_max": float(np.max(observed)),
                },
                checks={
                    "output_band_count_correct": observed.shape[-1] == len(responses),
                    "weighted_average_matches_reference": max_error <= 2e-7,
                    "dtype_is_float32": observed.dtype == np.float32,
                },
            )

        cases.append(
            _case(
                "sensor_convolution",
                index,
                f"Resample {input_bands} source bands into {output_bands} target bands.",
                {"input_shape_y_x_b": list(chunk.shape), "target_band_count": output_bands},
                {"max_absolute_error_lte": 2e-7, "dtype": "float32"},
                runner,
            )
        )
    return cases


def _write_rasterio_envi(path: Path, data: np.ndarray, wavelengths: list[float]) -> tuple[Path, Path]:
    import rasterio
    from rasterio.transform import from_origin

    data = np.asarray(data, dtype=np.float32)
    with rasterio.open(
        path,
        "w",
        driver="ENVI",
        height=data.shape[1],
        width=data.shape[2],
        count=data.shape[0],
        dtype="float32",
        crs="EPSG:32613",
        transform=from_origin(500000.0, 4420000.0, 1.0, 1.0),
        nodata=-9999.0,
    ) as destination:
        destination.write(data)
    hdr = path.with_suffix(".hdr")
    with hdr.open("a", encoding="utf-8") as stream:
        stream.write("\nwavelength units = Nanometers\n")
        stream.write("wavelength = {" + ", ".join(str(value) for value in wavelengths) + "}\n")
    return path, hdr


def _parquet_csv_cases(root: Path, count: int) -> list[ValidationCase]:
    cases = []
    for index in range(count):
        lines, samples, bands = 3 + index % 4, 4 + index % 5, 2 + index % 4
        chunk_size = 2 + index % 3
        rng = np.random.default_rng(4000 + index)
        data = rng.random((bands, lines, samples), dtype=np.float32)
        case_root = root / "parquet_csv" / f"case-{index:03d}"

        def runner(
            data=data,
            lines=lines,
            samples=samples,
            bands=bands,
            chunk_size=chunk_size,
            case_root=case_root,
        ):
            import duckdb

            case_root.mkdir(parents=True, exist_ok=True)
            img, hdr = _write_rasterio_envi(
                case_root / "validation_envi.img",
                data,
                np.linspace(450.0, 850.0, bands).tolist(),
            )
            parquet = case_root / "validation_envi.parquet"
            build_parquet_from_envi(img, hdr, parquet, chunk_size=chunk_size)
            csv_path = _export_csv_copy_from_parquet(parquet, overwrite=True)
            with duckdb.connect() as connection:
                row_count = connection.execute(
                    "SELECT count(*) FROM read_parquet(?)", [str(parquet)]
                ).fetchone()[0]
                columns = [row[0] for row in connection.execute("DESCRIBE SELECT * FROM read_parquet(?)", [str(parquet)]).fetchall()]
            with csv_path.open(newline="", encoding="utf-8") as stream:
                csv_rows = sum(1 for _ in csv.reader(stream)) - 1
            spectral_columns = [column for column in columns if "_wl" in column]
            return ValidationObservation(
                diagnostics={
                    "parquet_rows": row_count,
                    "csv_rows": csv_rows,
                    "column_count": len(columns),
                    "spectral_column_count": len(spectral_columns),
                    "parquet_bytes": parquet.stat().st_size,
                    "csv_bytes": csv_path.stat().st_size,
                },
                checks={
                    "all_pixels_exported": row_count == lines * samples,
                    "csv_row_count_matches": csv_rows == row_count,
                    "spectral_band_count_matches": len(spectral_columns) == bands,
                    "coordinate_columns_present": {"row", "col", "lat", "lon"}.issubset(columns),
                },
            )

        cases.append(
            _case(
                "parquet_csv",
                index,
                f"Extract a {lines}×{samples}×{bands} ENVI cube with chunk size {chunk_size}, then write CSV.",
                {"shape_b_y_x": [bands, lines, samples], "chunk_size": chunk_size},
                {"parquet_rows": lines * samples, "csv_rows": lines * samples},
                runner,
            )
        )
    return cases


def _save_restart_cases(root: Path, count: int) -> list[ValidationCase]:
    cases = []
    for index in range(count):
        lines, samples, bands = 3 + index % 4, 4 + index % 3, 2 + index % 5
        split_row = 1 + index % (lines - 1)
        rng = np.random.default_rng(5000 + index)
        data = rng.random((lines, samples, bands), dtype=np.float32)
        case_root = root / "save_restart" / f"case-{index:03d}"

        def runner(
            data=data,
            lines=lines,
            samples=samples,
            bands=bands,
            split_row=split_row,
            case_root=case_root,
        ):
            case_root.mkdir(parents=True, exist_ok=True)
            stem = case_root / "chunked_save"
            header = {
                "samples": samples,
                "lines": lines,
                "bands": bands,
                "data type": 4,
                "interleave": "bsq",
                "byte order": 0,
                "map info": _map_info(),
                "projection": "VALIDATION PROJECTION",
                "wavelength": np.linspace(450.0, 850.0, bands).tolist(),
                "fwhm": [10.0] * bands,
                "wavelength units": "Nanometers",
            }
            writer = EnviWriter(stem, header)
            writer.write_chunk(data[:split_row], 0, 0)
            writer.write_chunk(data[split_row:], split_row, 0)
            writer.close()
            img = stem.with_suffix(".img")
            before = (_sha256(img), img.stat().st_mtime_ns)
            observed = np.fromfile(img, dtype=np.float32).reshape(bands, lines, samples).transpose(1, 2, 0)
            after = (_sha256(img), img.stat().st_mtime_ns)
            max_error = float(np.max(np.abs(observed - data)))
            return ValidationObservation(
                diagnostics={
                    "chunk_split_row": split_row,
                    "image_bytes": img.stat().st_size,
                    "max_absolute_error": max_error,
                    "sha256": after[0],
                },
                checks={
                    "chunked_write_reconstructs_cube": max_error == 0.0,
                    "read_does_not_mutate_artifact": before == after,
                    "expected_byte_count": img.stat().st_size == lines * samples * bands * 4,
                },
            )

        cases.append(
            _case(
                "save_restart",
                index,
                f"Write an ENVI cube in two chunks split at row {split_row}.",
                {"shape_y_x_b": [lines, samples, bands], "chunk_split_row": split_row},
                {"lossless_write": True, "bytes": lines * samples * bands * 4},
                runner,
            )
        )
    return cases


def _write_qa_pair(base: Path, data: np.ndarray, wavelengths: list[float]) -> None:
    np.asarray(data, dtype=np.float32).tofile(base.with_suffix(".img"))
    header = [
        "ENVI",
        f"samples = {data.shape[2]}",
        f"lines = {data.shape[1]}",
        f"bands = {data.shape[0]}",
        "data type = 4",
        "interleave = bsq",
        "byte order = 0",
        "data ignore value = -9999",
        "wavelength units = Nanometers",
        "fwhm = {" + ", ".join("10" for _ in wavelengths) + "}",
        "wavelength = {" + ", ".join(str(value) for value in wavelengths) + "}",
    ]
    base.with_suffix(".hdr").write_text("\n".join(header), encoding="utf-8")


def _qa_cases(root: Path, count: int) -> list[ValidationCase]:
    cases = []
    for index in range(count):
        delta = [0.0, 0.005, -0.01, 0.02, -0.03][index % 5]
        nodata_fraction = [0.0, 0.02, 0.08, 0.15, 0.25][index % 5]
        rng = np.random.default_rng(6000 + index)
        bands, lines, samples = 4 + index % 3, 10 + index % 4, 9 + index % 5
        raw = (0.1 + rng.random((bands, lines, samples)) * 0.4).astype(np.float32)
        corrected = (raw + np.float32(delta)).astype(np.float32)
        invalid = int(lines * samples * nodata_fraction)
        if invalid:
            raw.reshape(bands, -1)[:, :invalid] = -9999.0
            corrected.reshape(bands, -1)[:, :invalid] = -9999.0
        case_root = root / "qa_plots" / f"case-{index:03d}" / f"NEON_VALIDATION_{index:03d}"

        def runner(
            raw=raw,
            corrected=corrected,
            case_root=case_root,
            bands=bands,
            delta=delta,
        ):
            case_root.mkdir(parents=True, exist_ok=True)
            stem = case_root.name
            wavelengths = np.linspace(480.0, 850.0, bands).tolist()
            _write_qa_pair(case_root / f"{stem}_envi", raw, wavelengths)
            _write_qa_pair(case_root / f"{stem}_brdfandtopo_corrected_envi", corrected, wavelengths)
            png, metrics = render_flightline_panel(case_root, quick=True)
            json_path = png.with_suffix(".json")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            finite_delta = np.asarray(payload["correction"]["delta_median"], dtype=float)
            return ValidationObservation(
                diagnostics={
                    "png_bytes": png.stat().st_size,
                    "json_bytes": json_path.stat().st_size,
                    "reported_valid_percent": payload["mask"]["valid_pct"],
                    "median_reported_delta": float(np.nanmedian(finite_delta)),
                    "issue_count": len(payload["issues"]),
                },
                checks={
                    "png_written": png.exists() and png.stat().st_size > 0,
                    "json_written": json_path.exists() and json_path.stat().st_size > 0,
                    "band_count_reported": metrics["header"]["n_bands"] == bands,
                    "delta_diagnostic_matches_input": np.isclose(np.nanmedian(finite_delta), delta, atol=1e-5),
                },
            )

        cases.append(
            _case(
                "qa_plots",
                index,
                f"Render QA for delta {delta:+.3f} and {nodata_fraction:.0%} injected NoData.",
                {"shape_b_y_x": [bands, lines, samples], "correction_delta": delta, "nodata_fraction": nodata_fraction},
                {"png_and_json_written": True, "reported_delta": delta},
                runner,
            )
        )
    return cases


def build_offline_cases(root: Path, count: int) -> list[ValidationCase]:
    """Return the complete deterministic offline validation matrix."""

    factories = (
        _download_cases,
        _h5_to_envi_cases,
        _topographic_cases,
        _brdf_cases,
        _convolution_cases,
        _parquet_csv_cases,
        _save_restart_cases,
        _qa_cases,
    )
    cases: list[ValidationCase] = []
    for factory in factories:
        cases.extend(factory(root, count))
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--iterations-per-module",
        type=int,
        default=5,
        help="Number of deterministic input variations for each module (default: 5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "validation" / "results" / "offline-contract.json",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Preserve intermediate artifacts here instead of using a temporary directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.iterations_per_module < 1:
        raise SystemExit("--iterations-per-module must be positive")
    logging.basicConfig(level=logging.WARNING)

    if args.work_dir is not None:
        work_root = args.work_dir.resolve()
        work_root.mkdir(parents=True, exist_ok=True)
        temporary_context = None
    else:
        temporary_context = tempfile.TemporaryDirectory(prefix="spectralbridge-validation-")
        work_root = Path(temporary_context.name)

    try:
        cases = build_offline_cases(work_root, args.iterations_per_module)
        campaign = run_campaign(
            cases,
            campaign_id=f"offline-contract-{args.iterations_per_module}-per-module",
            mode="offline",
            repo_root=REPO_ROOT,
            metadata={
                "module_labels": MODULE_LABELS,
                "iterations_per_module": args.iterations_per_module,
                "network_contacted": False,
                "evidence_scope": "Synthetic and already-present-input function contracts; not external scientific accuracy.",
            },
        )
        output = write_campaign(campaign, args.output)
    finally:
        if temporary_context is not None:
            temporary_context.cleanup()

    summary = campaign["summary"]
    print(
        f"Validation campaign: {summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['skipped']} skipped ({summary['total']} total)"
    )
    print(output)
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
