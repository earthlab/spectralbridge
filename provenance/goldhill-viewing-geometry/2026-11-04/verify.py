"""Verify source preservation and experimental outputs without promoting them."""

import json
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import rasterio

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P172 = ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"
sys.path.insert(0, str(P172))
from common import sha, safe, SOURCE  # noqa:E402

WORK = Path("/private/tmp/goldhill-viewing-geometry-20261104")


def read(name):
    return json.loads((HERE / name).read_text())


def write(name, value):
    (HERE / name).write_text(json.dumps(safe(value), indent=2, allow_nan=False) + "\n")


def main():
    manifest = read("input_manifest.json")
    protected = manifest["protected_hashes"]
    print("Checking", len(protected), "source and completed-P172 hashes", flush=True)
    for path, expected in protected.items():
        assert sha(path) == expected, path
    prior_missing = []
    prior_available = 0
    for path, expected in manifest.get("prior_expected_hashes", {}).items():
        if Path(path).exists():
            assert sha(path) == expected, path
            prior_available += 1
        else:
            prior_missing.append(
                dict(
                    path=path,
                    expected_sha256=expected,
                    status="HISTORICAL_TEMPORARY_PATH_UNAVAILABLE_NOT_USED_OR_RECREATED",
                )
            )
    write(
        "historical_source_availability.json",
        dict(
            available_prior_hashes_unchanged=prior_available,
            unavailable_prior_paths=prior_missing,
            task_direct_inputs_all_verified=True,
        ),
    )
    baseline = json.loads((P172 / "verification.json").read_text())
    for source in baseline["software"]:
        assert sha(ROOT / source["path"]) == source["current_sha256"], source["path"]
    assert (
        sha(ROOT / "src/spectralbridge/corrections.py")
        == manifest["source_module_sha256"]
    )
    artifacts = {}
    native = read("native_artifacts.json")
    assert native["module_sha256"] == sha(
        ROOT / "src/spectralbridge/drone_view_geometry.py"
    )
    assert native["script_sha256"] == sha(HERE / "reconstruct.py")
    for path, expected in native["artifacts"].items():
        assert sha(path) == expected, path
    statuses = read("experiment_status.json")
    assert len(statuses) == 8
    with rasterio.open(SOURCE) as src:
        source_profile = (src.crs, src.shape, src.transform)
        alpha = src.dataset_mask() > 0
    decoded = np.load(
        "/private/tmp/goldhill-clean-source-brdf-20261103/clean_candidate.npy",
        mmap_mode="r",
    )
    decode_checks = []
    with rasterio.open(SOURCE) as src:
        for band in range(10):
            original = src.read(band + 1)
            expected = original * np.float32(0.0001999969482421875)
            assert np.array_equal(expected[alpha], decoded[..., band][alpha]), band
            decode_checks.append(dict(band=band, exact_conditional_decode=True))
    complete = []
    for status in statuses:
        assert (
            status["image_created"]
            and status["numerical_status"] == "VALID"
            and status["supported_bands"] == 10
        )
        model = read(status["branch"] + "_model.json")
        assert model["radiometry"]["status"] == "HYPOTHETICAL_UNVERIFIED"
        for f in model["validation"]["fits"]:
            assert (
                f["rank"] == 3
                and f["stable_rank"] == 3
                and f["unsupported_application_predictions"] == 0
            )
        output = np.load(status["array"], mmap_mode="r")
        with rasterio.open(status["image"]) as src:
            assert (
                src.count == 10
                and src.crs == source_profile[0]
                and src.shape == source_profile[1]
            )
            np.testing.assert_allclose(
                tuple(src.transform), tuple(source_profile[2]), rtol=0, atol=1e-6
            )
            assert src.tags()["CALIBRATION"] == "HYPOTHETICAL_UNVERIFIED"
            assert (
                src.tags()["STATUS"] == "EXPERIMENTAL_NOT_VALIDATED"
                and src.tags()["PRODUCTION_APPROVED"] == "false"
            )
            for y in range(0, src.height, 128):
                end = min(y + 128, src.height)
                restored = np.moveaxis(
                    src.read(window=((y, end), (0, src.width))), 0, -1
                )
                assert np.array_equal(restored, output[y:end], equal_nan=True)
        artifacts[status["image"]] = sha(status["image"])
        artifacts[status["array"]] = sha(status["array"])
        complete.append(
            dict(
                branch=status["branch"],
                ten_band_native_GeoTIFF_exact=True,
                numerical_fit="VALID",
                scientific_status="EXPERIMENTAL_NOT_VALIDATED",
            )
        )
    # No altered membership support or class labels; compare serialized fold IDs canonically.
    oldfold = pd.read_csv(P172 / "classification_memberships.csv").astype(str)
    fold = pd.read_csv(HERE / "classification_memberships.csv").astype(str)
    pd.testing.assert_frame_equal(oldfold, fold)
    assert all(
        r["memberships"] == 144406 and r["polygons"] == 157
        for r in read("classification_summary.json")
    )
    metrics = read("matched_metrics.json")
    assert all(r["missing_from_fixed_P172_support"] == 0 for r in metrics)
    assert len(pd.read_csv(HERE / "minimum_source_subset.csv")) == 40
    assert len(read("fit_sensitivity.json")) == 24
    # Real, supported NEON values and masks must match the preceding task exactly.
    neon = read("neon_after_control.json")
    assert (
        neon["source_sha256"]
        == json.loads((P172 / "neon_after_control.json").read_text())["source_sha256"]
    )
    neon_records = []
    for mode, record in zip(["brdf", "combined"], neon["controls"]):
        assert record["status"] == "VALID" and record["supported_bands"] == 10
        assert record["serialized_control"]["accepted_library_contract"]
        before = np.load(
            "/private/tmp/goldhill-clean-source-brdf-20261103/neon_after_"
            + mode
            + ".npy",
            mmap_mode="r",
        )
        after = np.load(WORK / ("neon_after_" + mode + ".npy"), mmap_mode="r")
        assert np.array_equal(before, after, equal_nan=True)
        neon_records.append(
            dict(mode=mode, exact_values_and_masks=True, max_absolute_difference=0)
        )
    suites = list(
        ET.parse("/private/tmp/p173_final_tests.xml").getroot().iter("testsuite")
    )
    tests = {
        k: sum(int(s.attrib.get(k, 0)) for s in suites)
        for k in ["tests", "errors", "failures", "skipped"]
    }
    assert tests == dict(tests=163, errors=0, failures=0, skipped=0)
    logs = HERE / "verification_logs"
    logs.mkdir(exist_ok=True)
    for pattern in ["p173_*.log", "p173_*tests.xml"]:
        for path in Path("/private/tmp").glob(pattern):
            shutil.copyfile(path, logs / path.name)
    for name in ["raw_access_network.log", "metadata_live.log", "ancillary_live.log"]:
        shutil.copyfile(WORK / name, logs / name)
    write("large_artifacts.json", artifacts)
    write(
        "verification.json",
        dict(
            status="PASS",
            protected_source_and_prior_artifact_count=len(protected),
            protected_hashes_unchanged=True,
            prior_available_hashes_unchanged=prior_available,
            prior_temporary_paths_unavailable=prior_missing,
            core_P172_scientific_modules_unchanged=True,
            main_outputs=complete,
            NEON_regression=neon_records,
            test_results=tests,
            native_grid=[2238, 3165],
            ground_support=6683905,
            original_source_footprint=6683944,
            terrain_missing=39,
            unchanged_polygon_memberships=144406,
            unchanged_independent_ids=157,
            unchanged_identity_folds=True,
            source_to_experiment_decode=decode_checks,
            geometry="INFERRED_NADIR_NOT_VERIFIED_CONTRIBUTORS",
            calibration="HYPOTHETICAL_UNVERIFIED",
            official_library_created=False,
            BRDF_disabled=False,
            PDF_sha256=sha(HERE / "goldhill_viewing_geometry_experiment.pdf"),
            implementation_sha256=sha(
                ROOT / "src/spectralbridge/drone_view_geometry.py"
            ),
        ),
    )
    write(
        "artifact_checksums.json",
        {
            str(p.relative_to(HERE)): sha(p)
            for p in sorted(HERE.rglob("*"))
            if p.is_file()
            and p.name != "artifact_checksums.json"
            and "__pycache__" not in p.parts
        },
    )
    print(
        "PASS:",
        tests,
        "eight exact experimental rasters; protected hashes unchanged",
        flush=True,
    )


if __name__ == "__main__":
    main()
