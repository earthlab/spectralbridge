"""Quantile ordering, plant coverage and unchanged missing/negative samples."""

import numpy as np
import pytest
from spectralbridge.plant_quantile_overlays import _overlay_figure


def test_descending_percentiles_overlay_every_plant_without_fabricating_100():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    w = np.array([400.0, 500.0, 1400.0, 1500.0])
    curves = np.arange(3 * 99 * 4, dtype=float).reshape(3, 99, 4) - 100
    curves[:, :, 2] = np.nan
    original = curves.copy()
    fig = _overlay_figure(w, curves, ["B species", "A species", "B species"], "corr")
    axes = fig.axes
    assert len(axes) == 100
    assert [a.get_title() for a in axes] == [
        f"{p}% quantile" for p in range(100, 0, -1)
    ]
    assert not axes[0].collections
    for p, ax in zip(range(99, 0, -1), axes[1:]):
        collection = next(c for c in ax.collections if isinstance(c, LineCollection))
        paths = collection.get_paths()
        assert len(paths) == 3
        for i, path in enumerate(paths):
            np.testing.assert_equal(path.vertices[:, 0], w)
            np.testing.assert_equal(path.vertices[:, 1], curves[i, p - 1])
    np.testing.assert_equal(curves, original)
    assert [t.get_text() for t in fig.legends[0].texts] == ["A species", "B species"]
    plt.close(fig)


def test_incomplete_quantile_array_rejected():
    with pytest.raises(ValueError, match="1–99"):
        _overlay_figure(np.array([400, 500]), np.zeros((1, 98, 2)), ["A"], "corr")


def test_changed_model_index_is_rejected_before_checkpoint_reads(tmp_path):
    import json
    from spectralbridge.plant_quantile_overlays import run_quantile_overlays

    root = tmp_path / "models"
    root.mkdir()
    (root / "model_index.parquet").write_bytes(b"changed")
    (root / "quantile_manifest.json").write_text(
        json.dumps({"outputs": {"model_index.parquet": "wrong"}})
    )
    with pytest.raises(ValueError, match="checksum mismatch"):
        run_quantile_overlays(root, tmp_path / "output")


@pytest.mark.parametrize(
    "stage,wavelengths",
    [
        ("olioli", [443, 482, 561, 655, 865, 1609, 2201]),
        ("micasense", [475, 560, 668, 717, 840, 841, 842, 843, 844, 845]),
    ],
)
def test_sensor_overlays_preserve_only_their_own_discrete_grid(stage, wavelengths):
    import matplotlib.pyplot as plt

    w = np.array(wavelengths, dtype=float)
    values = np.broadcast_to(np.arange(len(w)), (2, 99, len(w))).copy().astype(float)
    fig = _overlay_figure(w, values, ["A", "B"], stage)
    for ax in fig.axes[1:]:
        assert not ax.patches  # NEON atmospheric masks do not apply to sensors
        collection = ax.collections[0]
        assert len(collection.get_paths()) == 2
        np.testing.assert_equal(collection.get_paths()[0].vertices[:, 0], w)
        assert ax.get_xlim() == (w[0], w[-1])
    assert ("unverified" in fig._suptitle.get_text()) == (stage == "micasense")
    plt.close(fig)
