"""Native-grid conditional correction refits with fixed source shade exclusions.

Preserves the November 5 experimental calibration boundary and frozen numerical
implementation. This tests model support, not physical calibration approval.
Runs baseline and all three previously frozen masks; no threshold is chosen by
its QA result. Raster application/translation is not part of this fit test.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from threadpoolctl import threadpool_limits

from drone_shade_mask_preview import ROOT, MASKS, file_sha256
from spectralbridge.bulk.provenance import write_json_atomic

PRIOR = ROOT / "provenance/drone-camera-rerun/2026-11-05"
FROZEN = ROOT / "provenance/drone-correction-stability/2026-11-05/stable_qr_v1"
BASE = ROOT / "archive/local/drone-correction-stability/2026-11-05/stable_qr_v1"
DEST = (
    ROOT / "provenance/drone-calibration-translation/2026-11-19/shade-excluded-refit-v2"
)
POLICY = dict(
    variants=["baseline", "conservative", "moderate", "stronger"],
    thresholds=[None, 0.1, 0.2, 0.3],
    equations="frozen November5 stable_qr_v1",
    shade_excluded_from="fitting and modeled application/validation spatial domain",
    fit_subset="original training subset (field polygons +2m buffer excluded) intersect retained mask",
    uncertainty="original20m spatial groups unchanged",
    reference="original45deg solar/nadir; exact original serialized reference vector",
    rho_limits="original0..2",
    independently_calibrated=False,
    interpretation="conditional experimental model support; no production acceptance or translation",
    original_images_reprocessed=False,
    all_variants_reported=True,
)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def retained_training(original, mask):
    if original.shape != mask.shape or original.dtype != bool:
        raise ValueError("Original boolean training grid and candidate mask must match")
    if not np.isin(mask, [0, 1, 255]).all():
        raise ValueError("Unknown shade mask code")
    return original & (mask == 0)


def setup():
    sys.path.insert(0, str(PRIOR))
    import correct_sites as driver

    sys.path.remove(str(PRIOR))
    topo = load_module(
        "spectralbridge._shade_refit_topographic", FROZEN / "source_topographic.py"
    )
    corrections = load_module(
        "spectralbridge._shade_refit_corrections", FROZEN / "source_corrections.py"
    )
    corrections.cluster_covariance = topo.cluster_covariance
    corrections.apply_conditioned_scs_c = topo.apply_conditioned_scs_c
    driver.support.c = corrections
    driver.support.topo = topo
    return driver


def cube_inputs(driver, config):
    folder = BASE / config["site"].lower()
    raw = np.load(folder / "candidate_stored.npy", mmap_mode="r")
    maps = np.load(folder / "geometry.npy", mmap_mode="r")
    design = np.load(folder / "center_design.npy", mmap_mode="r")
    solar = np.load(config["solar_arrays"], mmap_mode="r")
    geometry = dict(
        solar_zn=solar[..., 0],
        solar_az=solar[..., 1],
        sensor_zn=maps[..., 1],
        sensor_az=maps[..., 2],
    )
    for name, path in config["terrain_ancillary"].items():
        with rasterio.open(path) as src:
            values = src.read(1)
            geometry[name] = np.where(src.read_masks(1) > 0, values, np.nan)
    with rasterio.open(config["prepared"]) as src:
        footprint = src.dataset_mask() > 0
        transform, crs = src.transform, src.crs
    domain = footprint & (maps[..., 0] > 0)
    previous = json.loads(
        next((folder / "brdf_only").glob("*brdf_model.json")).read_text()
    )
    if int(domain.sum()) != previous["fitting_population"]["available_spatial"]:
        raise ValueError("Reconstructed original spatial population differs")
    training = np.load(folder / "training_mask.npy").astype(bool)
    if np.any(training & ~domain):
        raise ValueError("Original training pixels outside reconstructed domain")
    groups = np.load(folder / "spatial_groups.npy", mmap_mode="r")
    return raw, design, geometry, footprint, domain, training, groups, transform, crs


def verify_baseline(topo, models, folder):
    """Require same native fit coefficients/statuses before mask comparisons."""
    old_topo = json.loads((folder / "conditioned_scsc_model.json").read_text())
    for a, b in zip(topo["fits"], old_topo["fits"]):
        assert a["status"] == b["status"] and a["n"] == b["n"]
        if a.get("C") is not None:
            np.testing.assert_allclose(a["C"], b["C"], rtol=1e-10, atol=1e-12)
    for branch, model in models.items():
        old = json.loads(next((folder / branch).glob("*brdf_model.json")).read_text())
        assert model["kernel_config"] == old["kernel_config"]
        assert model["ndvi_config"] == old["ndvi_config"]
        np.testing.assert_allclose(
            model["reference_design"], old["reference_design"], rtol=1e-12, atol=1e-12
        )
        assert model["validation"]["status"] == old["validation"]["status"]
        assert len(model["validation"]["fits"]) == len(old["validation"]["fits"])
        for a, b in zip(model["validation"]["fits"], old["validation"]["fits"]):
            assert a["status"] == b["status"] and a["eligible"] == b["eligible"]
            np.testing.assert_allclose(
                a["diagnostic_coefficient_estimate"],
                b["diagnostic_coefficient_estimate"],
                rtol=1e-8,
                atol=1e-10,
            )
    return True


def mask_filename(flight_stem, threshold):
    """Keep integer legacy names, distinguish fractional cutoff percentages."""
    token = f"{threshold * 100:.6f}".rstrip("0").rstrip(".").replace(".", "p").zfill(2)
    return f"{flight_stem}__shade_candidate_relative_visible_{token}pct.tif"


def run(site, mask_inventory_path=None, variants=None):
    DEST.mkdir(parents=True, exist_ok=True)
    policy = json.loads(json.dumps(POLICY))
    path = DEST / "experiment_policy.json"
    if path.exists() and json.loads(path.read_text()) != policy:
        raise ValueError("Frozen experiment changed; create a new version")
    if not path.exists():
        write_json_atomic(path, policy)
    driver = setup()
    config = next(
        c
        for c in json.loads((PRIOR / "site_inputs.json").read_text())
        if c["site"].lower() == site
    )
    (
        raw,
        design,
        geometry,
        footprint,
        original_domain,
        original_training,
        groups,
        transform,
        crs,
    ) = cube_inputs(driver, config)
    baseline_configuration = json.loads(
        next((BASE / site / "brdf_only").glob("*brdf_model.json")).read_text()
    )
    design_hash = file_sha256(BASE / site / "center_design.npy")
    mask_provenance = json.loads(
        (
            mask_inventory_path or (DEST.parent / "shade-review/source_provenance.json")
        ).read_text()
    )
    source_identity = {
        name: file_sha256(BASE / site / name)
        for name in [
            "candidate_stored.npy",
            "center_design.npy",
            "geometry.npy",
            "training_mask.npy",
            "spatial_groups.npy",
        ]
    }
    source_identity.update(
        solar_sha256=file_sha256(Path(config["solar_arrays"])),
        frozen_corrections_sha256=file_sha256(FROZEN / "source_corrections.py"),
        frozen_topographic_sha256=file_sha256(FROZEN / "source_topographic.py"),
    )
    # Additive frozen site contract covers ancillary/configuration dependencies
    # beyond the compact original per-variant source identity.
    contract = dict(
        original_sources=source_identity,
        original_domain_sha256=hashlib.sha256(original_domain.tobytes()).hexdigest(),
        prepared_sha256=file_sha256(Path(config["prepared"])),
        terrain_ancillary_sha256={
            key: file_sha256(Path(value))
            for key, value in config["terrain_ancillary"].items()
        },
        fit_settings={
            key: baseline_configuration[key]
            for key in [
                "kernel_config",
                "ndvi_config",
                "reference_geometry",
                "reference_design",
                "rho_min",
                "rho_max",
            ]
        },
        research_adapter_sha256=file_sha256(
            ROOT
            / "provenance/drone-integrated-reliability/2026-11-04/experiment_support.py"
        ),
        original_hypothesis_adapter_sha256=file_sha256(
            ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03/common.py"
        ),
    )
    contract_path = DEST / site / "input_contract.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    if contract_path.exists() and json.loads(contract_path.read_text()) != contract:
        raise ValueError("Frozen source ancillary/configuration contract changed")
    write_json_atomic(contract_path, contract)
    with threadpool_limits(limits=1):
        for variant, threshold in zip(POLICY["variants"], POLICY["thresholds"]):
            if variants is not None and variant not in variants:
                continue
            folder = DEST / site / variant
            folder.mkdir(parents=True, exist_ok=True)
            keep = np.ones(original_domain.shape, bool)
            mask_hash = None
            if threshold is not None:
                mask_path = MASKS / mask_filename(config["flight_stem"], threshold)
                mask_hash = file_sha256(mask_path)
                if mask_hash != mask_provenance["mask_sha256"][mask_path.name]:
                    raise ValueError("Previously reviewed shade mask changed")
                with rasterio.open(mask_path) as src:
                    assert (
                        src.shape == keep.shape
                        and src.transform == transform
                        and src.crs == crs
                    )
                    mask = src.read(1)
                training = retained_training(original_training, mask)
                keep = mask == 0
            else:
                training = original_training.copy()
            identity = dict(
                sources=source_identity, mask_sha256=mask_hash, policy=policy
            )
            checkpoint = folder / "completed.json"
            if checkpoint.exists():
                saved = json.loads(checkpoint.read_text())
                if saved["identity"] != identity:
                    raise ValueError("Stale completed refit")
                for name, digest in saved["outputs"].items():
                    if file_sha256(folder / name) != digest:
                        raise ValueError("Changed refit result")
                print(site, variant, "reused verified refit", flush=True)
                continue
            print(
                site,
                variant,
                "native fit start;",
                int(training.sum()),
                "training pixels",
                flush=True,
            )
            cube = driver.support.Cube(
                raw,
                original_domain & keep,
                geometry,
                scale=driver.SCALE,
                footprint=footprint,
            )
            cube.h5_path = Path(config["prepared"])
            cube.projection_wkt = crs.to_wkt()
            cube.transform = transform.to_gdal()
            fit_provenance = dict(
                experiment="shade-excluded native refit",
                variant=variant,
                original_training_sha256=source_identity["training_mask.npy"],
                candidate_mask_sha256=mask_hash,
                calibration="original conditional unverified hypothesis retained",
            )
            topo_path = folder / "conditioned_scsc_model.json"
            if topo_path.exists():
                topo = json.loads(topo_path.read_text())
                if topo["fit_provenance"] != fit_provenance:
                    raise ValueError("Stale partial topographic fit")
            else:
                topo = driver.support.isolated(
                    driver.support.topo.fit_conditioned_scs_c
                )(
                    cube,
                    policy=driver.support.topo.SCSCPolicy(),
                    uncertainty_groups=groups,
                    fitting_mask=training,
                    provenance=fit_provenance,
                )
                write_json_atomic(topo_path, driver.clean(topo))
            print(site, variant, "SCS+C", topo["validation_status"], flush=True)
            models = {}
            for branch, apply_topography in [("brdf_only", False), ("combined", True)]:
                print(site, variant, branch, "BRDF fit", flush=True)
                path = driver.support.isolated(
                    driver.support.c.fit_and_save_brdf_model, design, design_hash
                )(
                    cube,
                    folder / branch,
                    brdf_kernel_config=driver.support.c.BRDFKernelConfig(
                        **baseline_configuration["kernel_config"]
                    ),
                    ndvi_config=driver.support.c.NDVIBinningConfig(
                        **baseline_configuration["ndvi_config"]
                    ),
                    rho_min=baseline_configuration["rho_min"],
                    rho_max=baseline_configuration["rho_max"],
                    apply_topography=apply_topography,
                    fitting_mask=training,
                    fitting_provenance=fit_provenance,
                    uncertainty_groups=groups,
                    topographic_model=topo if apply_topography else None,
                )
                models[branch] = json.loads(path.read_text())
                print(
                    site,
                    variant,
                    branch,
                    models[branch]["validation"]["status"],
                    flush=True,
                )
            if variant == "baseline":
                verify_baseline(topo, models, BASE / site)
                print(site, "BASELINE NUMERIC REPRODUCTION VERIFIED", flush=True)
            summary = dict(
                site=site,
                variant=variant,
                threshold=threshold,
                training_pixels=int(training.sum()),
                spatial_pixels=int((original_domain & keep).sum()),
                topographic_status=topo["validation_status"],
                branches={
                    branch: dict(
                        status=m["validation"]["status"],
                        fits=[
                            {
                                k: f.get(k)
                                for k in [
                                    "band",
                                    "bin",
                                    "status",
                                    "reasons",
                                    "eligible",
                                    "reference_prediction",
                                    "reference_standard_error",
                                    "unresolved_prediction_count",
                                ]
                            }
                            for f in m["validation"]["fits"]
                        ],
                    )
                    for branch, m in models.items()
                },
                experimental=True,
                physical_calibration_verified=False,
                production_approved=False,
            )
            write_json_atomic(folder / "summary.json", summary)
            write_json_atomic(
                checkpoint,
                dict(
                    identity=identity,
                    outputs={
                        str(p.relative_to(folder)): file_sha256(p)
                        for p in folder.rglob("*.json")
                        if p != checkpoint
                    },
                    baseline_numeric_verified=(variant == "baseline"),
                    code_sha256=file_sha256(Path(__file__)),
                ),
            )
            del cube, models, topo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, choices=["ruby", "gordon", "goldhill"])
    run(parser.parse_args().site)
