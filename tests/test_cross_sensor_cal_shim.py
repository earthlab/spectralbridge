import importlib
import sys
import tomllib
import warnings
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cross_sensor_cal_imports():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        compat = importlib.import_module("cross_sensor_cal")

    assert compat.__path__, "compatibility shim should expose the implementation path"
    assert importlib.import_module("cross_sensor_cal.pipelines.pipeline")
    assert importlib.import_module("cross_sensor_cal.brdf_topo")


def test_cross_sensor_cal_emits_deprecation_warning_and_reexports_public_helpers():
    for name in list(sys.modules):
        if name == "cross_sensor_cal" or name.startswith("cross_sensor_cal."):
            sys.modules.pop(name, None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        compat = importlib.import_module("cross_sensor_cal")
        spectralbridge = importlib.import_module("spectralbridge")

    assert any(
        item.category is DeprecationWarning
        and "cross_sensor_cal is deprecated; use spectralbridge instead." in str(item.message)
        for item in caught
    )
    assert compat.go_forth_and_multiply is spectralbridge.go_forth_and_multiply
    assert compat.process_one_flightline is spectralbridge.process_one_flightline


def test_project_script_entry_points_resolve_to_callables():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["project"]["scripts"]

    for script_name, target in scripts.items():
        module_name, attr_name = target.split(":")
        module = importlib.import_module(module_name)
        entry_point = getattr(module, attr_name)

        assert callable(entry_point), f"{script_name} -> {target} must resolve to a callable"
