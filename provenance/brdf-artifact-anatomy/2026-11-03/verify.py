"""Verify actual report evidence, preserved inputs and compact output contracts."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    checks = {}
    provenance = read("provenance.json")
    before = provenance["source_hashes_before"]
    after = {p: sha(p) for p in before}
    assert before == after, "Protected source changed"
    checks["protected_source_files_unchanged"] = len(before)
    for revision in [
        provenance["historical_implementation_revision"],
        provenance["original_run_QA_revision"],
    ]:
        blob = subprocess.check_output(
            ["git", "show", f"{revision}:src/spectralbridge/corrections.py"], cwd=ROOT
        )
        assert hashlib.sha256(blob).hexdigest() == provenance["historical_sha256"]
    checks["historical_code_matches_both_recorded_revisions"] = True
    for path in (HERE / "models").glob("*.json"):
        original = next(p for p in before if p.endswith("/" + path.name))
        assert sha(path) == before[original]
    checks["copied_models_match_originals"] = True
    replay = read("replay_validation.json")
    assert replay["current_cached_stage_mismatches"] == 0
    assert replay["current_cached_mask_mismatches"] == 0
    assert replay["red_factor_cache_exact"] and replay["red_denominator_cache_exact"]
    assert not replay["production_raster_currently_local"]
    checks["cache_replay_exact_prior_production_check_explicitly_reused"] = True
    fits = read("historical_fit_reconstruction.json")
    assert all(
        r["coefficient_exact_match"] for r in fits if r["reconstructed"] is not None
    )
    checks["nonneutral_coefficient_vectors_reconstructed_exactly"] = sum(
        r["reconstructed"] is not None for r in fits
    )
    flights = read("flight_comparison.json")
    assert all(
        f["modern_angular_design"]["rank"] == 1
        and not f["modern_angular_design"]["supported"]
        for f in flights.values()
    )
    bands = read("band_diagnostics.json")
    assert all(b["formula_replay_mismatches"] == 0 for b in bands)
    checks["all_band_formula_replay_mismatches"] = 0
    red = next(
        b for b in bands if b["flight"] == "goldhill" and b["wavelength_nm"] == 650
    )
    red_path = next(p for p in before if p.endswith("/red_factor.npy"))
    assert (
        float(np.nanmax(np.load(red_path, mmap_mode="r")))
        == red["factor_full_H5"]["max"]
    )
    boundary = read("boundary_correspondence.json")
    main_edge = boundary["main_denominator_transition_only"]
    assert boundary["xor_edges"] == main_edge["xor_edges"] == 0
    assert boundary["dice"] == main_edge["dice"] == 1
    assert boundary["max_directed_edge_displacement_m"] == 0
    assert (
        boundary["actual_edges"] - main_edge["actual_edges"]
        == boundary["denominator_only_extra_state_edges"]
    )
    checks["measured_boundary_edges"] = boundary["actual_edges"]
    checks["measured_main_streak_edges"] = main_edge["actual_edges"]
    selection = read("selection.json")
    r0, r1, c0, c1 = selection["roi_native_indices"]
    pixels = pd.read_csv(HERE / "pixel_trajectories.csv")
    assert (
        pixels.row.between(r0, r1 - 1).all() and pixels.column.between(c0, c1 - 1).all()
    )
    assert pixels.common_observed_valid.all()
    assert len(pixels) == len(selection["pixels"]) * len(fits)
    checks["tracked_band_observations_valid"] = len(pixels)
    poly = pd.read_csv(HERE / "polygon_stage_spectra.csv")
    grouped = poly.groupby("stage").agg(
        polygons=("GlobalID", "nunique"), memberships=("pixels", "sum")
    )
    assert grouped.polygons.nunique() == grouped.memberships.nunique() == 1
    assert poly.groupby("GlobalID").pixels.nunique().eq(1).all()
    assert poly.nonfinite_values.eq(0).all()
    checks["paired_polygons_per_stage"] = int(grouped.polygons.iloc[0])
    checks["paired_memberships_per_stage"] = int(grouped.memberships.iloc[0])
    zoom = np.load(HERE / "goldhill_zoom.npz")
    indices = np.array([5, 3, 1])
    raw, brdf = zoom["raw"][..., indices], zoom["brdf"][..., indices]
    valid = zoom["observed"] & np.isfinite(raw).all(-1) & np.isfinite(brdf).all(-1)
    changed = int(np.count_nonzero(raw[valid] != brdf[valid]))
    display = read("display_contract.json")
    assert changed == display["generic_QA_RGB_BRDF_only_changed_values"] == 0
    assert (
        "_DEFAULT_RGB_TARGETS = (660.0, 560.0, 490.0)"
        in (ROOT / "src/spectralbridge/qa_plots.py").read_text()
    )
    checks["generic_RGB_omits_corrupted_bands_and_is_unchanged"] = True
    pages = read("report_pages.json")
    figures = read("figure_manifest.json")
    assert sum("figure" in p for p in pages) == len(figures)
    for f in figures:
        for suffix in [".png", ".svg"]:
            assert (HERE / (f["name"] + suffix)).stat().st_size > 1000
    md = (HERE / "report.md").read_text()
    for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md):
        assert (HERE / image).is_file()
    assert all(page["title"] in md for page in pages)
    info = subprocess.check_output(
        ["pdfinfo", str(HERE / "anatomy_of_a_red_artifact.pdf")], text=True
    )
    assert int(re.search(r"Pages:\s+(\d+)", info).group(1)) == len(pages)
    checks["report_pages"] = len(pages)
    checks["high_resolution_figure_pairs"] = len(figures)
    assert not any(p.suffix.lower() in [".h5", ".tif", ".img"] for p in HERE.rglob("*"))
    checks["no_production_rasters_created"] = True
    versions = {
        name: importlib.metadata.version(name)
        for name in [
            "numpy",
            "scipy",
            "pandas",
            "geopandas",
            "rasterio",
            "h5py",
            "matplotlib",
        ]
    }
    result = dict(
        status="PASS",
        checks=checks,
        python=platform.python_version(),
        versions=versions,
        final_source_hashes=after,
        auxiliary_snapshot_hashes={
            "goldhill_production_qa.json": sha(HERE / "goldhill_production_qa.json")
        },
        scientific_limits="Physical calibration, source camera rays, timing and independent validation remain unresolved; current correction gates and production source files unchanged.",
    )
    (HERE / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
