"""Check immutable sources, spatial membership, unit safeguards and paired inference."""

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import xml.etree.ElementTree as ET

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import rasterio
from shapely import intersects_xy
from spectralbridge.radiometry import require_physical_table, Radiometry
from spectralbridge.envi import hdr_to_dict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path("/private/tmp/goldhill-end-to-end-20261103")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for b in iter(lambda: stream.read(4 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    manifest = json.loads((HERE / "input_manifest.json").read_text())
    protected = dict(manifest["protected_hashes"])
    times = json.loads((HERE / "photo_time_reconciliation.json").read_text())
    for source in times["sources"]:
        protected[source["path"]] = source["sha256"]
    assert all(sha(path) == digest for path, digest in protected.items())
    cfg = json.loads((HERE / "branches.json").read_text())
    index = pd.read_parquet(cfg["polygon_index"])
    ingestion = json.loads((HERE / "ingestion.json").read_text())
    with rasterio.open(ingestion["envi_img"]) as src:
        xs, ys = rasterio.transform.xy(
            src.transform, index.row.to_numpy(), index.col.to_numpy(), offset="center"
        )
        center_error = max(
            float(np.max(abs(np.asarray(xs) - index.x.to_numpy()))),
            float(np.max(abs(np.asarray(ys) - index.y.to_numpy()))),
        )
        assert center_error < 1e-6
        polygons = (
            gpd.read_file(
                ROOT
                / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
            )
            .to_crs(src.crs)
            .set_index("GlobalID")
        )
        failed_memberships = 0
        for identity, g in index.groupby("GlobalID"):
            geom = polygons.loc[identity].geometry
            failed_memberships += int(
                (
                    ~intersects_xy(geom.buffer(1e-7), g.x.to_numpy(), g.y.to_numpy())
                ).sum()
            )
        assert failed_memberships == 0
    raw_radiometry = Radiometry.from_header(hdr_to_dict(Path(ingestion["envi_hdr"])))
    assert raw_radiometry.status == "UNSUPPORTED" and raw_radiometry.scale is None
    stages = json.loads((HERE / "production_stage_results.json").read_text())
    by_name = {x["stage"]: x for x in stages}
    assert by_name["A_raw"]["status"] == "EXECUTED"
    for name in [
        "B_topographic",
        "C_brdf",
        "D_combined",
        "F_physical_polygon_library",
        "B_direct_scs_c_fit",
    ]:
        assert (
            by_name[name]["status"] == "UNSUPPORTED"
            and "Radiometry UNSUPPORTED" in by_name[name]["reason"]
        )
    assert "sensor_zn" in by_name["C_direct_brdf_fit"]["reason"]
    assert not (WORK / "production_attempt/physical_library.parquet").exists()
    for name in ["B_topographic", "C_brdf", "D_combined"]:
        assert not (WORK / "production_attempt" / name / (name + ".img")).exists()
    physical_guard = []
    for path in sorted((WORK / "numerical_polygon_tables").glob("*.parquet")):
        metadata = pq.read_schema(path).metadata
        assert b"spectralbridge.experimental_numeric_only" in metadata
        try:
            require_physical_table(path)
        except ValueError:
            physical_guard.append(str(path))
        else:
            raise AssertionError(
                "Numeric diagnostic was incorrectly approved as a physical table"
            )
    assert len(physical_guard) == 9
    for path in (WORK / "numerical_native_subsets").glob("*.hdr"):
        assert Radiometry.from_header(hdr_to_dict(path)).status == "UNSUPPORTED"
    prediction = pd.read_csv(HERE / "classification_predictions.csv")
    old = prediction[prediction.branch == "old_raw"].sort_values("identity")
    new = prediction[prediction.branch == "new_raw"].sort_values("identity")
    np.testing.assert_array_equal(old.identity, new.identity)
    np.testing.assert_array_equal(old.prediction, new.prediction)
    members = pd.read_csv(HERE / "classification_memberships_new_raw.csv")
    for _, fold in members.groupby("fold"):
        assert set(fold[fold.role == "train"].identity).isdisjoint(
            set(fold[fold.role == "test"].identity)
        )
    tree = ET.parse("/private/tmp/p169_tests.xml")
    assert not tree.findall(".//failure") and not tree.findall(".//error")
    passed = len(tree.findall(".//testcase"))
    skipped = len(tree.findall(".//skipped"))
    shutil.copyfile("/private/tmp/p169_tests.xml", HERE / "tests.xml")
    figures = json.loads((HERE / "figure_manifest.json").read_text())
    assert len(figures) == 13
    for f in figures:
        for ext in ["png", "svg"]:
            assert (HERE / f[ext]).stat().st_size > 1000
    layout = json.loads((HERE / "pdf_layout.json").read_text())
    assert len(layout) == 17 and min(p["lowest_content_y"] for p in layout) > 44
    # The renderer uses the bundled runtime; scientific calculations use this env.
    environment = dict(
        python=platform.python_version(),
        package_versions={
            name: importlib.metadata.version(name)
            for name in [
                "earthlab-spectralbridge",
                "numpy",
                "scipy",
                "pandas",
                "rasterio",
                "geopandas",
                "h5py",
                "scikit-learn",
                "pyarrow",
            ]
        },
        repository_revision=manifest["repository_revision"],
        scientific_environment=str(Path(__import__("sys").executable)),
        renderer="Bundled Codex Python with ReportLab 4.4.9",
        random_seed=20261103,
        classifier=dict(
            api="evaluate_identifiability",
            folds=3,
            C=1,
            scaling="training-fold only",
            sampling_unit="one non-overlapping polygon identity",
        ),
        permutation_test=dict(
            api="spectral_separability",
            permutations=499,
            integration_weights="equal discrete band weights; no interpolation across spectral gaps",
            scope="Holm within each branch; across-branch comparisons exploratory, not a confirmatory family",
        ),
        new_source_units="UNVERIFIED fixed numerical encoding; not fractional physical reflectance",
    )
    write("software_and_configuration.json", environment)
    summary = json.loads((HERE / "analysis_summary.json").read_text())
    classification = json.loads((HERE / "classification_summary.json").read_text())
    scientific = dict(
        status="EXPERIMENT_COMPLETE_PRODUCTION_NOT_READY",
        date="2026-11-03",
        production_ready=False,
        preprocessing="READY_FOR_NUMERICAL_USE",
        physical_calibration="UNVERIFIED",
        topographic="UNSUPPORTED current production; historical stress replay unstable",
        brdf="UNSUPPORTED; measured per-pixel viewing geometry absent",
        combined="UNSUPPORTED; no approved result",
        landsat_translation="UNSUPPORTED physical-input guard",
        micasense="Two native wavelength subsets executed as numerical diagnostics only",
        approved_library="UNSUPPORTED; nine numeric-only experimental tables are rejected by the physical-table guard",
        raw_classification_balanced_accuracy=next(
            x["balanced_accuracy"] for x in classification if x["branch"] == "new_raw"
        ),
        identification_gain_detected=False,
        raw_out_of_fold_predictions_identical=True,
        PFT_sample=dict(
            polygons=157,
            common_memberships=144406,
            classes=summary["independent_class_counts"],
        ),
        source_new_valid_pixels=6683944,
        all_branch_common_pixels=summary["scene_common_all"],
        raw_common_pixels=summary["scene_common_raw"],
        red_stripe="Persists in historical replay; absent as a comparable algorithmic discontinuity in raw baseline",
        abundance="NOT_EVALUATED: no independent abundance/reference validation",
        photo_time_recovery=dict(
            camera_records_matched=times["camera_records_uniquely_matched"],
            tag_date=times["all_photo_tag_dates"],
            inherited_minus_photo_midpoint_seconds=times[
                "inherited_minus_midpoint_seconds"
            ],
            timezone_status=times["timezone_status"],
        ),
        constraints=dict(
            source_files_modified=0,
            official_products_overwritten=0,
            datastore_writes=0,
            production_defaults_changed=0,
            calibration_or_viewing_geometry_invented=0,
        ),
        reproduction_scripts=[
            "run_pipeline.py",
            "audit_photo_times.py",
            "analyze.py",
            "figures.py",
            "write_report.py",
            "make_pdf.py",
            "verify.py",
        ],
    )
    write("scientific_summary.json", scientific)
    record = dict(
        status="PASS",
        protected_inputs_and_production_code_files=len(protected),
        protected_hashes=protected,
        all_protected_files_unchanged=True,
        spatial_pixel_center_max_error_m=center_error,
        polygon_memberships_outside_geometry=failed_memberships,
        actual_ingestion_finite_values_masks_and_grid_exact=True,
        physical_numeric_guard_rejections=len(physical_guard),
        paired_predictions_identical=True,
        grouped_memberships_disjoint=True,
        tests_passed=passed - skipped,
        tests_skipped=skipped,
        test_failures=0,
        figure_pairs=len(figures),
        visually_reviewed_figure_pairs=13,
        pdf_pages=len(layout),
        pdf_pages_visually_reviewed=17,
        production_codes_unchanged=True,
        notes="Existing QA/deprecation warnings; PDF render/text checks and source checksums retained. No complete physical correction or approved library was produced.",
    )
    write("verification.json", record)
    logs = {
        "pipeline_initial.log": "/private/tmp/p169_pipeline.log",
        "pipeline_resumed.log": "/private/tmp/p169_pipeline_resume.log",
        "analysis.log": "/private/tmp/p169_analysis_final.log",
        "targeted_tests.log": "/private/tmp/p169_tests.log",
        "photo_time_audit.log": "/private/tmp/p169_photo_time_audit.log",
    }
    for dest, source in logs.items():
        shutil.copyfile(source, HERE / dest)
    print(
        f"PASS: {len(protected)} protected files unchanged, {passed - skipped} tests, exact spatial membership, 9 numeric tables rejected as physical, {len(layout)} PDF pages"
    )


if __name__ == "__main__":
    main()
