"""SpectralBridge public package surface."""

from __future__ import annotations

from importlib import import_module

from .brightness_config import load_brightness_coefficients

try:  # pragma: no cover - exercised when optional plotting deps missing
    from .sensor_panel_plots import (
        make_micasense_vs_landsat_panels,
        make_sensor_vs_neon_panels,
    )
except Exception:  # pragma: no cover - importing plotting is optional in lite envs
    make_micasense_vs_landsat_panels = None  # type: ignore[assignment]
    make_sensor_vs_neon_panels = None  # type: ignore[assignment]
    _PLOT_EXPORTS: tuple[str, ...] = ()
else:
    _PLOT_EXPORTS = (
        make_micasense_vs_landsat_panels.__name__,
        make_sensor_vs_neon_panels.__name__,
    )

__version__ = "2.3.0rc1"

__all__ = ["__version__"]


__all__ = sorted(
    set(
        __all__
        + (
            [
                "apply_brightness_correction",
                "build_harmonized_dataset",
                "go_forth_and_multiply",
                "process_one_flightline",
                "run_bulk_pipeline",
                "run_drone_pipeline",
                "run_spectral_library_analysis",
                "summarize_bulk_results",
                "inspect_spectral_library_preflight",
                load_brightness_coefficients.__name__,
            ]
            + list(_PLOT_EXPORTS)
        )
    )
)


def __getattr__(name: str):  # pragma: no cover - thin lazy import helper
    if name == "build_harmonized_dataset":
        from .bulk.harmonized import build_harmonized_dataset as _builder

        globals()[name] = _builder
        return _builder
    if name == "run_bulk_pipeline":
        from .pipelines.bulk import run_bulk_pipeline as _run_bulk_pipeline

        globals()[name] = _run_bulk_pipeline
        return _run_bulk_pipeline
    if name == "summarize_bulk_results":
        from .bulk.results import summarize_bulk_results as _summarize_bulk_results

        globals()[name] = _summarize_bulk_results
        return _summarize_bulk_results
    if name == "run_spectral_library_analysis":
        from .bulk.analyses.spectral_library import (
            run_spectral_library_analysis as _run_spectral_library_analysis,
        )

        globals()[name] = _run_spectral_library_analysis
        return _run_spectral_library_analysis
    if name == "inspect_spectral_library_preflight":
        from .bulk.analyses.spectral_library import (
            inspect_spectral_library_preflight as _inspect_spectral_library_preflight,
        )

        globals()[name] = _inspect_spectral_library_preflight
        return _inspect_spectral_library_preflight
    if name == "apply_brightness_correction":
        from .brightness import (
            apply_brightness_correction as _apply_brightness_correction,
        )

        globals()[name] = _apply_brightness_correction
        return _apply_brightness_correction
    if name == "run_drone_pipeline":
        from .pipelines.drone import run_drone_pipeline as _run_drone_pipeline

        globals()[name] = _run_drone_pipeline
        return _run_drone_pipeline
    if name in {"go_forth_and_multiply", "process_one_flightline"}:
        module = import_module("spectralbridge.pipelines.pipeline")
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name == "pipeline":
        module = import_module("spectralbridge.pipelines.pipeline")
        globals()[name] = module
        __all__.append(name)
        return module
    if name == "pipelines":
        module = import_module("spectralbridge.pipelines")
        if not hasattr(module, "pipeline"):
            setattr(
                module,
                "pipeline",
                import_module("spectralbridge.pipelines.pipeline"),
            )
        globals()[name] = module
        __all__.append(name)
        return module
    if name == "brdf_topo":
        module = import_module("spectralbridge.brdf_topo")
        globals()[name] = module
        __all__.append(name)
        return module
    raise AttributeError(f"module 'spectralbridge' has no attribute '{name}'")
