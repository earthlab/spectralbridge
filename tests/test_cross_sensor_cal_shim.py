import importlib
import sys
import tomllib
import warnings
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def _fresh_namespace_modules():
    saved_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "spectralbridge"
        or name.startswith("spectralbridge.")
        or name == "cross_sensor_cal"
        or name.startswith("cross_sensor_cal.")
    }
    for name in list(sys.modules):
        if name == "spectralbridge" or name.startswith("spectralbridge."):
            sys.modules.pop(name, None)
        if name == "cross_sensor_cal" or name.startswith("cross_sensor_cal."):
            sys.modules.pop(name, None)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        for name in list(sys.modules):
            if (
                name == "spectralbridge"
                or name.startswith("spectralbridge.")
                or name == "cross_sensor_cal"
                or name.startswith("cross_sensor_cal.")
            ):
                sys.modules.pop(name, None)
        sys.modules.update(saved_modules)
        importlib.invalidate_caches()


def test_cross_sensor_cal_imports():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        compat = importlib.import_module("cross_sensor_cal")

    assert compat.__path__, "compatibility shim should expose the implementation path"
    assert importlib.import_module("cross_sensor_cal.pipelines.pipeline")
    assert importlib.import_module("cross_sensor_cal.brdf_topo")


def test_cross_sensor_cal_emits_deprecation_warning_and_reexports_public_helpers():
    with _fresh_namespace_modules():
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


def test_namespace_imports_work_from_non_repo_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    with _fresh_namespace_modules():
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            spectralbridge = importlib.import_module("spectralbridge")
            compat = importlib.import_module("cross_sensor_cal")
            cli_module = importlib.import_module("spectralbridge.cli")

        assert spectralbridge.go_forth_and_multiply is not None
        assert compat.process_one_flightline is spectralbridge.process_one_flightline
        assert callable(cli_module.pipeline_main)
        assert any(
            item.category is DeprecationWarning
            and "cross_sensor_cal is deprecated; use spectralbridge instead." in str(item.message)
            for item in caught
        )


def test_project_script_entry_points_resolve_from_non_repo_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with _fresh_namespace_modules():
        pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = pyproject["project"]["scripts"]

        for script_name, target in scripts.items():
            module_name, attr_name = target.split(":")
            module = importlib.import_module(module_name)
            entry_point = getattr(module, attr_name)

            assert callable(entry_point), f"{script_name} -> {target} must resolve from arbitrary cwd"
