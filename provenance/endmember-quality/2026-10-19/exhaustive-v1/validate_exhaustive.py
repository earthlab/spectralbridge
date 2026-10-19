"""Independent reconstruction/affine checks and benchmark replay."""
from itertools import combinations, product, islice
import json
import time
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from run_exhaustive import OUT, PREVIOUS, ROOT, sha, load_targets
from stream_mesma import search


def independent_full_target(target, e, labels):
    """Direct seven-band difference geometry, no Gram subtraction or kernel reuse."""
    groups = [np.flatnonzero(labels == c) for c in np.unique(labels)]
    best, count = np.inf, 0
    for k in (1, 2, 3):
        for comp in combinations(groups, k):
            iterator = product(*comp)
            while batch := list(islice(iterator, 4096)):
                ix = np.array(batch)
                refs = e[ix]
                if k == 1:
                    f = np.ones((len(ix), 1))
                    valid = np.ones(len(ix), bool)
                else:
                    a = refs[:, 1:] - refs[:, :1]
                    g = np.einsum('mib,mjb->mij', a, a)
                    eigen = np.linalg.eigvalsh(g)
                    good = eigen[:, 0] > np.maximum(1e-12, eigen[:, -1]*1e-10)
                    rhs = np.einsum('mib,mb->mi', a, target-refs[:, 0])
                    tail = np.zeros_like(rhs)
                    tail[good] = np.linalg.solve(g[good], rhs[good, :, None])[:, :, 0]
                    f = np.column_stack((1-tail.sum(1), tail))
                    valid = good & (f.min(1) > 1e-9)
                err = np.mean((np.einsum('mi,mib->mb', f, refs)-target)**2, axis=1)
                best = min(best, np.min(np.where(valid, err, np.inf)))
                count += len(ix)
    return best, count


def main():
    start = time.time()
    y, truth, e, labels, primary, members = load_targets()
    with np.load(OUT/'full_results.npz', allow_pickle=False) as z:
        result = {k: z[k] for k in z.files}
    np.testing.assert_array_equal(result['targets'], y)
    np.testing.assert_array_equal(result['truth'], truth)
    fractions = result['fractions']
    reconstructed = np.zeros_like(y)
    cls = np.zeros_like(truth)
    for i in range(len(y)):
        use = result['model_indices'][i] >= 0
        ix = result['model_indices'][i, use]
        f = result['member_fractions'][i, use]
        assert len(set(labels[ix])) == len(ix) <= 3
        assert f.min() > 0 and abs(f.sum()-1) < 1e-12
        reconstructed[i] = f @ e[ix]
        cls[i, labels[ix]-1] = f
        scale = 1e4  # Scale optimizer objective, not spectra, for small-residual stopping.
        fit = minimize(lambda w: scale*np.mean((w @ e[ix]-y[i])**2), np.ones(len(ix))/len(ix),
                       jac=lambda w: scale*2*e[ix] @ (w @ e[ix]-y[i])/y.shape[1],
                       method='SLSQP', bounds=[(0, 1)]*len(ix),
                       constraints={'type': 'eq', 'fun': lambda w: w.sum()-1},
                       options={'ftol': 1e-13, 'maxiter': 1000})
        assert fit.success
        np.testing.assert_allclose(fit.fun/scale, result['direct_RMSE'][i]**2, atol=1e-12)
        if len(ix) > 1:
            tail = np.linalg.lstsq((e[ix[1:]]-e[ix[0]]).T, y[i]-e[ix[0]], rcond=None)[0]
            direct = np.r_[1-tail.sum(), tail]
            np.testing.assert_allclose(direct, f, atol=1e-7)
    np.testing.assert_allclose(cls, fractions, atol=1e-14)
    np.testing.assert_allclose(reconstructed, result['reconstruction'], atol=1e-14)
    np.testing.assert_allclose(np.mean((reconstructed-y)**2, axis=1), result['RMSE']**2, atol=1e-13)
    # Shortlist solutions are feasible in full library; full residual cannot worsen.
    detail = pd.read_csv(PREVIOUS/'tables/screened_mesma_details.csv')
    selected = detail[detail.method == 'Selected screened MESMA'].sort_values('target')
    assert np.all(result['direct_RMSE'] <= selected.reconstruction_RMSE.to_numpy() + 1e-9)
    # 12-target pilot and full run agree at same model order despite target batching.
    with np.load(OUT/'pilot_results.npz', allow_pickle=False) as p:
        np.testing.assert_allclose(result['RMSE'][p['target_ids']]**2, p['RMSE']**2, atol=1e-13)
        np.testing.assert_allclose(fractions[p['target_ids']], p['fractions'], atol=1e-8)
    # Independently search EVERY model for one prespecified equal-third target.
    value, count = independent_full_target(y[30], e, labels)
    np.testing.assert_allclose(value, result['RMSE'][30]**2, atol=1e-13)
    assert count == int(result['model_count']) == 16918447
    print('independent full target verified', value, flush=True)
    # Full checkpoint reuse must reproduce all results without writes.
    cp = sorted((OUT/'full_checkpoints').glob('composition*.npz'))
    times = [p.stat().st_mtime_ns for p in cp]
    replay = search(y, e, labels, directory=OUT/'full_checkpoints', progress=False)
    np.testing.assert_array_equal(replay['fractions'], fractions)
    assert times == [p.stat().st_mtime_ns for p in cp]
    preserved = json.loads((OUT/'previous_packet_hashes.json').read_text())
    assert all(sha(ROOT/p) == h for p, h in preserved.items())
    verification = dict(targets_reconstructed=len(y), winning_models_SLSQP_checked=len(y),
                        independently_exhausted_target=30, independent_model_count=count,
                        independent_minimum_MSE=value, pilot_full_targets_checked=12,
                        checkpoint_reuse_verified=True, previous_files_unchanged=len(preserved),
                        elapsed_seconds=time.time()-start)
    (OUT/'numerical_validation.json').write_text(json.dumps(verification, indent=2)+'\n')
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
