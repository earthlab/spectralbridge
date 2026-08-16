"""Rebuild stage QA from an already completed canonical flightline directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..paths import FlightlinePaths
from .reporting import assemble_combined_report
from .stages import emit_stage_qa


def run_completed_flightline_qa(
    flightline_dir: Path,
    *,
    mode: str = "standard",
    force: bool = False,
    topo_fit_mode: str = "scene",
) -> dict[str, Any]:
    """Generate every applicable stage report from existing real artifacts."""

    flightline_dir = Path(flightline_dir).expanduser().resolve()
    if not flightline_dir.is_dir():
        raise FileNotFoundError(flightline_dir)
    flight_id = flightline_dir.name
    paths = FlightlinePaths(flightline_dir.parent, flight_id)
    h5_path = paths.h5
    raw_img = paths.envi_img if paths.envi_img.exists() else None
    corrected_img = paths.corrected_img if paths.corrected_img.exists() else None
    correction_jsons = sorted(flightline_dir.glob("*_brdfandtopo_corrected_envi.json"))
    brdf_models = sorted(flightline_dir.glob("*_brdf_model.json"))
    sensor_images = sorted(
        product.img
        for product in paths.sensor_products.values()
        if product.img.exists()
    )
    parquets = sorted(flightline_dir.glob("*.parquet"))
    reports: dict[str, Any] = {}

    acquisition_html, acquisition = emit_stage_qa(
        flightline_dir=flightline_dir,
        stage_id="acquisition",
        outputs=[h5_path],
        mode=mode,
        force=force,
    )
    reports["acquisition"] = {"html": str(acquisition_html), "report": acquisition}
    if raw_img is not None:
        input_html, input_report = emit_stage_qa(
            flightline_dir=flightline_dir,
            stage_id="input_data",
            inputs=[h5_path],
            outputs=[raw_img, raw_img.with_suffix(".hdr")],
            primary_img=raw_img,
            mode=mode,
            force=force,
        )
        reports["input_data"] = {"html": str(input_html), "report": input_report}
    parameter_outputs = [*correction_jsons, *brdf_models]
    if parameter_outputs:
        params_html, params_report = emit_stage_qa(
            flightline_dir=flightline_dir,
            stage_id="correction_parameters",
            inputs=[path for path in (h5_path, raw_img) if path is not None],
            outputs=parameter_outputs,
            mode=mode,
            force=force,
        )
        reports["correction_parameters"] = {
            "html": str(params_html),
            "report": params_report,
        }
    if raw_img is not None and corrected_img is not None:
        correction_html, correction_report = emit_stage_qa(
            flightline_dir=flightline_dir,
            stage_id="brdf_topographic_correction",
            inputs=[h5_path, raw_img, raw_img.with_suffix(".hdr"), *correction_jsons],
            outputs=[corrected_img, corrected_img.with_suffix(".hdr")],
            primary_img=corrected_img,
            reference_img=raw_img,
            chunk_shape=(100, 100) if topo_fit_mode == "tile" else None,
            parameters={"topo_fit_mode": topo_fit_mode},
            mode=mode,
            force=force,
        )
        reports["brdf_topographic_correction"] = {
            "html": str(correction_html),
            "report": correction_report,
        }
    if sensor_images:
        convolution_html, convolution_report = emit_stage_qa(
            flightline_dir=flightline_dir,
            stage_id="spectral_convolution",
            inputs=[
                path
                for path in (
                    h5_path,
                    corrected_img,
                    corrected_img.with_suffix(".hdr") if corrected_img else None,
                )
                if path is not None
            ],
            outputs=[
                path
                for image in sensor_images
                for path in (image, image.with_suffix(".hdr"))
            ],
            primary_img=sensor_images[0],
            chunk_shape=(100, 100),
            mode=mode,
            force=force,
        )
        reports["spectral_convolution"] = {
            "html": str(convolution_html),
            "report": convolution_report,
        }
    if parquets:
        tables_html, tables_report = emit_stage_qa(
            flightline_dir=flightline_dir,
            stage_id="analysis_tables",
            inputs=[*sensor_images],
            outputs=parquets,
            mode=mode,
            force=force,
        )
        reports["analysis_tables"] = {
            "html": str(tables_html),
            "report": tables_report,
        }
    combined_html, combined = assemble_combined_report(flightline_dir)
    reports["combined"] = {"html": str(combined_html), "report": combined}
    return reports


__all__ = ["run_completed_flightline_qa"]
