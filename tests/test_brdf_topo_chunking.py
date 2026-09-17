from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from spectralbridge.brdf_topo import _resolve_topo_chunk_dims, apply_brdf_topo_core


class _FakeCube:
    def __init__(self, h5_path: Path):
        self.h5_path = Path(h5_path)
        self.lines = 220
        self.columns = 180
        self.bands = 4
        self.scale_factor = 1.0
        self.no_data = -9999.0

    def build_envi_header(self):
        return {"samples": self.columns, "lines": self.lines, "bands": self.bands}

    def chunk_count(self, *, chunk_y: int, chunk_x: int) -> int:
        return 1

    def iter_chunks(self, *, chunk_y: int, chunk_x: int):
        self.chunk_args = (chunk_y, chunk_x)
        data = np.ones((self.lines, self.columns, self.bands), dtype=np.float32)
        yield 0, self.lines, 0, self.columns, data


class _FakeWriter:
    def __init__(self, *_args, **_kwargs):
        pass

    def write_chunk(self, *_args, **_kwargs):
        return None

    def close(self):
        return None


class _FakeReporter:
    def __init__(self, *_args, **_kwargs):
        pass

    def update(self, *_args, **_kwargs):
        return None

    def close(self):
        return None


def test_resolve_topo_chunk_dims_scene_mode() -> None:
    cube = _FakeCube(Path("fake.h5"))
    # Scene mode applies in full-width strips (not one giant OOM chunk).
    assert _resolve_topo_chunk_dims(cube, "scene") == (220, 180)


def test_resolve_topo_chunk_dims_scene_mode_uses_full_height_when_cap_large() -> None:
    cube = _FakeCube(Path("fake.h5"))
    cube.lines = 5000
    # With _SCENE_APPLY_CHUNK_Y >> lines, apply is unchunked (one full-height strip).
    assert _resolve_topo_chunk_dims(cube, "scene") == (5000, 180)


def test_resolve_topo_chunk_dims_tile_mode() -> None:
    cube = _FakeCube(Path("fake.h5"))
    assert _resolve_topo_chunk_dims(cube, "tile") == (100, 100)


def test_resolve_topo_chunk_dims_rejects_unknown_mode() -> None:
    cube = _FakeCube(Path("fake.h5"))
    with pytest.raises(ValueError, match="topo_fit_mode must be one of"):
        _resolve_topo_chunk_dims(cube, "window")


def test_apply_brdf_topo_core_uses_scene_chunk_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h5_path = tmp_path / "source.h5"
    h5_path.write_bytes(b"h5")
    raw_img = tmp_path / "raw_envi.img"
    raw_hdr = tmp_path / "raw_envi.hdr"
    raw_img.write_bytes(b"raw")
    raw_hdr.write_text("hdr", encoding="utf-8")
    out_img = tmp_path / "corrected.img"
    out_hdr = tmp_path / "corrected.hdr"

    cube = _FakeCube(h5_path)
    monkeypatch.setattr("spectralbridge.brdf_topo.NeonCube", lambda **_: cube)
    monkeypatch.setattr("spectralbridge.brdf_topo.EnviWriter", _FakeWriter)
    monkeypatch.setattr("spectralbridge.brdf_topo.TileProgressReporter", _FakeReporter)
    monkeypatch.setattr(
        "spectralbridge.brdf_topo.fit_scs_c_coefficients",
        lambda cube, **kwargs: np.zeros(cube.bands, dtype=np.float32),
    )

    captured: dict[str, object] = {}

    def _topo(cube, chunk, ys, ye, xs, xe, **kwargs):
        captured["scs_c"] = kwargs.get("scs_c")
        return np.asarray(chunk, dtype=np.float32)

    monkeypatch.setattr("spectralbridge.brdf_topo.apply_topo_correct", _topo)
    monkeypatch.setattr(
        "spectralbridge.brdf_topo.apply_brdf_correct",
        lambda cube, chunk, ys, ye, xs, xe, **kwargs: np.asarray(
            chunk, dtype=np.float32
        ),
    )
    monkeypatch.setattr(
        "spectralbridge.brdf_topo.is_valid_envi_pair",
        lambda img, hdr: True,
    )

    params = {
        "h5_path": str(h5_path),
        "coefficients_path": str(tmp_path / "missing.json"),
    }

    apply_brdf_topo_core(
        raw_img_path=raw_img,
        raw_hdr_path=raw_hdr,
        params=params,
        out_img_path=out_img,
        out_hdr_path=out_hdr,
        interactive_mode=False,
    )

    assert cube.chunk_args == (220, 180)
    assert captured["scs_c"] is not None


def test_apply_brdf_topo_core_honors_tile_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h5_path = tmp_path / "source.h5"
    h5_path.write_bytes(b"h5")
    raw_img = tmp_path / "raw_envi.img"
    raw_hdr = tmp_path / "raw_envi.hdr"
    raw_img.write_bytes(b"raw")
    raw_hdr.write_text("hdr", encoding="utf-8")
    out_img = tmp_path / "corrected.img"
    out_hdr = tmp_path / "corrected.hdr"

    cube = _FakeCube(h5_path)
    monkeypatch.setattr("spectralbridge.brdf_topo.NeonCube", lambda **_: cube)
    monkeypatch.setattr("spectralbridge.brdf_topo.EnviWriter", _FakeWriter)
    monkeypatch.setattr("spectralbridge.brdf_topo.TileProgressReporter", _FakeReporter)

    captured: dict[str, object] = {}

    def _topo(cube, chunk, ys, ye, xs, xe, **kwargs):
        captured["scs_c"] = kwargs.get("scs_c")
        return np.asarray(chunk, dtype=np.float32)

    monkeypatch.setattr("spectralbridge.brdf_topo.apply_topo_correct", _topo)
    monkeypatch.setattr(
        "spectralbridge.brdf_topo.apply_brdf_correct",
        lambda cube, chunk, ys, ye, xs, xe, **kwargs: np.asarray(
            chunk, dtype=np.float32
        ),
    )
    monkeypatch.setattr(
        "spectralbridge.brdf_topo.is_valid_envi_pair",
        lambda img, hdr: True,
    )

    params = {"h5_path": str(h5_path)}

    apply_brdf_topo_core(
        raw_img_path=raw_img,
        raw_hdr_path=raw_hdr,
        params=params,
        out_img_path=out_img,
        out_hdr_path=out_hdr,
        topo_fit_mode="tile",
        interactive_mode=False,
    )

    assert cube.chunk_args == (100, 100)
    assert captured["scs_c"] is None
