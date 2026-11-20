"""Apply the existing NPC/held-patch tests to the larger fixed reference batch.

Exact enumeration is retained up to 100,000 assignments. Above that bound use
99,999 reproducible within-block random assignments plus the observed assignment.
Only the permutation calculation changes; bands, patch unit, NPC statistics,
Holm family and classification/preprocessing remain unchanged. This avoids
exponential memory/time growth when additional independent patches are added.
"""

from hashlib import sha256
from math import comb, prod
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

import landsat_exploratory_pft_tests as exploratory
import landsat_hls_method_comparison as methods
from landsat_photo_annotation import exact_statistics
from landsat_hls_sampling_batch import ROOT
from spectralbridge.plant_pft_statistics import _center
from spectralbridge.pft_method_audit import npc_probability
from spectralbridge.bulk.provenance import write_json_atomic

DRAW_COUNT = 100000


def bounded_statistics(values, labels, blocks):
    y, z, b = np.asarray(values, float), np.asarray(labels, float), np.asarray(blocks)
    indices = [np.flatnonzero(b == block) for block in np.unique(b)]
    count = prod(comb(len(ix), int(z[ix].sum())) for ix in indices)
    if count <= 100000:
        return exact_statistics(y, z, b) | dict(
            permutation_method="exact", label_space_size=count, random_seed=None
        )
    # Hash the complete input identity: replay does not depend on pair/run order.
    identity = y.tobytes() + z.tobytes() + "|".join(map(str, b)).encode()
    seed = int.from_bytes(sha256(identity).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    ensemble = np.zeros((DRAW_COUNT, len(z)))
    ensemble[0] = z
    for ix in indices:
        positives = int(z[ix].sum())
        random = rng.random((DRAW_COUNT - 1, len(ix)))
        if positives:
            picks = np.argpartition(random, positives - 1, axis=1)[:, :positives]
            rows = np.broadcast_to(np.arange(1, DRAW_COUNT)[:, None], picks.shape)
            ensemble[rows, ix[picks]] = 1
    centered = _center(y, b)
    scale = np.sqrt(np.sum(centered**2, axis=0) / (len(y) - len(indices)))
    informative = np.isfinite(y).all(axis=0) & (scale > 0)
    if informative.sum() < 2:
        raise ValueError("Need two finite variable bands")
    standardized = centered[:, informative] / scale[informative]
    x = _center(z[:, None], b).ravel()
    xx = x @ x
    t = ensemble @ standardized / np.sqrt(xx)
    stats = np.column_stack([np.abs(t).max(axis=1), np.mean(t * t, axis=1)])
    beta = z @ centered[:, informative] / xx
    return dict(
        p_npc=npc_probability(stats),
        p_max=float(
            np.mean(stats[:, 0] >= stats[0, 0] - 1e-12 * max(1, abs(stats[0, 0])))
        ),
        p_integrated=float(
            np.mean(stats[:, 1] >= stats[0, 1] - 1e-12 * max(1, abs(stats[0, 1])))
        ),
        permutations=DRAW_COUNT,
        effect=float(np.sqrt(np.mean((beta / scale[informative]) ** 2))),
        observed_max=float(stats[0, 0]),
        observed_integrated=float(stats[0, 1]),
        permutation_method="monte_carlo_observed_plus_99999",
        label_space_size=count,
        random_seed=seed,
    )


def run():
    methods.SOURCE = ROOT / "review-batch-2/hls-combined"
    methods.OUTPUT = ROOT / "review-batch-2/analysis"
    methods.DESIGN = methods.DESIGN | dict(
        statistical_separation="patch-level max/integrated NPC; exact <=100000 assignments, otherwise observed+99999 random labels; Holm family10",
        randomization="fixed input-derived seed per comparison; within-region labels preserved for region-conditioned tests",
        sequential_collection="exploratory expanded cohort; current Holm family does not adjust across prior collection/analysis rounds",
    )
    exploratory.exact_statistics = bounded_statistics
    with threadpool_limits(limits=1):
        methods.run()
    write_json_atomic(
        methods.OUTPUT / "computation_provenance.json",
        dict(
            wrapper_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            permutations=DRAW_COUNT,
            exact_limit=100000,
            thresholds_unchanged=True,
            figure_updated=False,
            adequate_power_claimed=False,
        ),
    )


if __name__ == "__main__":
    run()
