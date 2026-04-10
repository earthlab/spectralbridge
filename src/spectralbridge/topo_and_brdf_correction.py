"""Backward-compatible shim for the legacy HyTools correction helpers."""

from __future__ import annotations

import warnings
from importlib import import_module


_LEGACY_MODULE = import_module("spectralbridge.deprecated.hytools")

warnings.warn(
    "spectralbridge.topo_and_brdf_correction is deprecated; "
    "use spectralbridge.deprecated.hytools instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = list(getattr(_LEGACY_MODULE, "__all__", ()))

for _name in __all__:
    globals()[_name] = getattr(_LEGACY_MODULE, _name)


def __getattr__(name: str):
    return getattr(_LEGACY_MODULE, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_LEGACY_MODULE)))
