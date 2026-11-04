"""Native assignment seams: factor jumps separated from measured raw edges."""

import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"))
from common import dist, safe  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")


def main():
    maps = np.load(WORK / "geometry_native.npy", mmap_mode="r")
    raw = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
        mmap_mode="r",
    )
    rows = []
    for scenario in ["A", "B", "C_uniform", "C_center"]:
        out = np.load(WORK / (scenario + "_brdf.npy"), mmap_mode="r")
        field = maps[..., 2 if scenario == "A" else 5 if scenario == "B" else 6]
        for band in [4, 7]:
            braw = raw[..., band]
            signal = out[..., band]
            cf = np.divide(
                signal, braw, out=np.full(braw.shape, np.nan), where=braw != 0
            )
            seam = field[:, :-1] != field[:, 1:]
            eligible = np.isfinite(cf[:, :-1]) & np.isfinite(cf[:, 1:])
            for label, chosen in [
                ("assignment_change", seam),
                ("no_assignment_change", ~seam),
            ]:
                select = eligible & chosen
                factorjump = abs(np.diff(cf, axis=1))[select]
                rawjump = abs(np.diff(braw, axis=1))[select]
                jump = abs(np.diff(signal, axis=1))[select]
                induced = abs(np.diff(cf, axis=1) * 0.5 * (braw[:, :-1] + braw[:, 1:]))[
                    select
                ]
                rows.append(
                    dict(
                        scenario=scenario,
                        wavelength=650 if band == 4 else 717,
                        edge_set=label,
                        definition="nearest ID"
                        if scenario == "A"
                        else "most-central ID"
                        if scenario == "B"
                        else "integer candidate-count change; not a single contributing-camera label",
                        edges=int(select.sum()),
                        factor_jump=dist(factorjump),
                        raw_jump=dist(rawjump),
                        corrected_jump=dist(jump),
                        factor_induced_signal_component=dist(induced),
                    )
                )
    (HERE / "assignment_boundary_metrics.json").write_text(
        json.dumps(safe(rows), indent=2) + "\n"
    )
    print("Assignment boundary metrics complete")


if __name__ == "__main__":
    main()
