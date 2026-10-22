"""Run four independent exact-search cells concurrently with isolated checkpoints.

No change to targets, models or frozen tolerances. Keep BLAS threads at one.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import numpy as np
from run_comparison import (
    OUT,
    CONFIG,
    SCHEMES,
    prepare,
    stream,
    label_codes,
    save_json,
    summarize,
)


def run_cell(name, scheme, lib, targets):
    path = OUT / "models" / f"{name}_{scheme}_mesma.npz"
    if path.exists():
        print(f"Reused {name}/{scheme}", flush=True)
        return
    print(
        f"Started {name}/{scheme}: isolated exhaustive checkpoint directory", flush=True
    )
    result = stream.search(
        targets,
        lib["x"],
        label_codes(lib["atoms"], scheme),
        directory=OUT / "checkpoints" / f"{name}_{scheme}",
        chunk_models=CONFIG["chunk_models"],
    )
    assert np.array_equal(result["classes"], np.arange(5))
    assert np.allclose(result["RMSE"], result["direct_RMSE"], atol=2e-7)
    np.savez_compressed(
        path,
        prediction=result["fractions"],
        spectral_RMSE=result["direct_RMSE"],
        reference_indices=result["model_indices"],
        reference_fractions=result["member_fractions"],
        complexity=result["complexity"],
    )
    save_json(
        OUT / "models" / f"{name}_{scheme}_mesma_metadata.json",
        dict(
            model_count=result["model_count"],
            seconds=result["seconds"],
            max_components=3,
            one_reference_per_category=True,
        ),
    )
    print(
        f"FINISHED {name}/{scheme}: {result['model_count']:,} models per target",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        raise ValueError("Use 1-4 independent search workers")
    libraries, _, targets, truth, meta, _, _ = prepare()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(run_cell, name, scheme, lib, targets)
            for scheme in SCHEMES
            for name, lib in libraries.items()
        ]
        for future in as_completed(futures):
            future.result()
    summarize(truth, meta)


if __name__ == "__main__":
    main()
