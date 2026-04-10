from __future__ import annotations

import importlib
import sys
import warnings


def test_legacy_hytools_module_moves_under_deprecated_package() -> None:
    sys.modules.pop("spectralbridge.topo_and_brdf_correction", None)
    sys.modules.pop("spectralbridge.deprecated.hytools", None)

    new_module = importlib.import_module("spectralbridge.deprecated.hytools")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        legacy_module = importlib.import_module("spectralbridge.topo_and_brdf_correction")

    assert legacy_module.topo_and_brdf_correction is new_module.topo_and_brdf_correction
    assert legacy_module.generate_config_json is new_module.generate_config_json
    assert any(
        "spectralbridge.deprecated.hytools" in str(item.message) for item in caught
    )
