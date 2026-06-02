"""Pipeline entry points for SpectralBridge."""

from __future__ import annotations

from importlib import import_module

__all__ = ["run_pipeline", "run_drone_pipeline", "run_download", "pipeline"]


def __getattr__(name: str):
    if name == "run_drone_pipeline":
        from .drone import run_drone_pipeline as _run_drone_pipeline

        globals()[name] = _run_drone_pipeline
        return _run_drone_pipeline
    if name == "run_download":
        from .download import run_download as _run_download

        globals()[name] = _run_download
        return _run_download
    if name == "run_pipeline":
        from .pipeline import run_pipeline as _run_pipeline

        globals()[name] = _run_pipeline
        return _run_pipeline
    if name == "pipeline":
        module = import_module("spectralbridge.pipelines.pipeline")
        globals()[name] = module
        return module
    raise AttributeError(f"module 'spectralbridge.pipelines' has no attribute {name!r}")
