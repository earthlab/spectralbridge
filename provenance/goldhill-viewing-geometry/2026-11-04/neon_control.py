# ruff: noqa: E402
"""Actual NEON observations and angular metadata; no synthetic signal substitute."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(
    0, str(HERE.parents[2] / "provenance/goldhill-clean-source-brdf/2026-11-03")
)
from common import NEON, WAVES, load_module, sha, dist  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")


def write(name, value):
    from common import safe

    (HERE / name).write_text(json.dumps(safe(value), indent=2) + "\n")


from spectralbridge.neon_cube import NeonCube  # noqa:E402
from spectralbridge import corrections  # noqa:E402
from spectralbridge.envi_writer import EnviWriter, finalize_scientific_header  # noqa:E402
from spectralbridge.radiometry import library_radiometry  # noqa:E402
import rasterio


def main(phase):
    mod = (
        load_module("spectralbridge._p172_before", HERE / "pre_edit_corrections.py")
        if phase == "before"
        else corrections
    )
    print("NEON real-data control", phase, "load fixed window", flush=True)
    c = NeonCube(NEON, line_slice=(350, 470), sample_slice=(1000, 4000))
    selected = np.array([np.argmin(abs(c.wavelengths - w)) for w in WAVES])
    c.data = c.data[..., selected].copy()
    c.wavelengths = c.wavelengths[selected]
    c.bands = len(selected)
    if c.fwhm is not None:
        c.fwhm = c.fwhm[selected]
    assert c.radiometry.status == "VALID"
    c.radiometry.require_valid()
    controls = []
    for topo in [False, True]:
        folder = (
            WORK
            / f"neon_{phase}_{'final_' if phase == 'after' else ''}{'combined' if topo else 'brdf'}"
        )

        path = mod.fit_and_save_brdf_model(
            c,
            folder,
            brdf_kernel_config=mod.HYTOOLS_BRDF_KERNEL_CONFIG,
            apply_topography=topo,
        )
        m = json.loads(path.read_text())
        print("NEON", phase, "topo", topo, m["validation"]["status"], flush=True)
        item = dict(
            apply_topography=topo,
            status=m["validation"]["status"],
            model_path=str(path),
            supported_bands=sum(
                r["status"] == "VALID" for r in m["validation"]["fits"]
            ),
            fits=m["validation"]["fits"],
        )
        (HERE / f"neon_{phase}_{'combined' if topo else 'brdf'}_model.json").write_text(
            json.dumps(m, indent=2) + "\n"
        )
        if m["validation"]["status"] == "VALID":
            before = c.data.copy()
            if topo:
                cc = np.array(m["topographic_c"], np.float32)
                data = mod.apply_topo_correct(
                    c, c.data, 0, c.lines, 0, c.columns, scs_c=cc
                )
            else:
                data = c.data
            corrected = mod.apply_brdf_correct(
                c,
                data,
                0,
                c.lines,
                0,
                c.columns,
                coeff_path=path,
                brdf_kernel_config=mod.HYTOOLS_BRDF_KERNEL_CONFIG,
                input_stage="topographic_only" if topo else "uncorrected",
            )
            physical = c.radiometry.to_physical(corrected)
            np.save(
                WORK / f"neon_{phase}_{'combined' if topo else 'brdf'}.npy", physical
            )
            assert np.array_equal(before, c.data, equal_nan=True)
            item["corrected_statistics"] = [
                dist(physical[..., b]) for b in range(c.bands)
            ]
            item["source_immutable"] = True
            if phase == "after":
                stem = WORK / f"neon_after_serialized_{'combined' if topo else 'brdf'}"
                header = c.build_envi_header()
                header.update(
                    {
                        "brdf status": "INCOMPLETE",
                        "brdf model schema": 2,
                        "brdf kernel math version": corrections.BRDF_KERNEL_MATH_VERSION,
                        "brdf validation policy": corrections.BRDF_VALIDATION_POLICY,
                    }
                )
                writer = EnviWriter(stem, header)
                writer.write_chunk(corrected, 0, 0)
                writer.close()
                finalize_scientific_header(
                    stem.with_suffix(".hdr"), header, brdf_status="VALID"
                )
                accepted = library_radiometry(stem.with_suffix(".img"))
                with rasterio.open(stem.with_suffix(".img")) as src:
                    restored = np.moveaxis(src.read(), 0, -1)
                assert np.array_equal(corrected, restored, equal_nan=True)
                assert accepted.status == "VALID"
                item["serialized_control"] = dict(
                    image=str(stem.with_suffix(".img")),
                    exact_stored_roundtrip=True,
                    accepted_library_contract=True,
                    validation_policy=corrections.BRDF_VALIDATION_POLICY,
                    scope="Bounded real NEON control only; no official library regeneration",
                )
        controls.append(item)
    write(
        f"neon_{phase}_control.json",
        dict(
            source=str(NEON),
            source_sha256=sha(NEON),
            window=dict(lines=[350, 470], samples=[1000, 4000]),
            band_indices=selected,
            wavelengths_nm=c.wavelengths,
            radiometry=c.radiometry.record(),
            controls=controls,
            scope="Real directional NEON observations;10nearest native channels as bounded shared-function regression control, not empirical calibration transfer to MicaSense.",
        ),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["before", "after"], required=True)
    a = p.parse_args()
    main(a.phase)
