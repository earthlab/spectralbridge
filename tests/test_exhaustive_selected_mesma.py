"""Bounded exhaustive analysis kernel: independent optima and restart contracts."""
import importlib.util
from pathlib import Path
from itertools import combinations, product
import numpy as np
import pytest
from spectralbridge.mixtures import fit_models

PATH = Path(__file__).resolve().parents[1] / 'provenance/endmember-quality/2026-10-19/exhaustive-v1/stream_mesma.py'
spec = importlib.util.spec_from_file_location('stream_mesma', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def independent(y, e, labels):
    errors = np.full(len(y), np.inf)
    groups = [np.flatnonzero(labels == c) for c in np.unique(labels)]
    count = 0
    for k in (1, 2, 3):
        for comp in combinations(groups, k):
            for ix in product(*comp):
                count += 1
                refs = e[list(ix)]
                if k == 1:
                    f = np.ones((len(y), 1))
                else:
                    tail = np.linalg.lstsq((refs[1:] - refs[0]).T, (y-refs[0]).T, rcond=None)[0].T
                    f = np.column_stack((1-tail.sum(1), tail))
                valid = (f >= -1e-10).all(1)
                err = np.mean((f @ refs-y)**2, axis=1)
                errors = np.minimum(errors, np.where(valid, err, np.inf))
    return np.sqrt(errors), count


@pytest.mark.parametrize('chunk', [1, 7, 128])
def test_matches_independent_and_existing(tmp_path, chunk):
    rng = np.random.default_rng(724)
    e = rng.uniform(size=(10, 7))
    labels = np.repeat(np.arange(5), 2)
    y = np.vstack((rng.uniform(size=(13, 7)), e[0], .3*e[2]+.7*e[5]))
    result = module.search(y, e, labels, directory=tmp_path, chunk_models=chunk, progress=False)
    expected = fit_models(y, labels, e, chunk_models=chunk)
    optimum, count = independent(y, e, labels)
    np.testing.assert_allclose(result['RMSE']**2, optimum**2, atol=1e-13)
    np.testing.assert_allclose(result['RMSE']**2, expected['RMSE']**2, atol=1e-13)
    np.testing.assert_allclose(result['fractions'], expected['fractions'], atol=1e-8)
    np.testing.assert_allclose(result['direct_RMSE']**2, result['RMSE']**2, atol=1e-13)
    assert result['model_count'] == count == 130
    np.testing.assert_allclose(result['fractions'].sum(1), 1)
    saved = sorted(tmp_path.glob('composition*.npz'))
    mtimes = [p.stat().st_mtime_ns for p in saved]
    again = module.search(y, e, labels, directory=tmp_path, chunk_models=chunk, progress=False)
    np.testing.assert_array_equal(result['fractions'], again['fractions'])
    assert mtimes == [p.stat().st_mtime_ns for p in saved]
    # Delete last composition to emulate an interrupted search.
    saved[-1].unlink()
    resumed = module.search(y, e, labels, directory=tmp_path, chunk_models=chunk, progress=False)
    np.testing.assert_array_equal(result['fractions'], resumed['fractions'])
    with pytest.raises(ValueError, match='mismatch'):
        module.search(y + .01, e, labels, directory=tmp_path, chunk_models=chunk, progress=False)


def test_degenerate_faces_and_ties(tmp_path):
    e = np.array([[1., 0, 0], [1, 0, 0], [0, 1, 0], [.5, .5, 0], [0, 0, 1]])
    y = np.array([[1, 0, 0], [.3, .2, .5], [.5, .5, 0]])
    result = module.search(y, e, np.arange(5), directory=tmp_path, progress=False)
    np.testing.assert_allclose(result['direct_RMSE'], 0, atol=1e-10)
    assert result['complexity'][0] == 1 and result['model_indices'][0, 0] == 0


@pytest.mark.parametrize('chunk', [0, -1, 1.5])
def test_bad_chunk(tmp_path, chunk):
    with pytest.raises(ValueError):
        module.search(np.eye(3), np.eye(3), [0, 1, 2], directory=tmp_path, chunk_models=chunk)
