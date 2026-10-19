"""Analysis-only streaming one-to-three distinct-class active-face MESMA.

Same rank/interior/improvement tolerances as spectralbridge.mixtures.fit_models.
Checkpoints are atomic per class set, fingerprint inputs/code/chunking, and store
only winners, never the candidate population. Near-set summaries retain one best
interior solution per class set, NOT full feasible abundance uncertainty.
"""
from pathlib import Path
from itertools import combinations, product, islice
import hashlib
import json
import math
import time
import numpy as np


def digest(a):
    a = np.ascontiguousarray(a)
    return hashlib.sha256(a.dtype.str.encode() + str(a.shape).encode() + a.tobytes()).hexdigest()


def search(targets, endmembers, labels, *, directory, chunk_models=1024, progress=True):
    y, e = np.asarray(targets, float), np.asarray(endmembers, float)
    labels = np.asarray(labels)
    if (y.ndim != 2 or e.ndim != 2 or y.shape[1] != e.shape[1]
            or y.shape[1] < 2 or not len(y) or not len(e)
            or labels.ndim != 1 or len(labels) != len(e)
            or not np.isfinite(y).all() or not np.isfinite(e).all()
            or not isinstance(chunk_models, int) or chunk_models < 1):
        raise ValueError('Finite aligned nonempty spectra/labels and positive chunk size required')
    classes, lab = np.unique(labels, return_inverse=True)
    if len(classes) < 1:
        raise ValueError('Classes required')
    groups = [np.flatnonzero(lab == j) for j in range(len(classes))]
    sets = [c for k in range(1, min(3, len(classes)) + 1)
            for c in combinations(range(len(classes)), k)]
    counts = [math.prod(len(groups[j]) for j in c) for c in sets]
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    config = dict(targets=digest(y), endmembers=digest(e), labels=classes.tolist(),
                  class_positions=digest(lab), chunk_models=chunk_models,
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  count=sum(counts), counts=counts, class_sets=sets,
                  rank_absolute=1e-12, rank_relative=1e-10,
                  positive_fraction=1e-9, improvement_MSE=1e-14)
    # JSON canonicalization converts tuples to lists consistently on reload.
    config = json.loads(json.dumps(config))
    cp = directory / 'config.json'
    if cp.exists():
        if json.loads(cp.read_text()) != config:
            raise ValueError('Checkpoint configuration/input/code mismatch')
    else:
        cp.write_text(json.dumps(config, indent=2) + '\n')
    n, bands = y.shape
    gram, dot = e @ e.T, y @ e.T
    yy = np.sum(y * y, axis=1)
    best = np.full(n, np.inf)
    bestf, bestix = np.zeros((n, 3)), np.full((n, 3), -1, int)
    errors, fractions, timings = [], [], []
    started = time.monotonic()
    done = 0
    last_progress = started
    for ci, (comp, count) in enumerate(zip(sets, counts)):
        path = directory / f'composition_{ci:02d}.npz'
        k = len(comp)
        if path.exists():
            with np.load(path, allow_pickle=False) as z:
                best, bestf, bestix = z['best'], z['bestf'], z['bestix']
                ce, cf, seconds = z['error'], z['fractions'], float(z['seconds'])
            errors.append(ce)
            fractions.append(cf)
            timings.append(seconds)
            done += count
            if progress:
                print(f'Reused {ci+1}/{len(sets)} class sets; {done:,}/{sum(counts):,} models', flush=True)
            continue
        ce, cf = np.full(n, np.inf), np.zeros((n, len(classes)))
        iterator = product(*(groups[j] for j in comp))
        t0 = time.monotonic()
        seen = 0
        while True:
            batch = list(islice(iterator, chunk_models))
            if not batch:
                break
            ix = np.asarray(batch, int)
            m = len(ix)
            if k == 1:
                f = np.ones((n, m, 1))
                valid = np.ones((n, m), bool)
                err = (yy[:, None] - 2 * dot[:, ix[:, 0]] + gram[ix[:, 0], ix[:, 0]]) / bands
            else:
                base, other = ix[:, 0], ix[:, 1:]
                g = (gram[other[:, :, None], other[:, None, :]]
                     - gram[other, base[:, None]][:, :, None]
                     - gram[base[:, None], other][:, None, :]
                     + gram[base, base][:, None, None])
                eig = np.linalg.eigvalsh(g)
                good = eig[:, 0] > np.maximum(1e-12, eig[:, -1] * 1e-10)
                rhs = (dot[:, other] - dot[:, base, None]
                       - gram[base[:, None], other][None, :, :]
                       + gram[base, base][None, :, None])
                # Explicit tiny inverse avoids per-model generic inverse overhead.
                inv = np.zeros_like(g)
                if k == 2:
                    inv[good, 0, 0] = 1 / g[good, 0, 0]
                    tail = rhs * inv[None, :, 0, 0, None]
                else:
                    det = g[:, 0, 0] * g[:, 1, 1] - g[:, 0, 1] ** 2
                    inv[good, 0, 0] = g[good, 1, 1] / det[good]
                    inv[good, 1, 1] = g[good, 0, 0] / det[good]
                    inv[good, 0, 1] = inv[good, 1, 0] = -g[good, 0, 1] / det[good]
                    tail = np.stack((rhs[:, :, 0] * inv[:, 0, 0] + rhs[:, :, 1] * inv[:, 1, 0],
                                     rhs[:, :, 0] * inv[:, 0, 1] + rhs[:, :, 1] * inv[:, 1, 1]), axis=2)
                f = np.concatenate((1 - tail.sum(2, keepdims=True), tail), axis=2)
                valid = good[None, :] & (f.min(2) > 1e-9) & (f.max(2) <= 1 + 1e-9)
                f = np.clip(f, 0, 1)
                f /= f.sum(2, keepdims=True)
                # Full quadratic expression agrees with the established kernel.
                err = yy[:, None].repeat(m, axis=1)
                for a in range(k):
                    err -= 2 * f[:, :, a] * dot[:, ix[:, a]]
                    for b in range(k):
                        err += f[:, :, a] * f[:, :, b] * gram[ix[:, a], ix[:, b]]
                err /= bands
            err = np.where(valid, np.maximum(err, 0), np.inf)
            loc = err.argmin(1)
            val = err[np.arange(n), loc]
            win = val < best - 1e-14
            rows = np.flatnonzero(win)
            best[rows] = val[rows]
            bestf[rows] = 0
            bestix[rows] = -1
            bestf[rows, :k] = f[rows, loc[rows]]
            bestix[rows, :k] = ix[loc[rows]]
            win = val < ce
            rows = np.flatnonzero(win)
            ce[rows] = val[rows]
            cf[rows] = 0
            cf[np.ix_(rows, comp)] = f[rows, loc[rows]]
            seen += m
            now = time.monotonic()
            if progress and now - last_progress >= 20:
                print(f'Set {ci+1}/{len(sets)}, {seen:,}/{count:,}; total {done+seen:,}/{sum(counts):,}; {now-started:.1f}s this invocation', flush=True)
                last_progress = now
        assert seen == count
        seconds = time.monotonic() - t0
        tmp = path.with_suffix('.tmp')
        with tmp.open('wb') as stream:
            np.savez_compressed(stream, best=best, bestf=bestf, bestix=bestix,
                                error=ce, fractions=cf, seconds=seconds)
        tmp.replace(path)
        errors.append(ce)
        fractions.append(cf)
        timings.append(seconds)
        done += count
        if progress:
            print(f'Completed {ci+1}/{len(sets)} class sets: {done:,}/{sum(counts):,} models; set {seconds:.2f}s', flush=True)
    classf = np.zeros((n, len(classes)))
    recon = np.zeros_like(y)
    for j in range(3):
        use = np.flatnonzero(bestix[:, j] >= 0)
        classf[use, lab[bestix[use, j]]] += bestf[use, j]
        recon[use] += bestf[use, j, None] * e[bestix[use, j]]
    return dict(fractions=classf, model_indices=bestix, member_fractions=bestf,
                reconstruction=recon, RMSE=np.sqrt(best),
                direct_RMSE=np.sqrt(np.mean((recon-y)**2, axis=1)),
                composition_errors=np.sqrt(np.stack(errors, axis=1)),
                composition_fractions=np.stack(fractions, axis=1),
                complexity=(bestix >= 0).sum(1), classes=classes,
                model_count=sum(counts), seconds=sum(timings))
