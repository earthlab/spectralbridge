"""Bounded isolated Goldhill BRDF experiment helpers, never production calibration."""

import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import textwrap

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/goldhill-clean-source-brdf-20261103")
SOURCE = Path(
    "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
)
LEGACY = (
    ROOT / "provenance/drone-radiometric-recovery/2026-11-02/historical_corrections.py"
)
MODEL = (
    ROOT
    / "provenance/goldhill-correction-diagnosis/2026-10-30/saved_production_brdf_model.json"
)
NEON = (
    ROOT
    / "archive/local/validation-input/NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5"
)
PRIOR = ROOT / "provenance/goldhill-end-to-end/2026-11-03"
WAVES = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
SCALE = 0.0001999969482421875
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.radiometry import Radiometry  # noqa:E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def safe(x):
    if isinstance(x, dict):
        return {str(k): safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [safe(v) for v in x]
    if isinstance(x, np.generic):
        return safe(x.item())
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def write(name, x):
    path = HERE / name
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(safe(x), indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def dist(x):
    a = np.asarray(x)
    a = a[np.isfinite(a)]
    if not a.size:
        return dict(n=0)
    return dict(
        n=len(a),
        minimum=a.min(),
        maximum=a.max(),
        mean=a.mean(),
        quantiles=np.quantile(a, [0, 0.001, 0.01, 0.25, 0.5, 0.75, 0.99, 0.999, 1]),
    )


class HypothesisRadiometry(Radiometry):
    """Affine arithmetic only; require_valid remains inherited and rejects this."""

    def to_physical(self, values, *, band_index=None):
        return self._affine(values, self.scale, self.offset, band_index=band_index)

    def to_stored(self, values, *, band_index=None):
        return self._affine(
            values, self.scale, self.offset, inverse=True, band_index=band_index
        )


def hypothesis(r):
    assert type(r) is HypothesisRadiometry and r.status == "HYPOTHETICAL_UNVERIFIED"
    assert r.provenance == "P172 isolated MicaSense_Metashape_DN_32768 hypothesis"
    return r


def isolated(function):
    """Only replace calibration precondition in an experimental function copy.

    All scientific statements and calls remain source-identical. The original
    functions/globals and inherited production calibration gate remain unchanged.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))

    class CalibrationBoundary(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "radiometry"
                and node.func.attr == "require_valid"
            ):
                return ast.copy_location(
                    ast.Call(
                        func=ast.Name(id="_p172_hypothesis", ctx=ast.Load()),
                        args=[node.func.value],
                        keywords=[],
                    ),
                    node,
                )
            return node

    tree = CalibrationBoundary().visit(tree)
    ast.fix_missing_locations(tree)
    namespace = dict(function.__globals__)
    namespace["_p172_hypothesis"] = hypothesis
    namespace["require_radiometry"] = lambda cube: hypothesis(cube.radiometry)
    if function.__name__ == "fit_and_save_brdf_model":
        for name in ["fit_scs_c_coefficients", "apply_topo_correct"]:
            namespace[name] = isolated(function.__globals__[name])
    exec(
        compile(tree, str(HERE / "experimental_calibration_adapter"), "exec"), namespace
    )
    return namespace[function.__name__]


class Cube:
    def __init__(self, data, mask, geometry, scale=SCALE, offset=0, footprint=None):
        self.data = data
        self.lines, self.columns, self.bands = data.shape
        self.mask_no_data = np.asarray(mask, bool).copy()
        self.source_valid_mask = footprint
        self.geometry = geometry
        self.scale_factor = scale if np.ndim(scale) == 0 else 1
        self.no_data = np.nan
        self.wavelengths = WAVES.copy()
        self.radiometry = HypothesisRadiometry(
            scale,
            offset,
            "HYPOTHETICAL_UNVERIFIED",
            "P172 isolated MicaSense_Metashape_DN_32768 hypothesis",
        )
        self.brdf_coefficients = copy.deepcopy(json.loads(MODEL.read_text()))

    def get_ancillary(self, name, radians=True):
        if name not in self.geometry:
            raise KeyError(name)
        a = self.geometry[name]
        return np.deg2rad(a) if radians else a

    def iter_chunks(self, chunk_y=128, chunk_x=None):
        for y in range(0, self.lines, chunk_y):
            end = min(y + chunk_y, self.lines)
            yield y, end, 0, self.columns, self.data[y:end]


def angle(x, y):
    den = np.linalg.norm(x, axis=-1) * np.linalg.norm(y, axis=-1)
    return np.rad2deg(
        np.arccos(np.clip(np.sum(x * y, axis=-1) / np.maximum(den, 1e-30), -1, 1))
    )


def ensure_snapshot():
    WORK.mkdir(parents=True, exist_ok=True)
    for name in [
        "corrections.py",
        "brdf_topo.py",
        "pipelines/drone.py",
        "radiometry.py",
    ]:
        path = HERE / ("pre_edit_" + name.replace("/", "_"))
        if not path.exists():
            path.write_bytes((ROOT / "src/spectralbridge" / name).read_bytes())


if __name__ == "__main__":
    ensure_snapshot()
